"""OpenAI LLM provider."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

from aforit.llm.base import BaseLLMProvider, LLMResponse


class OpenAIProvider(BaseLLMProvider):
    """Provider for OpenAI models (GPT-4, GPT-3.5, etc.)."""

    name = "openai"
    supports_streaming = True
    supports_tools = True
    supports_vision = True

    def __init__(self, api_key: str, base_url: str | None = None):
        self.api_key = api_key
        self.base_url = base_url
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        return self._client

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        model: str = "gpt-4",
        **kwargs,
    ) -> LLMResponse:
        client = self._get_client()
        params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        response = await client.chat.completions.create(**params)
        choice = response.choices[0]

        tool_calls = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments),
                })

        return LLMResponse(
            content=choice.message.content or "",
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            model=response.model,
            raw=response,
        )

    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        model: str = "gpt-4",
        **kwargs,
    ) -> AsyncIterator[dict[str, Any]]:
        client = self._get_client()
        params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        response = await client.chat.completions.create(**params)

        tool_call_buffer: dict[int, dict] = {}

        async for chunk in response:
            delta = chunk.choices[0].delta if chunk.choices else None
            if not delta:
                continue

            # Text content
            if delta.content:
                yield {"type": "text", "content": delta.content}

            # Tool calls (streamed incrementally)
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_call_buffer:
                        tool_call_buffer[idx] = {
                            "id": tc.id or "",
                            "name": "",
                            "arguments": "",
                        }
                    if tc.function:
                        if tc.function.name:
                            tool_call_buffer[idx]["name"] = tc.function.name
                        if tc.function.arguments:
                            tool_call_buffer[idx]["arguments"] += tc.function.arguments

            # Check for finish
            if chunk.choices[0].finish_reason == "tool_calls":
                for tc_data in tool_call_buffer.values():
                    try:
                        tc_data["arguments"] = json.loads(tc_data["arguments"])
                    except json.JSONDecodeError:
                        pass
                    yield {"type": "tool_call", **tc_data}

    def count_tokens(self, text: str) -> int:
        try:
            import tiktoken
            enc = tiktoken.encoding_for_model("gpt-4")
            return len(enc.encode(text))
        except ImportError:
            return len(text) // 4

    def get_available_models(self) -> list[str]:
        return [
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-3.5-turbo",
            "o1-preview",
            "o1-mini",
        ]
