"""Tests for smart cache validation based on pack releases."""

# Standard library imports
import tempfile
import time
from pathlib import Path

# Third-party imports
import pytest

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
        self.cached_packs = [{"code": "core", "name": "Core Set"}]

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
