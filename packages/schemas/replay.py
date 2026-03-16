from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class ReplayBase(BaseModel):
    run_id: int = Field(..., ge=1)
    episode_id: Optional[int] = Field(None, ge=1)
    name: str = Field(..., max_length=255)
    storage_uri: str
    format: Optional[str] = Field(None, max_length=50)


class ReplayRead(ReplayBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., ge=1)
    created_at: datetime
