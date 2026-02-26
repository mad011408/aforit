"""Anthropic LLM provider."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

from aforit.llm.base import BaseLLMProvider, LLMResponse


class AnthropicProvider(BaseLLMProvider):
    """Provider for Anthropic models (Claude)."""

    name = "anthropic"
    supports_streaming = True
    supports_tools = True
    supports_vision = True

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = None

    def _get_client(self):
        if self._client is None:
            from anthropic import AsyncAnthropic
            self._client = AsyncAnthropic(api_key=self.api_key)
        return self._client

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        model: str = "claude-sonnet-4-20250514",
        **kwargs,
    ) -> LLMResponse:
        client = self._get_client()

        # Extract system message
        system = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                chat_messages.append(msg)

        params: dict[str, Any] = {
            "model": model,
            "messages": chat_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system:
            params["system"] = system

        if tools:
            # Convert OpenAI tool format to Anthropic format
            anthropic_tools = []
            for tool in tools:
                func = tool.get("function", tool)
                anthropic_tools.append({
                    "name": func["name"],
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {}),
                })
            params["tools"] = anthropic_tools

        response = await client.messages.create(**params)

        content = ""
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "arguments": block.input,
                })

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=response.stop_reason,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
            model=model,
            raw=response,
        )

    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        model: str = "claude-sonnet-4-20250514",
        **kwargs,
    ) -> AsyncIterator[dict[str, Any]]:
        client = self._get_client()

        system = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                chat_messages.append(msg)

        params: dict[str, Any] = {
            "model": model,
            "messages": chat_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system:
            params["system"] = system

        if tools:
            anthropic_tools = []
            for tool in tools:
                func = tool.get("function", tool)
                anthropic_tools.append({
                    "name": func["name"],
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {}),
                })
            params["tools"] = anthropic_tools

        async with client.messages.stream(**params) as stream:
            async for event in stream:
                if hasattr(event, "type"):
                    if event.type == "content_block_delta":
                        if hasattr(event.delta, "text"):
                            yield {"type": "text", "content": event.delta.text}
                        elif hasattr(event.delta, "partial_json"):
                            yield {"type": "tool_input_delta", "content": event.delta.partial_json}
                    elif event.type == "content_block_start":
                        if hasattr(event.content_block, "name"):
                            yield {
                                "type": "tool_call_start",
                                "name": event.content_block.name,
                                "id": event.content_block.id,
                            }

    def count_tokens(self, text: str) -> int:
        # Rough estimation for Claude models
        return len(text) // 4

    def get_available_models(self) -> list[str]:
        return [
            "claude-sonnet-4-20250514",
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229",
            "claude-3-haiku-20240307",
        ]
