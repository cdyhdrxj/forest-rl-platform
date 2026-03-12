import numpy as np
from rich.live import Live
from rich.table import Table
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align

console = Console()


class GridWorldRendererExt:

    def __init__(self, env):
        self.env = env
        self.live = Live(console=console, refresh_per_second=8)

    def render(self):

        size = self.env.grid_world_size

        table = Table(
            show_header=False,
            show_lines=False,
            padding=(0, 1),
            box=None
        )

        for _ in range(size):
            table.add_column(justify="center")

        agent = self.env.agent
        ax = agent.x
        ay = agent.y

        # получаем реальное observation
        obs = self.env.obs.build_observation(self.env.word_layers, agent)

        obs_size = obs.shape[1]  # H
        half = obs_size // 2

        # создаём маску видимых клеток
        visible = set()

        for ox in range(obs_size):
            for oy in range(obs_size):

                wx = ax - half + ox
                wy = ay - half + oy

                if 0 <= wx < size and 0 <= wy < size:
                    visible.add((wx, wy))

        for x in range(size):

            row = []

            for y in range(size):

                # проверяем входит ли клетка в observation
                if (x, y) in visible:
                    cell = Text(".", style="bold yellow")
                else:
                    cell = Text(".", style="dim")

                # агент
                if x == ax and y == ay:
                    cell = Text(agent.get_symbol(), style="bold bright_cyan")

                # нарушители
                for intruder in self.env.intruders:
                    if intruder.x == x and intruder.y == y:
                        cell = Text(intruder.get_symbol(), style="bold red")

                row.append(cell)

            table.add_row(*row)

        hud = Text()
        hud.append(" GRIDWORLD ", style="bold yellow")
        hud.append(" | ")
        hud.append(f"Intruders: {len(self.env.intruders)} ", style="red")
        hud.append("| ")
        hud.append(f"Agent: ({ax},{ay}) ", style="cyan")
        hud.append("| ")
        hud.append(f"Obs shape: {obs.shape}", style="bold yellow")

        panel = Panel(
            Align.center(table),
            title=hud,
            border_style="bright_magenta"
        )

        return panel