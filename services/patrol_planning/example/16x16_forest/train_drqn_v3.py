import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

_DIR = os.path.abspath(os.path.dirname(__file__))
_CONFIG     = os.path.join(_DIR, "test_configs", "forest_16x16_v3.json")
_CONFIG_VAL = os.path.join(_DIR, "test_configs", "forest_16x16_val_v3.json")

from services.patrol_planning.learning.learn_tool import run_training
from packages.rl_algorithms.patrol_planning.alt_drqn.train.alt_drqn_train_config import AltDRQNTrainConfig
from services.patrol_planning.learning.validation.training_validator import ValidationConfig

if __name__ == "__main__":
    algo_cfg = AltDRQNTrainConfig(
        lr=3e-4,
        gamma=0.999,
        batch_size=64,
        lstm_hidden_size=256,
        unroll_length=25,
        buffer_capacity=75_000,
        learning_starts=5_000,
        target_update_freq=15_000,
        epsilon_decay_steps=300_000,
        epsilon_final=0.05,
        train_freq=12,
        log_interval=100,
        n_envs=12,
        use_amp=True,
        device="cuda",
        common_seed=False,
        cpu_cores_num=8,
        normalize_rewards=True
    )

    val_cfg = ValidationConfig(
        config_path=_CONFIG_VAL,
        exclude_layers=["terrain"],
        freq=100_000,
        n_episodes=20,
        seed=2026,
        verbose=True,
        drqn_device="cuda",
    )

    run_training(
        algorithm="alt_drqn",
        algo_config=algo_cfg,
        config_path=_CONFIG,
        output_dir=os.path.join(PROJECT_ROOT, "runs", "16x16_forest"),
        run_id="drqn_forest_16x16_done",
        total_timesteps=3_000_000,
        seed=42,
        exclude_layers=["terrain"],
        checkpoint_freq=150_000,
        use_tensorboard=True,
        validation_config=val_cfg,
    )
