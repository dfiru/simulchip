"""CLI utilities and business logic.

This module contains business logic that was in the CLI but should be
in the library for better separation of concerns.
"""

# Standard library imports
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .paths import DEFAULT_COLLECTION_PATH

# Business constants
DEFAULT_PAGE_SIZE = 10
DEFAULT_VIEWPORT_PADDING = {"pack": 9, "card": 11, "default": 10}


def resolve_collection_path(collection_file: Optional[Path]) -> Path:
    """Resolve collection file path with default fallback.

    Args:
        collection_file: Optional collection file path

    Returns:
        Resolved collection file path
    """
    return collection_file if collection_file is not None else DEFAULT_COLLECTION_PATH


def ensure_collection_directory(collection_file: Path) -> None:
    """Ensure collection file directory exists.

    Args:
        collection_file: Path to collection file
    """
    collection_file.parent.mkdir(parents=True, exist_ok=True)


def ensure_output_directory(output_path: Path) -> None:
    """Ensure output directory exists.

    Args:
        output_path: Path to output file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)


def validate_collection_exists(collection_file: Path) -> bool:
    """Check if collection file exists.

    Args:
        collection_file: Path to collection file

    Returns:
        True if collection file exists and is a file (not a directory)
    """
    return collection_file.exists() and collection_file.is_file()


def should_generate_proxies(proxy_cards: List[Any]) -> bool:
    """Determine if proxy generation should proceed.

    Args:
        proxy_cards: List of cards to generate proxies for

    Returns:
        True if proxy generation should proceed
    """
    return len(proxy_cards) > 0


def get_proxy_generation_message(proxy_cards: List[Any], all_cards: bool) -> str:
    """Get appropriate message for proxy generation.

    Args:
        proxy_cards: List of cards to generate proxies for
        all_cards: Whether generating all cards or just missing

    Returns:
        Formatted message string
    """
    count = len(proxy_cards)
    if all_cards:
        return f"Generating proxies for all {count} cards"
    else:
        return f"Generating proxies for {count} missing cards"


def filter_valid_packs(packs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter packs to only include valid ones (have code and name).

    Args:
        packs: List of pack data dictionaries

    Returns:
        List of valid pack data dictionaries
    """
    return [p for p in packs if p.get("code") and p.get("name")]


def calculate_collection_stats(
    owned_packs: set, all_packs: List[Dict[str, Any]]
) -> Dict[str, int]:
    """Calculate collection statistics.

    Args:
        owned_packs: Set of owned pack codes
        all_packs: List of all pack data

    Returns:
        Dictionary with collection statistics
    """
    valid_packs = filter_valid_packs(all_packs)
    return {"owned_count": len(owned_packs), "total_count": len(valid_packs)}


def validate_pack_selection(
    choice_str: str, max_choices: int
) -> Tuple[bool, Optional[int]]:
    """Validate pack selection input.

    Args:
        choice_str: User input string
        max_choices: Maximum valid choice number

    Returns:
        Tuple of (is_valid, choice_number or None)
    """
    try:
        choice_num = int(choice_str)
        if choice_num == 0:
            return True, None  # Cancel
        elif 1 <= choice_num <= max_choices:
            return True, choice_num - 1  # Convert to 0-based index
        else:
            return False, None
    except ValueError:
        return False, None


def get_navigation_page_size() -> int:
    """Get page size for navigation operations.

    Returns:
        Page size for pagination
    """
    return DEFAULT_PAGE_SIZE


def calculate_selection_bounds(
    current_idx: int, total_items: int, operation: str = "none"
) -> int:
    """Calculate new selection index within bounds.

    Args:
        current_idx: Current selection index
        total_items: Total number of items
        operation: Type of operation ('up', 'down', 'page_up', 'page_down', 'top', 'bottom')

    Returns:
        New selection index within bounds
    """
    if total_items == 0:
        return 0

    page_size = get_navigation_page_size()

    if operation == "up":
        return max(0, current_idx - 1)
    elif operation == "down":
        return min(total_items - 1, current_idx + 1)
    elif operation == "page_up":
        return max(0, current_idx - page_size)
    elif operation == "page_down":
        return min(total_items - 1, current_idx + page_size)
    elif operation == "top":
        return 0
    elif operation == "bottom":
        return total_items - 1
    else:
        # Ensure current index is within bounds
        return min(max(0, current_idx), total_items - 1)


def should_reset_selection_on_filter_change() -> bool:
    """Determine if selection should reset when filter changes.

    Returns:
        True if selection should reset to 0 when filter changes
    """
    return True


def get_card_quantity_action(key: str) -> Tuple[str, int]:
    """Map keyboard input to card quantity action.

    Args:
        key: Keyboard input key

    Returns:
        Tuple of (action_type, value) where action_type is 'increment', 'decrement', 'set', or 'none'
    """
    if key == "→" or key == "C":  # Right arrow
        return ("increment", 1)
    elif key == "←" or key == "D":  # Left arrow
        return ("decrement", 1)
    elif key == "0":
        return ("set", 0)
    elif key.isdigit() and key != "0":
        return ("set", int(key))
    else:
        return ("none", 0)


def should_ignore_pack_toggle_errors() -> bool:
    """Determine if pack toggle errors should be silently ignored.

    Returns:
        True if pack toggle errors should be ignored (for better UX)
    """
    return True


class NavigationConfig:
    """Configuration for navigation behavior."""

    def __init__(self) -> None:
        """Initialize navigation configuration with defaults."""
        self.page_size = DEFAULT_PAGE_SIZE
        self.reset_selection_on_filter = True
        self.ignore_toggle_errors = True

    def get_viewport_padding(self, interface_type: str) -> int:
        """Get viewport padding for interface type.

        Args:
            interface_type: Type of interface

        Returns:
            Number of lines to reserve for UI elements
        """
        return DEFAULT_VIEWPORT_PADDING.get(
            interface_type, DEFAULT_VIEWPORT_PADDING["default"]
        )
