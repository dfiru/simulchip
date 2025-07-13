"""Terminal image rendering utilities for card previews."""

# Standard library imports
import io
from typing import Any, Optional

# Third-party imports
import requests
from PIL import Image
from rich.console import Console
from rich_pixels import Pixels


def download_card_image(
    image_url: str, max_size: tuple[int, int] = (300, 420)
) -> Optional[Image.Image]:
    """Download and resize a card image for terminal display.

    Args:
        image_url: URL of the card image
        max_size: Maximum size (width, height) for the image

    Returns:
        PIL Image object or None if download fails
    """
    try:
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()

        # Create image from response content
        image = Image.open(io.BytesIO(response.content))

        # Resize image while maintaining aspect ratio
        image.thumbnail(max_size, Image.Resampling.LANCZOS)

        return image
    except (requests.RequestException, OSError):
        # Silently fail - terminal image rendering is optional
        return None


def render_card_image_terminal(image_url: str, width: int = 40) -> Optional[Pixels]:
    """Render a card image as terminal pixels.

    Args:
        image_url: URL of the card image to render
        width: Target width in terminal characters

    Returns:
        Pixels object for rich display or None if rendering fails
    """
    # Calculate appropriate height (cards are roughly 63mm x 88mm, so ~1.4 aspect ratio)
    height = int(width * 1.4)

    # Download and resize image
    image = download_card_image(image_url, max_size=(width * 2, height * 2))
    if image is None:
        return None

    try:
        # Convert to terminal pixels
        pixels: Pixels = Pixels.from_image(image, resize=(width, height))
        return pixels
    except Exception:
        # Silently fail if rendering doesn't work
        return None


def get_card_image_url(card_data: dict[str, Any]) -> Optional[str]:
    """Extract the image URL from card data.

    Args:
        card_data: Card data dictionary from NetrunnerDB API

    Returns:
        Image URL string or None if not found
    """
    # NetrunnerDB provides images in different formats
    # Try the main image URL first
    image_url = card_data.get("image_url")
    if image_url:
        return str(image_url)

    # Try alternative image fields
    for field in ["imagesrc", "image", "card_image"]:
        if field in card_data and card_data[field]:
            return str(card_data[field])

    # If no explicit image URL, construct it from the card code
    # NetrunnerDB uses the pattern: https://card-images.netrunnerdb.com/v1/large/[code].jpg
    card_code = card_data.get("code")
    if card_code:
        return f"https://card-images.netrunnerdb.com/v1/large/{card_code}.jpg"

    return None


def display_card_preview(
    console: Console, card_data: dict[str, Any], title: str = "", width: int = 30
) -> bool:
    """Display a card preview image in the terminal.

    Args:
        console: Rich console for output
        card_data: Card data from NetrunnerDB API
        title: Optional title to display above the image
        width: Width in terminal characters

    Returns:
        True if image was successfully displayed, False otherwise
    """
    image_url = get_card_image_url(card_data)
    if not image_url:
        return False

    pixels = render_card_image_terminal(image_url, width=width)
    if pixels is None:
        return False

    if title:
        console.print(f"\n[bold cyan]{title}[/bold cyan]")

    console.print(pixels)
    return True
