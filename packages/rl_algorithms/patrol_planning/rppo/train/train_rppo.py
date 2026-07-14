"""RecurrentPPO (LSTM-PPO) training pipeline для POMDP патрулирования леса.

Запуск из корня проекта:
    python services/patrol_planning/research/r_ppo/train/train_rppo.py
"""

import sys
import os
import time

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..")
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

_R_PPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


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


def _build_vec_env(make_env_fn, n_envs: int, seed: int, common_seed: bool):
    from stable_baselines3.common.env_util import make_vec_env
    from stable_baselines3.common.vec_env import SubprocVecEnv

    if common_seed:
        return make_vec_env(make_env_fn, n_envs=n_envs, vec_env_cls=SubprocVecEnv)

    from stable_baselines3.common.monitor import Monitor

    def _seeded_factory(s):
        def _fn():
            env = make_env_fn()
            env.reset(seed=s)
            return Monitor(env)
        return _fn

    return SubprocVecEnv([_seeded_factory(seed + i) for i in range(n_envs)])


def run_training_rppo(
    config_path: str = "services/patrol_planning/research/r_ppo/config_8x8_rppo.json",
    exclude_layers: list[str] | None = None,
    model_path: str = "services/patrol_planning/research/r_ppo/models/rppo_8x8_final",
    log_dir: str = "services/patrol_planning/research/r_ppo/logs",
    checkpoints_dir: str = "services/patrol_planning/research/r_ppo/checkpoints",
    total_timesteps: int = 500_000,
    seed: int = 42,
    run_id: str | None = None,
    show_render: bool = False,
    n_steps: int = 256,
    batch_size: int = 64,
    lstm_hidden_size: int = 256,
    n_envs: int = 4,
    _gamma: float = 0.995,
    _ent_coef: float = 0.03,
    _lr: float = 3e-4,
    use_cnn: bool = True,
    use_torch_compile: bool = False,
    device: str = "cuda",
    cpu_cores_num: int | None = None,
    use_subproc_env: bool = False,
    common_seed: bool = True,
    gae_lambda: float = 0.95,
    verbose: int = 1,
    n_lstm_layers: int = 1,
    shared_lstm: bool = False,
    net_arch: list[int] | None = None,
    features_dim: int = 128,
    checkpoint_save_freq: int = 100_000,
    checkpoint_name_prefix: str = "rppo",
    save_replay_buffer: bool = False,
    use_tensorboard: bool = True,
    validation_config=None,
    shared_train_state=None,
    extra_callbacks=None,
):
    import json
    import contextlib
    import random
    import numpy as np

    from sb3_contrib import RecurrentPPO
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
        algo_name="RPPO",
        config=config,
        hparams=dict(
            lr=_lr, gamma=_gamma, gae_lambda=gae_lambda, ent_coef=_ent_coef,
            n_steps=n_steps, batch_size=batch_size,
            lstm_hidden_size=lstm_hidden_size, n_lstm_layers=n_lstm_layers,
            shared_lstm=shared_lstm, use_cnn=use_cnn, features_dim=features_dim,
            use_torch_compile=use_torch_compile,
        ),
        meta=dict(
            total_timesteps=total_timesteps, seed=seed, device=device,
            n_envs=n_envs, run_id=run_id, checkpoint_save_freq=checkpoint_save_freq,
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

    assert (n_steps * n_envs) % batch_size == 0, (
        f"n_steps * n_envs ({n_steps * n_envs}) должно делиться на batch_size ({batch_size})"
    )

    if use_subproc_env:
        vec_env = _build_vec_env(make_env, n_envs, seed, common_seed)
    else:
        vec_env = make_vec_env(make_env, n_envs=n_envs)

    if use_cnn:
        policy_kwargs = {
            "features_extractor_class": CNNExtractor5x5,
            "features_extractor_kwargs": {"features_dim": features_dim},
            "lstm_hidden_size": lstm_hidden_size,
            "n_lstm_layers": n_lstm_layers,
            "shared_lstm": shared_lstm,
        }
    else:
        policy_kwargs = {
            "lstm_hidden_size": lstm_hidden_size,
            "n_lstm_layers": n_lstm_layers,
            "shared_lstm": shared_lstm,
            "net_arch": net_arch if net_arch is not None else [64, 64],
        }

    model = RecurrentPPO(
        policy="MlpLstmPolicy",
        env=vec_env,
        learning_rate=_lr,
        n_steps=n_steps,
        batch_size=batch_size,
        gamma=_gamma,
        gae_lambda=gae_lambda,
        ent_coef=_ent_coef,
        policy_kwargs=policy_kwargs,
        tensorboard_log=run_log_dir,
        verbose=verbose,
        device=device,
    )

    if use_torch_compile:
        import torch
        try:
            # inductor на CPU падает на Windows с пробелом в пути пользователя
            # (cl.exe не получает закавыченные пути). aot_eager даёт трассировку
            # без C++-компиляции и работает на обоих устройствах.
            _backend = "inductor" if str(model.device) != "cpu" else "aot_eager"
            model.policy = torch.compile(model.policy, backend=_backend)
            print("torch.compile: OK")
        except Exception as e:
            print(f"[WARNING] torch.compile недоступен, обучение без компиляции. Причина: {e}")

    print("ЗАПУЩЕНО НА:", model.device)
    if cpu_cores_num is not None:
        import torch
        print(f"CPU threads={torch.get_num_threads()}")

    checkpoint_cb = CheckpointCallback(
        save_freq=checkpoint_save_freq,
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
        callbacks.append(SB3ValidationCallback(validation_config, model_type="rppo"))

    renderer = GridWorldRendererExt(make_env, True, "intruders", True, "intruders")

    print(f"\n=== Начало обучения RecurrentPPO: {total_timesteps} шагов | run={run_id} ===\n")

    if extra_callbacks:
        callbacks.extend(extra_callbacks)

    with (renderer.live if show_render else contextlib.nullcontext()):
        model.learn(
            total_timesteps=total_timesteps,
            callback=callbacks,
            reset_num_timesteps=False,
        )

    os.makedirs(os.path.dirname(os.path.abspath(model_path)), exist_ok=True)
    model.save(model_path)
    print(f"\nМодель сохранена: {model_path}")

    print("\n── Итоги обучения ────────────────────────────────────")
    print(f"Начальная ценность леса: {initial_total_value:.1f}")
    print("Обучение завершено.")
    print("──────────────────────────────────────────────────────")

    return model


def run_tuning_rppo(
    model_path_load: str,
    config_path: str = "services/patrol_planning/research/r_ppo/config_8x8_rppo.json",
    exclude_layers: list[str] | None = None,
    model_path: str = "services/patrol_planning/research/r_ppo/models/rppo_8x8_tuned",
    log_dir: str = "services/patrol_planning/research/r_ppo/logs",
    checkpoints_dir: str = "services/patrol_planning/research/r_ppo/checkpoints",
    total_timesteps: int = 500_000,
    seed: int = 42,
    run_id: str | None = None,
    show_render: bool = False,
    n_steps: int = 256,
    batch_size: int = 64,
    n_envs: int = 4,
    _gamma: float = 0.995,
    _ent_coef: float = 0.01,
    _lr: float = 1e-4,
    use_cnn: bool = True,
    use_torch_compile: bool = False,
    device: str = "cuda",
    cpu_cores_num: int | None = None,
    use_subproc_env: bool = False,
    common_seed: bool = True,
):
    import json
    import contextlib
    import random
    import numpy as np

    from sb3_contrib import RecurrentPPO
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

    run_log_dir = os.path.join(log_dir, run_id)

    def make_env():
        env = GridForest.load(config)
        env.train_state = GridWorldTrainState()
        return env

    tmp_env = make_env()
    tmp_env.reset(seed=seed)
    initial_total_value = float(tmp_env.world_layers["value"].sum())

    assert (n_steps * n_envs) % batch_size == 0, (
        f"n_steps * n_envs ({n_steps * n_envs}) должно делиться на batch_size ({batch_size})"
    )

    if use_subproc_env:
        vec_env = _build_vec_env(make_env, n_envs, seed, common_seed)
    else:
        vec_env = make_vec_env(make_env, n_envs=n_envs)

    custom_objects = {
        "learning_rate": _lr,
        "ent_coef": _ent_coef,
        "gamma": _gamma,
        "gae_lambda": 0.95,
    }
    if use_cnn:
        custom_objects["features_extractor_class"] = CNNExtractor5x5

    model = RecurrentPPO.load(
        model_path_load,
        env=vec_env,
        device=device,
        custom_objects=custom_objects,
        tensorboard_log=run_log_dir,
    )

    model._setup_model()

    _compiled = False
    if use_torch_compile:
        import torch
        try:
            _backend = "inductor" if str(model.device) != "cpu" else "aot_eager"
            model.policy = torch.compile(model.policy, backend=_backend)
            _compiled = True
        except Exception as e:
            print(f"[WARNING] torch.compile недоступен, дообучение без компиляции. Причина: {e}")

    print("ДООБУЧЕНИЕ МОДЕЛИ:", model_path_load)
    print("ЗАПУЩЕНО НА:", model.device)
    extractor_name = "CNNExtractor5x5" if use_cnn else "FlattenMLP[64,64]"
    vec_name = f"SubprocVecEnv(common_seed={common_seed})" if use_subproc_env else "DummyVecEnv"
    print(f"ЭКСТРАКТОР: {extractor_name} | torch.compile={_compiled}")
    print(f"lr={_lr}, ent_coef={_ent_coef}, gamma={_gamma}")
    print(f"n_envs={n_envs}, n_steps={n_steps}, batch_size={batch_size} | vec={vec_name}")
    if cpu_cores_num is not None:
        import torch
        print(f"CPU threads={torch.get_num_threads()}")

    checkpoint_cb = CheckpointCallback(
        save_freq=100_000,
        save_path=checkpoints_dir,
        name_prefix="rppo_tuned",
        save_replay_buffer=False,
        verbose=1,
    )

    renderer = GridWorldRendererExt(make_env, True, "intruders", True, "intruders")

    print(f"\n=== Дообучение RecurrentPPO: {total_timesteps} шагов | run={run_id} ===\n")

    with (renderer.live if show_render else contextlib.nullcontext()):
        model.learn(
            total_timesteps=total_timesteps,
            callback=[checkpoint_cb, SpeedLoggerCallback()],
            reset_num_timesteps=False,
        )

    os.makedirs(os.path.dirname(os.path.abspath(model_path)), exist_ok=True)
    model.save(model_path)
    print(f"\nМодель сохранена: {model_path}")

    print("\n── Итоги дообучения ──────────────────────────────────")
    print(f"Начальная ценность леса: {initial_total_value:.1f}")
    print("Дообучение завершено.")
    print("──────────────────────────────────────────────────────")

    return model


if __name__ == "__main__":
     run_training_rppo(
        config_path=os.path.join(_R_PPO_DIR, "config_8x8_rppo.json"),
        model_path=os.path.join(_R_PPO_DIR, "models", "rppo_8x8_final"),
        log_dir=os.path.join(_R_PPO_DIR, "logs"),
        checkpoints_dir=os.path.join(_R_PPO_DIR, "checkpoints"),
        total_timesteps=500_000,
        seed=42,
        run_id="rppo_8x8_v1",
    )
