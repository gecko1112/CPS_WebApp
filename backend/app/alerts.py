"""
AlertService — manages active and recent anomaly alerts.

Prototype behaviour: a fake alert fires 30 s after startup so the UI can be
developed and tested without real sensor data.

── MQTT INTEGRATION POINT ────────────────────────────────────────────────────
When aiomqtt is wired up, remove _fake_alert_loop() and instead subscribe to:

  Topic:   alerts/<plant_id>
  Payload: {"severity": "warning"|"error", "code": "LOW_MOISTURE", "plain_message": "..."}

  On message received:
      alert_service.add_alert(
          severity=msg["severity"],
          code=msg["code"],
          plain_message=msg["plain_message"],
      )

  On resolved (anomaly detector publishes a clear event, or use TTL):
      alert_service.resolve(alert_id)   # specific alert
      alert_service.resolve_all()       # clear everything
──────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import asyncio
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import List


class Alert:
    def __init__(self, severity: str, code: str, plain_message: str):
        self.id = str(uuid.uuid4())
        self.severity = severity        # "warning" | "error"
        self.code = code                # machine-readable tag, e.g. "LOW_MOISTURE"
        self.plain_message = plain_message
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.active = True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "severity": self.severity,
            "code": self.code,
            "plain_message": self.plain_message,
            "timestamp": self.timestamp,
            "active": self.active,
        }


class AlertService:
    def __init__(self, recent_size: int = 50):
        self._active: List[Alert] = []
        self._recent: deque[Alert] = deque(maxlen=recent_size)
        self._task: asyncio.Task | None = None

    async def start(self):
        self._task = asyncio.create_task(self._fake_alert_loop())

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _fake_alert_loop(self):
        """
        Fires fake alerts so the UI can be built before real MQTT data arrives.
        Remove this entire method once aiomqtt integration is in place.
        """
        # Warning fires 30 s after startup
        await asyncio.sleep(30)
        self.add_alert(
            severity="warning",
            code="LOW_MOISTURE",
            plain_message="Soil moisture is getting low — the plant may need water soon.",
        )

        # Auto-resolve after 60 s, then fire an error to demo that state too
        await asyncio.sleep(60)
        self.resolve_all()

        await asyncio.sleep(10)
        self.add_alert(
            severity="error",
            code="TANK_CRITICAL",
            plain_message="Water tank is almost empty — refill it before the next watering cycle.",
        )

    # ── Public API (same interface whether data comes from fake loop or MQTT) ──

    def add_alert(self, severity: str, code: str, plain_message: str) -> Alert:
        alert = Alert(severity=severity, code=code, plain_message=plain_message)
        self._active.append(alert)
        self._recent.appendleft(alert)
        return alert

    def resolve(self, alert_id: str):
        self._active = [a for a in self._active if a.id != alert_id]

    def resolve_all(self):
        for a in self._active:
            a.active = False
        self._active.clear()

    @property
    def active_alerts(self) -> List[dict]:
        return [a.to_dict() for a in self._active]

    @property
    def recent_alerts(self) -> List[dict]:
        return [a.to_dict() for a in self._recent]


# Singleton — imported by main.py and (later) by the MQTT subscriber
alert_service = AlertService()
