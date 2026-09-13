import pytest

from app.config import Settings
from app.db import init_db
from app import repositories, retrieval
from data.seed import seed_database


@pytest.fixture
def seed_db(tmp_path, monkeypatch):
    database = tmp_path / "app.db"
    init_db(str(database))
    seed_database(str(database))
    monkeypatch.setattr(repositories, "settings", Settings(database_path=str(database)))
    monkeypatch.setattr(retrieval, "settings", Settings(database_path=str(database)))
    return database
