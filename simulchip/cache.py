"""Cache management for card data and images."""

# Standard library imports
import io
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Third-party imports
import requests
from PIL import Image


class CacheManager:
    """Manages caching of card data and images."""

    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize cache manager.

        Args:
            cache_dir: Directory for cache storage (defaults to .cache)
        """
        self.cache_dir = cache_dir or Path.cwd() / ".cache"
        self.cards_cache_file = self.cache_dir / "cards.json"
        self.packs_cache_file = self.cache_dir / "packs.json"
        self.images_dir = self.cache_dir / "images"

        # Create cache directories
        self.cache_dir.mkdir(exist_ok=True)
        self.images_dir.mkdir(exist_ok=True)

    def get_cached_cards(self) -> Optional[Dict[str, Any]]:
        """Get cached card data.

        Returns:
            Dictionary of card data or None if not cached
        """
        if self.cards_cache_file.exists():
            # Check if cache is less than 24 hours old
            age = time.time() - self.cards_cache_file.stat().st_mtime
            if age < 86400:  # 24 hours
                with open(self.cards_cache_file, "r", encoding="utf-8") as f:
                    data: Dict[str, Any] = json.load(f)
                    return data
        return None

    def cache_cards(self, cards_data: Dict[str, Any]) -> None:
        """Cache card data.

        Args:
            cards_data: Card data to cache
        """
        with open(self.cards_cache_file, "w", encoding="utf-8") as f:
            json.dump(cards_data, f, indent=2)

    def get_cached_packs(self) -> Optional[List[Dict[str, Any]]]:
        """Get cached pack data.

        Returns:
            List of pack data or None if not cached
        """
        if self.packs_cache_file.exists():
            # Check if cache is less than 24 hours old
            age = time.time() - self.packs_cache_file.stat().st_mtime
            if age < 86400:  # 24 hours
                with open(self.packs_cache_file, "r", encoding="utf-8") as f:
                    data: List[Dict[str, Any]] = json.load(f)
                    return data
        return None

    def cache_packs(self, packs_data: List[Dict[str, Any]]) -> None:
        """Cache pack data.

        Args:
            packs_data: Pack data to cache
        """
        with open(self.packs_cache_file, "w", encoding="utf-8") as f:
            json.dump(packs_data, f, indent=2)

    def get_card_image_path(self, card_code: str, extension: str = "png") -> Path:
        """Get path for cached card image.

        Args:
            card_code: Card code
            extension: File extension

        Returns:
            Path to image file
        """
        return self.images_dir / f"{card_code}.{extension}"

    def has_card_image(self, card_code: str) -> bool:
        """Check if card image is cached.

        Args:
            card_code: Card code

        Returns:
            True if image is cached
        """
        # Check for both PNG and JPG
        return (
            self.get_card_image_path(card_code, "png").exists()
            or self.get_card_image_path(card_code, "jpg").exists()
        )

    def get_card_image(self, card_code: str) -> Optional[Image.Image]:
        """Get cached card image.

        Args:
            card_code: Card code

        Returns:
            PIL Image or None if not cached
        """
        # Try PNG first, then JPG
        for ext in ["png", "jpg"]:
            image_path = self.get_card_image_path(card_code, ext)
            if image_path.exists():
                return Image.open(image_path)
        return None

    def download_and_cache_image(
        self, card_code: str, image_url: str
    ) -> Optional[Image.Image]:
        """Download and cache card image.

        Args:
            card_code: Card code
            image_url: URL to download image from

        Returns:
            PIL Image or None if download fails
        """
        try:
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()

            # Load image
            img: Image.Image = Image.open(io.BytesIO(response.content))

            # Convert to RGB if necessary (for consistency)
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Save to cache
            # Determine extension from URL
            ext = "jpg" if image_url.endswith(".jpg") else "png"
            image_path = self.get_card_image_path(card_code, ext)
            img.save(image_path, "PNG" if ext == "png" else "JPEG")

            return img

        except Exception as e:
            print(f"Failed to download image for {card_code}: {e}")
            return None

    def clear_cache(self) -> None:
        """Clear all cached data."""
        if self.cards_cache_file.exists():
            self.cards_cache_file.unlink()
        if self.packs_cache_file.exists():
            self.packs_cache_file.unlink()

        # Clear images
        for ext in ["*.png", "*.jpg"]:
            for image_file in self.images_dir.glob(ext):
                image_file.unlink()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        stats = {
            "cards_cached": self.cards_cache_file.exists(),
            "packs_cached": self.packs_cache_file.exists(),
            "images_cached": len(list(self.images_dir.glob("*.png")))
            + len(list(self.images_dir.glob("*.jpg"))),
            "cache_size_mb": 0.0,
        }

        # Calculate total cache size
        total_size = 0
        for file in self.cache_dir.rglob("*"):
            if file.is_file():
                total_size += file.stat().st_size

        stats["cache_size_mb"] = round(total_size / (1024 * 1024), 2)

        return stats
