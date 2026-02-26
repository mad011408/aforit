"""Context window management - keeps conversations within token limits."""

from __future__ import annotations

from typing import Any

from aforit.core.config import Config
from aforit.core.session import Session


SYSTEM_PROMPT = """You are Aforit, an advanced terminal AI assistant. You have access to powerful tools including file management, shell commands, code execution, web scraping, search, and database operations.

Guidelines:
- Be direct and technical. Skip pleasantries.
- When asked to do something, use the appropriate tool.
- Show your reasoning when solving complex problems.
- If a task requires multiple steps, break it down and execute each step.
- Always confirm destructive operations before proceeding.
- Format code with proper syntax highlighting hints.
"""


class ContextManager:
    """Manages the context window to stay within token limits."""

    def __init__(self, config: Config):
        self.config = config
        self.max_context = config.context_window
        self.reserved_for_response = config.max_tokens
        self.available_context = self.max_context - self.reserved_for_response

    def build_messages(
        self,
        session: Session,
        extra_context: str = "",
        tool_schemas: list[dict] | None = None,
    ) -> list[dict[str, Any]]:
        """Build the messages array for the LLM API, fitting within context limits."""
        messages = []

        # System message
        system_content = SYSTEM_PROMPT
        if extra_context:
            system_content += f"\n\nRelevant context:\n{extra_context}"
        messages.append({"role": "system", "content": system_content})

        # Add conversation history, trimming from the beginning if needed
        history = session.get_messages_as_dicts()

        # Estimate tokens (rough: 1 token ~ 4 chars)
        total_chars = len(system_content)
        fitted_history = []

        for msg in reversed(history):
            msg_chars = len(msg["content"])
            if (total_chars + msg_chars) / 4 < self.available_context:
                fitted_history.insert(0, msg)
                total_chars += msg_chars
            else:
                break

        messages.extend(fitted_history)
        return messages

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation. For precise counting, use tiktoken."""
        return len(text) // 4

    def get_usage_ratio(self, session: Session) -> float:
        """How much of the context window is currently used (0.0 to 1.0)."""
        total_chars = sum(len(m.content) for m in session.messages)
        estimated_tokens = total_chars // 4
        return min(estimated_tokens / self.available_context, 1.0)

    def should_summarize(self, session: Session) -> bool:
        """Check if the conversation should be summarized to free up context."""
        return self.get_usage_ratio(session) > 0.8
