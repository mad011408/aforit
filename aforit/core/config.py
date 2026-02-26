"""Configuration management for Aforit agent."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG_PATH = Path.home() / ".aforit" / "config.yaml"


@dataclass
class Config:
    """Central configuration object for the agent."""

    model_name: str = "gpt-4"
    theme_name: str = "monokai"
    memory_enabled: bool = True
    plugins: list[str] = field(default_factory=list)
    max_tokens: int = 4096
    temperature: float = 0.7
    context_window: int = 128000
    max_history: int = 50
    stream: bool = True
    tools_enabled: bool = True
    safe_mode: bool = True
    log_level: str = "INFO"
    data_dir: Path = field(default_factory=lambda: Path.home() / ".aforit" / "data")
    cache_dir: Path = field(default_factory=lambda: Path.home() / ".aforit" / "cache")
    plugins_dir: Path = field(default_factory=lambda: Path.home() / ".aforit" / "plugins")

    # API keys from environment
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))

    # Rate limiting
    requests_per_minute: int = 60
    tokens_per_minute: int = 90000

    # Retry settings
    max_retries: int = 3
    retry_delay: float = 1.0

    def __post_init__(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.plugins_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_file(cls, path: Path | str = DEFAULT_CONFIG_PATH) -> Config:
        """Load configuration from a YAML file."""
        path = Path(path)
        if not path.exists():
            return cls()
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_env(cls) -> Config:
        """Build config from environment variables."""
        overrides: dict[str, Any] = {}
        prefix = "AFORIT_"
        for key, fld in cls.__dataclass_fields__.items():
            env_key = f"{prefix}{key.upper()}"
            val = os.getenv(env_key)
            if val is not None:
                if fld.type == "bool":
                    overrides[key] = val.lower() in ("true", "1", "yes")
                elif fld.type == "int":
                    overrides[key] = int(val)
                elif fld.type == "float":
                    overrides[key] = float(val)
                else:
                    overrides[key] = val
        return cls(**overrides)

    def to_yaml(self) -> str:
        """Serialize config to YAML string."""
        data = {}
        for key in self.__dataclass_fields__:
            val = getattr(self, key)
            if isinstance(val, Path):
                val = str(val)
            data[key] = val
        return yaml.dump(data, default_flow_style=False, sort_keys=False)

    def save(self, path: Path | str = DEFAULT_CONFIG_PATH):
        """Save config to file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_yaml())

    def merge(self, overrides: dict[str, Any]) -> Config:
        """Return a new Config with overrides applied."""
        current = {k: getattr(self, k) for k in self.__dataclass_fields__}
        current.update(overrides)
        return Config(**current)
