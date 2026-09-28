import sqlite3

import pytest
from supplytwin.store import Store


def test_readonly_credentials_and_persistence(tmp_path):
    path = str(tmp_path / "test.db")
    store = Store(path)
    store.put_network({"id": "test", "data": 1})
    assert Store(path).network("test")["data"] == 1
    with store.connection(True) as db:
        with pytest.raises(sqlite3.OperationalError):
            db.execute("DELETE FROM networks")
    assert store.network("' OR 1=1 --") is None
