from __future__ import annotations

import numpy as np
from typing import Tuple, Dict, Any

class IdlenessMetric:
    """
    Хранит моменты посещения каждой ячейки и вычисляет метрику idleness.
    Также ведёт оперативную карту простоя ℓ_ij,t — время с последней проверки.
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

        # Карта простоя: сколько шагов прошло с момента последней проверки ячейки
        self.staleness_map = np.zeros((self.height, self.width), dtype=np.float32)

    def reset(self):
        """
        Сброс состояния для нового эпизода
        """
        self.visit_times = [
            [list() for _ in range(self.width)]
            for _ in range(self.height)
        ]

        # Сбрасываем карту простоя: каждый новый эпизод начинается с нулей
        self.staleness_map = np.zeros((self.height, self.width), dtype=np.float32)

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

        # Вычисляем границы один раз, убираем проверку внутри цикла
        gy_start = max(0, ay - offset_y)
        gy_stop  = min(self.height, ay - offset_y + obs_h)
        gx_start = max(0, ax - offset_x)
        gx_stop  = min(self.width,  ax - offset_x + obs_w)

        for gy in range(gy_start, gy_stop):
            for gx in range(gx_start, gx_stop):
                self.visit_times[gy][gx].append(step)

    def increment_staleness(self):
        """Увеличивает простой всех ячеек на один шаг (без сброса видимых)."""
        self.staleness_map += 1.0

    def reset_visible(
        self,
        observation: np.ndarray,
        agent_pos: Tuple[int, int],
    ):
        """
        Сбрасывает простой ячеек, попавших в текущую область видимости, в ноль.

        observation — текущее наблюдение формата (channels, height, width)
        agent_pos   — (x, y) позиция агента в глобальных координатах
        """
        obs_h, obs_w = observation.shape[1:3]
        ay, ax = agent_pos
        offset_y = obs_h // 2
        offset_x = obs_w // 2

        # Один numpy-срез вместо Python double-loop (obs_h × obs_w итераций)
        gy_start = max(0, ay - offset_y)
        gy_stop  = min(self.height, ay - offset_y + obs_h)
        gx_start = max(0, ax - offset_x)
        gx_stop  = min(self.width,  ax - offset_x + obs_w)

        self.staleness_map[gy_start:gy_stop, gx_start:gx_stop] = 0.0

    def update_staleness(
        self,
        observation: np.ndarray,
        agent_pos: Tuple[int, int],
    ):
        """
        Обновляет карту простоя по правилу:
            ℓ_ij,t+1 = 0,           если v_ij ∈ V_t^obs (ячейка в поле зрения агента)
            ℓ_ij,t+1 = ℓ_ij,t + 1,  иначе

        observation — текущее наблюдение формата (channels, height, width)
        agent_pos   — (x, y) позиция агента в глобальных координатах
        """
        self.increment_staleness()
        self.reset_visible(observation, agent_pos)

    def get_staleness_layer(self) -> np.ndarray:
        """Возвращает копию текущей карты простоя."""
        return self.staleness_map.copy()

    def calculate_metric(self, episode_length: int, cell_mask: "np.ndarray | None" = None) -> Dict[str, Any]:
        """
        episode_length — T (длина эпизода)
        cell_mask      — булева маска (height, width); если задана, max/mean считаются
                         только по ячейкам где mask=True. map всегда полный.

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

        if cell_mask is not None and cell_mask.any():
            relevant = interval_map[cell_mask]
        else:
            relevant = interval_map.ravel()

        return {
            "max": float(relevant.max()),
            "mean": float(relevant.mean()),
            "map": interval_map,
        }