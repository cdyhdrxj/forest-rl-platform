from sqlalchemy import Column, BigInteger, Integer, Float, ForeignKey, TIMESTAMP, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, SQLITE_BIGINT_PK


class MetricPoint(Base):
    __tablename__ = 'metric_points'
    __table_args__ = (
        UniqueConstraint('metric_series_id', 'point_index', name='uix_series_point'),
    )

    id = Column(SQLITE_BIGINT_PK, primary_key=True, autoincrement=True)
    metric_series_id = Column(BigInteger, ForeignKey('metric_series.id'), nullable=False)
    point_index = Column(Integer, nullable=False)
    train_step = Column(BigInteger)
    episode_index = Column(Integer)
    wall_time_sec = Column(Float)
    value = Column(Float, nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    series = relationship("MetricSeries", back_populates="points")
