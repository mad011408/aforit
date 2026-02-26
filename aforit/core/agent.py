"""Main Agent class - orchestrates all components."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, AsyncIterator

from aforit.core.config import Config
from aforit.core.context import ContextManager
from aforit.core.memory import MemoryStore
from aforit.core.registry import ToolRegistry
from aforit.core.session import Session, Message
from aforit.llm.router import ModelRouter
from aforit.plugins.loader import PluginLoader
from aforit.tools.base import ToolResult

if TYPE_CHECKING:
    from aforit.ui.terminal import TerminalUI


class Agent:
    """The central AI agent that ties everything together."""

    def __init__(self, config: Config):
        self.config = config
        self.session = Session()
        self.context = ContextManager(config)
        self.memory = MemoryStore(config) if config.memory_enabled else None
        self.router = ModelRouter(config)
        self.registry = ToolRegistry()
        self.plugin_loader = PluginLoader()
        self._running = False

        # Register built-in tools
        self._register_builtin_tools()

        # Load requested plugins
        for plugin_name in config.plugins:
            self.plugin_loader.load_plugin(plugin_name, self.registry)

    def _register_builtin_tools(self):
        """Register all built-in tools with the registry."""
        from aforit.tools.file_manager import FileManagerTool
        from aforit.tools.shell_tool import ShellTool
        from aforit.tools.code_executor import CodeExecutorTool
        from aforit.tools.web_scraper import WebScraperTool
        from aforit.tools.search_tool import SearchTool
        from aforit.tools.database_tool import DatabaseTool

        self.registry.register(FileManagerTool())
        self.registry.register(ShellTool(safe_mode=self.config.safe_mode))
        self.registry.register(CodeExecutorTool())
        self.registry.register(WebScraperTool())
        self.registry.register(SearchTool())
        self.registry.register(DatabaseTool())

    async def process_message(self, user_input: str) -> AsyncIterator[str]:
        """Process a user message and yield response chunks."""
        # Add user message to session
        self.session.add_message(Message(role="user", content=user_input))

        # Retrieve relevant memories
        context_additions = ""
        if self.memory:
            memories = await self.memory.search(user_input, top_k=5)
            if memories:
                context_additions = "\n".join(
                    f"[Memory] {m['content']}" for m in memories
                )

        # Build the prompt with context
        messages = self.context.build_messages(
            self.session, context_additions, self.registry.get_tool_schemas()
        )

        # Stream response from LLM
        full_response = ""
        tool_calls = []

        async for chunk in self.router.stream(messages, tools=self.registry.get_tool_schemas()):
            if chunk.get("type") == "text":
                full_response += chunk["content"]
                yield chunk["content"]
            elif chunk.get("type") == "tool_call":
                tool_calls.append(chunk)

        # Handle tool calls
        if tool_calls:
            for tc in tool_calls:
                tool_name = tc["name"]
                tool_args = tc["arguments"]
                yield f"\n[Running tool: {tool_name}]\n"

                result: ToolResult = await self.registry.execute(tool_name, tool_args)

                if result.success:
                    yield f"[Tool result]: {result.output[:500]}\n"
                else:
                    yield f"[Tool error]: {result.error}\n"

                # Feed tool result back to LLM for follow-up
                self.session.add_message(Message(
                    role="tool",
                    content=result.output if result.success else result.error,
                    metadata={"tool_name": tool_name},
                ))

            # Get follow-up response
            messages = self.context.build_messages(self.session)
            async for chunk in self.router.stream(messages):
                if chunk.get("type") == "text":
                    full_response += chunk["content"]
                    yield chunk["content"]

        # Save to session and memory
        self.session.add_message(Message(role="assistant", content=full_response))
        if self.memory:
            await self.memory.store(user_input, full_response)

    async def run_single(self, task: str) -> str:
        """Run a single task and return the result."""
        result_parts = []
        async for chunk in self.process_message(task):
            result_parts.append(chunk)
        return "".join(result_parts)

    async def run_interactive(self, ui: "TerminalUI"):
        """Run the interactive chat loop."""
        self._running = True
        ui.print_welcome()

        while self._running:
            try:
                user_input = await ui.get_input()
                if not user_input:
                    continue

                if user_input.strip().lower() in ("/quit", "/exit", "/q"):
                    ui.print_goodbye()
                    break

                if user_input.startswith("/"):
                    await self._handle_command(user_input, ui)
                    continue

                async for chunk in self.process_message(user_input):
                    ui.print_stream(chunk)
                ui.print_stream_end()

            except KeyboardInterrupt:
                ui.print_goodbye()
                break
            except Exception as e:
                ui.print_error(str(e))

    async def _handle_command(self, command: str, ui: "TerminalUI"):
        """Handle slash commands."""
        parts = command.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        commands = {
            "/help": lambda: ui.print_help(self.registry.list_tools()),
            "/clear": lambda: self.session.clear(),
            "/history": lambda: ui.print_history(self.session.messages),
            "/model": lambda: ui.print_info(f"Current model: {self.config.model_name}"),
            "/tools": lambda: ui.print_tools(self.registry.list_tools()),
            "/memory": lambda: ui.print_info(
                f"Memory: {'enabled' if self.memory else 'disabled'}"
            ),
            "/export": lambda: self.session.export(arg or "session.json"),
            "/theme": lambda: ui.set_theme(arg),
        }

        handler = commands.get(cmd)
        if handler:
            handler()
        else:
            ui.print_error(f"Unknown command: {cmd}. Type /help for available commands.")
