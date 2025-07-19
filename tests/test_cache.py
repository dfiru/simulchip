"""Tests for cache management functionality."""

# Standard library imports
import io
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

# Third-party imports
import pytest
from PIL import Image

# First-party imports
from simulchip.cache import CacheManager


class TestSmartCacheValidation:
    """Test smart cache validation functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache = CacheManager(Path(self.temp_dir))

        # Sample pack data
        self.old_packs = [
            {"code": "core", "name": "Core Set", "date_release": "2012-09-06"},
            {"code": "wla", "name": "What Lies Ahead", "date_release": "2012-12-14"},
        ]

        self.new_packs = self.old_packs + [
            {"code": "new", "name": "New Pack", "date_release": "2024-01-01"},
        ]

    def teardown_method(self):
        """Clean up test fixtures."""
        # Standard library imports
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_latest_pack_date(self):
        """Should correctly identify the latest pack release date."""
        # Test with packs
        latest = self.cache.get_latest_pack_date(self.old_packs)
        assert latest == "2012-12-14"

        latest = self.cache.get_latest_pack_date(self.new_packs)
        assert latest == "2024-01-01"

        # Test with empty list
        assert self.cache.get_latest_pack_date([]) is None

    def test_cache_metadata_operations(self):
        """Should correctly save and load cache metadata."""
        # Initially empty
        assert self.cache.get_cache_metadata() == {}

        # Save metadata
        metadata = {
            "timestamp": time.time(),
            "latest_pack_date": "2024-01-01",
            "pack_count": 3,
        }
        self.cache.update_cache_metadata(metadata)

        # Load metadata
        loaded = self.cache.get_cache_metadata()
        assert loaded["latest_pack_date"] == "2024-01-01"
        assert loaded["pack_count"] == 3
        assert "timestamp" in loaded

    def test_is_cache_valid_no_metadata(self):
        """Should return False when no metadata exists."""
        assert not self.cache.is_cache_valid()

    def test_is_cache_valid_missing_files(self):
        """Should return False when cache files are missing."""
        # Set metadata but no cache files
        self.cache.update_cache_metadata(
            {"timestamp": time.time(), "latest_pack_date": "2024-01-01"}
        )

        assert not self.cache.is_cache_valid()

    def test_is_cache_valid_new_pack_release(self):
        """Should return False when new pack is released."""
        # Create cache files
        self.cache.cache_cards({"01001": {"code": "01001", "title": "Test"}})
        self.cache.cache_packs(self.old_packs)
        self.cache.mark_cache_fresh(self.old_packs)

        # Cache should be valid with same packs
        assert self.cache.is_cache_valid(self.old_packs)

        # Cache should be invalid with new pack
        assert not self.cache.is_cache_valid(self.new_packs)

    def test_is_cache_valid_age_fallback(self):
        """Should use age fallback when cache is too old."""
        # Create fresh cache
        self.cache.cache_cards({"01001": {"code": "01001", "title": "Test"}})
        self.cache.cache_packs(self.old_packs)
        self.cache.mark_cache_fresh(self.old_packs)

        assert self.cache.is_cache_valid()

        # Simulate old cache (8 days)
        old_metadata = self.cache.get_cache_metadata()
        old_metadata["timestamp"] = time.time() - (8 * 24 * 60 * 60)
        self.cache.update_cache_metadata(old_metadata)

        assert not self.cache.is_cache_valid()

    def test_mark_cache_fresh(self):
        """Should correctly mark cache as fresh with pack info."""
        self.cache.mark_cache_fresh(self.new_packs)

        metadata = self.cache.get_cache_metadata()
        assert metadata["latest_pack_date"] == "2024-01-01"
        assert metadata["pack_count"] == 3
        assert time.time() - metadata["timestamp"] < 1  # Fresh timestamp

    def test_clear_cache_includes_metadata(self):
        """Should clear metadata when clearing cache."""
        # Create cache with metadata
        self.cache.cache_cards({"01001": {"code": "01001"}})
        self.cache.cache_packs(self.old_packs)
        self.cache.mark_cache_fresh(self.old_packs)

        # Clear cache
        self.cache.clear_cache()

        # Everything should be gone
        assert not self.cache.cards_cache_file.exists()
        assert not self.cache.packs_cache_file.exists()
        assert not self.cache.metadata_file.exists()
        assert self.cache.get_cache_metadata() == {}


class TestOfflineMode:
    """Test offline mode functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # First-party imports
        from simulchip.api.netrunnerdb import NetrunnerDBAPI

        self.temp_dir = tempfile.mkdtemp()
        self.api = NetrunnerDBAPI(cache_dir=Path(self.temp_dir))

        # Pre-populate cache
        self.cached_cards = {"01001": {"code": "01001", "title": "Test Card"}}
        self.cached_packs = [{"code": "core", "name": "Core Set", "date_release": ""}]

        self.api.cache.cache_cards(self.cached_cards)
        self.api.cache.cache_packs(self.cached_packs)
        self.api.cache.mark_cache_fresh(self.cached_packs)

    def teardown_method(self):
        """Clean up test fixtures."""
        # Standard library imports
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_offline_mode_toggle(self):
        """Should correctly toggle offline mode."""
        assert not self.api.is_offline_mode()

        self.api.set_offline_mode(True)
        assert self.api.is_offline_mode()

        self.api.set_offline_mode(False)
        assert not self.api.is_offline_mode()

    def test_offline_mode_prevents_requests(self):
        """Should prevent network requests in offline mode."""
        # First-party imports
        from simulchip.api.netrunnerdb import APIError

        self.api.set_offline_mode(True)

        with pytest.raises(APIError, match="Offline mode enabled"):
            self.api._make_request("cards")

    def test_offline_mode_uses_cache(self):
        """Should use cached data in offline mode."""
        self.api.set_offline_mode(True)

        # Should return cached data without network requests
        cards = self.api.get_all_cards()
        assert cards == self.cached_cards

        packs = self.api.get_all_packs()
        assert packs == self.cached_packs

    def test_cache_validity_in_offline_mode(self):
        """Should always consider cache valid in offline mode."""
        self.api.set_offline_mode(True)

        # Cache should always be valid in offline mode
        assert self.api.check_cache_validity()

        # Even with old metadata
        old_metadata = self.api.cache.get_cache_metadata()
        old_metadata["timestamp"] = 0  # Very old
        self.api.cache.update_cache_metadata(old_metadata)

        assert self.api.check_cache_validity()


class TestCacheManagerComprehensive:
    """Comprehensive tests for CacheManager."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_dir = Path(self.temp_dir) / "test_cache"
        self.cache_manager = CacheManager(cache_dir=self.cache_dir)

    def teardown_method(self) -> None:
        """Clean up test files."""
        # Standard library imports
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialization(self) -> None:
        """Test cache manager initialization."""
        assert self.cache_manager.cache_dir == self.cache_dir
        assert self.cache_manager.cards_cache_file == self.cache_dir / "cards.json"
        assert self.cache_manager.packs_cache_file == self.cache_dir / "packs.json"
        assert self.cache_manager.images_dir == self.cache_dir / "images"
        assert (
            self.cache_manager.metadata_file == self.cache_dir / "cache_metadata.json"
        )

        # Check directories were created
        assert self.cache_dir.exists()
        assert self.cache_manager.images_dir.exists()

    def test_get_cached_cards_no_file(self) -> None:
        """Test get_cached_cards when no cache file exists."""
        result = self.cache_manager.get_cached_cards()
        assert result is None

    def test_get_cached_cards_expired(self) -> None:
        """Test get_cached_cards when cache is expired."""
        # Create an old cache file
        cards_data = {"01001": {"title": "Sure Gamble"}}
        self.cache_manager.cache_cards(cards_data)

        # Make file appear old (older than 24 hours)
        old_time = time.time() - 100000  # More than 24 hours ago
        # Standard library imports
        import os

        os.utime(self.cache_manager.cards_cache_file, (old_time, old_time))

        result = self.cache_manager.get_cached_cards()
        assert result is None

    def test_get_cached_packs_no_file(self) -> None:
        """Test get_cached_packs when no cache file exists."""
        result = self.cache_manager.get_cached_packs()
        assert result is None

    def test_get_cached_packs_expired(self) -> None:
        """Test get_cached_packs when cache is expired."""
        # Create an old cache file
        packs_data = [{"code": "core", "name": "Core Set"}]
        self.cache_manager.cache_packs(packs_data)

        # Make file appear old
        old_time = time.time() - 100000
        # Standard library imports
        import os

        os.utime(self.cache_manager.packs_cache_file, (old_time, old_time))

        result = self.cache_manager.get_cached_packs()
        assert result is None

    def test_get_card_image_path(self) -> None:
        """Test getting card image path."""
        # Test PNG path
        png_path = self.cache_manager.get_card_image_path("01001", "png")
        assert png_path == self.cache_manager.images_dir / "01001.png"

        # Test JPG path
        jpg_path = self.cache_manager.get_card_image_path("01001", "jpg")
        assert jpg_path == self.cache_manager.images_dir / "01001.jpg"

        # Test default extension
        default_path = self.cache_manager.get_card_image_path("01001")
        assert default_path == self.cache_manager.images_dir / "01001.png"

    def test_has_card_image(self) -> None:
        """Test checking if card image exists."""
        # No image exists
        assert self.cache_manager.has_card_image("01001") is False

        # Create PNG image
        png_path = self.cache_manager.get_card_image_path("01001", "png")
        png_path.touch()
        assert self.cache_manager.has_card_image("01001") is True

        # Remove PNG, create JPG
        png_path.unlink()
        jpg_path = self.cache_manager.get_card_image_path("01001", "jpg")
        jpg_path.touch()
        assert self.cache_manager.has_card_image("01001") is True

    def test_get_card_image(self) -> None:
        """Test getting cached card image."""
        # No image exists
        assert self.cache_manager.get_card_image("01001") is None

        # Create a test PNG image
        img = Image.new("RGB", (100, 100), color="red")
        png_path = self.cache_manager.get_card_image_path("01001", "png")
        img.save(png_path, "PNG")

        # Get the image
        cached_img = self.cache_manager.get_card_image("01001")
        assert cached_img is not None
        assert cached_img.size == (100, 100)

        # Remove PNG, create JPG
        png_path.unlink()
        jpg_path = self.cache_manager.get_card_image_path("01001", "jpg")
        img.save(jpg_path, "JPEG")

        # Get the JPG image
        cached_img = self.cache_manager.get_card_image("01001")
        assert cached_img is not None
        assert cached_img.size == (100, 100)

    @patch("requests.get")
    def test_download_and_cache_image_success(self, mock_get: Mock) -> None:
        """Test successfully downloading and caching an image."""
        # Create a test image in memory
        img = Image.new("RGB", (300, 419), color="blue")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        # Mock the response
        mock_response = Mock()
        mock_response.content = img_bytes.getvalue()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Download and cache
        result = self.cache_manager.download_and_cache_image(
            "01001", "https://example.com/01001.png"
        )

        assert result is not None
        assert result.size == (300, 419)

        # Check image was saved
        assert self.cache_manager.has_card_image("01001")

    @patch("requests.get")
    def test_download_and_cache_image_jpg(self, mock_get: Mock) -> None:
        """Test downloading and caching a JPG image."""
        # Create a test image
        img = Image.new("RGB", (300, 419), color="green")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG")
        img_bytes.seek(0)

        # Mock the response
        mock_response = Mock()
        mock_response.content = img_bytes.getvalue()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Download and cache
        result = self.cache_manager.download_and_cache_image(
            "01002", "https://example.com/01002.jpg"
        )

        assert result is not None
        assert result.size == (300, 419)

        # Check JPG was saved
        jpg_path = self.cache_manager.get_card_image_path("01002", "jpg")
        assert jpg_path.exists()

    @patch("requests.get")
    def test_download_and_cache_image_non_rgb(self, mock_get: Mock) -> None:
        """Test downloading an image that needs RGB conversion."""
        # Create a grayscale image
        img = Image.new("L", (300, 419), color=128)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        # Mock the response
        mock_response = Mock()
        mock_response.content = img_bytes.getvalue()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Download and cache
        result = self.cache_manager.download_and_cache_image(
            "01003", "https://example.com/01003.png"
        )

        assert result is not None
        assert result.mode == "RGB"  # Should be converted to RGB

    @patch("requests.get")
    def test_download_and_cache_image_failure(self, mock_get: Mock) -> None:
        """Test handling download failures."""
        # Mock a failed request
        mock_get.side_effect = Exception("Network error")

        result = self.cache_manager.download_and_cache_image(
            "01004", "https://example.com/01004.png"
        )

        assert result is None
        assert not self.cache_manager.has_card_image("01004")

    def test_clear_cache_with_images(self) -> None:
        """Test clearing cache including images."""
        # Create cache files
        self.cache_manager.cache_cards({"01001": {"title": "Test"}})
        self.cache_manager.cache_packs([{"code": "core"}])
        self.cache_manager.update_cache_metadata({"test": "data"})

        # Create test images
        png_path = self.cache_manager.get_card_image_path("01001", "png")
        png_path.touch()
        jpg_path = self.cache_manager.get_card_image_path("01002", "jpg")
        jpg_path.touch()

        # Clear cache
        self.cache_manager.clear_cache()

        # Check everything is cleared
        assert not self.cache_manager.cards_cache_file.exists()
        assert not self.cache_manager.packs_cache_file.exists()
        assert not self.cache_manager.metadata_file.exists()
        assert not png_path.exists()
        assert not jpg_path.exists()

    def test_get_cache_stats(self) -> None:
        """Test getting cache statistics."""
        # Empty cache
        stats = self.cache_manager.get_cache_stats()
        assert stats["cards_cached"] is False
        assert stats["packs_cached"] is False
        assert stats["images_cached"] == 0
        assert stats["cache_size_mb"] == 0.0

        # Add some data
        self.cache_manager.cache_cards({"01001": {"title": "Test"}})
        self.cache_manager.cache_packs([{"code": "core"}])

        # Create test images
        img = Image.new("RGB", (100, 100), color="red")
        png_path = self.cache_manager.get_card_image_path("01001", "png")
        img.save(png_path, "PNG")
        jpg_path = self.cache_manager.get_card_image_path("01002", "jpg")
        img.save(jpg_path, "JPEG")

        # Get stats
        stats = self.cache_manager.get_cache_stats()
        assert stats["cards_cached"] is True
        assert stats["packs_cached"] is True
        assert stats["images_cached"] == 2
        assert stats["cache_size_mb"] >= 0  # May be 0 for very small files

    def test_get_cache_metadata_no_file(self) -> None:
        """Test getting metadata when file doesn't exist."""
        metadata = self.cache_manager.get_cache_metadata()
        assert metadata == {}

    def test_get_cache_metadata_invalid_json(self) -> None:
        """Test getting metadata with invalid JSON."""
        # Create invalid JSON file
        with open(self.cache_manager.metadata_file, "w") as f:
            f.write("{invalid json")

        metadata = self.cache_manager.get_cache_metadata()
        assert metadata == {}

    def test_get_cache_metadata_io_error(self) -> None:
        """Test getting metadata with IO error."""
        # Create a directory instead of file to cause IO error
        self.cache_manager.metadata_file.mkdir()

        metadata = self.cache_manager.get_cache_metadata()
        assert metadata == {}

    def test_get_latest_pack_date(self) -> None:
        """Test getting latest pack release date."""
        # Empty list
        assert self.cache_manager.get_latest_pack_date([]) is None

        # Single pack
        packs = [{"code": "core", "date_release": "2012-08-29"}]
        assert self.cache_manager.get_latest_pack_date(packs) == "2012-08-29"

        # Multiple packs
        packs = [
            {"code": "core", "date_release": "2012-08-29"},
            {"code": "wla", "date_release": "2012-12-14"},
            {"code": "ta", "date_release": "2013-01-15"},
        ]
        assert self.cache_manager.get_latest_pack_date(packs) == "2013-01-15"

        # Pack without date
        packs = [
            {"code": "core", "date_release": "2012-08-29"},
            {"code": "unknown"},  # No date_release
        ]
        assert self.cache_manager.get_latest_pack_date(packs) == "2012-08-29"

    def test_is_cache_valid_no_metadata(self) -> None:
        """Test cache validity with no metadata."""
        assert self.cache_manager.is_cache_valid() is False

    def test_is_cache_valid_missing_files(self) -> None:
        """Test cache validity with missing cache files."""
        # Create metadata but no cache files
        self.cache_manager.update_cache_metadata({"timestamp": time.time()})
        assert self.cache_manager.is_cache_valid() is False

    def test_is_cache_valid_new_pack(self) -> None:
        """Test cache validity with new pack release."""
        # Create cache files
        self.cache_manager.cache_cards({})
        self.cache_manager.cache_packs([])

        # Set metadata with old pack date
        metadata = {"timestamp": time.time(), "latest_pack_date": "2012-08-29"}
        self.cache_manager.update_cache_metadata(metadata)

        # Check with newer pack
        new_packs = [{"code": "new", "date_release": "2013-01-01"}]
        assert self.cache_manager.is_cache_valid(new_packs) is False

    def test_is_cache_valid_old_cache(self) -> None:
        """Test cache validity with old cache."""
        # Create cache files
        self.cache_manager.cache_cards({})
        self.cache_manager.cache_packs([])

        # Set metadata with old timestamp
        metadata = {
            "timestamp": time.time() - 700000,  # More than 7 days
            "latest_pack_date": "2012-08-29",
        }
        self.cache_manager.update_cache_metadata(metadata)

        assert self.cache_manager.is_cache_valid() is False

    def test_is_cache_valid_fresh(self) -> None:
        """Test cache validity with fresh cache."""
        # Create cache files
        self.cache_manager.cache_cards({})
        self.cache_manager.cache_packs([])

        # Set fresh metadata
        metadata = {"timestamp": time.time(), "latest_pack_date": "2012-08-29"}
        self.cache_manager.update_cache_metadata(metadata)

        # Check with same pack data
        packs = [{"code": "core", "date_release": "2012-08-29"}]
        assert self.cache_manager.is_cache_valid(packs) is True

    def test_mark_cache_fresh(self) -> None:
        """Test marking cache as fresh."""
        packs = [
            {"code": "core", "date_release": "2012-08-29"},
            {"code": "wla", "date_release": "2012-12-14"},
        ]

        self.cache_manager.mark_cache_fresh(packs)

        metadata = self.cache_manager.get_cache_metadata()
        assert "timestamp" in metadata
        assert metadata["latest_pack_date"] == "2012-12-14"
        assert metadata["pack_count"] == 2
