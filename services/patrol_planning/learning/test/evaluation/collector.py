from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from services.patrol_planning.learning.logging.rl_logger import RLLogger


class EvalCollector:
    """Сборщик метрик для режима оценки.

    Оборачивает RLLogger и добавляет трекинг, специфичный для оценки:
    - per-episode счётчики некорректных действий (out_of_bounds, impassable)
    - хитмап максимального времени простоя (max per cell across episodes)

    Подключается к среде вместо RLLogger:
        env.rl_logger = EvalCollector(grid_size=..., run_id=..., agent_name=...)

    Сохранение в CSV для последующей агрегации:
        collector.to_csv("path/episodes.csv")
    """

    def __init__(
        self,
        grid_size: int,
        run_id: str,
        agent_name: str,
        test_mode: str = "test1",
        max_episodes: int = 5000,
    ) -> None:
        self._logger = RLLogger(grid_size=grid_size, run_id=run_id, max_episodes=max_episodes)
        self.agent_name = agent_name
        self.test_mode = test_mode
        self.grid_size = grid_size

        self._max_idleness_hm = np.zeros((grid_size, grid_size), dtype=np.float64)

        # Счётчики некорректных действий за текущий эпизод
        self._ep_invalid_out: int = 0
        self._ep_invalid_block: int = 0

        # Накопители за все эпизоды
        self._invalid_out: List[int] = []
        self._invalid_block: List[int] = []

    # ------------------------------------------------------------------
    # Интерфейс, совместимый с env.rl_logger
    # ------------------------------------------------------------------

    def on_step(
        self,
        action: int,
        pos: tuple,
        reward: float,
        reward_components: Dict[str, float],
        events: List[str],
        total_damage: float = 0.0,
    ) -> None:
        self._logger.on_step(action, pos, reward, reward_components, events, total_damage)

        for ev in events:
            if ev == "BlockedMoveEvent_out_of_bounds":
                self._ep_invalid_out += 1
            elif ev == "BlockedMoveEvent_impassable":
                self._ep_invalid_block += 1

    def on_episode_end(
        self,
        terminated: bool,
        truncated: bool,
        episode_metrics: Optional[Dict[str, float]],
        intruders_scheduled: int = 0,
        idleness_map: Optional[np.ndarray] = None,
        idleness_interval_map: Optional[np.ndarray] = None,
        intruder_acc_map: Optional[np.ndarray] = None,
        damage_acc_map: Optional[np.ndarray] = None,
        catch_latency: Optional[List[int]] = None,
    ) -> None:
        self._logger.on_episode_end(
            terminated=terminated,
            truncated=truncated,
            episode_metrics=episode_metrics,
            intruders_scheduled=intruders_scheduled,
            idleness_map=idleness_map,
            idleness_interval_map=idleness_interval_map,
            intruder_acc_map=intruder_acc_map,
            damage_acc_map=damage_acc_map,
            catch_latency=catch_latency,
        )

        if idleness_interval_map is not None:
            np.maximum(self._max_idleness_hm, idleness_interval_map, out=self._max_idleness_hm)

        self._invalid_out.append(self._ep_invalid_out)
        self._invalid_block.append(self._ep_invalid_block)
        self._ep_invalid_out = 0
        self._ep_invalid_block = 0

    # ------------------------------------------------------------------
    # Прокси-методы к внутреннему RLLogger
    # ------------------------------------------------------------------

    def get_heatmap(self) -> np.ndarray:
        return self._logger.get_heatmap()

    def get_idleness_heatmap(self) -> np.ndarray:
        return self._logger.get_idleness_heatmap()

    def get_max_idleness_heatmap(self) -> np.ndarray:
        """Максимальное время простоя по всем эпизодам для каждой ячейки.
        Высокое значение = ячейка была систематически игнорируема."""
        return self._max_idleness_hm.copy()

    def get_intruder_heatmap(self) -> np.ndarray:
        return self._logger.get_intruder_heatmap()

    def get_damage_heatmap(self) -> np.ndarray:
        return self._logger.get_damage_heatmap()

    def get_action_histogram(self, normalize: bool = True) -> np.ndarray:
        return self._logger.get_action_histogram(normalize=normalize)

    def get_invalid_action_counts(self) -> Dict[str, List[int]]:
        """Per-episode счётчики некорректных действий."""
        return {
            "invalid_out": list(self._invalid_out),
            "invalid_block": list(self._invalid_block),
        }

    def visit_uniformity(self) -> float:
        return self._logger.visit_uniformity()

    def all_steps_to_df(self) -> "pd.DataFrame":
        return self._logger.all_steps_to_df()

    @property
    def episode_count(self) -> int:
        return self._logger.episode_count

    @property
    def run_id(self) -> Optional[str]:
        return self._logger.run_id

    # ------------------------------------------------------------------
    # DataFrame export
    # ------------------------------------------------------------------

    def episodes_to_df(self) -> pd.DataFrame:
        df = self._logger.episodes_to_df()
        if df.empty:
            return df
        n = len(df)
        df["agent"] = self.agent_name
        df["test_mode"] = self.test_mode
        df["invalid_out"] = self._invalid_out[:n]
        df["invalid_block"] = self._invalid_block[:n]
        return df

    def to_csv(self, path: str) -> None:
        """Сохранить все метрики эпизодов в CSV (включая метку агента и test_mode)."""
        df = self.episodes_to_df()
        if not df.empty:
            df.to_csv(path, index=False)

    def save_all(self, save_dir: str) -> None:
        """Сохранить CSV + numpy-хитмапы в директорию."""
        import os
        os.makedirs(save_dir, exist_ok=True)

        self.to_csv(os.path.join(save_dir, "episodes.csv"))

        np.save(os.path.join(save_dir, "heatmap_visits.npy"), self.get_heatmap())
        np.save(os.path.join(save_dir, "heatmap_idleness_mean.npy"), self.get_idleness_heatmap())
        np.save(os.path.join(save_dir, "heatmap_idleness_max.npy"), self.get_max_idleness_heatmap())
        np.save(os.path.join(save_dir, "heatmap_intruders.npy"), self.get_intruder_heatmap())
        np.save(os.path.join(save_dir, "heatmap_damage.npy"), self.get_damage_heatmap())
        np.save(os.path.join(save_dir, "action_histogram.npy"), self.get_action_histogram(normalize=True))

        df_steps = self.all_steps_to_df()
        if not df_steps.empty:
            df_steps.to_csv(os.path.join(save_dir, "steps.csv"), index=False)

    _PLOT_ACTION_LABELS = ["UP", "DOWN", "LEFT", "RIGHT", "STAY"]

    def save_plots(self, save_dir: str) -> None:
        """Сохранить отрендеренные графики как PNG в save_dir."""
        import os
        import matplotlib.pyplot as plt

        os.makedirs(save_dir, exist_ok=True)

        def _heatmap(data, fname, title, cmap, cbar_label):
            if data is None or data.max() == 0:
                return
            fig, ax = plt.subplots(figsize=(6, 5))
            im = ax.imshow(data, cmap=cmap, interpolation="nearest")
            fig.colorbar(im, ax=ax, label=cbar_label)
            ax.set_title(title)
            ax.axis("off")
            fig.savefig(os.path.join(save_dir, fname), bbox_inches="tight", dpi=120)
            plt.close(fig)

        _heatmap(self.get_heatmap(),              "heatmap_visits.png",        "Agent visits",    "hot",      "посещений")
        _heatmap(self.get_idleness_heatmap(),     "heatmap_idleness_mean.png", "Idleness mean",   "RdYlGn_r", "шагов")
        _heatmap(self.get_max_idleness_heatmap(), "heatmap_idleness_max.png",  "Idleness max",    "RdYlGn_r", "шагов")
        _heatmap(self.get_intruder_heatmap(),     "heatmap_intruders.png",     "Intruder visits", "Blues",    "посещений")
        _heatmap(self.get_damage_heatmap(),       "heatmap_damage.png",        "Damage map",      "Reds",     "урона")

        action_hist = self.get_action_histogram(normalize=True)
        if action_hist is not None:
            fig, ax = plt.subplots(figsize=(6, 4))
            bars = ax.bar(self._PLOT_ACTION_LABELS, action_hist, color="#3498db")
            for bar, v in zip(bars, action_hist):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                        f"{v:.1%}", ha="center", va="bottom", fontsize=9)
            ax.set_title("Action distribution")
            ax.set_ylim(0, 1)
            ax.set_ylabel("frequency")
            fig.savefig(os.path.join(save_dir, "action_histogram.png"), bbox_inches="tight", dpi=120)
            plt.close(fig)

        inv = self.get_invalid_action_counts()
        if inv:
            means = [np.mean(inv.get("invalid_out", [0])), np.mean(inv.get("invalid_block", [0]))]
            if any(m > 0 for m in means):
                fig, ax = plt.subplots(figsize=(5, 4))
                bars = ax.bar(["out_of_bounds", "impassable"], means, color=["#e74c3c", "#e67e22"])
                for bar, v in zip(bars, means):
                    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                            f"{v:.2f}", ha="center", va="bottom", fontsize=9)
                ax.set_title("Invalid actions / episode")
                ax.set_ylabel("mean per episode")
                fig.savefig(os.path.join(save_dir, "invalid_actions.png"), bbox_inches="tight", dpi=120)
                plt.close(fig)
