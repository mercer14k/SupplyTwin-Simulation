import pytest
from fastapi.testclient import TestClient
from supplytwin.data import generate, templates

from apps.api.main import create_app


@pytest.fixture(scope="session")
def network():
    return generate()


@pytest.fixture
def scenario():
    return templates()[2]


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(str(tmp_path / "test.db"))) as client:
        yield client
