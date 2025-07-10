"""Card collection management module.

This module provides functionality for managing a local collection of
Netrunner cards, including tracking owned cards, packs, and missing cards.

Classes:
    CollectionManager: Main class for managing card collections.
    CardRequirement: Represents a card requirement from a decklist.
    CollectionError: Custom exception for collection errors.

Protocols:
    APIClient: Protocol for API client dependency injection.
"""

from __future__ import annotations

# Standard library imports
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Final, List, Optional, Protocol, Set, TypedDict, Union

# Third-party imports
import toml

from ..api.netrunnerdb import CardData, PackData


class CollectionData(TypedDict, total=False):
    """Type definition for collection file structure.

    This represents the structure of the collection TOML file.

    Attributes:
        packs: List of pack codes that are fully owned.
        owned_packs: List of pack codes that are owned (new format).
        cards: Dictionary mapping card codes to quantities owned.
        missing: Dictionary mapping card codes to quantities marked as missing.
    """

    packs: List[str]
    owned_packs: List[str]
    cards: Dict[str, int]
    missing: Dict[str, int]


class PackSummary(TypedDict):
    """Type definition for pack summary statistics.

    Attributes:
        owned: Number of unique cards owned from this pack.
        total: Total number of unique cards in this pack.
    """

    owned: int
    total: int


@dataclass(frozen=True)
class CollectionError(Exception):
    """Custom exception for collection-related errors.

    Attributes:
        message: Error message describing what went wrong.
        file_path: Path to the collection file if applicable.
    """

    message: str
    file_path: Optional[Path] = None


@dataclass
class CardRequirement:
    """Represents a card requirement from a decklist.

    This class tracks how many copies of a card are required by a decklist
    and how many are available in the collection.

    Attributes:
        code: Card code (e.g., "01001").
        required: Number of copies required by the decklist.
        owned: Number of copies owned in the collection.
        missing: Number of additional copies needed.

    Properties:
        is_satisfied: True if owned >= required.

    Examples:
        >>> req = CardRequirement("01001", required=3, owned=2, missing=1)
        >>> req.is_satisfied
        False
    """

    code: str
    required: int
    owned: int
    missing: int

    @property
    def is_satisfied(self) -> bool:
        """Check if requirement is fully satisfied."""
        return self.missing == 0


class APIClient(Protocol):
    """Protocol for API client interface."""

    def get_all_cards(self) -> Dict[str, CardData]:
        """Get all cards from the API."""
        ...

    def get_pack_by_code(self, pack_code: str) -> Optional[PackData]:
        """Get pack data by code."""
        ...


# Class constants - defined outside dataclass
DEFAULT_CARD_COPIES: Final[int] = 3
SUPPORTED_FORMATS: Final[Set[str]] = {".toml"}


@dataclass
class CollectionManager:
    """Manages local card collection data with validation and functional patterns."""

    collection_file: Optional[Path] = None
    api: Optional[APIClient] = None
    owned_packs: Set[str] = field(default_factory=set)
    card_diffs: Dict[str, int] = field(
        default_factory=dict
    )  # Differences from expected

    # Deprecated - kept for backward compatibility during migration
    collection: Dict[str, int] = field(default_factory=dict)
    missing_cards: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize and load collection after dataclass initialization."""
        if self.collection_file and self.collection_file.exists():
            self.load_collection()

    def load_collection(self) -> None:
        """Load collection from file with validation.

        Raises:
            CollectionError: If file format is unsupported or data is invalid
        """
        if not self.collection_file or not self.collection_file.exists():
            return

        if self.collection_file.suffix not in SUPPORTED_FORMATS:
            raise CollectionError(
                f"Unsupported file format: {self.collection_file.suffix}. "
                f"Supported formats: {', '.join(SUPPORTED_FORMATS)}",
                file_path=self.collection_file,
            )

        try:
            with open(self.collection_file, "r", encoding="utf-8") as f:
                data = toml.load(f)
        except toml.TomlDecodeError as e:
            raise CollectionError(
                f"Failed to parse {self.collection_file}: {str(e)}",
                file_path=self.collection_file,
            ) from e

        self._parse_collection_data(data)

        # Expand packs after loading
        if self.owned_packs and self.api:
            self._expand_packs_to_cards()

    def _parse_collection_data(self, data: Union[Dict, List]) -> None:
        """Parse collection data from various formats.

        Args:
            data: Raw data from file

        Raises:
            CollectionError: If data format is invalid
        """
        if isinstance(data, dict):
            # Load owned packs
            if "owned_packs" in data:
                packs = data["owned_packs"]
                if not isinstance(packs, list):
                    raise CollectionError(
                        f"'owned_packs' must be a list, got {type(packs).__name__}"
                    )
                self.owned_packs = set(packs)
            elif "packs" in data:
                # Backward compatibility
                packs = data["packs"]
                if not isinstance(packs, list):
                    raise CollectionError(
                        f"'packs' must be a list, got {type(packs).__name__}"
                    )
                self.owned_packs = set(packs)

            # Load card differences (new format)
            if "cards" in data and "owned_packs" in data:
                cards = data["cards"]
                if not isinstance(cards, dict):
                    raise CollectionError(
                        f"'cards' must be a dict, got {type(cards).__name__}"
                    )
                # In new format, cards stores differences from expected
                self.card_diffs = self._validate_card_counts(cards, allow_negative=True)

            # Backward compatibility: Load individual cards (old format)
            elif "cards" in data:
                cards = data["cards"]
                if not isinstance(cards, dict):
                    raise CollectionError(
                        f"'cards' must be a dict, got {type(cards).__name__}"
                    )
                self.collection = self._validate_card_counts(cards)
            elif "packs" not in data and "owned_packs" not in data:
                # Root-level card dict (old format)
                self.collection = self._validate_card_counts(data)

            # Load missing cards (backward compatibility)
            if "missing" in data:
                missing = data["missing"]
                if not isinstance(missing, dict):
                    raise CollectionError(
                        f"'missing' must be a dict, got {type(missing).__name__}"
                    )
                self.missing_cards = self._validate_card_counts(missing)

        elif isinstance(data, list):
            # List format: [{"code": "card_code", "count": count}]
            self.collection = {}
            for item in data:
                if not isinstance(item, dict) or "code" not in item:
                    continue
                code = str(item["code"])
                count = int(item.get("count", 1))
                if count > 0:
                    self.collection[code] = count
        else:
            raise CollectionError(
                f"Invalid collection data type: {type(data).__name__}"
            )

    def _validate_card_counts(
        self, cards: Dict[str, Any], allow_negative: bool = False
    ) -> Dict[str, int]:
        """Validate and convert card counts to integers.

        Args:
            cards: Dictionary of card codes to counts
            allow_negative: Whether to allow negative counts (for differences)

        Returns:
            Validated dictionary with integer counts

        Raises:
            CollectionError: If counts are invalid
        """
        validated = {}
        for code, count in cards.items():
            try:
                count_int = int(count)
                if not allow_negative and count_int < 0:
                    raise CollectionError(
                        f"Card count cannot be negative: {code}={count}"
                    )
                if allow_negative:
                    # For differences, store all non-zero values (positive and negative)
                    if count_int != 0:
                        validated[str(code)] = count_int
                else:
                    # For absolute counts, only store positive values
                    if count_int > 0:
                        validated[str(code)] = count_int
            except (ValueError, TypeError) as e:
                raise CollectionError(f"Invalid count for card {code}: {count}") from e
        return validated

    def save_collection(self) -> None:
        """Save collection to file with atomic write.

        Raises:
            CollectionError: If save fails
        """
        if not self.collection_file:
            return

        data: CollectionData = {}

        # Use new format if we have card_diffs, otherwise use legacy format for compatibility
        if self.card_diffs or (self.owned_packs and not self.collection):
            # New simplified format
            if self.owned_packs:
                data["owned_packs"] = sorted(self.owned_packs)
            if self.card_diffs:
                data["cards"] = dict(sorted(self.card_diffs.items()))
        else:
            # Legacy format for backward compatibility
            if self.owned_packs:
                data["packs"] = sorted(self.owned_packs)
            if self.collection:
                data["cards"] = dict(sorted(self.collection.items()))
            if self.missing_cards:
                data["missing"] = dict(sorted(self.missing_cards.items()))

        # Atomic write with temporary file
        temp_file = self.collection_file.with_suffix(".tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                toml.dump(data, f)

            # Atomic rename
            temp_file.replace(self.collection_file)

        except Exception as e:
            # Clean up temp file if it exists
            if temp_file.exists():
                temp_file.unlink()
            raise CollectionError(
                f"Failed to save collection: {str(e)}", file_path=self.collection_file
            ) from e

    def modify_card_count(
        self, card_code: str, delta: int, target: Dict[str, int]
    ) -> None:
        """Modify card count with validation (functional helper).

        Args:
            card_code: Card code to modify
            delta: Change in count (positive or negative)
            target: Target dictionary to modify

        Raises:
            ValueError: If card_code is invalid
        """
        if not card_code:
            raise ValueError("Card code cannot be empty")

        current = target.get(card_code, 0)
        new_count = max(0, current + delta)

        if new_count > 0:
            target[card_code] = new_count
        elif card_code in target:
            del target[card_code]

    def add_card(self, card_code: str, count: int = 1) -> None:
        """Add cards to collection."""
        if count <= 0:
            raise ValueError(f"Count must be positive, got {count}")
        self.modify_card_count(card_code, count, self.collection)

    def remove_card(self, card_code: str, count: int = 1) -> None:
        """Remove cards from collection."""
        if count <= 0:
            raise ValueError(f"Count must be positive, got {count}")
        self.modify_card_count(card_code, -count, self.collection)

    def add_missing_card(self, card_code: str, count: int = 1) -> None:
        """Mark cards as missing/lost."""
        if count <= 0:
            raise ValueError(f"Count must be positive, got {count}")
        self.modify_card_count(card_code, count, self.missing_cards)

    def remove_missing_card(self, card_code: str, count: int = 1) -> None:
        """Mark missing cards as found."""
        if count <= 0:
            raise ValueError(f"Count must be positive, got {count}")
        self.modify_card_count(card_code, -count, self.missing_cards)

    def get_card_count(self, card_code: str) -> int:
        """Get effective card count (owned minus missing)."""
        owned = self.collection.get(card_code, 0)
        missing = self.missing_cards.get(card_code, 0)
        return max(0, owned - missing)

    def has_card(self, card_code: str, count: int = 1) -> bool:
        """Check if collection has enough copies of a card."""
        return self.get_card_count(card_code) >= count

    def analyze_decklist(self, decklist: Dict[str, int]) -> List[CardRequirement]:
        """Analyze decklist requirements against collection.

        Args:
            decklist: Dictionary mapping card codes to required counts

        Returns:
            List of card requirements with ownership status
        """
        if not decklist:
            return []

        return [
            CardRequirement(
                code=card_code,
                required=required_count,
                owned=min(self.get_card_count(card_code), required_count),
                missing=max(0, required_count - self.get_card_count(card_code)),
            )
            for card_code, required_count in sorted(decklist.items())
            if required_count > 0
        ]

    def get_missing_cards(self, decklist: Dict[str, int]) -> Dict[str, int]:
        """Get cards missing from collection for a decklist."""
        requirements = self.analyze_decklist(decklist)
        return {req.code: req.missing for req in requirements if req.missing > 0}

    def get_owned_cards(self, decklist: Dict[str, int]) -> Dict[str, int]:
        """Get cards from decklist that are in collection."""
        requirements = self.analyze_decklist(decklist)
        return {req.code: req.owned for req in requirements if req.owned > 0}

    def get_all_cards(self) -> Dict[str, int]:
        """Get all effective card counts."""
        # Compute effective counts accounting for missing cards
        all_codes = set(self.collection.keys()) | set(self.missing_cards.keys())
        return {
            code: self.get_card_count(code)
            for code in all_codes
            if self.get_card_count(code) > 0
        }

    def get_pack_summary(self, api_client: APIClient) -> Dict[str, PackSummary]:
        """Get collection summary by pack with functional approach.

        Args:
            api_client: NetrunnerDB API client

        Returns:
            Dictionary mapping pack codes to statistics
        """
        cards = api_client.get_all_cards()

        # Build pack summary using functional approach
        pack_cards = defaultdict(list)
        for code, card in cards.items():
            pack_code = card.get("pack_code", "unknown")
            pack_cards[pack_code].append(code)

        return {
            pack_code: PackSummary(
                owned=sum(1 for code in card_codes if code in self.collection),
                total=len(card_codes),
            )
            for pack_code, card_codes in pack_cards.items()
        }

    def _expand_packs_to_cards(self) -> None:
        """Expand owned packs to individual cards."""
        if not self.api:
            return

        cards = self.api.get_all_cards()

        # Get all cards from owned packs
        pack_cards = [
            (code, DEFAULT_CARD_COPIES)
            for code, card in cards.items()
            if card.get("pack_code") in self.owned_packs and code not in self.collection
        ]

        # Add to collection
        for code, count in pack_cards:
            self.collection[code] = count

    def add_pack(self, pack_code: str) -> None:
        """Add all cards from a pack to collection.

        Raises:
            ValueError: If pack_code is invalid
        """
        if not pack_code:
            raise ValueError("Pack code cannot be empty")

        self.owned_packs.add(pack_code)
        if self.api:
            self._expand_packs_to_cards()

    def remove_pack(self, pack_code: str) -> None:
        """Remove all cards from a pack from collection.

        Raises:
            ValueError: If pack is not owned
        """
        if pack_code not in self.owned_packs:
            raise ValueError(f"Pack not owned: {pack_code}")

        self.owned_packs.remove(pack_code)

        if self.api:
            # Remove cards from this pack
            cards = self.api.get_all_cards()
            cards_to_remove = [
                code
                for code, data in cards.items()
                if data.get("pack_code") == pack_code
            ]

            for card_code in cards_to_remove:
                self.collection.pop(card_code, None)

    def has_pack(self, pack_code: str) -> bool:
        """Check if collection has a pack."""
        return pack_code in self.owned_packs

    def get_owned_packs(self) -> List[str]:
        """Get sorted list of owned pack codes."""
        return sorted(self.owned_packs)

    def get_expected_card_count(self, card_code: str) -> int:
        """Get expected card count based on owned packs."""
        if not self.api:
            return 0

        cards = self.api.get_all_cards()
        card = cards.get(card_code)
        if not card:
            return 0

        expected_count = 0
        pack_code = card.get("pack_code")
        if pack_code in self.owned_packs:
            expected_count = card.get("quantity", 1)

        return expected_count

    def get_card_difference(self, card_code: str) -> int:
        """Get card difference from expected (positive = extra, negative = missing)."""
        return self.card_diffs.get(card_code, 0)

    def get_actual_card_count(self, card_code: str) -> int:
        """Get actual card count (expected + difference)."""
        expected = self.get_expected_card_count(card_code)
        diff = self.get_card_difference(card_code)
        return max(0, expected + diff)

    def modify_card_difference(self, card_code: str, delta: int) -> None:
        """Modify card difference by delta amount.

        Args:
            card_code: Card code to modify
            delta: Change in difference (positive or negative)
        """
        if not card_code:
            raise ValueError("Card code cannot be empty")

        current_diff = self.card_diffs.get(card_code, 0)
        new_diff = current_diff + delta

        if new_diff == 0:
            # Remove from dict if difference is zero
            self.card_diffs.pop(card_code, None)
        else:
            self.card_diffs[card_code] = new_diff

    def set_card_difference(self, card_code: str, difference: int) -> None:
        """Set card difference directly.

        Args:
            card_code: Card code to modify
            difference: New difference value (positive = extra, negative = missing)
        """
        if not card_code:
            raise ValueError("Card code cannot be empty")

        if difference == 0:
            self.card_diffs.pop(card_code, None)
        else:
            self.card_diffs[card_code] = difference

    def get_all_cards_with_differences(self) -> Dict[str, Dict[str, int]]:
        """Get all cards with their expected counts and differences.

        Returns:
            Dict mapping card codes to {'expected': int, 'difference': int, 'actual': int}
        """
        if not self.api:
            return {}

        cards = self.api.get_all_cards()
        result = {}

        # First, add all cards that have expected counts from owned packs
        for card_code, card in cards.items():
            pack_code = card.get("pack_code")
            if pack_code in self.owned_packs:
                expected = card.get("quantity", 1)
                difference = self.card_diffs.get(card_code, 0)
                actual = max(0, expected + difference)
                result[card_code] = {
                    "expected": expected,
                    "difference": difference,
                    "actual": actual,
                }

        # Then, add any cards that have differences but no expected count
        for card_code, difference in self.card_diffs.items():
            if card_code not in result:
                result[card_code] = {
                    "expected": 0,
                    "difference": difference,
                    "actual": max(0, difference),
                }

        return result

    def get_statistics(self) -> Dict[str, int]:
        """Calculate collection statistics.

        Returns:
            Dictionary with statistics:
            - owned_packs: Number of owned packs
            - unique_cards: Number of unique cards owned
            - total_cards: Total number of cards (counting duplicates)
            - missing_cards: Total number of missing cards
        """
        all_cards = self.get_all_cards()

        return {
            "owned_packs": len(self.owned_packs),
            "unique_cards": len(all_cards),
            "total_cards": sum(all_cards.values()),
            "missing_cards": sum(self.missing_cards.values()),
        }
