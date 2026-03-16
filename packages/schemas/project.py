from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class ProjectBase(BaseModel):
    code: str = Field(..., max_length=100)
    name: str = Field(..., max_length=255)
    description: Optional[str] = None


class ProjectRead(ProjectBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., ge=1)
    owner_user_id: int = Field(..., ge=1)
    created_at: datetime
