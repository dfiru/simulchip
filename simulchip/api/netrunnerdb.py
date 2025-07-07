"""NetrunnerDB API client module.

This module provides a client for interacting with the NetrunnerDB API
to fetch card data, pack information, and decklists.

Classes:
    NetrunnerDBAPI: Main API client class.
    APIError: Custom exception for API-related errors.

TypeDict Classes:
    CardData: Type definition for card data.
    PackData: Type definition for pack data.
    DecklistData: Type definition for decklist data.
"""

from __future__ import annotations

# Standard library imports
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Final, List, Optional, TypedDict

# Third-party imports
import requests
from requests.exceptions import RequestException

from ..cache import CacheManager


class CardData(TypedDict, total=False):
    """Type definition for card data from NetrunnerDB.

    Attributes:
        code: Unique card identifier (e.g., "01001").
        title: Card name.
        type_code: Card type code (e.g., "agenda", "asset", "ice").
        faction_code: Faction code (e.g., "haas-bioroid", "shaper").
        pack_code: Pack code where the card was released.
        quantity: Number of copies in a pack.
        deck_limit: Maximum copies allowed in a deck.
        image_url: URL to the card image.
    """

    code: str
    title: str
    type_code: str
    faction_code: str
    pack_code: str
    quantity: int
    deck_limit: int
    image_url: str


class PackData(TypedDict):
    """Type definition for pack data from NetrunnerDB.

    Attributes:
        code: Unique pack identifier (e.g., "core").
        name: Full pack name.
        position: Pack position in the cycle.
        cycle_code: Cycle code this pack belongs to.
        cycle: Full cycle name.
        date_release: Release date in YYYY-MM-DD format.
    """

    code: str
    name: str
    position: int
    cycle_code: str
    cycle: str
    date_release: str


class DecklistData(TypedDict):
    """Type definition for decklist data from NetrunnerDB.

    Attributes:
        id: Unique decklist identifier.
        name: Deck name.
        description: Deck description (may include HTML).
        cards: Dictionary mapping card codes to quantities.
    """

    id: str
    name: str
    description: str
    cards: Dict[str, int]


@dataclass(frozen=True)
class APIError(Exception):
    """Custom exception for API-related errors.

    Attributes:
        message: Error message describing what went wrong.
        status_code: HTTP status code if applicable.
        url: The URL that caused the error if applicable.
    """

    message: str
    status_code: Optional[int] = None
    url: Optional[str] = None


class NetrunnerDBAPI:
    """Client for interacting with NetrunnerDB API.

    Provides methods to fetch card data, pack information, and decklists
    from NetrunnerDB. Implements rate limiting and caching to be respectful
    of the API.

    Attributes:
        BASE_URL: Base URL for the NetrunnerDB API.
        DEFAULT_RATE_LIMIT: Default delay between API calls (0.5 seconds).
        rate_limit_delay: Configured delay between API calls.
        cache: Cache manager instance for storing API responses.

    Examples:
        Basic usage::

            api = NetrunnerDBAPI()
            cards = api.get_all_cards()
            decklist = api.get_decklist("12345")
    """

    BASE_URL: Final[str] = "https://netrunnerdb.com/api/2.0/public"
    DEFAULT_RATE_LIMIT: Final[float] = 0.5

    def __init__(
        self,
        rate_limit_delay: float = DEFAULT_RATE_LIMIT,
        cache_dir: Optional[Path] = None,
    ) -> None:
        """Initialize API client with validation.

        Args:
            rate_limit_delay: Delay between API calls in seconds
            cache_dir: Directory for cache storage

        Raises:
            ValueError: If rate_limit_delay is negative
        """
        if rate_limit_delay < 0:
            raise ValueError(
                f"rate_limit_delay must be non-negative, got {rate_limit_delay}"
            )

        self.rate_limit_delay = rate_limit_delay
        self._last_request_time: float = 0
        self._cards_cache: Optional[Dict[str, CardData]] = None
        self._packs_cache: Optional[List[PackData]] = None
        self._cycles_cache: Optional[Dict[str, str]] = None
        self.cache = CacheManager(cache_dir)

    def _rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time

        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)

        self._last_request_time = time.time()

    def _make_request(self, endpoint: str) -> Dict[str, Any]:
        """Make a request to the NetrunnerDB API with error handling.

        Args:
            endpoint: API endpoint path

        Returns:
            JSON response data

        Raises:
            APIError: If request fails or returns invalid data
        """
        if not endpoint:
            raise APIError("Endpoint cannot be empty")

        self._rate_limit()
        url = f"{self.BASE_URL}/{endpoint}"

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()
            if not isinstance(data, dict):
                raise APIError(
                    f"Expected dict response, got {type(data).__name__}", url=url
                )

            return data

        except RequestException as e:
            status_code = (
                getattr(e.response, "status_code", None)
                if hasattr(e, "response")
                else None
            )
            raise APIError(
                f"Request failed: {str(e)}", status_code=status_code, url=url
            ) from e
        except ValueError as e:
            raise APIError(f"Invalid JSON response: {str(e)}", url=url) from e

    def get_all_cards(self) -> Dict[str, CardData]:
        """Fetch all cards from NetrunnerDB with caching.

        Returns:
            Dictionary mapping card codes to card data

        Raises:
            APIError: If API request fails
        """
        if self._cards_cache is not None:
            return self._cards_cache

        # Try cache first
        cached_data = self.cache.get_cached_cards()
        if cached_data:
            self._cards_cache = cached_data
            return self._cards_cache

        # Fetch from API
        try:
            response = self._make_request("cards")

            if "data" not in response:
                raise APIError("Missing 'data' field in cards response")

            if not isinstance(response["data"], list):
                raise APIError(
                    f"Expected list in 'data' field, got {type(response['data']).__name__}"
                )

            # Build cards dictionary with validation
            cards: Dict[str, CardData] = {}
            for card in response["data"]:
                if not isinstance(card, dict):
                    continue

                code = card.get("code")
                if not code:
                    continue

                # Cast to CardData since we know it matches the structure
                cards[code] = card  # type: ignore[assignment]

            self._cards_cache = cards
            self.cache.cache_cards(cards)

            return cards

        except APIError:
            raise
        except Exception as e:
            raise APIError(f"Failed to process cards data: {str(e)}") from e

    def get_all_packs(self) -> List[PackData]:
        """Fetch all pack information with caching.

        Returns:
            List of pack data

        Raises:
            APIError: If API request fails
        """
        if self._packs_cache is not None:
            return self._packs_cache

        # Try cache first
        cached_data = self.cache.get_cached_packs()
        if cached_data:
            self._packs_cache = cached_data  # type: ignore[assignment]
            return cached_data  # type: ignore[return-value]

        # Fetch from API
        try:
            response = self._make_request("packs")

            if "data" not in response:
                raise APIError("Missing 'data' field in packs response")

            if not isinstance(response["data"], list):
                raise APIError(
                    f"Expected list in 'data' field, got {type(response['data']).__name__}"
                )

            packs: List[PackData] = response["data"]
            self._packs_cache = packs
            self.cache.cache_packs(response["data"])

            return packs

        except APIError:
            raise
        except Exception as e:
            raise APIError(f"Failed to process packs data: {str(e)}") from e

    def get_packs_by_release_date(self, newest_first: bool = True) -> List[PackData]:
        """Get all packs sorted by release date with enriched cycle names.

        Args:
            newest_first: If True, sort newest first. If False, sort oldest first.

        Returns:
            List of pack data sorted by release date

        Raises:
            APIError: If API request fails
        """
        packs = self.get_all_packs()

        # Get cycle name mapping to enrich pack data
        cycle_names = self.get_cycle_name_mapping()

        # Filter valid packs and sort by release date
        valid_packs = []
        for pack in packs:
            if pack.get("code") and pack.get("name"):
                # Enrich with full cycle name if we have the cycle code
                if "cycle_code" in pack and pack["cycle_code"] in cycle_names:
                    pack = pack.copy()  # Make a copy to avoid modifying cached data
                    pack["cycle"] = cycle_names[pack["cycle_code"]]

                # Use empty string for missing dates to sort them consistently
                date_release = pack.get("date_release") or ""
                valid_packs.append((date_release, pack))

        # Sort by date, putting empty dates at the end when newest_first=True
        if newest_first:
            valid_packs.sort(key=lambda x: x[0] if x[0] else "0000", reverse=True)
        else:
            valid_packs.sort(key=lambda x: x[0] if x[0] else "9999", reverse=False)

        return [pack for _, pack in valid_packs]

    def get_cycle_name_mapping(self) -> Dict[str, str]:
        """Fetch cycle code to name mapping with caching.

        Returns:
            Dictionary mapping cycle codes to cycle names

        Raises:
            APIError: If API request fails
        """
        if self._cycles_cache is not None:
            return self._cycles_cache

        try:
            response = self._make_request("cycles")

            if "data" not in response:
                raise APIError("Missing 'data' field in cycles response")

            if not isinstance(response["data"], list):
                raise APIError(
                    f"Expected list in 'data' field, got {type(response['data']).__name__}"
                )

            # Create mapping from cycle code to cycle name
            cycles_mapping = {}
            for cycle_data in response["data"]:
                if isinstance(cycle_data, dict):
                    code = cycle_data.get("code")
                    name = cycle_data.get("name")
                    if code and name:
                        cycles_mapping[code] = name

            self._cycles_cache = cycles_mapping
            return cycles_mapping

        except APIError:
            raise
        except Exception as e:
            raise APIError(f"Failed to process cycles data: {str(e)}") from e

    def get_decklist(self, decklist_id: str) -> DecklistData:
        """Fetch a specific decklist by ID with validation.

        Args:
            decklist_id: NetrunnerDB decklist ID

        Returns:
            Decklist data including cards

        Raises:
            ValueError: If decklist_id is invalid
            APIError: If API request fails or decklist not found
        """
        if not decklist_id:
            raise ValueError("Decklist ID cannot be empty")

        if not decklist_id.replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"Invalid decklist ID format: {decklist_id}")

        try:
            response = self._make_request(f"decklist/{decklist_id}")

            if "data" not in response:
                raise APIError("Missing 'data' field in decklist response")

            if not isinstance(response["data"], list) or not response["data"]:
                raise APIError(f"Decklist not found: {decklist_id}")

            decklist_data: DecklistData = response["data"][0]
            return decklist_data

        except APIError:
            raise
        except Exception as e:
            raise APIError(f"Failed to fetch decklist {decklist_id}: {str(e)}") from e

    def get_card_by_code(self, card_code: str) -> Optional[CardData]:
        """Get a specific card by its code with validation.

        Args:
            card_code: Card code (e.g., "01001")

        Returns:
            Card data or None if not found

        Raises:
            ValueError: If card_code is invalid format
        """
        if not card_code:
            raise ValueError("Card code cannot be empty")

        if not card_code.isdigit() or len(card_code) != 5:
            raise ValueError(f"Card code must be 5 digits, got: {card_code}")

        cards = self.get_all_cards()
        return cards.get(card_code)

    def get_pack_by_code(self, pack_code: str) -> Optional[PackData]:
        """Get a specific pack by its code using functional approach.

        Args:
            pack_code: Pack code (e.g., "core")

        Returns:
            Pack data or None if not found

        Raises:
            ValueError: If pack_code is invalid
        """
        if not pack_code:
            raise ValueError("Pack code cannot be empty")

        if not pack_code.replace("_", "").replace("-", "").isalnum():
            raise ValueError(f"Invalid pack code format: {pack_code}")

        packs = self.get_all_packs()

        # Functional approach with next()
        return next((pack for pack in packs if pack.get("code") == pack_code), None)

    def get_cards_by_pack(self, pack_code: str) -> List[CardData]:
        """Get all cards from a specific pack.

        Args:
            pack_code: Pack code to filter by

        Returns:
            List of cards in the pack

        Raises:
            ValueError: If pack_code is invalid
        """
        if not pack_code:
            raise ValueError("Pack code cannot be empty")

        cards = self.get_all_cards()

        # Functional filter approach
        return [card for card in cards.values() if card.get("pack_code") == pack_code]

    def refresh_cache(self) -> None:
        """Force refresh of all cached data."""
        self._cards_cache = None
        self._packs_cache = None
        self.cache.clear_cache()
