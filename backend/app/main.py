"""
FastAPI entry point for the Plant CPS prototype.

Run with:  uvicorn app.main:app --reload
Docs at:   http://localhost:8000/docs
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from .auth import (
    User,
    authenticate,
    create_access_token,
    get_current_user,
    require_operator,
)
from .sensors import sensor_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    await sensor_service.start()
    yield
    await sensor_service.stop()


app = FastAPI(
    title="Plant CPS API (Prototype)",
    version="0.2.0",
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
# Auth
# ---------------------------------------------------------------------------
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends()):
    user = authenticate(form.username, form.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(user)
    return TokenResponse(access_token=token, role=user.role)


@app.get("/api/auth/me", response_model=User)
async def me(user: User = Depends(get_current_user)):
    return user


# ---------------------------------------------------------------------------
# Sensors — all authenticated users
# ---------------------------------------------------------------------------
@app.get("/api/sensors/latest")
async def latest(_: User = Depends(get_current_user)):
    return sensor_service.get_latest()


@app.get("/api/sensors/history")
async def history(
    sensor: str,
    max_points: int = 200,
    _: User = Depends(get_current_user),
):
    if sensor not in ("moisture", "temperature", "tank_level"):
        raise HTTPException(status_code=400, detail="Unknown sensor")
    return sensor_service.get_history(sensor, max_points=max_points)


@app.get("/api/system/status")
async def system_status(_: User = Depends(get_current_user)):
    return sensor_service.system_status()


# ---------------------------------------------------------------------------
# Alerts — matches P08 AnomalyAlert shape
# ---------------------------------------------------------------------------
@app.get("/api/alerts/active")
async def alerts_active(_: User = Depends(get_current_user)):
    return sensor_service.active_alerts


@app.get("/api/alerts/recent")
async def alerts_recent(
    limit: int = Query(default=20, ge=1, le=100),
    _: User = Depends(get_current_user),
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
    return {"ok": True, "triggered_by": user.username, "duration_s": req.duration_s}


@app.get("/")
async def root():
    return {"service": "Plant CPS Prototype", "docs": "/docs"}
