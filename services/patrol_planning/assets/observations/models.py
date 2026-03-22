from pydantic import BaseModel, Field
from typing import List

from typing import Annotated
from pydantic import Field
from typing import Literal

class ObservationConfig(BaseModel):
    """Конфигурация базовой области наблюдения для GridWorld"""
    type: Literal["default"] = "default"
    
    size: int = Field(
        default= 3,
        description= "Размер области наблюдения"
    )

class ObsBoxConfig(ObservationConfig):
    type: Literal["box"] = "box"
    
    layers_count: int = Field(
        default= 2,
        description= "Число слоёв"
    )
    
ObservationConfigType = Annotated[
    ObsBoxConfig,
    Field(discriminator="type")
]