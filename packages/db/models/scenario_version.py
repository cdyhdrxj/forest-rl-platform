from sqlalchemy import Column, BigInteger, Integer, Boolean, Text, ForeignKey, TIMESTAMP, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, SQLITE_BIGINT_PK


class ScenarioVersion(Base):
    __tablename__ = 'scenario_versions'
    __table_args__ = (
        UniqueConstraint('scenario_id', 'version_no', name='uix_scenario_version'),
    )

    id = Column(SQLITE_BIGINT_PK, primary_key=True, autoincrement=True)
    scenario_id = Column(BigInteger, ForeignKey('scenarios.id'), nullable=False)
    version_no = Column(Integer, nullable=False)
    seed = Column(BigInteger)
    terrain_config_json = Column(JSON)
    obstacle_config_json = Column(JSON)
    event_config_json = Column(JSON)
    sensor_config_json = Column(JSON)
    reward_config_json = Column(JSON)
    world_file_uri = Column(Text)
    preview_image_uri = Column(Text)
    is_active = Column(Boolean, nullable=False, server_default='true')
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    scenario = relationship("Scenario", back_populates="versions")
    layers = relationship("ScenarioLayer", back_populates="scenario_version", cascade="all, delete-orphan")
    runs = relationship("Run", back_populates="scenario_version", cascade="all, delete-orphan")
