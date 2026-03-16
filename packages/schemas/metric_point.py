from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class MetricPointBase(BaseModel):
    metric_series_id: int = Field(..., ge=1)
    point_index: int = Field(..., ge=0)
    train_step: Optional[int] = Field(None, ge=0)
    episode_index: Optional[int] = Field(None, ge=0)
    wall_time_sec: Optional[float] = Field(None, ge=0)
    value: float


class MetricPointRead(MetricPointBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., ge=1)
    created_at: datetime
