"""Collection management commands."""

# Standard library imports
import sys
import termios
import tty
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Third-party imports
import typer
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

# First-party imports
from simulchip.api.netrunnerdb import NetrunnerDBAPI, PackData
from simulchip.collection.manager import CollectionManager

# Initialize console for rich output
console = Console()

# Create the collection command group
app = typer.Typer(help="Manage your card collection")

# Default collection file location
DEFAULT_COLLECTION = Path.home() / ".simulchip" / "collection.toml"

# Default option for collection file to avoid B008 flake8 warnings
COLLECTION_FILE_OPTION = typer.Option(
    None, "--file", "-f", help="Path to collection file"
)


def get_collection_manager(collection_file: Optional[Path] = None) -> CollectionManager:
    """Get or create a collection manager instance."""
    if collection_file is None:
        collection_file = DEFAULT_COLLECTION

    # Ensure directory exists
    collection_file.parent.mkdir(parents=True, exist_ok=True)

    api = NetrunnerDBAPI()
    return CollectionManager(collection_file=collection_file, api=api)


def _getch() -> str:
    """Get a single character from stdin without pressing enter."""
    if sys.platform == "win32":
        # Standard library imports
        import msvcrt

        return msvcrt.getch().decode("utf-8")
    else:
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            char = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return char


def _create_interactive_pack_table(
    packs: List[PackData],
    selected_idx: int,
    selected_packs: Set[str],
    filter_text: str,
    owned_packs: Set[str],
    viewport_size: int = 15,
) -> Tuple[Table, List[PackData], int, int]:
    """Create an interactive table showing packs with scrollable viewport."""
    # Filter packs based on filter text
    if filter_text:
        filtered_packs = []
        for pack in packs:
            if (
                filter_text.lower() in pack["name"].lower()
                or filter_text.lower() in pack["code"].lower()
                or filter_text.lower() in pack.get("cycle", "").lower()
            ):
                filtered_packs.append(pack)
    else:
        filtered_packs = packs

    # Calculate viewport window
    total_items = len(filtered_packs)
    if total_items == 0:
        return Table(), filtered_packs, 0, 0

    # Calculate viewport start position
    viewport_start = max(0, selected_idx - viewport_size // 2)
    viewport_end = min(total_items, viewport_start + viewport_size)

    # Adjust if we're near the end
    if viewport_end - viewport_start < viewport_size and total_items > viewport_size:
        viewport_start = max(0, viewport_end - viewport_size)

    table = Table(title="Pack Selection", show_header=True, header_style="bold cyan")
    table.add_column("", style="green", width=3, justify="center")
    table.add_column("Code", style="yellow", width=12)
    table.add_column("Pack Name", style="white")
    table.add_column("Cycle", style="cyan", width=20)
    table.add_column("Release Date", style="dim", width=12)

    # Only show packs in the current viewport
    for i in range(viewport_start, viewport_end):
        pack = filtered_packs[i]
        code = pack["code"]
        name = pack["name"]
        cycle = pack.get("cycle", "") or "Unknown"
        date_release = pack.get("date_release", "") or "Unknown"

        # Selection indicator - simple owned/not-owned
        if code in owned_packs:
            mark = "●"  # In collection
            mark_style = "green"
        else:
            mark = "○"  # Not in collection
            mark_style = "dim"

        # Highlight current row
        if i == selected_idx:
            style = "reverse"
            code = f"► {code}"
        else:
            style = None

        table.add_row(
            Text(mark, style=mark_style), code, name, cycle, date_release, style=style
        )

    return table, filtered_packs, viewport_start, viewport_end


def _select_pack_simple(packs: List[Dict[str, str]]) -> Optional[str]:
    """Provide simple numbered pack selection for non-interactive environments."""
    # Display pack selection in a table
    table = Table(title="Available Packs", show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Code", style="yellow", width=12)
    table.add_column("Pack Name", style="white")
    table.add_column("Cycle", style="cyan", width=20)
    table.add_column("Release Date", style="dim", width=12)

    choices = []
    for i, pack in enumerate(packs, 1):
        code = pack["code"]
        name = pack["name"]
        cycle = pack.get("cycle", "") or "Unknown"
        date_release = pack.get("date_release", "") or "Unknown"

        table.add_row(str(i), code, name, cycle, date_release)
        choices.append(code)

    table.add_row("0", "---", "[red]Cancel[/red]", "---", "---")

    console.print()
    console.print(table)

    # Get selection
    while True:
        try:
            choice = Prompt.ask("\nSelect pack number (0 to cancel)", default="0")
            choice_num = int(choice)

            if choice_num == 0:
                return None
            elif 1 <= choice_num <= len(choices):
                return choices[choice_num - 1]
            else:
                console.print(
                    f"[red]Invalid choice. Please select 0-{len(choices)}[/red]"
                )
        except ValueError:
            console.print("[red]Invalid input. Please enter a number[/red]")


def _manage_collection_interactive(api: NetrunnerDBAPI) -> None:
    """Interactive collection management with keyboard navigation and multi-select."""
    try:
        packs = api.get_packs_by_release_date(newest_first=True)
        if not packs:
            console.print("[red]No packs available[/red]")
            return

        # Check if we're in an interactive terminal
        if not sys.stdin.isatty():
            console.print(
                "[yellow]Interactive collection management requires a terminal[/yellow]"
            )
            return

        # Get current collection to show owned packs
        manager = get_collection_manager()
        owned_packs = set(manager.get_owned_packs())

        selected_idx = 0
        filter_text = ""

        with Live(console=console, auto_refresh=False) as live:
            while True:
                # Create and display table with viewport
                (
                    table,
                    filtered_packs,
                    viewport_start,
                    viewport_end,
                ) = _create_interactive_pack_table(
                    packs, selected_idx, set(), filter_text, owned_packs
                )

                # Instructions
                instructions = Text()
                instructions.append("Controls: ", style="bold")
                instructions.append("↑/↓", style="cyan")
                instructions.append(" navigate, ", style="dim")
                instructions.append("Space", style="cyan")
                instructions.append(" toggle pack in/out of collection, ", style="dim")
                instructions.append("Type", style="cyan")
                instructions.append(" to filter\n", style="dim")
                instructions.append("PgUp/PgDn", style="cyan")
                instructions.append(" scroll, ", style="dim")
                instructions.append("g/G", style="cyan")
                instructions.append(" top/bottom, ", style="dim")
                instructions.append("q/Esc", style="cyan")
                instructions.append(" save & quit", style="dim")

                # Legend
                legend = Text()
                legend.append("Legend: ", style="bold")
                legend.append("○", style="dim")
                legend.append(" not in collection ", style="dim")
                legend.append("●", style="green")
                legend.append(" in collection ", style="dim")
                if len(owned_packs) > 0:
                    total_packs = len(
                        [p for p in packs if p.get("code") and p.get("name")]
                    )
                    owned_count = len(owned_packs)
                    legend.append(
                        f" | Collection: {owned_count}/{total_packs} packs",
                        style="cyan",
                    )

                # Status with filter display and scroll position
                status = Text()
                if filter_text:
                    status.append(f"Filter: '{filter_text}'", style="yellow")
                else:
                    status.append("Filter: (type to search)", style="dim")

                # Show scroll position
                if len(filtered_packs) > 0:
                    current_pos = selected_idx + 1
                    total = len(filtered_packs)
                    status.append(f" | {current_pos}/{total}", style="cyan")
                    if len(filtered_packs) > 15:  # Show viewport info if scrolling
                        status.append(
                            f" (showing {viewport_start + 1}-{viewport_end})",
                            style="dim",
                        )
                else:
                    status.append(" | 0/0", style="dim")

                # Combine everything
                display = Panel(
                    Group(table, Text(""), instructions, legend, status),
                    title="Collection Manager - Interactive",
                )

                live.update(display)
                live.refresh()

                # Handle input
                char = _getch()

                if char == "\x1b":  # Escape key sequence
                    try:
                        next_char = _getch()
                        if next_char == "[":
                            arrow_char = _getch()
                            if arrow_char == "A":  # Up arrow
                                if selected_idx > 0:
                                    selected_idx -= 1
                            elif arrow_char == "B":  # Down arrow
                                if selected_idx < len(filtered_packs) - 1:
                                    selected_idx += 1
                            elif arrow_char == "5":  # Page Up (ESC[5~)
                                try:
                                    _getch()  # Read the '~'
                                    selected_idx = max(0, selected_idx - 10)
                                except (OSError, KeyboardInterrupt):
                                    pass
                            elif arrow_char == "6":  # Page Down (ESC[6~)
                                try:
                                    _getch()  # Read the '~'
                                    selected_idx = min(
                                        len(filtered_packs) - 1, selected_idx + 10
                                    )
                                except (OSError, KeyboardInterrupt):
                                    pass
                        else:
                            # Just escape key - save and exit
                            manager.save_collection()
                            console.print("\n[green]✓ Collection saved[/green]")
                            return
                    except (OSError, KeyboardInterrupt):
                        return None
                elif char == "\r" or char == "\n":  # Enter key - do nothing
                    pass
                elif char == " ":  # Space key - toggle pack in/out of collection
                    if filtered_packs and 0 <= selected_idx < len(filtered_packs):
                        pack_code = filtered_packs[selected_idx]["code"]
                        try:
                            if pack_code in owned_packs:
                                # Remove from collection
                                manager.remove_pack(pack_code)
                                owned_packs.discard(pack_code)
                            else:
                                # Add to collection
                                manager.add_pack(pack_code)
                                owned_packs.add(pack_code)
                        except Exception:
                            # Show error briefly but don't crash
                            pass
                elif char == "j":  # Vim-style down
                    if selected_idx < len(filtered_packs) - 1:
                        selected_idx += 1
                elif char == "k":  # Vim-style up
                    if selected_idx > 0:
                        selected_idx -= 1
                elif char == "\x15":  # Ctrl+U - page up
                    selected_idx = max(0, selected_idx - 10)
                elif char == "\x04":  # Ctrl+D - page down
                    selected_idx = min(len(filtered_packs) - 1, selected_idx + 10)
                elif char == "g":  # Go to top
                    selected_idx = 0
                elif char == "G":  # Go to bottom
                    selected_idx = len(filtered_packs) - 1 if filtered_packs else 0
                elif char == "q":  # Quit - save and exit
                    manager.save_collection()
                    console.print("\n[green]✓ Collection saved[/green]")
                    return
                elif (
                    char == "\x7f" or char == "\b"
                ):  # Backspace - clear filter character
                    if filter_text:
                        filter_text = filter_text[:-1]
                        selected_idx = 0  # Reset selection when filter changes
                elif char.isprintable():  # Any printable character - add to filter
                    filter_text += char
                    selected_idx = 0  # Reset selection when filter changes

    except Exception as e:
        console.print(f"[red]Error in collection management: {e}[/red]")


@app.command()
def init(
    collection_file: Optional[Path] = COLLECTION_FILE_OPTION,
) -> Any:
    """Initialize a new collection file."""
    if collection_file is None:
        collection_file = DEFAULT_COLLECTION

    if collection_file.exists():
        console.print(
            f"[yellow]Collection already exists at {collection_file}[/yellow]"
        )
        if not typer.confirm("Overwrite existing collection?"):
            raise typer.Abort()

    manager = get_collection_manager(collection_file)
    manager.save_collection()
    console.print(f"[green]✓ Collection initialized at {collection_file}[/green]")


@app.command()
def manage(
    collection_file: Optional[Path] = COLLECTION_FILE_OPTION,
) -> Any:
    """Interactive collection management - add/remove packs with keyboard controls."""
    manager = get_collection_manager(collection_file)
    if manager.api is not None:
        # Type assertion since we know manager.api is NetrunnerDBAPI when not None
        _manage_collection_interactive(manager.api)  # type: ignore[arg-type]


@app.command()
def add_card(
    card_code: str,
    quantity: int = 1,
    collection_file: Optional[Path] = COLLECTION_FILE_OPTION,
) -> Any:
    """Add copies of a specific card to your collection."""
    manager = get_collection_manager(collection_file)

    try:
        manager.add_card(card_code, quantity)
        manager.save_collection()
        console.print(f"[green]✓ Added {quantity}x {card_code} to collection[/green]")
    except Exception as e:
        console.print(f"[red]✗ Error adding card: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def remove_card(
    card_code: str,
    quantity: int = 1,
    collection_file: Optional[Path] = COLLECTION_FILE_OPTION,
) -> Any:
    """Remove copies of a specific card from your collection."""
    manager = get_collection_manager(collection_file)

    manager.remove_card(card_code, quantity)
    manager.save_collection()
    console.print(f"[green]✓ Removed {quantity}x {card_code} from collection[/green]")


@app.command()
def mark_missing(
    card_code: str,
    quantity: int = 1,
    collection_file: Optional[Path] = COLLECTION_FILE_OPTION,
) -> Any:
    """Mark cards as missing (lost/damaged)."""
    manager = get_collection_manager(collection_file)

    manager.add_missing_card(card_code, quantity)
    manager.save_collection()
    console.print(f"[yellow]⚠ Marked {quantity}x {card_code} as missing[/yellow]")


@app.command()
def stats(
    collection_file: Optional[Path] = COLLECTION_FILE_OPTION,
) -> Any:
    """Show collection statistics."""
    manager = get_collection_manager(collection_file)

    all_cards = manager.get_all_cards()

    total_unique = len(all_cards)
    total_cards = sum(all_cards.values())
    total_missing = sum(manager.missing_cards.values())

    # Create stats table
    table = Table(title="Collection Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white", justify="right")

    table.add_row("Owned Packs", str(len(manager.owned_packs)))
    table.add_row("Unique Cards", str(total_unique))
    table.add_row("Total Cards", str(total_cards))
    table.add_row("Missing Cards", str(total_missing))

    console.print(table)

    if collection_file:
        console.print(f"\n[dim]Collection file: {collection_file}[/dim]")
