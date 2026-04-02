from __future__ import annotations

from copy import deepcopy
from typing import Any


_COVERAGE_FAMILY_PRESETS: dict[str, dict[str, Any]] = {
    "S1": {
        "field_profile": "simple",
        "grid_size": 32,
        "row_count_range": [8, 12],
        "curvature_level": "low",
        "gap_probability": 0.0,
        "obstacle_count_range": [0, 0],
        "max_steps": 24,
    },
    "S2": {
        "field_profile": "tapered",
        "grid_size": 32,
        "row_count_range": [8, 12],
        "curvature_level": "low",
        "gap_probability": 0.0,
        "obstacle_count_range": [1, 2],
        "max_steps": 24,
    },
    "S3": {
        "field_profile": "concave",
        "grid_size": 36,
        "row_count_range": [8, 12],
        "curvature_level": "medium",
        "gap_probability": 0.0,
        "obstacle_count_range": [2, 4],
        "max_steps": 28,
    },
    "S4": {
        "field_profile": "concave",
        "grid_size": 36,
        "row_count_range": [8, 12],
        "curvature_level": "high",
        "gap_probability": 0.2,
        "obstacle_count_range": [2, 4],
        "gap_segment_length": 3,
        "max_steps": 28,
    },
}


def normalize_coverage_family(value: str | None) -> str:
    normalized = str(value or "").strip().upper()
    return normalized or "CUSTOM"


def is_known_coverage_family(value: str | None) -> bool:
    return normalize_coverage_family(value) in _COVERAGE_FAMILY_PRESETS


def get_coverage_family_preset(value: str | None) -> dict[str, Any] | None:
    normalized = normalize_coverage_family(value)
    preset = _COVERAGE_FAMILY_PRESETS.get(normalized)
    if preset is None:
        return None
    return deepcopy(preset)


def resolve_coverage_family_params(
    family: str | None,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    merged = get_coverage_family_preset(family) or {}
    merged.update(dict(overrides or {}))
    normalized = normalize_coverage_family(family)
    if normalized != "CUSTOM":
        merged.setdefault("family", normalized)
    return merged
