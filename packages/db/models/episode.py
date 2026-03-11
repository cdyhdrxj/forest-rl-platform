from sqlalchemy import Column, BigInteger, Integer, Boolean, String, Float, ForeignKey, TIMESTAMP, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class Episode(Base):
    __tablename__ = 'episodes'
    __table_args__ = (
        UniqueConstraint('run_id', 'episode_index', name='uix_run_episode'),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_id = Column(BigInteger, ForeignKey('runs.id'), nullable=False)
    episode_index = Column(Integer, nullable=False)
    success = Column(Boolean)
    terminated_by = Column(String(100))
    reward_total = Column(Float)
    steps_count = Column(Integer)
    duration_sec = Column(Float)
    path_length = Column(Float)
    path_cost = Column(Float)
    collisions_count = Column(Integer)
    coverage_ratio = Column(Float)
    avg_detection_delay = Column(Float)
    total_damage = Column(Float)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    run = relationship("Run", back_populates="episodes")
    events = relationship("EpisodeEvent", back_populates="episode", cascade="all, delete-orphan")
    replays = relationship("Replay", back_populates="episode")
