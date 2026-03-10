from sqlalchemy import Column, BigInteger, String, Text, ForeignKey, TIMESTAMP, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base
from .enums import ArtifactType

class Artifact(Base):
    __tablename__ = 'artifacts'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_id = Column(BigInteger, ForeignKey('runs.id'), nullable=False)
    model_id = Column(BigInteger, ForeignKey('models.id'))
    artifact_type = Column(SQLEnum(ArtifactType), nullable=False)
    name = Column(String(255), nullable=False)
    storage_uri = Column(Text, nullable=False)
    mime_type = Column(String(100))
    checksum = Column(String(128))
    size_bytes = Column(BigInteger)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    run = relationship("Run", back_populates="artifacts")
    model = relationship("Model", back_populates="artifacts")
