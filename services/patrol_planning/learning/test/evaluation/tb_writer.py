"""Логирование результатов оценки агента в TensorBoard.

Каждый запуск EvaluationRunner с tb_mode=True создаёт отдельный TB-run
в поддиректории {tb_log_dir}/{run_id}/, изолируя запуски друг от друга.

Структура тегов внутри run:
  {prefix}/episode/{metric}   — скаляры по номеру эпизода
  {prefix}/summary/{metric}   — агрегаты (mean/std) на шаге 0
  {prefix}/heatmap/{name}     — тепловые карты как RGB-изображения
  {prefix}/charts/{name}      — matplotlib-графики через add_figure
  {prefix}/summary_table      — HTML-таблица результатов
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from services.patrol_planning.learning.test.evaluation.plots import PlotData

ACTION_LABELS = ["UP", "DOWN", "LEFT", "RIGHT", "STAY"]

_EPISODE_SCALAR_COLS = [
    "metric_Z",
    "metric_M_damage",
    "metric_M_move",
    "metric_M_idleness",
    "total_reward",
    "catch_rate",
    "catch_latency_mean",
    "invalid_out",
    "invalid_block",
    "steps",
]

_SUMMARY_STAT_COLS = [
    "metric_Z",
    "metric_M_damage",
    "metric_M_move",
    "metric_M_idleness",
    "total_reward",
    "catch_rate",
    "catch_latency_mean",
    "invalid_out",
    "invalid_block",
    "steps",
]


def _make_heatmap_fig(
    arr: np.ndarray,
    cmap_name: str,
    title: str,
    colorbar_label: str,
) -> plt.Figure:
    """Тепловая карта с colorbar, осями и подписью."""
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(arr, cmap=cmap_name, origin="lower", aspect="equal")
    fig.colorbar(im, ax=ax, label=colorbar_label)
    ax.set_title(title)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    fig.tight_layout()
    return fig


def _make_reward_instant_fig(data: "PlotData") -> plt.Figure | None:
    """r(t) — средняя мгновенная награда по шагам."""
    if data.df_steps is None or data.df_steps.empty or data.df_episodes.empty:
        return None
    avg_len = int(data.df_episodes["steps"].mean())
    df_filt = data.df_steps[data.df_steps["step"] < avg_len]
    if df_filt.empty:
        return None

    grouped = df_filt.groupby("step")["reward"]
    mean_r = grouped.mean()
    std_r = grouped.std().fillna(0)
    steps = mean_r.index.to_numpy()

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(steps, mean_r.values, color="royalblue", linewidth=1.5, label="mean r(t)")
    ax.fill_between(steps, mean_r.values - std_r.values, mean_r.values + std_r.values,
                    alpha=0.2, color="royalblue", label="±std")
    ax.axhline(0, color="gray", linewidth=0.8, linestyle="--")
    ax.set_xlabel("шаг")
    ax.set_ylabel("reward")
    ax.set_title(f"Мгновенная награда r(t)  (avg_len={avg_len})")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig


def _make_reward_cumulative_fig(data: "PlotData") -> plt.Figure | None:
    """R(t) — средняя накопленная награда по шагам."""
    if data.df_steps is None or data.df_steps.empty or data.df_episodes.empty:
        return None
    avg_len = int(data.df_episodes["steps"].mean())
    df_filt = data.df_steps[data.df_steps["step"] < avg_len]
    if df_filt.empty:
        return None

    mean_r = df_filt.groupby("step")["reward"].mean()
    steps = mean_r.index.to_numpy()
    cumsum_r = mean_r.cumsum()

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(steps, cumsum_r.values, color="darkorange", linewidth=1.5, label="R(t)")
    ax.set_xlabel("шаг")
    ax.set_ylabel("reward (накопл.)")
    ax.set_title(f"Накопленная награда R(t) = Σr(0..t)  (avg_len={avg_len})")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig


def _make_action_hist_fig(action_hist: np.ndarray) -> plt.Figure:
    """Гистограмма действий агента."""
    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(ACTION_LABELS, action_hist, color="steelblue", edgecolor="white")
    for bar, val in zip(bars, action_hist):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                f"{val:.2%}", ha="center", va="bottom", fontsize=9)
    ax.set_ylim(0, max(action_hist.max() * 1.2 + 0.05, 0.1))
    ax.set_title("Распределение действий агента")
    ax.set_ylabel("доля от всех шагов")
    fig.tight_layout()
    return fig


def _build_html_table(df: pd.DataFrame, agent_name: str, test_label: str) -> str:
    """HTML-таблица сводных статистик по метрикам."""
    rows_html = ""
    for col in _SUMMARY_STAT_COLS:
        if col not in df.columns:
            continue
        valid = df[col].dropna()
        if valid.empty:
            continue
        rows_html += (
            f"<tr>"
            f"<td><b>{col}</b></td>"
            f"<td>{valid.mean():.4f}</td>"
            f"<td>{valid.std():.4f}</td>"
            f"<td>{valid.min():.4f}</td>"
            f"<td>{valid.median():.4f}</td>"
            f"<td>{valid.max():.4f}</td>"
            f"<td>{len(valid)}</td>"
            f"</tr>\n"
        )

    return (
        f"<h3>{test_label} | {agent_name} | эпизодов: {len(df)}</h3>"
        "<table border='1' cellpadding='4' cellspacing='0'>"
        "<thead><tr>"
        "<th>Метрика</th><th>Mean</th><th>Std</th><th>Min</th><th>Median</th><th>Max</th><th>N</th>"
        "</tr></thead>"
        f"<tbody>{rows_html}</tbody>"
        "</table>"
    )


class EvalTBWriter:
    """Пишет результаты оценки агента в TensorBoard.

    Использование:
        tb = EvalTBWriter(log_dir="/path/to/tb/run_id")
        tb.log_test(plot_data, prefix="test1")
        tb.log_test(plot_data, prefix="test2")
        tb.close()
    """

    def __init__(self, log_dir: str) -> None:
        from torch.utils.tensorboard import SummaryWriter
        self._writer = SummaryWriter(log_dir=log_dir)
        self._log_dir = log_dir

    def log_test(self, data: "PlotData", prefix: str, test_label: str = "") -> None:
        """Залогировать все результаты одного теста."""
        label = test_label or prefix
        self._log_episode_scalars(data.df_episodes, prefix)
        self._log_summary_scalars(data.df_episodes, prefix)
        self._log_heatmaps(data, prefix)
        self._log_charts(data, prefix)
        self._log_summary_table(data.df_episodes, data.agent_name, label, prefix)

    def _log_episode_scalars(self, df: pd.DataFrame, prefix: str) -> None:
        if df.empty or "episode" not in df.columns:
            return
        for _, row in df.iterrows():
            ep = int(row["episode"])
            for col in _EPISODE_SCALAR_COLS:
                if col in row and pd.notna(row[col]):
                    self._writer.add_scalar(f"{prefix}/episode/{col}", float(row[col]), ep)

    def _log_summary_scalars(self, df: pd.DataFrame, prefix: str) -> None:
        if df.empty:
            return
        for col in _SUMMARY_STAT_COLS:
            if col not in df.columns:
                continue
            valid = df[col].dropna()
            if valid.empty:
                continue
            self._writer.add_scalar(f"{prefix}/summary/{col}_mean", float(valid.mean()), 0)
            self._writer.add_scalar(f"{prefix}/summary/{col}_std", float(valid.std()), 0)

    def _log_heatmaps(self, data: "PlotData", prefix: str) -> None:
        heatmaps = [
            (data.heatmap_visits,        "visits",        "hot",       "Посещения агента",              "посещений"),
            (data.heatmap_idleness_mean, "idleness_mean", "RdYlGn_r",  "Среднее время простоя (↑ хуже)", "шагов"),
            (data.heatmap_idleness_max,  "idleness_max",  "RdYlGn_r",  "Макс. время простоя (↑ хуже)",  "шагов"),
        ]
        for arr, name, cmap, title, cb_label in heatmaps:
            if arr is None:
                continue
            fig = _make_heatmap_fig(arr, cmap, title, cb_label)
            self._writer.add_figure(f"{prefix}/heatmap/{name}", fig, 0)
            plt.close(fig)

    def _log_charts(self, data: "PlotData", prefix: str) -> None:
        if data.action_histogram is not None:
            fig = _make_action_hist_fig(data.action_histogram)
            self._writer.add_figure(f"{prefix}/charts/action_histogram", fig, 0)
            plt.close(fig)

        fig = _make_reward_instant_fig(data)
        if fig is not None:
            self._writer.add_figure(f"{prefix}/charts/reward_instant", fig, 0)
            plt.close(fig)

        fig = _make_reward_cumulative_fig(data)
        if fig is not None:
            self._writer.add_figure(f"{prefix}/charts/reward_cumulative", fig, 0)
            plt.close(fig)

    def _log_summary_table(
        self, df: pd.DataFrame, agent_name: str, test_label: str, prefix: str
    ) -> None:
        html = _build_html_table(df, agent_name, test_label)
        self._writer.add_text(f"{prefix}/summary_table", html, 0)

    def close(self) -> None:
        self._writer.close()
