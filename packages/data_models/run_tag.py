from pydantic import BaseModel, Field, ConfigDict

class RunTag(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., ge=1)
    run_id: int = Field(..., ge=1)
    tag: str = Field(..., max_length=100)
