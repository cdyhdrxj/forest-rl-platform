from __future__ import annotations

import math

import numpy as np


def compute_coverage_ratio(covered_mask: np.ndarray, coverage_mask: np.ndarray) -> float:
    total = float(np.count_nonzero(coverage_mask))
    if total <= 0.0:
        return 0.0
    covered = float(np.count_nonzero((covered_mask > 0) & (coverage_mask > 0)))
    return covered / total


def compute_missed_area_ratio(covered_mask: np.ndarray, coverage_mask: np.ndarray) -> float:
    return 1.0 - compute_coverage_ratio(covered_mask, coverage_mask)


def compute_repeat_coverage_ratio(target_visit_counts: np.ndarray, coverage_mask: np.ndarray) -> float:
    target_visits = np.where(coverage_mask > 0, target_visit_counts, 0)
    repeated = float(np.sum(np.clip(target_visits - 1.0, 0.0, None)))
    total = float(np.count_nonzero(coverage_mask))
    if total <= 0.0:
        return 0.0
    return repeated / total


def compute_return_error(position: tuple[int, int], home_position: tuple[int, int]) -> float:
    return float(math.hypot(position[0] - home_position[0], position[1] - home_position[1]))


def compute_return_success(position: tuple[int, int], home_position: tuple[int, int]) -> bool:
    return int(position[0]) == int(home_position[0]) and int(position[1]) == int(home_position[1])


def compute_path_length(points: list[tuple[int, int]] | list[list[int]]) -> float:
    if len(points) < 2:
        return 0.0
    total = 0.0
    for current, nxt in zip(points, points[1:]):
        total += float(math.hypot(float(nxt[0]) - float(current[0]), float(nxt[1]) - float(current[1])))
    return total


def compute_heading_angle(start: tuple[int, int], end: tuple[int, int]) -> float | None:
    dx = float(end[0] - start[0])
    dy = float(end[1] - start[1])
    if dx == 0.0 and dy == 0.0:
        return None
    return math.atan2(dy, dx)


def compute_turn_cost(previous_angle: float | None, current_angle: float | None) -> float:
    if previous_angle is None or current_angle is None:
        return 0.0
    delta = current_angle - previous_angle
    while delta > math.pi:
        delta -= 2.0 * math.pi
    while delta < -math.pi:
        delta += 2.0 * math.pi
    return abs(delta)

