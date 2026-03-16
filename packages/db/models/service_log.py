from sqlalchemy import Column, BigInteger, String, Text, ForeignKey, TIMESTAMP, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class ServiceLog(Base):
    __tablename__ = 'service_logs'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_id = Column(BigInteger, ForeignKey('runs.id'))
    service_name = Column(String(100), nullable=False)
    level = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    payload_json = Column(JSON)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    run = relationship("Run", back_populates="service_logs")
