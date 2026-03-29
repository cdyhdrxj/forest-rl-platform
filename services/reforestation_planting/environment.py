from __future__ import annotations

from typing import Optional

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from services.reforestation_planting.models import PlantingEnvConfig, PlantingTrainState


class SeedlingPlantingEnv(gym.Env):
    metadata = {"render_modes": []}

    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3
    PLANT = 4
    STAY = 5

    ORIENTATIONS = {
        UP: 0,
        RIGHT: 1,
        DOWN: 2,
        LEFT: 3,
    }

    MOVE_DELTAS = {
        UP: (-1, 0),
        DOWN: (1, 0),
        LEFT: (0, -1),
        RIGHT: (0, 1),
    }

    def __init__(self, config: PlantingEnvConfig, generated_layout: Optional[dict] = None):
        super().__init__()
        self.config = config
        self.size = config.grid_size
        self.train_state: Optional[PlantingTrainState] = None
        self.generated_layout = generated_layout or {}
        self.action_space = spaces.Discrete(6)
        self.observation_space = spaces.Box(
            low=0.0,
            high=1.0,
            shape=(8, self.size, self.size),
            dtype=np.float32,
        )

        self.free_mask = np.ones((self.size, self.size), dtype=np.float32)
        self.plantable_mask = np.ones((self.size, self.size), dtype=np.float32)
        self.quality_map = np.ones((self.size, self.size), dtype=np.float32)
        self.success_prob_map = np.ones((self.size, self.size), dtype=np.float32)
        self.target_density_map = np.full((self.size, self.size), config.target_density, dtype=np.float32)
        self.planted = np.zeros((self.size, self.size), dtype=np.float32)
        self.robot_pos = (0, 0)
        self.orientation = self.ORIENTATIONS[self.RIGHT]
        self.remaining_seedlings = config.initial_seedlings
        self.cur_step = 0

    def reset(self, seed=None, options=None):
        super().reset(seed=seed if seed is not None else self.config.seed)
        self.cur_step = 0
        self.orientation = self.ORIENTATIONS[self.RIGHT]
        self.remaining_seedlings = self.config.initial_seedlings
        self.planted = np.zeros((self.size, self.size), dtype=np.float32)

        self._generate_layout()
        self.robot_pos = self._sample_start_position()

        obs = self._build_observation()
        self._sync_state(reward=0.0, new_episode=False, invalid_plant=False, fail_move=False, obs=obs)
        return obs, {}

    def step(self, action):
        reward = 0.0
        fail_move = False
        invalid_plant = False
        terminated = False
        truncated = False

        if action in self.MOVE_DELTAS:
            reward -= self.config.beta_move
            reward -= self.config.beta_turn * float(self.orientation != self.ORIENTATIONS[action])
            self.orientation = self.ORIENTATIONS[action]
            fail_move = not self._move(action)
            if fail_move:
                reward -= self.config.beta_fail_move
        elif action == self.PLANT:
            planted_now = self._attempt_plant()
            if planted_now:
                x, y = self.robot_pos
                reward += self.config.alpha_plant
                reward += self.config.alpha_quality * float(self.quality_map[x, y])
            else:
                invalid_plant = True
                reward -= self.config.beta_invalid_plant
        else:
            reward -= self.config.beta_stay

        self.cur_step += 1
        terminated = self.remaining_seedlings == 0 or self._available_plant_cells_count() == 0
        truncated = self.cur_step >= self.config.max_steps

        if terminated or truncated:
            reward += self._terminal_reward()

        obs = self._build_observation()
        self._sync_state(
            reward=reward,
            new_episode=terminated or truncated,
            invalid_plant=invalid_plant,
            fail_move=fail_move,
            obs=obs,
        )
        return obs, reward, terminated, truncated, self._build_info()

    def _generate_layout(self) -> None:
        if self.generated_layout:
            self.free_mask = np.array(self.generated_layout["free_mask"], dtype=np.float32, copy=True)
            self.plantable_mask = np.array(self.generated_layout["plantable_mask"], dtype=np.float32, copy=True)
            self.quality_map = np.array(self.generated_layout["quality_map"], dtype=np.float32, copy=True)
            self.success_prob_map = np.array(self.generated_layout["success_prob_map"], dtype=np.float32, copy=True)
            return

        noise = self.np_random.random((self.size, self.size))
        self.free_mask = (noise > self.config.obstacle_density).astype(np.float32)
        if np.count_nonzero(self.free_mask) == 0:
            self.free_mask[0, 0] = 1.0

        plant_noise = self.np_random.random((self.size, self.size))
        self.plantable_mask = ((plant_noise < self.config.plantable_density) & (self.free_mask == 1)).astype(np.float32)
        if np.count_nonzero(self.plantable_mask) == 0:
            free_cells = np.argwhere(self.free_mask == 1)
            x, y = free_cells[0]
            self.plantable_mask[x, y] = 1.0

        quality_noise = self.np_random.random((self.size, self.size)).astype(np.float32)
        success_noise = self.np_random.random((self.size, self.size)).astype(np.float32)
        self.quality_map = np.where(
            self.plantable_mask == 1,
            np.clip(1.0 - self.config.quality_noise + quality_noise * self.config.quality_noise, 0.0, 1.0),
            0.0,
        ).astype(np.float32)
        self.success_prob_map = np.where(
            self.plantable_mask == 1,
            np.clip(1.0 - self.config.success_probability_noise + success_noise * self.config.success_probability_noise, 0.05, 1.0),
            0.0,
        ).astype(np.float32)

    def _sample_start_position(self) -> tuple[int, int]:
        if self.generated_layout and "start_position" in self.generated_layout:
            x, y = self.generated_layout["start_position"]
            return int(x), int(y)

        free_cells = np.argwhere(self.free_mask == 1)
        if self.config.random_start:
            idx = int(self.np_random.integers(0, len(free_cells)))
            x, y = free_cells[idx]
            return int(x), int(y)
        x, y = free_cells[0]
        return int(x), int(y)

    def _move(self, action: int) -> bool:
        dx, dy = self.MOVE_DELTAS[action]
        nx = self.robot_pos[0] + dx
        ny = self.robot_pos[1] + dy
        if 0 <= nx < self.size and 0 <= ny < self.size and self.free_mask[nx, ny] == 1:
            self.robot_pos = (nx, ny)
            return True
        return False

    def _attempt_plant(self) -> bool:
        if not self._can_plant_here():
            return False
        x, y = self.robot_pos
        success = bool(self.np_random.random() <= self.success_prob_map[x, y])
        self.remaining_seedlings = max(0, self.remaining_seedlings - 1)
        if success:
            self.planted[x, y] = 1.0
        return success

    def _can_plant_here(self) -> bool:
        x, y = self.robot_pos
        if self.remaining_seedlings <= 0:
            return False
        if self.plantable_mask[x, y] != 1 or self.planted[x, y] == 1:
            return False
        return self._is_spacing_valid(x, y)

    def _is_spacing_valid(self, x: int, y: int) -> bool:
        radius = self.config.min_plant_distance
        if radius <= 0:
            return True
        x0 = max(0, x - radius)
        x1 = min(self.size, x + radius + 1)
        y0 = max(0, y - radius)
        y1 = min(self.size, y + radius + 1)
        neighborhood = self.planted[x0:x1, y0:y1].copy()
        neighborhood[x - x0, y - y0] = 0.0
        return float(np.sum(neighborhood)) == 0.0

    def _available_plant_cells_count(self) -> int:
        available = 0
        for x, y in np.argwhere(self.plantable_mask == 1):
            if self.planted[x, y] == 0 and self._is_spacing_valid(int(x), int(y)):
                available += 1
        return available

    def _uniformity_penalty(self) -> float:
        radius = self.config.uniformity_radius
        penalty = 0.0
        plantable_positions = np.argwhere(self.plantable_mask == 1)
        for x, y in plantable_positions:
            x = int(x)
            y = int(y)
            x0 = max(0, x - radius)
            x1 = min(self.size, x + radius + 1)
            y0 = max(0, y - radius)
            y1 = min(self.size, y + radius + 1)
            plantable_window = self.plantable_mask[x0:x1, y0:y1]
            denominator = float(np.sum(plantable_window))
            if denominator <= 0:
                continue
            local_density = float(np.sum(self.planted[x0:x1, y0:y1])) / denominator
            penalty += (local_density - float(self.target_density_map[x, y])) ** 2
        return penalty

    def _underplanting_penalty(self) -> float:
        planted_count = int(np.sum(self.planted))
        return max(0, int(self.config.target_plant_count) - planted_count)

    def _terminal_reward(self) -> float:
        return (
            -self.config.lambda_uniformity * self._uniformity_penalty()
            -self.config.lambda_underplanting * self._underplanting_penalty()
        )

    def _build_observation(self) -> np.ndarray:
        agent_layer = np.zeros((self.size, self.size), dtype=np.float32)
        agent_layer[self.robot_pos] = 1.0

        valid_plant_layer = np.zeros((self.size, self.size), dtype=np.float32)
        for x, y in np.argwhere(self.plantable_mask == 1):
            if self.planted[x, y] == 0 and self._is_spacing_valid(int(x), int(y)):
                valid_plant_layer[int(x), int(y)] = 1.0

        inventory_layer = np.full(
            (self.size, self.size),
            self.remaining_seedlings / max(1, self.config.initial_seedlings),
            dtype=np.float32,
        )

        return np.stack(
            [
                self.free_mask,
                self.plantable_mask,
                self.planted,
                self.quality_map,
                self.success_prob_map,
                agent_layer,
                valid_plant_layer,
                inventory_layer,
            ]
        ).astype(np.float32)

    def _build_info(self) -> dict:
        return {
            "coverage_ratio": self._coverage_ratio(),
            "successful_plant_count": int(np.sum(self.planted)),
            "remaining_seedlings": self.remaining_seedlings,
            "available_plant_cells": self._available_plant_cells_count(),
        }

    def _coverage_ratio(self) -> float:
        denominator = float(np.sum(self.plantable_mask))
        if denominator <= 0:
            return 0.0
        return float(np.sum(self.planted)) / denominator

    def _sync_state(
        self,
        reward: float,
        new_episode: bool,
        invalid_plant: bool,
        fail_move: bool,
        obs: np.ndarray,
    ) -> None:
        if not self.train_state:
            return

        x, y = self.robot_pos
        self.train_state.agent_pos = [[float(x), float(y)]]
        self.train_state.trajectory.append([float(x), float(y)])
        self.train_state.goal_pos = [[float(px), float(py)] for px, py in np.argwhere(self.plantable_mask == 1)]
        self.train_state.landmark_pos = [[float(px), float(py)] for px, py in np.argwhere(self.free_mask == 0)]
        self.train_state.planted_pos = [[float(px), float(py)] for px, py in np.argwhere(self.planted == 1)]
        self.train_state.terrain_map = (1.0 - self.free_mask).tolist()
        self.train_state.plantable_map = self.plantable_mask.tolist()
        self.train_state.planted_map = self.planted.tolist()
        self.train_state.total_reward += reward
        self.train_state.step += 1
        self.train_state.new_episode = new_episode
        self.train_state.successful_plant_count = int(np.sum(self.planted))
        self.train_state.invalid_plant_count += int(invalid_plant)
        self.train_state.collision_count += int(fail_move)
        self.train_state.is_collision = fail_move
        self.train_state.coverage_ratio = self._coverage_ratio()
        self.train_state.remaining_seedlings = self.remaining_seedlings
        self.train_state.obs_raw = obs

        if new_episode:
            self.train_state.episode += 1
            self.train_state.last_episode_reward = self.train_state.total_reward
            self.train_state.total_reward = 0.0
            self.train_state.trajectory = []
