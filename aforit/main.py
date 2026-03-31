"""Entry point for the Aforit terminal AI agent."""

import asyncio
import signal
import sys
from pathlib import Path

import click
from dotenv import load_dotenv

load_dotenv()


@click.group()
@click.version_option(version="1.0.0", prog_name="aforit")
def cli():
    """Aforit - Advanced Terminal AI Agent."""
    pass


@cli.command()
@click.option("--model", "-m", default="gpt-4", help="LLM model to use")
@click.option("--theme", "-t", default="monokai", help="Color theme")
@click.option("--memory/--no-memory", default=True, help="Enable long-term memory")
@click.option("--plugins", "-p", multiple=True, help="Plugins to load")
def chat(model: str, theme: str, memory: bool, plugins: tuple):
    """Start an interactive AI chat session."""
    from aforit.core.agent import Agent
    from aforit.core.config import Config
    from aforit.ui.terminal import TerminalUI

    config = Config(
        model_name=model,
        theme_name=theme,
        memory_enabled=memory,
        plugins=list(plugins),
    )
    agent = Agent(config)
    ui = TerminalUI(config)

    def handle_sigint(sig, frame):
        ui.print_goodbye()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sigint)
    asyncio.run(agent.run_interactive(ui))


@cli.command()
@click.argument("task")
@click.option("--model", "-m", default="gpt-4", help="LLM model to use")
@click.option("--output", "-o", default=None, help="Output file path")
def run(task: str, model: str, output: str):
    """Run a single task and exit."""
    from aforit.core.agent import Agent
    from aforit.core.config import Config

    config = Config(model_name=model)
    agent = Agent(config)
    result = asyncio.run(agent.run_single(task))

    if output:
        Path(output).write_text(result)
        click.echo(f"Output written to {output}")
    else:
        click.echo(result)


@cli.command()
@click.argument("pipeline_file")
def pipeline(pipeline_file: str):
    """Execute a processing pipeline from YAML config."""
    from aforit.core.config import Config
    from aforit.core.pipeline import PipelineExecutor

    config = Config()
    executor = PipelineExecutor(config)
    asyncio.run(executor.run_from_file(pipeline_file))


@cli.command()
def plugins():
    """List available plugins."""
    from aforit.plugins.loader import PluginLoader

    loader = PluginLoader()
    available = loader.discover_plugins()
    for name, info in available.items():
        click.echo(f"  {name}: {info['description']}")


@cli.command()
def config():
    """Show current configuration."""
    from aforit.core.config import Config

    cfg = Config()
    click.echo(cfg.to_yaml())


if __name__ == "__main__":
    cli()
