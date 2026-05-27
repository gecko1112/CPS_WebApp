"""
FakeSensorService — generates plausible sensor readings for development.

Data shapes match the real Sparkplug B schema models from the monorepo
(schema.p01, schema.p05, schema.p07, schema.p08, schema.p11, schema.p12)
so the REST API responses won't change when we swap in real MQTT.
"""
from __future__ import annotations

import asyncio
import math
import random
from collections import deque
from datetime import datetime, timezone
from typing import Deque


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# Alert templates matching P08 AnomalyAlert shape
_ALERT_TEMPLATES = [
    {
        "component": "p01/soil_moisture",
        "alert_type": "sensor_fault",
        "severity": "warning",
        "observed_value": "0.01",
        "description": "Soil moisture reading near zero — possible sensor disconnection or dry-air exposure",
    },
    {
        "component": "p01/soil_moisture",
        "alert_type": "process_fault",
        "severity": "warning",
        "observed_value": "0.42",
        "description": "Soil moisture unchanged after watering completed — check water delivery path",
    },
    {
        "component": "p02/pump",
        "alert_type": "sensor_fault",
        "severity": "critical",
        "observed_value": "running_for_120s",
        "description": "Pump running longer than commanded duration — possible valve or relay stuck open",
    },
    {
        "component": "p11/tank_level",
        "alert_type": "sensor_fault",
        "severity": "warning",
        "observed_value": "105.3",
        "description": "Tank level sensor reading exceeds 100% — recalibration needed",
    },
    {
        "component": "p05/controller",
        "alert_type": "system_fault",
        "severity": "critical",
        "observed_value": "silent_for_30s",
        "description": "Watering controller missed heartbeat — node may be offline",
    },
]


class FakeSensorService:
    def __init__(self, history_size: int = 2880):
        # --- P01: Soil Moisture (calibrated 0.0–1.0) ---
        self.soil_moisture = {
            "calibrated": 0.45,
            "raw_adc": 1847,
            "status": "ok",
            "timestamp": _now(),
        }

        # --- P05: Controller State ---
        self.controller = {
            "state": "idle",
            "reason": None,
            "timestamp": _now(),
        }

        # --- P07: Weather Forecast ---
        self.weather = {
            "rainfall_mm": 2.5,
            "temperature_c": 22.0,
            "horizon_label": "+24h",
            "evapotranspiration_mm_day": None,
            "staleness_hours": None,
            "confidence": 0.85,
            "status": "fresh",
            "timestamp": _now(),
        }

        # --- P11: Tank Level ---
        self.tank = {
            "level_pct": 78.0,
            "volume_l": 15.6,
            "sensor_distance_mm": 120.0,
            "status": "ok",
            "timestamp": _now(),
        }
        self.tank_forecast = {
            "time_to_empty_h": 72.0,
            "confidence_h": 6.0,
            "status": "ok",
            "timestamp": _now(),
        }

        # --- P12: Power / Battery ---
        self.power = {
            "battery_soc": 85.0,
            "charging_rate_w": 12.5,
            "time_to_discharge_h": 48.0,
            "mode": "normal",
            "status": "ok",
            "timestamp": _now(),
        }

        # --- P08: Anomaly Alerts ---
        self.active_alerts: list[dict] = []
        self.recent_alerts: deque[dict] = deque(maxlen=50)

        # --- History ring buffers ---
        self.history: dict[str, Deque[dict]] = {
            "moisture": deque(maxlen=history_size),
            "temperature": deque(maxlen=history_size),
            "tank_level": deque(maxlen=history_size),
        }

        self.last_watered_at: datetime | None = None
        self._task: asyncio.Task | None = None
        self._tick = 0

    async def start(self):
        self._task = asyncio.create_task(self._generate_loop())

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _generate_loop(self):
        while True:
            self._tick += 1
            now = _now()

            # --- Soil moisture drift ---
            drift = -0.001 + random.uniform(-0.002, 0.002)
            cal = max(0.05, min(0.95, self.soil_moisture["calibrated"] + drift))
            self.soil_moisture.update({
                "calibrated": round(cal, 4),
                "raw_adc": int(cal * 4095),
                "status": "ok",
                "timestamp": now,
            })

            # --- Controller state ---
            self.controller["timestamp"] = now

            # --- Weather: slow drift, update every ~60 ticks ---
            if self._tick % 60 == 0:
                self.weather.update({
                    "rainfall_mm": round(random.uniform(0.0, 8.0), 1),
                    "temperature_c": round(18.0 + random.uniform(-3.0, 8.0), 1),
                    "confidence": round(random.uniform(0.6, 0.95), 2),
                    "status": "fresh",
                    "timestamp": now,
                })

            # --- Tank level: slowly decreases ---
            lvl = max(0.0, self.tank["level_pct"] - random.uniform(0.0, 0.03))
            self.tank.update({
                "level_pct": round(lvl, 2),
                "volume_l": round(lvl * 0.2, 2),
                "sensor_distance_mm": round(300.0 - lvl * 2.5, 1),
                "status": "ok",
                "timestamp": now,
            })
            tte = lvl * 1.5 if lvl > 0 else 0.0
            self.tank_forecast.update({
                "time_to_empty_h": round(tte, 1),
                "confidence_h": round(tte * 0.1, 1) if tte > 0 else None,
                "status": "ok",
                "timestamp": now,
            })

            # --- Power: sinusoidal charging ---
            charge = 10.0 + 8.0 * max(0, math.sin(self._tick / 200.0))
            soc = min(100.0, max(0.0, self.power["battery_soc"] + random.uniform(-0.1, 0.15)))
            self.power.update({
                "battery_soc": round(soc, 1),
                "charging_rate_w": round(charge, 1),
                "time_to_discharge_h": round(soc * 0.8, 1),
                "mode": "normal" if soc > 30 else ("low_power" if soc > 10 else "critical"),
                "status": "ok",
                "timestamp": now,
            })

            # --- Fake alerts: ~5% chance per tick to fire one ---
            if random.random() < 0.05 and len(self.active_alerts) < 3:
                template = random.choice(_ALERT_TEMPLATES)
                alert = {**template, "timestamp": now}
                self.active_alerts.append(alert)
                self.recent_alerts.appendleft(alert)

            # Clear oldest active alert after a while
            if self._tick % 30 == 0 and self.active_alerts:
                self.active_alerts.pop(0)

            # --- History ---
            self.history["moisture"].append(
                {"t": now, "v": round(cal * 100, 2)}
            )
            self.history["temperature"].append(
                {"t": now, "v": round(self.weather["temperature_c"], 2)}
            )
            self.history["tank_level"].append(
                {"t": now, "v": round(lvl, 2)}
            )

            await asyncio.sleep(2.0)

    def trigger_watering(self):
        cal = min(0.95, self.soil_moisture["calibrated"] + 0.25)
        self.soil_moisture.update({
            "calibrated": round(cal, 4),
            "raw_adc": int(cal * 4095),
        })
        self.tank["level_pct"] = max(0.0, self.tank["level_pct"] - 2.0)
        self.last_watered_at = datetime.now(timezone.utc)
        self.controller.update({
            "state": "watering",
            "reason": "manual_trigger",
            "timestamp": _now(),
        })

    def get_latest(self) -> dict:
        return {
            "soil_moisture": {**self.soil_moisture},
            "controller": {**self.controller},
            "weather": {**self.weather},
            "tank": {**self.tank},
            "tank_forecast": {**self.tank_forecast},
            "power": {**self.power},
        }

    def get_history(self, sensor: str, max_points: int = 200) -> list[dict]:
        if sensor not in self.history:
            return []
        full = list(self.history[sensor])
        if len(full) <= max_points:
            return full
        step = len(full) / max_points
        return [full[int(i * step)] for i in range(max_points)]

    def system_status(self) -> dict:
        cal = self.soil_moisture["calibrated"]
        tank = self.tank["level_pct"]
        ctrl = self.controller["state"]
        n_alerts = len(self.active_alerts)

        if ctrl == "error":
            level, message = "error", "Controller in error state"
        elif n_alerts > 0 and any(a["severity"] == "critical" for a in self.active_alerts):
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
        }


sensor_service = FakeSensorService()
