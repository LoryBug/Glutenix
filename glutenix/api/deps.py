from collections.abc import Generator

from fastapi import Depends
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from glutenix.config import DATABASE_URL
from glutenix.ml.gpr import PhysicsGPR


_engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


@event.listens_for(_engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


_SessionLocal = sessionmaker(_engine)


def get_db() -> Generator[Session, None, None]:
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


_gpr: PhysicsGPR | None = None


def get_gpr() -> PhysicsGPR:
    global _gpr
    if _gpr is None:
        _gpr = PhysicsGPR()
    return _gpr
