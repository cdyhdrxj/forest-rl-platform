from sqlalchemy import Column, BigInteger, String, Text, ForeignKey, TIMESTAMP, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import Enum as SQLEnum

from .base import Base, SQLITE_BIGINT_PK
from .enums import ProjectMode


class Scenario(Base):
    __tablename__ = 'scenarios'
    __table_args__ = (
        UniqueConstraint('project_id', 'code', name='uix_project_code'),
    )

    id = Column(SQLITE_BIGINT_PK, primary_key=True, autoincrement=True)
    project_id = Column(BigInteger, ForeignKey('projects.id'), nullable=False)
    code = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    mode = Column(SQLEnum(ProjectMode), nullable=False)
    description = Column(Text)
    created_by_user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    project = relationship("Project", back_populates="scenarios")
    creator = relationship("User", back_populates="created_scenarios")
    versions = relationship("ScenarioVersion", back_populates="scenario", cascade="all, delete-orphan")
