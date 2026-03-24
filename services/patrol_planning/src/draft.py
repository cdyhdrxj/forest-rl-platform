# from __future__ import annotations

# import gymnasium as gym
# from gymnasium import spaces
# import numpy as np
# from typing import List, Type

# import copy
# import time

# from services.patrol_planning.assets.envs.models import GridWorldConfig
# from services.patrol_planning.service.models import GridWorldTrainState
# from services.patrol_planning.assets.agents.models import AgentConfig
# from services.patrol_planning.assets.observations.models import ObsBoxConfig
# from services.patrol_planning.assets.intruders.models import PoacherConfig, ControllableConfig, WandererConfig
# from services.patrol_planning.service.models import GridWorldTrainState


# ##Настроенные модели сред

# wanderer = PoacherConfig()
# wanderer.pos = [1,1]
# wanderer.is_random_spawned = True

# controlable = PoacherConfig()
# controlable.pos = [2,2]
# controlable.is_random_spawned = True

# agent = AgentConfig()
# agent.pos = [4,4]
# agent.is_random_spawned = False

# obs = ObsBoxConfig()
# obs.size = 4

# GW_DEFAULT = GridWorldConfig()
# GW_DEFAULT.grid_size = 8
# GW_DEFAULT.obs_config = obs
# GW_DEFAULT.agent_config = agent
# GW_DEFAULT.intruder_config = [controlable, wanderer]
# GW_DEFAULT.max_steps = 150

# GW_STATE_DEFAULT = GridWorldTrainState()