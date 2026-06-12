from __future__ import annotations
import gymnasium as gym
from gymnasium import spaces
import numpy as np
from .obs import Observation

from services.patrol_planning.assets.agents.agent import GridWorldAgent
from services.patrol_planning.assets.observations.models import ObsBoxConfig

class ObservationBox(Observation):
    """Custom observation handler for the forest patrol environment."""

    def __init__(self, obs_size=10, layers_count: int = 2,
                 max_value: float = 1000.0, max_steps: int = 250, grid_size: int = 20,
                 exclude_layers: list[str] | None = None, oob_value: float = -1.0):
        super().__init__(obs_size)
        self.layers_count = layers_count
        self.max_value = max_value
        self.max_steps = max_steps
        self.grid_size = grid_size
        self.exclude_layers: set[str] = set(exclude_layers) if exclude_layers else set()
        self.oob_value = oob_value

        # Предвыделенный буфер: избавляет от np.stack + np.pad в горячем пути
        self._build_buf: np.ndarray | None = None

        self.space = spaces.Box(
            low=-1.0,
            high=1.0,
            shape=self.get_obs_shape(),
            dtype=np.float32
        )


    def build_observation(self, layers: dict, agent: GridWorldAgent):
        """
        Построить локальное наблюдение вокруг агента.

        layers: dict[str, np.ndarray] — словарь слоёв карты
        agent: агент с полями x, y

        Оптимизация: предвыделенный буфер (C, obs_size, obs_size) заполняется
        прямыми срезами без np.stack и np.pad.
        """
        # Фильтруем исключённые слои — один раз за вызов
        if self.exclude_layers:
            items = [(k, v) for k, v in layers.items() if k not in self.exclude_layers]
        else:
            items = list(layers.items())

        names  = [k for k, _ in items]
        arrays = [v for _, v in items]

        x, y = agent.x, agent.y
        half  = self.obs_size // 2
        wsize = 2 * half + 1   # реальный размер окна: для obs_size=10 → 11, для 5 → 5

        size_x, size_y = arrays[0].shape

        # Границы окна на карте (глобальные координаты)
        gx_start = max(0, x - half)
        gx_stop  = min(size_x, x + half + 1)
        gy_start = max(0, y - half)
        gy_stop  = min(size_y, y + half + 1)

        # Позиции вставки в буфере (куда пишем данные карты)
        bx_start = max(0, half - x)
        by_start = max(0, half - y)
        bx_stop  = bx_start + (gx_stop - gx_start)
        by_stop  = by_start + (gy_stop  - gy_start)

        # Lazy-init буфера: размер wsize, а не obs_size (они совпадают для нечётных,
        # но расходятся для чётных: obs_size=10 → wsize=11)
        C = len(arrays)
        if self._build_buf is None or self._build_buf.shape[0] != C:
            self._build_buf = np.empty((C, wsize, wsize), dtype=np.float32)

        # Заполняем весь буфер oob_value, затем перезаписываем in-bounds область
        self._build_buf.fill(self.oob_value)

        for i, (name, arr) in enumerate(zip(names, arrays)):
            # Прямая запись среза — ни np.stack, ни np.pad не нужны
            self._build_buf[i, bx_start:bx_stop, by_start:by_stop] = \
                arr[gx_start:gx_stop, gy_start:gy_stop]

            # Нормировка in-place только над in-bounds прямоугольником
            ib = self._build_buf[i, bx_start:bx_stop, by_start:by_stop]
            match name:
                case "rows" | "cols":
                    ib /= max(self.grid_size - 1, 1)
                case "value":
                    ib /= self.max_value
                case "idleness":
                    ib /= self.max_steps
                # passability, intruders, terrain: уже в [0, 1], не трогаем

        return self._build_buf.copy()  # (C, obs_size, obs_size)

    def get_obs_shape(self):
        """
        Получить shape
        """

        #Создаём двумерный слой размером с наблюдение
        layer = np.zeros((self.obs_size, self.obs_size))

        #Формируем входные данные для функции
        layers = {f"layer_{i}": layer.copy() for i in range(self.layers_count)}

        obs = self.build_observation(layers, GridWorldAgent(0, 0))
        return obs.shape

    @staticmethod
    def load(config: ObsBoxConfig) -> ObservationBox:
        """
        Создать экземпляр ObservationBox из конфигурации.

        Args:
            config: конфигурация ObservationBox

        Returns:
            ObservationBox: настроенный экземпляр
        """
        return ObservationBox(
            obs_size=config.size,
            layers_count=config.layers_count,
            max_value=config.max_value,
            max_steps=config.max_steps,
            grid_size=config.grid_size,
            exclude_layers=config.exclude_layers,
            oob_value=config.oob_value,
        )
