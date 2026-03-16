from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional


class UserBase(BaseModel):
    full_name: str = Field(..., max_length=255)
    email: EmailStr = Field(..., max_length=255)
    role: Optional[str] = Field(None, max_length=100)


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., ge=1)
    created_at: datetime
