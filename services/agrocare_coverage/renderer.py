from __future__ import annotations

from typing import Any

import numpy as np


def build_landmark_positions(mask: np.ndarray, *, limit: int = 256) -> list[list[float]]:
    points = np.argwhere(mask > 0)
    return [[float(x), float(y)] for x, y in points[:limit]]


def build_row_centers(row_paths: list[list[list[int]]]) -> list[list[float]]:
    centers: list[list[float]] = []
    for path in row_paths:
        if not path:
            centers.append([0.0, 0.0])
            continue
        rows = [float(point[0]) for point in path]
        cols = [float(point[1]) for point in path]
        centers.append([sum(rows) / len(rows), sum(cols) / len(cols)])
    return centers


def build_preview_payload(layout: dict[str, Any]) -> dict[str, Any]:
    obstacle_mask = np.asarray(layout["obstacle_mask"], dtype=np.float32)
    coverage_mask = np.asarray(layout["coverage_mask"], dtype=np.float32)
    row_paths = list(layout.get("row_paths") or [])
    row_centers = build_row_centers(row_paths)
    start_position = list(layout["start_position"])

    return {
        "terrain_map": obstacle_mask.tolist(),
        "agent_pos": [[float(start_position[0]), float(start_position[1])]],
        "goal_pos": [[float(item[0]), float(item[1])] for item in row_centers],
        "landmark_pos": build_landmark_positions(obstacle_mask),
        "coverage_target_map": coverage_mask.tolist(),
    }

