"""RecurrentPPO агент vs игрок-нарушитель.

Управление:
    W / ↑   — вверх
    S / ↓   — вниз
    A / ←   — влево
    D / →   — вправо
    Q / Esc — выход

Запуск из корня проекта:
    python services/patrol_planning/research/r_ppo/play/play_rppo_manual.py
"""

import sys
import os

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..")
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

_R_PPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _spawn_player(env):
    """Создаёт игрока-нарушителя на случайной граничной клетке и встраивает в среду."""
    from services.patrol_planning.assets.intruders.controllable import Controllable
    from services.patrol_planning.assets.envs.src import sample_spawn_cell

    pos = sample_spawn_cell(env, mu_min=0.5)
    if pos is None:
        pos = (0, 0)

    player = Controllable(y=pos[1], x=pos[0], is_random_spawned=False, catch_reward=1)
    player.spawn_time = env.train_state.step

    env.intruders.append(player)
    env.world_layers["intruders"][player.x][player.y] = 1

    env.intruder_schedule = {}
    env.intruder_schedule_start = {"player": None}

    return player


def run_manual_playground(
    model_path: str = "services/patrol_planning/research/r_ppo/models/rppo_8x8_final",
    config_path: str = "services/patrol_planning/research/r_ppo/config_8x8_rppo.json",
    exclude_layers: list[str] | None = None,
    debug_layer_enabled: bool = True,
    layer_key: str | None = "value",
    step_sleep: float = 0.5,
    seed: int = 42,
) -> None:
    """Запускает интерактивный режим: игрок управляет нарушителем, агент патрулирует.

    Args:
        model_path: Путь к сохранённой модели RecurrentPPO (без расширения).
        config_path: Путь к JSON-конфигу среды.
        exclude_layers: Слои, исключаемые из наблюдения агента.
        debug_layer_enabled: Показывать отладочный слой среды.
        layer_key: Ключ слоя среды для отладки (например, "value").
        step_sleep: Задержка между шагами (секунды).
        seed: Зерно генератора случайных чисел.
    """
    import json
    import random
    import time
    import threading
    import numpy as np
    import keyboard

    from sb3_contrib import RecurrentPPO
    from services.patrol_planning.assets.envs.forest import GridForest
    from services.patrol_planning.assets.envs.models import GridForestConfig
    from services.patrol_planning.src.renderer_extended import GridWorldRendererExt
    from services.patrol_planning.src.pp_types import InputActions
    from services.patrol_planning.service.models import GridWorldTrainState

    if exclude_layers is None:
        exclude_layers = ["terrain", "rows", "cols", "passability"]

    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass

    with open(config_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)

    config = GridForestConfig.model_validate(config_data)
    config.obs_config.exclude_layers = exclude_layers

    env = GridForest.load(config)
    env.train_state = GridWorldTrainState()

    renderer = GridWorldRendererExt(env, debug_layer_enabled, layer_key)
    env.renderer = renderer
    env.render_time_sleep = 0.0

    model = RecurrentPPO.load(model_path, env=env)

    state = {"next_input": InputActions.STAY, "stop": False}

    def _input_listener():
        while not state["stop"]:
            if keyboard.is_pressed("w") or keyboard.is_pressed("up"):
                state["next_input"] = InputActions.UP
            elif keyboard.is_pressed("s") or keyboard.is_pressed("down"):
                state["next_input"] = InputActions.DOWN
            elif keyboard.is_pressed("a") or keyboard.is_pressed("left"):
                state["next_input"] = InputActions.LEFT
            elif keyboard.is_pressed("d") or keyboard.is_pressed("right"):
                state["next_input"] = InputActions.RIGHT
            if keyboard.is_pressed("q") or keyboard.is_pressed("esc"):
                state["stop"] = True
            time.sleep(0.05)

    listener_thread = threading.Thread(target=_input_listener, daemon=True)
    listener_thread.start()

    obs, _ = env.reset(seed=seed)
    player = _spawn_player(env)

    lstm_states = None
    episode_starts = np.ones((1,), dtype=bool)

    with renderer.live:
        while not state["stop"]:
            action, lstm_states = model.predict(
                obs,
                state=lstm_states,
                episode_start=episode_starts,
                deterministic=True,
            )
            episode_starts = np.zeros((1,), dtype=bool)

            player.input_action = state["next_input"]
            state["next_input"] = InputActions.STAY

            obs, _, _, truncated, _ = env.step(action)

            time.sleep(step_sleep)

            if len(env.intruders) == 0:
                print("Агент поймал вас! Новый эпизод...")
                time.sleep(1.5)
                obs, _ = env.reset(seed=seed)
                player = _spawn_player(env)
                lstm_states = None
                episode_starts = np.ones((1,), dtype=bool)
            elif truncated:
                print("Время вышло! Новый эпизод...")
                time.sleep(1.5)
                obs, _ = env.reset(seed=seed)
                player = _spawn_player(env)
                lstm_states = None
                episode_starts = np.ones((1,), dtype=bool)

    state["stop"] = True
    listener_thread.join()


if __name__ == "__main__":
    run_manual_playground(
        model_path=os.path.join(_R_PPO_DIR, "checkpoints", "rppo_16x16_CPU_v1", "rppo_5400000_steps.zip"),
        config_path=os.path.join(_R_PPO_DIR, "C:/Users/George Doroshin/repos/forest-rl-platform/services/patrol_planning/research/16x16_assym/configs/6ch/0_learn.json"),
        exclude_layers=["terrain"],
        step_sleep=0.2,
    )
