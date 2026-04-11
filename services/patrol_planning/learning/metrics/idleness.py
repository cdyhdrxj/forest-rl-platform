from __future__ import annotations

import numpy as np
from typing import Tuple, Dict, Any

class IdlenessMetric:
    """
    Хранит моменты посещения каждой ячейки и вычисляет метрику idleness.
    """

    def __init__(self, env):
        
        #Получаем информацию о размерах территории
        i = env.world_layers['intruders']
        rows, cols = len(i), len(i[0])
        
        self.height = rows
        self.width = cols

        # 2D карта списков моментов посещения
        self.visit_times = [
            [list() for _ in range(self.width)]
            for _ in range(self.height)
        ]
        
    def reset(self):
        """
        Сброс состояния для нового эпизода
        """
        self.visit_times = [
            [list() for _ in range(self.width)]
            for _ in range(self.height)
        ]

    def update(
        self,
        observation: np.ndarray,
        agent_pos: Tuple[int, int],
        step: int,
    ):
        #Shape должен быть с формате: сhannels height with
        obs_h, obs_w = observation.shape[1:3]

        ay, ax = agent_pos

        offset_y = obs_h // 2
        offset_x = obs_w // 2

        for dy in range(obs_h):
            for dx in range(obs_w):

                gy = ay + (dy - offset_y)
                gx = ax + (dx - offset_x)

                if 0 <= gy < self.height and 0 <= gx < self.width:
                    self.visit_times[gy][gx].append(step)

    def calculate_metric(self, episode_length: int) -> Dict[str, Any]:
        """
        episode_length — T (длина эпизода)

        Возвращает:
            max
            mean
            map
        """

        interval_map = np.zeros((self.height, self.width), dtype=float)

        for y in range(self.height):
            for x in range(self.width):

                times = self.visit_times[y][x]

                if not times:
                    # никогда не посещалась → вся длительность эпизода
                    interval_map[y, x] = episode_length
                    continue

                intervals = []

                # первый интервал (от начала эпизода)
                prev = 0
                for t in times:
                    intervals.append(t - prev)
                    prev = t

                # хвост до конца эпизода
                intervals.append(episode_length - times[-1])

                interval_map[y, x] = float(np.mean(intervals))

        return {
            "max": float(np.max(interval_map)),
            "mean": float(np.mean(interval_map)),
            "map": interval_map,
        }