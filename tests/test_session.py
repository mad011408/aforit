"""Tests for the Session module."""

import json
from pathlib import Path

import pytest

from aforit.core.session import Session, Message


class TestMessage:
    def test_create_message(self):
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.message_id
        assert msg.timestamp > 0

    def test_message_to_dict(self):
        msg = Message(role="user", content="test")
        d = msg.to_dict()
        assert d["role"] == "user"
        assert d["content"] == "test"
        assert "message_id" in d

    def test_message_from_dict(self):
        data = {"role": "assistant", "content": "response", "timestamp": 1000.0, "message_id": "abc", "metadata": {}, "token_count": 10}
        msg = Message.from_dict(data)
        assert msg.role == "assistant"
        assert msg.content == "response"
        assert msg.token_count == 10


class TestSession:
    def test_create_session(self):
        session = Session()
        assert session.session_id
        assert session.message_count == 0

    def test_add_message(self):
        session = Session()
        session.add_message(Message(role="user", content="Hello"))
        assert session.message_count == 1

    def test_clear(self):
        session = Session()
        session.add_message(Message(role="user", content="Hello"))
        session.clear()
        assert session.message_count == 0

    def test_get_messages_limit(self):
        session = Session()
        for i in range(10):
            session.add_message(Message(role="user", content=f"msg {i}"))
        last_3 = session.get_messages(limit=3)
        assert len(last_3) == 3
        assert last_3[0].content == "msg 7"

    def test_export_and_load(self, tmp_path):
        session = Session()
        session.add_message(Message(role="user", content="Hello"))
        session.add_message(Message(role="assistant", content="Hi there"))

        export_path = tmp_path / "session.json"
        session.export(export_path)

        loaded = Session.load(export_path)
        assert loaded.message_count == 2
        assert loaded.messages[0].content == "Hello"

    def test_fork(self):
        session = Session()
        session.add_message(Message(role="user", content="Hello"))
        forked = session.fork()
        assert forked.session_id != session.session_id
        assert forked.message_count == 1
        assert forked.metadata["forked_from"] == session.session_id

    def test_summarize(self):
        session = Session()
        session.add_message(Message(role="user", content="Hello"))
        summary = session.summarize()
        assert "1 user messages" in summary
