from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

class MetricSeries(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., ge=1)
    run_id: int = Field(..., ge=1)
    name: str = Field(..., max_length=150) # reward_mean, success_rate, damage_total
    unit: Optional[str] = Field(None, max_length=50)
    aggregation: Optional[str] = Field(None, max_length=50) # mean, sum, max, min
    source: Optional[str] = Field(None, max_length=100) # trainer, simulator, evaluator
    description: Optional[str] = None
    created_at: datetime
