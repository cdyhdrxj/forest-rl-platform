from sqlalchemy import Column, BigInteger, String, Text, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, SQLITE_BIGINT_PK


class ScenarioLayer(Base):
    __tablename__ = 'scenario_layers'

    id = Column(SQLITE_BIGINT_PK, primary_key=True, autoincrement=True)
    scenario_version_id = Column(BigInteger, ForeignKey('scenario_versions.id'), nullable=False)
    layer_type = Column(String(100), nullable=False)
    file_uri = Column(Text, nullable=False)
    file_format = Column(String(50))
    description = Column(Text)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    scenario_version = relationship("ScenarioVersion", back_populates="layers")
