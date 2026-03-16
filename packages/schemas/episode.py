from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class EpisodeBase(BaseModel):
    run_id: int = Field(..., ge=1)
    episode_index: int = Field(..., ge=0)
    success: Optional[bool] = None
    terminated_by: Optional[str] = Field(None, max_length=100) # goal, timeout, collision, manual
    reward_total: Optional[float] = None
    steps_count: Optional[int] = Field(None, ge=0)
    duration_sec: Optional[float] = Field(None, ge=0)
    path_length: Optional[float] = Field(None, ge=0)
    path_cost: Optional[float] = None
    collisions_count: Optional[int] = Field(None, ge=0)
    coverage_ratio: Optional[float] = Field(None, ge=0, le=1)
    avg_detection_delay: Optional[float] = Field(None, ge=0)
    total_damage: Optional[float] = None


class EpisodeRead(EpisodeBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., ge=1)
    created_at: datetime
