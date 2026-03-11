from sqlalchemy import Column, BigInteger, String, Text, ForeignKey, TIMESTAMP, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base
from .enums import AlgorithmFamily, ProjectMode

class Algorithm(Base):
    __tablename__ = 'algorithms'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    code = Column(String(100), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    family = Column(SQLEnum(AlgorithmFamily), nullable=False)
    mode = Column(SQLEnum(ProjectMode), nullable=False)
    framework = Column(String(100))
    description = Column(Text)
    default_config_json = Column(JSON)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    runs = relationship("Run", back_populates="algorithm", cascade="all, delete-orphan")
