"""Collection management commands."""

# Standard library imports
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Third-party imports
import typer
from rich import box
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

# First-party imports
from simulchip.api.netrunnerdb import CardData, NetrunnerDBAPI, PackData
from simulchip.cli_utils import (
    calculate_collection_stats,
    calculate_selection_bounds,
    ensure_collection_directory,
    resolve_collection_path,
    should_ignore_pack_toggle_errors,
    should_reset_selection_on_filter_change,
    validate_pack_selection,
)
from simulchip.collection.manager import CollectionManager
from simulchip.collection.operations import get_reset_items, sort_cards_by_title
from simulchip.display import (
    calculate_viewport_size,
    calculate_viewport_window,
    format_viewport_status,
)
from simulchip.filters import filter_cards_raw, filter_packs_raw
from simulchip.models import CardModel, PackModel
from simulchip.platform import getch, is_interactive_terminal

# Local imports
from ..components.interactive_table import InteractiveTable, InteractiveTableConfig

# Initialize console for rich output
console = Console()


# Use models from library instead of defining here
PackItem = PackModel
CardItem = CardModel

# Create the collection command group
app = typer.Typer(help="Manage your card collection")


# Default option for collection file to avoid B008 flake8 warnings
COLLECTION_FILE_OPTION = typer.Option(
    None, "--file", "-f", help="Path to collection file"
)
FORCE_OPTION = typer.Option(False, "--force", help="Skip confirmation prompt")


def get_collection_manager(collection_file: Optional[Path] = None) -> CollectionManager:
    """Get or create a collection manager instance."""
    collection_file = resolve_collection_path(collection_file)
    ensure_collection_directory(collection_file)

    api = NetrunnerDBAPI()
    return CollectionManager(collection_file=collection_file, api=api)


def _create_interactive_pack_table(
    packs: List[PackData],
    selected_idx: int,
    selected_packs: Set[str],
    filter_text: str,
    owned_packs: Set[str],
    viewport_size: Optional[int] = None,
) -> Tuple[Table, List[PackData], int, int]:
    """Create an interactive table showing packs with scrollable viewport."""
    # Use dynamic viewport size if not provided
    if viewport_size is None:
        viewport_size = calculate_viewport_size(console, "pack")

    # Filter packs using library function
    filtered_packs = filter_packs_raw(packs, filter_text)  # type: ignore

    # Calculate viewport window
    total_items = len(filtered_packs)
    if total_items == 0:
        return Table(), filtered_packs, 0, 0  # type: ignore

    # Calculate viewport using library function
    viewport_window = calculate_viewport_window(
        selected_idx, total_items, viewport_size
    )
    viewport_start = viewport_window["start"]
    viewport_end = viewport_window["end"]

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

    return table, filtered_packs, viewport_start, viewport_end  # type: ignore


def _create_interactive_card_table(
    cards: List[CardData],
    selected_idx: int,
    filter_text: str,
    manager: CollectionManager,
    show_expected_only: bool = False,
    viewport_size: Optional[int] = None,
) -> Tuple[Table, List[CardData], int, int]:
    """Create an interactive table showing cards with scrollable viewport."""
    # Use dynamic viewport size if not provided
    if viewport_size is None:
        viewport_size = calculate_viewport_size(console, "card")

    # Filter cards using library function
    filtered_cards = filter_cards_raw(cards, filter_text, manager, show_expected_only)  # type: ignore

    # Handle empty results
    if not filtered_cards:
        table = Table(title="No cards match filter")
        return table, [], 0, 0

    # Calculate viewport window
    total_items = len(filtered_cards)
    viewport_window = calculate_viewport_window(
        selected_idx, total_items, viewport_size
    )
    viewport_start = viewport_window["start"]
    viewport_end = viewport_window["end"]

    # Create table with mode indicator
    mode_text = "Expected Cards Only" if show_expected_only else "All Cards"
    table = Table(
        title=f"Card Management - {mode_text} (Showing {viewport_end - viewport_start} of {total_items} cards)",
        show_header=True,
        header_style="bold cyan",
        box=box.ROUNDED,
    )
    table.add_column("Expected", style="dim", width=8, justify="center")
    table.add_column("Diff", style="white", width=6, justify="center")
    table.add_column("Card", style="yellow", width=50)
    table.add_column("Type", style="cyan", width=12)
    table.add_column("Faction", style="magenta", width=10)
    table.add_column("Pack", style="dim", width=12)

    # Add rows for the current viewport
    for i in range(viewport_start, viewport_end):
        card = filtered_cards[i]
        code = card["code"]
        title = card.get("title", "Unknown")
        type_code = card.get("type_code", "")
        faction = card.get("faction_code", "")
        pack_code = card.get("pack_code", "")

        # Get expected quantity and difference using new format
        expected = manager.get_expected_card_count(code)
        diff = manager.get_card_difference(code)

        # Format expected
        expected_str = str(expected) if expected > 0 else "-"

        # Format difference with color
        if diff > 0:
            diff_str = f"+{diff}"
            diff_style = "green"
        elif diff < 0:
            diff_str = str(diff)
            diff_style = "red"
        else:
            diff_str = "-"
            diff_style = "dim"

        # Highlight current row
        if i == selected_idx:
            style = "reverse"
            title = f"► {title}"
        else:
            style = None

        # Create row with styled diff value
        row = [
            expected_str,
            Text(diff_str, style=diff_style),
            title,
            type_code,
            faction,
            pack_code,
        ]
        table.add_row(
            *[str(cell) if not isinstance(cell, Text) else cell for cell in row],
            style=style,
        )

    return table, filtered_cards, viewport_start, viewport_end  # type: ignore


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
        choice = Prompt.ask("\nSelect pack number (0 to cancel)", default="0")
        is_valid, choice_idx = validate_pack_selection(choice, len(choices))

        if is_valid:
            if choice_idx is None:
                return None  # Cancel
            else:
                return choices[choice_idx]
        else:
            console.print(f"[red]Invalid choice. Please select 0-{len(choices)}[/red]")


def _manage_collection_interactive(api: NetrunnerDBAPI) -> None:
    """Interactive collection management with keyboard navigation and multi-select."""
    try:
        packs = api.get_packs_by_release_date(newest_first=True)
        if not packs:
            console.print("[red]No packs available[/red]")
            return

        # Check if we're in an interactive terminal
        if not is_interactive_terminal():
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
                    stats = calculate_collection_stats(owned_packs, packs)  # type: ignore
                    legend.append(
                        f" | Collection: {stats['owned_count']}/{stats['total_count']} packs",
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
                    viewport_status = format_viewport_status(
                        selected_idx,
                        len(filtered_packs),
                        viewport_start,
                        viewport_end,
                        calculate_viewport_size(console, "pack"),
                    )
                    status.append(f" | {viewport_status}", style="cyan")
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
                char = getch()

                if char == "\x1b":  # Escape key sequence
                    try:
                        next_char = getch()
                        if next_char == "[":
                            arrow_char = getch()
                            if arrow_char == "A":  # Up arrow
                                selected_idx = calculate_selection_bounds(
                                    selected_idx, len(filtered_packs), "up"
                                )
                            elif arrow_char == "B":  # Down arrow
                                selected_idx = calculate_selection_bounds(
                                    selected_idx, len(filtered_packs), "down"
                                )
                            elif arrow_char == "5":  # Page Up (ESC[5~)
                                try:
                                    getch()  # Read the '~'
                                    selected_idx = calculate_selection_bounds(
                                        selected_idx, len(filtered_packs), "page_up"
                                    )
                                except (OSError, KeyboardInterrupt):
                                    pass
                            elif arrow_char == "6":  # Page Down (ESC[6~)
                                try:
                                    getch()  # Read the '~'
                                    selected_idx = calculate_selection_bounds(
                                        selected_idx, len(filtered_packs), "page_down"
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
                            # Show error briefly but don't crash (business rule)
                            if not should_ignore_pack_toggle_errors():
                                raise
                elif char == "j":  # Vim-style down
                    selected_idx = calculate_selection_bounds(
                        selected_idx, len(filtered_packs), "down"
                    )
                elif char == "k":  # Vim-style up
                    selected_idx = calculate_selection_bounds(
                        selected_idx, len(filtered_packs), "up"
                    )
                elif char == "\x15":  # Ctrl+U - page up
                    selected_idx = calculate_selection_bounds(
                        selected_idx, len(filtered_packs), "page_up"
                    )
                elif char == "\x04":  # Ctrl+D - page down
                    selected_idx = calculate_selection_bounds(
                        selected_idx, len(filtered_packs), "page_down"
                    )
                elif char == "g":  # Go to top
                    selected_idx = calculate_selection_bounds(
                        selected_idx, len(filtered_packs), "top"
                    )
                elif char == "G":  # Go to bottom
                    selected_idx = calculate_selection_bounds(
                        selected_idx, len(filtered_packs), "bottom"
                    )
                elif char == "q":  # Quit - save and exit
                    manager.save_collection()
                    console.print("\n[green]✓ Collection saved[/green]")
                    return
                elif (
                    char == "\x7f" or char == "\b"
                ):  # Backspace - clear filter character
                    if filter_text:
                        filter_text = filter_text[:-1]
                        if should_reset_selection_on_filter_change():
                            selected_idx = 0
                elif char.isprintable():  # Any printable character - add to filter
                    filter_text += char
                    if should_reset_selection_on_filter_change():
                        selected_idx = 0

    except Exception as e:
        console.print(f"[red]Error in collection management: {e}[/red]")


def _manage_collection_interactive_new(api: NetrunnerDBAPI) -> None:
    """Interactive collection management using reusable table component."""
    try:
        packs_data = api.get_packs_by_release_date(newest_first=True)
        if not packs_data:
            console.print("[red]No packs available[/red]")
            return

        # Get current collection to show owned packs
        manager = get_collection_manager()
        owned_packs = set(manager.get_owned_packs())

        # Convert to PackItem wrappers
        pack_items = [PackItem(pack) for pack in packs_data]  # type: ignore

        # Configure table
        config = InteractiveTableConfig(
            title="Pack Management",
            columns=[
                ("", "green", 2, "center"),  # ownership indicator
                ("Code", "yellow", 12, "left"),
                ("Pack Name", "white", 40, "left"),
                ("Cycle", "cyan", 20, "left"),
                ("Release Date", "dim", 12, "left"),
            ],
            instructions=[
                ("Space", "toggle pack in/out of collection"),
                ("PgUp/PgDn", "scroll"),
                ("g/G", "top/bottom"),
            ],
        )

        def render_pack_row(pack_item: PackItem, is_selected: bool) -> List[str]:
            pack = pack_item.data
            code = pack["code"]
            name = pack.get("name", "Unknown")
            cycle = pack.get("cycle", "") or "Unknown"
            date_release = pack.get("date_release", "") or "Unknown"

            # Ownership indicator
            if code in owned_packs:
                mark = "●"
            else:
                mark = "○"

            # Add selection indicator
            if is_selected:
                code = f"► {code}"

            return [mark, code, name, cycle, date_release]

        def handle_action(action: str, item: PackItem, index: int) -> bool:
            if action == "space" and item:
                pack_code = item.get_id()
                try:
                    if pack_code in owned_packs:
                        manager.remove_pack(pack_code)
                        owned_packs.discard(pack_code)
                    else:
                        manager.add_pack(pack_code)
                        owned_packs.add(pack_code)
                except Exception:
                    pass
                return True
            elif action == "quit":
                manager.save_collection()
                console.print("\n[green]✓ Collection saved[/green]")
                return False
            return True

        # Create and run interactive table
        table = InteractiveTable(
            console, config, pack_items, render_pack_row, handle_action
        )
        table.run()

    except Exception as e:
        console.print(f"[red]Error in collection management: {e}[/red]")


def _manage_cards_interactive(
    api: NetrunnerDBAPI, collection_file: Optional[Path] = None
) -> None:
    """Interactive card management with keyboard navigation."""
    try:
        # Get all cards
        console.print("[dim]Loading cards from API...[/dim]")
        all_cards_dict = api.get_all_cards()
        if not all_cards_dict:
            console.print("[red]No cards available[/red]")
            return

        console.print(f"[dim]Loaded {len(all_cards_dict)} cards, sorting...[/dim]")
        # Convert to list and sort by title using library function
        cards = sort_cards_by_title(all_cards_dict)
        console.print("[dim]Cards sorted, starting interface...[/dim]")

        # Check if we're in an interactive terminal
        if not is_interactive_terminal():
            console.print(
                "[yellow]Interactive card management requires a terminal[/yellow]"
            )
            return

        # Get current collection data
        manager = get_collection_manager(collection_file)

        selected_idx = 0
        filter_text = ""
        show_expected_only = False

        with Live(console=console, auto_refresh=False) as live:
            while True:
                # Create and display table with viewport
                (
                    table,
                    filtered_cards,
                    viewport_start,
                    viewport_end,
                ) = _create_interactive_card_table(
                    cards, selected_idx, filter_text, manager, show_expected_only  # type: ignore
                )

                # Instructions
                instructions = Text()
                instructions.append("Controls: ", style="bold")
                instructions.append("↑/↓", style="cyan")
                instructions.append(" navigate, ", style="dim")
                instructions.append("←/→", style="cyan")
                instructions.append(" decrease/increase difference, ", style="dim")
                instructions.append("0", style="cyan")
                instructions.append(" reset to expected\n", style="dim")
                instructions.append("Type", style="cyan")
                instructions.append(" to filter, ", style="dim")
                instructions.append("e", style="cyan")
                instructions.append(" toggle expected only, ", style="dim")
                instructions.append("Delete", style="cyan")
                instructions.append(" reset difference\n", style="dim")
                instructions.append("q/Esc", style="cyan")
                instructions.append(" save & quit", style="dim")

                # Status info (filter and mode)
                status_parts = []
                if filter_text:
                    status_parts.append(f"Filter: {filter_text}")

                mode_text = "Expected only" if show_expected_only else "All cards"
                status_parts.append(f"Mode: {mode_text}")

                status_info = Panel(
                    " | ".join(status_parts),
                    style="yellow" if filter_text else "cyan",
                    expand=False,
                )
                live.update(Group(table, instructions, status_info))

                live.refresh()

                # Get user input
                char = getch()

                # Handle input
                if char == "\x1b":  # ESC
                    next_char = getch()
                    if next_char == "[":  # Arrow keys
                        arrow_char = getch()
                        if arrow_char == "A":  # Up arrow
                            if selected_idx > 0:
                                selected_idx -= 1
                        elif arrow_char == "B":  # Down arrow
                            if (
                                filtered_cards
                                and selected_idx < len(filtered_cards) - 1
                            ):
                                selected_idx += 1
                        elif arrow_char == "C":  # Right arrow - increase difference
                            if filtered_cards and 0 <= selected_idx < len(
                                filtered_cards
                            ):
                                card_code = filtered_cards[selected_idx]["code"]
                                manager.modify_card_difference(card_code, 1)
                        elif arrow_char == "D":  # Left arrow - decrease difference
                            if filtered_cards and 0 <= selected_idx < len(
                                filtered_cards
                            ):
                                card_code = filtered_cards[selected_idx]["code"]
                                manager.modify_card_difference(card_code, -1)
                        elif arrow_char == "5":  # Page Up
                            selected_idx = max(0, selected_idx - 10)
                        elif arrow_char == "6":  # Page Down
                            if filtered_cards:
                                selected_idx = min(
                                    len(filtered_cards) - 1, selected_idx + 10
                                )
                    else:
                        # Plain ESC - quit
                        manager.save_collection()
                        console.print("\n[green]✓ Collection saved[/green]")
                        return
                elif char == "\x03" or char == "q":  # Ctrl+C or q - quit
                    manager.save_collection()
                    console.print("\n[green]✓ Collection saved[/green]")
                    return
                elif char == "\r" or char == "\n":  # Enter - toggle details (optional)
                    pass  # Could show card details in future
                elif char == "\x7f" or char == "\b":  # Backspace
                    if filter_text:
                        filter_text = filter_text[:-1]
                        selected_idx = 0
                elif (
                    char == "\x7f" and not filter_text
                ):  # Delete with no filter - reset card difference
                    if filtered_cards and 0 <= selected_idx < len(filtered_cards):
                        card_code = filtered_cards[selected_idx]["code"]
                        manager.set_card_difference(card_code, 0)
                elif char == "0":  # Zero key - reset to expected
                    if filtered_cards and 0 <= selected_idx < len(filtered_cards):
                        card_code = filtered_cards[selected_idx]["code"]
                        manager.set_card_difference(card_code, 0)
                elif (
                    char.isdigit() and char != "0"
                ):  # Number keys 1-9 - set positive difference
                    if filtered_cards and 0 <= selected_idx < len(filtered_cards):
                        card_code = filtered_cards[selected_idx]["code"]
                        difference = int(char)
                        manager.set_card_difference(card_code, difference)
                elif char == "e" or char == "E":  # Toggle expected only mode
                    show_expected_only = not show_expected_only
                    selected_idx = 0  # Reset selection when mode changes
                elif (
                    char.isprintable()
                ):  # Any other printable character - add to filter
                    filter_text += char
                    selected_idx = 0  # Reset selection when filter changes

    except Exception as e:
        console.print(f"[red]Error in card management: {e}[/red]")


@app.command()
def init(
    collection_file: Optional[Path] = COLLECTION_FILE_OPTION,
) -> Any:
    """Initialize a new collection file."""
    collection_file = resolve_collection_path(collection_file)

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
def packs(
    collection_file: Optional[Path] = COLLECTION_FILE_OPTION,
) -> Any:
    """Interactive pack management - add/remove packs from your collection."""
    manager = get_collection_manager(collection_file)
    if manager.api is not None:
        # Type assertion since we know manager.api is NetrunnerDBAPI when not None
        _manage_collection_interactive_new(manager.api)  # type: ignore[arg-type]


@app.command()
def cards(
    collection_file: Optional[Path] = COLLECTION_FILE_OPTION,
) -> Any:
    """Interactive card management - manage quantities owned and missing."""
    manager = get_collection_manager(collection_file)
    if manager.api is not None:
        _manage_cards_interactive(manager.api, collection_file)  # type: ignore[arg-type]


@app.command()
def reset(
    collection_file: Optional[Path] = COLLECTION_FILE_OPTION,
    force: bool = FORCE_OPTION,
) -> Any:
    """Reset and re-initialize card library files and collection."""
    # First-party imports
    from simulchip.paths import reset_simulchip_data

    collection_file = resolve_collection_path(collection_file)

    # Check what will be reset using library function
    items_to_reset = get_reset_items(collection_file)

    if not items_to_reset:
        console.print("[yellow]No files found to reset[/yellow]")
        return

    # Show what will be reset
    console.print("[yellow]The following will be reset:[/yellow]")
    for item in items_to_reset:
        console.print(f"  • {item}")

    # Confirmation prompt unless forced
    if not force:
        console.print()
        if not typer.confirm("Are you sure you want to reset these files?"):
            console.print("[dim]Reset cancelled[/dim]")
            return

    # Perform reset using library function
    result = reset_simulchip_data(collection_path=collection_file)

    # Show results
    for item in result["removed"]:
        console.print(f"[green]✓[/green] {item}")

    for error in result["errors"]:
        console.print(f"[red]✗[/red] {error}")

    # Re-initialize collection if anything was removed
    if result["removed"]:
        try:
            console.print("[dim]Re-initializing collection...[/dim]")
            manager = get_collection_manager(collection_file)
            manager.save_collection()
            console.print(
                f"[green]✓[/green] Re-initialized collection at {collection_file}"
            )
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to re-initialize collection: {e}")

    console.print(
        f"\n[green]Reset complete. {len(result['removed'])} items processed.[/green]"
    )


@app.command()
def stats(
    collection_file: Optional[Path] = COLLECTION_FILE_OPTION,
) -> Any:
    """Show collection statistics."""
    manager = get_collection_manager(collection_file)
    stats = manager.get_statistics()

    # Create stats table
    table = Table(title="Collection Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white", justify="right")

    table.add_row("Owned Packs", str(stats["owned_packs"]))
    table.add_row("Unique Cards", str(stats["unique_cards"]))
    table.add_row("Total Cards", str(stats["total_cards"]))
    table.add_row("Missing Cards", str(stats["missing_cards"]))

    console.print(table)

    if collection_file:
        console.print(f"\n[dim]Collection file: {collection_file}[/dim]")
