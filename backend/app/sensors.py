"""
FakeSensorService — generates plausible sensor readings for development.

Replace this with a real aiomqtt subscriber once the MQTT topic schema
is agreed with the other groups. The interface (latest(), history())
should stay roughly the same so the rest of the app doesn't change.
"""
from __future__ import annotations

import asyncio
import math
import random
from collections import deque
from datetime import datetime, timezone
from typing import Deque, Dict, List


class FakeSensorService:
    def __init__(self, history_size: int = 2880):  # ~24h at 30s intervals
        # Latest values (in-memory cache)
        self.latest: Dict[str, float] = {
            "moisture": 45.0,
            "temperature": 21.5,
            "tank_level": 78.0,
        }
        # Ring buffers for history
        self.history: Dict[str, Deque[dict]] = {
            "moisture": deque(maxlen=history_size),
            "temperature": deque(maxlen=history_size),
            "tank_level": deque(maxlen=history_size),
        }
        self.last_watered_at: datetime | None = None
        self._task: asyncio.Task | None = None
        self._tick = 0

    async def start(self):
        """Start the background data generator."""
        self._task = asyncio.create_task(self._generate_loop())

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _generate_loop(self):
        """Tick every 2s in dev (would be ~30s for real sensors)."""
        while True:
            self._tick += 1
            now = datetime.now(timezone.utc)

            # Moisture: drifts down over time, jumps up when watered
            drift = -0.05 + random.uniform(-0.1, 0.1)
            self.latest["moisture"] = max(
                5.0, min(95.0, self.latest["moisture"] + drift)
            )

            # Temperature: sinusoidal day/night + noise
            base = 20.0 + 5.0 * math.sin(self._tick / 100.0)
            self.latest["temperature"] = base + random.uniform(-0.5, 0.5)

            # Tank: slowly decreases
            self.latest["tank_level"] = max(
                0.0, self.latest["tank_level"] - random.uniform(0.0, 0.05)
            )

            # Append to history
            for sensor in ("moisture", "temperature", "tank_level"):
                self.history[sensor].append(
                    {"t": now.isoformat(), "v": round(self.latest[sensor], 2)}
                )

            await asyncio.sleep(2.0)

    def trigger_watering(self):
        """Simulate a watering event — bumps moisture, drops tank."""
        self.latest["moisture"] = min(95.0, self.latest["moisture"] + 25.0)
        self.latest["tank_level"] = max(0.0, self.latest["tank_level"] - 2.0)
        self.last_watered_at = datetime.now(timezone.utc)

    def get_history(self, sensor: str, max_points: int = 200) -> List[dict]:
        """Return downsampled history for a sensor — max_points evenly sampled."""
        if sensor not in self.history:
            return []
        full = list(self.history[sensor])
        if len(full) <= max_points:
            return full
        step = len(full) / max_points
        return [full[int(i * step)] for i in range(max_points)]

    def system_status(self) -> dict:
        """Derive a high-level status from sensor values."""
        moisture = self.latest["moisture"]
        tank = self.latest["tank_level"]
        if tank < 10:
            level = "error"
            message = "Water tank almost empty"
        elif moisture < 20:
            level = "warning"
            message = "Soil is dry — watering soon"
        elif tank < 25:
            level = "warning"
            message = "Tank level low"
        else:
            level = "ok"
            message = "All systems normal"
        return {
            "level": level,
            "message": message,
            "last_watered_at": (
                self.last_watered_at.isoformat() if self.last_watered_at else None
            ),
        }


# Singleton instance used by FastAPI routes
sensor_service = FakeSensorService()
