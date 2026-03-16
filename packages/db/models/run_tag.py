from sqlalchemy import Column, BigInteger, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from .base import Base


class RunTag(Base):
    __tablename__ = 'run_tags'
    __table_args__ = (
        UniqueConstraint('run_id', 'tag', name='uix_run_tag'),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_id = Column(BigInteger, ForeignKey('runs.id'), nullable=False)
    tag = Column(String(100), nullable=False)

    run = relationship("Run", back_populates="tags")
