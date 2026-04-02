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

import sys
import os, json

# Абсолютный путь до корня проекта (где лежит environment, observations и т.д.)
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)

# Добавляем в sys.path, если ещё нет
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.patrol_planning.assets.intruders.models import PoacherConfig
from services.patrol_planning.assets.observations.models import ObsBoxConfig
from services.patrol_planning.assets.envs.models import GridWorldConfig, GridForestConfig

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

## ССтандартная модель для лесного массива
config = GridForestConfig()
p_config = PoacherConfig()
o_config = ObsBoxConfig()
o_config.size = 4
o_config.layers_count = 4
p_config.pos = [5,5]
config.intruder_config = [p_config]
config.obs_config = o_config
config.grid_size = 8
with open(
    "services/patrol_planning/learning/configs/FOREST_DEFAULT.json",
    "w",
    encoding="utf-8"
) as f:
    f.write(config.model_dump_json(indent=2))