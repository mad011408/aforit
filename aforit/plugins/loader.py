"""Plugin loader - discovers and loads plugins dynamically."""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Any

from aforit.core.registry import ToolRegistry


class PluginBase:
    """Base class for all plugins."""

    name: str = "base_plugin"
    version: str = "1.0.0"
    description: str = "Base plugin"

    def on_load(self, registry: ToolRegistry):
        """Called when the plugin is loaded. Register tools here."""
        pass

    def on_unload(self):
        """Called when the plugin is unloaded. Cleanup here."""
        pass


# Built-in plugin registry
BUILTIN_PLUGINS: dict[str, dict[str, Any]] = {
    "git": {
        "module": "aforit.plugins.git_plugin",
        "class": "GitPlugin",
        "description": "Git repository operations (status, commit, diff, log, branch)",
    },
    "docker": {
        "module": "aforit.plugins.docker_plugin",
        "class": "DockerPlugin",
        "description": "Docker container and image management",
    },
    "api_tester": {
        "module": "aforit.plugins.api_tester",
        "class": "ApiTesterPlugin",
        "description": "HTTP API testing and endpoint exploration",
    },
}


class PluginLoader:
    """Discovers and loads plugins."""

    def __init__(self, plugins_dir: Path | None = None):
        self.plugins_dir = plugins_dir
        self._loaded: dict[str, PluginBase] = {}

    def discover_plugins(self) -> dict[str, dict[str, Any]]:
        """Discover all available plugins (built-in and external)."""
        available = dict(BUILTIN_PLUGINS)

        # Scan plugins directory for external plugins
        if self.plugins_dir and self.plugins_dir.exists():
            for path in self.plugins_dir.glob("*.py"):
                if path.stem.startswith("_"):
                    continue
                available[path.stem] = {
                    "module": None,
                    "path": str(path),
                    "class": None,
                    "description": f"External plugin: {path.stem}",
                }

        return available

    def load_plugin(self, name: str, registry: ToolRegistry) -> bool:
        """Load a plugin by name."""
        if name in self._loaded:
            return True

        # Check built-in plugins
        if name in BUILTIN_PLUGINS:
            info = BUILTIN_PLUGINS[name]
            try:
                module = importlib.import_module(info["module"])
                plugin_class = getattr(module, info["class"])
                plugin = plugin_class()
                plugin.on_load(registry)
                self._loaded[name] = plugin
                return True
            except (ImportError, AttributeError) as e:
                print(f"Failed to load plugin '{name}': {e}")
                return False

        # Check external plugins
        if self.plugins_dir:
            plugin_path = self.plugins_dir / f"{name}.py"
            if plugin_path.exists():
                return self._load_external(name, plugin_path, registry)

        return False

    def _load_external(self, name: str, path: Path, registry: ToolRegistry) -> bool:
        """Load an external plugin from a file path."""
        try:
            spec = importlib.util.spec_from_file_location(f"aforit_plugin_{name}", str(path))
            if not spec or not spec.loader:
                return False

            module = importlib.util.module_from_spec(spec)
            sys.modules[f"aforit_plugin_{name}"] = module
            spec.loader.exec_module(module)

            # Look for a class that inherits from PluginBase
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, PluginBase)
                    and attr is not PluginBase
                ):
                    plugin = attr()
                    plugin.on_load(registry)
                    self._loaded[name] = plugin
                    return True

            return False
        except Exception as e:
            print(f"Failed to load external plugin '{name}': {e}")
            return False

    def unload_plugin(self, name: str) -> bool:
        """Unload a plugin."""
        plugin = self._loaded.get(name)
        if plugin:
            plugin.on_unload()
            del self._loaded[name]
            return True
        return False

    def get_loaded(self) -> list[str]:
        """Get names of loaded plugins."""
        return list(self._loaded.keys())
