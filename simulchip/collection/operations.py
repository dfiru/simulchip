"""Collection operations and utilities.

This module provides utility functions for collection management
that are used by the CLI but should be in the library.
"""

# Standard library imports
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..api.netrunnerdb import NetrunnerDBAPI, PackData
from ..paths import get_cache_locations
from .manager import CollectionManager


def get_reset_items(collection_path: Path) -> List[str]:
    """Get list of items that would be reset.

    Args:
        collection_path: Path to collection file

    Returns:
        List of description strings for items to be reset
    """
    items_to_reset = []

    # Check collection file
    if collection_path.exists():
        items_to_reset.append(f"Collection file: {collection_path}")

    # Check for API cache files in all locations
    for cache_dir in get_cache_locations():
        if cache_dir.exists():
            cache_files = list(cache_dir.glob("*"))
            if cache_files:
                items_to_reset.append(
                    f"API cache files in {cache_dir}: {len(cache_files)} files"
                )

    return items_to_reset


def get_or_create_manager(
    collection_file: Optional[Path], api: NetrunnerDBAPI, all_cards: bool = False
) -> CollectionManager:
    """Get or create a collection manager with appropriate settings.

    Args:
        collection_file: Path to collection file (can be None)
        api: NetrunnerDB API instance
        all_cards: If True, use empty collection (ignore existing collection)

    Returns:
        CollectionManager instance
    """
    if collection_file and collection_file.exists() and not all_cards:
        return CollectionManager(collection_file=collection_file, api=api)
    else:
        # Empty collection if generating all cards or no collection exists
        return CollectionManager(api=api)


def sort_cards_by_title(cards_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Sort cards by title for consistent display.

    Args:
        cards_dict: Dictionary of card code to card data

    Returns:
        List of card data sorted by title
    """
    return sorted(cards_dict.values(), key=lambda x: x.get("title", ""))


def get_packs_by_release_date(
    api: NetrunnerDBAPI, newest_first: bool = True
) -> List[PackData]:
    """Get packs sorted by release date.

    Args:
        api: NetrunnerDB API instance
        newest_first: If True, sort newest first

    Returns:
        List of pack data sorted by release date
    """
    return api.get_packs_by_release_date(newest_first=newest_first)
