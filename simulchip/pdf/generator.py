"""PDF generation module for Simulchip proxy cards.

This module provides functionality to generate print-ready PDF files
containing proxy cards for Netrunner. Cards are laid out in a 3x3 grid
optimized for standard card sleeves.

Classes:
    ProxyPDFGenerator: Main class for generating proxy PDFs.
"""

# Standard library imports
from pathlib import Path
from typing import List, Optional, Tuple

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
    ) -> None:
        """Generate PDF with proxy cards.

        Args:
            cards: List of cards to generate proxies for
            output_path: Output PDF file path
            download_images: Whether to download card images
            group_by_pack: Whether to group cards by pack
        """
        # Prepare card list (with duplicates for multiple copies)
        proxy_list = []
        for card in cards:
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
