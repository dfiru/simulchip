"""Tests for CLI utilities and business logic."""

# Standard library imports
import tempfile
from pathlib import Path

# First-party imports
from simulchip.cli_utils import (
    DEFAULT_PAGE_SIZE,
    NavigationConfig,
    calculate_collection_stats,
    calculate_selection_bounds,
    ensure_collection_directory,
    ensure_output_directory,
    filter_valid_packs,
    get_card_quantity_action,
    get_navigation_page_size,
    get_proxy_generation_message,
    resolve_collection_path,
    should_generate_proxies,
    should_ignore_pack_toggle_errors,
    should_reset_selection_on_filter_change,
    validate_collection_exists,
    validate_pack_selection,
)
from simulchip.paths import DEFAULT_COLLECTION_PATH


class TestResolveCollectionPath:
    """Test collection path resolution logic."""

    def test_returns_provided_path_when_given(self):
        """Should return the provided path when not None."""
        custom_path = Path("/custom/collection.toml")
        result = resolve_collection_path(custom_path)
        assert result == custom_path

    def test_returns_default_when_none(self):
        """Should return default path when None provided."""
        result = resolve_collection_path(None)
        assert result == DEFAULT_COLLECTION_PATH

    def test_handles_pathlib_path_objects(self):
        """Should handle Path objects correctly."""
        path_obj = Path("/some/path/collection.toml")
        result = resolve_collection_path(path_obj)
        assert result == path_obj
        assert isinstance(result, Path)


class TestEnsureDirectories:
    """Test directory creation logic."""

    def test_ensure_collection_directory_creates_parent(self):
        """Should create parent directory for collection file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection_file = Path(tmpdir) / "new_dir" / "collection.toml"
            assert not collection_file.parent.exists()

            ensure_collection_directory(collection_file)

            assert collection_file.parent.exists()
            assert collection_file.parent.is_dir()

    def test_ensure_output_directory_creates_parent(self):
        """Should create parent directory for output file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "new_dir" / "output.pdf"
            assert not output_file.parent.exists()

            ensure_output_directory(output_file)

            assert output_file.parent.exists()
            assert output_file.parent.is_dir()

    def test_ensure_directories_handles_existing_dirs(self):
        """Should handle existing directories gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection_file = Path(tmpdir) / "collection.toml"

            # Should not raise error for existing directory
            ensure_collection_directory(collection_file)
            ensure_output_directory(collection_file)


class TestValidateCollectionExists:
    """Test collection file validation."""

    def test_returns_true_for_existing_file(self):
        """Should return True for existing files."""
        with tempfile.NamedTemporaryFile() as tmpfile:
            path = Path(tmpfile.name)
            assert validate_collection_exists(path) is True

    def test_returns_false_for_nonexistent_file(self):
        """Should return False for non-existent files."""
        path = Path("/nonexistent/file.toml")
        assert validate_collection_exists(path) is False

    def test_returns_false_for_directory(self):
        """Should return False for directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            # Directory exists but is not a file
            assert validate_collection_exists(path) is False


class TestProxyGeneration:
    """Test proxy generation decision logic."""

    def test_should_generate_proxies_with_cards(self):
        """Should return True when there are cards to proxy."""
        proxy_cards = [{"code": "01001"}, {"code": "01002"}]
        assert should_generate_proxies(proxy_cards) is True

    def test_should_not_generate_proxies_when_empty(self):
        """Should return False when no cards to proxy."""
        assert should_generate_proxies([]) is False

    def test_get_proxy_generation_message_all_cards(self):
        """Should return appropriate message for all cards."""
        proxy_cards = [{"code": "01001"}, {"code": "01002"}]
        message = get_proxy_generation_message(proxy_cards, all_cards=True)
        assert message == "Generating proxies for all 2 cards"

    def test_get_proxy_generation_message_missing_cards(self):
        """Should return appropriate message for missing cards."""
        proxy_cards = [{"code": "01001"}]
        message = get_proxy_generation_message(proxy_cards, all_cards=False)
        assert message == "Generating proxies for 1 missing cards"


class TestPackFiltering:
    """Test pack filtering and validation logic."""

    def test_filter_valid_packs_includes_valid(self):
        """Should include packs with both code and name."""
        packs = [
            {"code": "core", "name": "Core Set"},
            {"code": "sg", "name": "System Gateway"},
        ]
        result = filter_valid_packs(packs)
        assert len(result) == 2
        assert result == packs

    def test_filter_valid_packs_excludes_incomplete(self):
        """Should exclude packs missing code or name."""
        packs = [
            {"code": "core", "name": "Core Set"},  # Valid
            {"code": "sg"},  # Missing name
            {"name": "No Code Pack"},  # Missing code
            {"code": "", "name": "Empty Code"},  # Empty code
            {"code": "valid", "name": ""},  # Empty name
        ]
        result = filter_valid_packs(packs)
        assert len(result) == 1
        assert result[0]["code"] == "core"

    def test_calculate_collection_stats(self):
        """Should calculate correct collection statistics."""
        owned_packs = {"core", "sg"}
        all_packs = [
            {"code": "core", "name": "Core Set"},
            {"code": "sg", "name": "System Gateway"},
            {"code": "invalid"},  # Invalid pack
            {"code": "ru", "name": "Reign and Reverie"},
        ]

        stats = calculate_collection_stats(owned_packs, all_packs)

        assert stats["owned_count"] == 2
        assert stats["total_count"] == 3  # Only valid packs counted


class TestPackSelection:
    """Test pack selection validation logic."""

    def test_validate_pack_selection_valid_number(self):
        """Should validate correct pack selection."""
        is_valid, choice_idx = validate_pack_selection("2", 5)
        assert is_valid is True
        assert choice_idx == 1  # Convert to 0-based index

    def test_validate_pack_selection_cancel(self):
        """Should handle cancel (0) selection."""
        is_valid, choice_idx = validate_pack_selection("0", 5)
        assert is_valid is True
        assert choice_idx is None

    def test_validate_pack_selection_out_of_range(self):
        """Should reject out of range selections."""
        is_valid, choice_idx = validate_pack_selection("6", 5)
        assert is_valid is False
        assert choice_idx is None

        is_valid, choice_idx = validate_pack_selection("-1", 5)
        assert is_valid is False
        assert choice_idx is None

    def test_validate_pack_selection_invalid_input(self):
        """Should reject non-numeric input."""
        is_valid, choice_idx = validate_pack_selection("abc", 5)
        assert is_valid is False
        assert choice_idx is None

        is_valid, choice_idx = validate_pack_selection("", 5)
        assert is_valid is False
        assert choice_idx is None


class TestSelectionBounds:
    """Test selection bounds calculation logic."""

    def test_calculate_selection_bounds_up(self):
        """Should move selection up correctly."""
        result = calculate_selection_bounds(5, 10, "up")
        assert result == 4

        # Should not go below 0
        result = calculate_selection_bounds(0, 10, "up")
        assert result == 0

    def test_calculate_selection_bounds_down(self):
        """Should move selection down correctly."""
        result = calculate_selection_bounds(5, 10, "down")
        assert result == 6

        # Should not go beyond total items
        result = calculate_selection_bounds(9, 10, "down")
        assert result == 9

    def test_calculate_selection_bounds_page_operations(self):
        """Should handle page up/down operations."""
        # Page up
        result = calculate_selection_bounds(15, 20, "page_up")
        assert result == 5  # 15 - 10 (page size)

        # Page down
        result = calculate_selection_bounds(5, 20, "page_down")
        assert result == 15  # 5 + 10 (page size)

        # Page up from near beginning
        result = calculate_selection_bounds(3, 20, "page_up")
        assert result == 0

        # Page down from near end
        result = calculate_selection_bounds(15, 20, "page_down")
        assert result == 19

    def test_calculate_selection_bounds_top_bottom(self):
        """Should handle top/bottom navigation."""
        result = calculate_selection_bounds(5, 10, "top")
        assert result == 0

        result = calculate_selection_bounds(5, 10, "bottom")
        assert result == 9

    def test_calculate_selection_bounds_empty_list(self):
        """Should handle empty lists gracefully."""
        result = calculate_selection_bounds(0, 0, "up")
        assert result == 0

        result = calculate_selection_bounds(5, 0, "down")
        assert result == 0

    def test_calculate_selection_bounds_bounds_correction(self):
        """Should correct out-of-bounds indices."""
        result = calculate_selection_bounds(15, 10, "none")
        assert result == 9  # Corrected to last valid index

        result = calculate_selection_bounds(-5, 10, "none")
        assert result == 0  # Corrected to first valid index


class TestCardQuantityActions:
    """Test card quantity action mapping."""

    def test_get_card_quantity_action_arrows(self):
        """Should map arrow keys correctly."""
        action, value = get_card_quantity_action("→")
        assert action == "increment"
        assert value == 1

        action, value = get_card_quantity_action("←")
        assert action == "decrement"
        assert value == 1

        # Also test escape sequence versions
        action, value = get_card_quantity_action("C")  # Right arrow escape
        assert action == "increment"
        assert value == 1

        action, value = get_card_quantity_action("D")  # Left arrow escape
        assert action == "decrement"
        assert value == 1

    def test_get_card_quantity_action_numbers(self):
        """Should map number keys correctly."""
        action, value = get_card_quantity_action("0")
        assert action == "set"
        assert value == 0

        action, value = get_card_quantity_action("5")
        assert action == "set"
        assert value == 5

        action, value = get_card_quantity_action("9")
        assert action == "set"
        assert value == 9

    def test_get_card_quantity_action_invalid(self):
        """Should handle invalid keys."""
        action, value = get_card_quantity_action("a")
        assert action == "none"
        assert value == 0

        action, value = get_card_quantity_action("!")
        assert action == "none"
        assert value == 0


class TestBusinessRules:
    """Test business rule functions."""

    def test_should_reset_selection_on_filter_change(self):
        """Should return consistent business rule for filter reset."""
        result = should_reset_selection_on_filter_change()
        assert isinstance(result, bool)
        assert result is True  # Current business rule

    def test_should_ignore_pack_toggle_errors(self):
        """Should return consistent business rule for error handling."""
        result = should_ignore_pack_toggle_errors()
        assert isinstance(result, bool)
        assert result is True  # Current business rule

    def test_get_navigation_page_size(self):
        """Should return consistent page size."""
        result = get_navigation_page_size()
        assert isinstance(result, int)
        assert result == DEFAULT_PAGE_SIZE
        assert result == 10


class TestNavigationConfig:
    """Test navigation configuration class."""

    def test_navigation_config_initialization(self):
        """Should initialize with correct defaults."""
        config = NavigationConfig()

        assert config.page_size == DEFAULT_PAGE_SIZE
        assert config.reset_selection_on_filter is True
        assert config.ignore_toggle_errors is True

    def test_get_viewport_padding(self):
        """Should return correct viewport padding for interface types."""
        config = NavigationConfig()

        assert config.get_viewport_padding("pack") == 9
        assert config.get_viewport_padding("card") == 11
        assert config.get_viewport_padding("default") == 10
        assert config.get_viewport_padding("unknown") == 10  # Default fallback


class TestConstants:
    """Test module constants."""

    def test_default_page_size(self):
        """Should have reasonable default page size."""
        assert isinstance(DEFAULT_PAGE_SIZE, int)
        assert DEFAULT_PAGE_SIZE > 0
        assert DEFAULT_PAGE_SIZE == 10
