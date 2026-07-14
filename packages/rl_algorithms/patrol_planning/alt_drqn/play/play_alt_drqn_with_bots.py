"""AltDRQN агент vs PoacherSimple боты — бесконечный цикл эпизодов.

Запуск из корня проекта:
    python packages/rl_algorithms/patrol_planning/alt_drqn/play/play_alt_drqn_with_bots.py
"""

import sys
import os

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..")
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def run_bot_playground(
    model_path: str,
    config_path: str,
    exclude_layers: list[str] | None = None,
    debug_layer_enabled: bool = True,
    layer_key: str | None = "idleness",
    obs_debug_enabled: bool = True,
    obs_layer_key: str | None = "idleness",
    render_time_sleep: float = 0.3,
    seed: int = 999,
    max_episodes: int | None = None,
    device: str = "cpu",
) -> None:
    """Запускает показ работы AltDRQN-агента против ботов-нарушителей.

    Args:
        model_path: Путь к .pt-чекпоинту AltDRQN.
        config_path: Путь к JSON-конфигу среды.
        exclude_layers: Слои, исключаемые из наблюдения.
        debug_layer_enabled: Показывать отладочный слой среды.
        layer_key: Ключ слоя среды для отладки.
        obs_debug_enabled: Показывать отладочный слой наблюдения.
        obs_layer_key: Ключ слоя наблюдения для отладки.
        render_time_sleep: Задержка между шагами (секунды).
        seed: Зерно генератора случайных чисел.
        max_episodes: Максимальное число эпизодов; None — бесконечный цикл.
        device: Устройство вывода ('cpu' или 'cuda').
    """
    import json
    import random
    import numpy as np
    import torch

    from packages.rl_algorithms.patrol_planning.alt_drqn.networks.drqn_net import DRQNNet
    from services.patrol_planning.assets.envs.forest import GridForest
    from services.patrol_planning.assets.envs.models import GridForestConfig
    from services.patrol_planning.src.renderer_extended import GridWorldRendererExt
    from services.patrol_planning.service.models import GridWorldTrainState

    if exclude_layers is None:
        exclude_layers = ["terrain", "rows", "cols", "passability"]

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

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

    _device = torch.device(device)
    checkpoint = torch.load(model_path, map_location=_device, weights_only=False)
    sd = checkpoint["net_state_dict"]
    lstm_hidden_size = sd["lstm.weight_hh_l0"].shape[0] // 4
    features_dim = sd["lstm.weight_ih_l0"].shape[1]
    n_actions = env.action_space.n

    net = DRQNNet(env.observation_space, n_actions, lstm_hidden_size, features_dim).to(_device)
    net.load_state_dict(sd)
    net.eval()

    def _predict(obs: np.ndarray, hidden):
        with torch.no_grad():
            obs_t = torch.tensor(
                obs[np.newaxis, np.newaxis],
                dtype=torch.float32,
                device=_device,
            )
            q_values, hidden = net(obs_t, hidden)
        return int(q_values[0, 0].argmax().item()), hidden

    obs, _ = env.reset(seed=seed)
    hidden = net.init_hidden(1, _device)

    episode = 0
    with renderer.live:
        while True:
            action, hidden = _predict(obs, hidden)
            obs, _, terminated, truncated, _ = env.step(action)

            if terminated or truncated:
                episode += 1
                reason = "поймал всех нарушителей" if terminated else "время вышло"
                print(f"Эпизод {episode}: {reason}")
                if max_episodes is not None and episode >= max_episodes:
                    break
                obs, _ = env.reset()
                hidden = net.init_hidden(1, _device)


_DIR = os.path.abspath(os.path.dirname(__file__))
_CONFIG = r"C:\Users\George Doroshin\repos\forest-rl-platform\services\patrol_planning\research\32x32_forest\test_configs\forest_32x32_val_v3.json"

if __name__ == "__main__":
    run_bot_playground(
        model_path=os.path.join(
            PROJECT_ROOT,
            "runs/32x32_forest/20260531_150842_drqn_forest_v2/model/final.pt",
        ),
        config_path=_CONFIG,
        render_time_sleep=0.1,
        exclude_layers=["terrain"],
        debug_layer_enabled=True,
        layer_key="idleness",
        obs_debug_enabled=True,
        obs_layer_key="idleness",
        device="cpu",
    )
