"""Display utilities for terminal interfaces.

This module provides utilities for calculating display dimensions
and managing terminal interface layouts.
"""

# Standard library imports
from typing import Dict

# Third-party imports
from rich.console import Console


def calculate_viewport_size(console: Console, interface_type: str = "default") -> int:
    """Calculate optimal viewport size based on terminal height and interface type.

    Args:
        console: Rich console instance
        interface_type: Type of interface ("pack", "card", or "default")

    Returns:
        Number of table rows that can fit in the terminal
    """
    terminal_height = int(console.size.height)

    # Reserve space based on interface type
    if interface_type == "pack":
        # Pack interface:
        # - Table title (2 lines including padding)
        # - Table header (1 line)
        # - Instructions (2 lines)
        # - Legend (1 line)
        # - Status (1 line)
        # - Padding (2 lines)
        reserved_lines = 9
    elif interface_type == "card":
        # Card interface:
        # - Table title (2 lines including padding)
        # - Table header (1 line)
        # - Instructions (3 lines)
        # - Status panel with borders (3 lines)
        # - Padding (2 lines)
        reserved_lines = 11
    else:
        # Default/generic interface
        reserved_lines = 10

    # Calculate available space for table rows
    available_height = max(5, terminal_height - reserved_lines)  # Minimum 5 rows
    return available_height


def calculate_viewport_window(
    selected_idx: int, total_items: int, viewport_size: int
) -> Dict[str, int]:
    """Calculate viewport window start and end positions.

    Args:
        selected_idx: Currently selected item index
        total_items: Total number of items
        viewport_size: Size of the viewport

    Returns:
        Dictionary with 'start' and 'end' keys for viewport window
    """
    if total_items == 0:
        return {"start": 0, "end": 0}

    # Calculate viewport start position
    viewport_start = max(0, selected_idx - viewport_size // 2)
    viewport_end = min(total_items, viewport_start + viewport_size)

    # Adjust if we're near the end
    if viewport_end - viewport_start < viewport_size and total_items > viewport_size:
        viewport_start = max(0, viewport_end - viewport_size)

    return {"start": viewport_start, "end": viewport_end}


def format_viewport_status(
    selected_idx: int,
    total_items: int,
    viewport_start: int,
    viewport_end: int,
    viewport_size: int,
) -> str:
    """Format viewport status text for display.

    Args:
        selected_idx: Currently selected item index
        total_items: Total number of items
        viewport_start: Start of viewport window
        viewport_end: End of viewport window
        viewport_size: Size of the viewport

    Returns:
        Formatted status string
    """
    if total_items == 0:
        return "0/0"

    current_pos = selected_idx + 1
    status = f"{current_pos}/{total_items}"

    # Show viewport info if there are more items than can be displayed
    if total_items > viewport_size:
        status += f" (showing {viewport_start + 1}-{viewport_end})"

    return status


def get_completion_color(completion_percentage: float) -> str:
    """Get color for completion percentage display.

    Args:
        completion_percentage: Completion percentage (0-100)

    Returns:
        Color string for rich console display
    """
    if completion_percentage == 100:
        return "green"
    elif completion_percentage >= 80:
        return "yellow"
    else:
        return "red"
