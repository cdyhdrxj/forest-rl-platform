from pydantic import BaseModel, Field
from typing import List

from typing import Annotated
from pydantic import Field
from typing import Literal

class IntruderConfig(BaseModel):
    """Конфигурация базового нарушителя GridWorld"""
    type: Literal["default"] = "default"
    
    pos: List[int] = Field(
        default= [0,0],
        description= "Текущая позиция нарушителя в среде"
    )
    is_random_spawned: bool = Field(
        default=False,
        description="При каждом сбросе среды (reset), "
                    "если True, нарушитель случайным образом размещается в среде"
    )
    manual_spawn: bool = Field(
        default=False,
        description="True — спавн в момент incoming_moment в позицию pos (ручной). "
                    "False — время и позиция назначаются планировщиком случайно."
    )
    catch_reward: float = Field(
        default= 1.0,
        description= "Награда агенту за поимку"
    )
    
class ControllableConfig(IntruderConfig):
    """Конфигурация управляемого нарушителя GridWorld"""
    type: Literal["controllable"] = "controllable"
    pass

class WandererConfig(IntruderConfig):
    """Конфигурация блуждающего нарушителя GridWorld"""
    type: Literal["wanderer"] = "wanderer"
    pass

class PoacherConfig(IntruderConfig):
    """Конфигурация нарушителя-браконьера GridWorld"""
    type: Literal["poacher"] = "poacher"
    
    m_plan: float = Field(
        default=100.0,
        description="Размер ущерба, который браконьер должен причинить вырубкой"
    )
    m_defence: float = Field(
        default=1.5,
        description="Множитель награды за предотвращённый ущерб"
    )
    felling_intensity: float = Field(
        default=100.0,
        description="Интенсивность вырубки"
    )

    incoming_moment: int = Field(
        default=10,
        description="Шаг появления. -1 — выбирается случайно из "
                    "[incoming_patience, max_steps - incoming_patience]"
    )

    
class PoacherSimpleConfig(IntruderConfig):
    """Конфигурация нарушителя-браконьера GridWorld"""
    type: Literal["poacher_simple"] = "poacher_simple"

    m_plan: float = Field(
        default=100.0,
        description="Размер ущерба, который браконьер должен причинить вырубкой"
    )
    m_defence: float = Field(
        default=1.5,
        description="Множитель награды за предотвращённый ущерб"
    )
    m_tool_power: float = Field(
        default=100.0,
        description="Мощность инструмента браконьера"
    )
    search_patience: int = Field(
        default=50,
        description="Терпение при поиске цели"
    )
    
    incoming_moment: int = Field(
        default=10,
        description="Шаг появления. -1 — выбирается случайно из "
                    "[incoming_patience, max_steps - incoming_patience]"
    )
    

class PoacherAltConfig(IntruderConfig):
    """Конфигурация нарушителя-браконьера PoacherAlt (без search_patience, с N ближайших целей)"""
    type: Literal["poacher_alt"] = "poacher_alt"

    m_plan: float = Field(
        default=100.0,
        description="Размер ущерба, который браконьер должен причинить вырубкой"
    )
    m_tool_power: float = Field(
        default=100.0,
        description="Мощность инструмента браконьера"
    )
    n_targets: int = Field(
        default=1,
        description="Размер пула ближайших целей для случайного выбора. 1 = всегда ближайшая"
    )
    use_idleness_targeting: bool = Field(
        default=False,
        description="Если True, выбирает ближайшую из топ-N клеток по score=value×idleness "
                    "(ценные и давно не посещённые агентом). Если False — N ближайших со случайным выбором."
    )
    use_passability_routing: bool = Field(
        default=False,
        description="Если True, стоимость ребра в A* = 1/passability: браконьер ищет маршрут "
                    "с максимальной проходимостью, избегая труднопроходимых клеток. "
                    "Если False — кратчайший путь по числу шагов."
    )

    incoming_moment: int = Field(
        default=10,
        description="Шаг появления. -1 — выбирается случайно"
    )


IntruderConfigType = Annotated[
    ControllableConfig | WandererConfig | PoacherConfig | PoacherSimpleConfig | PoacherAltConfig,
    Field(discriminator="type")
]




