"""Data models and wrappers for Simulchip.

This module provides standardized data models for working with
cards, packs, and other Netrunner data throughout the library.
"""

# Standard library imports
from typing import Any, Dict, List, Protocol


class FilterableItem(Protocol):
    """Protocol for items that can be filtered and displayed."""

    def get_id(self) -> str:
        """Get unique identifier for this item."""
        ...

    def matches_filter(self, filter_text: str) -> bool:
        """Check if this item matches the filter text."""
        ...


class PackModel:
    """Model wrapper for pack data with filtering capabilities."""

    def __init__(self, pack_data: Dict[str, Any]):
        """Initialize with pack data from API.

        Args:
            pack_data: Dictionary containing pack information
        """
        self.data = pack_data
        self.code = str(pack_data.get("code", ""))
        self.name = str(pack_data.get("name", ""))
        self.cycle = str(pack_data.get("cycle", ""))
        self.date_release = str(pack_data.get("date_release", ""))

    def get_id(self) -> str:
        """Get unique identifier (pack code)."""
        return self.code

    def matches_filter(self, filter_text: str) -> bool:
        """Check if pack matches the filter text.

        Args:
            filter_text: Text to search for (case-insensitive)

        Returns:
            True if any searchable field contains the filter text
        """
        if not filter_text:
            return True

        filter_lower = filter_text.lower()
        searchable_fields = [
            self.code,
            self.name,
            self.cycle,
        ]

        return any(
            filter_lower in field.lower() for field in searchable_fields if field
        )


class CardModel:
    """Model wrapper for card data with filtering capabilities."""

    def __init__(self, card_data: Dict[str, Any]):
        """Initialize with card data from API.

        Args:
            card_data: Dictionary containing card information
        """
        self.data = card_data
        self.code = str(card_data.get("code", ""))
        self.title = str(card_data.get("title", ""))
        self.type_code = str(card_data.get("type_code", ""))
        self.faction_code = str(card_data.get("faction_code", ""))
        self.pack_code = str(card_data.get("pack_code", ""))
        self.text = str(card_data.get("text", ""))
        self.quantity = int(card_data.get("quantity", 1))
        self.deck_limit = int(card_data.get("deck_limit", 3))

    def get_id(self) -> str:
        """Get unique identifier (card code)."""
        return self.code

    def matches_filter(self, filter_text: str) -> bool:
        """Check if card matches the filter text.

        Args:
            filter_text: Text to search for (case-insensitive)

        Returns:
            True if any searchable field contains the filter text
        """
        if not filter_text:
            return True

        filter_lower = filter_text.lower()
        searchable_fields = [
            self.title,
            self.type_code,
            self.faction_code,
            self.text,
        ]

        return any(
            filter_lower in field.lower() for field in searchable_fields if field
        )

    @property
    def is_identity(self) -> bool:
        """Check if this card is an identity."""
        return self.type_code == "identity"


def filter_items(items: List[FilterableItem], filter_text: str) -> List[FilterableItem]:
    """Filter a list of items based on filter text.

    Args:
        items: List of filterable items
        filter_text: Text to filter by

    Returns:
        Filtered list of items
    """
    if not filter_text:
        return items

    return [item for item in items if item.matches_filter(filter_text)]
