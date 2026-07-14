"""Утилита сравнения нескольких агентов по сохранённым CSV."""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from matplotlib.figure import Figure

_PALETTE = [
    "steelblue", "tomato", "seagreen", "darkorange",
    "purple", "brown", "deeppink", "teal",
]

_METRIC_COLS = [
    ("metric_Z", "Z(π)", "↓ лучше"),
    ("metric_M_damage", "M_damage", "↓ лучше"),
    ("metric_M_move", "M_move", "↓ лучше"),
    ("metric_M_idleness", "M_idleness", "↓ лучше"),
    ("total_reward", "R (награда)", "↑ лучше"),
    ("catch_rate", "Catch rate", "↑ лучше"),
    ("catch_latency_mean", "Catch latency (шагов)", "↓ лучше"),
]


def _s(style: dict | None, key: str, default):
    if style and key in style and style[key] not in ("", None):
        return style[key]
    return default


def _ss(style: dict | None, key: str, default: str) -> str:
    """Как _s(), но пустая строка считается валидным значением (не откатывается на default)."""
    if style is not None and key in style and style[key] is not None:
        return str(style[key])
    return default


def _figsize(style: dict | None, default_w: float, default_h: float) -> tuple[float, float]:
    w = _s(style, "figwidth", default_w)
    h = _s(style, "figheight", default_h)
    try:
        w, h = float(w), float(h)
    except (TypeError, ValueError):
        w, h = default_w, default_h
    return (w if w > 0 else default_w, h if h > 0 else default_h)


def _load_steps(csv_path: str) -> pd.DataFrame | None:
    folder = os.path.dirname(csv_path)
    steps_path = os.path.join(folder, "steps.csv")
    if os.path.exists(steps_path):
        try:
            return pd.read_csv(steps_path)
        except Exception:
            return None
    return None


def _load(csv_paths: list[str], labels: list[str] | None) -> pd.DataFrame:
    frames = []
    for i, path in enumerate(csv_paths):
        df = pd.read_csv(path)
        label = labels[i] if labels and i < len(labels) else df.get("agent", [f"agent_{i}"])[0]
        df["_label"] = label
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def plot_metrics_comparison(
    df: pd.DataFrame,
    output_dir: str,
    rolling: int = 20,
    title: str | None = None,
    style: dict | None = None,
    return_fig: bool = False,
) -> "Figure | None":
    labels = df["_label"].unique().tolist()
    available = [(col, label, note) for col, label, note in _METRIC_COLS if col in df.columns]
    if not available:
        return None

    lw = float(_s(style, "linewidth", 2.0))
    fw, fh_base = _figsize(style, 14, 3.5)
    fh = fh_base * len(available) if fh_base == 3.5 else fh_base
    legend_loc = _s(style, "legend_loc", "upper right")
    legend_fs = int(_s(style, "legend_fontsize", 8))
    legend_ms = float(_s(style, "legend_markerscale", 1.0))

    fig, axes = plt.subplots(len(available), 1, figsize=(fw, fh), sharex=False)
    if len(available) == 1:
        axes = [axes]
    fig.suptitle(title if title is not None else "Сравнение агентов — метрики по эпизодам", fontsize=13)

    for ax, (col, metric_label, note) in zip(axes, available):
        for i, agent_label in enumerate(labels):
            color = _PALETTE[i % len(_PALETTE)]
            sub = df[df["_label"] == agent_label].reset_index(drop=True)
            ax.plot(sub.index, sub[col], alpha=0.25, color=color, linewidth=max(lw * 0.35, 0.5))
            rolled = sub[col].rolling(rolling, min_periods=1).mean()
            ax.plot(sub.index, rolled, color=color, linewidth=lw,
                    label=f"{agent_label} (μ={sub[col].mean():.4f})")
        ax.set_ylabel(f"{metric_label}\n({note})")
        ax.legend(fontsize=legend_fs, loc=legend_loc, markerscale=legend_ms)
        ax.grid(True, alpha=0.3)

    axes[-1].set_xlabel(_ss(style, "xlabel", "эпизод"))
    fig.tight_layout()

    if return_fig:
        return fig
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "comparison_metrics.png")
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"  Сохранено: {path}")
    return None


def plot_invalid_actions_comparison(
    df: pd.DataFrame,
    output_dir: str,
    title: str | None = None,
    style: dict | None = None,
    return_fig: bool = False,
) -> "Figure | None":
    if "invalid_out" not in df.columns and "invalid_block" not in df.columns:
        return None

    labels = df["_label"].unique().tolist()
    x = np.arange(len(labels))
    width = 0.35

    fw, fh = _figsize(style, 8, 5)
    fig, ax = plt.subplots(figsize=(fw, fh))
    fig.suptitle(title if title is not None else "Некорректные действия (среднее/эп.)", fontsize=12)

    if "invalid_out" in df.columns:
        means_out = [df[df["_label"] == l]["invalid_out"].mean() for l in labels]
        stds_out = [df[df["_label"] == l]["invalid_out"].std() for l in labels]
        ax.bar(x - width / 2, means_out, width, label="out_of_bounds (m_out)",
               color="tomato", yerr=stds_out, capsize=5, error_kw={"elinewidth": 1.5})

    if "invalid_block" in df.columns:
        means_block = [df[df["_label"] == l]["invalid_block"].mean() for l in labels]
        stds_block = [df[df["_label"] == l]["invalid_block"].std() for l in labels]
        ax.bar(x + width / 2, means_block, width, label="impassable (m_block)",
               color="darkorange", yerr=stds_block, capsize=5, error_kw={"elinewidth": 1.5})

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_xlabel(_ss(style, "xlabel", ""))
    ax.set_ylabel(_ss(style, "ylabel", "шагов / эпизод"))
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()

    if return_fig:
        return fig
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "comparison_invalid_actions.png")
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"  Сохранено: {path}")
    return None


def plot_action_histograms_comparison(
    csv_paths: list[str],
    labels: list[str] | None,
    output_dir: str,
    title: str | None = None,
    style: dict | None = None,
    return_fig: bool = False,
) -> "Figure | None":
    action_names = ["UP", "DOWN", "LEFT", "RIGHT", "STAY"]
    action_cols = ["n_up", "n_down", "n_left", "n_right", "n_stay"]

    agent_labels = labels or [f"agent_{i}" for i in range(len(csv_paths))]
    data = []
    for path, label in zip(csv_paths, agent_labels):
        df = pd.read_csv(path)
        if all(c in df.columns for c in action_cols):
            totals = np.array([df[c].sum() for c in action_cols], dtype=float)
            data.append((label, totals / totals.sum() if totals.sum() > 0 else totals))

    if not data:
        return None

    x = np.arange(len(action_names))
    width = 0.8 / len(data)
    fw, fh = _figsize(style, 10, 5)
    fig, ax = plt.subplots(figsize=(fw, fh))
    fig.suptitle(title if title is not None else "Гистограмма действий — сравнение агентов", fontsize=12)

    for i, (label, fracs) in enumerate(data):
        color = _PALETTE[i % len(_PALETTE)]
        offset = (i - len(data) / 2 + 0.5) * width
        ax.bar(x + offset, fracs, width, label=label, color=color, alpha=0.85)

    ax.set_xticks(x)
    ax.set_xticklabels(action_names)
    ax.set_xlabel(_ss(style, "xlabel", "действие"))
    ax.set_ylabel(_ss(style, "ylabel", "доля"))
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()

    if return_fig:
        return fig
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "comparison_actions.png")
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"  Сохранено: {path}")
    return None


def plot_action_histograms_npy_comparison(
    csv_paths: list[str],
    labels: list[str] | None,
    output_dir: str,
    title: str | None = None,
    style: dict | None = None,
    return_fig: bool = False,
) -> "Figure | None":
    """Сводная гистограмма действий из action_histogram.npy — по одному столбцу на агента для каждого действия."""
    action_names = ["UP", "DOWN", "LEFT", "RIGHT", "STAY"]
    agent_labels = labels or [f"agent_{i}" for i in range(len(csv_paths))]

    data = []
    for path, label in zip(csv_paths, agent_labels):
        npy_path = os.path.join(os.path.dirname(path), "action_histogram.npy")
        if os.path.exists(npy_path):
            try:
                fracs = np.load(npy_path).astype(float)
                if fracs.shape == (5,):
                    data.append((label, fracs))
            except Exception:
                pass

    if not data:
        fw, fh = _figsize(style, 10, 5)
        fig, ax = plt.subplots(figsize=(fw, fh))
        fig.suptitle(title if title is not None else "Сводная гистограмма действий", fontsize=12)
        ax.text(0.5, 0.5, "Нет данных — action_histogram.npy не найден",
                ha="center", va="center", transform=ax.transAxes, fontsize=11, color="gray")
        if return_fig:
            return fig
        os.makedirs(output_dir, exist_ok=True)
        out = os.path.join(output_dir, "comparison_actions_npy.png")
        fig.savefig(out, dpi=120, bbox_inches="tight")
        plt.close(fig)
        return None

    x = np.arange(len(action_names))
    group_width = float(_s(style, "bar_group_width", 0.8))
    group_width = max(0.1, min(1.0, group_width))
    inner_gap = float(_s(style, "bar_inner_gap", 0.0))
    inner_gap = max(0.0, min(0.9, inner_gap))
    step = group_width / len(data)
    bar_w = step * (1.0 - inner_gap)
    fw, fh = _figsize(style, 10, 5)
    fig, ax = plt.subplots(figsize=(fw, fh))
    fig.suptitle(title if title is not None else "Сводная гистограмма действий", fontsize=12)

    bar_label = _s(style, "bar_label_rotation", "vertical")
    for i, (label, fracs) in enumerate(data):
        color = _PALETTE[i % len(_PALETTE)]
        offset = (i - len(data) / 2 + 0.5) * step
        bars = ax.bar(x + offset, fracs, bar_w, label=label, color=color, alpha=0.85, edgecolor="white")
        if bar_label != "none":
            rot = 90 if bar_label == "vertical" else 0
            for bar, val in zip(bars, fracs):
                if val >= 0.01:
                    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.003,
                            f"{val:.1%}", ha="center", va="bottom", fontsize=7, rotation=rot)

    ax.set_xticks(x)
    ax.set_xticklabels(action_names)
    ax.set_xlabel(_ss(style, "xlabel", "действие"))
    ax.set_ylabel(_ss(style, "ylabel", "доля"))
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()

    if return_fig:
        return fig
    os.makedirs(output_dir, exist_ok=True)
    out = os.path.join(output_dir, "comparison_actions_npy.png")
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"  Сохранено: {out}")
    return None


def plot_action_histograms_npy_by_agent(
    csv_paths: list[str],
    labels: list[str] | None,
    output_dir: str,
    title: str | None = None,
    style: dict | None = None,
    return_fig: bool = False,
) -> "Figure | None":
    """Гистограмма действий из action_histogram.npy — группировка по агентам, подписи действий снизу."""
    action_names = ["UP", "DOWN", "LEFT", "RIGHT", "STAY"]
    action_colors = [_PALETTE[i % len(_PALETTE)] for i in range(len(action_names))]
    agent_labels = labels or [f"agent_{i}" for i in range(len(csv_paths))]

    data = []
    for path, label in zip(csv_paths, agent_labels):
        npy_path = os.path.join(os.path.dirname(path), "action_histogram.npy")
        if os.path.exists(npy_path):
            try:
                fracs = np.load(npy_path).astype(float)
                if fracs.shape == (5,):
                    data.append((label, fracs))
            except Exception:
                pass

    fw, fh = _figsize(style, 10, 5)
    fig, ax = plt.subplots(figsize=(fw, fh))
    fig.suptitle(title if title is not None else "Гистограмма действий по агентам", fontsize=12)

    if not data:
        ax.text(0.5, 0.5, "Нет данных — action_histogram.npy не найден",
                ha="center", va="center", transform=ax.transAxes, fontsize=11, color="gray")
        if return_fig:
            return fig
        os.makedirs(output_dir, exist_ok=True)
        out = os.path.join(output_dir, "comparison_actions_npy_by_agent.png")
        fig.savefig(out, dpi=120, bbox_inches="tight")
        plt.close(fig)
        return None

    n_agents = len(data)
    n_actions = len(action_names)
    group_width = float(_s(style, "bar_group_width", 0.8))
    group_width = max(0.1, min(1.0, group_width))
    inner_gap = float(_s(style, "bar_inner_gap", 0.0))
    inner_gap = max(0.0, min(0.9, inner_gap))
    step = group_width / n_actions
    bar_w = step * (1.0 - inner_gap)

    x = np.arange(n_agents)
    bar_label = _s(style, "bar_label_rotation", "vertical")

    for j, (action, color) in enumerate(zip(action_names, action_colors)):
        offset = (j - n_actions / 2 + 0.5) * step
        vals = [fracs[j] for _, fracs in data]
        bars = ax.bar(x + offset, vals, bar_w, label=action, color=color, alpha=0.85, edgecolor="white")
        if bar_label != "none":
            rot = 90 if bar_label == "vertical" else 0
            for bar, val in zip(bars, vals):
                if val >= 0.01:
                    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.003,
                            f"{val:.1%}", ha="center", va="bottom", fontsize=7, rotation=rot)

    ax.set_xticks(x)
    ax.set_xticklabels([lbl for lbl, _ in data])

    ax.set_xlabel(_ss(style, "xlabel", "агент"))
    ax.set_ylabel(_ss(style, "ylabel", "доля"))
    legend_title = _ss(style, "legend_title", "действие")
    legend_loc = _s(style, "legend_loc", "upper right")
    legend_fs = int(_s(style, "legend_fontsize", 8))
    legend_ms = float(_s(style, "legend_markerscale", 1.0))
    ax.legend(title=legend_title or None, loc=legend_loc, fontsize=legend_fs, markerscale=legend_ms)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()

    if return_fig:
        return fig
    os.makedirs(output_dir, exist_ok=True)
    out = os.path.join(output_dir, "comparison_actions_npy_by_agent.png")
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"  Сохранено: {out}")
    return None


def save_summary_table(df: pd.DataFrame, output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)
    numeric_cols = [
        col for col in [
            "metric_Z", "metric_M_damage", "metric_M_move", "metric_M_idleness",
            "total_reward", "catch_rate", "catch_latency_mean",
            "invalid_out", "invalid_block",
        ]
        if col in df.columns
    ]
    summary = (
        df.groupby("_label")[numeric_cols]
        .agg(["mean", "std"])
        .round(4)
    )
    summary.columns = ["_".join(c) for c in summary.columns]
    summary.index.name = "agent"
    csv_path = os.path.join(output_dir, "comparison_summary.csv")
    summary.to_csv(csv_path)
    print(f"  Сохранено: {csv_path}")


def plot_reward_dynamics_instant_comparison(
    csv_paths: list[str],
    labels: list[str] | None,
    output_dir: str,
    title: str | None = None,
    show_std: bool = True,
    style: dict | None = None,
    return_fig: bool = False,
) -> "Figure | None":
    agent_labels = labels or [f"agent_{i}" for i in range(len(csv_paths))]
    lw = float(_s(style, "linewidth", 1.5))
    fw, fh = _figsize(style, 14, 5)
    legend_loc = _s(style, "legend_loc", "upper right")
    legend_fs = int(_s(style, "legend_fontsize", 8))
    legend_ms = float(_s(style, "legend_markerscale", 1.0))

    fig, ax = plt.subplots(figsize=(fw, fh))
    fig.suptitle(title if title is not None else "Сравнение мгновенной награды r(t) по шагам", fontsize=12)

    has_data = False
    for i, (path, label) in enumerate(zip(csv_paths, agent_labels)):
        df_steps = _load_steps(path)
        if df_steps is None or df_steps.empty or "reward" not in df_steps.columns:
            continue
        try:
            df_ep = pd.read_csv(path)
            avg_len = int(df_ep["steps"].mean()) if "steps" in df_ep.columns else None
        except Exception:
            avg_len = None
        if avg_len:
            df_steps = df_steps[df_steps["step"] < avg_len]

        color = _PALETTE[i % len(_PALETTE)]
        grouped = df_steps.groupby("step")["reward"]
        mean_r = grouped.mean()
        if show_std:
            std_r = grouped.std().fillna(0)
            ax.fill_between(mean_r.index, mean_r - std_r, mean_r + std_r,
                            alpha=0.1, color=color)
        ax.plot(mean_r.index, mean_r.values, color=color, linewidth=lw, label=label)
        has_data = True

    if not has_data:
        ax.text(0.5, 0.5, "Нет данных — steps.csv не найден рядом с episodes.csv",
                ha="center", va="center", transform=ax.transAxes, fontsize=11, color="gray")
    ax.axhline(0, color="gray", linewidth=0.7, linestyle="--")
    ax.set_xlabel(_ss(style, "xlabel", "шаг патрулирования"))
    ax.set_ylabel(_ss(style, "ylabel", "reward (мгн.)"))
    if has_data:
        ax.legend(fontsize=legend_fs, loc=legend_loc, markerscale=legend_ms)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    if return_fig:
        return fig
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "comparison_reward_dynamics_instant.png")
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"  Сохранено: {out_path}")
    return None


def plot_reward_dynamics_cumulative_comparison(
    csv_paths: list[str],
    labels: list[str] | None,
    output_dir: str,
    title: str | None = None,
    style: dict | None = None,
    return_fig: bool = False,
) -> "Figure | None":
    agent_labels = labels or [f"agent_{i}" for i in range(len(csv_paths))]
    lw = float(_s(style, "linewidth", 1.5))
    fw, fh = _figsize(style, 14, 5)
    legend_loc = _s(style, "legend_loc", "upper right")
    legend_fs = int(_s(style, "legend_fontsize", 8))
    legend_ms = float(_s(style, "legend_markerscale", 1.0))

    fig, ax = plt.subplots(figsize=(fw, fh))
    fig.suptitle(title if title is not None else "Сравнение накопленной награды R(t) по шагам", fontsize=12)

    has_data = False
    for i, (path, label) in enumerate(zip(csv_paths, agent_labels)):
        df_steps = _load_steps(path)
        if df_steps is None or df_steps.empty or "reward" not in df_steps.columns:
            continue
        try:
            df_ep = pd.read_csv(path)
            avg_len = int(df_ep["steps"].mean()) if "steps" in df_ep.columns else None
        except Exception:
            avg_len = None
        if avg_len:
            df_steps = df_steps[df_steps["step"] < avg_len]

        color = _PALETTE[i % len(_PALETTE)]
        mean_r = df_steps.groupby("step")["reward"].mean()
        cumsum_r = mean_r.cumsum()
        ax.plot(cumsum_r.index, cumsum_r.values, color=color, linewidth=lw, label=label)
        has_data = True

    if not has_data:
        ax.text(0.5, 0.5, "Нет данных — steps.csv не найден рядом с episodes.csv",
                ha="center", va="center", transform=ax.transAxes, fontsize=11, color="gray")
    ax.set_xlabel(_ss(style, "xlabel", "шаг патрулирования"))
    ax.set_ylabel(_ss(style, "ylabel", "reward (накопл.)"))
    if has_data:
        ax.legend(fontsize=legend_fs, loc=legend_loc, markerscale=legend_ms)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    if return_fig:
        return fig
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "comparison_reward_dynamics_cumulative.png")
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"  Сохранено: {out_path}")
    return None


def compare_agents(
    csv_paths: list[str],
    labels: list[str] | None = None,
    test_mode: str = "test1",
    output_dir: str = "comparison",
    rolling: int = 20,
) -> None:
    print(f"\n=== Сравнение агентов [{test_mode}] ===")
    df = _load(csv_paths, labels)
    plot_metrics_comparison(df, output_dir, rolling=rolling)
    plot_invalid_actions_comparison(df, output_dir)
    plot_action_histograms_comparison(csv_paths, labels, output_dir)
    save_summary_table(df, output_dir)
    print(f"\nВсе результаты сохранены в: {output_dir}")
