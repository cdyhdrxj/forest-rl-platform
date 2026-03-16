from pydantic import BaseModel, Field, ConfigDict

class RunTagBase(BaseModel):
    run_id: int = Field(..., ge=1)
    tag: str = Field(..., max_length=100)


class RunTagRead(RunTagBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., ge=1)
