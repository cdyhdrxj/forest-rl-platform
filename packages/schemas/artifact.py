from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
from .enums import ArtifactType

class Artifact(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., ge=1)
    run_id: int = Field(..., ge=1)
    model_id: Optional[int] = Field(None, ge=1)
    artifact_type: ArtifactType
    name: str = Field(..., max_length=255)
    storage_uri: str
    mime_type: Optional[str] = Field(None, max_length=100)
    checksum: Optional[str] = Field(None, max_length=128)
    size_bytes: Optional[int] = Field(None, ge=0)
    created_at: datetime
