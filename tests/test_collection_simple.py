"""Simple tests for collection management functionality."""

# Standard library imports
import tempfile
from pathlib import Path
from typing import Dict, Optional

# Third-party imports
import pytest
import toml

# First-party imports
from simulchip.api.netrunnerdb import CardData, PackData
from simulchip.collection.manager import CollectionError, CollectionManager


class MockAPIClient:
    """Mock API client that implements the APIClient protocol."""

    def __init__(self) -> None:
        """Initialize mock API with test data."""
        self.cards = {
            "01001": {
                "code": "01001",
                "title": "Test Card 1",
                "type_code": "program",
                "faction_code": "anarch",
                "pack_code": "core",
                "quantity": 3,
                "deck_limit": 3,
                "image_url": "https://example.com/01001.png",
            },
            "01002": {
                "code": "01002",
                "title": "Test Card 2",
                "type_code": "event",
                "faction_code": "criminal",
                "pack_code": "core",
                "quantity": 3,
                "deck_limit": 3,
                "image_url": "https://example.com/01002.png",
            },
        }

        self.packs = {
            "core": {
                "code": "core",
                "name": "Core Set",
                "position": 1,
                "cycle_code": "core",
                "cycle": "Core",
                "date_release": "2012-08-29",
            }
        }

    def get_all_cards(self) -> Dict[str, CardData]:
        """Return mock card data."""
        return self.cards  # type: ignore[return-value]

    def get_pack_by_code(self, pack_code: str) -> Optional[PackData]:
        """Return mock pack by code."""
        return self.packs.get(pack_code)  # type: ignore[return-value]


class TestCollectionManagerSimple:
    """Simple tests for collection manager."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.collection_path = Path(self.temp_dir) / "test_collection.toml"
        self.api = MockAPIClient()

    def test_init_new_collection(self) -> None:
        """Test initialization of a new collection."""
        manager = CollectionManager(collection_file=self.collection_path, api=self.api)

        assert manager.collection_file == self.collection_path
        assert manager.api == self.api
        assert manager.owned_packs == set()
        assert manager.collection == {}
        assert manager.missing_cards == {}

    def test_init_existing_collection(self) -> None:
        """Test initialization from existing collection file."""
        # Create a test collection file
        collection_data = {
            "packs": ["core"],
            "cards": {"01001": 2},
            "missing": {"01002": 1},
        }

        with open(self.collection_path, "w") as f:
            toml.dump(collection_data, f)

        # Initialize manager from existing file
        manager = CollectionManager(collection_file=self.collection_path, api=self.api)

        assert manager.owned_packs == {"core"}
        assert manager.collection.get("01001") == 2
        assert manager.missing_cards.get("01002") == 1

    def test_load_invalid_collection_file(self) -> None:
        """Test handling of invalid collection file."""
        # Create invalid TOML file
        with open(self.collection_path, "w") as f:
            f.write("invalid toml content [[[")

        with pytest.raises(CollectionError, match="Failed to parse"):
            CollectionManager(collection_file=self.collection_path, api=self.api)

    def test_save_collection(self) -> None:
        """Test saving collection to file."""
        manager = CollectionManager(collection_file=self.collection_path, api=self.api)

        # Add some data
        manager.owned_packs.add("core")
        manager.collection["01001"] = 3
        manager.missing_cards["01002"] = 1

        manager.save_collection()

        # Verify file was created and contains correct data
        assert self.collection_path.exists()

        with open(self.collection_path) as f:
            data = toml.load(f)

        assert "core" in data["packs"]
        assert data["cards"]["01001"] == 3
        assert data["missing"]["01002"] == 1

    def test_collection_without_api(self) -> None:
        """Test that collection can work without API for basic operations."""
        manager = CollectionManager(collection_file=self.collection_path)

        # Should be able to do basic operations
        manager.collection["01001"] = 3
        manager.missing_cards["01002"] = 1
        manager.save_collection()

        assert self.collection_path.exists()

    def test_unsupported_file_format(self) -> None:
        """Test handling of unsupported file formats."""
        json_path = Path(self.temp_dir) / "collection.json"
        json_path.write_text('{"test": "data"}')

        with pytest.raises(CollectionError, match="Unsupported file format"):
            CollectionManager(collection_file=json_path, api=self.api)
