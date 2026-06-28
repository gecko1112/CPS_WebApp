"""
FastAPI entry point for the Plant CPS prototype.

Run with:  uv run uvicorn app.main:app --reload
Docs at:   http://localhost:8000/docs
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .alerts import alert_service
from .auth import (
    auth_backend,
    current_active_user,
    fastapi_users,
    init_db,
    require_operator,
)
from .models import User
from .mqtt_publisher import watering_publisher
from .schemas import UserCreate, UserRead, UserUpdate
from .sensors import sensor_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await sensor_service.start()
    await alert_service.start()
    watering_publisher.start()
    yield
    watering_publisher.stop()
    await sensor_service.stop()
    await alert_service.stop()


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
# Sensors — all authenticated users
# ---------------------------------------------------------------------------
@app.get("/api/sensors/latest")
async def latest(_: User = Depends(current_active_user)):
    return sensor_service.get_latest()


@app.get("/api/sensors/history")
async def history(
    sensor: str,
    max_points: int = 200,
    _: User = Depends(current_active_user),
):
    if sensor not in ("moisture", "temperature", "tank_level"):
        raise HTTPException(status_code=400, detail="Unknown sensor")
    return await sensor_service.get_history(sensor, max_points=max_points)


@app.get("/api/system/status")
async def system_status(_: User = Depends(current_active_user)):
    return sensor_service.system_status()


# ---------------------------------------------------------------------------
# Alerts — matches P08 AnomalyAlert shape
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
# Commands — operator only
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
    try:
        result = watering_publisher.publish_watering(req.action, duration)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Watering command could not be sent: {exc}",
        ) from exc
    return {
        "ok": True,
        "triggered_by": user.email,
        "action": req.action,
        "duration_s": duration,
        **result,
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
