import sys
import os
import time

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


from stable_baselines3.common.callbacks import BaseCallback


class SpeedLoggerCallback(BaseCallback):
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


def _plot_page1_train(logger, save_dir: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec

    os.makedirs(save_dir, exist_ok=True)

    df_ep = logger.episodes_to_df()
    heatmap = logger.get_heatmap()
    idleness_hm = logger.get_idleness_heatmap()
    intruder_hm = logger.get_intruder_heatmap()
    damage_hm = logger.get_damage_heatmap()
    action_hist = logger.get_action_histogram()
    action_labels = ["UP", "DOWN", "LEFT", "RIGHT", "STAY"]

    fig = plt.figure(figsize=(18, 12))
    fig.suptitle(
        f"Метрики среды  |  run={logger.run_id}  |  эпизодов: {logger.episode_count}",
        fontsize=14,
    )
    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.4, wspace=0.35)

    ax_intr = fig.add_subplot(gs[0, 0])
    im_intr = ax_intr.imshow(intruder_hm.T, origin="lower", cmap="hot", aspect="equal")
    fig.colorbar(im_intr, ax=ax_intr, label="шагов/эп.")
    ax_intr.set_title("Тепловая карта нарушителей\n(среднее шагов присутствия)")
    ax_intr.set_xlabel("x"); ax_intr.set_ylabel("y")

    ax_dmg = fig.add_subplot(gs[0, 1])
    im_dmg = ax_dmg.imshow(damage_hm.T, origin="lower", cmap="YlOrRd", aspect="equal")
    fig.colorbar(im_dmg, ax=ax_dmg, label="ценности/эп.")
    ax_dmg.set_title("Тепловая карта урона лесу\n(средний урон за эпизод, ↑ хуже)")
    ax_dmg.set_xlabel("x"); ax_dmg.set_ylabel("y")

    ax_vl = fig.add_subplot(gs[0, 2])
    if not df_ep.empty and "total_damage" in df_ep:
        ax_vl.plot(df_ep["episode"], df_ep["total_damage"], alpha=0.4, color="tomato", label="эпизод")
        vl_roll = df_ep["total_damage"].rolling(50, min_periods=1).mean()
        ax_vl.plot(df_ep["episode"], vl_roll, color="tomato", linewidth=2, label="скольз. среднее 50")
        ax_vl.legend(fontsize=8)
    ax_vl.set_title("Потеря ценности леса\n(урон нарушителей за эпизод, ↓ лучше)")
    ax_vl.set_xlabel("эпизод"); ax_vl.set_ylabel("потеря ценности")

    ax_hm = fig.add_subplot(gs[1, 0])
    im = ax_hm.imshow(heatmap.T, origin="lower", cmap="hot", aspect="equal")
    fig.colorbar(im, ax=ax_hm, label="посещений")
    ax_hm.set_title("Тепловая карта агента\n(кол-во посещений)")
    ax_hm.set_xlabel("x"); ax_hm.set_ylabel("y")

    ax_idle = fig.add_subplot(gs[1, 1])
    im2 = ax_idle.imshow(idleness_hm.T, origin="lower", cmap="RdYlGn_r", aspect="equal")
    fig.colorbar(im2, ax=ax_idle, label="шагов")
    ax_idle.set_title("Тепловая карта покрытия\n(среднее время простоя, ↑ хуже)")
    ax_idle.set_xlabel("x"); ax_idle.set_ylabel("y")

    ax_act = fig.add_subplot(gs[1, 2])
    bars = ax_act.bar(action_labels, action_hist, color="steelblue", edgecolor="white")
    for bar, val in zip(bars, action_hist):
        ax_act.text(
            bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
            f"{val:.2%}", ha="center", va="bottom", fontsize=9,
        )
    ax_act.set_title("Гистограмма действий\n(доля от всех шагов)")
    ax_act.set_ylim(0, max(action_hist) * 1.2 + 0.05)
    ax_act.set_ylabel("доля")

    path1 = os.path.join(save_dir, "train_page1.png")
    fig.savefig(path1, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"  Сохранено: {path1}")


def _plot_page2_train(logger, save_dir: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec

    os.makedirs(save_dir, exist_ok=True)

    df_ep = logger.episodes_to_df()
    df_sb3 = logger.sb3_metrics_to_df()

    sb3_cols = [c for c in df_sb3.columns if c not in ("run_id", "timestep")] if not df_sb3.empty else []
    priority = [
        "train/policy_gradient_loss", "train/value_loss", "train/entropy_loss",
        "train/approx_kl", "train/explained_variance", "rollout/ep_rew_mean",
    ]
    plot_cols = [c for c in priority if c in sb3_cols] + [c for c in sb3_cols if c not in priority]
    plot_cols = plot_cols[:6]

    has_sb3 = bool(plot_cols) and not df_sb3.empty
    nrows_sb3 = (len(plot_cols) + 2) // 3 if has_sb3 else 0
    total_rows = 1 + nrows_sb3

    fig = plt.figure(figsize=(18, 5 * total_rows))
    fig.suptitle(
        f"RL-метрики обучения  |  run={logger.run_id}  |  эпизодов: {logger.episode_count}",
        fontsize=14,
    )
    gs = gridspec.GridSpec(total_rows, 3, figure=fig, hspace=0.4, wspace=0.35)

    ax_rew = fig.add_subplot(gs[0, 0])
    if not df_ep.empty and "total_reward" in df_ep:
        ax_rew.plot(df_ep["episode"], df_ep["total_reward"], alpha=0.4, color="royalblue", label="эпизод")
        ax_rew.plot(df_ep["episode"], df_ep["reward_rolling_50"], color="royalblue", linewidth=2, label="скольз. среднее 50")
        ax_rew.legend(fontsize=8)
    ax_rew.set_title("Суммарная награда по эпизодам")
    ax_rew.set_xlabel("эпизод"); ax_rew.set_ylabel("reward")

    ax_z = fig.add_subplot(gs[0, 1])
    if not df_ep.empty and "metric_Z" in df_ep:
        ax_z.plot(df_ep["episode"], df_ep["metric_Z"], color="tomato", alpha=0.5, label="Z (↓ лучше)")
        z_roll = df_ep["metric_Z"].rolling(50, min_periods=1).mean()
        ax_z.plot(df_ep["episode"], z_roll, color="tomato", linewidth=2)
        ax_z.legend(fontsize=8)
    ax_z.set_title("Целевая функция Z(π)\nM_damage + M_move + M_idleness")
    ax_z.set_xlabel("эпизод"); ax_z.set_ylabel("Z")

    ax_catch = fig.add_subplot(gs[0, 2])
    if not df_ep.empty and "catch_rate" in df_ep:
        ax_catch.plot(df_ep["episode"], df_ep["catch_rate"], color="seagreen", alpha=0.4)
        cr_roll = df_ep["catch_rate"].rolling(50, min_periods=1).mean()
        ax_catch.plot(df_ep["episode"], cr_roll, color="seagreen", linewidth=2)
        ax_catch.set_ylim(-0.05, 1.05)
    ax_catch.set_title("Доля пойманных нарушителей")
    ax_catch.set_xlabel("эпизод"); ax_catch.set_ylabel("catch rate")

    if has_sb3:
        ncols = 3
        for idx, col in enumerate(plot_cols):
            r, c = divmod(idx, ncols)
            ax = fig.add_subplot(gs[1 + r, c])
            ax.plot(df_sb3["timestep"], df_sb3[col], linewidth=1.5)
            ax.set_title(col.replace("train/", "").replace("rollout/", ""), fontsize=10)
            ax.set_xlabel("timestep"); ax.grid(True, alpha=0.3)
        for idx in range(len(plot_cols), nrows_sb3 * ncols):
            r, c = divmod(idx, ncols)
            fig.add_subplot(gs[1 + r, c]).set_visible(False)

    path2 = os.path.join(save_dir, "train_page2.png")
    fig.savefig(path2, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"  Сохранено: {path2}")

def _build_policy(policy_type: str, features_dim: int = 64):
    if policy_type == "cnn":
        from packages.rl_algorithms.patrol_planning.rppo.networks.cnn_extractor_5x5 import CNNExtractor5x5
        kwargs = {
            "features_extractor_class": CNNExtractor5x5,
            "features_extractor_kwargs": {"features_dim": features_dim},
            "normalize_images": False,
        }
        return "CnnPolicy", kwargs
    elif policy_type == "mlp":
        return "MlpPolicy", {}
    else:
        raise ValueError(policy_type)

def run_training_m(
    config_path: str = "services/patrol_planning/learning/configs/research/4x4_no_obstacle.json",
    exclude_layers: list[str] | None = None,
    model_path: str = "services/patrol_planning/learning/models/ppo_forest_agent_1",
    log_dir: str = "services/patrol_planning/learning/logs",
    total_timesteps: int = 20_000,
    seed: int = 42,
    run_id: str | None = None,
    show_render: bool = False,
    render_delay: float = 0.1,
    policy_type: str = "mlp",
    features_dim: int = 64,
    lr: float = 3e-4,
    gamma: float = 0.99,
    gae_lambda: float = 0.95,
    ent_coef: float = 0.0,
    n_steps: int = 2048,
    batch_size: int = 64,
    n_epochs: int = 10,
    clip_range: float = 0.2,
    device: str = "cpu",
    n_envs: int = 4,
    use_subproc_env: bool = False,
    common_seed: bool = True,
    n_stack: int = 1,
    cpu_cores_num: int | None = None,
    verbose: int = 1,
    normalize_rewards: bool = False,
    validation_config=None,
    use_tensorboard: bool = True,
    checkpoints_dir: str | None = None,
    checkpoint_freq: int = 100_000,
    shared_train_state=None,
    extra_callbacks=None,
):
    import os
    import json
    import contextlib
    import random
    import numpy as np

    from stable_baselines3 import PPO
    from stable_baselines3.common.env_util import make_vec_env

    from services.patrol_planning.assets.envs.forest import GridForest
    from services.patrol_planning.assets.envs.models import GridForestConfig
    from services.patrol_planning.src.renderer_extended import GridWorldRendererExt
    from services.patrol_planning.service.models import GridWorldTrainState

    if exclude_layers is None:
        exclude_layers = ["terrain", "rows", "cols"]
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

    if use_subproc_env:
        vec_env = _build_vec_env(make_env, n_envs, seed, common_seed)
    else:
        vec_env = make_vec_env(make_env, n_envs=n_envs)

    if n_stack > 1:
        from stable_baselines3.common.vec_env import VecFrameStack
        vec_env = VecFrameStack(vec_env, n_stack=n_stack, channels_order="first")

    if normalize_rewards:
        from stable_baselines3.common.vec_env import VecNormalize
        vec_env = VecNormalize(vec_env, norm_obs=False, norm_reward=True,
                               clip_reward=10.0, gamma=gamma)

    _policy, _policy_kwargs = _build_policy(policy_type, features_dim)
    model = PPO(
        policy=_policy,
        env=vec_env,
        verbose=verbose,
        device=device,
        learning_rate=lr,
        gamma=gamma,
        gae_lambda=gae_lambda,
        ent_coef=ent_coef,
        n_steps=n_steps,
        batch_size=batch_size,
        n_epochs=n_epochs,
        clip_range=clip_range,
        policy_kwargs=_policy_kwargs,
        tensorboard_log=run_log_dir,
    )

    from services.patrol_planning.learning.learn_tool.print_utils import print_training_header
    vec_name = f"SubprocVecEnv(common_seed={common_seed})" if use_subproc_env else "DummyVecEnv"
    print_training_header(
        algo_name="PPO",
        config=config,
        hparams=dict(
            lr=lr, gamma=gamma, gae_lambda=gae_lambda, ent_coef=ent_coef,
            n_steps=n_steps, batch_size=batch_size, n_epochs=n_epochs,
            clip_range=clip_range, policy_type=policy_type, n_stack=n_stack,
            normalize_rewards=normalize_rewards,
        ),
        meta=dict(
            total_timesteps=total_timesteps, seed=seed, run_id=run_id,
            device=device, n_envs=n_envs, vec_env=vec_name,
            tensorboard=use_tensorboard,
            checkpoints=checkpoints_dir or "disabled",
        ),
    )

    renderer = GridWorldRendererExt(make_env, True, "intruders", True, "intruders")

    print(f"\n=== Начало обучения PPO: {total_timesteps} шагов | run={run_id} ===\n")

    from stable_baselines3.common.callbacks import CheckpointCallback
    callbacks = [SpeedLoggerCallback(shared_train_state)]
    if shared_train_state is not None:
        class _StopCallback(BaseCallback):
            def _on_step(self):
                return bool(shared_train_state["running"])
        callbacks.append(_StopCallback())
    if checkpoints_dir is not None:
        os.makedirs(checkpoints_dir, exist_ok=True)
        callbacks.insert(0, CheckpointCallback(
            save_freq=max(checkpoint_freq // n_envs, 1),
            save_path=checkpoints_dir,
            name_prefix="ppo",
            verbose=verbose,
        ))
    if validation_config is not None:
        from services.patrol_planning.learning.validation.training_validator import SB3ValidationCallback
        callbacks.append(SB3ValidationCallback(validation_config, model_type="ppo"))

    if extra_callbacks:
        callbacks.extend(extra_callbacks)

    with (renderer.live if show_render else contextlib.nullcontext()):
        model.learn(total_timesteps=total_timesteps, callback=callbacks)

    if run_log_dir is not None:
        os.makedirs(run_log_dir, exist_ok=True)

    model.save(model_path)
    print(f"\nМодель сохранена: {model_path}")

    print("\n── Итоги (без RLLogger) ─────────────────────────────")

    print(f"Начальная ценность леса: {initial_total_value:.1f}")

    print("Обучение завершено.")
    print("─────────────────────────────────────────────────────")

    return model


def run_tuning(
    model_path_load: str,
    config_path: str = "services/patrol_planning/learning/configs/research/4x4_no_obstacle.json",
    exclude_layers: list[str] | None = None,
    model_path: str = "services/patrol_planning/learning/models/ppo_forest_agent_1",
    log_dir: str = "services/patrol_planning/learning/logs",
    total_timesteps: int = 20_000,
    seed: int = 42,
    run_id: str | None = None,
    show_render: bool = False,
    ent_coef = 0.02,
    lr = 1e-4,
):
    import os
    import json
    import contextlib
    import random
    import numpy as np

    from stable_baselines3 import PPO
    from stable_baselines3.common.env_util import make_vec_env

    from services.patrol_planning.assets.envs.forest import GridForest
    from services.patrol_planning.assets.envs.models import GridForestConfig
    from services.patrol_planning.src.renderer_extended import GridWorldRendererExt
    from services.patrol_planning.service.models import GridWorldTrainState

    if exclude_layers is None:
        exclude_layers = ["terrain", "rows", "cols"]
    if run_id is None:
        run_id = f"seed_{seed}"

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
    config.metrics_config.enabled = False

    run_log_dir = os.path.join(log_dir, run_id)

    def make_env():
        env = GridForest.load(config)
        env.train_state = GridWorldTrainState()
        return env

    tmp_env = make_env()
    tmp_env.reset(seed=seed)
    initial_total_value = float(tmp_env.world_layers["value"].sum())

    vec_env = make_vec_env(make_env, n_envs=4)

    model = PPO.load(model_path_load, env=vec_env, device="cuda")

    model.ent_coef = ent_coef
    model.learning_rate = lr

    model.gamma = 0.995
    model.gae_lambda = 0.95

    model._setup_model()

    print("ДООБУЧЕНИЕ МОДЕЛИ:", model_path_load)
    print("ЗАПУЩЕНО НА:", model.device)

    renderer = GridWorldRendererExt(make_env, True, "intruders", True, "intruders")

    print(f"\n=== Дообучение: {total_timesteps} шагов | run={run_id} ===\n")

    with (renderer.live if show_render else contextlib.nullcontext()):
        model.learn(total_timesteps=total_timesteps, reset_num_timesteps=False)

    os.makedirs(run_log_dir, exist_ok=True)

    model.save(model_path)
    print(f"\nМодель сохранена: {model_path}")

    print("\n── Итоги дообучения ─────────────────────────────────")
    print(f"Начальная ценность леса: {initial_total_value:.1f}")
    print("Дообучение завершено.")
    print("─────────────────────────────────────────────────────")

    return model


if __name__ == "__main__":
    run_training_m(
    config_path="C:/Users/George Doroshin/repos/forest-rl-platform/services/patrol_planning/learning/configs/research/4x4_no_obstacle_random_map.json",
    exclude_layers=["terrain", "rows", "cols", "passability", "value", "idleness"],
    model_path="C:/Users/George Doroshin/repos/forest-rl-platform/services/patrol_planning/research/baseline_random",
    log_dir="C:/Users/George Doroshin/repos/forest-rl-platform/services/patrol_planning/research/4x4_no_obstacle/results",
    total_timesteps=20_000,
    seed=42,
    run_id="baseline_4x4",
    show_render=False,
    
)
