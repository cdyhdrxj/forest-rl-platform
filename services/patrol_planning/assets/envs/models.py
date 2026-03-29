from pydantic import BaseModel, Field
from services.patrol_planning.assets.agents.models import AgentConfig
from services.patrol_planning.assets.intruders.models import IntruderConfigType, WandererConfig
from services.patrol_planning.assets.observations.models import ObservationConfigType, ObsBoxConfig
from typing import List, Optional


class GridWorldStepImage(BaseModel):
    pass


class GridWorldConfig(BaseModel):
    agent_config: AgentConfig = Field(
        default_factory=AgentConfig,
        description="Конфигурация агента GridWorld",
    )

    intruder_config: List[IntruderConfigType] = Field(
        default_factory=lambda: [WandererConfig()],
        description="Список с конфигурациями нарушителей",
    )

    obs_config: ObservationConfigType = Field(
        default_factory=ObsBoxConfig,
        description="Конфигурация наблюдения",
    )

    max_steps: int = Field(
        default=50,
        description="Длина эпизода патрулирования в шагах",
    )

    grid_size: int = Field(
        default=20,
        description="Длина стороны сеточного мира в ячейках",
    )

    seed: Optional[int] = Field(
        default=None,
        description="Seed для генерации сценария",
    )

    terrain_hilliness: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="Интенсивность неровностей terrain layer",
    )
