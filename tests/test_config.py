from app.config import Settings
from pathlib import Path


def test_settings_disable_llm_without_api_key(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    settings = Settings()
    assert settings.llm_enabled is False
    assert Path(settings.database_path).parts[-2:] == ("data", "app.db")
