"""
Component registry + freshness helper for the "which components are online"
strip. Pure (no schema import) so the mock service can use it too.
"""

from __future__ import annotations

from datetime import UTC, datetime

# (id, human label) for the upstream components the dashboard tracks.
COMPONENTS: list[tuple[str, str]] = [
    ("p01", "Soil moisture"),
    ("p05", "Controller"),
    ("p06", "Data logger"),
    ("p07", "Weather"),
    ("p08", "Anomaly detection"),
    ("p11", "Water tank"),
    ("p12", "Power"),
]


def is_fresh(ts_iso: str | None, window_s: float) -> bool:
    """True when an ISO-8601 timestamp is within ``window_s`` of now."""
    if not ts_iso:
        return False
    try:
        ts = datetime.fromisoformat(ts_iso)
    except ValueError:
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return (datetime.now(UTC) - ts).total_seconds() <= window_s
