from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from services.patrol_planning.src.dict_like import DictLikeModel


class CoverageEnvConfig(BaseModel):
    grid_size: int = Field(default=32, ge=12, le=96)
    row_count: int = Field(default=8, ge=3, le=24)
    max_rows: int = Field(default=24, ge=3, le=32)
    curvature_level: Literal["low", "medium", "high"] = "low"
    field_profile: Literal["simple", "tapered", "concave"] = "simple"
    gap_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    gap_segment_length: int = Field(default=2, ge=1, le=8)
    obstacle_count: int = Field(default=0, ge=0, le=16)
    obstacle_radius_min: int = Field(default=1, ge=1, le=8)
    obstacle_radius_max: int = Field(default=2, ge=1, le=10)
    max_steps: int = Field(default=24, ge=1, le=256)
    seed: Optional[int] = None

    alpha_new_coverage: float = Field(default=2.0, ge=0.0)
    beta_repeat_coverage: float = Field(default=0.35, ge=0.0)
    beta_transition: float = Field(default=0.08, ge=0.0)
    beta_path: float = Field(default=0.02, ge=0.0)
    beta_turn: float = Field(default=0.05, ge=0.0)
    beta_invalid_action: float = Field(default=0.75, ge=0.0)
    success_bonus: float = Field(default=6.0, ge=0.0)
    failure_penalty: float = Field(default=3.0, ge=0.0)

    @model_validator(mode="after")
    def validate_ranges(self) -> "CoverageEnvConfig":
        if self.row_count > self.max_rows:
            raise ValueError("row_count must not exceed max_rows")
        if self.obstacle_radius_max < self.obstacle_radius_min:
            raise ValueError("obstacle_radius_max must be greater than or equal to obstacle_radius_min")
        if self.max_steps < self.row_count:
            self.max_steps = self.row_count
        return self


class CoverageTrainState(DictLikeModel):
    model_config = {"arbitrary_types_allowed": True}

    running: bool = False
    mode: str = "coverage"
    episode: int = 0
    step: int = 0
    total_reward: float = 0.0
    last_episode_reward: float = 0.0
    new_episode: bool = False
    goal_count: int = 0
    collision_count: int = 0
    transition_count: int = 0
    total_target_count: int = 0
    covered_target_count: int = 0
    repeated_target_steps: int = 0
    coverage_ratio: float = 0.0
    missed_area_ratio: float = 1.0
    repeat_coverage_ratio: float = 0.0
    angular_work_rad: float = 0.0
    compute_time_sec: float = 0.0
    task_time_sec: float = 0.0
    path_length: float = 0.0
    return_error: float = 0.0
    return_to_start_success: bool = False
    success: bool = False
    remaining_rows: int = 0
    current_row_index: Optional[int] = None
    obs_raw: Optional[object] = None
    is_collision: bool = False
    agent_pos: list[list[float]] = Field(default_factory=lambda: [[0.0, 0.0]])
    goal_pos: list[list[float]] = Field(default_factory=list)
    landmark_pos: list[list[float]] = Field(default_factory=list)
    trajectory: list[list[float]] = Field(default_factory=list)
    terrain_map: Optional[list[list[float]]] = None
    coverage_target_map: Optional[list[list[float]]] = None
    covered_map: Optional[list[list[float]]] = None
    row_completion: list[float] = Field(default_factory=list)

    def reset_counters(self) -> None:
        self.running = False
        self.mode = "coverage"
        self.episode = 0
        self.step = 0
        self.total_reward = 0.0
        self.last_episode_reward = 0.0
        self.new_episode = False
        self.goal_count = 0
        self.collision_count = 0
        self.transition_count = 0
        self.total_target_count = 0
        self.covered_target_count = 0
        self.repeated_target_steps = 0
        self.coverage_ratio = 0.0
        self.missed_area_ratio = 1.0
        self.repeat_coverage_ratio = 0.0
        self.angular_work_rad = 0.0
        self.compute_time_sec = 0.0
        self.task_time_sec = 0.0
        self.path_length = 0.0
        self.return_error = 0.0
        self.return_to_start_success = False
        self.success = False
        self.remaining_rows = 0
        self.current_row_index = None
        self.obs_raw = None
        self.is_collision = False
        self.agent_pos = [[0.0, 0.0]]
        self.goal_pos = []
        self.landmark_pos = []
        self.trajectory = []
        self.terrain_map = None
        self.coverage_target_map = None
        self.covered_map = None
        self.row_completion = []
