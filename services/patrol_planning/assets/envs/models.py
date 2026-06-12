from pydantic import BaseModel, Field, model_validator
from services.patrol_planning.assets.agents.models import AgentConfig
from services.patrol_planning.assets.intruders.models import IntruderConfigType, WandererConfig, ControllableConfig, PoacherSimpleConfig
from services.patrol_planning.assets.observations.models import ObservationConfigType, ObsBoxConfig
from services.patrol_planning.assets.rewards.reward_config import RewardConfig
from services.patrol_planning.learning.metrics.metrics_config import MetricsConfig
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


class LoadLayersConfig(BaseModel):
    """Пути к CSV-файлам для загрузки слоёв карты."""

    passability: str = Field(
        description="Путь к CSV-файлу с картой проходимости (матрица grid_size×grid_size)"
    )

    value: str = Field(
        description="Путь к CSV-файлу с картой ценности (матрица grid_size×grid_size)"
    )


class GridForestConfig(GridWorldConfig):
    """Конфигурация лесной среды GridForest."""

    reward_config: RewardConfig = Field(
        default_factory=RewardConfig,
        description="Конфигурация системы наград (веса компонентов, штрафы)"
    )

    metrics_config: MetricsConfig = Field(
        default_factory=MetricsConfig,
        description="Конфигурация метрик задачи (веса Z(π) = w1·M_damage + w2·M_move + w3·M_idleness)"
    )

    intruder_config: List[IntruderConfigType] = Field(
        default_factory=lambda: [PoacherSimpleConfig()],
        description="Список с конфигурациями нарушителей (по умолчанию — Poacher)"
    )
    
    mu_min: float = Field(
        default=0.9,
        description="Минимальная проходимость граничной клетки для спавна и выхода нарушителей"
    )

    max_intruders: int = Field(
        default=-1,
        description="Макс. число нарушителей за эпизод: -1 = без ограничений, 0 = нет, >0 = не более K"
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

    random_map: bool = Field(
        default=False,
        description="Генерировать новую случайную карту при каждом reset() (seed игнорируется)"
    )

    load_layers: Optional[LoadLayersConfig] = Field(
        default=None,
        description=(
            "Загрузить passability и value из CSV-файлов вместо процедурной генерации. "
            "Несовместимо с random_map=True."
        )
    )

    continue_until_max_steps: bool = Field(
        default=False,
        description=(
            "Не завершать эпизод досрочно при поимке/выходе всех запланированных нарушителей; "
            "ждать до истечения max_steps (truncated)."
        )
    )

    @model_validator(mode="after")
    def _check_load_layers_vs_random_map(self) -> "GridForestConfig":
        if self.load_layers is not None and self.random_map:
            raise ValueError(
                "load_layers и random_map=True несовместимы: "
                "нельзя одновременно загружать карту из файлов и генерировать случайную"
            )
        return self

