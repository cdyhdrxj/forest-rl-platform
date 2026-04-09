from pydantic import BaseModel, Field
from services.patrol_planning.assets.agents.models import AgentConfig
from services.patrol_planning.assets.intruders.models import IntruderConfigType, WandererConfig, ControllableConfig, PoacherSimpleConfig
from services.patrol_planning.assets.observations.models import ObservationConfigType, ObsBoxConfig
from typing import List, Optional

class GridWorldStepImage(BaseModel):
    pass

class GridWorldConfig(BaseModel):
    agent_config: AgentConfig = Field(
        default_factory = AgentConfig,
        description= "Конфигурация агента GridWorld"
    )
    
    intruder_config: List[IntruderConfigType] = Field(
        default_factory= lambda: [WandererConfig()],
        description="Список с конфигурациями нарушителей"
    )
    
    obs_config: ObservationConfigType = Field(
        default_factory=ObsBoxConfig,
        description="Конфигурация наблюдения"
    )
    
    max_steps: int = Field(
        default= 50,
        description= "Длина эпизода патрулирования, (сколько шагов до сброса среды)"
    )
    
    grid_size: int = Field(
        default= 20,
        description= "Длина стороны сеточного мира в ячейках"
    )
    
    intruder_detection_reward: float = Field(
        default=1.0,
        description= "Награда за попадание нарушителя в область видимости (множитель)"
    )

    intruder_interception_reward: float = Field(
        default=1.5,
        description= "Награда за перехват нарушителя (множитель к несовершёному ущербу)"
    )


class GridForestConfig(GridWorldConfig):
    """Конфигурация лесной среды GridForest."""

    intruder_config: List[IntruderConfigType] = Field(
        default_factory=lambda: [PoacherSimpleConfig()],
        description="Список с конфигурациями нарушителей (по умолчанию — Poacher)"
    )
    
    #Параметры прихода нарушителей
    random_spawn_position: bool = Field(
        default=True,
        description="Игнорировать заданную позицию нарушителя и использовать случайную"
    )
    
    random_spawn_time: bool = Field(
        default=True,
        description="Игнорировать заданный момент прихода и использовать случайный"
    )
    
    tau_min: int = Field(
        default=5,
        description="Минимальная длина интервала появления"
    )
    
    tau_max: int = Field(
        default=10,
        description="Максимальная длина интервала появления"
    )

    #Параметры генерации карты
    map_seed: Optional[int] = Field(
        default=None,
        description="Зерно генератора карты (None — случайная карта)"
    )
    passability_low: float = Field(
        default=0.1,
        description="Минимальное значение проходимости для проходимых клеток"
    )
    passability_high: float = Field(
        default=1.0,
        description="Максимальное значение проходимости"
    )
    impassable_prob: float = Field(
        default=0.15,
        description="Вероятность того, что ячейка непроходима (μ = 0)"
    )
    max_value: float = Field(
        default=1000.0,
        description="Максимальная ценность ячейки"
    )
    value_density: float = Field(
        default=0.7,
        description="Доля проходимых клеток, имеющих ценность > 0"
    )
    




    
    