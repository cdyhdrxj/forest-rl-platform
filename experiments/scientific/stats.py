from __future__ import annotations

from statistics import mean, median, pstdev
from typing import Iterable


def maybe_mean(values: Iterable[float | int | None]) -> float | None:
    prepared = _prepare(values)
    if not prepared:
        return None
    return float(mean(prepared))


def maybe_median(values: Iterable[float | int | None]) -> float | None:
    prepared = _prepare(values)
    if not prepared:
        return None
    return float(median(prepared))


def maybe_std(values: Iterable[float | int | None]) -> float | None:
    prepared = _prepare(values)
    if not prepared:
        return None
    if len(prepared) == 1:
        return 0.0
    return float(pstdev(prepared))


def maybe_min(values: Iterable[float | int | None]) -> float | None:
    prepared = _prepare(values)
    if not prepared:
        return None
    return float(min(prepared))


def maybe_max(values: Iterable[float | int | None]) -> float | None:
    prepared = _prepare(values)
    if not prepared:
        return None
    return float(max(prepared))


def _prepare(values: Iterable[float | int | None]) -> list[float]:
    prepared: list[float] = []
    for value in values:
        if value is None:
            continue
        prepared.append(float(value))
    return prepared

