from rich.live import Live
from rich.console import Console
import numpy as np
import time

console = Console()

class GridWorldRenderer:
    def __init__(self, env):
        self.env = env
        self.live = Live(console=console, refresh_per_second=5)  # 5 FPS

    def render(self):
        """
        Рендер сетки в консоль через rich.Live.
        Агент: "A"
        Нарушители: символ из intruder.get_symbol()
        Пустые клетки: "."
        """
        # создаём пустую сетку
        grid_world = np.full((self.env.grid_world_size, self.env.grid_world_size), ".")

        # рисуем агента
        agent = self.env.agent
        
        ax = agent.x
        ay = agent.y
        
        grid_world[ax, ay] = agent.get_symbol()

        # рисуем нарушителей
        for intruder in self.env.intruders:
            if 0 <= intruder.x < self.env.grid_world_size and 0 <= intruder.y < self.env.grid_world_size:
                grid_world[intruder.x, intruder.y] = intruder.get_symbol()

        # создаём текст для вывода
        grid_text = "\n".join(" ".join(row) for row in grid_world)

        return grid_text  # возвращаем строку для Live.update()