"""RecurrentPPO агент vs PoacherSimple боты — бесконечный цикл эпизодов.

Запуск из корня проекта:
    python services/patrol_planning/research/r_ppo/play/play_rppo_with_bots.py
"""

import sys
import os

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..")
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def run_bot_playground(
    model_path: str = "services/patrol_planning/research/r_ppo/models/rppo_8x8_final",
    config_path: str = "services/patrol_planning/research/r_ppo/config_8x8_rppo.json",
    exclude_layers: list[str] | None = None,
    debug_layer_enabled: bool = True,
    layer_key: str | None = "intruders",
    obs_debug_enabled: bool = True,
    obs_layer_key: str | None = "intruders",
    render_time_sleep: float = 0.3,
    seed: int = 999,
    max_episodes: int | None = None,
) -> None:
    """Запускает показ работы RecurrentPPO-агента против ботов-нарушителей.

    Args:
        model_path: Путь к сохранённой модели RecurrentPPO (без расширения).
        config_path: Путь к JSON-конфигу среды.
        exclude_layers: Слои, исключаемые из наблюдения.
        debug_layer_enabled: Показывать отладочный слой среды.
        layer_key: Ключ слоя среды для отладки.
        obs_debug_enabled: Показывать отладочный слой наблюдения.
        obs_layer_key: Ключ слоя наблюдения для отладки.
        render_time_sleep: Задержка между шагами (секунды).
        seed: Зерно генератора случайных чисел.
        max_episodes: Максимальное число эпизодов; None — бесконечный цикл.
    """
    import json
    import random
    import numpy as np

    from sb3_contrib import RecurrentPPO
    from services.patrol_planning.assets.envs.forest import GridForest
    from services.patrol_planning.assets.envs.models import GridForestConfig
    from services.patrol_planning.src.renderer_extended import GridWorldRendererExt
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

    renderer = GridWorldRendererExt(
        env,
        debug_layer_enabled,
        layer_key,
        obs_debug_enabled,
        obs_layer_key,
    )
    env.renderer = renderer
    env.render_time_sleep = render_time_sleep

    from packages.rl_algorithms.patrol_planning.rppo.networks.cnn_extractor_5x5 import CNNExtractor5x5
    model = RecurrentPPO.load(
        model_path,
        env=env,
        custom_objects={"features_extractor_class": CNNExtractor5x5},
    )

    obs, _ = env.reset(seed=seed)

    lstm_states = None
    episode_starts = np.ones((1,), dtype=bool)

    episode = 0
    with renderer.live:
        while True:
            action, lstm_states = model.predict(
                obs,
                state=lstm_states,
                episode_start=episode_starts,
                deterministic=True,
            )
            obs, _, terminated, truncated, _ = env.step(action)
            episode_starts = np.zeros((1,), dtype=bool)

            if terminated or truncated:
                episode += 1
                reason = "поймал всех нарушителей" if terminated else "время вышло"
                print(f"Эпизод {episode}: {reason}")
                if max_episodes is not None and episode >= max_episodes:
                    break
                obs, _ = env.reset()
                lstm_states = None
                episode_starts = np.ones((1,), dtype=bool)
                
CONFIG = r"C:\Users\George Doroshin\repos\forest-rl-platform\services\patrol_planning\research\32x32_forest\test_configs\forest_32x32_val_v2.json"
VAL_CONFIG = r"C:\Users\George Doroshin\repos\forest-rl-platform\services\patrol_planning\research\8x8_cross_analysis\test_configs\basic_val.json"
if __name__ == "__main__":
    run_bot_playground(
        model_path=os.path.join(PROJECT_ROOT, "services/patrol_planning/research/8x8_cross_analysis/models/rppo_basic_mod_e"),
        config_path=os.path.join(CONFIG),
        render_time_sleep=0.2,
        exclude_layers=["terrain"],
        debug_layer_enabled=True,
        layer_key="idleness",
        obs_debug_enabled=True,
        obs_layer_key="idleness",
    )

