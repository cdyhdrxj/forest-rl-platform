"""DQN + CNN на 16x16 карте леса v3.

Сравнение с DRQN (train_drqn_v3.py) на той же карте и конфигах.
- gamma=0.999, total_timesteps=3M — как у DRQN для честного сравнения.
- buffer_size=750k, exploration_fraction=0.45 — между 14x14 и 20x20.

Запуск из корня проекта:
    python services/patrol_planning/research/16x16_forest/train_dqn_v3.py

Результаты: runs/16x16_forest/<timestamp>_dqn_forest_v3/
"""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

_DIR        = os.path.abspath(os.path.dirname(__file__))
_CONFIG     = os.path.join(_DIR, "test_configs", "forest_16x16_v3.json")
_CONFIG_VAL = os.path.join(_DIR, "test_configs", "forest_16x16_val_v3.json")

from services.patrol_planning.learning.learn_tool import run_training
from packages.rl_algorithms.patrol_planning.dqn.train.dqn_train_config import DQNTrainConfig
from services.patrol_planning.learning.validation.training_validator import ValidationConfig

if __name__ == "__main__":
    algo_cfg = DQNTrainConfig(
        lr=3e-4,
        gamma=0.999,
        batch_size=256,
        buffer_size=750_000,
        learning_starts=25_000,
        target_update_interval=8_000,
        exploration_fraction=0.45,
        exploration_final_eps=0.05,
        n_envs=4,
        common_seed=False,
        normalize_rewards=True,
        use_cnn=True,
        features_dim=64,
        use_torch_compile=True,
        device="cuda",
        cpu_cores_num=8,
        verbose=1,
    )

    val_cfg = ValidationConfig(
        config_path=_CONFIG_VAL,
        exclude_layers=["terrain"],
        freq=100_000,
        n_episodes=20,
        seed=2026,
        verbose=True,
    )

    run_training(
        algorithm="dqn",
        algo_config=algo_cfg,
        config_path=_CONFIG,
        output_dir=os.path.join(PROJECT_ROOT, "runs", "16x16_forest"),
        run_id="dqn_forest_v3",
        total_timesteps=3_000_000,
        seed=42,
        exclude_layers=["terrain"],
        checkpoint_freq=150_000,
        use_tensorboard=True,
        validation_config=val_cfg,
    )
