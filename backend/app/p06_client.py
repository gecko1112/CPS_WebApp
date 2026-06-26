"""
P06 query-API client + row-grouping helpers.

P13 reads ALL dashboard data from P06 (Data Logging & Visualisation), which
subscribes to the whole ``spBv1.0/#`` bus, decodes Sparkplug B, and stores
everything in InfluxDB. P06 exposes a read-only HTTP query API so we never
touch MQTT or Sparkplug for reads. (The one write path — manual watering — is
separate and publishes to P05 over MQTT.)

P06 query API (default ``http://localhost:8088``):
    GET /health
    GET /data?start=-24h&stop=now[&topic=<mqtt-filter>]          (relative window)
    GET /query?topic=<mqtt-filter>&from=<rfc3339>&to=<rfc3339>&downsample=<dur>

Each returned row is::

    {"time": <rfc3339>, "measurement": <metric name>, "topic": <mqtt topic>,
     "field": "value"|"value_str", "value": <number|str>}

``measurement`` is the Sparkplug metric name, e.g. ``soil_moisture/calibrated``
(slash-path) or ``temperature_c`` (flat, P03). The helpers below reshape these
flat rows into the per-reading dicts the REST API serves.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

log = logging.getLogger("p13.p06")

P06_API_URL = os.getenv("P06_API_URL", "http://localhost:8088")
P06_TIMEOUT_S = float(os.getenv("P06_TIMEOUT_S", "5"))


# ---------------------------------------------------------------------------
# Pure helpers (no I/O — unit-testable on sample rows)
# ---------------------------------------------------------------------------


def _short(measurement: str) -> str:
    """Short field name: the part after the last '/' (handles flat names too)."""
    return measurement.rsplit("/", 1)[-1]


def latest_values(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Collapse rows to the most recent value of each metric.

    Returns ``{<short_field>: value, ..., "timestamp": <newest rfc3339>}``.
    Empty dict (no ``timestamp``) when there are no rows.
    """
    by_metric: dict[str, tuple[str, Any]] = {}
    for r in rows:
        measurement = r.get("measurement")
        ts = r.get("time")
        if measurement is None or ts is None:
            continue
        if measurement not in by_metric or ts > by_metric[measurement][0]:
            by_metric[measurement] = (ts, r.get("value"))

    out: dict[str, Any] = {}
    latest_ts: str | None = None
    for measurement, (ts, value) in by_metric.items():
        out[_short(measurement)] = value
        if latest_ts is None or ts > latest_ts:
            latest_ts = ts
    if latest_ts is not None:
        out["timestamp"] = latest_ts
    return out


def metric_series(
    rows: list[dict[str, Any]], measurement: str, scale: float = 1.0
) -> list[dict[str, Any]]:
    """Time-ordered ``[{"t": <rfc3339>, "v": <value>}]`` for one measurement."""
    pts = [
        {
            "t": r["time"],
            "v": (
                round(r["value"] * scale, 4)
                if isinstance(r.get("value"), (int, float))
                else r.get("value")
            ),
        }
        for r in rows
        if r.get("measurement") == measurement and r.get("value") is not None
    ]
    pts.sort(key=lambda p: p["t"])
    return pts


def group_events(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Reassemble per-payload events (one payload = several metric rows).

    Groups by (topic, time) and returns one dict per event with each metric as
    a ``<short_field>`` key plus ``timestamp``, oldest first.
    """
    groups: dict[tuple[Any, Any], dict[str, Any]] = {}
    for r in rows:
        key = (r.get("topic"), r.get("time"))
        event = groups.setdefault(key, {"timestamp": r.get("time")})
        measurement = r.get("measurement")
        if measurement is not None:
            event[_short(measurement)] = r.get("value")
    return [groups[k] for k in sorted(groups, key=lambda k: k[1] or "")]


# ---------------------------------------------------------------------------
# Async HTTP client
# ---------------------------------------------------------------------------


class P06Client:
    """Thin async wrapper over the P06 query API. Never raises on request
    failure — returns empty results and logs, so the dashboard degrades
    gracefully when P06 is down."""

    def __init__(
        self, base_url: str = P06_API_URL, timeout: float = P06_TIMEOUT_S
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def health(self) -> bool:
        try:
            resp = await self._client.get("/health")
            resp.raise_for_status()
            return bool(resp.json().get("ok"))
        except Exception as exc:  # noqa: BLE001 — degrade gracefully
            log.warning("P06 /health failed: %s", exc)
            return False

    async def window(self, topic: str, start: str = "-15m") -> list[dict[str, Any]]:
        """Rows for a topic over a relative window (e.g. '-15m'). For 'latest'."""
        try:
            resp = await self._client.get(
                "/data", params={"start": start, "stop": "now", "topic": topic}
            )
            resp.raise_for_status()
            return resp.json().get("rows", [])
        except Exception as exc:  # noqa: BLE001
            log.warning("P06 /data topic=%s failed: %s", topic, exc)
            return []

    async def history(
        self, topic: str, hours: int = 24, downsample: str | None = "5m"
    ) -> list[dict[str, Any]]:
        """Rows for a topic over the last ``hours`` (absolute range + downsample)."""
        now = datetime.now(UTC)
        params: dict[str, str] = {
            "topic": topic,
            "from": (now - timedelta(hours=hours)).isoformat(),
            "to": now.isoformat(),
        }
        if downsample:
            params["downsample"] = downsample
        try:
            resp = await self._client.get("/query", params=params)
            resp.raise_for_status()
            return resp.json().get("rows", [])
        except Exception as exc:  # noqa: BLE001
            log.warning("P06 /query topic=%s failed: %s", topic, exc)
            return []
