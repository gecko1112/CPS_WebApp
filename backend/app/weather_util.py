"""
Weather-condition derivation from P07 signals - a pure helper (no schema import,
so both the mock and the real service can use it).

P07 publishes hourly forecasts with ``precipitation_mm`` and
``solar_radiation_wm2`` (a good cloudiness proxy: clear-sky daytime radiation is
high, overcast is low). We distil those into a coarse condition the dashboard
shows as a sun/cloud/rain icon.
"""

from __future__ import annotations

# Condition ids - the frontend maps each to an icon + label.
SUNNY = "sunny"
PARTLY_CLOUDY = "partly_cloudy"
CLOUDY = "cloudy"
LIGHT_RAIN = "light_rain"
RAINY = "rainy"
STORMY = "stormy"
UNKNOWN = "unknown"


def weather_condition(
    precipitation_mm: float | None,
    solar_radiation_wm2: float | None = None,
) -> str:
    """Coarse weather condition for a forecast window.

    ``precipitation_mm`` is the expected rainfall over the window; when it's dry,
    ``solar_radiation_wm2`` (peak over the window) decides sun vs. cloud.
    """
    if precipitation_mm is None:
        return UNKNOWN
    if precipitation_mm >= 10.0:
        return STORMY
    if precipitation_mm >= 2.5:  # noqa: PLR2004
        return RAINY
    if precipitation_mm >= 0.2:  # noqa: PLR2004
        return LIGHT_RAIN
    # Dry - use solar radiation as a cloudiness proxy.
    if solar_radiation_wm2 is None:
        return CLOUDY
    if solar_radiation_wm2 >= 500.0:  # noqa: PLR2004
        return SUNNY
    if solar_radiation_wm2 >= 200.0:  # noqa: PLR2004
        return PARTLY_CLOUDY
    return CLOUDY
