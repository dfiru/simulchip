"""Filtering utilities for cards and packs.

This module provides centralized filtering logic for searching
and filtering card/pack collections.
"""

# Standard library imports
from typing import Any, Callable, Dict, List, Optional

from .models import CardModel, PackModel


def filter_packs(
    packs: List[Dict[str, Any]],
    filter_text: str = "",
    owned_packs: Optional[set] = None,
    show_owned_only: bool = False,
) -> List[PackModel]:
    """Filter packs based on search text and ownership.

    Args:
        packs: List of pack data dictionaries
        filter_text: Text to search for in pack fields
        owned_packs: Set of owned pack codes
        show_owned_only: If True, only show owned packs

    Returns:
        List of filtered PackModel objects
    """
    pack_models = [PackModel(pack) for pack in packs]

    # Apply text filter
    if filter_text:
        pack_models = [p for p in pack_models if p.matches_filter(filter_text)]

    # Apply ownership filter
    if show_owned_only and owned_packs:
        pack_models = [p for p in pack_models if p.code in owned_packs]

    return pack_models


def filter_packs_raw(
    packs: List[Dict[str, Any]], filter_text: str = ""
) -> List[Dict[str, Any]]:
    """Filter pack dictionaries based on search text (for CLI usage).

    Args:
        packs: List of pack data dictionaries
        filter_text: Text to search for in pack fields

    Returns:
        List of filtered pack dictionaries
    """
    if not filter_text:
        return packs

    filtered_packs = []
    filter_lower = filter_text.lower()

    for pack in packs:
        name = pack.get("name") or ""
        code = pack.get("code") or ""
        cycle = pack.get("cycle") or ""

        if (
            filter_lower in name.lower()
            or filter_lower in code.lower()
            or filter_lower in cycle.lower()
        ):
            filtered_packs.append(pack)

    return filtered_packs


def filter_cards(
    cards: List[Dict[str, Any]],
    filter_text: str = "",
    expected_cards: Optional[Dict[str, int]] = None,
    show_expected_only: bool = False,
) -> List[CardModel]:
    """Filter cards based on search text and expected quantities.

    Args:
        cards: List of card data dictionaries
        filter_text: Text to search for in card fields
        expected_cards: Dictionary of card codes to expected quantities
        show_expected_only: If True, only show cards with expected quantities

    Returns:
        List of filtered CardModel objects
    """
    card_models = [CardModel(card) for card in cards]

    # Apply expected-only filter first (more restrictive)
    if show_expected_only and expected_cards:
        card_models = [c for c in card_models if expected_cards.get(c.code, 0) > 0]

    # Apply text filter
    if filter_text:
        card_models = [c for c in card_models if c.matches_filter(filter_text)]

    return card_models


def filter_cards_raw(
    cards: List[Dict[str, Any]],
    filter_text: str = "",
    manager: Optional[Any] = None,
    show_expected_only: bool = False,
) -> List[Dict[str, Any]]:
    """Filter card dictionaries based on search text and expected quantities (for CLI usage).

    Args:
        cards: List of card data dictionaries
        filter_text: Text to search for in card fields
        manager: CollectionManager instance for expected card logic
        show_expected_only: If True, only show cards with expected quantities

    Returns:
        List of filtered card dictionaries
    """
    filtered_cards = []
    filter_lower = filter_text.lower() if filter_text else ""

    for card in cards:
        # Check if card should be included based on expected-only mode
        if show_expected_only and manager:
            expected = manager.get_expected_card_count(card["code"])
            if expected == 0:
                continue  # Skip cards with no expected quantity

        # Apply text filter if present
        if filter_text:
            title = card.get("title", "").lower()
            type_code = card.get("type_code", "").lower()
            faction = card.get("faction_code", "").lower()
            text = card.get("text", "").lower()
            if not any(
                filter_lower in field for field in [title, type_code, faction, text]
            ):
                continue  # Skip cards that don't match filter

        filtered_cards.append(card)

    return filtered_cards


def create_pack_filter(
    owned_packs: Optional[set] = None, show_owned_only: bool = False
) -> Callable[[PackModel], bool]:
    """Create a pack filter function for use in filtering operations.

    Args:
        owned_packs: Set of owned pack codes
        show_owned_only: If True, only show owned packs

    Returns:
        Filter function that returns True if pack should be included
    """

    def filter_func(pack: PackModel) -> bool:
        if show_owned_only and owned_packs:
            return pack.code in owned_packs
        return True

    return filter_func


def create_card_filter(
    expected_cards: Optional[Dict[str, int]] = None, show_expected_only: bool = False
) -> Callable[[CardModel], bool]:
    """Create a card filter function for use in filtering operations.

    Args:
        expected_cards: Dictionary of card codes to expected quantities
        show_expected_only: If True, only show cards with expected quantities

    Returns:
        Filter function that returns True if card should be included
    """

    def filter_func(card: CardModel) -> bool:
        if show_expected_only and expected_cards:
            return expected_cards.get(card.code, 0) > 0
        return True

    return filter_func


def filter_items_generic(items: List[Any], filter_text: str) -> List[Any]:
    """Filter items generically based on filter text.

    Args:
        items: List of items to filter
        filter_text: Text to search for

    Returns:
        List of filtered items
    """
    if not filter_text:
        return items

    filtered = []
    filter_lower = filter_text.lower()

    for item in items:
        if hasattr(item, "matches_filter"):
            if item.matches_filter(filter_lower):
                filtered.append(item)
        else:
            # Fallback: check if filter text is in string representation
            if filter_lower in str(item).lower():
                filtered.append(item)

    return filtered
