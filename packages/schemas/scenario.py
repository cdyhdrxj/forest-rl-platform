from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from .enums import ProjectMode

class Scenario(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., ge=1)
    project_id: int = Field(..., ge=1)
    code: str = Field(..., max_length=100)
    name: str = Field(..., max_length=255)
    mode: ProjectMode
    description: Optional[str] = None
    created_by_user_id: int = Field(..., ge=1)
    created_at: datetime
