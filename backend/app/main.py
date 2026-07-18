"""
FastAPI entry point for the Plant CPS prototype.

Run with:  uv run uvicorn app.main:app --reload
Docs at:   http://localhost:8000/docs
"""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .auth import (
    auth_backend,
    current_active_user,
    fastapi_users,
    init_db,
    require_operator,
)
from .email_util import EMAIL_ENABLED, send_email
from .mock_data import MockSensorService
from .models import User
from .profiles import profile_store
from .schemas import UserCreate, UserRead, UserUpdate

# Data source toggle. Real mode reads from P06's query API and publishes manual
# watering over MQTT. Demo mode (MOCK_DATA=true) uses a self-contained mock with
# NO cps-schema / P06 / MQTT dependency, so it runs standalone for live demos.
MOCK_DATA = os.getenv("MOCK_DATA", "false").lower() in ("1", "true", "yes", "on")

if MOCK_DATA:
    from .mock_data import mock_service as sensor_service

    watering_publisher = None
else:
    from .mqtt_publisher import watering_publisher
    from .sensors import sensor_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await sensor_service.start()
    if watering_publisher is not None:
        watering_publisher.start()
    yield
    if watering_publisher is not None:
        watering_publisher.stop()
    await sensor_service.stop()


app = FastAPI(
    title="Plant CPS API (Prototype)",
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Auth (fastapi-users)
# ---------------------------------------------------------------------------
app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/api/auth/jwt",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/api/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/api/users",
    tags=["users"],
)


# ---------------------------------------------------------------------------
# Sensors - all authenticated users
# ---------------------------------------------------------------------------
@app.get("/api/sensors/latest")
async def latest(_: User = Depends(current_active_user)):
    return sensor_service.get_latest()


@app.get("/api/sensors/history")
async def history(
    sensor: str,
    max_points: int = 200,
    hours: int = Query(default=24, ge=1, le=168),
    _: User = Depends(current_active_user),
):
    if sensor not in ("moisture", "temperature", "tank_level"):
        raise HTTPException(status_code=400, detail="Unknown sensor")
    return await sensor_service.get_history(sensor, max_points=max_points, hours=hours)


@app.get("/api/system/status")
async def system_status(_: User = Depends(current_active_user)):
    return sensor_service.system_status()


@app.get("/api/system/components")
async def system_components(_: User = Depends(current_active_user)):
    return sensor_service.get_component_health()


# ---------------------------------------------------------------------------
# Email notifications (stretch goal). Operator sends a test mail to the mock
# SMTP server (Mailpit) to demo the feature.
# ---------------------------------------------------------------------------
@app.post("/api/notify/test")
async def notify_test(user: User = Depends(require_operator)):
    if not EMAIL_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Email is disabled. Set EMAIL_ENABLED=true and run Mailpit (:1025).",
        )
    ok = await send_email(
        "🌱 Plant CPS - test notification",
        f"This is a test alert notification from the Plant CPS dashboard.\n"
        f"Requested by {user.email}.",
    )
    if not ok:
        raise HTTPException(
            status_code=502,
            detail="Could not send the email - is Mailpit running on :1025?",
        )
    return {"ok": True}


# ---------------------------------------------------------------------------
# Alerts - matches P08 AnomalyAlert shape
# ---------------------------------------------------------------------------
@app.get("/api/alerts/active")
async def alerts_active(_: User = Depends(current_active_user)):
    return sensor_service.active_alerts


@app.get("/api/alerts/recent")
async def alerts_recent(
    limit: int = Query(default=20, ge=1, le=100),
    _: User = Depends(current_active_user),
):
    return list(sensor_service.recent_alerts)[:limit]


# ---------------------------------------------------------------------------
# Commands - operator only
# ---------------------------------------------------------------------------
class WaterRequest(BaseModel):
    confirm: bool = False
    action: str = "start"
    duration_s: int = 30


@app.post("/api/commands/water")
async def trigger_water(req: WaterRequest, user: User = Depends(require_operator)):
    if not req.confirm:
        raise HTTPException(
            status_code=400,
            detail="Manual watering requires explicit confirmation (confirm=true)",
        )
    if req.action not in ("start", "stop"):
        raise HTTPException(status_code=400, detail="action must be 'start' or 'stop'")
    if req.action == "start" and not (1 <= req.duration_s <= 3600):
        raise HTTPException(
            status_code=400,
            detail="duration_s must be between 1 and 3600",
        )
    duration = req.duration_s if req.action == "start" else None
    if watering_publisher is None:  # demo / mock mode - no broker
        assert isinstance(sensor_service, MockSensorService)
        result = sensor_service.trigger_watering(req.action, duration)
    else:
        try:
            result = watering_publisher.publish_watering(req.action, duration)
        except RuntimeError as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Watering command could not be sent: {exc}",
            ) from exc
    # Best-effort email notification (fire-and-forget, only sends when
    # EMAIL_ENABLED). Never blocks or fails the command.
    asyncio.create_task(
        send_email(
            "🌱 Plant CPS - watering triggered",
            f"A manual watering command ({req.action}"
            + (f", {duration} s" if duration else "")
            + f") was issued by {user.email}.",
        )
    )
    return {
        "ok": True,
        "triggered_by": user.email,
        "action": req.action,
        "duration_s": duration,
        **result,
    }


class AutoWateringRequest(BaseModel):
    enabled: bool


@app.post("/api/commands/auto-watering")
async def set_auto_watering(
    req: AutoWateringRequest, user: User = Depends(require_operator)
):
    """Enable/disable P05's automatic watering (schema.p05.AutoWateringCommand -
    one of exactly two commands P05 accepts from us over MQTT)."""
    if watering_publisher is None:  # demo / mock mode - no broker
        assert isinstance(sensor_service, MockSensorService)
        result = sensor_service.set_auto_watering(req.enabled)
    else:
        try:
            result = watering_publisher.publish_auto_watering(req.enabled)
        except RuntimeError as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Auto-watering command could not be sent: {exc}",
            ) from exc
    return {"ok": True, "enabled": req.enabled, "set_by": user.email, **result}


class ProfileOverrideRequest(BaseModel):
    key: str
    value: float | bool | None = None
    clear: bool = False


@app.post("/api/config/watering/override")
async def profile_override(
    req: ProfileOverrideRequest, user: User = Depends(require_operator)
):
    """Runtime override of one parameter of P05's active profile
    (schema.p05.ProfileOverrideCommand). In-memory on P05, lost on its
    restart; clear=true reverts the key to the profile's own value.
    Booleans go on the wire as 0.0/1.0."""
    value = req.value
    if isinstance(value, bool):
        value = 1.0 if value else 0.0
    if watering_publisher is None:  # demo / mock mode - no broker
        assert isinstance(sensor_service, MockSensorService)
        try:
            result = sensor_service.set_profile_override(req.key, value, req.clear)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    else:
        from schema.p05 import validate_profile_override

        if not req.clear:
            if value is None:
                raise HTTPException(status_code=400, detail="value is required")
            try:
                validate_profile_override(req.key, value)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        try:
            result = watering_publisher.publish_profile_override(
                req.key, value, req.clear
            )
        except RuntimeError as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Profile override could not be sent: {exc}",
            ) from exc
        except ValueError as exc:  # schema model validation (bad key, range)
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ok": True,
        "key": req.key,
        "value": value,
        "clear": req.clear,
        "set_by": user.email,
        **result,
    }


# ---------------------------------------------------------------------------
# Watering history + plant profile.
# ---------------------------------------------------------------------------
@app.get("/api/watering/history")
async def watering_history(
    limit: int = Query(default=20, ge=1, le=100),
    _: User = Depends(current_active_user),
):
    return sensor_service.get_watering_history(limit)


# The profile catalogue is owned by the web app (see profiles.py). Fixed presets plus one
# editable "custom" profile. On every change the active profile's full value
# set is pushed to P05 as per-key runtime overrides.
_PROFILE_NOTE_REAL = (
    "Presets are fixed; edit the 'custom' profile. Changes are pushed to the "
    "controller as runtime overrides (reset when the controller restarts)."
)
_PROFILE_NOTE_DEMO = (
    "Presets are fixed; edit the 'custom' profile. Demo mode applies changes "
    "locally."
)


@app.get("/api/config/watering")
async def watering_config(_: User = Depends(current_active_user)):
    note = _PROFILE_NOTE_DEMO if watering_publisher is None else _PROFILE_NOTE_REAL
    return profile_store.config(note=note)


class WateringConfigUpdate(BaseModel):
    active: str | None = None
    profiles: dict | None = None


@app.patch("/api/config/watering")
async def update_watering_config(
    req: WateringConfigUpdate, user: User = Depends(require_operator)
):
    try:
        pairs = profile_store.update(active=req.active, profiles=req.profiles)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    published = 0
    if watering_publisher is not None:
        try:
            for key, value in pairs:
                watering_publisher.publish_profile_override(key, value)
                published += 1
        except RuntimeError as exc:
            raise HTTPException(
                status_code=503,
                detail=(
                    f"Profile saved, but only {published}/{len(pairs)} values "
                    f"reached the controller: {exc}"
                ),
            ) from exc
    return {
        "ok": True,
        "updated_by": user.email,
        "active": profile_store.active,
        "published_overrides": published,
    }


# ---------------------------------------------------------------------------
# Static frontend (single-process serving for the monorepo / Pi deployment).
#
# When a built Vue app is present next to this package (a `static/` dir created
# by the monorepo export script), serve it directly and fall back to index.html
# for client-side routes (vue-router runs in history mode).
#
# In standalone dev there is no `static/` dir, so this block is skipped: the
# Vite dev server (port 5173) serves the frontend and proxies /api here.
# ---------------------------------------------------------------------------
_STATIC_DIR = Path(__file__).resolve().parent / "static"

if _STATIC_DIR.is_dir():
    _ASSETS_DIR = _STATIC_DIR / "assets"
    if _ASSETS_DIR.is_dir():
        app.mount("/assets", StaticFiles(directory=_ASSETS_DIR), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        # Never let the SPA catch-all swallow unmatched API routes.
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = _STATIC_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_STATIC_DIR / "index.html")

else:

    @app.get("/")
    async def root():
        return {"service": "Plant CPS Prototype", "docs": "/docs"}
