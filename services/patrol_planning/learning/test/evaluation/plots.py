"""Функции визуализации результатов оценки агента.

PlotData — центральный объект данных, принимаемый всеми функциями.
Создаётся из EvalCollector (PlotData.from_collector) или из директории результатов
(PlotData.from_dir).

plot_all(data, save_dir, chart_cfg=None) — сводная точка входа.
chart_cfg: dict[str, {"enabled": bool, "title": str|None, "show_std": bool, "tab": str,
                       "style": dict}]
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

import matplotlib
matplotlib.use("Agg")
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from matplotlib.figure import Figure
    from services.patrol_planning.learning.test.evaluation.collector import EvalCollector

ACTION_LABELS = ["UP", "DOWN", "LEFT", "RIGHT", "STAY"]


def _s(style: dict | None, key: str, default):
    """Достать значение из style-словаря с fallback на default."""
    if style and key in style and style[key] not in ("", None):
        return style[key]
    return default


def _ss(style: dict | None, key: str, default: str) -> str:
    """Как _s(), но пустая строка считается валидным значением."""
    if style is not None and key in style and style[key] is not None:
        return str(style[key])
    return default


@dataclass
class PlotData:
    """Данные для построения графиков."""

    df_episodes: pd.DataFrame
    df_steps: pd.DataFrame | None = None
    heatmap_visits: np.ndarray | None = None
    heatmap_idleness_mean: np.ndarray | None = None
    heatmap_idleness_max: np.ndarray | None = None
    heatmap_damage: np.ndarray | None = None
    heatmap_intruders: np.ndarray | None = None
    action_histogram: np.ndarray | None = None
    grid_size: int = 8
    agent_name: str = ""

    @classmethod
    def from_collector(cls, collector: "EvalCollector") -> "PlotData":
        df_steps = collector.all_steps_to_df()
        return cls(
            df_episodes=collector.episodes_to_df(),
            df_steps=df_steps if not df_steps.empty else None,
            heatmap_visits=collector.get_heatmap(),
            heatmap_idleness_mean=collector.get_idleness_heatmap(),
            heatmap_idleness_max=collector.get_max_idleness_heatmap(),
            action_histogram=collector.get_action_histogram(normalize=True),
            grid_size=collector.grid_size,
            agent_name=collector.agent_name,
        )

    @classmethod
    def from_dir(cls, folder: str) -> "PlotData":
        """Загрузить из директории результатов (episodes.csv + npy-файлы)."""
        csv_path = os.path.join(folder, "episodes.csv")
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"episodes.csv не найден в: {folder}")

        df_ep = pd.read_csv(csv_path)
        agent_name = (
            str(df_ep["agent"].iloc[0])
            if "agent" in df_ep.columns and not df_ep.empty
            else os.path.basename(folder)
        )

        steps_path = os.path.join(folder, "steps.csv")
        df_steps = pd.read_csv(steps_path) if os.path.exists(steps_path) else None

        def _npy(name: str) -> np.ndarray | None:
            p = os.path.join(folder, name)
            return np.load(p) if os.path.exists(p) else None

        hm = _npy("heatmap_visits.npy")
        grid_size = int(hm.shape[0]) if hm is not None else 8

        action_hist = _npy("action_histogram.npy")
        if action_hist is None and df_steps is not None and "action" in df_steps.columns:
            counts = np.zeros(5, dtype=np.float64)
            for a in range(5):
                counts[a] = float((df_steps["action"] == a).sum())
            total = counts.sum()
            action_hist = counts / total if total > 0 else counts

        if (df_steps is not None
                and "invalid_out" not in df_ep.columns
                and "episode" in df_steps.columns
                and "events" in df_steps.columns):
            ev = df_steps[["episode", "events"]].copy()
            ev["_io"] = ev["events"].str.contains(
                "BlockedMoveEvent_out_of_bounds", na=False).astype(int)
            ev["_ib"] = ev["events"].str.contains(
                "BlockedMoveEvent_impassable", na=False).astype(int)
            per_ep = ev.groupby("episode")[["_io", "_ib"]].sum()
            df_ep = df_ep.merge(
                per_ep.rename(columns={"_io": "invalid_out", "_ib": "invalid_block"}),
                on="episode", how="left",
            )

        return cls(
            df_episodes=df_ep,
            df_steps=df_steps,
            heatmap_visits=hm,
            heatmap_idleness_mean=_npy("heatmap_idleness_mean.npy"),
            heatmap_idleness_max=_npy("heatmap_idleness_max.npy"),
            heatmap_damage=_npy("heatmap_damage.npy"),
            heatmap_intruders=_npy("heatmap_intruders.npy"),
            action_histogram=action_hist,
            grid_size=grid_size,
            agent_name=agent_name,
        )


def _ep_prefix(data: PlotData) -> str:
    n = len(data.df_episodes) if data.df_episodes is not None else 0
    return f"{data.agent_name} | эп: {n}"


def _suptitle(title: str | None, default: str, prefix: str = "") -> str:
    """title=None → default; title='' → пустой заголовок (без замены на default)."""
    head = default if title is None else title
    if head and prefix:
        return f"{head}\n{prefix}"
    return head or prefix


def _save_no_data(save_dir: str, filename: str, msg: str) -> None:
    os.makedirs(save_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.text(0.5, 0.5, msg, ha="center", va="center",
            transform=ax.transAxes, fontsize=12, color="gray",
            wrap=True)
    ax.axis("off")
    path = os.path.join(save_dir, filename)
    fig.savefig(path, dpi=100, bbox_inches="tight")
    plt.close(fig)
    print(f"  [!] Нет данных → заглушка: {path}")


def _figsize(style: dict | None, default_w: float, default_h: float) -> tuple[float, float]:
    w = _s(style, "figwidth", default_w)
    h = _s(style, "figheight", default_h)
    try:
        w = float(w)
        h = float(h)
    except (TypeError, ValueError):
        w, h = default_w, default_h
    return (w if w > 0 else default_w, h if h > 0 else default_h)


def _apply_heatmap_ticks(ax, n: int, style: dict | None) -> None:
    """Задать тики осей тепловой карты согласно tick_freq из style.

    tick_freq=0 → каждая координата; 1 → каждая 2-я (default); 2 → каждая 3-я …
    """
    try:
        freq = int(_s(style, "tick_freq", 1))
    except (TypeError, ValueError):
        freq = 1
    step = freq + 1
    ticks = list(range(0, n, step))
    ax.set_xticks(ticks)
    ax.set_yticks(ticks)
    tick_fs = _s(style, "tick_fontsize", None)
    if tick_fs is not None:
        try:
            tick_fs = int(tick_fs)
            ax.tick_params(axis="both", labelsize=tick_fs)
        except (TypeError, ValueError):
            pass


def _apply_line_style(ax, style: dict | None, xlabel: str = "", ylabel: str = "") -> None:
    """Применить стиль к линейному графику."""
    xl = _ss(style, "xlabel", xlabel)
    yl = _ss(style, "ylabel", ylabel)
    if xl:
        ax.set_xlabel(xl)
    if yl:
        ax.set_ylabel(yl)
    loc = _s(style, "legend_loc", None)
    fs = _s(style, "legend_fontsize", None)
    legend = ax.get_legend()
    if legend is not None:
        if loc:
            legend.set_loc(loc)
        if fs is not None:
            try:
                for text in legend.get_texts():
                    text.set_fontsize(int(fs))
            except (TypeError, ValueError):
                pass


# ------------------------------------------------------------------
# 1. Метрики задачи + Reward по эпизодам
# ------------------------------------------------------------------

def plot_episode_metrics(
    data: PlotData,
    save_dir: str,
    title: str | None = None,
    show_std: bool = False,
    rolling: int = 20,
    style: dict | None = None,
    return_fig: bool = False,
) -> "Figure | None":
    """Z(π), M_damage, M_move, M_idleness и суммарная R по эпизодам."""
    df = data.df_episodes

    metric_cols = [
        ("metric_Z",          "Z(π)",        "black"),
        ("metric_M_damage",   "M_damage",    "tomato"),
        ("metric_M_move",     "M_move",      "steelblue"),
        ("metric_M_idleness", "M_idleness",  "seagreen"),
        ("total_reward",      "R (награда)", "royalblue"),
    ]
    available = [(col, label, color) for col, label, color in metric_cols if col in df.columns]
    if not available:
        return None

    lw = float(_s(style, "linewidth", 2.0))
    fw, fh = _figsize(style, 12, 3 * len(available))
    fh_auto = fh if fh != 3 * len(available) else 3 * len(available)

    fig, axes = plt.subplots(len(available), 1, figsize=(fw, fh_auto), sharex=True)
    if len(available) == 1:
        axes = [axes]
    fig.suptitle(_suptitle(title, "Метрики задачи по эпизодам", _ep_prefix(data)), fontsize=12)

    for ax, (col, label, color) in zip(axes, available):
        ax.plot(df["episode"], df[col], alpha=0.4, color=color, linewidth=max(lw * 0.4, 0.5))
        roll_mean = df[col].rolling(rolling, min_periods=1).mean()
        ax.plot(df["episode"], roll_mean, color=color, linewidth=lw,
                label=f"скользящее ({rolling} эп.)")
        if show_std:
            roll_std = df[col].rolling(rolling, min_periods=1).std().fillna(0)
            ax.fill_between(df["episode"],
                            roll_mean - roll_std, roll_mean + roll_std,
                            alpha=0.15, color=color, label="±std")
        mean_val = df[col].mean()
        ax.axhline(mean_val, color=color, linewidth=max(lw * 0.75, 1.0), linestyle="--",
                   label=f"среднее: {mean_val:.4f}")
        ax.set_ylabel(label)
        legend_loc = _s(style, "legend_loc", "upper right")
        legend_fs = int(_s(style, "legend_fontsize", 8))
        legend_ms = float(_s(style, "legend_markerscale", 1.0))
        ax.legend(fontsize=legend_fs, loc=legend_loc, markerscale=legend_ms)
        ax.grid(True, alpha=0.3)

    axes[-1].set_xlabel(_ss(style, "xlabel", "эпизод"))
    fig.tight_layout()

    if return_fig:
        return fig
    os.makedirs(save_dir, exist_ok=True)
    path = os.path.join(save_dir, "metrics_per_episode.png")
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"  Сохранено: {path}")
    return None


# ------------------------------------------------------------------
# 2. Вспомогательные метрики: R, catch_rate, catch_latency
# ------------------------------------------------------------------

def plot_rl_metrics(
    data: PlotData,
    save_dir: str,
    title: str | None = None,
    show_std: bool = False,
    rolling: int = 20,
    style: dict | None = None,
    return_fig: bool = False,
) -> "Figure | None":
    df = data.df_episodes
    if df.empty:
        return None

    lw = float(_s(style, "linewidth", 2.0))
    fw, fh = _figsize(style, 18, 5)
    legend_loc = _s(style, "legend_loc", "upper right")
    legend_fs = int(_s(style, "legend_fontsize", 8))
    legend_ms = float(_s(style, "legend_markerscale", 1.0))

    fig = plt.figure(figsize=(fw, fh))
    fig.suptitle(_suptitle(title, "Вспомогательные метрики", _ep_prefix(data)), fontsize=12)
    gs = gridspec.GridSpec(1, 3, figure=fig, wspace=0.35)

    def _panel(ax_obj, col, panel_title, color, ylabel):
        if col not in df.columns:
            return
        series = df[col]
        ax_obj.plot(df["episode"], series, alpha=0.4, color=color, linewidth=max(lw * 0.4, 0.5))
        roll_m = series.rolling(rolling, min_periods=1).mean()
        ax_obj.plot(df["episode"], roll_m, color=color, linewidth=lw)
        if show_std:
            roll_s = series.rolling(rolling, min_periods=1).std().fillna(0)
            ax_obj.fill_between(df["episode"], roll_m - roll_s, roll_m + roll_s,
                                alpha=0.15, color=color)
        mean_v = series.mean()
        ax_obj.axhline(mean_v, color=color, linewidth=max(lw * 0.75, 1.0), linestyle="--",
                       label=f"среднее: {mean_v:.3f}")
        ax_obj.legend(fontsize=legend_fs, loc=legend_loc, markerscale=legend_ms)
        ax_obj.set_title(panel_title)
        ax_obj.set_xlabel(_ss(style, "xlabel", "эпизод"))
        ax_obj.set_ylabel(ylabel)
        ax_obj.grid(True, alpha=0.3)

    _panel(fig.add_subplot(gs[0, 0]), "total_reward", "Суммарная награда R", "royalblue", "reward")
    ax_c = fig.add_subplot(gs[0, 1])
    _panel(ax_c, "catch_rate", "Доля перехваченных нарушителей", "seagreen", "catch rate")
    ax_c.set_ylim(-0.05, 1.05)
    _panel(fig.add_subplot(gs[0, 2]), "catch_latency_mean",
           "Среднее время до перехвата\n(шагов от появления до поимки)", "darkorange", "шагов")

    fig.tight_layout()

    if return_fig:
        return fig
    os.makedirs(save_dir, exist_ok=True)
    path = os.path.join(save_dir, "rl_metrics.png")
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"  Сохранено: {path}")
    return None


# ------------------------------------------------------------------
# 3a. Мгновенная награда по шагам
# ------------------------------------------------------------------

def plot_reward_dynamics_instant(
    data: PlotData,
    save_dir: str,
    title: str | None = None,
    show_std: bool = True,
    style: dict | None = None,
    return_fig: bool = False,
) -> "Figure | None":
    if data.df_steps is None or data.df_steps.empty or data.df_episodes.empty:
        if not return_fig:
            _save_no_data(save_dir, "reward_dynamics_instant.png",
                          "Нет данных: steps.csv не найден.\n"
                          "Перезапустите оценку — обновлённый runner сохраняет steps.csv автоматически.")
        return None

    avg_len = int(data.df_episodes["steps"].mean())
    df_filt = data.df_steps[data.df_steps["step"] < avg_len].copy()
    if df_filt.empty:
        return None

    grouped = df_filt.groupby("step")["reward"]
    mean_r = grouped.mean()
    std_r = grouped.std().fillna(0)
    steps = mean_r.index.to_numpy()

    lw = float(_s(style, "linewidth", 1.5))
    fw, fh = _figsize(style, 12, 4)
    legend_loc = _s(style, "legend_loc", "upper right")
    legend_fs = int(_s(style, "legend_fontsize", 8))
    legend_ms = float(_s(style, "legend_markerscale", 1.0))

    fig, ax = plt.subplots(figsize=(fw, fh))
    _head = (title if title is not None else "Мгновенная награда по шагам")
    fig.suptitle(_suptitle(_head, "", f"avg_len={avg_len} | {_ep_prefix(data)}"), fontsize=12)
    ax.plot(steps, mean_r.values, color="royalblue", linewidth=lw, label="mean reward")
    if show_std:
        ax.fill_between(steps,
                        mean_r.values - std_r.values,
                        mean_r.values + std_r.values,
                        alpha=0.2, color="royalblue", label="±std")
    ax.axhline(0, color="gray", linewidth=0.8, linestyle="--")
    ax.set_xlabel(_ss(style, "xlabel", "шаг патрулирования"))
    ax.set_ylabel(_ss(style, "ylabel", "reward (мгн.)"))
    ax.set_title("r(t), усреднённая по тестовым эпизодам")
    ax.legend(fontsize=legend_fs, loc=legend_loc, markerscale=legend_ms)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    if return_fig:
        return fig
    os.makedirs(save_dir, exist_ok=True)
    path = os.path.join(save_dir, "reward_dynamics_instant.png")
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"  Сохранено: {path}")
    return None


# ------------------------------------------------------------------
# 3b. Накопленная награда по шагам
# ------------------------------------------------------------------

def plot_reward_dynamics_cumulative(
    data: PlotData,
    save_dir: str,
    title: str | None = None,
    style: dict | None = None,
    return_fig: bool = False,
) -> "Figure | None":
    if data.df_steps is None or data.df_steps.empty or data.df_episodes.empty:
        if not return_fig:
            _save_no_data(save_dir, "reward_dynamics_cumulative.png",
                          "Нет данных: steps.csv не найден.\n"
                          "Перезапустите оценку — обновлённый runner сохраняет steps.csv автоматически.")
        return None

    avg_len = int(data.df_episodes["steps"].mean())
    df_filt = data.df_steps[data.df_steps["step"] < avg_len].copy()
    if df_filt.empty:
        return None

    mean_r = df_filt.groupby("step")["reward"].mean()
    steps = mean_r.index.to_numpy()
    cumsum_r = mean_r.cumsum()

    lw = float(_s(style, "linewidth", 1.5))
    fw, fh = _figsize(style, 12, 4)
    legend_loc = _s(style, "legend_loc", "upper right")
    legend_fs = int(_s(style, "legend_fontsize", 8))
    legend_ms = float(_s(style, "legend_markerscale", 1.0))

    fig, ax = plt.subplots(figsize=(fw, fh))
    _head = (title if title is not None else "Накопленная награда по шагам")
    fig.suptitle(_suptitle(_head, "", f"avg_len={avg_len} | {_ep_prefix(data)}"), fontsize=12)
    ax.plot(steps, cumsum_r.values, color="darkorange", linewidth=lw, label="R(t)")
    ax.set_xlabel(_ss(style, "xlabel", "шаг патрулирования"))
    ax.set_ylabel(_ss(style, "ylabel", "reward (накопл.)"))
    ax.set_title("R(t) = Σr(0..t)")
    ax.legend(fontsize=legend_fs, loc=legend_loc, markerscale=legend_ms)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    if return_fig:
        return fig
    os.makedirs(save_dir, exist_ok=True)
    path = os.path.join(save_dir, "reward_dynamics_cumulative.png")
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"  Сохранено: {path}")
    return None


def plot_reward_dynamics(
    data: PlotData,
    save_dir: str,
    title: str | None = None,
    show_std: bool = True,
) -> None:
    plot_reward_dynamics_instant(data, save_dir, title=title, show_std=show_std)
    plot_reward_dynamics_cumulative(data, save_dir, title=title)


# ------------------------------------------------------------------
# 4. Гистограммы: действия агента + некорректные действия
# ------------------------------------------------------------------

def plot_histograms(
    data: PlotData,
    save_dir: str,
    title: str | None = None,
    show_std: bool = True,
    style: dict | None = None,
    return_fig: bool = False,
) -> "Figure | None":
    df = data.df_episodes

    fw, fh = _figsize(style, 14, 5)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(fw, fh))
    fig.suptitle(_suptitle(title, "Гистограммы", _ep_prefix(data)), fontsize=12)

    if data.action_histogram is not None:
        action_hist = data.action_histogram
        bars = ax1.bar(ACTION_LABELS, action_hist, color="steelblue", edgecolor="white")
        for bar, val in zip(bars, action_hist):
            ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                     f"{val:.2%}", ha="center", va="bottom", fontsize=9)
        ax1.set_ylim(0, max(action_hist) * 1.2 + 0.05 if action_hist.max() > 0 else 1.0)
    else:
        ax1.text(0.5, 0.5, "Нет данных", ha="center", va="center",
                 transform=ax1.transAxes, fontsize=12, color="gray")
    ax1.set_title("Гистограмма действий агента\n(доля от всех шагов)")
    ax1.set_xlabel(_ss(style, "xlabel", "действие"))
    ax1.set_ylabel(_ss(style, "ylabel", "доля"))

    if not df.empty and "invalid_out" in df.columns and "invalid_block" in df.columns:
        labels = ["Выход за границу\n(m_out)", "Непроходимая\nклетка (m_block)"]
        means = [df["invalid_out"].mean(), df["invalid_block"].mean()]
        stds = [df["invalid_out"].std(), df["invalid_block"].std()] if show_std else [0.0, 0.0]
        colors = ["tomato", "darkorange"]
        bars2 = ax2.bar(labels, means, color=colors, edgecolor="white",
                        yerr=stds if show_std else None,
                        capsize=6 if show_std else 0,
                        error_kw={"elinewidth": 1.5})
        offset = max(stds) * 0.05 + 0.2 if show_std else 0.2
        for bar, val in zip(bars2, means):
            ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + offset,
                     f"{val:.2f}/эп.", ha="center", va="bottom", fontsize=9)
        suffix = " ± std)" if show_std else ")"
        ax2.set_title(f"Некорректные действия\n(среднее за эпизод{suffix}")
        ax2.set_ylabel("шагов / эпизод")
    else:
        ax2.text(0.5, 0.5, "Нет данных", ha="center", va="center",
                 transform=ax2.transAxes, fontsize=12, color="gray")
        ax2.set_title("Некорректные действия")

    fig.tight_layout()

    if return_fig:
        return fig
    os.makedirs(save_dir, exist_ok=True)
    path = os.path.join(save_dir, "histograms.png")
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"  Сохранено: {path}")
    return None


# ------------------------------------------------------------------
# 5a. Тепловая карта посещений
# ------------------------------------------------------------------

def plot_heatmap_visits(
    data: PlotData,
    save_dir: str,
    title: str | None = None,
    style: dict | None = None,
    return_fig: bool = False,
) -> "Figure | None":
    if data.heatmap_visits is None:
        return None
    fw, fh = _figsize(style, 6, 5)
    vmin = _s(style, "vmin", None)
    vmax = _s(style, "vmax", None)
    try:
        vmin = float(vmin) if vmin not in (None, "") else None
        vmax = float(vmax) if vmax not in (None, "") else None
    except (TypeError, ValueError):
        vmin = vmax = None

    fig, ax = plt.subplots(figsize=(fw, fh))
    im = ax.imshow(data.heatmap_visits, cmap="hot", origin="lower", aspect="equal",
                   vmin=vmin, vmax=vmax)
    cb_label = _ss(style, "colorbar_label", "посещений")
    cb = fig.colorbar(im, ax=ax)
    cb.set_label(cb_label, fontsize=_s(style, "colorbar_fontsize", None) or None)
    _apply_heatmap_ticks(ax, data.heatmap_visits.shape[0], style)
    ax.set_title(title if title is not None else "Движения агента\n(кол-во посещений)")
    ax.set_xlabel(_ss(style, "xlabel", "x"))
    ax.set_ylabel(_ss(style, "ylabel", "y"))
    fig.suptitle(_ep_prefix(data), fontsize=10)
    fig.tight_layout()

    if return_fig:
        return fig
    os.makedirs(save_dir, exist_ok=True)
    path = os.path.join(save_dir, "heatmap_visits.png")
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"  Сохранено: {path}")
    return None


# ------------------------------------------------------------------
# 5b. Тепловая карта среднего простоя
# ------------------------------------------------------------------

def plot_heatmap_idleness_mean(
    data: PlotData,
    save_dir: str,
    title: str | None = None,
    style: dict | None = None,
    return_fig: bool = False,
) -> "Figure | None":
    if data.heatmap_idleness_mean is None:
        return None
    fw, fh = _figsize(style, 6, 5)
    vmin = _s(style, "vmin", None)
    vmax = _s(style, "vmax", None)
    try:
        vmin = float(vmin) if vmin not in (None, "") else None
        vmax = float(vmax) if vmax not in (None, "") else None
    except (TypeError, ValueError):
        vmin = vmax = None

    fig, ax = plt.subplots(figsize=(fw, fh))
    im = ax.imshow(data.heatmap_idleness_mean, cmap="RdYlGn_r", origin="lower", aspect="equal",
                   vmin=vmin, vmax=vmax)
    cb_label = _ss(style, "colorbar_label", "шагов")
    cb = fig.colorbar(im, ax=ax)
    cb.set_label(cb_label, fontsize=_s(style, "colorbar_fontsize", None) or None)
    _apply_heatmap_ticks(ax, data.heatmap_idleness_mean.shape[0], style)
    ax.set_title(title if title is not None else "Среднее время простоя\n(avg-интервал по эп., ↑ хуже)")
    ax.set_xlabel(_ss(style, "xlabel", "x"))
    ax.set_ylabel(_ss(style, "ylabel", "y"))
    fig.suptitle(_ep_prefix(data), fontsize=10)
    fig.tight_layout()

    if return_fig:
        return fig
    os.makedirs(save_dir, exist_ok=True)
    path = os.path.join(save_dir, "heatmap_idleness_mean.png")
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"  Сохранено: {path}")
    return None


# ------------------------------------------------------------------
# 5c. Тепловая карта максимального простоя
# ------------------------------------------------------------------

def plot_heatmap_idleness_max(
    data: PlotData,
    save_dir: str,
    title: str | None = None,
    style: dict | None = None,
    return_fig: bool = False,
) -> "Figure | None":
    if data.heatmap_idleness_max is None:
        return None
    fw, fh = _figsize(style, 6, 5)
    vmin = _s(style, "vmin", None)
    vmax = _s(style, "vmax", None)
    try:
        vmin = float(vmin) if vmin not in (None, "") else None
        vmax = float(vmax) if vmax not in (None, "") else None
    except (TypeError, ValueError):
        vmin = vmax = None

    fig, ax = plt.subplots(figsize=(fw, fh))
    im = ax.imshow(data.heatmap_idleness_max, cmap="RdYlGn_r", origin="lower", aspect="equal",
                   vmin=vmin, vmax=vmax)
    cb_label = _ss(style, "colorbar_label", "шагов")
    cb = fig.colorbar(im, ax=ax)
    cb.set_label(cb_label, fontsize=_s(style, "colorbar_fontsize", None) or None)
    _apply_heatmap_ticks(ax, data.heatmap_idleness_max.shape[0], style)
    ax.set_title(title if title is not None else "Максимальное время простоя\n(worst-case по эп., ↑ хуже)")
    ax.set_xlabel(_ss(style, "xlabel", "x"))
    ax.set_ylabel(_ss(style, "ylabel", "y"))
    fig.suptitle(_ep_prefix(data), fontsize=10)
    fig.tight_layout()

    if return_fig:
        return fig
    os.makedirs(save_dir, exist_ok=True)
    path = os.path.join(save_dir, "heatmap_idleness_max.png")
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"  Сохранено: {path}")
    return None


# ------------------------------------------------------------------
# 5d. Тепловая карта урона
# ------------------------------------------------------------------

def plot_heatmap_damage(
    data: PlotData,
    save_dir: str,
    title: str | None = None,
    style: dict | None = None,
    return_fig: bool = False,
) -> "Figure | None":
    if data.heatmap_damage is None:
        return None
    fw, fh = _figsize(style, 6, 5)
    vmin = _s(style, "vmin", None)
    vmax = _s(style, "vmax", None)
    try:
        vmin = float(vmin) if vmin not in (None, "") else None
        vmax = float(vmax) if vmax not in (None, "") else None
    except (TypeError, ValueError):
        vmin = vmax = None

    fig, ax = plt.subplots(figsize=(fw, fh))
    im = ax.imshow(data.heatmap_damage, cmap="YlOrRd", origin="lower", aspect="equal",
                   vmin=vmin, vmax=vmax)
    cb_label = _ss(style, "colorbar_label", "урон")
    cb = fig.colorbar(im, ax=ax)
    cb.set_label(cb_label, fontsize=_s(style, "colorbar_fontsize", None) or None)
    _apply_heatmap_ticks(ax, data.heatmap_damage.shape[0], style)
    ax.set_title(title if title is not None else "Урон нарушителей\n(avg по эп., ↑ хуже)")
    ax.set_xlabel(_ss(style, "xlabel", "x"))
    ax.set_ylabel(_ss(style, "ylabel", "y"))
    fig.suptitle(_ep_prefix(data), fontsize=10)
    fig.tight_layout()

    if return_fig:
        return fig
    os.makedirs(save_dir, exist_ok=True)
    path = os.path.join(save_dir, "heatmap_damage.png")
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"  Сохранено: {path}")
    return None


# ------------------------------------------------------------------
# 5e. Тепловая карта активности нарушителей
# ------------------------------------------------------------------

def plot_heatmap_intruders(
    data: PlotData,
    save_dir: str,
    title: str | None = None,
    style: dict | None = None,
    return_fig: bool = False,
) -> "Figure | None":
    if data.heatmap_intruders is None:
        return None
    fw, fh = _figsize(style, 6, 5)
    vmin = _s(style, "vmin", None)
    vmax = _s(style, "vmax", None)
    try:
        vmin = float(vmin) if vmin not in (None, "") else None
        vmax = float(vmax) if vmax not in (None, "") else None
    except (TypeError, ValueError):
        vmin = vmax = None

    fig, ax = plt.subplots(figsize=(fw, fh))
    im = ax.imshow(data.heatmap_intruders, cmap="Purples", origin="lower", aspect="equal",
                   vmin=vmin, vmax=vmax)
    cb_label = _ss(style, "colorbar_label", "появлений")
    cb = fig.colorbar(im, ax=ax)
    cb.set_label(cb_label, fontsize=_s(style, "colorbar_fontsize", None) or None)
    _apply_heatmap_ticks(ax, data.heatmap_intruders.shape[0], style)
    ax.set_title(title if title is not None else "Активность нарушителей\n(avg появлений по эп.)")
    ax.set_xlabel(_ss(style, "xlabel", "x"))
    ax.set_ylabel(_ss(style, "ylabel", "y"))
    fig.suptitle(_ep_prefix(data), fontsize=10)
    fig.tight_layout()

    if return_fig:
        return fig
    os.makedirs(save_dir, exist_ok=True)
    path = os.path.join(save_dir, "heatmap_intruders.png")
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"  Сохранено: {path}")
    return None


def plot_heatmaps(data: PlotData, save_dir: str, title: str | None = None) -> None:
    plot_heatmap_visits(data, save_dir, title=title)
    plot_heatmap_idleness_mean(data, save_dir, title=title)
    plot_heatmap_idleness_max(data, save_dir, title=title)


# ------------------------------------------------------------------
# Сводная функция
# ------------------------------------------------------------------

def plot_all(
    data: PlotData,
    save_dir: str,
    chart_cfg: dict | None = None,
    rolling: int = 20,
    return_figs: bool = False,
) -> "dict[str, Figure] | None":
    """Построить все включённые графики.

    Если return_figs=True — возвращает dict[key, Figure] вместо сохранения.
    chart_cfg поддерживает поле "style" для каждого ключа.
    """
    def _cfg(key: str) -> dict:
        defaults = {"enabled": True, "title": None, "show_std": False, "tab": "", "style": None}
        if chart_cfg and key in chart_cfg:
            return {**defaults, **chart_cfg[key]}
        return defaults

    def _dir(cfg: dict) -> str:
        tab = (cfg.get("tab") or "").strip()
        return os.path.join(save_dir, tab) if tab else save_dir

    if not return_figs:
        print(f"\n  === Графики: {data.agent_name} ===")

    figs: dict = {}

    _MAP = [
        ("metrics_per_episode",        plot_episode_metrics,
         lambda c, d: dict(title=c["title"], show_std=c["show_std"], rolling=rolling,
                           style=c.get("style"), return_fig=return_figs)),
        ("rl_metrics",                 plot_rl_metrics,
         lambda c, d: dict(title=c["title"], show_std=c["show_std"], rolling=rolling,
                           style=c.get("style"), return_fig=return_figs)),
        ("reward_dynamics_instant",    plot_reward_dynamics_instant,
         lambda c, d: dict(title=c["title"], show_std=c["show_std"],
                           style=c.get("style"), return_fig=return_figs)),
        ("reward_dynamics_cumulative", plot_reward_dynamics_cumulative,
         lambda c, d: dict(title=c["title"],
                           style=c.get("style"), return_fig=return_figs)),
        ("histograms",                 plot_histograms,
         lambda c, d: dict(title=c["title"], show_std=c["show_std"],
                           style=c.get("style"), return_fig=return_figs)),
        ("heatmap_visits",             plot_heatmap_visits,
         lambda c, d: dict(title=c["title"],
                           style=c.get("style"), return_fig=return_figs)),
        ("heatmap_idleness_mean",      plot_heatmap_idleness_mean,
         lambda c, d: dict(title=c["title"],
                           style=c.get("style"), return_fig=return_figs)),
        ("heatmap_idleness_max",       plot_heatmap_idleness_max,
         lambda c, d: dict(title=c["title"],
                           style=c.get("style"), return_fig=return_figs)),
        ("heatmap_damage",             plot_heatmap_damage,
         lambda c, d: dict(title=c["title"],
                           style=c.get("style"), return_fig=return_figs)),
        ("heatmap_intruders",          plot_heatmap_intruders,
         lambda c, d: dict(title=c["title"],
                           style=c.get("style"), return_fig=return_figs)),
    ]

    for key, fn, kwargs_fn in _MAP:
        c = _cfg(key)
        if not c["enabled"]:
            continue
        result = fn(data, _dir(c), **kwargs_fn(c, data))
        if return_figs and result is not None:
            figs[key] = result

    return figs if return_figs else None
