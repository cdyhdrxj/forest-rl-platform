from pydantic import BaseModel, Field
from typing import List, Literal

class AgentConfig(BaseModel):
    """Конфигурация базового агента GridWorld"""
    type: Literal["default"] = "default"
    
    pos: List[int] = Field(
        default= [0,0],
        description= "Текущая позиция агента в среде"
    )
    is_random_spawned: bool = Field(
        default= False,
        description= "При каждом сбросе среды (reset) \
        агент случайным образом размещается в среде"
    )
    


