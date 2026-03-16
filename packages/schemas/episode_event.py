from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any

from .enums import EventType


class EpisodeEventBase(BaseModel):
    episode_id: int = Field(..., ge=1)
    step_index: Optional[int] = Field(None, ge=0)
    sim_time_sec: Optional[float] = Field(None, ge=0)
    event_type: EventType
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    payload_json: Optional[Dict[str, Any]] = None


class EpisodeEventRead(EpisodeEventBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., ge=1)
    created_at: datetime
