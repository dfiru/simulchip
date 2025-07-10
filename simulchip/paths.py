"""Path management utilities for Simulchip.

This module provides centralized path generation and management for:
- Collection files
- Deck PDFs
- Cache directories
- Configuration files
"""

# Standard library imports
from pathlib import Path
from typing import Any, Optional

from .utils import sanitize_filename

# Default paths
DEFAULT_COLLECTION_FILENAME = "collection.toml"
DEFAULT_SIMULCHIP_DIR = Path.home() / ".simulchip"
DEFAULT_COLLECTION_PATH = DEFAULT_SIMULCHIP_DIR / DEFAULT_COLLECTION_FILENAME
DEFAULT_CACHE_DIR = DEFAULT_SIMULCHIP_DIR / "cache"
DEFAULT_DECKS_DIR = Path.cwd() / "decks"


def get_default_collection_path() -> Path:
    """Get the default collection file path.

    Returns:
        Path to the default collection file (~/.simulchip/collection.toml)
    """
    return DEFAULT_COLLECTION_PATH


def get_default_cache_dir() -> Path:
    """Get the default cache directory path.

    Returns:
        Path to the default cache directory (~/.simulchip/cache)
    """
    return DEFAULT_CACHE_DIR


def get_deck_pdf_path(
    identity_title: str, deck_name: str, side: str, base_dir: Optional[Path] = None
) -> Path:
    """Generate the standard path for a deck PDF.

    Creates a path structure like:
    decks/(corporation|runner)/(identity-slug)/(deck-name).pdf

    Args:
        identity_title: The identity card title (e.g., "Zahya Sadeghi: Versatile Smuggler")
        deck_name: The deck name
        side: The side ("corp", "corporation", or "runner")
        base_dir: Base directory for decks (defaults to ./decks)

    Returns:
        Path object for the deck PDF

    Examples:
        >>> get_deck_pdf_path("Zahya Sadeghi: Versatile Smuggler", "My Deck", "runner")
        PosixPath('decks/runner/zahya-sadeghi-versatile-smuggler/my-deck.pdf')
    """
    if base_dir is None:
        base_dir = DEFAULT_DECKS_DIR

    # Create identity slug from title
    identity_slug = create_identity_slug(identity_title)

    # Sanitize the deck name for filesystem
    safe_deck_name = sanitize_filename(deck_name.lower().replace(" ", "-"))

    # Determine side directory
    side_dir = "corporation" if side.lower() in ["corp", "corporation"] else "runner"

    # Create path: base_dir/(corporation|runner)/(identity-slug)/(deck-name).pdf
    return base_dir / side_dir / identity_slug / f"{safe_deck_name}.pdf"


def create_identity_slug(identity_title: str) -> str:
    """Create a filesystem-safe slug from an identity title.

    Args:
        identity_title: The identity card title

    Returns:
        A filesystem-safe slug

    Examples:
        >>> create_identity_slug("Zahya Sadeghi: Versatile Smuggler")
        'zahya-sadeghi-versatile-smuggler'
        >>> create_identity_slug("Haas-Bioroid: Engineering the Future")
        'haas-bioroid-engineering-the-future'
    """
    # Remove colons and replace spaces with hyphens
    slug = identity_title.lower().replace(":", "").replace(" ", "-")
    # Use sanitize_filename to ensure it's filesystem-safe
    return sanitize_filename(slug)


def ensure_path_exists(path: Path) -> None:
    """Ensure a path and its parent directories exist.

    Args:
        path: Path to create (if it's a file, only parent dirs are created)
    """
    if path.suffix:  # It's a file
        path.parent.mkdir(parents=True, exist_ok=True)
    else:  # It's a directory
        path.mkdir(parents=True, exist_ok=True)


def get_cache_subdirectory(subdir: str) -> Path:
    """Get a subdirectory within the cache directory.

    Args:
        subdir: Name of the subdirectory

    Returns:
        Path to the cache subdirectory
    """
    return DEFAULT_CACHE_DIR / subdir


def get_cache_locations() -> list[Path]:
    """Get all potential cache directory locations.

    Returns:
        List of paths where cache files might be stored
    """
    return [
        DEFAULT_CACHE_DIR,  # ~/.simulchip/cache
        Path.cwd() / ".cache",  # ./cache (CacheManager default)
    ]


def reset_simulchip_data(
    collection_path: Optional[Path] = None,
    reset_collection: bool = True,
    reset_cache: bool = True,
) -> dict[str, list[str]]:
    """Reset Simulchip data files.

    Args:
        collection_path: Path to collection file (uses default if None)
        reset_collection: Whether to reset the collection file
        reset_cache: Whether to clear cache directories

    Returns:
        Dictionary with 'removed' and 'errors' lists describing what happened
    """
    # Standard library imports
    import shutil

    if collection_path is None:
        collection_path = DEFAULT_COLLECTION_PATH

    removed = []
    errors = []

    # Reset collection file
    if reset_collection and collection_path.exists():
        try:
            collection_path.unlink()
            removed.append(f"Collection file: {collection_path}")
        except Exception as e:
            errors.append(f"Failed to remove collection file: {e}")

    # Reset cache directories
    if reset_cache:
        for cache_dir in get_cache_locations():
            if cache_dir.exists():
                try:
                    shutil.rmtree(cache_dir)
                    removed.append(f"Cache directory: {cache_dir}")
                except Exception as e:
                    errors.append(f"Failed to remove cache {cache_dir}: {e}")

    return {"removed": removed, "errors": errors}


def generate_default_output_path(comparison_result: Any) -> Path:
    """Generate default output path for a deck comparison result.

    Args:
        comparison_result: Deck comparison result with identity and decklist_name

    Returns:
        Path for the deck PDF
    """
    from .utils import get_faction_side

    # Determine if corp or runner based on identity
    identity_faction = comparison_result.identity.faction_code
    side = get_faction_side(identity_faction)

    return get_deck_pdf_path(
        comparison_result.identity.title, comparison_result.decklist_name, side
    )
