from __future__ import annotations
from typing import List, Optional
from pydantic import Field
from services.patrol_planning.src.dict_like import DictLikeModel
import numpy as np


class GridWorldTrainState(DictLikeModel):
    """TrainState для GridWorld"""
    
    model_config = {
        "arbitrary_types_allowed": True
    }
        
    def reset_counters(self):
        self.episode = 0
        self.step = 0
        self.total_reward = 0.0
        self.last_episode_reward = 0.0
        self.new_episode = False
        self.goal_count = 0
        self.collision_count = 0
        self.trajectory = []
        self.terrain_map = None
        
    #Параметры, обновляемые средой
    agent_pos: List[List[float]] = Field(
        default_factory= lambda: [[0.0,0.0]],
        description="Позиция агента [[x, y]]"
    )

    goal_pos: List[List[float]] = Field(
        default_factory= lambda: [[0.0,0.0]],
        description="Позиция цели [[x, y]]"
    )
    
    trajectory: List[List[float]] = Field(
        default_factory=list,
        description="Путь агента"
    )
    
    step: int = Field(
        default=0,
        description="Счетчик шагов внутри эпизода"
    )

    total_reward: float = Field(
        default=0.0,
        description="Накопленная награда за текущий эпизод"
    )
    
    episode: int = Field(
        default=0,
        description="Номер текущего эпизода"
    )
    
    last_episode_reward: float = Field(
        default=0.0,
        description="Награда за предыдущий эпизод"
    )
    
    new_episode: bool = Field(
        default=False,
        description="Флаг начала нового эпизода"
    )
    
    i_count: int = Field(
        default=1,
        description="Число не пойманных нарушителей"
    )
    
    obs_raw: np.ndarray | None  = Field(
        default= None,
        description= "Данные области наблюдения агента"
    )

    #Параметры, не обновляемые/не используемые средой
    running: bool = Field(
        default=False,
        description="Флаг выполнения обучения"
    )

    mode: str = Field(
        default="trail",
        description="Режим работы"
    )

    landmark_pos: List[List[float]] = Field(
        default_factory=list,
        description="Позиции препятствий"
    )

    is_collision: bool = Field(
        default=False,
        description="Флаг столкновения"
    )

    goal_count: int = Field(
        default=0,
        description="Сколько раз агент достиг цели за эпизод"
    )

    collision_count: int = Field(
        default=0,
        description="Сколько столкновений за эпизод"
    )

    terrain_map: Optional[List[List[float]]] = Field(
        default=None,
        description="Карта рельефа [[float,...],...], значения 0..1 размер grid_size×grid_size"
    )
    

    