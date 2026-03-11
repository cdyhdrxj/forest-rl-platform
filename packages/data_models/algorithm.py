from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from .enums import AlgorithmFamily, ProjectMode

class Algorithm(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., ge=1)
    code: str = Field(..., max_length=100)
    name: str = Field(..., max_length=255)
    family: AlgorithmFamily
    mode: ProjectMode
    framework: Optional[str] = Field(None, max_length=100) # pytorch, custom, networkx
    description: Optional[str] = None
    default_config_json: Optional[Dict[str, Any]] = None
    created_at: datetime
