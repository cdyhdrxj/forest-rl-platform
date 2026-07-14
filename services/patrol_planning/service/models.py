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
        """Полный сброс — вызывается при старте нового обучения."""
        self.episode = 0
        self.step = 0
        self.total_reward = 0.0
        self.last_episode_reward = 0.0
        self.new_episode = False
        self.trajectory = []
        self.catch_latency = []
        self.total_damage = 0
        self.train_metrics = None
        self.val_metrics = None
        self.val_step = 0

    def reset_per_episode(self):
        """Сброс внутри-эпизодных счётчиков — вызывается в env.reset()."""
        self.step = 0
        self.total_reward = 0.0
        self.new_episode = False
        self.trajectory = []
        self.catch_latency = []
        self.total_damage = 0
        # episode, last_episode_reward, train_metrics, val_metrics сохраняются
        
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

    episode_metrics: dict | None = Field(
        default=None,
        description="Метрики задачи за последний завершённый эпизод: M_damage, M_move, M_idleness, idleness_max, Z"
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

    train_metrics: dict | None = Field(
        default=None,
        description="Метрики обучения: fps, ep_rew_mean, ep_len_mean, global_step"
    )

    val_metrics: dict | None = Field(
        default=None,
        description="Метрики последней валидации: total_reward, metric_Z, metric_M_idleness, etc."
    )

    val_step: int = Field(
        default=0,
        description="Глобальный шаг обучения, на котором проводилась последняя валидация"
    )

    step_delay: float = Field(
        default=0.0,
        description="Задержка после каждого шага среды в секундах (режим визуализации)"
    )

    visualize: bool = Field(
        default=False,
        description="Режим визуализации: True = визуальные данные (agent_pos, trajectory, world_layers) пишутся в train_state"
    )



    