"""Per-video conversion to the benchmark's 100-point score scale."""

from __future__ import annotations

import math

OFFICIAL_CENTER = 0.1107
OFFICIAL_SCALE = 0.07355


def official_technical_100(raw: float) -> float:
    """Apply 100*sigmoid((raw-0.1107)/0.07355) to a DOVER++ technical score."""
    raw = float(raw)
    if not math.isfinite(raw):
        raise ValueError("Technical score must be finite")
    value = (raw - OFFICIAL_CENTER) / OFFICIAL_SCALE
    if value >= 0:
        return 100 / (1 + math.exp(-value))
    exp_value = math.exp(value)
    return 100 * exp_value / (1 + exp_value)


def _full_scale_percentage(raw: float, maximum: float) -> float:
    raw = float(raw)
    if not math.isfinite(raw) or not 1 <= raw <= maximum:
        raise ValueError(f"Score outside 1..{maximum:g}: {raw}")
    return raw * (100.0 / maximum)


def aesthetic_100(raw: float) -> float:
    """Convert an aesthetic score with raw*10."""
    return _full_scale_percentage(raw, 10)


def physics_100(raw: float) -> float:
    """Convert a physics score with raw*20."""
    return _full_scale_percentage(raw, 5)
