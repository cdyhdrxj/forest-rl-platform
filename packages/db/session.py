import os
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session


def _default_sqlite_url() -> str:
    repo_root = Path(__file__).resolve().parents[2]
    db_path = repo_root / "data" / "platform_dev.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path.as_posix()}"


def get_database_url() -> str:
    return os.getenv("DATABASE_URL") or _default_sqlite_url()


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    database_url = get_database_url()
    engine_kwargs = {
        "pool_pre_ping": True,
    }
    if database_url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}

    engine = create_engine(database_url, **engine_kwargs)

    if database_url.startswith("sqlite"):
        import packages.db.models  # noqa: F401
        from packages.db.models.base import Base

        Base.metadata.create_all(engine)

    return engine


@lru_cache(maxsize=1)
def get_session_factory():
    return sessionmaker(
        bind=get_engine(),
        autoflush=False,
        expire_on_commit=False,
    )


# Зависимость для FastAPI
def get_db():
    db: Session = get_session_factory()()
    try:
        yield db
    finally:
        db.close()


# context manager для работы с БД вне FastAPI
@contextmanager
def db_session():
    db: Session = get_session_factory()()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
