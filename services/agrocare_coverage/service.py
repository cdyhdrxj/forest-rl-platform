from __future__ import annotations

import threading
import time

from stable_baselines3.common.env_util import make_vec_env

from apps.api.sb3.sb3_trainer import SB3Trainer
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

    def start(self, params: dict) -> None:
        algorithm = str(params.get("algorithm", "greedy_nearest")).lower()
        self.training_state["mode"] = params.get("mode", "coverage")
        if algorithm in BASELINE_ALGORITHMS:
            self._start_baseline_run(params, algorithm)
            return
        super().start(params)

    def stop(self) -> None:
        self._baseline_stop_event.set()
        if self._baseline_thread is not None and self._baseline_thread.is_alive():
            self._baseline_thread.join(timeout=1.0)
        self._baseline_thread = None
        super().stop()

    def reset(self) -> None:
        self.stop()
        self.training_state = CoverageTrainState()
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
        }

    def _build_env(self, params: dict):
        if self.loaded_config is None or self.loaded_layout is None:
            raise RuntimeError("AgrocareCoverageService.start() requires a scenario loaded by the dispatcher")

        def factory():
            env = CoveragePlanningEnv(self.loaded_config, generated_layout=self.loaded_layout)
            env.train_state = self.training_state
            return env

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
        if scenario.get_layer_data("obstacle_mask") is None:
            messages.append("Coverage runtime requires an obstacle_mask layer")
        if runtime_config is None:
            messages.append("Coverage runtime requires serialized runtime config")
        return messages

    def _start_baseline_run(self, params: dict, algorithm: str) -> None:
        if self.training_state["running"]:
            return
        if self.loaded_config is None or self.loaded_layout is None:
            raise RuntimeError("AgrocareCoverageService.start() requires a scenario loaded by the dispatcher")

        self._reset_counters()
        self.last_error = None
        self._baseline_stop_event.clear()
        self.training_state.running = True

        env = CoveragePlanningEnv(self.loaded_config, generated_layout=self.loaded_layout)
        env.train_state = self.training_state
        env.reset(seed=self.loaded_config.seed)
        self.env = env

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

