from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any

class ServiceLog(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., ge=1)
    run_id: Optional[int] = Field(None, ge=1)
    service_name: str = Field(..., max_length=100) # simulator, api, trainer, robot_adapter
    level: str = Field(..., max_length=20)
    message: str
    payload_json: Optional[Dict[str, Any]] = None
    created_at: datetime
