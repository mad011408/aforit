"""Tests for the Config module."""

import os
import tempfile
from pathlib import Path

import pytest

from aforit.core.config import Config


class TestConfig:
    def test_default_config(self):
        config = Config()
        assert config.model_name == "gpt-4"
        assert config.temperature == 0.7
        assert config.max_tokens == 4096
        assert config.memory_enabled is True
        assert config.safe_mode is True

    def test_custom_config(self):
        config = Config(model_name="claude-sonnet-4-20250514", temperature=0.5)
        assert config.model_name == "claude-sonnet-4-20250514"
        assert config.temperature == 0.5

    def test_to_yaml(self):
        config = Config()
        yaml_str = config.to_yaml()
        assert "model_name: gpt-4" in yaml_str
        assert "temperature: 0.7" in yaml_str

    def test_save_and_load(self, tmp_path):
        config = Config(model_name="test-model", temperature=0.3)
        save_path = tmp_path / "test_config.yaml"
        config.save(save_path)

        loaded = Config.from_file(save_path)
        assert loaded.model_name == "test-model"
        assert loaded.temperature == 0.3

    def test_merge(self):
        config = Config(model_name="gpt-4")
        merged = config.merge({"model_name": "gpt-4o", "temperature": 0.9})
        assert merged.model_name == "gpt-4o"
        assert merged.temperature == 0.9
        # Original unchanged
        assert config.model_name == "gpt-4"

    def test_from_file_missing(self):
        config = Config.from_file("/nonexistent/path.yaml")
        assert config.model_name == "gpt-4"  # defaults
