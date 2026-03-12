from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

class ScenarioLayer(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., ge=1)
    scenario_version_id: int = Field(..., ge=1)
    layer_type: str = Field(..., max_length=100) # высоты, проходимость, опасность, ценность, события
    file_uri: str
    file_format: Optional[str] = Field(None, max_length=50) # tif, geojson, json, npy
    description: Optional[str] = None
    created_at: datetime
