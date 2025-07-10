"""Proxy sheet generation commands."""

# Standard library imports
from pathlib import Path
from typing import Any, Optional

# Third-party imports
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# First-party imports
from simulchip.api.netrunnerdb import NetrunnerDBAPI
from simulchip.cli_utils import (
    ensure_output_directory,
    get_proxy_generation_message,
    resolve_collection_path,
    should_generate_proxies,
)
from simulchip.collection.operations import get_or_create_manager
from simulchip.comparison import DecklistComparer
from simulchip.display import get_completion_color
from simulchip.paths import generate_default_output_path
from simulchip.pdf.generator import ProxyPDFGenerator
from simulchip.utils import extract_decklist_id

# Initialize console for rich output
console = Console()

# This module exports the proxy command function directly
# No need for a Typer app since we're making proxy a direct command


# Default options for typer to avoid B008 flake8 warnings
OUTPUT_OPTION = typer.Option(None, "--output", "-o", help="Custom output path for PDF")
COLLECTION_OPTION = typer.Option(
    None, "--collection", "-c", help="Path to collection file"
)
ALL_CARDS_OPTION = typer.Option(
    False, "--all", "-a", help="Generate proxies for all cards, not just missing"
)
NO_IMAGES_OPTION = typer.Option(
    False, "--no-images", help="Skip downloading card images"
)
PAGE_SIZE_OPTION = typer.Option(
    "letter", "--page-size", "-p", help="Page size (letter, a4, legal)"
)
DETAILED_OPTION = typer.Option(
    False, "--detailed", "-d", help="Show detailed comparison"
)
LIMIT_OPTION = typer.Option(
    None, "--limit", "-l", help="Limit number of URLs to process"
)
ALTERNATE_PRINTS_OPTION = typer.Option(
    False, "--alternate-prints", help="Interactively select alternate printings"
)
COMPARE_ONLY_OPTION = typer.Option(
    False,
    "--compare-only",
    help="Only compare deck against collection, don't generate PDF",
)


def proxy(
    decklist_url: str,
    output: Optional[Path] = OUTPUT_OPTION,
    collection_file: Optional[Path] = COLLECTION_OPTION,
    all_cards: bool = ALL_CARDS_OPTION,
    no_images: bool = NO_IMAGES_OPTION,
    page_size: str = PAGE_SIZE_OPTION,
    alternate_prints: bool = ALTERNATE_PRINTS_OPTION,
    compare_only: bool = COMPARE_ONLY_OPTION,
    detailed: bool = DETAILED_OPTION,
) -> Any:
    """Generate proxy sheets for a decklist, or just compare it against your collection."""
    # Extract decklist ID
    decklist_id = extract_decklist_id(decklist_url)
    if not decklist_id:
        console.print(f"[red]✗ Invalid decklist URL: {decklist_url}[/red]")
        raise typer.Exit(1)

    # Initialize API and collection
    api = NetrunnerDBAPI()

    collection_file = resolve_collection_path(collection_file)

    # Create collection manager using library function
    manager = get_or_create_manager(collection_file, api, all_cards)

    # Create comparer
    comparer = DecklistComparer(api, manager)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        # Compare decklist
        progress.add_task(description="Fetching decklist...", total=None)
        try:
            result = comparer.compare_decklist(decklist_id)
        except Exception as e:
            console.print(f"[red]✗ Error fetching decklist: {e}[/red]")
            raise typer.Exit(1)

    # If compare_only is True, display results and exit
    if compare_only:
        # Display results
        console.print(f"\n[bold]Deck: {result.decklist_name}[/bold]")
        console.print(f"Identity: [yellow]{result.identity.title}[/yellow]")
        console.print(f"URL: [dim]{decklist_url}[/dim]\n")

        # Stats using library function for color
        completion_pct = result.stats.completion_percentage
        color = get_completion_color(completion_pct)

        console.print(f"Completion: [{color}]{completion_pct:.1f}%[/{color}]")
        console.print(f"Total cards: {result.stats.total_cards}")
        console.print(f"Cards owned: [green]{result.stats.owned_cards}[/green]")
        console.print(f"Cards missing: [red]{result.stats.missing_cards}[/red]")

        if detailed and result.missing_cards:
            console.print("\n[bold]Missing Cards:[/bold]")
            report = comparer.format_comparison_report(result)
            console.print(report)
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        # Determine output path using library function
        if output is None:
            output = generate_default_output_path(result)

        # Create output directory
        ensure_output_directory(output)

        # Get cards to proxy using library function
        proxy_cards = comparer.get_proxy_cards_for_generation(result, all_cards)

        if not should_generate_proxies(proxy_cards):
            console.print("[green]✓ You have all cards for this deck![/green]")
            return

        message = get_proxy_generation_message(proxy_cards, all_cards)
        color = "blue" if all_cards else "yellow"
        console.print(f"[{color}]{message}[/{color}]")

        # Generate PDF
        progress.add_task(description="Generating PDF...", total=None)
        pdf_generator = ProxyPDFGenerator(api, page_size=page_size)

        try:
            pdf_generator.generate_proxy_pdf(
                proxy_cards,
                output,
                download_images=not no_images,
                group_by_pack=True,
                interactive_printing_selection=alternate_prints,
            )
        except Exception as e:
            console.print(f"[red]✗ Error generating PDF: {e}[/red]")
            raise typer.Exit(1)

    console.print(f"[green]✓ Proxy sheet saved to: {output}[/green]")

    # Show summary
    console.print(f"\nDeck: [cyan]{result.decklist_name}[/cyan]")
    console.print(f"Identity: [yellow]{result.identity.title}[/yellow]")
    console.print(f"Total cards: {result.stats.total_cards}")
    console.print(f"Cards owned: {result.stats.owned_cards}")
    console.print(f"Cards missing: {result.stats.missing_cards}")
