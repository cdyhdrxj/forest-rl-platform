from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any


class ModelBase(BaseModel):
    run_id: int = Field(..., ge=1)
    name: str = Field(..., max_length=255)
    framework: str = Field(..., max_length=100)
    storage_uri: str
    checkpoint_epoch: Optional[int] = Field(None, ge=0)
    is_best: bool = False
    metrics_json: Optional[Dict[str, Any]] = None


class ModelRead(ModelBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., ge=1)
    created_at: datetime
