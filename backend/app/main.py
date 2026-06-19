"""
FastAPI entry point for the Plant CPS prototype.

Run with:  uv run uvicorn app.main:app --reload
Docs at:   http://localhost:8000/docs
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .auth import (
    auth_backend,
    current_active_user,
    fastapi_users,
    init_db,
    require_operator,
)
from .models import User
from .schemas import UserCreate, UserRead, UserUpdate
from .sensors import sensor_service
from .alerts import alert_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await sensor_service.start()
    await alert_service.start()
    yield
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
    return sensor_service.get_history(sensor, max_points=max_points)


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
    duration_s: int = 30


@app.post("/api/commands/water")
async def trigger_water(
    req: WaterRequest, user: User = Depends(require_operator)
):
    if not req.confirm:
        raise HTTPException(
            status_code=400,
            detail="Manual watering requires explicit confirmation (confirm=true)",
        )
    if req.duration_s < 1 or req.duration_s > 3600:
        raise HTTPException(
            status_code=400,
            detail="duration_s must be between 1 and 3600",
        )
    sensor_service.trigger_watering()
    return {"ok": True, "triggered_by": user.email, "duration_s": req.duration_s}


@app.get("/")
async def root():
    return {"service": "Plant CPS Prototype", "docs": "/docs"}
