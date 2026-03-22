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
        default= False,
        description= "При каждом сбросе среды (reset), \
        если True, нарушитель случайным образом размещается в среде"
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

IntruderConfigType = Annotated[
    ControllableConfig | WandererConfig,
    Field(discriminator="type")
]




