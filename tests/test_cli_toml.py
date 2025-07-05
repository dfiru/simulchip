"""Test CLI commands with TOML configuration."""

# Standard library imports
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

# Third-party imports
import pytest
import toml

# First-party imports
from simulchip.api.netrunnerdb import NetrunnerDBAPI
from simulchip.cli.main import NetrunnerProxyCLI
from simulchip.collection.manager import CollectionManager


@pytest.fixture
def temp_collection_file():
    """Create a temporary collection file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        collection_data = {
            "packs": ["core"],
            "cards": {"01001": 3, "30001": 2},
            "missing": {"01001": 1},
        }
        toml.dump(collection_data, f)
        temp_path = f.name

    yield temp_path

    # Cleanup
    os.unlink(temp_path)


@pytest.fixture
def mock_api():
    """Create a mock API client with sample data."""
    api = Mock(spec=NetrunnerDBAPI)

    # Sample card data
    api.get_all_cards.return_value = {
        "01001": {
            "code": "01001",
            "title": "Noise: Hacker Extraordinaire",
            "type_code": "identity",
            "faction_code": "anarch",
            "pack_code": "core",
        },
        "30001": {
            "code": "30001",
            "title": "Zahya Sadeghi: Versatile Smuggler",
            "type_code": "identity",
            "faction_code": "criminal",
            "pack_code": "sg",
        },
        "30010": {
            "code": "30010",
            "title": "Sure Gamble",
            "type_code": "event",
            "faction_code": "anarch",
            "pack_code": "sg",
        },
    }

    # Sample pack data
    api.get_all_packs.return_value = [
        {
            "code": "core",
            "name": "Core Set",
            "position": 1,
            "cycle_code": "core",
            "cycle": "Core Set",
            "date_release": "2012-09-06",
        },
        {
            "code": "sg",
            "name": "System Gateway",
            "position": 1,
            "cycle_code": "sg21",
            "cycle": "System Gateway",
            "date_release": "2021-03-05",
        },
        {
            "code": "ms",
            "name": "Midnight Sun",
            "position": 1,
            "cycle_code": "ms",
            "cycle": "Midnight Sun",
            "date_release": "2022-03-01",
        },
    ]

    api.get_pack_by_code.side_effect = lambda code: next(
        (p for p in api.get_all_packs.return_value if p["code"] == code), None
    )

    api.get_card_by_code.side_effect = lambda code: api.get_all_cards.return_value.get(
        code
    )

    # Mock cache for PDF generation
    api.cache = Mock()
    api.cache.get_card_image.return_value = None
    api.cache.download_and_cache_image.return_value = None

    # Sample decklist data
    api.get_decklist.return_value = {
        "id": "12345678-1234-5678-9012-123456789012",
        "name": "Test Deck",
        "cards": {"30001": 1, "30010": 3},  # Zahya (identity)  # Sure Gamble
    }

    return api


class TestCLIInit:
    """Test the init command."""

    def test_init_toml_format(self, tmp_path):
        """Test creating a TOML collection file."""
        collection_file = tmp_path / "test_collection.toml"

        cli = NetrunnerProxyCLI()

        # Mock input to avoid interactive prompt
        with patch("builtins.input", return_value="y"):
            cli.init(str(collection_file))

        assert collection_file.exists()

        # Check file contents
        with open(collection_file) as f:
            data = toml.load(f)

        # Should be empty but valid structure
        assert isinstance(data, dict)

    def test_init_default_extension(self, tmp_path):
        """Test that init adds .toml extension if missing."""
        collection_file = tmp_path / "test_collection"

        cli = NetrunnerProxyCLI()
        cli.init(str(collection_file))

        expected_file = tmp_path / "test_collection.toml"
        assert expected_file.exists()


class TestCLIPackManagement:
    """Test pack add/remove commands."""

    def test_add_pack(self, temp_collection_file, mock_api):
        """Test adding a pack to collection."""
        cli = NetrunnerProxyCLI(api=mock_api)
        cli.add_pack(temp_collection_file, "ms")

        # Verify pack was added
        manager = CollectionManager(Path(temp_collection_file), mock_api)
        assert manager.has_pack("ms")

    def test_remove_pack(self, temp_collection_file, mock_api):
        """Test removing a pack from collection."""
        cli = NetrunnerProxyCLI(api=mock_api)

        # First verify the pack exists
        manager = CollectionManager(Path(temp_collection_file), mock_api)
        assert manager.has_pack("core")

        # Remove it
        cli.remove_pack(temp_collection_file, "core")

        # Verify it's gone
        manager_after = CollectionManager(Path(temp_collection_file), mock_api)
        assert not manager_after.has_pack("core")


class TestCLICardManagement:
    """Test individual card add/remove commands."""

    def test_add_card(self, temp_collection_file, mock_api):
        """Test adding individual cards."""
        cli = NetrunnerProxyCLI(api=mock_api)
        cli.add(temp_collection_file, "30010", count=2)

        # Verify card was added
        manager = CollectionManager(Path(temp_collection_file), mock_api)
        assert manager.get_card_count("30010") >= 2

    def test_remove_card(self, temp_collection_file, mock_api):
        """Test removing individual cards."""
        cli = NetrunnerProxyCLI(api=mock_api)

        # Use a card that doesn't have any missing entries so removal affects actual cards
        initial_count = CollectionManager(
            Path(temp_collection_file), mock_api
        ).get_card_count("30001")

        cli.remove(temp_collection_file, "30001", count=1)

        final_count = CollectionManager(
            Path(temp_collection_file), mock_api
        ).get_card_count("30001")
        assert final_count < initial_count


class TestCLIMissingCards:
    """Test missing card management commands."""

    def test_mark_missing(self, temp_collection_file, mock_api):
        """Test marking cards as missing."""
        cli = NetrunnerProxyCLI(api=mock_api)
        cli.mark_missing(temp_collection_file, "30010", count=1)

        # Verify card was marked as missing
        manager = CollectionManager(Path(temp_collection_file), mock_api)
        assert "30010" in manager.missing_cards
        assert manager.missing_cards["30010"] >= 1

    def test_found_missing(self, temp_collection_file, mock_api):
        """Test marking missing cards as found."""
        cli = NetrunnerProxyCLI(api=mock_api)

        # Verify we have missing cards to start
        manager = CollectionManager(Path(temp_collection_file), mock_api)
        initial_missing = manager.missing_cards.get("01001", 0)
        assert initial_missing > 0

        cli.found(temp_collection_file, "01001", count=1)

        # Verify missing count decreased
        manager_after = CollectionManager(Path(temp_collection_file), mock_api)
        final_missing = manager_after.missing_cards.get("01001", 0)
        assert final_missing < initial_missing


class TestCLIStats:
    """Test stats command."""

    def test_stats_display(self, temp_collection_file, mock_api, capsys):
        """Test stats command displays information."""
        cli = NetrunnerProxyCLI(api=mock_api)
        cli.stats(temp_collection_file)

        captured = capsys.readouterr()
        assert "Collection Statistics:" in captured.out
        assert "Unique cards:" in captured.out
        assert "Total cards:" in captured.out
        assert "Missing cards:" in captured.out


class TestCLIListPacks:
    """Test list_packs command."""

    def test_list_packs(self, mock_api, capsys):
        """Test listing available packs."""
        cli = NetrunnerProxyCLI(api=mock_api)
        cli.list_packs()

        captured = capsys.readouterr()
        assert "Core Set" in captured.out
        assert "System Gateway" in captured.out


class TestCLICompare:
    """Test compare command (main functionality)."""

    def test_compare_decklist(self, temp_collection_file, mock_api, capsys):
        """Test comparing a decklist against collection."""
        cli = NetrunnerProxyCLI(api=mock_api)
        cli.compare(
            "https://netrunnerdb.com/en/decklist/12345678-1234-5678-9012-123456789012/test-deck",
            collection=temp_collection_file,
        )

        captured = capsys.readouterr()
        assert "Test Deck" in captured.out
        assert "Total cards needed:" in captured.out
        assert "Cards owned:" in captured.out
        assert "Cards missing:" in captured.out

    @patch("simulchip.cli.main.ProxyPDFGenerator")
    def test_compare_with_pdf_output(
        self, mock_pdf_gen, temp_collection_file, mock_api, tmp_path
    ):
        """Test compare command with PDF generation."""
        cli = NetrunnerProxyCLI(api=mock_api)
        output_file = tmp_path / "test_output.pdf"

        # Mock PDF generator
        mock_pdf_instance = Mock()
        mock_pdf_gen.return_value = mock_pdf_instance

        cli.compare(
            "https://netrunnerdb.com/en/decklist/12345678-1234-5678-9012-123456789012/test-deck",
            collection=temp_collection_file,
            output=str(output_file),
        )

        # Should call PDF generator if there are missing cards
        if mock_api.get_decklist.return_value["cards"]:
            mock_pdf_gen.assert_called_once()


class TestCLICache:
    """Test cache management commands."""

    def test_cache_stats(self, capsys):
        """Test cache stats display."""
        mock_cache_instance = Mock()
        mock_cache_instance.get_cache_stats.return_value = {
            "cards_cached": True,
            "packs_cached": True,
            "images_cached": 42,
            "cache_size_mb": 15.5,
        }

        cli = NetrunnerProxyCLI(cache_manager=mock_cache_instance)
        cli.cache(stats=True)

        captured = capsys.readouterr()
        assert "Cache Statistics:" in captured.out
        assert "Cards cached: Yes" in captured.out
        assert "Images cached: 42" in captured.out

    def test_cache_clear(self):
        """Test cache clear functionality."""
        mock_cache_instance = Mock()
        cli = NetrunnerProxyCLI(cache_manager=mock_cache_instance)
        cli.cache(clear=True)
        mock_cache_instance.clear_cache.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
