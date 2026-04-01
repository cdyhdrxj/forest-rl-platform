from sqlalchemy import Column, BigInteger, String, Integer, ForeignKey, TIMESTAMP, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class ExperimentSuiteRun(Base):
    __tablename__ = "experiment_suite_runs"
    __table_args__ = (
        UniqueConstraint("suite_id", "run_id", name="uix_suite_run"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    suite_id = Column(BigInteger, ForeignKey("experiment_suites.id"), nullable=False)
    run_id = Column(BigInteger, ForeignKey("runs.id"), nullable=False)
    scenario_family = Column(String(100), nullable=False)
    dataset_split = Column(String(50), nullable=False)
    method_code = Column(String(100), nullable=False)
    replicate_index = Column(Integer, nullable=False, default=1)
    role = Column(String(50), nullable=False)
    train_seed = Column(BigInteger)
    eval_seed = Column(BigInteger)
    group_key = Column(String(150), nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    suite = relationship("ExperimentSuite", back_populates="suite_runs")
    run = relationship("Run")
