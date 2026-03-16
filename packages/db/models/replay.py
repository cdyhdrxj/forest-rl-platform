from sqlalchemy import Column, BigInteger, String, Text, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class Replay(Base):
    __tablename__ = 'replays'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_id = Column(BigInteger, ForeignKey('runs.id'), nullable=False)
    episode_id = Column(BigInteger, ForeignKey('episodes.id'))
    name = Column(String(255), nullable=False)
    storage_uri = Column(Text, nullable=False)
    format = Column(String(50))
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    run = relationship("Run", back_populates="replays")
    episode = relationship("Episode", back_populates="replays")
