"""Utility functions for simulchip with enhanced type safety."""

from __future__ import annotations

# Standard library imports
import re
from enum import Enum
from typing import Dict, Final, Optional, Pattern, Tuple


class FactionCode(str, Enum):
    """Valid faction codes in Netrunner."""

    # Runner factions
    ANARCH = "anarch"
    CRIMINAL = "criminal"
    SHAPER = "shaper"
    ADAM = "adam"
    APEX = "apex"
    SUNNY_LEBEAU = "sunny-lebeau"

    # Corp factions
    HAAS_BIOROID = "haas-bioroid"
    JINTEKI = "jinteki"
    NBN = "nbn"
    WEYLAND = "weyland-consortium"

    # Neutral
    NEUTRAL_CORP = "neutral-corp"
    NEUTRAL_RUNNER = "neutral-runner"


# Compiled regex patterns for better performance
UUID_PATTERN: Final[Pattern[str]] = re.compile(
    r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"
)

DECKLIST_URL_PATTERNS: Final[Tuple[Pattern[str], ...]] = (
    re.compile(r"/decklist/(\d+)(?:/|$)"),
    re.compile(r"/decklist/view/(\d+)"),
    re.compile(r"/en/decklist/(\d+)"),
)

# Faction symbols mapping
FACTION_SYMBOLS: Final[Dict[str, str]] = {
    # Runner factions
    "anarch": "[A]",
    "criminal": "[C]",
    "shaper": "[S]",
    "adam": "[AD]",
    "apex": "[AP]",
    "sunny-lebeau": "[SL]",
    # Corp factions
    "haas-bioroid": "[HB]",
    "jinteki": "[J]",
    "nbn": "[N]",
    "weyland-consortium": "[W]",
    "neutral-corp": "[NC]",
    "neutral-runner": "[NR]",
}


def extract_decklist_id(url: str) -> Optional[str]:
    """Extract decklist ID from a NetrunnerDB URL.

    Args:
        url: Full NetrunnerDB URL

    Returns:
        The decklist ID or None if invalid URL

    Raises:
        ValueError: If url is empty

    Examples:
        >>> extract_decklist_id("https://netrunnerdb.com/en/decklist/7a9e2d43-bd55-45d0-bd2c-99cad2d17d4c/deck-name")
        '7a9e2d43-bd55-45d0-bd2c-99cad2d17d4c'

        >>> extract_decklist_id("https://netrunnerdb.com/decklist/view/12345")
        '12345'
    """
    if not url:
        raise ValueError("URL cannot be empty")

    # Clean input
    url = url.strip()

    # Must be a URL
    if not url.startswith(("http://", "https://")):
        return None

    # Must be from netrunnerdb.com
    if "netrunnerdb.com" not in url:
        return None

    # Try to match a UUID pattern in URL
    uuid_match = UUID_PATTERN.search(url)
    if uuid_match:
        return uuid_match.group(0)

    # Try to match numeric ID in various URL formats
    for pattern in DECKLIST_URL_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)

    # No valid pattern found
    return None


def get_faction_symbol(faction_code: str) -> str:
    """Get a symbol for each faction with validation.

    Args:
        faction_code: Faction code from NetrunnerDB

    Returns:
        A text symbol representing the faction
    """
    if not faction_code:
        return "[?]"

    # Normalize faction code
    faction_code = faction_code.lower().strip()

    return FACTION_SYMBOLS.get(faction_code, f"[{faction_code[:2].upper()}]")


def format_card_count(count: int, card_name: str) -> str:
    """Format a card count and name for display with validation.

    Args:
        count: Number of copies
        card_name: Name of the card

    Returns:
        Formatted string like "3x Card Name"

    Raises:
        ValueError: If count is negative or card_name is empty
    """
    if count < 0:
        raise ValueError(f"Count cannot be negative: {count}")
    if not card_name or not card_name.strip():
        raise ValueError("Card name cannot be empty")

    return f"{count}x {card_name.strip()}"


def sanitize_filename(filename: str, max_length: int = 50) -> str:
    """Sanitize a string for use as a filename.

    Args:
        filename: String to sanitize
        max_length: Maximum length of the result

    Returns:
        Sanitized filename safe for all platforms

    Raises:
        ValueError: If filename is empty after sanitization
    """
    if not filename:
        raise ValueError("Filename cannot be empty")

    # Remove or replace invalid characters
    sanitized = "".join(
        c if c.isalnum() or c in " -_" else "_" for c in filename
    ).strip()

    # Replace multiple spaces/underscores with single underscore
    sanitized = re.sub(r"[_\s]+", "_", sanitized)

    # Truncate to max length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip("_")

    if not sanitized:
        raise ValueError("Filename is empty after sanitization")

    return sanitized


def get_faction_short_name(faction_code: str) -> str:
    """Get a short name for a faction suitable for filenames.

    Args:
        faction_code: Faction code from NetrunnerDB

    Returns:
        Short faction name (4 chars max)
    """
    faction_shortcuts = {
        "anarch": "ana",
        "criminal": "crim",
        "shaper": "shap",
        "adam": "adam",
        "apex": "apex",
        "sunny-lebeau": "sun",
        "haas-bioroid": "hb",
        "jinteki": "jin",
        "nbn": "nbn",
        "weyland-consortium": "wey",
        "neutral-corp": "ncor",
        "neutral-runner": "nrun",
    }

    if not faction_code:
        return "unkn"

    faction_code = faction_code.lower().strip()
    return faction_shortcuts.get(faction_code, faction_code[:4])


def parse_card_code(card_code: str) -> Tuple[str, str]:
    """Parse a card code into pack number and card number.

    Args:
        card_code: Card code like "01001"

    Returns:
        Tuple of (pack_number, card_number)

    Raises:
        ValueError: If card code format is invalid
    """
    if not card_code:
        raise ValueError("Card code cannot be empty")

    if not card_code.isdigit() or len(card_code) != 5:
        raise ValueError(f"Card code must be 5 digits, got: {card_code}")

    return card_code[:2], card_code[2:]


def format_deck_size(card_count: int) -> str:
    """Format deck size for display.

    Args:
        card_count: Number of cards in deck

    Returns:
        Formatted string like "45 cards"
    """
    if card_count < 0:
        raise ValueError(f"Card count cannot be negative: {card_count}")

    return f"{card_count} card{'s' if card_count != 1 else ''}"


def get_faction_side(faction_code: str) -> str:
    """Determine if a faction is corporation or runner side.

    Args:
        faction_code: Faction code from NetrunnerDB

    Returns:
        Either "corporation" or "runner"

    Examples:
        >>> get_faction_side("haas-bioroid")
        'corporation'

        >>> get_faction_side("anarch")
        'runner'
    """
    if not faction_code:
        return "runner"  # Default to runner for unknown factions

    faction_code = faction_code.lower().strip()

    # Corporation factions
    corp_factions = {
        FactionCode.HAAS_BIOROID.value,
        FactionCode.JINTEKI.value,
        FactionCode.NBN.value,
        FactionCode.WEYLAND.value,
        FactionCode.NEUTRAL_CORP.value,
    }

    return "corporation" if faction_code in corp_factions else "runner"
