"""Session management - tracks conversation state."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Message:
    """A single message in the conversation."""

    role: str  # user, assistant, system, tool
    content: str
    timestamp: float = field(default_factory=time.time)
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: dict[str, Any] = field(default_factory=dict)
    token_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "message_id": self.message_id,
            "metadata": self.metadata,
            "token_count": self.token_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Message:
        return cls(**data)


@dataclass
class Session:
    """Manages the current conversation session."""

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    messages: list[Message] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)
    _total_tokens: int = 0

    def add_message(self, message: Message):
        """Add a message to the session."""
        self.messages.append(message)
        self._total_tokens += message.token_count

    def clear(self):
        """Clear all messages but keep the session."""
        self.messages.clear()
        self._total_tokens = 0

    def get_messages(self, limit: int | None = None) -> list[Message]:
        """Get messages, optionally limited to the last N."""
        if limit:
            return self.messages[-limit:]
        return self.messages

    def get_messages_as_dicts(self, limit: int | None = None) -> list[dict]:
        """Get messages as plain dicts for LLM APIs."""
        msgs = self.get_messages(limit)
        return [{"role": m.role, "content": m.content} for m in msgs if m.role != "tool"]

    @property
    def total_tokens(self) -> int:
        return self._total_tokens

    @property
    def message_count(self) -> int:
        return len(self.messages)

    def export(self, path: str | Path):
        """Export session to a JSON file."""
        path = Path(path)
        data = {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "metadata": self.metadata,
            "messages": [m.to_dict() for m in self.messages],
        }
        path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: str | Path) -> Session:
        """Load a session from a JSON file."""
        path = Path(path)
        data = json.loads(path.read_text())
        session = cls(
            session_id=data["session_id"],
            created_at=data["created_at"],
            metadata=data.get("metadata", {}),
        )
        for msg_data in data["messages"]:
            session.add_message(Message.from_dict(msg_data))
        return session

    def fork(self) -> Session:
        """Create a fork of this session (branching conversation)."""
        new_session = Session(metadata={"forked_from": self.session_id})
        for msg in self.messages:
            new_session.add_message(msg)
        return new_session

    def summarize(self) -> str:
        """Get a quick summary of the session."""
        user_msgs = [m for m in self.messages if m.role == "user"]
        assistant_msgs = [m for m in self.messages if m.role == "assistant"]
        return (
            f"Session {self.session_id[:8]}... | "
            f"{len(user_msgs)} user messages, {len(assistant_msgs)} assistant messages | "
            f"Total tokens: {self._total_tokens}"
        )
