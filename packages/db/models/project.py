from sqlalchemy import Column, BigInteger, String, Text, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, SQLITE_BIGINT_PK


class Project(Base):
    __tablename__ = 'projects'

    id = Column(SQLITE_BIGINT_PK, primary_key=True, autoincrement=True)
    code = Column(String(100), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    owner_user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    owner = relationship("User", back_populates="owned_projects", foreign_keys=[owner_user_id])
    scenarios = relationship("Scenario", back_populates="project", cascade="all, delete-orphan")
    runs = relationship("Run", back_populates="project", cascade="all, delete-orphan")
