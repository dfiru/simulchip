"""Simulchip CLI - Manage your Netrunner collection and generate proxy sheets."""

# Standard library imports
from typing import Any

# Third-party imports
import typer
from rich.console import Console

# First-party imports
from simulchip import __version__

from .commands import collection, proxy

# Initialize Rich console for pretty output
console = Console()

# Default option for verbose flag to avoid B008 flake8 warnings
VERBOSE_OPTION = typer.Option(False, "--verbose", "-v", help="Enable verbose output")

# Create the main Typer app
app = typer.Typer(
    name="simulchip",
    help="Manage your Netrunner collection and generate proxy sheets.",
    add_completion=True,
    rich_markup_mode="rich",
)

# Add command groups
app.add_typer(collection.app, name="collect", help="Manage your card collection")

# Add proxy as a direct command
app.command(name="proxy", help="Generate proxy sheets for decklists")(proxy.proxy)


@app.command()
def version() -> Any:
    """Show the simulchip version."""
    console.print(f"simulchip version {__version__}")


@app.callback()
def main(
    ctx: typer.Context,
    verbose: bool = VERBOSE_OPTION,
) -> Any:
    """
    Simulchip CLI - Manage your Netrunner collection and generate proxy sheets.

    Use 'simulchip COMMAND --help' for more information on a command.
    """
    # Store verbose flag in context for use by subcommands
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


if __name__ == "__main__":
    app()
