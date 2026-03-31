"""Local LLM provider - supports Ollama and other local inference servers."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from aforit.llm.base import BaseLLMProvider, LLMResponse


class LocalProvider(BaseLLMProvider):
    """Provider for locally-hosted models via Ollama or compatible APIs."""

    name = "local"
    supports_streaming = True
    supports_tools = False
    supports_vision = False

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip("/")

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        model: str = "llama3",
        **kwargs,
    ) -> LLMResponse:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()

        return LLMResponse(
            content=data.get("message", {}).get("content", ""),
            finish_reason="stop",
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0)
                + data.get("eval_count", 0),
            },
            model=model,
            raw=data,
        )

    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        model: str = "llama3",
        **kwargs,
    ) -> AsyncIterator[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": True,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    },
                },
            ) as response:
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield {"type": "text", "content": content}
                        if data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue

    async def list_local_models(self) -> list[dict[str, Any]]:
        """List models available on the local Ollama instance."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
                return data.get("models", [])
            except (httpx.HTTPError, Exception):
                return []

    async def pull_model(self, model_name: str) -> AsyncIterator[dict[str, Any]]:
        """Pull a model from the Ollama registry."""
        async with httpx.AsyncClient(timeout=600.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/pull",
                json={"name": model_name},
            ) as response:
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            yield json.loads(line)
                        except json.JSONDecodeError:
                            continue

    def count_tokens(self, text: str) -> int:
        return len(text) // 4

    def get_available_models(self) -> list[str]:
        return [
            "llama3",
            "llama3:70b",
            "codellama",
            "mistral",
            "mixtral",
            "phi3",
            "gemma",
            "deepseek-coder",
        ]
