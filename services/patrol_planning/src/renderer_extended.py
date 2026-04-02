import numpy as np
from rich.live import Live
from rich.table import Table
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align

console = Console()


def _value_style(norm: float, partial: bool) -> str:
    """
    Возвращает rich-стиль для ячейки с ценностью.

    Args:
        norm: Нормализованная ценность [0, 1].
        partial: True если μ < 1 (частично проходимая).
    """
    if partial:
        # Смешанный серо-зелёный — приглушённый оттенок
        if norm >= 0.8:
            return "bold green"
        elif norm >= 0.5:
            return "green"
        else:
            return "dim green"
    else:
        # Полностью проходимая — чистый зелёный с яркостью по норме
        if norm >= 0.8:
            return "bold bright_green"
        elif norm >= 0.5:
            return "green"
        else:
            return "dim green"


class GridWorldRendererExt:

    def __init__(self, env, debug_layer_enabled: bool = False, layer_key: str | None = None):
        self.env = env
        self.live = Live(console=console, refresh_per_second=8)

        # debug слой
        self.debug_layer_enabled = debug_layer_enabled
        self.layer_key = layer_key

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

        # Получаем лесные слои (если среда — GridForest, иначе None)
        passability = self.env.word_layers.get("passability")
        value_layer = self.env.word_layers.get("value")
        intruders = self.env.word_layers.get("intruders")

        # Максимальная ценность для нормализации
        max_c = float(np.max(value_layer)) if value_layer is not None else 1.0
        if max_c == 0.0:
            max_c = 1.0

        for x in range(size):

            row = []

            for y in range(size):

                cell = self._build_cell(
                    x, y,
                    ax, ay,
                    visible,
                    passability,
                    value_layer,
                    max_c,
                )

                # агент (перекрывает всё)
                if x == ax and y == ay:
                    cell = Text(agent.get_symbol(), style="bold bright_cyan")

                # нарушители (перекрывают фон, но не агента)
                for intruder in self.env.intruders:
                    if intruder.x == x and intruder.y == y and intruders[x][y] == 1.0:
                        if not (x == ax and y == ay):
                            cell = Text(intruder.get_symbol(), style="bold red")

                row.append(cell)

            table.add_row(*row)

        hud = Text()
        hud.append(" GRIDFOREST " if passability is not None else " GRIDWORLD ",
                   style="bold yellow")
        hud.append(" | ")
        hud.append(f"Step: {self.env.train_state.step:.3f}/{self.env.max_steps:.3f} ", style="bold gray")
        hud.append(" | ")
        hud.append(f"Intruders: {len(self.env.intruders)} ", style="red")
        hud.append("| ")
        hud.append(f"Agent: ({ax},{ay}) ", style="cyan")
        hud.append("| ")
        hud.append(f"Reward: {self.env.train_state.total_reward:.3f} ", style="bold green")
        hud.append("| ")
        hud.append(f"Obs shape: {obs.shape}", style="bold yellow")

        main_content = table

        # --- DEBUG LAYER ---------------------------------------------------------
        if self.debug_layer_enabled and self.layer_key is not None:

            debug_layer = self.env.word_layers.get(self.layer_key)

            if debug_layer is not None:

                debug_table = Table(
                    show_header=False,
                    show_lines=False,
                    padding=(0, 1),
                    box=None
                )

                for _ in range(size):
                    debug_table.add_column(justify="center")

                for x in range(size):

                    row = []

                    for y in range(size):

                        value = debug_layer[x][y]

                        # форматирование числа
                        if isinstance(value, float):
                            text = f"{value:.2f}"
                        else:
                            text = str(value)

                        style = "dim" if (x, y) not in visible else "bold yellow"

                        row.append(Text(text, style=style))

                    debug_table.add_row(*row)

                main_content = Table.grid()
                main_content.add_column()
                main_content.add_column()

                main_content.add_row(
                    Align.center(table),
                    Align.center(debug_table)
                )

        # -------------------------------------------------------------------------

        panel = Panel(
            Align.center(main_content),
            title=hud,
            border_style="bright_magenta"
        )

        return panel

    # ------------------------------------------------------------------ #
    #  Построение ячейки                                                   #
    # ------------------------------------------------------------------ #

    def _build_cell(
        self,
        x: int,
        y: int,
        ax: int,
        ay: int,
        visible: set,
        passability,
        value_layer,
        max_c: float,
    ) -> Text:
        """
        Формирует rich.Text для одной клетки сетки.

        Правила отображения (GridForest):
          1. μ == 0                  → ▧ серый  (непроходимо, c = 0)
          2. μ > 0, c == 0           → .  серый  (проходимо, без ценности)
          3. μ == 1, c > 0           → #  зелёный (яркость по norm)
          4. 0 < μ < 1, c > 0        → #  серо-зелёный (частично проходимо)

        Для базового GridWorld (без лесных слоёв) поведение прежнее.
        """
        dim = (x, y) not in visible

        # --- Базовое отображение (без лесных слоёв) ---
        if passability is None or value_layer is None:
            symbol = "."
            style = "dim"
        else:
            mu = float(passability[x][y])
            c = float(value_layer[x][y])

            # --- Непроходимая ячейка (μ = 0) ---
            if mu == 0.0:
                symbol = "▧"
                style = "grey50"

            # --- Проходимая, без ценности (μ > 0, c = 0) ---
            elif c == 0.0:
                symbol = "."
                style = "grey70"

            # --- Ячейка с ценностью ---
            else:
                norm = c / max_c
                partial = mu < 1.0
                symbol = "#"
                style = _value_style(norm, partial)

        # --- Применение видимости ---
        if dim:
            style = f"dim {style}"
        else:
            style = "bold yellow"

        return Text(symbol, style=style)