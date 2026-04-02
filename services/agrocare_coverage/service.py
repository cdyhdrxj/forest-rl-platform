from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

import numpy as np
from stable_baselines3.common.env_util import make_vec_env

from apps.api.sb3.model_params import ALGO_DEFAULTS
from apps.api.sb3.sb3_trainer import ALGORITHMS, SB3Trainer
from services.agrocare_coverage.baselines import choose_greedy_nearest_action, choose_greedy_two_step_action
from services.agrocare_coverage.callback import CoverageCallback
from services.agrocare_coverage.environment import CoveragePlanningEnv
from services.agrocare_coverage.models import CoverageEnvConfig, CoverageTrainState
from services.scenario_generator import extract_coverage_runtime_layout
from services.scenario_generator.models import GeneratedScenario


BASELINE_ALGORITHMS = {
    "greedy_nearest": choose_greedy_nearest_action,
    "greedy_two_step": choose_greedy_two_step_action,
}

EVALUATION_ROLES = {"eval", "validation", "test", "test_eval"}


class AgrocareCoverageService(SB3Trainer):
    def __init__(self):
        self.env = None
        self.model = None
        self.last_error: str | None = None
        self.training_state = CoverageTrainState()
        self.loaded_scenario: GeneratedScenario | None = None
        self.loaded_config: CoverageEnvConfig | None = None
        self.loaded_layout: dict | None = None
        self._baseline_thread: threading.Thread | None = None
        self._baseline_stop_event = threading.Event()
        self._rl_thread: threading.Thread | None = None
        self._rl_stop_event = threading.Event()
        self._last_checkpoint_path: str | None = None

    def start(self, params: dict) -> None:
        algorithm = str(params.get("algorithm", "greedy_nearest")).lower()
        execution_role = str(params.get("execution_role") or params.get("role") or "train").lower()
        self.training_state["mode"] = params.get("mode", "coverage")
        if algorithm in BASELINE_ALGORITHMS:
            self._start_baseline_run(params, algorithm)
            return
        if execution_role in EVALUATION_ROLES:
            self._start_rl_evaluation(params, algorithm)
            return
        self._start_rl_training(params, algorithm)

    def stop(self) -> None:
        self.training_state.running = False
        self._baseline_stop_event.set()
        self._rl_stop_event.set()
        if self._baseline_thread is not None and self._baseline_thread.is_alive():
            self._baseline_thread.join(timeout=1.0)
        if self._rl_thread is not None and self._rl_thread.is_alive():
            self._rl_thread.join(timeout=1.0)
        self._baseline_thread = None
        self._rl_thread = None

    def reset(self) -> None:
        self.stop()
        self.training_state = CoverageTrainState()
        self._last_checkpoint_path = None
        if self.loaded_scenario is not None:
            self._apply_preview_state(self.loaded_scenario)

    def load_scenario(self, scenario: GeneratedScenario, runtime_config: dict | None = None) -> None:
        self.stop()
        self.env = None
        self.model = None
        self.training_state = CoverageTrainState()
        self.training_state["mode"] = scenario.task_kind.value
        self.loaded_scenario = scenario
        self.loaded_config = CoverageEnvConfig.model_validate(runtime_config or {})
        self.loaded_layout = extract_coverage_runtime_layout(scenario)
        self._apply_preview_state(scenario)

    def get_state(self) -> dict:
        s = self.training_state
        return {
            "running": s.running,
            "mode": s.mode,
            "episode": s.episode,
            "step": s.step,
            "total_reward": s.total_reward,
            "last_episode_reward": s.last_episode_reward,
            "new_episode": s.new_episode,
            "agent_pos": s.agent_pos,
            "goal_pos": s.goal_pos,
            "landmark_pos": s.landmark_pos,
            "trajectory": s.trajectory,
            "is_collision": s.is_collision,
            "goal_count": s.goal_count,
            "collision_count": s.collision_count,
            "terrain_map": s.terrain_map,
            "coverage_target_map": s.coverage_target_map,
            "covered_map": s.covered_map,
            "coverage_ratio": s.coverage_ratio,
            "missed_area_ratio": s.missed_area_ratio,
            "return_to_start_success": s.return_to_start_success,
            "return_error": s.return_error,
            "path_length": s.path_length,
            "task_time_sec": s.task_time_sec,
            "transition_count": s.transition_count,
            "repeat_coverage_ratio": s.repeat_coverage_ratio,
            "angular_work_rad": s.angular_work_rad,
            "compute_time_sec": s.compute_time_sec,
            "success": s.success,
            "remaining_rows": s.remaining_rows,
            "current_row_index": s.current_row_index,
            "row_completion": s.row_completion,
            "checkpoint_path": self._last_checkpoint_path,
        }

    def _build_env(self, params: dict):
        def factory():
            return self._build_single_env()

        return make_vec_env(factory, n_envs=1)

    def _make_callback(self) -> CoverageCallback:
        return CoverageCallback(self.training_state)

    def _reset_counters(self) -> None:
        self.training_state.reset_counters()
        self.training_state.running = False

    def validate_scenario(self, scenario: GeneratedScenario, runtime_config: dict | None = None) -> list[str]:
        messages: list[str] = []
        if scenario.environment_kind.value != "continuous_2d":
            messages.append("Coverage runtime can load only continuous_2d scenarios")
        if scenario.runtime_context.get("coverage") is None:
            messages.append("Coverage runtime requires coverage runtime context")
        if scenario.get_layer_data("coverage_mask") is None:
            messages.append("Coverage runtime requires a coverage_mask layer")
        if scenario.get_layer_data("field_mask") is None:
            messages.append("Coverage runtime requires a field_mask layer")
        if scenario.get_layer_data("obstacle_mask") is None:
            messages.append("Coverage runtime requires an obstacle_mask layer")
        if runtime_config is None:
            messages.append("Coverage runtime requires serialized runtime config")
        return messages

    def _start_baseline_run(self, params: dict, algorithm: str) -> None:
        if self.training_state["running"]:
            return

        self._ensure_loaded()
        self._reset_counters()
        self.last_error = None
        self._baseline_stop_event.clear()
        self.training_state.running = True

        env = self._build_single_env()
        step_sleep = float(params.get("tick_sleep") or 0.01)
        policy = BASELINE_ALGORITHMS[algorithm]

        def loop() -> None:
            try:
                while not self._baseline_stop_event.is_set():
                    action = policy(env)
                    _, _, terminated, truncated, _ = env.step(action)
                    if terminated or truncated:
                        break
                    time.sleep(step_sleep)
            except Exception as exc:
                self.last_error = str(exc)
            finally:
                self.training_state.running = False

        self._baseline_thread = threading.Thread(target=loop, daemon=True)
        self._baseline_thread.start()

    def _start_rl_training(self, params: dict, algorithm: str) -> None:
        if self.training_state["running"]:
            return

        self._ensure_loaded()
        self._reset_counters()
        self.last_error = None
        self._rl_stop_event.clear()
        self.training_state.running = True
        self.training_state["mode"] = "coverage_train"

        env = self._build_env(params)
        self.env = env
        self.model = self._build_or_load_model(algorithm, env, params)
        total_timesteps = max(1, int(params.get("total_timesteps") or 10_000))
        checkpoint_out_path = self._resolve_checkpoint_path(
            params.get("save_checkpoint_path") or params.get("checkpoint_out_path")
        )

        def loop() -> None:
            try:
                self.model.learn(
                    total_timesteps=total_timesteps,
                    callback=self._make_callback(),
                    reset_num_timesteps=bool(params.get("reset_num_timesteps", not bool(params.get("load_checkpoint_path")))),
                )
                if checkpoint_out_path is not None:
                    self._save_model_checkpoint(checkpoint_out_path)
            except Exception as exc:
                self.last_error = str(exc)
            finally:
                self.training_state.running = False

        self._rl_thread = threading.Thread(target=loop, daemon=True)
        self._rl_thread.start()

    def _start_rl_evaluation(self, params: dict, algorithm: str) -> None:
        if self.training_state["running"]:
            return

        self._ensure_loaded()
        self._reset_counters()
        self.last_error = None
        self._rl_stop_event.clear()
        self.training_state.running = True
        self.training_state["mode"] = "coverage_eval"

        env = self._build_single_env()
        self.model = self._build_or_load_model(algorithm, env, params)
        deterministic = bool(params.get("deterministic", True))
        eval_episodes = max(1, int(params.get("eval_episodes") or 1))
        step_sleep = float(params.get("tick_sleep") or 0.0)
        base_seed = int(params.get("eval_seed") or params.get("seed") or self.loaded_config.seed or 0)

        def loop() -> None:
            completed = 0
            try:
                observation, _ = env.reset(seed=base_seed)
                while not self._rl_stop_event.is_set():
                    action = self._predict_action(self.model, observation, deterministic=deterministic)
                    observation, _, terminated, truncated, _ = env.step(action)
                    if terminated or truncated:
                        completed += 1
                        if completed >= eval_episodes:
                            break
                        observation, _ = env.reset(seed=base_seed + completed)
                    if step_sleep > 0:
                        time.sleep(step_sleep)
            except Exception as exc:
                self.last_error = str(exc)
            finally:
                self.training_state.running = False

        self._rl_thread = threading.Thread(target=loop, daemon=True)
        self._rl_thread.start()

    def _ensure_loaded(self) -> None:
        if self.loaded_config is None or self.loaded_layout is None:
            raise RuntimeError("AgrocareCoverageService.start() requires a scenario loaded by the dispatcher")

    def _build_single_env(self) -> CoveragePlanningEnv:
        self._ensure_loaded()
        env = CoveragePlanningEnv(self.loaded_config, generated_layout=self.loaded_layout)
        env.train_state = self.training_state
        env.reset(seed=self.loaded_config.seed)
        self.env = env
        return env

    def _build_or_load_model(self, algorithm: str, env, params: dict[str, Any]):
        algo_key = str(algorithm or "ppo").lower()
        algo_class = ALGORITHMS.get(algo_key, ALGORITHMS["ppo"])
        checkpoint_path = params.get("load_checkpoint_path")
        if checkpoint_path:
            checkpoint = Path(str(checkpoint_path)).resolve()
            if not checkpoint.exists():
                raise FileNotFoundError(f"Coverage checkpoint not found: {checkpoint}")
            if hasattr(algo_class, "load"):
                try:
                    self._last_checkpoint_path = str(checkpoint)
                    return algo_class.load(str(checkpoint), env=env)
                except TypeError:
                    self._last_checkpoint_path = str(checkpoint)
                    return algo_class.load(str(checkpoint))
        self._last_checkpoint_path = None
        model_kwargs = self._resolve_model_kwargs(algo_key, params)
        verbose = int(params.get("verbose", 1))
        return algo_class("MlpPolicy", env, verbose=verbose, **model_kwargs)

    def _resolve_model_kwargs(self, algorithm: str, params: dict[str, Any]) -> dict[str, Any]:
        defaults = ALGO_DEFAULTS.get(algorithm, {})
        overrides = {key: params[key] for key in defaults if key in params}
        model_kwargs = {**defaults, **overrides}
        for key in ("policy_kwargs", "tensorboard_log", "device"):
            if key in params:
                model_kwargs[key] = params[key]
        return model_kwargs

    def _save_model_checkpoint(self, checkpoint_path: Path) -> None:
        if self.model is None:
            return
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        if hasattr(self.model, "save"):
            self.model.save(str(checkpoint_path))
        self._last_checkpoint_path = str(checkpoint_path)

    @staticmethod
    def _resolve_checkpoint_path(value: Any) -> Path | None:
        if value in {None, ""}:
            return None
        return Path(str(value)).resolve()

    @staticmethod
    def _predict_action(model: Any, observation: Any, *, deterministic: bool) -> Any:
        if hasattr(model, "predict"):
            prediction = model.predict(observation, deterministic=deterministic)
            if isinstance(prediction, tuple):
                return prediction[0]
            return prediction
        return np.zeros((2,), dtype=np.float32)

    def _apply_preview_state(self, scenario: GeneratedScenario) -> None:
        preview = scenario.preview_payload
        layout = dict(scenario.runtime_context.get("coverage") or {})

        self.training_state.agent_pos = list(preview.get("agent_pos") or [])
        self.training_state.goal_pos = list(preview.get("goal_pos") or [])
        self.training_state.landmark_pos = list(preview.get("landmark_pos") or [])
        self.training_state.trajectory = []
        self.training_state.is_collision = False
        self.training_state.new_episode = False
        self.training_state.running = False
        self.training_state.coverage_ratio = 0.0
        self.training_state.missed_area_ratio = 1.0
        self.training_state.repeat_coverage_ratio = 0.0
        self.training_state.return_to_start_success = False
        self.training_state.return_error = 0.0
        self.training_state.path_length = 0.0
        self.training_state.task_time_sec = 0.0
        self.training_state.transition_count = 0
        self.training_state.angular_work_rad = 0.0
        self.training_state.compute_time_sec = 0.0
        self.training_state.success = False
        self.training_state.remaining_rows = len(preview.get("goal_pos") or [])
        self.training_state.current_row_index = None
        self.training_state.goal_count = 0
        self.training_state.collision_count = 0
        self.training_state.covered_target_count = 0
        self.training_state.total_target_count = int(sum(layout.get("row_target_counts") or []))
        self.training_state.repeated_target_steps = 0
        self.training_state.terrain_map = preview.get("terrain_map")
        self.training_state.coverage_target_map = preview.get("coverage_target_map")
        self.training_state.covered_map = (
            [[0.0 for _ in row] for row in list(preview.get("coverage_target_map") or [])]
            if preview.get("coverage_target_map") is not None
            else None
        )
        self.training_state.row_completion = list(layout.get("row_completion_template") or [])
