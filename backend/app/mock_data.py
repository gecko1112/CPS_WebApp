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
from datetime import UTC, datetime


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


# Rotating anomaly alerts (P08 AnomalyAlert shape) shown during the demo.
_ALERT_TEMPLATES = [
    {
        "component": "p01/soil_moisture",
        "alert_type": "process_fault",
        "severity": "warning",
        "observed_value": "0.42",
        "description": "Soil moisture unchanged after watering completed — "
        "check the water delivery path.",
    },
    {
        "component": "p11/tank_level",
        "alert_type": "sensor_fault",
        "severity": "warning",
        "observed_value": "105.3",
        "description": "Tank level sensor reading exceeds 100% — recalibration needed.",
    },
    {
        "component": "p05/controller",
        "alert_type": "system_fault",
        "severity": "critical",
        "observed_value": "silent_for_30s",
        "description": "Watering controller missed its heartbeat — the node may "
        "be offline.",
    },
]


class MockSensorService:
    def __init__(self, history_size: int = 2880) -> None:
        self.soil_moisture = {
            "calibrated": 0.45,
            "raw_adc": 1847,
            "status": "ok",
            "timestamp": _now(),
        }
        self.controller = {"state": "idle", "reason": None, "timestamp": _now()}
        self.weather = {
            "rainfall_mm": 2.5,
            "temperature_c": 22.0,
            "horizon_label": "+24h",
            "confidence": 0.85,
            "status": "live",
            "timestamp": _now(),
        }
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
        self.power = {
            "battery_soc": 85.0,
            "charging_rate_w": 12.5,
            "time_to_discharge_h": 48.0,
            "mode": "normal",
            "status": "ok",
            "timestamp": _now(),
        }

        # Seed one active alert so the alert panel is populated on demo open.
        first = {**_ALERT_TEMPLATES[0], "timestamp": _now()}
        self.active_alerts: list[dict] = [first]
        self.recent_alerts: deque[dict] = deque([first], maxlen=50)

        self.history: dict[str, deque[dict]] = {
            "moisture": deque(maxlen=history_size),
            "temperature": deque(maxlen=history_size),
            "tank_level": deque(maxlen=history_size),
        }
        self.last_watered_at: datetime | None = None
        self._task: asyncio.Task | None = None
        self._tick = 0

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

            if self._tick % 60 == 0:
                self.weather.update(
                    {
                        "rainfall_mm": round(random.uniform(0.0, 8.0), 1),
                        "temperature_c": round(18.0 + random.uniform(-3.0, 8.0), 1),
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

            # Rotate alerts so the panel stays lively during a demo.
            if self._tick % 25 == 0:
                if self.active_alerts:
                    self.active_alerts.pop(0)
                else:
                    alert = {**random.choice(_ALERT_TEMPLATES), "timestamp": now}
                    self.active_alerts.append(alert)
                    self.recent_alerts.appendleft(alert)

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
        else:
            self.controller.update(
                {"state": "idle", "reason": "manual_stop", "timestamp": _now()}
            )
        return {"topic": "mock://p05/manual_trigger", "seq": self._tick}

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

    async def get_history(self, sensor: str, max_points: int = 200) -> list[dict]:
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
            "demo_mode": True,
        }


mock_service = MockSensorService()
