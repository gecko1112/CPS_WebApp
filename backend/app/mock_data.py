"""
MockSensorService — self-contained demo data source.

Enabled with ``MOCK_DATA=true``. It mirrors the public interface of
``P06SensorService`` (get_latest / get_history / system_status / active_alerts /
recent_alerts / start / stop) plus ``trigger_watering`` for the watering button,
but generates plausible moving data and rotating anomaly alerts instead of
reading from P06.

Deliberately has NO dependency on ``cps-schema``, MQTT, P06, or any other group,
so the dashboard can be live-demoed standalone — even when the real data sources
are down or the shared schema is broken. The JSON shapes are identical to the
real service, so the frontend is unchanged.
"""

from __future__ import annotations

import asyncio
import math
import random
from collections import deque
from datetime import UTC, datetime, timedelta
from typing import TypedDict

from .alert_email import notify_critical_alerts
from .components import COMPONENTS
from .weather_util import weather_condition


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


class SoilMoistureState(TypedDict):
    calibrated: float
    raw_adc: int
    status: str
    timestamp: str


class ControllerState(TypedDict):
    state: str
    reason: str | None
    timestamp: str


class WeatherState(TypedDict):
    condition: str
    temperature_c: float
    precipitation_mm: float
    solar_radiation_wm2: float
    horizon_label: str
    confidence: float
    status: str
    timestamp: str


class TankState(TypedDict):
    level_pct: float
    volume_l: float
    sensor_distance_mm: float
    status: str
    timestamp: str


class TankForecastState(TypedDict):
    time_to_empty_h: float
    confidence_h: float | None
    status: str
    timestamp: str


class PowerState(TypedDict):
    battery_soc: float
    charging_rate_w: float
    time_to_discharge_h: float
    mode: str
    status: str
    timestamp: str


# (precipitation_mm, solar_radiation_wm2) pairs the demo rotates through so the
# weather icon visibly changes: sunny, partly cloudy, cloudy, light rain, rainy,
# stormy.
_WEATHER_SCENARIOS = [
    (0.0, 820.0),
    (0.0, 320.0),
    (0.0, 90.0),
    (0.6, 160.0),
    (4.0, 70.0),
    (12.0, 40.0),
]


# Plant watering profiles (mirrors P05's profiles/*.json: target_moist 0–1,
# dry_days = min days between waterings, suppress_daytime = water at night only).
_PLANT_PROFILES = {
    "tomato": {"target_moist": 0.45, "dry_days": 2, "suppress_daytime": True},
    "cactus": {"target_moist": 0.15, "dry_days": 10, "suppress_daytime": False},
    "herbs": {"target_moist": 0.55, "dry_days": 1, "suppress_daytime": True},
}


# Demo alert story (P08 AnomalyAlert shape): the system starts healthy, then
# exactly ONE warning and later ONE critical appear — no rotation, so the
# demo (and the Mailpit inbox) never floods.
_WARNING_ALERT = {
    "component": "p11/tank_level",
    "alert_type": "sensor_fault",
    "severity": "warning",
    "observed_value": "105.3",
    "description": "Tank level sensor reading exceeds 100% — recalibration needed.",
}

_CRITICAL_ALERT = {
    "component": "p02/pump",
    "alert_type": "process_fault",
    "severity": "critical",
    "observed_value": "no_flow",
    "description": "The pump ran but no water arrived at the plant — the pump "
    "inlet may be blocked or the tank hose disconnected.",
}


class MockSensorService:
    def __init__(self, history_size: int = 20000) -> None:
        self.soil_moisture: SoilMoistureState = {
            "calibrated": 0.45,
            "raw_adc": 1847,
            "status": "ok",
            "timestamp": _now(),
        }
        self.controller: ControllerState = {
            "state": "idle",
            "reason": None,
            "timestamp": _now(),
        }
        self.weather: WeatherState = {
            "condition": weather_condition(0.6, 160.0),
            "temperature_c": 22.0,
            "precipitation_mm": 0.6,
            "solar_radiation_wm2": 160.0,
            "horizon_label": "next 24h",
            "confidence": 0.85,
            "status": "live",
            "timestamp": _now(),
        }
        self.tank: TankState = {
            "level_pct": 78.0,
            "volume_l": 15.6,
            "sensor_distance_mm": 120.0,
            "status": "ok",
            "timestamp": _now(),
        }
        self.tank_forecast: TankForecastState = {
            "time_to_empty_h": 72.0,
            "confidence_h": 6.0,
            "status": "ok",
            "timestamp": _now(),
        }
        self.power: PowerState = {
            "battery_soc": 85.0,
            "charging_rate_w": 12.5,
            "time_to_discharge_h": 48.0,
            "mode": "normal",
            "status": "ok",
            "timestamp": _now(),
        }

        # Start with no alerts: the demo opens on "All systems normal" and the
        # warning/critical arrive later (see _generate_loop).
        self.active_alerts: list[dict] = []
        self.recent_alerts: deque[dict] = deque(maxlen=50)

        self.history: dict[str, deque[dict]] = {
            "moisture": deque(maxlen=history_size),
            "temperature": deque(maxlen=history_size),
            "tank_level": deque(maxlen=history_size),
        }
        self._seed_history()
        self.last_watered_at: datetime | None = None
        self._task: asyncio.Task | None = None
        self._tick = 0
        self._offline_component: str | None = None  # one component "drops" now and then

        # Plant profile (owned by P05; we only display + forward edits). In demo
        # mode we keep an editable in-memory copy so the UI is fully functional.
        self.active_profile = "tomato"
        self.profiles = {name: dict(v) for name, v in _PLANT_PROFILES.items()}
        now = datetime.now(tz=UTC)
        self.watering_events: deque[dict] = deque(
            [
                {
                    "timestamp": (now - timedelta(hours=h)).isoformat(),
                    "duration_s": dur,
                    "trigger": trig,
                    "moisture_before": mb,
                    "moisture_after": ma,
                }
                for h, dur, trig, mb, ma in (
                    (6, 30, "auto", 0.31, 0.56),
                    (18, 25, "auto", 0.29, 0.52),
                    (30, 45, "manual", 0.22, 0.61),
                )
            ],
            maxlen=50,
        )

    def _seed_history(self) -> None:
        """Backfill ~24 h of history (5-min steps) so the time-range selector
        (1h / 12h / 24h) has data from the very start of a demo."""
        now = datetime.now(tz=UTC)
        for i in range(288, 0, -1):  # 288 * 5 min = 24 h
            t = (now - timedelta(minutes=5 * i)).isoformat()
            moist = 45 + 12 * math.sin(i / 22) + random.uniform(-3, 3)
            temp = 22 + 4 * math.sin(i / 34) + random.uniform(-1, 1)
            tank = 80 - (288 - i) * 0.02
            self.history["moisture"].append(
                {"t": t, "v": round(max(5, min(95, moist)), 2)}
            )
            self.history["temperature"].append({"t": t, "v": round(temp, 2)})
            self.history["tank_level"].append({"t": t, "v": round(max(0, tank), 2)})

    # -- lifecycle ----------------------------------------------------------

    async def start(self) -> None:
        self._task = asyncio.create_task(self._generate_loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _generate_loop(self) -> None:
        while True:
            self._tick += 1
            now = _now()

            drift = -0.001 + random.uniform(-0.002, 0.002)
            cal = max(0.05, min(0.95, self.soil_moisture["calibrated"] + drift))
            self.soil_moisture.update(
                {
                    "calibrated": round(cal, 4),
                    "raw_adc": int(cal * 4095),
                    "status": "ok",
                    "timestamp": now,
                }
            )

            # Controller returns to idle a while after a manual watering.
            if self.controller["state"] == "watering" and self._tick % 10 == 0:
                self.controller.update(
                    {"state": "idle", "reason": None, "timestamp": now}
                )
            else:
                self.controller["timestamp"] = now

            if self._tick % 30 == 0:
                precip, solar = random.choice(_WEATHER_SCENARIOS)
                self.weather.update(
                    {
                        "condition": weather_condition(precip, solar),
                        "temperature_c": round(18.0 + random.uniform(-3.0, 8.0), 1),
                        "precipitation_mm": round(precip, 1),
                        "solar_radiation_wm2": round(solar, 0),
                        "confidence": round(random.uniform(0.6, 0.95), 2),
                        "status": "live",
                        "timestamp": now,
                    }
                )

            lvl = max(0.0, self.tank["level_pct"] - random.uniform(0.0, 0.03))
            self.tank.update(
                {
                    "level_pct": round(lvl, 2),
                    "volume_l": round(lvl * 0.2, 2),
                    "sensor_distance_mm": round(300.0 - lvl * 2.5, 1),
                    "status": "ok",
                    "timestamp": now,
                }
            )
            tte = lvl * 1.5 if lvl > 0 else 0.0
            self.tank_forecast.update(
                {
                    "time_to_empty_h": round(tte, 1),
                    "confidence_h": round(tte * 0.1, 1) if tte > 0 else None,
                    "status": "ok",
                    "timestamp": now,
                }
            )

            charge = 10.0 + 8.0 * max(0, math.sin(self._tick / 200.0))
            soc = min(
                100.0, max(0.0, self.power["battery_soc"] + random.uniform(-0.1, 0.15))
            )
            self.power.update(
                {
                    "battery_soc": round(soc, 1),
                    "charging_rate_w": round(charge, 1),
                    "time_to_discharge_h": round(soc * 0.8, 1),
                    "mode": "normal"
                    if soc > 30
                    else ("low_power" if soc > 10 else "critical"),
                    "status": "ok",
                    "timestamp": now,
                }
            )

            # Alert story: one warning ~40 s in, one critical ~2 min in (the
            # critical also goes out by email, best-effort). Nothing repeats.
            if self._tick == 20:
                alert = {**_WARNING_ALERT, "timestamp": now}
                self.active_alerts.append(alert)
                self.recent_alerts.appendleft(alert)
            elif self._tick == 60:
                alert = {**_CRITICAL_ALERT, "timestamp": now}
                self.active_alerts.append(alert)
                self.recent_alerts.appendleft(alert)
                notify_critical_alerts([alert])

            # Occasionally drop one component offline (then restore it) so the
            # component-health strip visibly changes during a demo.
            if self._tick % 45 == 0:
                self._offline_component = (
                    None
                    if self._offline_component
                    else random.choice(["p07", "p08", "p11", "p12"])
                )

            self.history["moisture"].append({"t": now, "v": round(cal * 100, 2)})
            self.history["temperature"].append(
                {"t": now, "v": round(self.weather["temperature_c"], 2)}
            )
            self.history["tank_level"].append({"t": now, "v": round(lvl, 2)})

            await asyncio.sleep(2.0)

    # -- write path (demo: optimistic local update, no MQTT) ----------------

    def trigger_watering(
        self, action: str = "start", duration_s: int | None = 30
    ) -> dict:
        if action == "start":
            cal = min(0.95, self.soil_moisture["calibrated"] + 0.25)
            self.soil_moisture.update(
                {"calibrated": round(cal, 4), "raw_adc": int(cal * 4095)}
            )
            self.tank["level_pct"] = max(0.0, self.tank["level_pct"] - 2.0)
            self.last_watered_at = datetime.now(tz=UTC)
            self.controller.update(
                {"state": "watering", "reason": "manual_trigger", "timestamp": _now()}
            )
            self.watering_events.appendleft(
                {
                    "timestamp": self.last_watered_at.isoformat(),
                    "duration_s": duration_s or 30,
                    "trigger": "manual",
                    "moisture_before": round(cal - 0.25, 4),
                    "moisture_after": round(cal, 4),
                }
            )
        else:
            self.controller.update(
                {"state": "idle", "reason": "manual_stop", "timestamp": _now()}
            )
        return {"topic": "mock://p05/manual_trigger", "seq": self._tick}

    # -- watering history + plant profile -----------------------------------

    def get_component_health(self) -> list[dict]:
        now = _now()
        return [
            {
                "id": cid,
                "label": label,
                "online": cid != self._offline_component,
                "last_seen": None if cid == self._offline_component else now,
            }
            for cid, label in COMPONENTS
        ]

    def get_watering_history(self, limit: int = 20) -> list[dict]:
        return list(self.watering_events)[:limit]

    def get_watering_config(self) -> dict:
        return {
            "active": self.active_profile,
            "profiles": self.profiles,
            "editable": True,
        }

    def update_watering_config(
        self, active: str | None = None, profiles: dict | None = None
    ) -> dict:
        # In real mode this would publish to P05; in demo mode we just apply it
        # locally so operators can see selection + value edits take effect.
        if profiles is not None:
            self.profiles = profiles
        if active is not None:
            if active not in self.profiles:
                raise ValueError(f"unknown profile '{active}'")
            self.active_profile = active
        return self.get_watering_config()

    # -- read API (identical shapes to P06SensorService) --------------------

    def get_latest(self) -> dict:
        return {
            "soil_moisture": {**self.soil_moisture},
            "controller": {**self.controller},
            "weather": {**self.weather},
            "tank": {**self.tank},
            "tank_forecast": {**self.tank_forecast},
            "power": {**self.power},
        }

    async def get_history(
        self, sensor: str, max_points: int = 200, hours: int = 24
    ) -> list[dict]:
        if sensor not in self.history:
            return []
        cutoff = (datetime.now(tz=UTC) - timedelta(hours=hours)).isoformat()
        full = [p for p in self.history[sensor] if p["t"] >= cutoff]
        if len(full) <= max_points:
            return full
        step = len(full) / max_points
        return [full[int(i * step)] for i in range(max_points)]

    def system_status(self) -> dict:
        cal = self.soil_moisture["calibrated"]
        tank = self.tank["level_pct"]
        ctrl = self.controller["state"]
        n_alerts = len(self.active_alerts)
        has_critical = any(a.get("severity") == "critical" for a in self.active_alerts)

        if ctrl == "error":
            level, message = "error", "Controller in error state"
        elif has_critical:
            level, message = "error", "Critical alert active"
        elif tank < 10:
            level, message = "error", "Water tank almost empty"
        elif cal < 0.20:
            level, message = "warning", "Soil is dry — watering soon"
        elif tank < 25:
            level, message = "warning", "Tank level getting low"
        elif n_alerts > 0:
            level, message = "warning", f"{n_alerts} alert(s) active"
        else:
            level, message = "ok", "All systems normal"

        return {
            "level": level,
            "message": message,
            "controller_state": ctrl,
            "last_watered_at": (
                self.last_watered_at.isoformat() if self.last_watered_at else None
            ),
            "active_alert_count": n_alerts,
            # Plant health headline pinned to "healthy" in demo mode (P16 is
            # vacant — placeholder per the presentation plan). The status
            # banner still reacts to the demo alerts; the plant itself is fine.
            "plant_health": "healthy",
            "demo_mode": True,
        }


mock_service = MockSensorService()
