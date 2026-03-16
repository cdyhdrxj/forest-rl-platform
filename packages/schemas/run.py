from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any

from .enums import ProjectMode, RunStatus


class RunBase(BaseModel):
    project_id: int = Field(..., ge=1)
    scenario_version_id: int = Field(..., ge=1)
    algorithm_id: int = Field(..., ge=1)
    mode: ProjectMode
    status: RunStatus
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    seed: Optional[int] = Field(None, ge=0)
    config_json: Dict[str, Any]
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class RunRead(RunBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., ge=1)
    created_by_user_id: int = Field(..., ge=1)
    created_at: datetime
