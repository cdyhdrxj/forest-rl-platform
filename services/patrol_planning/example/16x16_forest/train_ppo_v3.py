import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

_DIR        = os.path.abspath(os.path.dirname(__file__))
_CONFIG     = os.path.join(_DIR, "test_configs", "forest_16x16_v3.json")
_CONFIG_VAL = os.path.join(_DIR, "test_configs", "forest_16x16_val_v3.json")

from services.patrol_planning.learning.learn_tool import run_training
from packages.rl_algorithms.patrol_planning.ppo.ppo_train_config import PPOTrainConfig
from services.patrol_planning.learning.validation.training_validator import ValidationConfig

if __name__ == "__main__":
    algo_cfg = PPOTrainConfig(
        lr=3e-4,
        gamma=0.999,
        gae_lambda=0.95,
        ent_coef=0.01,
        n_steps=512,        # 512 * 8 envs = 4096 шагов за rollout ≈ 20 эпизодов
        batch_size=256,     # 4096 % 256 == 0
        n_epochs=10,
        clip_range=0.2,
        policy_type="cnn",
        features_dim=64,
        device="cuda",
        n_envs=8,
        use_subproc_env=True,
        normalize_rewards=True,
        common_seed=False,
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
        algorithm="ppo",
        algo_config=algo_cfg,
        config_path=_CONFIG,
        output_dir=os.path.join(PROJECT_ROOT, "runs", "16x16_forest"),
        run_id="ppo_forest_v3",
        total_timesteps=3_000_000,
        seed=42,
        exclude_layers=["terrain"],
        checkpoint_freq=150_000,
        use_tensorboard=True,
        validation_config=val_cfg,
    )
