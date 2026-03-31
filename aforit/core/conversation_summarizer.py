"""Conversation summarizer - compress long conversations to save context."""

from __future__ import annotations

from typing import Any

from aforit.core.session import Message


class ConversationSummarizer:
    """Summarize conversation history to fit within context limits.

    Uses a progressive summarization strategy:
    1. Keep recent messages intact
    2. Summarize older messages into condensed form
    3. Keep key decision points and tool outputs
    """

    def __init__(self, keep_recent: int = 10, summary_max_tokens: int = 500):
        self.keep_recent = keep_recent
        self.summary_max_tokens = summary_max_tokens

    def should_summarize(self, messages: list[Message], max_tokens: int) -> bool:
        """Check if summarization is needed."""
        total_chars = sum(len(m.content) for m in messages)
        estimated_tokens = total_chars // 4
        return estimated_tokens > max_tokens * 0.7

    def summarize(self, messages: list[Message]) -> list[Message]:
        """Summarize older messages while keeping recent ones intact."""
        if len(messages) <= self.keep_recent:
            return messages

        # Split into old and recent
        old_messages = messages[:-self.keep_recent]
        recent_messages = messages[-self.keep_recent:]

        # Create summary of old messages
        summary = self._create_summary(old_messages)

        # Return summary + recent messages
        summary_message = Message(
            role="system",
            content=f"[Conversation Summary]\n{summary}",
            metadata={"is_summary": True, "summarized_count": len(old_messages)},
        )

        return [summary_message] + recent_messages

    def _create_summary(self, messages: list[Message]) -> str:
        """Create a condensed summary of messages."""
        parts = []

        # Group by topic/exchange
        exchanges = self._group_exchanges(messages)

        for exchange in exchanges:
            user_msgs = [m for m in exchange if m.role == "user"]
            assistant_msgs = [m for m in exchange if m.role == "assistant"]
            tool_msgs = [m for m in exchange if m.role == "tool"]

            if user_msgs:
                topic = user_msgs[0].content[:100]
                parts.append(f"- User asked about: {topic}")

            if tool_msgs:
                tool_names = set(m.metadata.get("tool_name", "unknown") for m in tool_msgs)
                parts.append(f"  Tools used: {', '.join(tool_names)}")

            if assistant_msgs:
                # Take first and last sentence of each response
                response = assistant_msgs[-1].content
                first_line = response.split("\n")[0][:150]
                parts.append(f"  Response: {first_line}")

        summary = "\n".join(parts)

        # Trim if too long
        max_chars = self.summary_max_tokens * 4
        if len(summary) > max_chars:
            summary = summary[:max_chars] + "\n[...truncated]"

        return summary

    def _group_exchanges(self, messages: list[Message]) -> list[list[Message]]:
        """Group messages into user-assistant exchanges."""
        exchanges: list[list[Message]] = []
        current: list[Message] = []

        for msg in messages:
            if msg.role == "user" and current:
                exchanges.append(current)
                current = []
            current.append(msg)

        if current:
            exchanges.append(current)

        return exchanges

    def extract_key_decisions(self, messages: list[Message]) -> list[str]:
        """Extract key decisions and actions from conversation."""
        decisions = []
        for msg in messages:
            if msg.role == "tool" and msg.metadata.get("tool_name"):
                tool = msg.metadata["tool_name"]
                outcome = "success" if "error" not in msg.content.lower() else "failed"
                decisions.append(f"Used {tool}: {outcome}")
            elif msg.role == "assistant" and any(
                keyword in msg.content.lower()
                for keyword in ["created", "updated", "deleted", "installed", "configured"]
            ):
                first_line = msg.content.split("\n")[0][:100]
                decisions.append(f"Action: {first_line}")
        return decisions
