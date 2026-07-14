"""DQN training pipeline для патрулирования леса (SB3).

Запуск из корня проекта:
    python services/patrol_planning/research/dqn/train/train_dqn.py
"""

import sys
import os
import time

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..")
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

_DQN_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_R_PPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "r_ppo"))


from stable_baselines3.common.callbacks import BaseCallback


class SpeedLoggerCallback(BaseCallback):
    """Печатает Δt и шагов/с сразу под каждой таблицей SB3."""

    def __init__(self, shared_train_state=None):
        super().__init__(verbose=0)
        self._last_time: float = 0.0
        self._last_timesteps: int = 0
        self._shared_state = shared_train_state

    def _on_training_start(self) -> None:
        self._last_time = time.perf_counter()
        self._last_timesteps = self.model.num_timesteps
        original_dump = self.model.logger.dump
        cb = self

        def _patched_dump(step=None):
            _vals = dict(cb.model.logger.name_to_value) if cb._shared_state is not None else {}
            original_dump(step)
            now = time.perf_counter()
            dt = now - cb._last_time
            d_steps = cb.model.num_timesteps - cb._last_timesteps
            if dt > 0 and d_steps > 0:
                fps = d_steps / dt
                print(f"  ↳ Δt={dt:.1f}s | {fps:.0f} шагов/с")
                if cb._shared_state is not None:
                    m = {"fps": round(fps, 1)}
                    for k, short in (
                        ("rollout/ep_rew_mean", "ep_rew_mean"),
                        ("rollout/ep_len_mean", "ep_len_mean"),
                        ("time/total_timesteps", "global_step"),
                    ):
                        if k in _vals:
                            m[short] = round(float(_vals[k]), 4)
                    cb._shared_state["train_metrics"] = m
            cb._last_time = now
            cb._last_timesteps = cb.model.num_timesteps

        self.model.logger.dump = _patched_dump

    def _on_step(self) -> bool:
        return True


def run_training_dqn(
    config_path: str = "services/patrol_planning/research/r_ppo/config_8x8_rppo.json",
    exclude_layers: list[str] | None = None,
    model_path: str = "services/patrol_planning/research/dqn/models/dqn_8x8_final",
    log_dir: str = "services/patrol_planning/research/dqn/logs",
    checkpoints_dir: str = "services/patrol_planning/research/dqn/checkpoints",
    total_timesteps: int = 500_000,
    seed: int = 42,
    run_id: str | None = None,
    show_render: bool = False,
    n_envs: int = 1,
    use_cnn: bool = True,
    lr: float = 1e-4,
    _gamma: float = 0.99,
    batch_size: int = 32,
    buffer_size: int = 50_000,
    learning_starts: int = 1_000,
    target_update_interval: int = 500,
    exploration_fraction: float = 0.2,
    exploration_final_eps: float = 0.05,
    checkpoint_freq: int = 100_000,
    use_torch_compile: bool = False,
    use_tensorboard: bool = True,
    device: str = "cuda",
    cpu_cores_num: int | None = None,
    common_seed: bool = True,
    features_dim: int = 128,
    torch_compile_mode: str = "reduce-overhead",
    checkpoint_name_prefix: str = "dqn",
    save_replay_buffer: bool = False,
    reset_num_timesteps: bool = False,
    verbose: int = 1,
    normalize_rewards: bool = False,
    validation_config=None,
    shared_train_state=None,
    extra_callbacks=None,
):
    import json
    import contextlib
    import random
    import numpy as np

    from stable_baselines3 import DQN
    from stable_baselines3.common.env_util import make_vec_env
    from stable_baselines3.common.callbacks import CheckpointCallback

    from services.patrol_planning.assets.envs.forest import GridForest
    from services.patrol_planning.assets.envs.models import GridForestConfig
    from services.patrol_planning.src.renderer_extended import GridWorldRendererExt
    from services.patrol_planning.service.models import GridWorldTrainState

    if use_cnn:
        from packages.rl_algorithms.patrol_planning.rppo.networks.cnn_extractor_5x5 import CNNExtractor5x5

    if exclude_layers is None:
        exclude_layers = ["terrain", "rows", "cols", "passability"]
    if run_id is None:
        run_id = f"seed_{seed}"

    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        if cpu_cores_num is not None:
            torch.set_num_threads(cpu_cores_num)
    except ImportError:
        pass

    with open(config_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)

    config = GridForestConfig.model_validate(config_data)
    config.obs_config.exclude_layers = exclude_layers
    config.metrics_config.enabled = False

    run_log_dir = os.path.join(log_dir, run_id) if use_tensorboard else None

    from services.patrol_planning.learning.learn_tool.print_utils import print_training_header
    print_training_header(
        algo_name="DQN",
        config=config,
        hparams=dict(
            lr=lr, gamma=_gamma, batch_size=batch_size, buffer_size=buffer_size,
            learning_starts=learning_starts, target_update_interval=target_update_interval,
            exploration_fraction=exploration_fraction, exploration_final_eps=exploration_final_eps,
            use_cnn=use_cnn, features_dim=features_dim, use_torch_compile=use_torch_compile,
            normalize_rewards=normalize_rewards,
        ),
        meta=dict(
            total_timesteps=total_timesteps, seed=seed, device=device,
            n_envs=n_envs, run_id=run_id, checkpoint_freq=checkpoint_freq,
            use_tensorboard=use_tensorboard,
        ),
    )

    _tmp = GridForest.load(config)
    _tmp.train_state = GridWorldTrainState()
    _tmp.reset(seed=seed)
    initial_total_value = float(_tmp.world_layers["value"].sum())
    del _tmp

    _env_counter = [0]

    def make_env():
        is_first = _env_counter[0] == 0
        _env_counter[0] += 1
        env = GridForest.load(config)
        env.train_state = (
            shared_train_state if (shared_train_state is not None and is_first)
            else GridWorldTrainState()
        )
        return env

    vec_env = make_vec_env(make_env, n_envs=n_envs, seed=None if common_seed else seed)

    if normalize_rewards:
        from stable_baselines3.common.vec_env import VecNormalize
        vec_env = VecNormalize(vec_env, norm_obs=False, norm_reward=True,
                               clip_reward=10.0, gamma=_gamma)

    if use_cnn:
        policy_kwargs = {
            "features_extractor_class": CNNExtractor5x5,
            "features_extractor_kwargs": {"features_dim": features_dim},
        }
        policy = "CnnPolicy"
    else:
        policy_kwargs = {}
        policy = "MlpPolicy"

    model = DQN(
        policy=policy,
        env=vec_env,
        learning_rate=lr,
        buffer_size=buffer_size,
        learning_starts=learning_starts,
        batch_size=batch_size,
        gamma=_gamma,
        target_update_interval=target_update_interval,
        exploration_fraction=exploration_fraction,
        exploration_final_eps=exploration_final_eps,
        policy_kwargs=policy_kwargs,
        tensorboard_log=run_log_dir,
        verbose=verbose,
        device=device,
    )

    _compiled = False
    if use_torch_compile:
        import torch
        try:
            model.policy = torch.compile(model.policy, mode=torch_compile_mode)
            _compiled = True
        except Exception as e:
            print(f"[WARNING] torch.compile недоступен, обучение без компиляции. Причина: {e}")

    print("ЗАПУЩЕНО НА:", model.device)
    if cpu_cores_num is not None:
        import torch
        print(f"CPU threads={torch.get_num_threads()}")

    checkpoint_cb = CheckpointCallback(
        save_freq=max(checkpoint_freq // n_envs, 1),
        save_path=checkpoints_dir,
        name_prefix=checkpoint_name_prefix,
        save_replay_buffer=save_replay_buffer,
        verbose=verbose,
    )

    callbacks = [checkpoint_cb, SpeedLoggerCallback(shared_train_state)]
    if shared_train_state is not None:
        class _StopCallback(BaseCallback):
            def _on_step(self):
                return bool(shared_train_state["running"])
        callbacks.append(_StopCallback())
    if validation_config is not None:
        from services.patrol_planning.learning.validation.training_validator import SB3ValidationCallback
        callbacks.append(SB3ValidationCallback(validation_config, model_type="dqn"))

    renderer = GridWorldRendererExt(make_env, True, "intruders", True, "intruders")

    print(f"\n=== Начало обучения DQN: {total_timesteps} шагов | run={run_id} ===\n")

    if extra_callbacks:
        callbacks.extend(extra_callbacks)

    with (renderer.live if show_render else contextlib.nullcontext()):
        model.learn(
            total_timesteps=total_timesteps,
            callback=callbacks,
            reset_num_timesteps=reset_num_timesteps,
        )

    os.makedirs(os.path.dirname(os.path.abspath(model_path)), exist_ok=True)
    model.save(model_path)
    print(f"\nМодель сохранена: {model_path}")

    print("\n── Итоги обучения ────────────────────────────────────")
    print(f"Начальная ценность леса: {initial_total_value:.1f}")
    print("Обучение завершено.")
    print("──────────────────────────────────────────────────────")

    return model


if __name__ == "__main__":
    run_training_dqn(
        config_path=os.path.join(_R_PPO_DIR, "config_8x8_rppo.json"),
        model_path=os.path.join(_DQN_DIR, "models", "dqn_8x8_final"),
        log_dir=os.path.join(_DQN_DIR, "logs"),
        checkpoints_dir=os.path.join(_DQN_DIR, "checkpoints"),
        total_timesteps=500_000,
        seed=42,
        run_id="dqn_8x8_v1",
    )
