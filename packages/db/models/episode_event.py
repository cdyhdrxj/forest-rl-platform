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
