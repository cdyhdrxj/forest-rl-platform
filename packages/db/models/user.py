from sqlalchemy import Column, BigInteger, String, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    role = Column(String(100))
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    owned_projects = relationship("Project", back_populates="owner", foreign_keys="Project.owner_user_id")
    created_scenarios = relationship("Scenario", back_populates="creator", foreign_keys="Scenario.created_by_user_id")
    created_runs = relationship("Run", back_populates="creator", foreign_keys="Run.created_by_user_id")
