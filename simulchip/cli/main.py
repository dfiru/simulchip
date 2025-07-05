"""Command-line interface for Simulchip.

This module provides the main CLI functionality for comparing NetrunnerDB
decklists against your local card collection and generating proxy PDFs.
"""

# Standard library imports
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Third-party imports
import fire  # type: ignore[import-untyped]

from ..api.netrunnerdb import NetrunnerDBAPI, PackData
from ..cache import CacheManager
from ..collection.manager import CollectionManager
from ..comparison import DecklistComparer
from ..pdf.generator import ProxyPDFGenerator
from ..utils import (
    extract_decklist_id,
    get_faction_short_name,
    sanitize_filename,
)


class SimulchipCLI:
    """Main CLI class for Simulchip.

    Provides commands for managing your card collection, comparing decklists,
    and generating proxy PDFs for missing cards.

    Examples:
        Basic usage::

            # Initialize a new collection
            simulchip init

            # Add cards to collection
            simulchip add-pack gateway
            simulchip add-card "hedge-fund:3"

            # Compare and generate proxies
            simulchip compare https://netrunnerdb.com/en/decklist/12345
    """

    def __init__(
        self,
        api: Optional[NetrunnerDBAPI] = None,
        cache_manager: Optional[CacheManager] = None,
    ):
        """Initialize the CLI.

        Args:
            api: Optional NetrunnerDB API client instance. If not provided,
                a new instance will be created with default settings.
            cache_manager: Optional cache manager instance. If not provided,
                a new instance will be created with default cache directory.
        """
        self._api = api
        self._cache_manager = cache_manager

    def compare(
        self,
        decklist_url: str,
        collection: Optional[str] = None,
        output: Optional[str] = None,
        no_images: bool = False,
        group_by_pack: bool = False,
        page_size: str = "letter",
    ) -> None:
        """Compare a NetrunnerDB decklist against your collection.

        Fetches a decklist from NetrunnerDB, compares it against your local
        collection, and optionally generates a PDF of proxy cards for any
        missing cards.

        Args:
            decklist_url: Full NetrunnerDB decklist URL.
            collection: Path to collection file (default: collection.toml).
            output: Output PDF filename. If not specified, generates a name
                based on the deck name.
            no_images: If True, generates proxies without card images (text only).
            group_by_pack: If True, groups missing cards by pack in the output.
            page_size: PDF page size, either "letter" (8.5x11") or "a4".

        Examples:
            Basic comparison::

                simulchip compare https://netrunnerdb.com/en/decklist/12345

            Generate PDF with custom name::

                simulchip compare https://netrunnerdb.com/en/decklist/12345 -o proxies.pdf

        Raises:
            ValueError: If the decklist URL is invalid or the deck cannot be found.
            RuntimeError: If there's an error generating the PDF.

        Args:
            decklist_url: Full NetrunnerDB URL
            collection: Path to collection file (TOML)
            output: Output PDF file path
            no_images: Generate PDF without downloading card images
            group_by_pack: Group cards by pack in the PDF
            page_size: PDF page size ('letter' or 'a4')
        """
        try:
            # Extract decklist ID from URL
            decklist_id = extract_decklist_id(decklist_url)
            if not decklist_id:
                print(f"Invalid decklist URL: {decklist_url}", file=sys.stderr)
                print("Expected formats:", file=sys.stderr)
                print(
                    "  - https://netrunnerdb.com/en/decklist/<id>/deck-name",
                    file=sys.stderr,
                )
                print("  - https://netrunnerdb.com/decklist/view/<id>", file=sys.stderr)
                sys.exit(1)

            # Initialize components
            api = self._api or NetrunnerDBAPI()

            collection_path = Path(collection) if collection else None
            if collection_path and not collection_path.exists():
                print(f"Collection file not found: {collection_path}", file=sys.stderr)
                sys.exit(1)

            collection_manager = CollectionManager(collection_path, api)
            comparer = DecklistComparer(api, collection_manager)

            # Perform comparison
            print(f"Fetching decklist {decklist_id}...")
            result = comparer.compare_decklist(decklist_id)

            # Display results
            print("\n" + comparer.format_comparison_report(result))

            # Generate PDF if requested
            if output and result.stats.missing_cards > 0:
                # If output is a directory, generate filename from deck info
                output_path = Path(output)
                if output_path.is_dir() or not output_path.suffix:
                    # Clean deck name for filename
                    safe_deck_name = sanitize_filename(result.decklist_name)

                    # Create filename: faction_deckname.pdf
                    faction_short = get_faction_short_name(result.identity_faction)
                    filename = f"{faction_short}_{safe_deck_name}.pdf"

                    if output_path.is_dir():
                        output_path = output_path / filename
                    else:
                        output_path = output_path.parent / filename

                pdf_gen = ProxyPDFGenerator(api, page_size)

                print(
                    f"\nGenerating PDF with {result.stats.missing_cards} proxy cards..."
                )
                proxy_cards = comparer.get_proxy_cards(result)
                pdf_gen.generate_proxy_pdf(
                    proxy_cards,
                    output_path,
                    download_images=not no_images,
                    group_by_pack=group_by_pack,
                )
                print(f"PDF saved to: {output_path}")

        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    def init(self, collection: str) -> None:
        """Initialize a new collection file.

        Args:
            collection: Path to collection file to create/update
        """
        collection_path = Path(collection)

        if collection_path.exists():
            response = input(
                f"File {collection_path} already exists. Overwrite? (y/N): "
            )
            if response.lower() != "y":
                print("Aborted.")
                return

        # Ensure correct extension
        if not collection_path.suffix:
            collection_path = collection_path.with_suffix(".toml")

        # Create empty collection
        manager = CollectionManager(collection_path, None)
        manager.save_collection()

        print(f"Created empty collection file: {collection_path}")
        print("\nExample format:")
        print("# Define owned packs (all cards from these packs)")
        print("packs = [")
        print('  "core",  # Core Set')
        print('  "wla",   # What Lies Ahead')
        print('  "sg",    # System Gateway')
        print("]")
        print("")
        print("# Define individual cards (overrides pack ownership)")
        print("[cards]")
        print('"01001" = 3  # Noise: Hacker Extraordinaire')
        print('"01002" = 2  # Déjà Vu')
        print("")
        print("# Track missing/lost cards from owned packs")
        print("[missing]")
        print('"34080" = 1  # Lost to Cupellation!')

    def list_packs(self) -> None:
        """List all available Netrunner packs."""
        api = self._api or NetrunnerDBAPI()
        packs = api.get_all_packs()

        # Group by cycle
        cycles: Dict[str, List[PackData]] = {}
        for pack in packs:
            cycle_code = pack.get("cycle_code", "other")
            if cycle_code not in cycles:
                cycles[cycle_code] = []
            cycles[cycle_code].append(pack)

        # Sort cycles by the most recent release date in each cycle (reverse chronological)
        def get_cycle_latest_release(cycle_code: str) -> str:
            cycle_packs = cycles[cycle_code]
            if not cycle_packs:
                return "1900-01-01"  # Default for cycles with no packs
            # Get the latest release date in the cycle, handling None values
            release_dates = [
                pack.get("date_release") or "1900-01-01" for pack in cycle_packs
            ]
            latest_date = max(release_dates)
            return latest_date

        sorted_cycles = sorted(
            cycles.keys(), key=get_cycle_latest_release, reverse=True
        )

        # Display packs
        for cycle_code in sorted_cycles:
            cycle_packs = cycles[cycle_code]
            if cycle_packs:
                # Get cycle name from first pack
                cycle_name = cycle_packs[0].get("cycle", cycle_code)
                print(f"\n{cycle_name}:")
                # Sort packs within cycle by release date (reverse chronological)
                for pack in sorted(
                    cycle_packs,
                    key=lambda p: p.get("date_release") or "1900-01-01",
                    reverse=True,
                ):
                    print(f"  {pack['code']: <20} {pack['name']}")

    def add_pack(self, collection: str, pack_code: str) -> None:
        """Add all cards from a pack to your collection.

        Args:
            collection: Path to collection file
            pack_code: Pack code to add
        """
        collection_path = Path(collection)
        api = self._api or NetrunnerDBAPI()

        # Verify pack exists
        pack = api.get_pack_by_code(pack_code)
        if not pack:
            print(f"Pack not found: {pack_code}", file=sys.stderr)
            print("Use 'simulchip list_packs' to see available packs")
            sys.exit(1)

        manager = CollectionManager(collection_path, api)
        manager.add_pack(pack_code)
        manager.save_collection()

        print(f"Added pack: {pack['name']} ({pack_code})")

        # Show pack stats
        all_cards = api.get_all_cards()
        pack_cards = [c for c in all_cards.values() if c.get("pack_code") == pack_code]
        print(f"Added {len(pack_cards)} unique cards (3 copies each)")

    def remove_pack(self, collection: str, pack_code: str) -> None:
        """Remove all cards from a pack from your collection.

        Args:
            collection: Path to collection file
            pack_code: Pack code to remove
        """
        collection_path = Path(collection)
        api = self._api or NetrunnerDBAPI()
        manager = CollectionManager(collection_path, api)

        if not manager.has_pack(pack_code):
            print(f"Pack not in collection: {pack_code}", file=sys.stderr)
            sys.exit(1)

        # Get pack info
        pack = api.get_pack_by_code(pack_code)
        pack_name = pack["name"] if pack else pack_code

        manager.remove_pack(pack_code)
        manager.save_collection()

        print(f"Removed pack: {pack_name} ({pack_code})")

    def add(self, collection: str, card_code: str, count: int = 1) -> None:
        """Add cards to your collection.

        Args:
            collection: Path to collection file
            card_code: Card code to add
            count: Number of copies to add
        """
        collection_path = Path(collection)
        api = self._api or NetrunnerDBAPI()
        manager = CollectionManager(collection_path, api)

        # Verify card exists
        card = api.get_card_by_code(card_code)
        if not card:
            print(f"Card not found: {card_code}", file=sys.stderr)
            sys.exit(1)

        # Add to collection
        manager.add_card(card_code, count)
        manager.save_collection()

        total = manager.get_card_count(card_code)
        print(f"Added {count}x {card['title']} ({card_code})")
        print(f"Total owned: {total}")

    def remove(self, collection: str, card_code: str, count: int = 1) -> None:
        """Remove cards from your collection.

        Args:
            collection: Path to collection file
            card_code: Card code to remove
            count: Number of copies to remove
        """
        collection_path = Path(collection)
        api = self._api or NetrunnerDBAPI()
        manager = CollectionManager(collection_path, api)

        # First try to remove from missing cards, then from collection
        missing_count = manager.missing_cards.get(card_code, 0)
        if missing_count > 0:
            removed_from_missing = min(count, missing_count)
            manager.remove_missing_card(card_code, removed_from_missing)
            count -= removed_from_missing
            print(f"Removed {removed_from_missing}x {card_code} from missing list")

        # Remove remaining count from collection
        if count > 0:
            manager.remove_card(card_code, count)
            print(f"Removed {count}x {card_code} from collection")

        manager.save_collection()

        remaining = manager.get_card_count(card_code)
        print(f"Available count: {remaining}")

    def mark_missing(self, collection: str, card_code: str, count: int = 1) -> None:
        """Mark cards as missing/lost from your collection.

        Args:
            collection: Path to collection file
            card_code: Card code to mark as missing
            count: Number of copies to mark as missing
        """
        collection_path = Path(collection)
        api = self._api or NetrunnerDBAPI()
        manager = CollectionManager(collection_path, api)

        # Verify card exists
        card = api.get_card_by_code(card_code)
        if not card:
            print(f"Card not found: {card_code}", file=sys.stderr)
            sys.exit(1)

        # Mark as missing
        manager.add_missing_card(card_code, count)
        manager.save_collection()

        remaining = manager.get_card_count(card_code)
        print(f"Marked {count}x {card['title']} ({card_code}) as missing")
        print(f"Available count: {remaining}")

    def found(self, collection: str, card_code: str, count: int = 1) -> None:
        """Mark missing cards as found.

        Args:
            collection: Path to collection file
            card_code: Card code to mark as found
            count: Number of copies to mark as found
        """
        collection_path = Path(collection)
        api = self._api or NetrunnerDBAPI()
        manager = CollectionManager(collection_path, api)

        # Remove from missing
        manager.remove_missing_card(card_code, count)
        manager.save_collection()

        remaining = manager.get_card_count(card_code)
        print(f"Marked {count}x {card_code} as found")
        print(f"Available count: {remaining}")

    def stats(self, collection: str) -> None:
        """Show collection statistics.

        Args:
            collection: Path to collection file
        """
        collection_path = Path(collection)
        api = self._api or NetrunnerDBAPI()
        manager = CollectionManager(collection_path, api)

        # Get statistics
        all_cards = manager.get_all_cards()
        total_unique = len(all_cards)
        total_cards = sum(all_cards.values())

        print("Collection Statistics:")
        print(f"  Unique cards: {total_unique}")
        print(f"  Total cards: {total_cards}")

        # Show missing cards
        if manager.missing_cards:
            total_missing = sum(manager.missing_cards.values())
            print(f"  Missing cards: {total_missing}")
            print("\nMissing cards detail:")
            for card_code, count in sorted(manager.missing_cards.items()):
                card = api.get_card_by_code(card_code)
                card_name = card["title"] if card else card_code
                print(f"  - {count}x {card_name} ({card_code})")

        # Show owned packs
        owned_packs = manager.get_owned_packs()
        if owned_packs:
            print(f"\nOwned packs ({len(owned_packs)}):")
            for pack_code in owned_packs:
                pack = api.get_pack_by_code(pack_code)
                pack_name = pack["name"] if pack else pack_code
                print(f"  - {pack_name} ({pack_code})")

        # Pack summary
        pack_summary = manager.get_pack_summary(api)
        print("\nCards by pack:")
        for pack_code, stats in sorted(pack_summary.items()):
            percentage = (
                (stats["owned"] / stats["total"] * 100) if stats["total"] > 0 else 0
            )
            pack = api.get_pack_by_code(pack_code)
            pack_name = pack["name"] if pack else pack_code
            print(
                f"  {pack_name}: {stats['owned']}/{stats['total']} ({percentage:.1f}%)"
            )

    def cache(self, clear: bool = False, stats: bool = False) -> None:
        """Manage the cache for card data and images.

        Args:
            clear: Clear all cached data
            stats: Show cache statistics
        """
        cache_mgr = self._cache_manager or CacheManager()

        if clear:
            cache_mgr.clear_cache()
            print("Cache cleared successfully")
        elif stats:
            cache_stats = cache_mgr.get_cache_stats()
            print("Cache Statistics:")
            print(f"  Cards cached: {'Yes' if cache_stats['cards_cached'] else 'No'}")
            print(f"  Packs cached: {'Yes' if cache_stats['packs_cached'] else 'No'}")
            print(f"  Images cached: {cache_stats['images_cached']}")
            print(f"  Cache size: {cache_stats['cache_size_mb']} MB")
        else:
            print("Use --clear to clear cache or --stats to view statistics")


def main() -> None:
    """Launch the CLI application."""
    fire.Fire(SimulchipCLI)


if __name__ == "__main__":
    main()
