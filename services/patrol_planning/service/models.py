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
        self.trajectory = []
        self.catch_latency = []
        self.total_damage = 0
        
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
    
    catch_latency: List[int] = Field(
        default_factory=list,
        description="Среднее время между появлением и поимкой нарушителя"
    )
    
    step: int = Field(
        default=0,
        description="Счетчик шагов внутри эпизода"
    )

    total_reward: float = Field(
        default=0.0,
        description="Накопленная награда за текущий эпизод"
    )
     
    total_damage: float = Field(
        default=0.0,
        description="Ущерб, нанесённый нарушителями за текущий эпизод"
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
    
    world_layers: dict | None  = Field(
        default= None,
        description= "Зона патрулирования (послойно). Ключи: \
        intruders - нарушители, rows - индексы строк, cols -индексы столбцов, passability - проходимость, value - ценность"
    )

    #Параметры, не обновляемые/не используемые средой
    running: bool = Field(
        default=False,
        description="Флаг выполнения обучения"
    )

    mode: str = Field(
        default="patrol",
        description="Режим работы"
    )

    

    