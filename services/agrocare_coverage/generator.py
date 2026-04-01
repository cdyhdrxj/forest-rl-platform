from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np

from services.agrocare_coverage.models import CoverageEnvConfig
from services.agrocare_coverage.renderer import build_preview_payload
from services.scenario_generator.models import GeneratedLayer, GeneratedScenario


CURVATURE_TO_AMPLITUDE = {
    "low": 0.75,
    "medium": 1.5,
    "high": 2.5,
}


def generate_coverage_layout(config: CoverageEnvConfig) -> dict[str, Any]:
    rng = np.random.default_rng(config.seed)
    size = int(config.grid_size)
    row_count = int(config.row_count)

    terrain = rng.random((size, size), dtype=np.float32) * 0.15
    obstacle_mask = np.zeros((size, size), dtype=np.float32)
    free_mask = np.ones((size, size), dtype=np.float32)
    coverage_mask = np.zeros((size, size), dtype=np.float32)
    gap_mask = np.zeros((size, size), dtype=np.float32)
    row_id_map = np.full((size, size), -1, dtype=np.int32)

    base_rows = np.linspace(2, size - 3, row_count)
    amplitude = CURVATURE_TO_AMPLITUDE[str(config.curvature_level)] * max(1.0, size / 32.0)
    path_buffer: set[tuple[int, int]] = set()
    row_paths: list[list[list[int]]] = []

    for row_index, base in enumerate(base_rows):
        phase = float(rng.uniform(0.0, 2.0 * np.pi))
        frequency = float(rng.uniform(0.85, 1.25))
        raw_points: list[tuple[int, int]] = []
        for col in range(1, size - 1):
            row = int(round(base + amplitude * np.sin((2.0 * np.pi * col / max(size - 2, 1)) * frequency + phase)))
            row = int(np.clip(row, 1, size - 2))
            raw_points.append((row, col))

        row_path = _deduplicate_points(_densify_polyline(raw_points))
        for cell in row_path:
            path_buffer.add(tuple(cell))
        row_paths.append([[int(x), int(y)] for x, y in row_path])

    for obstacle_cells in _sample_obstacles(rng, config, size, path_buffer):
        for x, y in obstacle_cells:
            obstacle_mask[x, y] = 1.0
            free_mask[x, y] = 0.0

    row_target_counts: list[int] = []
    row_completion_template: list[float] = []
    for row_index, row_path in enumerate(row_paths):
        gap_cells = _sample_gap_cells(rng, row_path, probability=float(config.gap_probability), length=int(config.gap_segment_length))
        target_count = 0
        for x, y in row_path:
            if (x, y) in gap_cells:
                gap_mask[x, y] = 1.0
                continue
            coverage_mask[x, y] = 1.0
            row_id_map[x, y] = row_index
            target_count += 1
        if target_count == 0 and row_path:
            x, y = row_path[len(row_path) // 2]
            coverage_mask[x, y] = 1.0
            row_id_map[x, y] = row_index
            target_count = 1
        row_target_counts.append(target_count)
        row_completion_template.append(0.0)

    start_row = row_paths[0][0][0] if row_paths and row_paths[0] else 1
    start_position = [int(start_row), 0]
    home_position = list(start_position)
    if free_mask[start_position[0], start_position[1]] != 1:
        free_mask[start_position[0], start_position[1]] = 1.0
        obstacle_mask[start_position[0], start_position[1]] = 0.0

    layout = {
        "grid_size": size,
        "row_count": row_count,
        "terrain": terrain.astype(np.float32),
        "free_mask": free_mask.astype(np.float32),
        "coverage_mask": coverage_mask.astype(np.float32),
        "gap_mask": gap_mask.astype(np.float32),
        "obstacle_mask": obstacle_mask.astype(np.float32),
        "row_id_map": row_id_map.astype(np.int32),
        "row_paths": row_paths,
        "row_target_counts": row_target_counts,
        "row_completion_template": row_completion_template,
        "start_position": start_position,
        "home_position": home_position,
    }
    return layout


def apply_coverage_layout_to_scenario(
    scenario: GeneratedScenario,
    config: CoverageEnvConfig,
    *,
    family: str | None = None,
    split: str | None = None,
) -> None:
    layout = generate_coverage_layout(config)
    preview_payload = build_preview_payload(layout)

    scenario.generator_name = "agrocare_coverage_generator"
    scenario.generator_version = "v1"
    scenario.effective_params.update(
        {
            "grid_size": config.grid_size,
            "row_count": config.row_count,
            "curvature_level": config.curvature_level,
            "gap_probability": config.gap_probability,
            "obstacle_count": config.obstacle_count,
            "max_steps": config.max_steps,
        }
    )
    if family:
        scenario.effective_params["family"] = family
    if split:
        scenario.effective_params["split"] = split

    scenario.runtime_context["coverage"] = layout
    scenario.preview_payload = preview_payload
    scenario.add_layer(GeneratedLayer("coverage_mask", "coverage_mask", layout["coverage_mask"], description="Cells to cover"))
    scenario.add_layer(GeneratedLayer("gap_mask", "gap_mask", layout["gap_mask"], description="Coverage gaps"))
    scenario.add_layer(GeneratedLayer("obstacle_mask", "obstacle_mask", layout["obstacle_mask"], description="Internal obstacles"))
    scenario.add_layer(GeneratedLayer("free_mask", "free_mask", layout["free_mask"], description="Traversable cells"))
    scenario.add_layer(
        GeneratedLayer(
            "row_id_map",
            "row_id_map",
            layout["row_id_map"].astype(np.float32),
            description="Row index for each coverage cell",
        )
    )


def build_runtime_config(params: dict[str, Any], scenario: GeneratedScenario) -> CoverageEnvConfig:
    effective = dict(scenario.effective_params or {})
    merged = {
        "grid_size": effective.get("grid_size", params.get("grid_size", 32)),
        "row_count": effective.get("row_count", params.get("row_count", 8)),
        "curvature_level": effective.get("curvature_level", params.get("curvature_level", "low")),
        "gap_probability": effective.get("gap_probability", params.get("gap_probability", 0.0)),
        "obstacle_count": effective.get("obstacle_count", params.get("obstacle_count", 0)),
        "max_steps": effective.get("max_steps", params.get("max_steps", 24)),
        "seed": scenario.seed,
    }

    passthrough = [
        "max_rows",
        "gap_segment_length",
        "obstacle_radius_min",
        "obstacle_radius_max",
        "alpha_new_coverage",
        "beta_repeat_coverage",
        "beta_transition",
        "beta_path",
        "beta_turn",
        "beta_invalid_action",
        "success_bonus",
        "failure_penalty",
    ]
    for key in passthrough:
        if key in params:
            merged[key] = params[key]

    return CoverageEnvConfig.model_validate(merged)


def _sample_obstacles(
    rng: np.random.Generator,
    config: CoverageEnvConfig,
    size: int,
    protected_cells: set[tuple[int, int]],
) -> list[list[tuple[int, int]]]:
    obstacles: list[list[tuple[int, int]]] = []
    attempts = 0
    while len(obstacles) < int(config.obstacle_count) and attempts < int(config.obstacle_count) * 80 + 40:
        attempts += 1
        center_x = int(rng.integers(2, size - 2))
        center_y = int(rng.integers(2, size - 2))
        radius = int(rng.integers(config.obstacle_radius_min, config.obstacle_radius_max + 1))
        cells: list[tuple[int, int]] = []
        overlap = False
        for x in range(max(1, center_x - radius), min(size - 1, center_x + radius + 1)):
            for y in range(max(1, center_y - radius), min(size - 1, center_y + radius + 1)):
                if (x - center_x) ** 2 + (y - center_y) ** 2 > radius ** 2:
                    continue
                cells.append((x, y))
                if any((nx, ny) in protected_cells for nx, ny in _neighbors_with_margin(x, y)):
                    overlap = True
                    break
            if overlap:
                break
        if overlap or not cells:
            continue
        obstacles.append(cells)
    return obstacles


def _sample_gap_cells(
    rng: np.random.Generator,
    row_path: list[list[int]],
    *,
    probability: float,
    length: int,
) -> set[tuple[int, int]]:
    if probability <= 0.0 or len(row_path) < 6:
        return set()

    gap_cells: set[tuple[int, int]] = set()
    gap_count = 0
    if rng.random() < probability:
        gap_count += 1
    if probability >= 0.4 and rng.random() < probability - 0.25:
        gap_count += 1

    for _ in range(gap_count):
        start = int(rng.integers(2, max(3, len(row_path) - length - 1)))
        for point in row_path[start:start + length]:
            gap_cells.add((int(point[0]), int(point[1])))
    return gap_cells


def _deduplicate_points(points: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    deduplicated: list[tuple[int, int]] = []
    for point in points:
        if not deduplicated or deduplicated[-1] != point:
            deduplicated.append(point)
    return deduplicated


def _densify_polyline(points: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not points:
        return []
    dense: list[tuple[int, int]] = [points[0]]
    for current, nxt in zip(points, points[1:]):
        for point in _bresenham(current, nxt)[1:]:
            dense.append(point)
    return dense


def _bresenham(start: tuple[int, int], end: tuple[int, int]) -> list[tuple[int, int]]:
    x0, y0 = start
    x1, y1 = end
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    points: list[tuple[int, int]] = []
    while True:
        points.append((int(x0), int(y0)))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy
    return points


def _neighbors_with_margin(x: int, y: int) -> list[tuple[int, int]]:
    return [
        (x + dx, y + dy)
        for dx in (-1, 0, 1)
        for dy in (-1, 0, 1)
    ]

