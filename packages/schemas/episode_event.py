from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Optional, Dict, Any

from .enums import EventType


class EpisodeEventBase(BaseModel):
    episode_id: int = Field(..., ge=1)
    step_index: Optional[int] = Field(None, ge=0)
    sim_time_sec: Optional[float] = Field(None, ge=0)
    event_type: EventType
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    intruder_id: Optional[int] = Field(None, description="ID нарушителя для intruder-событий")
    payload_json: Optional[Dict[str, Any]] = None

    @model_validator(mode="before")
    @classmethod
    def sync_intruder_payload(cls, data):
        if not isinstance(data, dict):
            return data

        data = dict(data)
        payload_json = dict(data.get("payload_json") or {})

        if "intruder_id" in data:
            intruder_id = data.get("intruder_id")
            if intruder_id is None:
                payload_json.pop("intruder_id", None)
            else:
                payload_json["intruder_id"] = int(intruder_id)
            data["payload_json"] = payload_json or None
        elif "intruder_id" in payload_json:
            data["intruder_id"] = payload_json["intruder_id"]

        return data


class EpisodeEventRead(EpisodeEventBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., ge=1)
    created_at: datetime
