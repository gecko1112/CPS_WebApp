"""
FastAPI entry point for the Plant CPS prototype.

Run with:  uvicorn app.main:app --reload
Docs at:   http://localhost:8000/docs
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
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
    # Startup: kick off the fake sensor generator
    await sensor_service.start()
    yield
    # Shutdown: stop the background task cleanly
    await sensor_service.stop()


app = FastAPI(
    title="Plant CPS API (Prototype)",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow the Vite dev server to talk to us during development.
# In production, lock this down to the actual frontend origin.
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
# Sensors (read-only — any authenticated user)
# ---------------------------------------------------------------------------
@app.get("/api/sensors/latest")
async def latest(_: User = Depends(get_current_user)):
    return sensor_service.latest


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
# Commands (operator only)
# ---------------------------------------------------------------------------
class WaterRequest(BaseModel):
    confirm: bool = False


@app.post("/api/commands/water")
async def trigger_water(
    req: WaterRequest, user: User = Depends(require_operator)
):
    if not req.confirm:
        raise HTTPException(
            status_code=400,
            detail="Manual watering requires explicit confirmation (confirm=true)",
        )
    sensor_service.trigger_watering()
    # In the real system: publish to MQTT topic commands/water/<plant_id>
    return {"ok": True, "triggered_by": user.username}


@app.get("/")
async def root():
    return {"service": "Plant CPS Prototype", "docs": "/docs"}
