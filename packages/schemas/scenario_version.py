from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any

class ScenarioVersion(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., ge=1)
    scenario_id: int = Field(..., ge=1)
    version_no: int = Field(..., ge=1)
    seed: Optional[int] = Field(None, ge=0)
    terrain_config_json: Optional[Dict[str, Any]] = None
    obstacle_config_json: Optional[Dict[str, Any]] = None
    event_config_json: Optional[Dict[str, Any]] = None
    sensor_config_json: Optional[Dict[str, Any]] = None
    reward_config_json: Optional[Dict[str, Any]] = None
    world_file_uri: Optional[str] = None
    preview_image_uri: Optional[str] = None
    is_active: bool = True
    created_at: datetime
