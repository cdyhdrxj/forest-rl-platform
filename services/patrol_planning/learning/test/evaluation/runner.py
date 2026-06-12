"""Движок оценки агентов: N эпизодов на одном конфиге, полный набор метрик."""
from __future__ import annotations

import contextlib
import json
import os
from datetime import datetime

from services.patrol_planning.learning.test.evaluation.agent import EvalAgent, make_agent
from services.patrol_planning.learning.test.evaluation.collector import EvalCollector
from services.patrol_planning.learning.test.evaluation.config import EvalRunConfig


def _build_env(config_path: str, exclude_layers: list[str]):
    """Загрузить среду из JSON-конфига."""
    from services.patrol_planning.assets.envs.forest import GridForest
    from services.patrol_planning.assets.envs.models import GridForestConfig
    from services.patrol_planning.service.models import GridWorldTrainState

    with open(config_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    config = GridForestConfig.model_validate(raw)
    config.obs_config.exclude_layers = exclude_layers
    env = GridForest.load(config)
    env.train_state = GridWorldTrainState()
    return env, config


def _run_episodes(
    env,
    agent: EvalAgent,
    collector: EvalCollector,
    n_episodes: int,
    seed: int,
    show_render: bool = False,
    render_delay: float = 0.1,
) -> None:
    """Запустить n_episodes эпизодов и записать метрики в collector."""
    from services.patrol_planning.src.renderer_extended import GridWorldRendererExt

    renderer = GridWorldRendererExt(env, True, "intruders", True, "intruders")
    if show_render:
        env.renderer = renderer
        env.render_time_sleep = render_delay

    env.rl_logger = collector

    with (renderer.live if show_render else contextlib.nullcontext()):
        env.reset(seed=seed)
        for ep in range(n_episodes):
            agent.reset()
            _run_single_episode(env, agent)
            env.reset(seed=seed + ep + 1)

            done = collector.episode_count
            if done % 10 == 0 or done == n_episodes:
                df = collector.episodes_to_df()
                mean_r = df["total_reward"].mean() if not df.empty else 0.0
                print(f"  Эпизод {done:>4}/{n_episodes}  |  средняя награда: {mean_r:.2f}")

    env.renderer = None
    env.rl_logger = None


def _run_single_episode(env, agent: EvalAgent) -> None:
    """Прогнать один эпизод до завершения."""
    obs = env._last_obs
    terminated = False
    truncated = False
    while not (terminated or truncated):
        action = agent.predict(obs)
        obs, _, terminated, truncated, _ = env.step(action)


def _print_summary(collector: EvalCollector) -> None:
    df = collector.episodes_to_df()
    if df.empty:
        return
    print(f"\n── {collector.agent_name} — итоги ─────────────────────────────────────────")
    print(f"  Эпизодов            : {collector.episode_count}")
    print(f"  Средняя R           : {df['total_reward'].mean():.3f}  ±{df['total_reward'].std():.3f}")
    if "metric_Z" in df:
        print(f"  Средний Z(π)        : {df['metric_Z'].mean():.4f}  ±{df['metric_Z'].std():.4f}")
    for col, label in [
        ("metric_M_damage", "    M_damage"),
        ("metric_M_move", "    M_move  "),
        ("metric_M_idleness", "    M_idleness"),
    ]:
        if col in df:
            print(f"  {label}         : {df[col].mean():.4f}")
    if "catch_rate" in df:
        print(f"  Catch rate          : {df['catch_rate'].mean():.2%}  ±{df['catch_rate'].std():.2%}")
    if "catch_latency_mean" in df:
        valid = df["catch_latency_mean"].dropna()
        if not valid.empty:
            print(f"  Avg catch latency   : {valid.mean():.1f} шагов")
    if "invalid_out" in df:
        print(f"  Invalid out/ep      : {df['invalid_out'].mean():.2f}")
    if "invalid_block" in df:
        print(f"  Invalid block/ep    : {df['invalid_block'].mean():.2f}")
    print(f"  Uniformity (CV)     : {collector.visit_uniformity():.3f}  (↓ = равномернее)")
    print("──────────────────────────────────────────────────────────────────\n")


class EvaluationRunner:
    """Запускает оценку одного агента: N эпизодов, один конфиг, полные метрики.

    Использование:
        cfg = EvalRunConfig(agent_name="drqn_v3", agent_type="drqn",
                            model_path="path/to/model.pt", config_path="path/to/config.json")
        runner = EvaluationRunner(cfg)
        collector = runner.run()
    """

    def __init__(self, cfg: EvalRunConfig) -> None:
        self.cfg = cfg
        if cfg.run_id is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._run_id = f"{cfg.agent_name}_{ts}"
        else:
            self._run_id = cfg.run_id

    def _make_agent(self, env=None) -> EvalAgent:
        extra: dict = {}
        if self.cfg.agent_type in ("drqn", "alt_drqn") and env is not None:
            extra["observation_space"] = env.observation_space
            extra["n_actions"] = env.action_space.n
            extra["device"] = self.cfg.drqn_device
        if self.cfg.agent_type in ("greedy_intruder", "greedy_damage", "lawnmower"):
            from services.patrol_planning.learning.test.evaluation.agent import build_channel_map
            extra["channel_map"] = build_channel_map(self.cfg.exclude_layers)
        if self.cfg.agent_type == "lawnmower" and env is not None:
            extra["grid_size"] = env.grid_world_size
        return make_agent(
            agent_type=self.cfg.agent_type,
            model_path=self.cfg.model_path,
            seed=self.cfg.seed,
            **extra,
        )

    def run_eval(self) -> EvalCollector:
        """N эпизодов на конфиге config_path."""
        cfg = self.cfg
        print(f"\n=== Оценка | агент: {cfg.agent_name} | эпизодов: {cfg.n_episodes} ===")

        env, config = _build_env(cfg.config_path, cfg.exclude_layers)
        agent = self._make_agent(env)
        collector = EvalCollector(
            grid_size=config.grid_size,
            run_id=self._run_id,
            agent_name=cfg.agent_name,
            test_mode="eval",
        )

        _run_episodes(
            env=env,
            agent=agent,
            collector=collector,
            n_episodes=cfg.n_episodes,
            seed=cfg.seed,
            show_render=cfg.show_render,
            render_delay=cfg.render_delay,
        )
        _print_summary(collector)
        return collector

    def run(self) -> EvalCollector:
        """Запустить оценку, сохранить результаты и (опционально) залогировать в TB."""
        from services.patrol_planning.learning.test.evaluation import plots
        from services.patrol_planning.learning.test.evaluation.plots import PlotData

        cfg = self.cfg
        collector = self.run_eval()

        save_dir = os.path.join(cfg.output_dir, self._run_id)
        collector.save_all(save_dir)

        if cfg.tb_mode:
            from services.patrol_planning.learning.test.evaluation.tb_writer import EvalTBWriter
            tb_dir = cfg.tb_log_dir or os.path.join(cfg.output_dir, "tensorboard")
            tb = EvalTBWriter(log_dir=os.path.join(tb_dir, self._run_id))
            tb.log_test(PlotData.from_collector(collector), prefix="eval",
                        test_label=cfg.agent_name)
            tb.close()
            print(f"  [TB] tensorboard --logdir \"{tb_dir}\"")
        else:
            plots.plot_all(PlotData.from_collector(collector), save_dir)

        print(f"  Результаты сохранены: {save_dir}")
        return collector
