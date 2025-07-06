#!/usr/bin/env python3
"""
Simulchip Library Usage Examples.

This script demonstrates how to use the Simulchip library for:
- Managing your card collection
- Comparing decklists against your collection
- Generating proxy PDFs for missing cards

Run this script to see example usage, or copy parts of it to build your own tools.
"""

# Standard library imports
from pathlib import Path
from typing import Optional

# First-party imports
from simulchip.api.netrunnerdb import NetrunnerDBAPI
from simulchip.collection.manager import CollectionManager
from simulchip.comparison import ComparisonResult, DecklistComparer
from simulchip.pdf.generator import ProxyPDFGenerator
from simulchip.utils import extract_decklist_id


def example_collection_management() -> CollectionManager:
    """Demonstrate collection management."""
    print("=== Collection Management Example ===")

    # Initialize API and collection
    api = NetrunnerDBAPI()
    collection_path = Path("example_collection.toml")

    # Create a new collection manager
    collection = CollectionManager(collection_path, api)

    # Add some packs to your collection
    print("Adding packs to collection...")
    collection.add_pack("sg")  # System Gateway
    collection.add_pack("core")  # Core Set

    # Add individual cards
    print("Adding individual cards...")
    collection.add_card("01001", 3)  # Noise: Hacker Extraordinaire
    collection.add_card("01002", 2)  # Déjà Vu

    # Mark some cards as missing (lost/damaged)
    print("Marking cards as missing...")
    collection.add_missing_card("01001", 1)  # Lost 1 copy of Noise

    # Save the collection
    collection.save_collection()
    print(f"Collection saved to: {collection_path}")

    # Show collection stats
    all_cards = collection.get_all_cards()
    total_unique = len(all_cards)
    total_cards = sum(all_cards.values())

    print("\nCollection Statistics:")
    print(f"  Unique cards: {total_unique}")
    print(f"  Total cards: {total_cards}")
    print(f"  Missing cards: {sum(collection.missing_cards.values())}")

    return collection


def example_pack_browsing() -> None:
    """Demonstrate pack browsing."""
    print("\n=== Pack Browsing Example ===")

    api = NetrunnerDBAPI()

    # Get all available packs
    packs = api.get_all_packs()
    print(f"Total packs available: {len(packs)}")

    # Show the newest packs (limit to 5 for example)
    print("\nNewest 5 packs:")
    sorted_packs = sorted(
        packs, key=lambda p: p.get("date_release") or "1900-01-01", reverse=True
    )

    for pack in sorted_packs[:5]:
        print(
            f"  {pack['code']}: {pack['name']} ({pack.get('date_release', 'Unknown date')})"
        )

    # Get details about a specific pack
    sg_pack = api.get_pack_by_code("sg")
    if sg_pack:
        print("\nSystem Gateway details:")
        print(f"  Name: {sg_pack['name']}")
        print(f"  Code: {sg_pack['code']}")
        print(f"  Release: {sg_pack.get('date_release', 'Unknown')}")


def example_decklist_comparison() -> Optional[ComparisonResult]:
    """Demonstrate decklist comparison."""
    print("\n=== Decklist Comparison Example ===")

    # Use the collection we created earlier
    api = NetrunnerDBAPI()
    collection_path = Path("example_collection.toml")

    if not collection_path.exists():
        print("No collection found. Run collection management example first.")
        return None

    collection = CollectionManager(collection_path, api)
    comparer = DecklistComparer(api, collection)

    # Example NetrunnerDB decklist URL - replace with a real one for testing
    decklist_url = "https://netrunnerdb.com/en/decklist/7a9e2d43-bd55-45d0-bd2c-99cad2d17d4c/aggravated-assault-zahya"

    # Extract decklist ID
    decklist_id = extract_decklist_id(decklist_url)
    if not decklist_id:
        print(f"Invalid decklist URL: {decklist_url}")
        return None

    print(f"Comparing decklist {decklist_id}...")

    # Perform the comparison
    result = comparer.compare_decklist(decklist_id)

    # Display results
    print(f"\nDecklist: {result.decklist_name}")
    print(f"Identity: {result.identity}")
    print(f"Total cards needed: {result.stats.total_cards}")
    print(f"Cards owned: {result.stats.owned_cards}")
    print(f"Cards missing: {result.stats.missing_cards}")

    # Show detailed missing cards report
    if result.stats.missing_cards > 0:
        print("\nDetailed missing cards report:")
        report = comparer.format_comparison_report(result)
        print(report)

    return result


def example_pdf_generation(comparison_result: Optional[ComparisonResult]) -> None:
    """Demonstrate PDF generation."""
    print("\n=== PDF Generation Example ===")

    if not comparison_result or comparison_result.stats.missing_cards == 0:
        print("No missing cards to generate proxies for.")
        return

    # Initialize PDF generator
    api = NetrunnerDBAPI()
    pdf_generator = ProxyPDFGenerator(api, page_size="letter")

    # Get proxy cards from comparison result
    comparer = DecklistComparer(
        api, CollectionManager(Path("example_collection.toml"), api)
    )
    proxy_cards = comparer.get_proxy_cards(comparison_result)

    # Generate PDF
    output_path = Path("example_proxies.pdf")
    print(f"Generating PDF with {len(proxy_cards)} proxy cards...")

    pdf_generator.generate_proxy_pdf(
        proxy_cards,
        output_path,
        download_images=True,  # Set to False for faster generation without images
        group_by_pack=True,  # Group cards by pack in PDF
    )

    print(f"PDF saved to: {output_path}")


def example_custom_workflow() -> None:
    """Demonstrate custom workflow."""
    print("\n=== Custom Workflow Example ===")

    # This shows how you might build a custom script for your specific needs
    api = NetrunnerDBAPI()

    # Get all cards from a specific pack
    all_cards = api.get_all_cards()
    sg_cards = {
        code: card for code, card in all_cards.items() if card.get("pack_code") == "sg"
    }

    print(f"System Gateway contains {len(sg_cards)} cards:")

    # Show cards by faction
    factions: dict[str, list] = {}
    for card in sg_cards.values():
        faction = card.get("faction_code", "unknown")
        if faction not in factions:
            factions[faction] = []
        factions[faction].append(card)

    for faction, cards in factions.items():
        print(f"  {faction}: {len(cards)} cards")

    # You could extend this to:
    # - Build automatic collection updates
    # - Create custom reports
    # - Integrate with other tools
    # - Build web interfaces
    # - Create automated proxy generation pipelines


def main() -> None:
    """Run all examples."""
    print("Simulchip Library Examples")
    print("=" * 50)

    # Run examples in order
    example_collection_management()
    example_pack_browsing()
    comparison_result = example_decklist_comparison()
    example_pdf_generation(comparison_result)
    example_custom_workflow()

    print("\n" + "=" * 50)
    print("Examples complete!")
    print("\nFiles created:")
    print("  - example_collection.toml (your card collection)")
    print("  - example_proxies.pdf (proxy cards PDF, if missing cards found)")
    print("\nNext steps:")
    print("  1. Modify example_collection.toml to match your actual collection")
    print("  2. Replace the example decklist URL with real NetrunnerDB URLs")
    print("  3. Copy parts of this script to build your own tools")
    print("  4. See the README for library API documentation")


if __name__ == "__main__":
    main()
