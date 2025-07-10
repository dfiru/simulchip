"""Decklist comparison functionality with enhanced type safety and patterns."""

from __future__ import annotations

# Standard library imports
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Final, List, Optional, Tuple

from .api.netrunnerdb import CardData, NetrunnerDBAPI, PackData
from .collection.manager import CollectionManager
from .utils import get_faction_symbol


@dataclass(frozen=True)
class CardInfo:
    """Detailed information about a card in a decklist."""

    code: str
    title: str
    pack_code: str
    pack_name: str
    type_code: str
    faction_code: str
    required_count: int
    owned_count: int
    missing_count: int

    @property
    def is_identity(self) -> bool:
        """Check if this card is an identity."""
        return self.type_code == "identity"

    @property
    def is_fully_owned(self) -> bool:
        """Check if all required copies are owned."""
        return self.missing_count == 0

    @property
    def ownership_ratio(self) -> float:
        """Get ratio of owned to required cards."""
        return (
            self.owned_count / self.required_count if self.required_count > 0 else 1.0
        )


@dataclass
class DecklistStats:
    """Statistics for a decklist comparison."""

    total_cards: int = 0
    owned_cards: int = 0
    missing_cards: int = 0
    unique_cards: int = 0
    unique_owned: int = 0
    unique_missing: int = 0

    @property
    def completion_percentage(self) -> float:
        """Calculate deck completion percentage."""
        return (
            (self.owned_cards / self.total_cards * 100)
            if self.total_cards > 0
            else 100.0
        )

    @property
    def is_complete(self) -> bool:
        """Check if all cards are owned."""
        return self.missing_cards == 0


@dataclass
class ComparisonResult:
    """Comprehensive result of comparing a decklist against a collection."""

    decklist_id: str
    decklist_name: str
    identity: CardInfo
    stats: DecklistStats
    cards_by_pack: Dict[str, List[CardInfo]] = field(default_factory=dict)
    cards_by_faction: Dict[str, List[CardInfo]] = field(default_factory=dict)
    missing_cards: List[CardInfo] = field(default_factory=list)
    owned_cards: List[CardInfo] = field(default_factory=list)
    all_cards: List[CardInfo] = field(default_factory=list)

    @property
    def identity_title(self) -> str:
        """Get identity title for backwards compatibility."""
        return self.identity.title

    @property
    def identity_faction(self) -> str:
        """Get identity faction for backwards compatibility."""
        return self.identity.faction_code

    @property
    def total_cards(self) -> int:
        """Get total cards for backwards compatibility."""
        return self.stats.total_cards

    @property
    def owned_cards_count(self) -> int:
        """Get owned cards count for backwards compatibility."""
        return self.stats.owned_cards

    @property
    def missing_cards_count(self) -> int:
        """Get missing cards count for backwards compatibility."""
        return self.stats.missing_cards

    @property
    def missing_by_pack(self) -> Dict[str, List[CardInfo]]:
        """Get missing cards grouped by pack for backwards compatibility."""
        return {
            pack: [card for card in cards if card.missing_count > 0]
            for pack, cards in self.cards_by_pack.items()
            if any(card.missing_count > 0 for card in cards)
        }

    @property
    def owned_by_pack(self) -> Dict[str, List[CardInfo]]:
        """Get owned cards grouped by pack for backwards compatibility."""
        return {
            pack: [card for card in cards if card.owned_count > 0]
            for pack, cards in self.cards_by_pack.items()
            if any(card.owned_count > 0 for card in cards)
        }


class DecklistComparisonError(Exception):
    """Custom exception for comparison errors."""


class DecklistComparer:
    """Compare decklists against local collection with validation."""

    IDENTITY_TYPE_CODE: Final[str] = "identity"

    def __init__(
        self, api_client: NetrunnerDBAPI, collection_manager: CollectionManager
    ) -> None:
        """Initialize comparer with validation.

        Args:
            api_client: NetrunnerDB API client
            collection_manager: Local collection manager

        Raises:
            TypeError: If arguments are of incorrect type
        """
        if not isinstance(api_client, NetrunnerDBAPI):
            raise TypeError(
                "api_client must be NetrunnerDBAPI instance, "
                f"got {type(api_client).__name__}"
            )
        if not isinstance(collection_manager, CollectionManager):
            raise TypeError(
                "collection_manager must be CollectionManager instance, "
                f"got {type(collection_manager).__name__}"
            )

        self.api = api_client
        self.collection = collection_manager

        # Ensure collection has API client for pack expansion
        if not self.collection.api:
            self.collection.api = api_client
            self.collection._expand_packs_to_cards()

    def compare_decklist(self, decklist_id: str) -> ComparisonResult:
        """Compare a decklist against local collection with comprehensive analysis.

        Args:
            decklist_id: NetrunnerDB decklist ID

        Returns:
            Detailed comparison result

        Raises:
            ValueError: If decklist_id is invalid
            DecklistComparisonError: If comparison fails
        """
        if not decklist_id:
            raise ValueError("Decklist ID cannot be empty")

        try:
            # Fetch decklist
            decklist_data = self.api.get_decklist(decklist_id)
            cards_in_deck = decklist_data.get("cards", {})

            if not cards_in_deck:
                raise DecklistComparisonError("Decklist has no cards")

            # Get all card and pack data
            all_cards = self.api.get_all_cards()
            all_packs = {p["code"]: p for p in self.api.get_all_packs()}

            # Process cards
            card_infos = self._create_card_infos(cards_in_deck, all_cards, all_packs)

            # Find identity
            identity = self._find_identity(card_infos)
            if not identity:
                raise DecklistComparisonError("No identity found in decklist")

            # Calculate statistics
            stats = self._calculate_stats(card_infos)

            # Group cards
            cards_by_pack = self._group_by_attribute(card_infos, lambda c: c.pack_name)
            cards_by_faction = self._group_by_attribute(
                card_infos, lambda c: c.faction_code
            )

            # Filter card lists
            missing_cards = [c for c in card_infos if c.missing_count > 0]
            owned_cards = [c for c in card_infos if c.owned_count > 0]

            return ComparisonResult(
                decklist_id=decklist_id,
                decklist_name=decklist_data.get("name", "Unnamed Deck"),
                identity=identity,
                stats=stats,
                cards_by_pack=cards_by_pack,
                cards_by_faction=cards_by_faction,
                missing_cards=missing_cards,
                owned_cards=owned_cards,
                all_cards=card_infos,
            )

        except Exception as e:
            if isinstance(e, (ValueError, DecklistComparisonError)):
                raise
            raise DecklistComparisonError(
                f"Failed to compare decklist {decklist_id}: {str(e)}"
            ) from e

    def _create_card_infos(
        self,
        cards_in_deck: Dict[str, int],
        all_cards: Dict[str, CardData],
        all_packs: Dict[str, PackData],
    ) -> List[CardInfo]:
        """Create CardInfo objects for all cards in decklist.

        Args:
            cards_in_deck: Card codes and counts from decklist
            all_cards: All card data
            all_packs: All pack data

        Returns:
            List of CardInfo objects
        """
        card_infos = []

        for card_code, required_count in sorted(cards_in_deck.items()):
            if required_count <= 0:
                continue

            card_data = all_cards.get(card_code)
            if not card_data:
                continue

            # Get ownership info
            owned_count = self.collection.get_card_count(card_code)
            missing_count = max(0, required_count - owned_count)

            # Get pack info
            pack_code = card_data.get("pack_code", "unknown")
            pack_data = all_packs.get(pack_code)  # type: Optional[PackData]

            card_info = CardInfo(
                code=card_code,
                title=card_data.get("title", "Unknown Card"),
                pack_code=pack_code,
                pack_name=(
                    pack_data.get("name", "Unknown Pack")
                    if pack_data
                    else "Unknown Pack"
                ),
                type_code=card_data.get("type_code", ""),
                faction_code=card_data.get("faction_code", ""),
                required_count=required_count,
                owned_count=min(owned_count, required_count),
                missing_count=missing_count,
            )

            card_infos.append(card_info)

        return card_infos

    def _find_identity(self, card_infos: List[CardInfo]) -> Optional[CardInfo]:
        """Find the identity card from card list.

        Args:
            card_infos: List of all cards

        Returns:
            Identity card or None
        """
        return next((card for card in card_infos if card.is_identity), None)

    def _calculate_stats(self, card_infos: List[CardInfo]) -> DecklistStats:
        """Calculate statistics from card list using functional approach.

        Args:
            card_infos: List of all cards

        Returns:
            Calculated statistics
        """
        # Exclude identity from stats
        non_identity_cards = [c for c in card_infos if not c.is_identity]

        return DecklistStats(
            total_cards=sum(c.required_count for c in non_identity_cards),
            owned_cards=sum(c.owned_count for c in non_identity_cards),
            missing_cards=sum(c.missing_count for c in non_identity_cards),
            unique_cards=len(non_identity_cards),
            unique_owned=sum(1 for c in non_identity_cards if c.owned_count > 0),
            unique_missing=sum(1 for c in non_identity_cards if c.missing_count > 0),
        )

    def _group_by_attribute(
        self, cards: List[CardInfo], key_func: Callable[[CardInfo], str]
    ) -> Dict[str, List[CardInfo]]:
        """Group cards by a given attribute using functional approach.

        Args:
            cards: List of cards to group
            key_func: Function to extract grouping key

        Returns:
            Dictionary of grouped cards
        """
        groups = defaultdict(list)
        for card in cards:
            key = key_func(card)
            groups[key].append(card)

        # Sort cards within each group by title
        return {
            key: sorted(cards, key=lambda c: c.title)
            for key, cards in sorted(groups.items())
        }

    def get_proxy_cards(self, comparison_result: ComparisonResult) -> List[CardInfo]:
        """Get list of cards that need proxies.

        Args:
            comparison_result: Result from compare_decklist

        Returns:
            List of cards that need proxies, sorted by pack and title
        """
        return sorted(
            comparison_result.missing_cards, key=lambda c: (c.pack_name, c.title)
        )

    def get_proxy_cards_for_generation(
        self, comparison_result: ComparisonResult, all_cards: bool = False
    ) -> List[CardInfo]:
        """Get list of cards for proxy generation with all_cards option.

        Args:
            comparison_result: Result from compare_decklist
            all_cards: If True, return all cards; if False, return only missing cards

        Returns:
            List of cards for proxy generation
        """
        if all_cards:
            return comparison_result.all_cards
        else:
            return self.get_proxy_cards(comparison_result)

    def format_comparison_report(self, comparison_result: ComparisonResult) -> str:
        """Format comparison result as a readable report.

        Args:
            comparison_result: Result from compare_decklist

        Returns:
            Formatted report string
        """
        lines = []
        faction_symbol = get_faction_symbol(comparison_result.identity_faction)

        # Header
        lines.extend(
            [
                f"{faction_symbol} {comparison_result.identity_title}",
                f"Decklist: {comparison_result.decklist_name}",
                f"ID: {comparison_result.decklist_id}",
                "",
                f"Total cards needed: {comparison_result.stats.total_cards}",
                f"Cards owned: {comparison_result.stats.owned_cards}",
                f"Cards missing: {comparison_result.stats.missing_cards}",
                f"Completion: {comparison_result.stats.completion_percentage:.1f}%",
                "",
            ]
        )

        if comparison_result.stats.is_complete:
            lines.append("✅ You have all cards needed for this deck!")
        else:
            lines.extend(["Missing cards by pack:", "-" * 50])

            # Get pack data and cycle mapping for sorting and display
            all_packs = {p["code"]: p for p in self.api.get_all_packs()}
            cycle_mapping = self.api.get_cycle_name_mapping()

            # Group packs by cycle and sort by release date
            packs_by_cycle: Dict[str, List[Dict[str, Any]]] = {}
            for pack_name, cards in comparison_result.missing_by_pack.items():
                missing_cards = [c for c in cards if c.missing_count > 0]
                if missing_cards:
                    pack_code = missing_cards[0].pack_code
                    pack_data = all_packs.get(pack_code)

                    if pack_data:
                        cycle_code = pack_data.get("cycle_code", "unknown")
                        cycle_name = cycle_mapping.get(cycle_code, "Unknown Cycle")
                        release_date = pack_data.get("date_release", "1900-01-01")

                        if cycle_name not in packs_by_cycle:
                            packs_by_cycle[cycle_name] = []

                        packs_by_cycle[cycle_name].append(
                            {
                                "name": pack_name,
                                "code": pack_code,
                                "release_date": release_date,
                                "missing_cards": missing_cards,
                            }
                        )

            # Sort cycles by their newest pack's release date (newest cycle first)
            def get_cycle_sort_key(cycle_item: Tuple[str, List[Dict[str, Any]]]) -> str:
                _, packs = cycle_item
                latest_date: str = max(pack["release_date"] for pack in packs)
                return latest_date

            sorted_cycles = sorted(
                packs_by_cycle.items(),
                key=get_cycle_sort_key,
                reverse=True,  # Newest cycle first
            )

            # Generate output grouped by cycle
            for cycle_name, packs in sorted_cycles:
                # Add cycle heading
                lines.append(f"\n=== {cycle_name} ===")

                # Sort packs within cycle by release date (newest first)
                sorted_packs = sorted(
                    packs, key=lambda p: p["release_date"], reverse=True
                )

                for pack in sorted_packs:
                    pack_header = f"\n{pack['name']} ({pack['release_date']}):"
                    lines.append(pack_header)

                    for card in sorted(pack["missing_cards"], key=lambda c: c.title):
                        lines.append(
                            f"  {card.missing_count}x {card.title} ({card.code})"
                        )

        return "\n".join(lines)

    def get_pack_requirements(
        self, comparison_result: ComparisonResult
    ) -> Dict[str, Dict[str, int]]:
        """Get pack requirements for missing cards.

        Args:
            comparison_result: Result from compare_decklist

        Returns:
            Dictionary mapping pack names to card requirements
        """
        pack_reqs: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"unique": 0, "total": 0}
        )

        for card in comparison_result.missing_cards:
            pack_reqs[card.pack_name]["unique"] += 1
            pack_reqs[card.pack_name]["total"] += card.missing_count

        return dict(pack_reqs)
