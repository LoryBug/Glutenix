import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from glutenix.db.base import Base


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session = sessionmaker(engine)()
    yield session
    session.close()
