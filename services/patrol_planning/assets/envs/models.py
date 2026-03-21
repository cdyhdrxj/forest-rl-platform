from pydantic import BaseModel, Field
from services.patrol_planning.assets.agents.models import AgentConfig
from services.patrol_planning.assets.intruders.models import IntruderConfig, WandererConfig, ControllableConfig
from services.patrol_planning.assets.observations.models import ObservationConfig, ObsBoxConfig
from typing import List

class GridWorldConfig(BaseModel):
    agent_config: AgentConfig = Field(
        default= AgentConfig(),
        description= "Конфигурация агента GridWorld"
    )
    
    intruder_config: List[IntruderConfig] = Field(
        default= [IntruderConfig()],
        description= "Список с конфигурациями нарушителей"
    )
    
    obs_config: ObservationConfig = Field(
        default= ObservationConfig(),
        description= "Конфигурация наблюдения"
    )
    
    max_steps: int = Field(
        default= 50,
        description= "Длина эпизода патрулирования, (сколько шагов до сброса среды)"
    )
    
    grid_size: int = Field(
        default= 20,
        description= "Длина стороны сеточного мира в ячейках"
    )
    
##Настроенные модели сред

wanderer = WandererConfig()
wanderer.pos = [1,1]
wanderer.is_random_spawned = True

controlable = ControllableConfig()
controlable.pos = [1,1]
controlable.is_random_spawned = True

agent = AgentConfig()
agent.pos = [4,4]
agent.is_random_spawned = False

obs = ObsBoxConfig()
obs.size = 4

GW_DEFAULT = GridWorldConfig()
GW_DEFAULT.grid_size = 8
GW_DEFAULT.obs_config = obs
GW_DEFAULT.agent_config = agent
GW_DEFAULT.intruder_config = [controlable, wanderer]
GW_DEFAULT.max_steps = 150




    
    