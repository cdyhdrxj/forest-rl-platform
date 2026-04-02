from sqlalchemy import Column, BigInteger, String, Text, ForeignKey, TIMESTAMP, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, SQLITE_BIGINT_PK


class ExperimentSuite(Base):
    __tablename__ = "experiment_suites"

    id = Column(SQLITE_BIGINT_PK, primary_key=True, autoincrement=True)
    code = Column(String(120), nullable=False, unique=True)
    title = Column(String(255), nullable=False)
    route_key = Column(String(100), nullable=False)
    mode = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)
    config_json = Column(JSON, nullable=False)
    summary_json = Column(JSON)
    manifest_uri = Column(Text)
    created_by_user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    started_at = Column(TIMESTAMP)
    finished_at = Column(TIMESTAMP)

    creator = relationship("User", back_populates="created_suites", foreign_keys=[created_by_user_id])
    suite_runs = relationship("ExperimentSuiteRun", back_populates="suite", cascade="all, delete-orphan")
