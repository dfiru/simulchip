"""PDF generation module for Simulchip proxy cards.

This module provides functionality to generate print-ready PDF files
containing proxy cards for Netrunner. Cards are laid out in a 3x3 grid
optimized for standard card sleeves.

Classes:
    ProxyPDFGenerator: Main class for generating proxy PDFs.
"""

# Standard library imports
from pathlib import Path
from typing import Any, List, Optional, Tuple, Union

# Third-party imports
from PIL import Image
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import inch, mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from ..api.netrunnerdb import NetrunnerDBAPI
from ..collection.manager import CollectionManager
from ..comparison import CardInfo


class ProxyPDFGenerator:
    """Generate PDF files with proxy cards.

    This class creates print-ready PDFs with Netrunner cards laid out in a
    3x3 grid. Cards are sized to match standard Netrunner dimensions
    (63mm x 88mm) and are optimized for printing and sleeving.

    Attributes:
        CARD_WIDTH: Standard Netrunner card width (63mm).
        CARD_HEIGHT: Standard Netrunner card height (88mm).
        PAGE_MARGIN: Margin around the page edges.
        CARD_SPACING: Space between cards.

    Examples:
        Generate a PDF with proxy cards::

            generator = ProxyPDFGenerator(api_client)
            missing_cards = [CardInfo(...)]
            generator.generate_pdf(missing_cards, "proxies.pdf")
    """

    # Netrunner card dimensions (63mm x 88mm converted to inches)
    CARD_WIDTH = 63 * mm
    CARD_HEIGHT = 88 * mm

    # Margins and spacing optimized for 3x3 grid on letter
    PAGE_MARGIN = 0.25 * inch
    CARD_SPACING = 0.125 * inch

    def __init__(self, api_client: NetrunnerDBAPI, page_size: str = "letter"):
        """Initialize PDF generator.

        Args:
            api_client: NetrunnerDB API client instance for fetching card images.
            page_size: Page size for the PDF. Supported values are "letter"
                (8.5x11 inches) or "a4". Defaults to "letter".

        Note:
            The generator always uses a 3x3 grid layout regardless of page size
            to ensure consistent card sizing and optimal printing.
        """
        self.api = api_client
        self.page_size = letter if page_size == "letter" else A4
        self.page_width, self.page_height = self.page_size

        # Force 3x3 grid for optimal layout
        self.cards_per_row = 3
        self.cards_per_col = 3
        self.cards_per_page = 9

        # Calculate optimal spacing for 3x3 grid
        # Available width = page_width - margins - (3 * card_width)
        available_width = self.page_width - 2 * self.PAGE_MARGIN - 3 * self.CARD_WIDTH
        self.horizontal_spacing = available_width / 2  # 2 gaps between 3 cards

        # Available height = page_height - margins - (3 * card_height)
        available_height = (
            self.page_height - 2 * self.PAGE_MARGIN - 3 * self.CARD_HEIGHT
        )
        self.vertical_spacing = available_height / 2  # 2 gaps between 3 cards

    def _get_card_image_url(self, card_code: str) -> Optional[str]:
        """Get card image URL from NetrunnerDB.

        Args:
            card_code: Card code

        Returns:
            Image URL or None
        """
        # Get card data to find the image URL
        card_data = self.api.get_card_by_code(card_code)
        if card_data and "image_url" in card_data:
            return card_data["image_url"]

        # Fallback to constructed URL (v2 API)
        return f"https://card-images.netrunnerdb.com/v2/large/{card_code}.jpg"

    def _select_printing_interactive(
        self, card_title: str, printings: List[Any]
    ) -> str:
        """Use interactive table to select a printing.

        Args:
            card_title: Title of the card
            printings: List of available printings

        Returns:
            Selected card code
        """
        # Standard library imports
        import sys
        import termios
        import tty

        # Third-party imports
        from rich import box
        from rich.console import Console
        from rich.live import Live
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text

        console = Console()

        # Get pack names for display
        packs = {pack["code"]: pack for pack in self.api.get_all_packs()}

        selected_idx = 0

        def _getch() -> str:
            """Get a single character from stdin."""
            if sys.platform == "win32":
                # Standard library imports
                import msvcrt

                return msvcrt.getch().decode("utf-8")
            else:
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                try:
                    tty.setraw(sys.stdin.fileno())
                    char = sys.stdin.read(1)
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                return char

        with Live(console=console, auto_refresh=False) as live:
            while True:
                # Create table
                table = Table(
                    title=f"Select printing for: {card_title}",
                    show_header=True,
                    header_style="bold cyan",
                    box=box.ROUNDED,
                )
                table.add_column("", width=3, justify="center")
                table.add_column("Pack", style="yellow")
                table.add_column("Code", style="dim", width=10)
                table.add_column("Release Date", style="cyan", width=12)

                # Add rows
                for i, printing in enumerate(printings):
                    pack_code = printing.get("pack_code", "")
                    pack = packs.get(pack_code, {})  # type: ignore
                    pack_name = pack.get("name", "Unknown Pack")
                    release_date = pack.get("date_release", "Unknown")

                    # Selection indicator
                    if i == selected_idx:
                        mark = "►"
                        style = "reverse"
                    else:
                        mark = " "
                        style = None

                    table.add_row(
                        mark, pack_name, printing["code"], release_date, style=style
                    )

                # Instructions
                instructions = Text()
                instructions.append("↑/↓", style="cyan")
                instructions.append(" navigate (with preview), ", style="dim")
                instructions.append("Enter", style="cyan")
                instructions.append(" select, ", style="dim")
                instructions.append("q/Esc", style="cyan")
                instructions.append(" use newest (default)", style="dim")

                # Try to display card image for selected printing
                card_preview = None
                try:
                    # First-party imports
                    from simulchip.terminal_images import (
                        get_card_image_url,
                        render_card_image_terminal,
                    )

                    selected_printing = printings[selected_idx]
                    image_url = get_card_image_url(selected_printing)
                    if image_url:
                        card_preview = render_card_image_terminal(image_url, width=25)
                except Exception:
                    # Silently ignore image rendering failures
                    pass

                # Display
                # Third-party imports
                from rich.console import Group

                if card_preview:
                    # Show table and image side by side
                    table_and_instructions = Group(table, Text(""), instructions)

                    # Get pack name for preview
                    selected_pack_code = selected_printing.get("pack_code", "")
                    selected_pack = packs.get(selected_pack_code, {})  # type: ignore
                    selected_pack_name = selected_pack.get("name", "Unknown Pack")

                    # Create preview header with proper markup
                    preview_header = Text()
                    preview_header.append("Preview: ", style="bold cyan")
                    preview_header.append(selected_pack_name, style="cyan")

                    preview_section = Group(
                        preview_header,
                        card_preview,
                    )
                    # Try to force side-by-side layout
                    # Use a table to ensure columns stay side by side
                    layout_table = Table(show_header=False, box=None, padding=0)
                    layout_table.add_column(ratio=2)  # Table column
                    layout_table.add_column(ratio=1)  # Preview column
                    layout_table.add_row(table_and_instructions, preview_section)
                else:
                    display_group = Group(table, Text(""), instructions)  # Blank line

                # Choose the right display based on whether we have a preview
                display: Union[Table, Group]
                if card_preview:
                    display = layout_table
                else:
                    display = display_group

                panel = Panel(
                    display,
                    title="[bold]Alternate Printing Selection[/bold]",
                    subtitle=f"[dim]{len(printings)} printings available[/dim]",
                    border_style="blue",
                )

                live.update(panel)
                live.refresh()

                # Handle input
                char = _getch()

                if char == "\x1b":  # ESC sequence
                    next_char = _getch()
                    if next_char == "[":
                        arrow_char = _getch()
                        if arrow_char == "A" and selected_idx > 0:  # Up
                            selected_idx -= 1
                        elif (
                            arrow_char == "B" and selected_idx < len(printings) - 1
                        ):  # Down
                            selected_idx += 1
                    else:
                        # Just ESC - use default (newest)
                        return str(printings[0]["code"])
                elif char == "\r" or char == "\n":  # Enter
                    return str(printings[selected_idx]["code"])
                elif char == "q" or char == "\x03":  # q or Ctrl+C
                    return str(printings[0]["code"])
                elif char == "k" and selected_idx > 0:  # Vim-style up
                    selected_idx -= 1
                elif (
                    char == "j" and selected_idx < len(printings) - 1
                ):  # Vim-style down
                    selected_idx += 1

    def _get_pack_name(self, pack_code: str) -> str:
        """Get pack name from pack code.

        Args:
            pack_code: Pack code

        Returns:
            Pack name or pack code if not found
        """
        packs = self.api.get_all_packs()
        for pack in packs:
            if pack.get("code") == pack_code:
                return pack.get("name", pack_code)
        return pack_code

    def _download_card_image(self, card_code: str) -> Optional[Image.Image]:
        """Download card image using cache.

        Args:
            card_code: Card code

        Returns:
            PIL Image or None if download fails
        """
        # Check cache first
        cached_image = self.api.cache.get_card_image(card_code)
        if cached_image:
            return cached_image

        # Download and cache
        url = self._get_card_image_url(card_code)
        if url:
            return self.api.cache.download_and_cache_image(card_code, url)

        return None

    def _get_card_position(self, index: int) -> Tuple[float, float]:
        """Calculate card position on page for 3x3 grid.

        Args:
            index: Card index on current page (0-based)

        Returns:
            (x, y) position of card's bottom-left corner
        """
        row = index // self.cards_per_row
        col = index % self.cards_per_row

        x = self.PAGE_MARGIN + col * (self.CARD_WIDTH + self.horizontal_spacing)
        y = (
            self.page_height
            - self.PAGE_MARGIN
            - (row + 1) * self.CARD_HEIGHT
            - row * self.vertical_spacing
        )

        return x, y

    def _draw_card_placeholder(
        self, c: canvas.Canvas, x: float, y: float, card: CardInfo
    ) -> None:
        """Draw a placeholder for a card without image.

        Args:
            c: ReportLab canvas
            x: X position
            y: Y position
            card: Card information
        """
        # Draw border
        c.rect(x, y, self.CARD_WIDTH, self.CARD_HEIGHT)

        # Add card information
        text_x = x + 0.1 * inch
        text_y = y + self.CARD_HEIGHT - 0.3 * inch

        c.setFont("Helvetica-Bold", 12)
        c.drawString(text_x, text_y, card.title)

        c.setFont("Helvetica", 10)
        c.drawString(text_x, text_y - 15, f"Code: {card.code}")
        c.drawString(text_x, text_y - 30, f"Pack: {card.pack_name}")
        c.drawString(text_x, text_y - 45, f"Type: {card.type_code}")

        # Add "PROXY" watermark
        c.saveState()
        c.setFont("Helvetica-Bold", 36)
        c.setFillColorRGB(0.8, 0.8, 0.8)
        c.translate(x + self.CARD_WIDTH / 2, y + self.CARD_HEIGHT / 2)
        c.rotate(45)
        c.drawCentredString(0, 0, "PROXY")
        c.restoreState()

    def _draw_cut_lines(self, c: canvas.Canvas) -> None:
        """Draw dashed cut lines for card separation.

        Args:
            c: ReportLab canvas
        """
        c.saveState()
        c.setStrokeColorRGB(0.7, 0.7, 0.7)  # Light gray
        c.setLineWidth(0.5)
        c.setDash([3, 3])  # Dashed line pattern

        # Calculate grid boundaries
        grid_left = self.PAGE_MARGIN
        grid_right = (
            self.PAGE_MARGIN + 3 * self.CARD_WIDTH + 2 * self.horizontal_spacing
        )
        grid_top = self.page_height - self.PAGE_MARGIN
        grid_bottom = (
            self.page_height
            - self.PAGE_MARGIN
            - 3 * self.CARD_HEIGHT
            - 2 * self.vertical_spacing
        )

        # Draw continuous horizontal lines from margin to margin
        # Need 6 horizontal lines: top edge of row1, bottom edge of row1, top edge of row2, bottom edge of row2, top edge of row3, bottom edge of row3
        for row in range(3):  # For each row
            # Top edge of this row
            y_top = (
                self.page_height
                - self.PAGE_MARGIN
                - row * (self.CARD_HEIGHT + self.vertical_spacing)
            )
            c.line(grid_left, y_top, grid_right, y_top)

            # Bottom edge of this row
            y_bottom = (
                self.page_height
                - self.PAGE_MARGIN
                - row * (self.CARD_HEIGHT + self.vertical_spacing)
                - self.CARD_HEIGHT
            )
            c.line(grid_left, y_bottom, grid_right, y_bottom)

        # Draw continuous vertical lines from margin to margin
        # Need 6 vertical lines: left edge of col1, right edge of col1, left edge of col2, right edge of col2, left edge of col3, right edge of col3
        for col in range(3):  # For each column
            # Left edge of this column
            x_left = self.PAGE_MARGIN + col * (
                self.CARD_WIDTH + self.horizontal_spacing
            )
            c.line(x_left, grid_top, x_left, grid_bottom)

            # Right edge of this column
            x_right = (
                self.PAGE_MARGIN
                + col * (self.CARD_WIDTH + self.horizontal_spacing)
                + self.CARD_WIDTH
            )
            c.line(x_right, grid_top, x_right, grid_bottom)

        c.restoreState()

    def generate_proxy_pdf(
        self,
        cards: List[CardInfo],
        output_path: Path,
        download_images: bool = True,
        group_by_pack: bool = False,
        interactive_printing_selection: bool = False,
    ) -> None:
        """Generate PDF with proxy cards.

        Args:
            cards: List of cards to generate proxies for
            output_path: Output PDF file path
            download_images: Whether to download card images
            group_by_pack: Whether to group cards by pack
            interactive_printing_selection: Whether to prompt for alternate printings
        """
        # Prepare card list (with duplicates for multiple copies)
        proxy_list = []

        # Handle alternate printing selection if requested
        printing_selections = {}  # Map from original code to selected code

        if interactive_printing_selection:
            # Third-party imports
            from rich.console import Console

            console = Console()

            console.print("\n[cyan]Checking for alternate printings...[/cyan]")

            # Check if we're in an interactive terminal
            # Standard library imports
            import sys

            if not sys.stdin.isatty():
                console.print(
                    "[yellow]Interactive printing selection requires a terminal[/yellow]"
                )
                console.print("[dim]Using newest printing for all cards[/dim]")
            else:
                for card in cards:
                    printings = self.api.get_all_printings(card.title)
                    if len(printings) > 1:
                        # Use interactive table to select printing
                        selected_code = self._select_printing_interactive(
                            card.title, printings
                        )
                        printing_selections[card.code] = selected_code

                        # Show confirmation
                        selected_printing = next(
                            p for p in printings if p["code"] == selected_code
                        )
                        pack_name = self._get_pack_name(
                            selected_printing.get("pack_code", "")
                        )
                        console.print(
                            f"[green]✓[/green] {card.title}: Selected [yellow]{pack_name}[/yellow] version"
                        )

        # Build proxy list with selected printings
        for card in cards:
            # Use selected printing code if available, otherwise use original
            card_code = printing_selections.get(card.code, card.code)

            # Create modified CardInfo with selected printing code
            if card_code != card.code:
                # Create new CardInfo with updated code
                # Standard library imports
                from dataclasses import replace

                modified_card = replace(card, code=card_code)
                proxy_list.extend([modified_card] * card.missing_count)
            else:
                proxy_list.extend([card] * card.missing_count)

        # Sort if grouping by pack
        if group_by_pack:
            proxy_list.sort(key=lambda c: (c.pack_name, c.title))

        # Create PDF
        c = canvas.Canvas(str(output_path), pagesize=self.page_size)

        # Track images to avoid re-downloading
        image_cache = {}

        # Draw cut lines on first page
        self._draw_cut_lines(c)

        for i, card in enumerate(proxy_list):
            # New page if needed
            if i > 0 and i % self.cards_per_page == 0:
                c.showPage()
                self._draw_cut_lines(c)  # Draw cut lines on new page

            # Get position on current page
            page_index = i % self.cards_per_page
            x, y = self._get_card_position(page_index)

            # Try to use card image
            image_drawn = False
            if download_images:
                if card.code not in image_cache:
                    image_cache[card.code] = self._download_card_image(card.code)

                img = image_cache[card.code]
                if img:
                    # Convert to RGB if necessary
                    if img.mode != "RGB":
                        img = img.convert("RGB")

                    # Create ImageReader for ReportLab
                    img_reader = ImageReader(img)

                    # Draw image
                    c.drawImage(
                        img_reader,
                        x,
                        y,
                        width=self.CARD_WIDTH,
                        height=self.CARD_HEIGHT,
                        preserveAspectRatio=True,
                        mask="auto",
                    )
                    image_drawn = True

            # Draw placeholder if no image
            if not image_drawn:
                self._draw_card_placeholder(c, x, y, card)

        # Save PDF
        c.save()

    def generate_pack_pdf(
        self,
        pack_code: str,
        output_path: Path,
        collection_manager: CollectionManager,
        download_images: bool = True,
    ) -> None:
        """Generate PDF for all missing cards from a specific pack.

        Args:
            pack_code: Pack code
            output_path: Output PDF file path
            collection_manager: Collection manager to check owned cards
            download_images: Whether to download card images
        """
        # Get all cards from pack
        all_cards = self.api.get_all_cards()
        pack_cards = [
            card for card in all_cards.values() if card["pack_code"] == pack_code
        ]

        # Find missing cards
        missing_cards = []
        for card_data in pack_cards:
            card_code = card_data["code"]
            if not collection_manager.has_card(card_code):
                pack_data = self.api.get_pack_by_code(pack_code)
                card_info = CardInfo(
                    code=card_code,
                    title=card_data["title"],
                    pack_code=pack_code,
                    pack_name=pack_data["name"] if pack_data else "Unknown Pack",
                    type_code=card_data.get("type_code", ""),
                    faction_code=card_data.get("faction_code", ""),
                    required_count=1,
                    owned_count=0,
                    missing_count=1,
                )
                missing_cards.append(card_info)

        # Generate PDF
        if missing_cards:
            self.generate_proxy_pdf(missing_cards, output_path, download_images)
