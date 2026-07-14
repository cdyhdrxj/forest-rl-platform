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
        default=2,
        description="Число слоёв"
    )
    max_value: float = Field(
        default=1000.0,
        description="Максимальная ценность клетки (для нормировки слоя value)"
    )
    max_steps: int = Field(
        default=250,
        description="Горизонт планирования T (для нормировки слоя idleness)"
    )
    grid_size: int = Field(
        default=20,
        description="Размер сетки (для нормировки слоёв rows/cols)"
    )
    exclude_layers: List[str] = Field(
        default_factory=list,
        description="Ключи слоёв, которые исключаются из тензора наблюдений"
    )
    oob_value: float = Field(
        default=-1.0,
        description="Значение для out-of-bounds ячеек (для CNN используй 0.0)"
    )


ObservationConfigType = Annotated[
    ObsBoxConfig,
    Field(discriminator="type")
]