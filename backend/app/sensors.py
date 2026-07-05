"""
P06SensorService — feeds the dashboard from P06's query API.

Replaces the old FakeSensorService. It polls P06 on a fixed interval and caches
the latest reading per topic in the exact JSON shapes the REST API already
served, so the frontend is unchanged. History is fetched from P06 on demand.

Topic + metric names come from the canonical ``cps-schema`` package — never
hardcoded — so an upstream rename breaks at import (fail fast).

The manual-watering command is a separate WRITE path (MQTT to P05) and lives in
``mqtt_publisher.py`` — this service is read-only.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections import deque
from datetime import UTC, datetime, timedelta

import schema.p01 as p01
import schema.p03 as p03
import schema.p05 as p05
import schema.p07 as p07
import schema.p08 as p08
import schema.p11 as p11
import schema.p12 as p12

from .components import COMPONENTS, is_fresh
from .p06_client import P06Client, group_events, latest_values, metric_series
from .weather_util import weather_condition

log = logging.getLogger("p13.sensors")

POLL_INTERVAL_S = float(os.getenv("POLL_INTERVAL_S", "10"))
ACTIVE_ALERT_WINDOW_MIN = float(os.getenv("ACTIVE_ALERT_WINDOW_MIN", "10"))
COMPONENT_FRESH_WINDOW_S = float(os.getenv("COMPONENT_FRESH_WINDOW_S", "90"))

# Sensors exposed by /api/sensors/history -> (topic, measurement, value scale).
# Soil is scaled 0–1 -> 0–100 % to match the previous chart units.
_HISTORY_SOURCES: dict[str, tuple[str, str, float]] = {
    "moisture": (
        p01.SoilReadingTopic.address,
        p01.SoilMoistureReading.METRIC_CALIBRATED,
        100.0,
    ),
    "tank_level": (p11.LevelTopic.address, p11.TankLevelReading.METRIC_LEVEL_PCT, 1.0),
    "temperature": (
        p03.BME280Topic.address,
        p03.EnvironmentBME280.METRIC_TEMPERATURE_C,
        1.0,
    ),
}


def _num(value: object) -> float | None:
    return value if isinstance(value, (int, float)) else None


class P06SensorService:
    def __init__(self) -> None:
        # Latest-reading cache. Same keys the frontend already consumes;
        # initialised to "no data yet" until the first successful poll.
        self.soil_moisture = {
            "calibrated": None,
            "raw_adc": None,
            "status": "unavailable",
            "timestamp": None,
        }
        self.controller = {"state": "unknown", "reason": None, "timestamp": None}
        self.weather = {
            "condition": "unknown",
            "temperature_c": None,
            "precipitation_mm": None,
            "solar_radiation_wm2": None,
            "horizon_label": "next 24h",
            "confidence": None,
            "status": "unavailable",
            "timestamp": None,
        }
        self.tank = {
            "level_pct": None,
            "volume_l": None,
            "sensor_distance_mm": None,
            "status": "unavailable",
            "timestamp": None,
        }
        self.tank_forecast = {
            "time_to_empty_h": None,
            "confidence_h": None,
            "status": "unavailable",
            "timestamp": None,
        }
        self.power = {
            "battery_soc": None,
            "charging_rate_w": None,
            "time_to_discharge_h": None,
            "mode": "unknown",
            "status": "unavailable",
            "timestamp": None,
        }

        self.active_alerts: list[dict] = []
        self.recent_alerts: deque[dict] = deque(maxlen=50)

        self.last_watered_at: datetime | None = None
        self._connected = False
        self._client: P06Client | None = None
        self._task: asyncio.Task | None = None

    # -- lifecycle ----------------------------------------------------------

    async def start(self) -> None:
        self._client = P06Client()
        self._task = asyncio.create_task(self._poll_loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._client:
            await self._client.aclose()

    async def _poll_loop(self) -> None:
        while True:
            try:
                await self._poll_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 — never kill the loop
                self._connected = False
                log.warning("P06 poll cycle failed: %s", exc)
            await asyncio.sleep(POLL_INTERVAL_S)

    async def _poll_once(self) -> None:
        assert self._client is not None
        c = self._client
        # Fetch P06 health + all latest windows + the alert log concurrently.
        # window()/history() swallow errors and return [], so connectivity is
        # judged from /health, not from whether a cycle raised.
        (
            health,
            soil,
            ctrl,
            tank,
            forecast,
            power,
            weather,
            anomalies,
        ) = await asyncio.gather(
            c.health(),
            c.window(p01.SoilReadingTopic.address),
            c.window(p05.ControllerStateTopic.address),
            c.window(p11.LevelTopic.address),
            c.window(p11.ForecastTopic.address),
            c.window(p12.PowerReadingTopic.address),
            c.window(p07.ForecastTopic.address, start="-6h"),  # 2 h cadence
            c.history(p08.AnomalyAlertTopic.address, hours=24, downsample=None),
        )
        self._connected = bool(health)

        self._apply_soil(latest_values(soil))
        self._apply_controller(latest_values(ctrl))
        self._apply_tank(latest_values(tank))
        self._apply_tank_forecast(latest_values(forecast))
        self._apply_power(latest_values(power))
        self._apply_weather(latest_values(weather))
        self._apply_alerts(group_events(anomalies))

    # -- latest-reading mappers (only overwrite when P06 returned data) -----

    def _apply_soil(self, v: dict) -> None:
        if not v.get("timestamp"):
            return
        self.soil_moisture = {
            "calibrated": _num(v.get("calibrated")),
            "raw_adc": v.get("raw_adc"),
            "status": v.get("status", "ok"),
            "timestamp": v.get("timestamp"),
        }

    def _apply_controller(self, v: dict) -> None:
        if not v.get("timestamp"):
            return
        state = v.get("state", "unknown")
        self.controller = {
            "state": state,
            "reason": None,
            "timestamp": v.get("timestamp"),
        }
        # Approximate "last watered" from the controller heartbeat.
        if state in ("watering", "soaking"):
            self.last_watered_at = datetime.now(UTC)

    def _apply_tank(self, v: dict) -> None:
        if not v.get("timestamp"):
            return
        self.tank = {
            "level_pct": _num(v.get("level_pct")),
            "volume_l": _num(v.get("volume_l")),
            "sensor_distance_mm": _num(v.get("sensor_distance_mm")),
            "status": v.get("status", "ok"),
            "timestamp": v.get("timestamp"),
        }

    def _apply_tank_forecast(self, v: dict) -> None:
        if not v.get("timestamp"):
            return
        self.tank_forecast = {
            "time_to_empty_h": _num(v.get("time_to_empty_h")),
            "confidence_h": _num(v.get("confidence_h")),
            "status": v.get("status", "ok"),
            "timestamp": v.get("timestamp"),
        }

    def _apply_power(self, v: dict) -> None:
        if not v.get("timestamp"):
            return
        self.power = {
            "battery_soc": _num(v.get("battery_soc")),
            "charging_rate_w": _num(v.get("charging_rate_w")),
            "time_to_discharge_h": _num(v.get("time_to_discharge_h")),
            "mode": v.get("mode", "unknown"),
            "status": v.get("status", "ok"),
            "timestamp": v.get("timestamp"),
        }

    def _apply_weather(self, v: dict) -> None:
        """P07 ships the useful numbers inside a JSON-encoded ``forecast_hours``
        metric (stored as a string by P06). Parse it best-effort."""
        if not v.get("timestamp"):
            return
        temperature_c: float | None = None
        precipitation_mm: float | None = None
        solar_radiation_wm2: float | None = None
        raw_hours = v.get("forecast_hours")
        if isinstance(raw_hours, str):
            try:
                hours = json.loads(raw_hours)
                if hours:
                    window = hours[:24]
                    temperature_c = _num(window[0].get("temperature_c"))
                    precipitation_mm = round(
                        sum(float(h.get("precipitation_mm", 0) or 0) for h in window),
                        1,
                    )
                    solar_radiation_wm2 = max(
                        (float(h.get("solar_radiation_wm2", 0) or 0) for h in window),
                        default=None,
                    )
            except (ValueError, TypeError, AttributeError):
                pass
        self.weather = {
            "condition": weather_condition(precipitation_mm, solar_radiation_wm2),
            "temperature_c": temperature_c,
            "precipitation_mm": precipitation_mm,
            "solar_radiation_wm2": solar_radiation_wm2,
            "horizon_label": "next 24h",
            "confidence": None,
            "status": v.get("status", "unavailable"),
            "timestamp": v.get("timestamp"),
        }

    def _apply_alerts(self, events: list[dict]) -> None:
        # Newest first, matching the old fake service ordering.
        ordered = list(reversed(events))
        self.recent_alerts = deque(ordered[:50], maxlen=50)
        cutoff = (
            datetime.now(UTC) - timedelta(minutes=ACTIVE_ALERT_WINDOW_MIN)
        ).isoformat()
        self.active_alerts = [
            e for e in ordered if (e.get("timestamp") or "") >= cutoff
        ]

    # -- read API (unchanged shapes) ----------------------------------------

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
        source = _HISTORY_SOURCES.get(sensor)
        if source is None or self._client is None:
            return []
        topic, measurement, scale = source
        downsample = "1m" if hours <= 1 else "5m"
        rows = await self._client.history(topic, hours=hours, downsample=downsample)
        pts = metric_series(rows, measurement, scale=scale)
        if len(pts) > max_points:
            step = len(pts) / max_points
            pts = [pts[int(i * step)] for i in range(max_points)]
        return pts

    def system_status(self) -> dict:
        cal = _num(self.soil_moisture.get("calibrated"))
        tank = _num(self.tank.get("level_pct"))
        ctrl = self.controller.get("state", "unknown")
        n_alerts = len(self.active_alerts)
        has_critical = any(a.get("severity") == "critical" for a in self.active_alerts)

        if not self._connected:
            level, message = (
                "warning",
                "No data from logger (P06) — check the connection",
            )
        elif ctrl == "error":
            level, message = "error", "Controller in error state"
        elif has_critical:
            level, message = "error", "Critical alert active"
        elif tank is not None and tank < 10:
            level, message = "error", "Water tank almost empty"
        elif cal is not None and cal < 0.20:
            level, message = "warning", "Soil is dry — watering soon"
        elif tank is not None and tank < 25:
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
            # Plant health headline. Placeholder until P16 (Plant Health Model)
            # ships a real score; for now derived from the overall status level.
            "plant_health": "needs_attention" if level == "error" else "healthy",
        }

    def get_component_health(self) -> list[dict]:
        # Derive liveness from the freshness of each component's latest reading.
        # P06 is judged by our own connection; P08 is event-driven so it's only
        # inferable from a recent alert (else "unknown" -> online=None).
        latest_ts = {
            "p01": self.soil_moisture.get("timestamp"),
            "p05": self.controller.get("timestamp"),
            "p07": self.weather.get("timestamp"),
            "p11": self.tank.get("timestamp"),
            "p12": self.power.get("timestamp"),
        }
        p08_ts = self.recent_alerts[0].get("timestamp") if self.recent_alerts else None

        out: list[dict] = []
        for cid, label in COMPONENTS:
            if cid == "p06":
                online: bool | None = self._connected
                last = None
            elif cid == "p08":
                last = p08_ts
                online = is_fresh(p08_ts, COMPONENT_FRESH_WINDOW_S) if p08_ts else None
            else:
                last = latest_ts.get(cid)
                online = is_fresh(last, COMPONENT_FRESH_WINDOW_S)
            out.append({"id": cid, "label": label, "online": online, "last_seen": last})
        return out

    # -- watering history + plant profile (real mode: honest stubs) ---------

    def get_watering_history(self, limit: int = 20) -> list[dict]:
        # TODO(p06): derive watering events (idle -> watering transitions) from
        # P06's controller-state history once that query path is available.
        return []

    def get_watering_config(self) -> dict:
        # Profile definitions mirror P05's profiles/*.json. We can't read the
        # *active* profile or change it until P05 exposes/accepts that (issue:
        # P05 integration), so editing is disabled in real mode.
        return {
            "active": None,
            "profiles": {
                "tomato": {
                    "target_moist": 0.45,
                    "dry_days": 2,
                    "suppress_daytime": True,
                },
                "cactus": {
                    "target_moist": 0.15,
                    "dry_days": 10,
                    "suppress_daytime": False,
                },
                "herbs": {
                    "target_moist": 0.55,
                    "dry_days": 1,
                    "suppress_daytime": True,
                },
            },
            "editable": False,
            "note": "Plant profile control requires P05 integration (not wired yet).",
        }

    def update_watering_config(
        self, active: str | None = None, profiles: dict | None = None
    ) -> dict:
        # P05 owns the profiles; editing them needs a P05 command path which
        # isn't wired yet. Fail honestly so the UI shows it's read-only.
        raise NotImplementedError(
            "Editing watering profiles requires a P05 command (not wired yet)."
        )


sensor_service = P06SensorService()
