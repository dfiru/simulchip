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
from simulchip.collection.manager import CollectionManager
from simulchip.comparison import DecklistComparer
from simulchip.pdf.generator import ProxyPDFGenerator
from simulchip.utils import extract_decklist_id, get_faction_side, sanitize_filename

# Initialize console for rich output
console = Console()

# Create the proxy command group
app = typer.Typer(help="Generate proxy sheets for decklists")

# Default paths
DEFAULT_COLLECTION = Path.home() / ".simulchip" / "collection.toml"
DEFAULT_DECKS_DIR = Path.cwd() / "decks"

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


def get_deck_path(decklist_id: str, deck_name: str, side: str) -> Path:
    """Generate the standard deck path."""
    # Sanitize the deck name for filesystem
    safe_name = sanitize_filename(deck_name.lower().replace(" ", "-"))

    # Determine side directory
    side_dir = "corporation" if side.lower() in ["corp", "corporation"] else "runner"

    # Create path: decks/(corporation|runner)/(id)/(deck-name).pdf
    return DEFAULT_DECKS_DIR / side_dir / decklist_id / f"{safe_name}.pdf"


@app.command()
def generate(
    decklist_url: str,
    output: Optional[Path] = OUTPUT_OPTION,
    collection_file: Optional[Path] = COLLECTION_OPTION,
    all_cards: bool = ALL_CARDS_OPTION,
    no_images: bool = NO_IMAGES_OPTION,
    page_size: str = PAGE_SIZE_OPTION,
) -> Any:
    """Generate proxy sheets for a decklist."""
    # Extract decklist ID
    decklist_id = extract_decklist_id(decklist_url)
    if not decklist_id:
        console.print(f"[red]✗ Invalid decklist URL: {decklist_url}[/red]")
        raise typer.Exit(1)

    # Initialize API and collection
    api = NetrunnerDBAPI()

    if collection_file is None:
        collection_file = DEFAULT_COLLECTION

    # Create collection manager
    if collection_file.exists() and not all_cards:
        manager = CollectionManager(collection_file=collection_file, api=api)
    else:
        # Empty collection if generating all cards or no collection exists
        manager = CollectionManager(api=api)

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

        # Determine output path
        if output is None:
            # Determine if corp or runner based on identity
            identity_faction = result.identity.faction_code
            side = get_faction_side(identity_faction)
            output = get_deck_path(decklist_id, result.decklist_name, side)

        # Create output directory
        output.parent.mkdir(parents=True, exist_ok=True)

        # Get cards to proxy
        if all_cards:
            proxy_cards = result.all_cards
            console.print(
                f"[blue]Generating proxies for all {len(proxy_cards)} cards[/blue]"
            )
        else:
            proxy_cards = comparer.get_proxy_cards(result)
            if not proxy_cards:
                console.print("[green]✓ You have all cards for this deck![/green]")
                return
            console.print(
                f"[yellow]Generating proxies for {len(proxy_cards)} missing cards[/yellow]"
            )

        # Generate PDF
        progress.add_task(description="Generating PDF...", total=None)
        pdf_generator = ProxyPDFGenerator(api, page_size=page_size)

        try:
            pdf_generator.generate_proxy_pdf(
                proxy_cards,
                output,
                download_images=not no_images,
                group_by_pack=True,
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


@app.command()
def compare(
    decklist_url: str,
    collection_file: Optional[Path] = COLLECTION_OPTION,
    detailed: bool = DETAILED_OPTION,
) -> Any:
    """Compare a decklist against your collection."""
    # Extract decklist ID
    decklist_id = extract_decklist_id(decklist_url)
    if not decklist_id:
        console.print(f"[red]✗ Invalid decklist URL: {decklist_url}[/red]")
        raise typer.Exit(1)

    # Initialize API and collection
    api = NetrunnerDBAPI()

    if collection_file is None:
        collection_file = DEFAULT_COLLECTION

    if not collection_file.exists():
        console.print(f"[red]✗ Collection not found at {collection_file}[/red]")
        console.print(
            "[yellow]Initialize a collection with: simulchip collection init[/yellow]"
        )
        raise typer.Exit(1)

    manager = CollectionManager(collection_file=collection_file, api=api)
    comparer = DecklistComparer(api, manager)

    # Compare decklist
    with console.status("Comparing decklist..."):
        try:
            result = comparer.compare_decklist(decklist_id)
        except Exception as e:
            console.print(f"[red]✗ Error comparing decklist: {e}[/red]")
            raise typer.Exit(1)

    # Display results
    console.print(f"\n[bold]Deck: {result.decklist_name}[/bold]")
    console.print(f"Identity: [yellow]{result.identity.title}[/yellow]")
    console.print(f"URL: [dim]{decklist_url}[/dim]\n")

    # Stats
    completion_pct = result.stats.completion_percentage
    color = (
        "green"
        if completion_pct == 100
        else "yellow"
        if completion_pct >= 80
        else "red"
    )

    console.print(f"Completion: [{color}]{completion_pct:.1f}%[/{color}]")
    console.print(f"Total cards: {result.stats.total_cards}")
    console.print(f"Cards owned: [green]{result.stats.owned_cards}[/green]")
    console.print(f"Cards missing: [red]{result.stats.missing_cards}[/red]")

    if detailed and result.missing_cards:
        console.print("\n[bold]Missing Cards:[/bold]")
        report = comparer.format_comparison_report(result)
        console.print(report)


@app.command()
def batch(
    decklist_file: Path,
    collection_file: Optional[Path] = COLLECTION_OPTION,
    no_images: bool = NO_IMAGES_OPTION,
    page_size: str = PAGE_SIZE_OPTION,
) -> Any:
    """Generate proxy sheets for multiple decklists from a file."""
    if not decklist_file.exists():
        console.print(f"[red]✗ File not found: {decklist_file}[/red]")
        raise typer.Exit(1)

    # Read URLs from file
    urls = []
    with open(decklist_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):  # Skip empty lines and comments
                urls.append(line)

    if not urls:
        console.print(f"[red]✗ No URLs found in {decklist_file}[/red]")
        raise typer.Exit(1)

    console.print(f"[blue]Found {len(urls)} decklists to process[/blue]\n")

    # Process each URL
    success = 0
    failed = 0

    for i, url in enumerate(urls, 1):
        console.print(f"[dim]Processing {i}/{len(urls)}:[/dim] {url}")

        try:
            # Use the generate command logic
            generate(
                decklist_url=url,
                collection_file=collection_file,
                no_images=no_images,
                page_size=page_size,
                output=None,
                all_cards=False,
            )
            success += 1
        except typer.Exit:
            failed += 1
            console.print("[red]✗ Failed[/red]\n")
        except Exception as e:
            failed += 1
            console.print(f"[red]✗ Error: {e}[/red]\n")

    # Summary
    console.print("\n[bold]Batch complete![/bold]")
    console.print(f"Success: [green]{success}[/green]")
    console.print(f"Failed: [red]{failed}[/red]")
