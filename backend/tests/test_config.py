"""Configuration management tests: env var support with EIYE_ prefix."""

from eiye_db.config import Settings


def test_defaults():
    s = Settings(_env_file=None)
    assert s.app_name == "eiye_db"
    assert s.port == 8000
    assert s.debug is False


def test_env_override(monkeypatch):
    monkeypatch.setenv("EIYE_PORT", "9000")
    monkeypatch.setenv("EIYE_DEBUG", "true")
    monkeypatch.setenv("EIYE_LOG_LEVEL", "DEBUG")
    s = Settings(_env_file=None)
    assert s.port == 9000
    assert s.debug is True
    assert s.log_level == "DEBUG"


def test_unprefixed_env_ignored(monkeypatch):
    monkeypatch.setenv("PORT", "1234")
    s = Settings(_env_file=None)
    assert s.port == 8000
