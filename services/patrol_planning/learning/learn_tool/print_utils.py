"""Форматированный вывод параметров в начале обучения.

Каждый тренер вызывает print_training_header() перед стартом обучения.
"""
from __future__ import annotations

from typing import Any

_W_KEY = 28
_W_VAL = 20
_LINE = "═" * (_W_KEY + _W_VAL + 5)
_SEP  = "─" * (_W_KEY + _W_VAL + 5)


def _fmt(v: Any) -> str:
    if isinstance(v, float):
        return f"{v:.4g}"
    if isinstance(v, int):
        return f"{v:,}".replace(",", "_")
    return str(v)


def _section(name: str, items: dict) -> None:
    print(f"  {name}")
    for k, v in items.items():
        line = f"    {k:<{_W_KEY}}{_fmt(v):>{_W_VAL}}"
        print(line)


def print_training_header(
    algo_name: str,
    config,           # GridForestConfig
    hparams: dict,
    meta: dict,
) -> None:
    """Вывести форматированный заголовок запуска обучения.

    Args:
        algo_name: Название алгоритма ("PPO", "DQN", "RPPO", "AltDRQN").
        config:    GridForestConfig (содержит параметры среды).
        hparams:   Словарь гиперпараметров алгоритма.
        meta:      Словарь мета-параметров (total_timesteps, seed, etc.).
    """
    print()
    print(_LINE)
    print(f"  ЗАПУСК ОБУЧЕНИЯ: {algo_name}")
    print(_SEP)

    # Параметры среды
    env_items: dict = {}
    try:
        gs = config.grid_size
        env_items["grid_size"] = f"{gs}x{gs}" if isinstance(gs, int) else str(gs)
    except AttributeError:
        pass
    try:
        env_items["reward_config"] = type(config.reward_config).__name__
    except AttributeError:
        pass
    try:
        ic = config.intruders_config
        env_items["intruder_type"] = type(ic).__name__ if ic is not None else "none"
    except AttributeError:
        pass
    try:
        env_items["obs_channels"] = str(getattr(config.obs_config, "exclude_layers", "—"))
    except AttributeError:
        pass
    try:
        mc = config.metrics_config
        env_items["metrics_enabled"] = str(mc.enabled)
        env_items["w1/w2/w3"] = f"{mc.w1}/{mc.w2}/{mc.w3}"
    except AttributeError:
        pass

    if env_items:
        _section("Среда", env_items)

    # Гиперпараметры
    if hparams:
        _section("Гиперпараметры", hparams)

    # Мета параметры запуска
    if meta:
        _section("Параметры запуска", meta)

    print(_LINE)
    print()
