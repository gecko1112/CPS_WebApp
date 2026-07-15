"""
P13-owned plant-profile catalogue.

Decision (2026-07-15, agreed with P05): the profile data lives HERE in the
web app, not in P05. Four FIXED presets (base/cactus/herbs/tomato - value-
identical to P05's shipped central-config profiles) plus exactly ONE editable
profile, "custom". Whenever something changes - the custom profile's values
or which profile is active - the ACTIVE profile's full parameter set is
pushed to P05 as per-key runtime overrides (schema.p05.ProfileOverrideCommand,
in-memory on P05).

State here is in-memory as well: the custom profile and the active selection
reset when the backend restarts, matching the lifetime of P05's overrides.
"""

from __future__ import annotations

# Parameter bounds - same rules schema.p05.validate_profile_override enforces
# on the wire (kept in sync manually; the wire is validated again anyway).
_BOOL_KEYS = frozenset({"suppress_daytime", "suppress_rain"})
_RANGES: dict[str, tuple[float, float]] = {
    "moist_lower": (0.0, 1.0),
    "moist_upper": (0.0, 1.0),
    "dry_days": (0.0, 365.0),
    "rain_suppress_threshold_mm": (0.0, 200.0),
}
PROFILE_KEYS = (
    "moist_lower",
    "moist_upper",
    "dry_days",
    "suppress_daytime",
    "suppress_rain",
    "rain_suppress_threshold_mm",
)

# Value-identical to P05's shipped central-config profiles (cps_config.p05).
FIXED_PROFILES: dict[str, dict] = {
    "base": {
        "moist_lower": 0.6,
        "moist_upper": 0.7,
        "dry_days": 0,
        "suppress_daytime": False,
        "suppress_rain": True,
        "rain_suppress_threshold_mm": 2.0,
    },
    "cactus": {
        "moist_lower": 0.1,
        "moist_upper": 0.2,
        "dry_days": 14,
        "suppress_daytime": False,
        "suppress_rain": False,
        "rain_suppress_threshold_mm": 0.0,
    },
    "herbs": {
        "moist_lower": 0.4,
        "moist_upper": 0.55,
        "dry_days": 0,
        "suppress_daytime": False,
        "suppress_rain": True,
        "rain_suppress_threshold_mm": 20.0,
    },
    "tomato": {
        "moist_lower": 0.35,
        "moist_upper": 0.5,
        "dry_days": 0,
        "suppress_daytime": True,
        "suppress_rain": True,
        "rain_suppress_threshold_mm": 10.0,
    },
}


def _validate_profile(values: dict) -> dict:
    """Validate + normalise a full custom-profile value set. Raises ValueError
    with a human-readable message."""
    out: dict = {}
    for key in PROFILE_KEYS:
        if key not in values:
            raise ValueError(f"missing profile key {key!r}")
        value = values[key]
        if key in _BOOL_KEYS:
            out[key] = bool(value)
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"value for {key!r} must be a number")
        low, high = _RANGES[key]
        if not (low <= value <= high):
            raise ValueError(f"value for {key!r} must be between {low} and {high}")
        if key == "dry_days":
            if not float(value).is_integer():
                raise ValueError("dry_days must be a whole number")
            value = int(value)
        out[key] = value
    if out["moist_upper"] <= out["moist_lower"]:
        raise ValueError("moist_upper must be greater than moist_lower")
    return out


class ProfileStore:
    def __init__(self) -> None:
        # "custom" starts as a copy of base - a sensible editing baseline.
        self.custom: dict = dict(FIXED_PROFILES["base"])
        # P05 boots with its central-config default profile ("base").
        self.active: str = "base"

    @property
    def profiles(self) -> dict[str, dict]:
        return {**{k: dict(v) for k, v in FIXED_PROFILES.items()}, "custom": dict(self.custom)}

    def config(self, note: str = "") -> dict:
        return {
            "active": self.active,
            "profiles": self.profiles,
            "editable": True,
            "editable_profiles": ["custom"],
            "note": note,
        }

    def update(
        self, active: str | None = None, profiles: dict | None = None
    ) -> list[tuple[str, float]]:
        """Apply a change (active selection and/or new custom values; edits to
        fixed presets are ignored - the UI disables them anyway). Returns the
        ACTIVE profile's full (key, wire-value) list to push to P05."""
        if profiles is not None and "custom" in profiles:
            self.custom = _validate_profile(profiles["custom"])
        if active is not None:
            if active not in self.profiles:
                raise ValueError(f"unknown profile {active!r}")
            self.active = active
        values = self.profiles[self.active]
        return [
            (key, 1.0 if values[key] else 0.0)
            if key in _BOOL_KEYS
            else (key, float(values[key]))
            for key in PROFILE_KEYS
        ]


profile_store = ProfileStore()
