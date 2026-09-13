from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import Settings, settings


class LLMClient:
    def generate_json(self, system_prompt: str, user_prompt: str, schema: dict) -> dict:
        raise NotImplementedError


class LocalFallbackLLM(LLMClient):
    def generate_json(self, system_prompt: str, user_prompt: str, schema: dict) -> dict:
        return {
            "answer": "当前使用本地确定性回退逻辑，结论仅基于设备数据和演示知识库。",
            "grounded": True,
            "schema": schema.get("title", "structured_response"),
        }


class OpenAICompatibleLLM(LLMClient):
    def __init__(self, config: Settings = settings, timeout: float = 30.0) -> None:
        if not config.llm_enabled:
            raise ValueError("LLM_API_KEY 未配置")
        self.config = config
        self.timeout = timeout

    def generate_json(self, system_prompt: str, user_prompt: str, schema: dict) -> dict:
        payload = {
            "model": self.config.llm_model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        response = httpx.post(
            f"{self.config.llm_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {self.config.llm_api_key}"},
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        if isinstance(content, list):
            content = "".join(item.get("text", "") for item in content)
        result: Any = json.loads(content)
        if not isinstance(result, dict):
            raise ValueError("LLM 返回的 JSON 不是对象")
        return result


def get_llm_client(config: Settings = settings) -> LLMClient:
    if config.llm_enabled:
        return OpenAICompatibleLLM(config)
    return LocalFallbackLLM()
