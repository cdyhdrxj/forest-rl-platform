from __future__ import annotations

from typing import Any

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import jax
import jax.numpy as jnp
from camar import camar_v0


class CamarGymWrapper(gym.Env):
    """Обёртка CAMAR для SB3"""""

    _KNOWN_PARAMS = {
        "seed",
        "obstacle_density",
        "goal_reward",
        "collision_penalty",
        "grid_size",
        "max_steps",
        "frameskip",
        "max_speed",
        "accel",
        "damping",
        "dt",
        "step_penalty",
    }

    def __init__(
        self,
        seed: int = 0,
        grid_size: int = 10,
        obstacle_density: float = 0.2,
        goal_reward: float = 1.0,
        collision_penalty: float = 0.3,
        step_penalty: float = 0.0,
        max_steps: int = 100,
        max_speed: float = 50.0,
        accel: float = 40.0,
        damping: float = 0.6,
        dt: float = 0.03,
        frameskip: int = 1,
        **kwargs,
    ):
        super().__init__()

        self.seed_value = seed
        self.grid_size = grid_size
        self.goal_reward = goal_reward
        self.collision_penalty = collision_penalty
        self.step_penalty = step_penalty
        self.terrain_map = []

        self.env = camar_v0(
            map_generator="random_grid",
            map_kwargs={
                "num_agents": 1,
                "num_rows": grid_size,
                "num_cols": grid_size,
                "obstacle_density": obstacle_density,
                "goal_rad_range": (0.3, 0.3),
            },
            dynamic_kwargs={
                "max_speed": max_speed,
                "accel": accel,
                "damping": damping,
                "dt": dt,
            },
            frameskip=frameskip,
            max_steps=max_steps,
        )

        self._map_key = jax.random.PRNGKey(seed)
        self._step_key = jax.random.PRNGKey(seed + 1000)

        self.state = None
        self.goal_count = 0
        self.collision_count = 0

        self._jit_step = jax.jit(self.env.step)
        self._jit_reset = jax.jit(self.env.reset)

        obs_dim = self.env.observation_size
        self.observation_space = spaces.Box(
            -np.inf, np.inf, shape=(obs_dim,), dtype=np.float32
        )
        self.action_space = spaces.Box(-1.0, 1.0, shape=(2,), dtype=np.float32)

    def reset(self, seed: int | None = None, **kwargs) -> tuple[np.ndarray, dict]:
        if seed is not None:
            self._step_key = jax.random.PRNGKey(seed + 1000)

        obs, self.state = self._jit_reset(self._map_key)
        return np.array(obs).flatten().astype(np.float32), {}

    def step(self, action: np.ndarray) -> tuple[np.ndarray, float, bool, bool, dict]:
        self._step_key, subkey = jax.random.split(self._step_key)
        action_jax = jnp.array(action.reshape(1, 2))

        obs, self.state, reward, done, info = self._jit_step(
            subkey, self.state, action_jax
        )

        on_goal = bool(np.array(self.state.on_goal).any())
        is_collision = bool(np.array(self.state.is_collision).any())

        r = float(np.array(reward).sum())

        if is_collision:
            r -= self.collision_penalty
            self.collision_count += 1

        r -= self.step_penalty

        if on_goal:
            r += self.goal_reward
            self.goal_count += 1

        d = bool(np.array(done).any())

        return (
            np.array(obs).flatten().astype(np.float32),
            r,
            d,
            False,
            {"on_goal": on_goal, "is_collision": is_collision},
        )

    def get_terrain_map(self):
        return self.terrain_map

    def get_render_state(self) -> dict[str, Any]:
        if self.state is None:
            return {}
        return {
            "agent_pos": np.array(self.state.physical_state.agent_pos).tolist(),
            "goal_pos": np.array(self.state.goal_pos).tolist(),
            "landmark_pos": np.array(self.state.landmark_pos).tolist(),
            "is_collision": bool(np.array(self.state.is_collision).any()),
            "on_goal": bool(np.array(self.state.on_goal).any()),
        }

    def render(self) -> None:
        pass

    def close(self) -> None:
        pass