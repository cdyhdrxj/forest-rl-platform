from __future__ import annotations

from collections import deque
from time import perf_counter
from typing import Optional

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from services.agrocare_coverage.generator import generate_coverage_layout
from services.agrocare_coverage.metrics import (
    compute_coverage_ratio,
    compute_heading_angle,
    compute_missed_area_ratio,
    compute_path_length,
    compute_repeat_coverage_ratio,
    compute_return_error,
    compute_return_success,
    compute_turn_cost,
)
from services.agrocare_coverage.models import CoverageEnvConfig, CoverageTrainState


class CoveragePlanningEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, config: CoverageEnvConfig, generated_layout: Optional[dict] = None):
        super().__init__()
        self.config = config
        self.row_count = int(config.row_count)
        self.size = int(config.grid_size)
        self.train_state: Optional[CoverageTrainState] = None
        self.generated_layout = dict(generated_layout or {})

        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(2,), dtype=np.float32)
        self.observation_space = spaces.Box(
            low=-1.0,
            high=1.0,
            shape=(11 + int(config.max_rows) * 4,),
            dtype=np.float32,
        )

        self.terrain = np.zeros((self.size, self.size), dtype=np.float32)
        self.free_mask = np.ones((self.size, self.size), dtype=np.float32)
        self.obstacle_mask = np.zeros((self.size, self.size), dtype=np.float32)
        self.coverage_mask = np.zeros((self.size, self.size), dtype=np.float32)
        self.gap_mask = np.zeros((self.size, self.size), dtype=np.float32)
        self.row_id_map = np.full((self.size, self.size), -1, dtype=np.int32)
        self.row_paths: list[list[tuple[int, int]]] = []
        self.row_centers: list[tuple[float, float]] = []
        self.row_target_counts: list[int] = []

        self.covered_mask = np.zeros((self.size, self.size), dtype=np.float32)
        self.target_visit_counts = np.zeros((self.size, self.size), dtype=np.float32)
        self.row_covered_counts: list[int] = []
        self.row_completion: list[float] = []

        self.home_position = (0, 0)
        self.current_position = (0, 0)
        self.current_row_index: int | None = None
        self.prev_heading_angle: float | None = None

        self.cur_step = 0
        self.total_reward = 0.0
        self.total_path_length = 0.0
        self.total_transition_count = 0
        self.total_angular_work = 0.0
        self.total_compute_time = 0.0
        self.total_repeat_target_steps = 0
        self.started_at = 0.0
        self.success = False

    def reset(self, seed=None, options=None):
        super().reset(seed=seed if seed is not None else self.config.seed)
        self._load_layout()

        self.covered_mask = np.zeros_like(self.coverage_mask, dtype=np.float32)
        self.target_visit_counts = np.zeros_like(self.coverage_mask, dtype=np.float32)
        self.row_covered_counts = [0 for _ in range(self.row_count)]
        self.row_completion = [0.0 for _ in range(self.row_count)]
        self.current_position = tuple(self.home_position)
        self.current_row_index = None
        self.prev_heading_angle = None
        self.cur_step = 0
        self.total_reward = 0.0
        self.total_path_length = 0.0
        self.total_transition_count = 0
        self.total_angular_work = 0.0
        self.total_compute_time = 0.0
        self.total_repeat_target_steps = 0
        self.started_at = perf_counter()
        self.success = False
        if self.train_state is not None:
            self.train_state.trajectory = []
            self.train_state.is_collision = False
            self.train_state.new_episode = False

        self._sync_state(reward=0.0, new_episode=False, is_collision=False, increment_step=False)
        return self._build_observation(), {}

    def step(self, action):
        started = perf_counter()
        reward = 0.0
        terminated = False
        truncated = False
        is_collision = False

        row_index, direction = self._decode_action(action)
        plan = self._plan_row_visit(row_index, direction)

        if plan is None:
            reward -= float(self.config.beta_invalid_action)
            is_collision = True
        else:
            transition_path = plan["transition_path"]
            traversal_path = plan["traversal_path"]
            full_path = plan["full_path"]

            if self.current_row_index is not None and self.current_row_index != row_index:
                self.total_transition_count += 1

            heading_cost = self._apply_heading_cost(full_path)
            self.total_angular_work += heading_cost
            transition_length = compute_path_length(transition_path)
            path_length = compute_path_length(full_path)
            self.total_path_length += path_length

            new_covered, repeated_steps = self._apply_path(full_path, row_index=row_index)
            self.total_repeat_target_steps += repeated_steps
            self.current_position = full_path[-1]
            self.current_row_index = row_index

            reward += float(self.config.alpha_new_coverage) * float(new_covered)
            reward -= float(self.config.beta_repeat_coverage) * float(repeated_steps)
            reward -= float(self.config.beta_transition) * float(transition_length)
            reward -= float(self.config.beta_path) * float(path_length)
            reward -= float(self.config.beta_turn) * float(heading_cost)

        self.cur_step += 1
        self.total_compute_time += perf_counter() - started
        coverage_ratio = compute_coverage_ratio(self.covered_mask, self.coverage_mask)

        if coverage_ratio >= 0.999:
            return_path = self._shortest_path(self.current_position, self.home_position)
            if return_path is not None and len(return_path) > 1:
                self.total_angular_work += self._apply_heading_cost(return_path)
                self.total_path_length += compute_path_length(return_path)
                _, repeated_steps = self._apply_path(return_path, row_index=None)
                self.total_repeat_target_steps += repeated_steps
                self.current_position = return_path[-1]

            self.success = compute_return_success(self.current_position, self.home_position)
            if self.success:
                reward += float(self.config.success_bonus)
            else:
                reward -= float(self.config.failure_penalty) * compute_return_error(self.current_position, self.home_position)
            terminated = True

        if self.cur_step >= int(self.config.max_steps) and not terminated:
            reward -= float(self.config.failure_penalty) * (
                compute_missed_area_ratio(self.covered_mask, self.coverage_mask)
                + compute_return_error(self.current_position, self.home_position) / max(1.0, float(self.size))
            )
            truncated = True

        self.total_reward += reward
        obs = self._build_observation()
        self._sync_state(
            reward=reward,
            new_episode=terminated or truncated,
            is_collision=is_collision,
            increment_step=True,
        )
        return obs, reward, terminated, truncated, self._build_info()

    def get_candidate_row_indices(self) -> list[int]:
        remaining = self.get_remaining_row_indices()
        return remaining or list(range(self.row_count))

    def get_remaining_row_indices(self) -> list[int]:
        return [index for index, completion in enumerate(self.row_completion) if completion < 0.999]

    def estimate_row_transition_cost(self, row_index: int, direction: int) -> dict | None:
        if row_index < 0 or row_index >= self.row_count or not self.row_paths[row_index]:
            return None
        traversal_path = self._ordered_row_path(row_index, direction)
        start = traversal_path[0]
        transition_path = self._shortest_path(self.current_position, start)
        if transition_path is None:
            return None
        return {
            "transition_length": compute_path_length(transition_path),
            "row_length": compute_path_length(traversal_path),
            "end_position": traversal_path[-1],
        }

    def estimate_future_row_cost(self, *, current_row_index: int, end_position: tuple[int, int]) -> float:
        estimates: list[float] = []
        for row_index in self.get_candidate_row_indices():
            if row_index == current_row_index:
                continue
            for direction in (-1, 1):
                traversal_path = self._ordered_row_path(row_index, direction)
                transition_path = self._shortest_path(end_position, traversal_path[0])
                if transition_path is None:
                    continue
                estimates.append(compute_path_length(transition_path) + 0.25 * compute_path_length(traversal_path))
        if estimates:
            return float(min(estimates))

        return_path = self._shortest_path(end_position, self.home_position)
        if return_path is None:
            return float(self.size * 2)
        return compute_path_length(return_path)

    def _load_layout(self) -> None:
        if not self.generated_layout:
            self.generated_layout = generate_coverage_layout(self.config)

        layout = dict(self.generated_layout)
        self.terrain = np.asarray(layout.get("terrain"), dtype=np.float32)
        self.free_mask = np.asarray(layout["free_mask"], dtype=np.float32)
        self.obstacle_mask = np.asarray(layout["obstacle_mask"], dtype=np.float32)
        self.coverage_mask = np.asarray(layout["coverage_mask"], dtype=np.float32)
        self.gap_mask = np.asarray(layout["gap_mask"], dtype=np.float32)
        self.row_id_map = np.asarray(layout["row_id_map"], dtype=np.int32)
        self.row_paths = [
            [(int(point[0]), int(point[1])) for point in path]
            for path in list(layout.get("row_paths") or [])
        ]
        self.row_target_counts = [int(item) for item in list(layout.get("row_target_counts") or [])]
        self.row_count = len(self.row_paths)
        self.home_position = tuple(int(v) for v in list(layout["home_position"]))
        self.row_centers = []
        for path in self.row_paths:
            rows = [point[0] for point in path]
            cols = [point[1] for point in path]
            self.row_centers.append((float(sum(rows) / len(rows)), float(sum(cols) / len(cols))))

    def _build_observation(self) -> np.ndarray:
        coverage_ratio = compute_coverage_ratio(self.covered_mask, self.coverage_mask)
        repeat_ratio = compute_repeat_coverage_ratio(self.target_visit_counts, self.coverage_mask)
        missed_ratio = compute_missed_area_ratio(self.covered_mask, self.coverage_mask)
        return_error = compute_return_error(self.current_position, self.home_position) / max(1.0, float(self.size))
        remaining_ratio = len(self.get_remaining_row_indices()) / max(1, self.row_count)
        transition_ratio = self.total_transition_count / max(1, self.row_count)
        angular_ratio = self.total_angular_work / max(1.0, float(self.row_count) * np.pi)

        features: list[float] = [
            self.current_position[0] / max(1.0, float(self.size - 1)),
            self.current_position[1] / max(1.0, float(self.size - 1)),
            self.home_position[0] / max(1.0, float(self.size - 1)),
            self.home_position[1] / max(1.0, float(self.size - 1)),
            coverage_ratio,
            missed_ratio,
            repeat_ratio,
            return_error,
            remaining_ratio,
            transition_ratio,
            angular_ratio,
        ]

        for row_index in range(int(self.config.max_rows)):
            if row_index < self.row_count:
                center_x, center_y = self.row_centers[row_index]
                features.extend(
                    [
                        center_x / max(1.0, float(self.size - 1)),
                        center_y / max(1.0, float(self.size - 1)),
                        float(self.row_completion[row_index]),
                        float(self.row_target_counts[row_index]) / max(1.0, float(self.size)),
                    ]
                )
            else:
                features.extend([0.0, 0.0, 0.0, 0.0])

        return np.asarray(features, dtype=np.float32)

    def _decode_action(self, action) -> tuple[int, int]:
        array = np.asarray(action, dtype=np.float32).reshape(-1)
        if array.size < 2:
            array = np.pad(array, (0, 2 - array.size), constant_values=0.0)
        normalized_row = float(np.clip(array[0], -1.0, 1.0))
        normalized_direction = float(np.clip(array[1], -1.0, 1.0))
        row_index = int(round((normalized_row + 1.0) * 0.5 * max(0, self.row_count - 1)))
        direction = 1 if normalized_direction >= 0.0 else -1
        return int(np.clip(row_index, 0, max(0, self.row_count - 1))), direction

    def _ordered_row_path(self, row_index: int, direction: int) -> list[tuple[int, int]]:
        row_path = list(self.row_paths[row_index])
        return row_path if direction >= 0 else list(reversed(row_path))

    def _plan_row_visit(self, row_index: int, direction: int) -> dict | None:
        if row_index < 0 or row_index >= self.row_count:
            return None
        traversal_path = self._ordered_row_path(row_index, direction)
        if not traversal_path:
            return None
        transition_path = self._shortest_path(self.current_position, traversal_path[0])
        if transition_path is None:
            return None
        full_path = list(transition_path)
        for point in traversal_path[1:]:
            full_path.append(point)
        return {
            "transition_path": transition_path,
            "traversal_path": traversal_path,
            "full_path": full_path,
        }

    def _apply_path(self, path: list[tuple[int, int]], *, row_index: int | None) -> tuple[int, int]:
        if not path:
            return 0, 0

        new_covered = 0
        repeated_steps = 0
        if not self.train_state:
            self.train_state = CoverageTrainState()

        for point in path:
            x, y = int(point[0]), int(point[1])
            self.train_state.trajectory.append([float(x), float(y)])
            if self.coverage_mask[x, y] > 0:
                self.target_visit_counts[x, y] += 1.0
                if self.covered_mask[x, y] == 0:
                    self.covered_mask[x, y] = 1.0
                    new_covered += 1
                    row_id = int(self.row_id_map[x, y])
                    if row_id >= 0:
                        self.row_covered_counts[row_id] += 1
                        total = max(1, self.row_target_counts[row_id])
                        self.row_completion[row_id] = min(1.0, self.row_covered_counts[row_id] / total)
                else:
                    repeated_steps += 1

        if row_index is not None and 0 <= row_index < self.row_count:
            total = max(1, self.row_target_counts[row_index])
            self.row_completion[row_index] = min(1.0, self.row_covered_counts[row_index] / total)

        return new_covered, repeated_steps

    def _apply_heading_cost(self, path: list[tuple[int, int]]) -> float:
        if len(path) < 2:
            return 0.0
        angle = compute_heading_angle(path[0], path[1])
        cost = compute_turn_cost(self.prev_heading_angle, angle)
        self.prev_heading_angle = angle
        return cost

    def _shortest_path(self, start: tuple[int, int], goal: tuple[int, int]) -> list[tuple[int, int]] | None:
        start = (int(start[0]), int(start[1]))
        goal = (int(goal[0]), int(goal[1]))
        if start == goal:
            return [start]
        if self.free_mask[start[0], start[1]] != 1 or self.free_mask[goal[0], goal[1]] != 1:
            return None

        queue: deque[tuple[int, int]] = deque([start])
        parents: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
        while queue:
            current = queue.popleft()
            if current == goal:
                break
            for nxt in self._neighbors(current):
                if nxt in parents:
                    continue
                parents[nxt] = current
                queue.append(nxt)

        if goal not in parents:
            return None

        path: list[tuple[int, int]] = []
        cursor: tuple[int, int] | None = goal
        while cursor is not None:
            path.append(cursor)
            cursor = parents[cursor]
        path.reverse()
        return path

    def _neighbors(self, point: tuple[int, int]) -> list[tuple[int, int]]:
        x, y = point
        neighbors: list[tuple[int, int]] = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.size and 0 <= ny < self.size and self.free_mask[nx, ny] == 1:
                neighbors.append((nx, ny))
        return neighbors

    def _build_info(self) -> dict:
        return {
            "success": self.success,
            "coverage_ratio": compute_coverage_ratio(self.covered_mask, self.coverage_mask),
            "missed_area_ratio": compute_missed_area_ratio(self.covered_mask, self.coverage_mask),
            "return_to_start_success": compute_return_success(self.current_position, self.home_position),
            "return_error": compute_return_error(self.current_position, self.home_position),
            "path_length": self.total_path_length,
            "task_time_sec": max(0.0, perf_counter() - self.started_at),
            "transition_count": self.total_transition_count,
            "repeat_coverage_ratio": compute_repeat_coverage_ratio(self.target_visit_counts, self.coverage_mask),
            "angular_work_rad": self.total_angular_work,
            "compute_time_sec": self.total_compute_time,
            "completed_rows": int(sum(1 for item in self.row_completion if item >= 0.999)),
            "remaining_rows": len(self.get_remaining_row_indices()),
        }

    def _sync_state(
        self,
        *,
        reward: float,
        new_episode: bool,
        is_collision: bool,
        increment_step: bool,
    ) -> None:
        if not self.train_state:
            return

        info = self._build_info()
        coverage_ratio = float(info["coverage_ratio"])
        missed_ratio = float(info["missed_area_ratio"])
        repeat_ratio = float(info["repeat_coverage_ratio"])
        return_error = float(info["return_error"])
        return_success = bool(info["return_to_start_success"])

        if increment_step:
            self.train_state.step += 1
        self.train_state.agent_pos = [[float(self.current_position[0]), float(self.current_position[1])]]
        self.train_state.goal_pos = [
            [float(center[0]), float(center[1])]
            for index, center in enumerate(self.row_centers)
            if self.row_completion[index] < 0.999
        ]
        self.train_state.landmark_pos = [
            [float(x), float(y)]
            for x, y in np.argwhere(self.obstacle_mask > 0)[:256]
        ]
        self.train_state.terrain_map = self.obstacle_mask.tolist()
        self.train_state.coverage_target_map = self.coverage_mask.tolist()
        self.train_state.covered_map = self.covered_mask.tolist()
        self.train_state.row_completion = [float(item) for item in self.row_completion]
        self.train_state.total_reward += reward
        self.train_state.new_episode = bool(new_episode)
        self.train_state.goal_count = int(info["completed_rows"])
        self.train_state.collision_count += int(is_collision)
        self.train_state.transition_count = int(self.total_transition_count)
        self.train_state.total_target_count = int(np.count_nonzero(self.coverage_mask))
        self.train_state.covered_target_count = int(np.count_nonzero(self.covered_mask))
        self.train_state.repeated_target_steps = int(self.total_repeat_target_steps)
        self.train_state.coverage_ratio = coverage_ratio
        self.train_state.missed_area_ratio = missed_ratio
        self.train_state.repeat_coverage_ratio = repeat_ratio
        self.train_state.angular_work_rad = float(info["angular_work_rad"])
        self.train_state.compute_time_sec = float(info["compute_time_sec"])
        self.train_state.task_time_sec = float(info["task_time_sec"])
        self.train_state.path_length = float(info["path_length"])
        self.train_state.return_error = return_error
        self.train_state.return_to_start_success = return_success
        self.train_state.success = bool(info["success"])
        self.train_state.remaining_rows = int(info["remaining_rows"])
        self.train_state.current_row_index = self.current_row_index
        self.train_state.obs_raw = self._build_observation()
        self.train_state.is_collision = bool(is_collision)

        if new_episode:
            self.train_state.episode += 1
            self.train_state.last_episode_reward = self.train_state.total_reward
            self.train_state.total_reward = 0.0
