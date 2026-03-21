import gymnasium as gym
from gymnasium import spaces
import numpy as np
import jax
import jax.numpy as jnp
from camar import camar_v0
from camar.maps.utils import perlin_noise_vectorized


class CamarGymWrapper(gym.Env):
    """Обёртка CAMAR для Gymnasium: адаптирует JAX-среду под интерфейс SB3"""

    def __init__(self, seed=0, obstacle_density=0.2, action_scale=1.0,
                 frameskip=1, goal_reward=1.0, collision_penalty=0.3,
                 grid_size=10, max_steps=100,
                 max_speed=50.0, accel=40.0, damping=0.6, dt=0.03,
                 terrain_penalty=0.3, step_penalty=0.0):
        super().__init__()
        self._min_dist = float('inf')
        self.goal_reward = goal_reward
        self.collision_penalty = collision_penalty
        self.step_penalty = step_penalty
        self.terrain_penalty = terrain_penalty
        self.grid_size = grid_size
        self._cached_render = None
        self.terrain_map = None
        self.goal_count = 0
        self.collision_count = 0

        self.env = camar_v0(
            map_generator="random_grid",
            map_kwargs={
                "num_agents": 1,
                "num_rows": grid_size,
                "num_cols": grid_size,
                "obstacle_density": obstacle_density,
                "goal_rad_range": (0.3, 0.3)
            },
            dynamic_kwargs={
                "max_speed": max_speed * action_scale,
                "accel": accel,
                "damping": damping,
                "dt": dt,
            },
            frameskip=frameskip,
            max_steps=max_steps
        )
        self.key = jax.random.PRNGKey(seed)
        self.state = None
        self.fixed_reset_key = None

        self._jit_step = jax.jit(self.env.step)
        self._jit_reset = jax.jit(self.env.reset)

        obs_dim = self.env.observation_size
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=(obs_dim,), dtype=np.float32)
        self.action_space = spaces.Box(-1.0, 1.0, shape=(2,), dtype=np.float32)

    def _generate_terrain(self):
        """Генерация карты рельефа через шум Перлина"""
        self.key, subkey = jax.random.split(self.key)
        res = self.grid_size * 4
        noise = perlin_noise_vectorized(subkey, res, res, 4, 4)
        noise = jnp.abs(noise)
        noise = (noise - noise.min()) / (noise.max() - noise.min() + 1e-8)
        self.terrain_map = np.array(noise).tolist()

    def reset(self, seed=None, **kwargs):
        """Сброс среды, фиксация сида"""
        if self.fixed_reset_key is None:
            self.key, subkey = jax.random.split(self.key)
            self.fixed_reset_key = subkey
        self._cached_render = None
        self._generate_terrain()
        obs, self.state = self._jit_reset(self.fixed_reset_key)
        return np.array(obs).flatten().astype(np.float32), {}

    def step(self, action):
        """Выполнение шага, формирование награды"""
        self.key, subkey = jax.random.split(self.key)
        action_jax = jnp.array(action.reshape(1, 2))
        self._cached_render = None
        obs, self.state, reward, done, info = self._jit_step(subkey, self.state, action_jax)
        render = self.get_render_state()

        on_goal = bool(np.array(self.state.on_goal).any())
        is_collision = bool(np.array(self.state.is_collision).any())

        r = float(np.array(reward).sum())

        if render.get("is_collision"):
            r -= self.collision_penalty

        r -= self.step_penalty

        if on_goal:
            r += self.goal_reward
            self.goal_count += 1

        d = bool(np.array(done).any())

        return np.array(obs).flatten().astype(np.float32), r, d, False, {
            "on_goal": on_goal,
            "is_collision": is_collision,
        }

    def get_terrain_map(self):
        return self.terrain_map

    def get_render_state(self):
        if self._cached_render is not None:
            return self._cached_render
        if self.state is None:
            return {}
        self._cached_render = {
            "agent_pos": np.array(self.state.physical_state.agent_pos).tolist(),
            "goal_pos": np.array(self.state.goal_pos).tolist(),
            "landmark_pos": np.array(self.state.landmark_pos).tolist(),
            "is_collision": bool(np.array(self.state.is_collision).any()),
            "on_goal": bool(np.array(self.state.on_goal).any()),
        }
        return self._cached_render