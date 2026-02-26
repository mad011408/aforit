# Aforit - Advanced Terminal AI Agent

A full-featured terminal AI agent framework built in Python. Aforit gives your terminal superpowers with LLM-powered intelligence, tool execution, persistent memory, and a plugin system.

## Features

- **Multi-Provider LLM Support** - OpenAI (GPT-4), Anthropic (Claude), and local models via Ollama
- **Intelligent Model Routing** - automatic failover between providers with retry logic
- **Built-in Tools** - file management, shell execution, code runner, web scraping, search, database operations
- **Plugin System** - extensible architecture with Git, Docker, and API testing plugins
- **Rich Terminal UI** - colorful output with 8 themes (Monokai, Dracula, Nord, Catppuccin, etc.)
- **Long-term Memory** - semantic search over past conversations
- **Processing Pipelines** - chain operations together via YAML configs
- **Task Scheduler** - async task queue with priority and retry
- **Event Bus** - pub/sub for inter-component communication
- **Middleware Chain** - input/output processing with prompt injection detection
- **Safety Controls** - blocked command patterns, safe code execution sandbox
- **Metrics & Monitoring** - counters, gauges, histograms for performance tracking

## Project Structure

```
aforit/
  __init__.py
  main.py                  # CLI entry point (click)
  core/
    __init__.py
    agent.py               # Main agent orchestrator
    config.py              # Configuration management (YAML/env)
    context.py             # Context window management
    conversation_summarizer.py  # Progressive conversation compression
    event_bus.py           # Pub/sub event system
    memory.py              # Long-term memory with semantic search
    middleware.py           # Message processing middleware chain
    pipeline.py            # Multi-step processing pipelines
    registry.py            # Tool registration and execution
    scheduler.py           # Async task scheduler with retry
    session.py             # Conversation session management
  llm/
    __init__.py
    base.py                # Abstract LLM provider interface
    openai_provider.py     # OpenAI GPT integration
    anthropic_provider.py  # Anthropic Claude integration
    local_provider.py      # Ollama / local model support
    router.py              # Intelligent model routing with fallback
  tools/
    __init__.py
    base.py                # Base tool interface
    file_manager.py        # File system operations
    shell_tool.py          # Safe shell command execution
    code_executor.py       # Python/Bash code execution sandbox
    web_scraper.py         # Web page fetching and parsing
    search_tool.py         # Web search (DuckDuckGo, Google)
    database_tool.py       # SQLite database operations
  plugins/
    __init__.py
    loader.py              # Dynamic plugin discovery and loading
    git_plugin.py          # Git operations tool
    docker_plugin.py       # Docker management tool
    api_tester.py          # HTTP API testing tool
  ui/
    __init__.py
    terminal.py            # Rich terminal interface
    themes.py              # 8 color themes
    components.py          # Spinners, progress bars, menus
    markdown_renderer.py   # Enhanced markdown rendering
  utils/
    __init__.py
    ast_analyzer.py        # Python AST code analysis
    cache.py               # LRU, TTL, and disk caching
    crypto.py              # Encryption and secure storage
    diff_engine.py         # Text diff computation and patching
    file_watcher.py        # File system change monitoring
    logger.py              # Rich colored logging
    metrics.py             # Performance metrics collection
    process_manager.py     # Background process management
    rate_limiter.py        # Token bucket and sliding window limiters
    retry.py               # Exponential backoff with jitter
    templating.py          # Prompt template engine
    token_counter.py       # LLM token counting
    validators.py          # Chainable input validation
tests/
  __init__.py
  test_cache.py
  test_config.py
  test_memory.py
  test_registry.py
  test_session.py
  test_tools.py
  test_validators.py
```

## Quick Start

```bash
# Install
pip install -e .

# Set your API key
export OPENAI_API_KEY="your-key-here"
# or
export ANTHROPIC_API_KEY="your-key-here"

# Start interactive chat
aforit chat

# Run a single task
aforit run "list all Python files in the current directory"

# Use a specific model
aforit chat --model claude-sonnet-4-20250514

# Load plugins
aforit chat --plugins git --plugins docker

# Change theme
aforit chat --theme dracula
```

## Commands (in chat)

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/tools` | List available tools |
| `/model` | Show current model |
| `/memory` | Show memory status |
| `/history` | Show conversation history |
| `/clear` | Clear conversation |
| `/theme <name>` | Change color theme |
| `/export <file>` | Export session to JSON |
| `/quit` | Exit |

## Running Tests

```bash
pip install pytest pytest-asyncio
pytest tests/ -v
```

## License

MIT
