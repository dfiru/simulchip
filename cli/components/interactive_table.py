"""Interactive table component for CLI interfaces."""

# Standard library imports
from typing import Any, Callable, List, Literal, Optional, Protocol, Tuple

# Third-party imports
from rich import box
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# First-party imports
from simulchip.display import calculate_viewport_size
from simulchip.platform import getch, is_interactive_terminal


class InteractiveTableRow(Protocol):
    """Protocol for items that can be displayed in interactive tables."""

    def get_id(self) -> str:
        """Get unique identifier for this item."""
        ...

    def matches_filter(self, filter_text: str) -> bool:
        """Check if this item matches the filter text."""
        ...


class InteractiveTableConfig:
    """Configuration for interactive table behavior.

    Args:
        title: Title displayed above the table
        columns: List of column specifications (name, style, width, justify)
        filter_placeholder: Placeholder text for filter input
        viewport_size: Optional fixed viewport size
        instructions: Optional list of (key, description) instruction pairs
    """

    def __init__(
        self,
        title: str,
        columns: List[
            Tuple[str, str, int, Literal["default", "left", "center", "right", "full"]]
        ],
        filter_placeholder: str = "Type to filter...",
        viewport_size: Optional[int] = None,
        instructions: Optional[List[Tuple[str, str]]] = None,  # key, description pairs
    ):
        """Initialize table configuration."""
        self.title = title
        self.columns = columns
        self.filter_placeholder = filter_placeholder
        self.viewport_size = viewport_size
        self.instructions = instructions or []


class InteractiveTable:
    """Reusable interactive table with filtering and navigation.

    Args:
        console: Rich console for output
        config: Table configuration
        items: List of items to display
        row_renderer: Function to render a single row
        on_action: Function to handle user actions
    """

    def __init__(
        self,
        console: Console,
        config: InteractiveTableConfig,
        items: List[Any],
        row_renderer: Callable[[Any, bool], List[str]],  # item, is_selected -> row data
        on_action: Optional[
            Callable[[str, Any, int], bool]
        ] = None,  # action, item, index -> continue?
    ):
        """Initialize interactive table."""
        self.console = console
        self.config = config
        self.items = items
        self.row_renderer = row_renderer
        self.on_action = (
            on_action if on_action is not None else (lambda a, i, idx: True)
        )

        self.selected_idx = 0
        self.filter_text = ""

    def _filter_items(self) -> List[Any]:
        """Filter items based on current filter text."""
        if not self.filter_text:
            return self.items

        filtered = []
        filter_lower = self.filter_text.lower()
        for item in self.items:
            if hasattr(item, "matches_filter"):
                if item.matches_filter(filter_lower):
                    filtered.append(item)
            else:
                # Fallback: check if filter text is in string representation
                if filter_lower in str(item).lower():
                    filtered.append(item)
        return filtered

    def _create_table(self, filtered_items: List[Any]) -> Tuple[Table, int, int]:
        """Create the table with current viewport."""
        if not filtered_items:
            table = Table(title="No items match filter")
            return table, 0, 0

        # Calculate viewport with dynamic sizing
        total_items = len(filtered_items)
        viewport_size = self.config.viewport_size or calculate_viewport_size(
            self.console, "default"
        )
        viewport_start = max(0, self.selected_idx - viewport_size // 2)
        viewport_end = min(total_items, viewport_start + viewport_size)

        # Adjust viewport if at the end
        if viewport_end == total_items:
            viewport_start = max(0, total_items - viewport_size)

        # Create table
        table = Table(
            title=f"{self.config.title} (Showing {viewport_end - viewport_start} of {total_items} items)",
            show_header=True,
            header_style="bold cyan",
            box=box.ROUNDED,
        )

        # Add columns
        for name, style, width, justify in self.config.columns:
            table.add_column(name, style=style, width=width, justify=justify)

        # Add rows for current viewport
        for i in range(viewport_start, viewport_end):
            item = filtered_items[i]
            is_selected = i == self.selected_idx
            row_data = self.row_renderer(item, is_selected)

            row_style: Optional[str] = "reverse" if is_selected else None
            table.add_row(*row_data, style=row_style)

        return table, viewport_start, viewport_end

    def _create_instructions(self) -> Text:
        """Create instruction text."""
        instructions = Text()
        instructions.append("Controls: ", style="bold")

        # Default navigation instructions
        instructions.append("↑/↓", style="cyan")
        instructions.append(" navigate, ", style="dim")

        # Custom instructions
        for key, description in self.config.instructions:
            instructions.append(key, style="cyan")
            instructions.append(f" {description}, ", style="dim")

        # Default filter/quit instructions
        instructions.append("Type", style="cyan")
        instructions.append(" to filter, ", style="dim")
        instructions.append("q/Esc", style="cyan")
        instructions.append(" quit", style="dim")

        return instructions

    def run(self) -> None:
        """Run the interactive table interface."""
        # Check if we're in an interactive terminal
        if not is_interactive_terminal():
            self.console.print(
                "[yellow]Interactive interface requires a terminal[/yellow]"
            )
            return

        with Live(console=self.console, auto_refresh=False) as live:
            while True:
                # Filter items
                filtered_items = self._filter_items()

                # Ensure selected_idx is valid
                if filtered_items:
                    self.selected_idx = min(self.selected_idx, len(filtered_items) - 1)
                else:
                    self.selected_idx = 0

                # Create table and instructions
                table, viewport_start, viewport_end = self._create_table(filtered_items)
                instructions = self._create_instructions()

                # Create display
                if self.filter_text:
                    filter_info = Panel(
                        f"Filter: {self.filter_text}",
                        style="yellow",
                        expand=False,
                    )
                    live.update(Group(table, instructions, filter_info))
                else:
                    live.update(Group(table, instructions))

                live.refresh()

                # Get user input
                char = getch()

                # Handle navigation
                if char == "\x1b":  # ESC key
                    next_char = getch()
                    if next_char == "[":  # Arrow keys
                        arrow_char = getch()
                        if arrow_char == "A":  # Up arrow
                            if self.selected_idx > 0:
                                self.selected_idx -= 1
                        elif arrow_char == "B":  # Down arrow
                            if (
                                filtered_items
                                and self.selected_idx < len(filtered_items) - 1
                            ):
                                self.selected_idx += 1
                        elif arrow_char == "5":  # Page Up
                            self.selected_idx = max(0, self.selected_idx - 10)
                        elif arrow_char == "6":  # Page Down
                            if filtered_items:
                                self.selected_idx = min(
                                    len(filtered_items) - 1, self.selected_idx + 10
                                )
                        else:
                            # Pass other arrow keys to action handler
                            if filtered_items and 0 <= self.selected_idx < len(
                                filtered_items
                            ):
                                current_item = filtered_items[self.selected_idx]
                                if not self.on_action(
                                    f"arrow_{arrow_char}",
                                    current_item,
                                    self.selected_idx,
                                ):
                                    return
                    else:
                        # Plain ESC - quit
                        if not self.on_action("quit", None, -1):
                            return
                elif char == "\x03" or char == "q":  # Ctrl+C or q - quit
                    if not self.on_action("quit", None, -1):
                        return
                elif char in ["\r", "\n"]:  # Enter
                    if filtered_items and 0 <= self.selected_idx < len(filtered_items):
                        current_item = filtered_items[self.selected_idx]
                        if not self.on_action("enter", current_item, self.selected_idx):
                            return
                elif char == " ":  # Space
                    if filtered_items and 0 <= self.selected_idx < len(filtered_items):
                        current_item = filtered_items[self.selected_idx]
                        if not self.on_action("space", current_item, self.selected_idx):
                            return
                elif char == "g":  # Go to top
                    self.selected_idx = 0
                elif char == "G":  # Go to bottom
                    if filtered_items:
                        self.selected_idx = len(filtered_items) - 1
                elif char in ["\x7f", "\b"]:  # Backspace
                    if self.filter_text:
                        self.filter_text = self.filter_text[:-1]
                        self.selected_idx = 0
                    else:
                        # Pass backspace/delete to action handler
                        if filtered_items and 0 <= self.selected_idx < len(
                            filtered_items
                        ):
                            current_item = filtered_items[self.selected_idx]
                            if not self.on_action(
                                "delete", current_item, self.selected_idx
                            ):
                                return
                elif char.isprintable():  # Printable character - add to filter
                    self.filter_text += char
                    self.selected_idx = 0
                else:
                    # Pass other characters to action handler
                    if filtered_items and 0 <= self.selected_idx < len(filtered_items):
                        current_item = filtered_items[self.selected_idx]
                        if not self.on_action(
                            f"char_{char}", current_item, self.selected_idx
                        ):
                            return
