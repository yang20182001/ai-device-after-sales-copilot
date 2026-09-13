from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    app_name: str = "AI 设备售后与运维助手"
    database_path: str = os.getenv(
        "DATABASE_PATH", str(PROJECT_ROOT / "data" / "app.db")
    )
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_base_url: str = os.getenv(
        "LLM_BASE_URL", "https://api.openai.com/v1"
    )
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_api_key.strip())


settings = Settings()
