from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from services.patrol_planning.src.dict_like import DictLikeModel


class PlantingEnvConfig(BaseModel):
    grid_size: int = Field(default=10, ge=4, le=32)
    observation_mode: Literal["global"] = "global"
    obstacle_density: float = Field(default=0.12, ge=0.0, le=0.45)
    plantable_density: float = Field(default=0.7, ge=0.1, le=1.0)
    initial_seedlings: int = Field(default=30, ge=1)
    max_steps: int = Field(default=250, ge=20)
    min_plant_distance: int = Field(default=1, ge=0, le=5)
    uniformity_radius: int = Field(default=1, ge=0, le=5)
    target_density: float = Field(default=0.35, ge=0.0, le=1.0)
    quality_noise: float = Field(default=0.25, ge=0.0, le=1.0)
    success_probability_noise: float = Field(default=0.2, ge=0.0, le=1.0)
    random_start: bool = Field(default=True)
    seed: Optional[int] = None

    alpha_plant: float = Field(default=4.0, gt=0.0)
    alpha_quality: float = Field(default=2.0, ge=0.0)
    beta_move: float = Field(default=0.08, ge=0.0)
    beta_turn: float = Field(default=0.04, ge=0.0)
    beta_fail_move: float = Field(default=0.25, ge=0.0)
    beta_stay: float = Field(default=0.12, ge=0.0)
    beta_invalid_plant: float = Field(default=0.6, ge=0.0)
    lambda_uniformity: float = Field(default=3.0, ge=0.0)
    lambda_underplanting: float = Field(default=1.5, ge=0.0)
    target_plant_count: Optional[int] = Field(default=None, ge=0)

    @model_validator(mode="after")
    def set_default_target_plant_count(self) -> "PlantingEnvConfig":
        if self.target_plant_count is None:
            area = self.grid_size * self.grid_size
            self.target_plant_count = max(1, int(area * self.target_density * self.plantable_density))
        return self


class PlantingTrainState(DictLikeModel):
    model_config = {"arbitrary_types_allowed": True}

    running: bool = False
    mode: str = "reforestation"
    episode: int = 0
    step: int = 0
    total_reward: float = 0.0
    last_episode_reward: float = 0.0
    new_episode: bool = False
    successful_plant_count: int = 0
    invalid_plant_count: int = 0
    collision_count: int = 0
    coverage_ratio: float = 0.0
    remaining_seedlings: int = 0
    agent_pos: List[List[float]] = Field(default_factory=lambda: [[0.0, 0.0]])
    goal_pos: List[List[float]] = Field(default_factory=list)
    landmark_pos: List[List[float]] = Field(default_factory=list)
    planted_pos: List[List[float]] = Field(default_factory=list)
    trajectory: List[List[float]] = Field(default_factory=list)
    terrain_map: Optional[List[List[float]]] = None
    plantable_map: Optional[List[List[float]]] = None
    planted_map: Optional[List[List[float]]] = None
    obs_raw: Optional[object] = None
    is_collision: bool = False

    def reset_counters(self) -> None:
        self.episode = 0
        self.step = 0
        self.total_reward = 0.0
        self.last_episode_reward = 0.0
        self.new_episode = False
        self.successful_plant_count = 0
        self.invalid_plant_count = 0
        self.collision_count = 0
        self.coverage_ratio = 0.0
        self.remaining_seedlings = 0
        self.agent_pos = [[0.0, 0.0]]
        self.goal_pos = []
        self.landmark_pos = []
        self.planted_pos = []
        self.trajectory = []
        self.terrain_map = None
        self.plantable_map = None
        self.planted_map = None
        self.obs_raw = None
        self.is_collision = False
