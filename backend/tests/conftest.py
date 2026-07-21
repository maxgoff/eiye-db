import os

import pytest
from fastapi.testclient import TestClient

from eiye_db import db
from eiye_db.main import app


@pytest.fixture(autouse=True)
def _clear_eiye_env(monkeypatch):
    """Isolate tests from ambient EIYE_* environment variables."""
    for key in list(os.environ):
        if key.startswith("EIYE_"):
            monkeypatch.delenv(key)


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    """Point the metadata store at a fresh SQLite file per test."""
    db.configure(f"sqlite:///{tmp_path}/eiye_test.db")


@pytest.fixture
def client():
    return TestClient(app)
