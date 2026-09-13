from app.db import get_connection, init_db
from data.seed import seed_database


def test_seed_creates_repeatable_demo_data(tmp_path):
    database = tmp_path / "app.db"
    init_db(str(database))
    seed_database(str(database))
    connection = get_connection(str(database))
    first = connection.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
    seed_database(str(database))
    second = connection.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
    assert first >= 6
    assert second == first
    connection.close()
