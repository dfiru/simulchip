"""Collection management commands."""

# Standard library imports
from pathlib import Path
from typing import Any, Optional

# Third-party imports
import typer
from rich.console import Console

# First-party imports
from simulchip.api.netrunnerdb import NetrunnerDBAPI
from simulchip.cli_utils import ensure_collection_directory, resolve_collection_path
from simulchip.collection.manager import CollectionManager

# Initialize console for rich output
console = Console()

# Create the collection command group
app = typer.Typer(help="Manage your card collection")

# Define option constants
COLLECTION_FILE_OPTION = typer.Option(
    None, "--file", "-f", help="Path to collection file"
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    collection_file: Optional[Path] = COLLECTION_FILE_OPTION,
) -> Any:
    """Manage your card collection with pack and card management."""
    if ctx.invoked_subcommand is None:
        # No subcommand was invoked, launch the unified TUI app
        try:
            console.print("[dim]Initializing collection manager...[/dim]")
            manager = get_collection_manager(collection_file)
            if manager.api is not None:
                console.print("[dim]Loading TUI app...[/dim]")
                from ..screens.collection_app import CollectionMainApp

                app = CollectionMainApp(manager, manager.api, collection_file)
                console.print("[dim]Starting app...[/dim]")
                result = app.run()

                # Handle the result
                if result == "quit":
                    console.print("[dim]Collection management closed[/dim]")
                elif result == "no_changes":
                    console.print("[dim]No changes made[/dim]")
                else:
                    console.print("[green]✓ Collection saved[/green]")
                    if result != "saved":
                        console.print(f"[yellow]Changes:[/yellow] {result}")
            else:
                console.print("[red]Error: API not available[/red]")
        except Exception as e:
            console.print(f"[red]Error launching TUI: {e}[/red]")
            # Standard library imports
            import traceback

            traceback.print_exc()


def get_collection_manager(collection_file: Optional[Path] = None) -> CollectionManager:
    """Get or create a collection manager instance."""
    collection_file = resolve_collection_path(collection_file)
    ensure_collection_directory(collection_file)

    api = NetrunnerDBAPI()
    return CollectionManager(collection_file=collection_file, api=api)
