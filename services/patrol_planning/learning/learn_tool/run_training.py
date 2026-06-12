"""Единая точка входа для обучения агентов патрулирования.

Использование:
    from services.patrol_planning.learning.learn_tool import run_training
    from packages.rl_algorithms.patrol_planning.rppo.train.rppo_train_config import RPPOTrainConfig

    run_training(
        algorithm="rppo",
        algo_config=RPPOTrainConfig(lr=1e-4, n_envs=8),
        config_path="services/patrol_planning/learning/configs/FOREST_DEFAULT.json",
        output_dir="runs/my_experiment",
        run_id="rppo_v1",
        total_timesteps=4_000_000,
    )

Структура директории запуска (создаётся автоматически):
    output_dir/
      {timestamp}_{run_id}/
        model/final          — финальная модель
        checkpoints/         — чекпоинты
        logs/                — TensorBoard логи
        configs/
          env_config.json    — копия конфига среды
          algo_config.json   — гиперпараметры алгоритма
          validation_config.json  — (если включена валидация)
"""
from __future__ import annotations

import dataclasses
import datetime
import json
import os
import shutil
from typing import TYPE_CHECKING, Literal, Optional, Union

if TYPE_CHECKING:
    from packages.rl_algorithms.patrol_planning.ppo.ppo_train_config import PPOTrainConfig
    from packages.rl_algorithms.patrol_planning.dqn.train.dqn_train_config import DQNTrainConfig
    from packages.rl_algorithms.patrol_planning.rppo.train.rppo_train_config import RPPOTrainConfig
    from packages.rl_algorithms.patrol_planning.alt_drqn.train.alt_drqn_train_config import AltDRQNTrainConfig

AlgorithmName = Literal["ppo", "dqn", "rppo", "alt_drqn"]


def _save_run_configs(
    run_dir: str,
    config_path: str,
    algo_config,
    val_cfg=None,
) -> None:
    cfg_dir = os.path.join(run_dir, "configs")
    os.makedirs(cfg_dir, exist_ok=True)
    shutil.copy2(config_path, os.path.join(cfg_dir, "env_config.json"))
    with open(os.path.join(cfg_dir, "algo_config.json"), "w", encoding="utf-8") as f:
        f.write(algo_config.model_dump_json(indent=2))
    if val_cfg is not None:
        with open(os.path.join(cfg_dir, "validation_config.json"), "w", encoding="utf-8") as f:
            val_dict = {
                k: v for k, v in dataclasses.asdict(val_cfg).items()
                if k != "shared_train_state"
            }
            json.dump(val_dict, f, indent=2, ensure_ascii=False)


def run_training(
    algorithm: AlgorithmName,
    algo_config: "Union[PPOTrainConfig, DQNTrainConfig, RPPOTrainConfig, AltDRQNTrainConfig]",
    config_path: str,
    output_dir: str,
    total_timesteps: int,
    run_id: str = "experiment",
    seed: int = 42,
    exclude_layers: Optional[list[str]] = None,
    show_render: bool = False,
    checkpoint_freq: int = 100_000,
    use_tensorboard: bool = True,
    enable_validation: bool = False,
    validation_freq: int = 20_000,
    validation_n_episodes: int = 20,
    validation_seed: int = 999,
    validation_config=None,
    setup_msvc: bool = True,
    inductor_cache: str = "C:/torchinductor_cache",
    triton_cache: str = "C:/triton_cache",
    compile_threads: int = 1,
    shared_train_state=None,
    step_delay: float = 0.0,
):
    """Запустить обучение выбранного алгоритма.

    Args:
        algorithm:             Алгоритм: "ppo", "dqn", "rppo" или "alt_drqn".
        algo_config:           Pydantic-модель с гиперпараметрами для выбранного алгоритма.
        config_path:           Путь к JSON-конфигу среды GridForest.
        output_dir:            Корневая директория для сохранения результатов. Внутри неё
                               автоматически создаётся поддиректория {timestamp}_{run_id}/.
        total_timesteps:       Общее число шагов обучения.
        run_id:                Метка запуска (добавляется к timestamp в имени папки).
        seed:                  Базовый seed для воспроизводимости.
        exclude_layers:        Слои наблюдения для исключения. None = дефолт алгоритма.
        show_render:           Показывать рендер среды во время обучения.
        checkpoint_freq:       Каждые N шагов сохранять чекпоинт.
        use_tensorboard:       Включить логирование в TensorBoard.
        enable_validation:     Включить периодическую валидацию во время обучения.
        validation_freq:       Каждые N шагов запускать валидацию.
        validation_n_episodes: Число эпизодов за одну валидацию.
        validation_seed:       Seed для eval-среды.
        validation_config:     Полный ValidationConfig (overrides enable_validation и прочие
                               validation_* параметры, если передан).
        setup_msvc:            Инъектировать MSVC env на Windows (нужно для torch.compile).
        inductor_cache:        Путь для TORCHINDUCTOR_CACHE_DIR.
        triton_cache:          Путь для TRITON_CACHE_DIR.
        compile_threads:       torch._inductor.config.compile_threads.
        shared_train_state:    Если передан (GridWorldTrainState), env[0] разделяет этот state
                               с вызывающим сервисом — для live-мониторинга через WebSocket.
                               None = каждая среда получает независимый state (режим standalone).

    Returns:
        Обученная модель (тип зависит от алгоритма).
    """
    from services.patrol_planning.learning.learn_tool.torch_setup import configure_torch

    use_compile = getattr(algo_config, "use_torch_compile", False)
    configure_torch(
        cpu_cores_num=getattr(algo_config, "cpu_cores_num", None),
        use_torch_compile=use_compile,
        setup_msvc=setup_msvc,
        inductor_cache=inductor_cache,
        triton_cache=triton_cache,
        compile_threads=compile_threads,
    )

    # ── Директории запуска ────────────────────────────────────────────────
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_folder = f"{timestamp}_{run_id}"
    run_dir = os.path.join(output_dir, run_folder)

    model_path    = os.path.join(run_dir, "model", "final")
    log_dir       = os.path.join(run_dir, "logs")
    checkpoints_dir = os.path.join(run_dir, "checkpoints")

    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(checkpoints_dir, exist_ok=True)
    os.makedirs(os.path.dirname(model_path), exist_ok=True)

    # ── ValidationConfig ──────────────────────────────────────────────────
    _val_cfg = validation_config
    if _val_cfg is None and enable_validation:
        from services.patrol_planning.learning.validation.training_validator import ValidationConfig
        _val_cfg = ValidationConfig(
            config_path=config_path,
            exclude_layers=exclude_layers or [],
            freq=validation_freq,
            n_episodes=validation_n_episodes,
            seed=validation_seed,
        )

    # ── Сохранить конфиги запуска ─────────────────────────────────────────
    _save_run_configs(run_dir, config_path, algo_config, _val_cfg)

    # ── Step-delay callback (режим визуализации) ──────────────────────────
    _extra_callbacks = None
    if step_delay > 0:
        import time
        from stable_baselines3.common.callbacks import BaseCallback

        class _StepDelayCallback(BaseCallback):
            def _on_step(self) -> bool:
                time.sleep(step_delay)
                return True

        _extra_callbacks = [_StepDelayCallback()]

    # ── Dispatch ──────────────────────────────────────────────────────────
    if algorithm == "ppo":
        from packages.rl_algorithms.patrol_planning.ppo.train import run_training_m
        return run_training_m(
            config_path=config_path,
            model_path=model_path,
            log_dir=log_dir,
            total_timesteps=total_timesteps,
            seed=seed,
            run_id=run_folder,
            exclude_layers=exclude_layers,
            show_render=show_render,
            render_delay=algo_config.render_delay,
            policy_type=algo_config.policy_type,
            features_dim=algo_config.features_dim,
            lr=algo_config.lr,
            gamma=algo_config.gamma,
            gae_lambda=algo_config.gae_lambda,
            ent_coef=algo_config.ent_coef,
            n_steps=algo_config.n_steps,
            batch_size=algo_config.batch_size,
            n_epochs=algo_config.n_epochs,
            clip_range=algo_config.clip_range,
            device=algo_config.device,
            n_envs=algo_config.n_envs,
            use_subproc_env=algo_config.use_subproc_env,
            common_seed=algo_config.common_seed,
            n_stack=algo_config.n_stack,
            cpu_cores_num=algo_config.cpu_cores_num,
            verbose=algo_config.verbose,
            normalize_rewards=algo_config.normalize_rewards,
            use_tensorboard=use_tensorboard,
            checkpoints_dir=checkpoints_dir,
            checkpoint_freq=checkpoint_freq,
            validation_config=_val_cfg,
            shared_train_state=shared_train_state,
            extra_callbacks=_extra_callbacks,
        )

    elif algorithm == "dqn":
        from packages.rl_algorithms.patrol_planning.dqn.train.train_dqn import run_training_dqn
        return run_training_dqn(
            config_path=config_path,
            model_path=model_path,
            log_dir=log_dir,
            checkpoints_dir=checkpoints_dir,
            total_timesteps=total_timesteps,
            seed=seed,
            run_id=run_folder,
            exclude_layers=exclude_layers,
            show_render=show_render,
            n_envs=algo_config.n_envs,
            use_cnn=algo_config.use_cnn,
            lr=algo_config.lr,
            _gamma=algo_config.gamma,
            batch_size=algo_config.batch_size,
            buffer_size=algo_config.buffer_size,
            learning_starts=algo_config.learning_starts,
            target_update_interval=algo_config.target_update_interval,
            exploration_fraction=algo_config.exploration_fraction,
            exploration_final_eps=algo_config.exploration_final_eps,
            checkpoint_freq=checkpoint_freq,
            use_torch_compile=algo_config.use_torch_compile,
            use_tensorboard=use_tensorboard,
            device=algo_config.device,
            cpu_cores_num=algo_config.cpu_cores_num,
            common_seed=algo_config.common_seed,
            features_dim=algo_config.features_dim,
            torch_compile_mode=algo_config.torch_compile_mode,
            checkpoint_name_prefix=algo_config.checkpoint_name_prefix,
            save_replay_buffer=algo_config.save_replay_buffer,
            reset_num_timesteps=algo_config.reset_num_timesteps,
            verbose=algo_config.verbose,
            normalize_rewards=algo_config.normalize_rewards,
            validation_config=_val_cfg,
            shared_train_state=shared_train_state,
            extra_callbacks=_extra_callbacks,
        )

    elif algorithm == "rppo":
        from packages.rl_algorithms.patrol_planning.rppo.train.train_rppo import run_training_rppo
        return run_training_rppo(
            config_path=config_path,
            model_path=model_path,
            log_dir=log_dir,
            checkpoints_dir=checkpoints_dir,
            total_timesteps=total_timesteps,
            seed=seed,
            run_id=run_folder,
            exclude_layers=exclude_layers,
            show_render=show_render,
            n_steps=algo_config.n_steps,
            batch_size=algo_config.batch_size,
            lstm_hidden_size=algo_config.lstm_hidden_size,
            n_envs=algo_config.n_envs,
            _gamma=algo_config.gamma,
            _ent_coef=algo_config.ent_coef,
            _lr=algo_config.lr,
            use_cnn=algo_config.use_cnn,
            use_torch_compile=algo_config.use_torch_compile,
            use_tensorboard=use_tensorboard,
            device=algo_config.device,
            cpu_cores_num=algo_config.cpu_cores_num,
            use_subproc_env=algo_config.use_subproc_env,
            common_seed=algo_config.common_seed,
            gae_lambda=algo_config.gae_lambda,
            verbose=algo_config.verbose,
            n_lstm_layers=algo_config.n_lstm_layers,
            shared_lstm=algo_config.shared_lstm,
            net_arch=algo_config.net_arch,
            features_dim=algo_config.features_dim,
            checkpoint_save_freq=checkpoint_freq,
            checkpoint_name_prefix=algo_config.checkpoint_name_prefix,
            save_replay_buffer=algo_config.save_replay_buffer,
            validation_config=_val_cfg,
            shared_train_state=shared_train_state,
            extra_callbacks=_extra_callbacks,
        )

    elif algorithm == "alt_drqn":
        from packages.rl_algorithms.patrol_planning.alt_drqn.train.train_alt_drqn import run_training_alt_drqn
        return run_training_alt_drqn(
            config_path=config_path,
            model_path=model_path,
            log_dir=log_dir,
            checkpoints_dir=checkpoints_dir,
            total_timesteps=total_timesteps,
            seed=seed,
            run_id=run_folder,
            exclude_layers=exclude_layers,
            lr=algo_config.lr,
            _gamma=algo_config.gamma,
            batch_size=algo_config.batch_size,
            lstm_hidden_size=algo_config.lstm_hidden_size,
            unroll_length=algo_config.unroll_length,
            buffer_capacity=algo_config.buffer_capacity,
            learning_starts=algo_config.learning_starts,
            target_update_freq=algo_config.target_update_freq,
            epsilon_decay_steps=algo_config.epsilon_decay_steps,
            epsilon_final=algo_config.epsilon_final,
            train_freq=algo_config.train_freq,
            log_interval=algo_config.log_interval,
            checkpoint_freq=checkpoint_freq,
            n_envs=algo_config.n_envs,
            use_amp=algo_config.use_amp,
            normalize_rewards=algo_config.normalize_rewards,
            burn_in=algo_config.burn_in,
            use_tensorboard=use_tensorboard,
            device=algo_config.device,
            cpu_cores_num=algo_config.cpu_cores_num,
            common_seed=algo_config.common_seed,
            validation_config=_val_cfg,
            shared_train_state=shared_train_state,
            step_delay=step_delay,
        )

    else:
        raise ValueError(
            f"Неизвестный алгоритм: {algorithm!r}. "
            "Допустимые значения: 'ppo', 'dqn', 'rppo', 'alt_drqn'."
        )
