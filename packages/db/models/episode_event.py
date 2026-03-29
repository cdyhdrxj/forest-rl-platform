from sqlalchemy import Column, BigInteger, Integer, Float, ForeignKey, TIMESTAMP, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base
from .enums import EventType


class EpisodeEvent(Base):
    __tablename__ = 'episode_events'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    episode_id = Column(BigInteger, ForeignKey('episodes.id'), nullable=False)
    step_index = Column(Integer)
    sim_time_sec = Column(Float)
    event_type = Column(SQLEnum(EventType), nullable=False)
    x = Column(Float)
    y = Column(Float)
    z = Column(Float)
    payload_json = Column(JSON)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    episode = relationship("Episode", back_populates="events")

    @property
    def intruder_id(self):
        if not isinstance(self.payload_json, dict):
            return None

        value = self.payload_json.get("intruder_id")
        if value is None:
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @intruder_id.setter
    def intruder_id(self, value):
        payload = dict(self.payload_json or {})

        if value is None:
            payload.pop("intruder_id", None)
        else:
            payload["intruder_id"] = int(value)

        self.payload_json = payload or None
