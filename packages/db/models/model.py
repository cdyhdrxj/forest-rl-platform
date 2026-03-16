from sqlalchemy import Column, BigInteger, String, Integer, Boolean, Text, ForeignKey, TIMESTAMP, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class Model(Base):
    __tablename__ = 'models'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_id = Column(BigInteger, ForeignKey('runs.id'), nullable=False)
    name = Column(String(255), nullable=False)
    framework = Column(String(100), nullable=False)
    storage_uri = Column(Text, nullable=False)
    checkpoint_epoch = Column(Integer)
    is_best = Column(Boolean, nullable=False, server_default='false')
    metrics_json = Column(JSON)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    run = relationship("Run", back_populates="models")
    artifacts = relationship("Artifact", back_populates="model")
