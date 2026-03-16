from sqlalchemy import Column, BigInteger, String, Text, ForeignKey, TIMESTAMP, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class MetricSeries(Base):
    __tablename__ = 'metric_series'
    __table_args__ = (
        UniqueConstraint('run_id', 'name', 'aggregation', name='uix_run_metric'),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_id = Column(BigInteger, ForeignKey('runs.id'), nullable=False)
    name = Column(String(150), nullable=False)
    unit = Column(String(50))
    aggregation = Column(String(50))
    source = Column(String(100))
    description = Column(Text)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    run = relationship("Run", back_populates="metric_series")
    points = relationship("MetricPoint", back_populates="series", cascade="all, delete-orphan")
