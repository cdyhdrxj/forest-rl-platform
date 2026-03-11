from sqlalchemy import Column, BigInteger, String, Text, ForeignKey, TIMESTAMP, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base
from .enums import ProjectMode, RunStatus

class Run(Base):
    __tablename__ = 'runs'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    project_id = Column(BigInteger, ForeignKey('projects.id'), nullable=False)
    scenario_version_id = Column(BigInteger, ForeignKey('scenario_versions.id'), nullable=False)
    algorithm_id = Column(BigInteger, ForeignKey('algorithms.id'), nullable=False)
    created_by_user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False)
    mode = Column(SQLEnum(ProjectMode), nullable=False)
    status = Column(SQLEnum(RunStatus), nullable=False)
    title = Column(String(255))
    description = Column(Text)
    seed = Column(BigInteger)
    config_json = Column(JSON, nullable=False)
    started_at = Column(TIMESTAMP)
    finished_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    project = relationship("Project", back_populates="runs")
    scenario_version = relationship("ScenarioVersion", back_populates="runs")
    algorithm = relationship("Algorithm", back_populates="runs")
    creator = relationship("User", back_populates="created_runs")
    tags = relationship("RunTag", back_populates="run", cascade="all, delete-orphan")
    models = relationship("Model", back_populates="run", cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="run", cascade="all, delete-orphan")
    episodes = relationship("Episode", back_populates="run", cascade="all, delete-orphan")
    metric_series = relationship("MetricSeries", back_populates="run", cascade="all, delete-orphan")
    replays = relationship("Replay", back_populates="run", cascade="all, delete-orphan")
    service_logs = relationship("ServiceLog", back_populates="run")
