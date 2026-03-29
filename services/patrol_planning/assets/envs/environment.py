from __future__ import annotations

import copy
import time
from typing import List

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from services.patrol_planning.assets.agents.agent import GridWorldAgent
from services.patrol_planning.assets.envs.models import GridWorldConfig
from services.patrol_planning.assets.intruders.controllable import Controllable
from services.patrol_planning.assets.intruders.models import WandererConfig
from services.patrol_planning.assets.intruders.wanderer import Wanderer
from services.patrol_planning.assets.observations.obs_box import ObservationBox
from services.patrol_planning.service.models import GridWorldTrainState


class GridWorld(gym.Env):
    """Grid-based patrol environment."""

    def __init__(
        self,
        agent: GridWorldAgent,
        obs_model,
        grid_world_size: int = 20,
        intruders: List = [],
        max_steps: int = 50,
        static_layers: dict[str, np.ndarray] | None = None,
    ):
        self.grid_world_size = grid_world_size
        self.word_layers = {
            "terrain": np.zeros((grid_world_size, grid_world_size), dtype=np.float32),
            "intruders": np.zeros((grid_world_size, grid_world_size), dtype=np.float32),
        }
        self.agent = agent
        self.intruders_start = copy.deepcopy(intruders)
        self.intruders = copy.deepcopy(intruders)
        self.action_space = spaces.Discrete(len(agent.ACTIONS))
        self.obs = obs_model
        self.observation_space = self.obs.space
        self.max_steps = max_steps
        self.cur_step = 0
        self.static_layers = static_layers or {}

        self.renderer = None
        self.render_time_sleep = 0.0
        self.train_state: GridWorldTrainState | None = None

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.cur_step = 0

        terrain = self.static_layers.get("terrain")
        if terrain is None:
            terrain = np.zeros((self.grid_world_size, self.grid_world_size), dtype=np.float32)
        else:
            terrain = np.array(terrain, dtype=np.float32, copy=True)

        self.word_layers = {
            "terrain": terrain,
            "intruders": np.zeros((self.grid_world_size, self.grid_world_size), dtype=np.float32),
        }

        self.agent.reset(self)
        self.intruders = copy.deepcopy(self.intruders_start)
        for intruder in self.intruders:
            intruder.reset(self)

        observation = self.obs.build_observation(self.word_layers, self.agent)
        if self.train_state:
            self.train_state.terrain_map = self.word_layers["terrain"].tolist()
        return observation, {}

    def step(self, action):
        self.agent.step(self, action)

        reward = 0.0
        terminated = False
        truncated = False

        for intruder in list(self.intruders):
            reward += intruder.step(self)

        if len(self.intruders) == 0:
            terminated = True

        self.cur_step += 1
        if self.cur_step >= self.max_steps:
            truncated = True

        observation = self.obs.build_observation(self.word_layers, self.agent)
        info = {"intruders_left": len(self.intruders)}

        if self.renderer is not None:
            self.renderer.live.update(self.renderer.render())
            time.sleep(self.render_time_sleep)

        self.update_train_state(truncated, terminated, reward, observation)
        return observation, reward, terminated, truncated, info

    def update_train_state(self, truncated, terminated, reward, obs):
        if not self.train_state:
            return

        self.train_state.agent_pos = [[self.agent.x, self.agent.y]]
        self.train_state.trajectory.append([self.agent.x, self.agent.y])
        self.train_state.total_reward += reward
        self.train_state.obs_raw = obs
        self.train_state.terrain_map = self.word_layers["terrain"].tolist()

        goal_pos = []
        for intruder in self.intruders:
            goal_pos.append([intruder.x, intruder.y])
        self.train_state.goal_pos = goal_pos.copy()
        self.train_state.i_count = len(self.intruders)
        self.train_state.step += 1
        self.train_state.new_episode = truncated or terminated

        if truncated or terminated:
            self.train_state.episode += 1
            self.train_state.last_episode_reward = self.train_state.total_reward
            self.train_state.total_reward = 0.0
            self.train_state.trajectory = []

    @staticmethod
    def load(config: GridWorldConfig, static_layers: dict[str, np.ndarray] | None = None) -> "GridWorld":
        if not isinstance(config, GridWorldConfig):
            raise ValueError(f"Expected GridWorldConfig, got: {type(config)}")

        agent = GridWorldAgent.load(config.agent_config)

        match type(config.obs_config).__name__:
            case "ObsBoxConfig":
                obs_model = ObservationBox.load(config.obs_config)
            case _:
                raise ValueError(
                    f"Unsupported observation config type: {type(config.obs_config).__name__}"
                )

        intruders = []
        for intruder_config in config.intruder_config:
            match type(intruder_config).__name__:
                case "WandererConfig":
                    intruders.append(Wanderer.load(intruder_config))
                case "ControllableConfig":
                    intruders.append(Controllable.load(intruder_config))
                case "PoacherConfig":
                    intruders.append(Wanderer.load(WandererConfig()))
                case _:
                    raise ValueError(
                        f"Unsupported intruder config type: {type(intruder_config).__name__}"
                    )

        return GridWorld(
            agent=agent,
            obs_model=obs_model,
            grid_world_size=config.grid_size,
            intruders=intruders,
            max_steps=config.max_steps,
            static_layers=static_layers,
        )
