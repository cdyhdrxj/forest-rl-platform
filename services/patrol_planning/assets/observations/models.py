from pydantic import BaseModel, Field
from typing import List

class ObservationConfig(BaseModel):
    """Конфигурация базовой области наблюдения для GridWorld"""
    size: int = Field(
        default= 3,
        description= "Размер области наблюдения"
    )

class ObsBoxConfig(ObservationConfig):
    layers_count: int = Field(
        default= 2,
        description= "Число слоёв"
    )