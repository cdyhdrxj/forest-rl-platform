import sys
import os
import queue
import time
from collections import deque

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..")
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

_ALT_DRQN_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_R_PPO_DIR    = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "r_ppo"))

_KEY_W, _VAL_W = 20, 8
_BORDER = "-" * (_KEY_W + _VAL_W + 7)


def _fmt_val(v) -> str:
    if isinstance(v, float):
        return f"{v:.4g}"
    return str(v)


def _print_sb3_table(stats: dict, dt: float, steps_per_sec: float) -> None:
    print(_BORDER)
    for section, items in stats.items():
        print(f"| {section + '/':<{_KEY_W}} | {'':>{_VAL_W}} |")
        for key, val in items.items():
            print(f"| {'    ' + key:<{_KEY_W}} | {_fmt_val(val):>{_VAL_W}} |")
    print(_BORDER)
    print(f"  ↳ Δt={dt:.1f}s | {steps_per_sec:.0f} шагов/с")


def run_training_alt_drqn(
    config_path: str = "services/patrol_planning/research/r_ppo/config_8x8_rppo.json",
    exclude_layers: list[str] | None = None,
    model_path: str = "services/patrol_planning/research/alt_drqn/models/alt_drqn_8x8_final",
    log_dir: str = "services/patrol_planning/research/alt_drqn/logs",
    checkpoints_dir: str = "services/patrol_planning/research/alt_drqn/checkpoints",
    total_timesteps: int = 500_000,
    seed: int = 42,
    run_id: str | None = None,
    lr: float = 5e-5,
    _gamma: float = 0.995,
    batch_size: int = 64,
    lstm_hidden_size: int = 256,
    unroll_length: int = 20,
    buffer_capacity: int = 10_000,
    learning_starts: int = 5_000,
    target_update_freq: int = 2000,
    epsilon_decay_steps: int = 40_000,
    epsilon_final: float = 0.05,
    train_freq: int = 4,
    log_interval: int = 20,
    checkpoint_freq: int = 100_000,
    n_envs: int = 2,
    use_amp: bool = True,
    normalize_rewards: bool = False,
    burn_in: int = 0,
    use_tensorboard: bool = True,
    device: str = "cuda",
    cpu_cores_num: int | None = None,
    common_seed: bool = False,
    validation_config=None,
    shared_train_state=None,
    step_delay: float = 0.0,
):
    import json
    import random
    import numpy as np
    import torch

    from services.patrol_planning.assets.envs.forest import GridForest
    from services.patrol_planning.assets.envs.models import GridForestConfig
    from services.patrol_planning.service.models import GridWorldTrainState
    from packages.rl_algorithms.patrol_planning.alt_drqn.alt_drqn_agent import AltDRQNAgent

    if exclude_layers is None:
        exclude_layers = ["terrain", "rows", "cols", "passability"]
    if run_id is None:
        run_id = f"seed_{seed}"

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    if cpu_cores_num is not None:
        torch.set_num_threads(cpu_cores_num)

    with open(config_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)

    config = GridForestConfig.model_validate(config_data)
    config.obs_config.exclude_layers = exclude_layers
    config.metrics_config.enabled = False

    from services.patrol_planning.learning.learn_tool.print_utils import print_training_header
    print_training_header(
        algo_name="AltDRQN",
        config=config,
        hparams=dict(
            lr=lr, gamma=_gamma, batch_size=batch_size,
            lstm_hidden_size=lstm_hidden_size, unroll_length=unroll_length,
            buffer_capacity=buffer_capacity, learning_starts=learning_starts,
            target_update_freq=target_update_freq,
            epsilon_decay_steps=epsilon_decay_steps, epsilon_final=epsilon_final,
            train_freq=train_freq, use_amp=use_amp,
            normalize_rewards=normalize_rewards, burn_in=burn_in,
        ),
        meta=dict(
            total_timesteps=total_timesteps, seed=seed, device=device,
            n_envs=n_envs, run_id=run_id, checkpoint_freq=checkpoint_freq,
            use_tensorboard=use_tensorboard,
        ),
    )

    run_log_dir = os.path.join(log_dir, run_id) if use_tensorboard else None
    if run_log_dir is not None:
        os.makedirs(run_log_dir, exist_ok=True)
    os.makedirs(checkpoints_dir, exist_ok=True)

    _writer = None
    if use_tensorboard:
        from torch.utils.tensorboard import SummaryWriter
        _writer = SummaryWriter(run_log_dir)

    envs = []
    for i in range(n_envs):
        env = GridForest.load(config)
        env.train_state = (
            shared_train_state if (shared_train_state is not None and i == 0)
            else GridWorldTrainState()
        )
        envs.append(env)

    obss = []
    for i, env in enumerate(envs):
        obs, _ = env.reset(seed=seed if common_seed else seed + i)
        obss.append(obs)

    initial_total_value = float(envs[0].world_layers["value"].sum())

    agent = AltDRQNAgent(
        observation_space=envs[0].observation_space,
        n_actions=envs[0].action_space.n,
        n_envs=n_envs,
        lr=lr,
        gamma=_gamma,
        epsilon_decay_steps=epsilon_decay_steps,
        epsilon_final=epsilon_final,
        buffer_capacity=buffer_capacity,
        unroll_length=unroll_length,
        batch_size=batch_size,
        target_update_freq=target_update_freq,
        learning_starts=learning_starts,
        lstm_hidden_size=lstm_hidden_size,
        use_amp=use_amp,
        normalize_rewards=normalize_rewards,
        burn_in=burn_in,
        device=device,
    )

    agent.reset_all_hiddens()

    print("ЗАПУЩЕНО НА:", agent.device)
    if cpu_cores_num is not None:
        print(f"CPU threads={torch.get_num_threads()}")

    print(f"\n=== Начало обучения alt_DRQN: {total_timesteps} шагов | run={run_id} ===\n")

    _validator = None
    if validation_config is not None:
        from services.patrol_planning.learning.validation.training_validator import (
            TrainingValidator, AltDRQNLiveAgent,
        )
        _validator = TrainingValidator(validation_config)
        _live_agent = AltDRQNLiveAgent(agent, device=validation_config.drqn_device)

    agent.start_update_thread()

    ep_rewards = [0.0] * n_envs
    ep_lengths = [0]   * n_envs

    _ep_buf_size = max(1_000, log_interval * 50)
    episode_rewards: deque = deque(maxlen=_ep_buf_size)
    episode_lengths: deque = deque(maxlen=_ep_buf_size)
    total_episodes = 0

    train_start      = time.perf_counter()
    _last_log_time   = train_start
    _last_log_step   = 0
    _last_ckpt_step  = 0

    env_ids = list(range(n_envs))

    while agent._step < total_timesteps and (shared_train_state is None or shared_train_state["running"]):
        obs_batch = np.stack(obss)
        actions = agent.select_action_batch(obs_batch, env_ids)

        for i in range(n_envs):
            next_obs, reward, terminated, truncated, _ = envs[i].step(actions[i])
            if step_delay > 0:
                time.sleep(step_delay)
            done = terminated or truncated

            agent.add_transition(i, obss[i], actions[i], reward, next_obs, done)
            ep_rewards[i] += reward
            ep_lengths[i] += 1

            if done:
                episode_rewards.append(ep_rewards[i])
                episode_lengths.append(ep_lengths[i])
                ep_rewards[i] = 0.0
                ep_lengths[i] = 0
                total_episodes += 1
                agent.reset_hidden(i)
                obss[i], _ = envs[i].reset()
            else:
                obss[i] = next_obs

        if agent.can_learn() and agent._step % train_freq == 0:
            try:
                agent._update_queue.put_nowait(True)
            except queue.Full:
                pass

        if total_episodes > 0 and total_episodes % log_interval == 0:
            _log_key = total_episodes
            if not hasattr(run_training_alt_drqn, "_last_logged") or \
               run_training_alt_drqn._last_logged != _log_key:
                run_training_alt_drqn._last_logged = _log_key

                now = time.perf_counter()
                dt = now - _last_log_time
                d_steps = agent._step - _last_log_step
                steps_per_sec = d_steps / dt if dt > 0 else 0.0
                _last_log_time = now
                _last_log_step = agent._step

                mean_rew = float(np.mean(list(episode_rewards)[-log_interval:]))
                mean_len = float(np.mean(list(episode_lengths)[-log_interval:]))

                _print_sb3_table({
                    "rollout": {
                        "ep_len_mean":      round(mean_len, 1),
                        "ep_rew_mean":      round(mean_rew, 1),
                        "exploration_rate": round(agent.epsilon, 4),
                    },
                    "time": {
                        "episodes":        total_episodes,
                        "fps":             int(steps_per_sec),
                        "time_elapsed":    int(now - train_start),
                        "total_timesteps": agent._step,
                    },
                    "train": {
                        "loss":      round(agent._last_loss, 4),
                        "n_updates": agent.n_updates,
                    },
                }, dt, steps_per_sec)

                if _writer is not None:
                    _writer.add_scalar("rollout/ep_rew_mean", mean_rew, agent._step)
                    _writer.add_scalar("rollout/ep_len_mean", mean_len, agent._step)
                    _writer.add_scalar("rollout/exploration_rate", agent.epsilon, agent._step)
                    _writer.add_scalar("train/loss", agent._last_loss, agent._step)
                    _writer.add_scalar("train/n_updates", agent.n_updates, agent._step)
                    _writer.add_scalar("time/fps", steps_per_sec, agent._step)

                if shared_train_state is not None:
                    shared_train_state["train_metrics"] = {
                        "fps": round(steps_per_sec, 1),
                        "ep_rew_mean": round(mean_rew, 4),
                        "ep_len_mean": round(mean_len, 1),
                        "global_step": agent._step,
                    }

        if _validator is not None:
            _val_df = _validator.maybe_validate(agent._step, _live_agent, writer=_writer)
            if _val_df is not None and _writer is not None and not _val_df.empty:
                for _col in ("total_reward", "metric_Z", "metric_M_idleness",
                             "metric_M_damage", "metric_M_move", "catch_rate"):
                    if _col in _val_df.columns:
                        _writer.add_scalar(f"val/{_col}", float(_val_df[_col].mean()), agent._step)

        if agent._step - _last_ckpt_step >= checkpoint_freq:
            ckpt_path = os.path.join(checkpoints_dir, f"alt_drqn_{agent._step}_steps.pt")
            torch.save({
                "net_state_dict":       agent.net.state_dict(),
                "optimizer_state_dict": agent.optimizer.state_dict(),
                "epsilon": agent.epsilon,
                "step":    agent._step,
            }, ckpt_path)
            print(f"  Чекпоинт: {ckpt_path}")
            _last_ckpt_step = agent._step

    agent.stop_update_thread()
    agent.buffer.flush_episode()
    agent.buffer.episodes.clear()
    episode_rewards.clear()
    episode_lengths.clear()
    if _writer is not None:
        _writer.close()

    model_dir = os.path.dirname(os.path.abspath(model_path))
    os.makedirs(model_dir, exist_ok=True)
    torch.save({
        "net_state_dict":       agent.net.state_dict(),
        "optimizer_state_dict": agent.optimizer.state_dict(),
        "epsilon": agent.epsilon,
        "step":    agent._step,
    }, model_path + ".pt")
    print(f"\nМодель сохранена: {model_path}.pt")

    print("\n── Итоги обучения ────────────────────────────────────")
    print(f"Начальная ценность леса: {initial_total_value:.1f}")
    print(f"Эпизодов завершено: {total_episodes}")
    print(f"Шагов: {agent._step}")
    print(f"Gradient updates: {agent.n_updates}")
    print("Обучение завершено.")
    print("──────────────────────────────────────────────────────")

    return agent


if __name__ == "__main__":
    run_training_alt_drqn(
        config_path=os.path.join(_R_PPO_DIR, "config_8x8_rppo.json"),
        model_path=os.path.join(_ALT_DRQN_DIR, "models", "alt_drqn_8x8_final"),
        log_dir=os.path.join(_ALT_DRQN_DIR, "logs"),
        checkpoints_dir=os.path.join(_ALT_DRQN_DIR, "checkpoints"),
        total_timesteps=500_000,
        seed=42,
        run_id="alt_drqn_8x8_v1",
        n_envs=2,
        use_amp=True,
    )
