from sqlalchemy import BigInteger, Integer
from sqlalchemy.orm import declarative_base

Base = declarative_base()
SQLITE_BIGINT_PK = BigInteger().with_variant(Integer, "sqlite")
