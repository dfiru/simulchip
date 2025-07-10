"""Tests for filtering utilities and functions."""

# Standard library imports
from unittest.mock import Mock

# First-party imports
from simulchip.filters import (
    create_card_filter,
    create_pack_filter,
    filter_cards,
    filter_cards_raw,
    filter_items_generic,
    filter_packs,
    filter_packs_raw,
)
from simulchip.models import CardModel, PackModel


class TestFilterPacksRaw:
    """Test raw pack filtering functionality."""

    def test_filter_packs_by_name(self):
        """Should filter packs by name."""
        packs = [
            {"code": "core", "name": "Core Set", "cycle": "Genesis"},
            {"code": "wla", "name": "What Lies Ahead", "cycle": "Genesis"},
            {"code": "sg", "name": "System Gateway", "cycle": "System Update 2021"},
        ]

        result = filter_packs_raw(packs, "Core")

        assert len(result) == 1
        assert result[0]["code"] == "core"

    def test_filter_packs_by_code(self):
        """Should filter packs by code."""
        packs = [
            {"code": "core", "name": "Core Set", "cycle": "Genesis"},
            {"code": "wla", "name": "What Lies Ahead", "cycle": "Genesis"},
            {"code": "sg", "name": "System Gateway", "cycle": "System Update 2021"},
        ]

        result = filter_packs_raw(packs, "sg")

        assert len(result) == 1
        assert result[0]["code"] == "sg"

    def test_filter_packs_by_cycle(self):
        """Should filter packs by cycle."""
        packs = [
            {"code": "core", "name": "Core Set", "cycle": "Genesis"},
            {"code": "wla", "name": "What Lies Ahead", "cycle": "Genesis"},
            {"code": "sg", "name": "System Gateway", "cycle": "System Update 2021"},
        ]

        result = filter_packs_raw(packs, "Genesis")

        assert len(result) == 2
        assert all(pack["cycle"] == "Genesis" for pack in result)

    def test_filter_packs_case_insensitive(self):
        """Should filter packs case-insensitively."""
        packs = [
            {"code": "core", "name": "Core Set", "cycle": "Genesis"},
        ]

        result = filter_packs_raw(packs, "core set")
        assert len(result) == 1

        result = filter_packs_raw(packs, "CORE SET")
        assert len(result) == 1

        result = filter_packs_raw(packs, "genesis")
        assert len(result) == 1

    def test_filter_packs_no_match(self):
        """Should return empty list when no matches."""
        packs = [
            {"code": "core", "name": "Core Set", "cycle": "Genesis"},
        ]

        result = filter_packs_raw(packs, "nonexistent")
        assert result == []

    def test_filter_packs_empty_filter(self):
        """Should return all packs when filter is empty."""
        packs = [
            {"code": "core", "name": "Core Set", "cycle": "Genesis"},
            {"code": "wla", "name": "What Lies Ahead", "cycle": "Genesis"},
        ]

        result = filter_packs_raw(packs, "")
        assert result == packs

        result = filter_packs_raw(packs)  # Default parameter
        assert result == packs

    def test_filter_packs_missing_fields(self):
        """Should handle packs with missing fields gracefully."""
        packs = [
            {"code": "core", "name": "Core Set"},  # Missing cycle
            {"name": "No Code Pack", "cycle": "Genesis"},  # Missing code
            {"code": "sg", "cycle": "System Update 2021"},  # Missing name
        ]

        # Should not crash and should handle missing fields
        result = filter_packs_raw(packs, "core")
        assert len(result) == 1
        assert result[0]["code"] == "core"


class TestFilterCardsRaw:
    """Test raw card filtering functionality."""

    def test_filter_cards_by_title(self):
        """Should filter cards by title."""
        cards = [
            {
                "code": "01001",
                "title": "Wyldside",
                "type_code": "resource",
                "faction_code": "anarch",
            },
            {
                "code": "01002",
                "title": "Diesel",
                "type_code": "event",
                "faction_code": "shaper",
            },
            {
                "code": "01003",
                "title": "Sure Gamble",
                "type_code": "event",
                "faction_code": "neutral-runner",
            },
        ]

        result = filter_cards_raw(cards, "Wyldside")

        assert len(result) == 1
        assert result[0]["code"] == "01001"

    def test_filter_cards_by_type(self):
        """Should filter cards by type."""
        cards = [
            {
                "code": "01001",
                "title": "Wyldside",
                "type_code": "resource",
                "faction_code": "anarch",
            },
            {
                "code": "01002",
                "title": "Diesel",
                "type_code": "event",
                "faction_code": "shaper",
            },
            {
                "code": "01003",
                "title": "Sure Gamble",
                "type_code": "event",
                "faction_code": "neutral-runner",
            },
        ]

        result = filter_cards_raw(cards, "event")

        assert len(result) == 2
        assert all(card["type_code"] == "event" for card in result)

    def test_filter_cards_by_faction(self):
        """Should filter cards by faction."""
        cards = [
            {
                "code": "01001",
                "title": "Wyldside",
                "type_code": "resource",
                "faction_code": "anarch",
            },
            {
                "code": "01002",
                "title": "Diesel",
                "type_code": "event",
                "faction_code": "shaper",
            },
            {
                "code": "01003",
                "title": "Sure Gamble",
                "type_code": "event",
                "faction_code": "neutral-runner",
            },
        ]

        result = filter_cards_raw(cards, "anarch")

        assert len(result) == 1
        assert result[0]["faction_code"] == "anarch"

    def test_filter_cards_by_text(self):
        """Should filter cards by card text."""
        cards = [
            {
                "code": "01001",
                "title": "Wyldside",
                "type_code": "resource",
                "faction_code": "anarch",
                "text": "Draw 2 cards",
            },
            {
                "code": "01002",
                "title": "Diesel",
                "type_code": "event",
                "faction_code": "shaper",
                "text": "Draw 3 cards",
            },
            {
                "code": "01003",
                "title": "Sure Gamble",
                "type_code": "event",
                "faction_code": "neutral-runner",
                "text": "Gain 9 credits",
            },
        ]

        result = filter_cards_raw(cards, "draw")

        assert len(result) == 2
        assert all("Draw" in card["text"] for card in result)

    def test_filter_cards_expected_only_mode(self):
        """Should filter cards based on expected-only mode."""
        cards = [
            {"code": "01001", "title": "Wyldside"},
            {"code": "01002", "title": "Diesel"},
            {"code": "01003", "title": "Sure Gamble"},
        ]

        # Mock manager that returns expected counts
        mock_manager = Mock()
        mock_manager.get_expected_card_count.side_effect = lambda code: {
            "01001": 3,  # Expected
            "01002": 0,  # Not expected
            "01003": 2,  # Expected
        }.get(code, 0)

        result = filter_cards_raw(cards, "", mock_manager, show_expected_only=True)

        assert len(result) == 2
        assert result[0]["code"] == "01001"
        assert result[1]["code"] == "01003"

    def test_filter_cards_combined_filters(self):
        """Should combine text filter and expected-only mode."""
        cards = [
            {"code": "01001", "title": "Wyldside", "text": "Draw 2 cards"},
            {"code": "01002", "title": "Diesel", "text": "Draw 3 cards"},
            {"code": "01003", "title": "Sure Gamble", "text": "Gain 9 credits"},
        ]

        mock_manager = Mock()
        mock_manager.get_expected_card_count.side_effect = lambda code: {
            "01001": 3,  # Expected
            "01002": 0,  # Not expected
            "01003": 2,  # Expected
        }.get(code, 0)

        result = filter_cards_raw(cards, "draw", mock_manager, show_expected_only=True)

        # Should only include Wyldside (expected + matches "draw")
        assert len(result) == 1
        assert result[0]["code"] == "01001"

    def test_filter_cards_case_insensitive(self):
        """Should filter cards case-insensitively."""
        cards = [
            {
                "code": "01001",
                "title": "Wyldside",
                "type_code": "resource",
                "faction_code": "anarch",
            },
        ]

        result = filter_cards_raw(cards, "WYLDSIDE")
        assert len(result) == 1

        result = filter_cards_raw(cards, "wyldside")
        assert len(result) == 1

    def test_filter_cards_no_manager(self):
        """Should handle missing manager gracefully."""
        cards = [
            {"code": "01001", "title": "Wyldside"},
        ]

        # Should not crash when manager is None
        result = filter_cards_raw(cards, "", None, show_expected_only=True)
        assert result == cards  # Should return all cards when no manager


class TestFilterPacksWithModels:
    """Test pack filtering with PackModel objects."""

    def test_filter_packs_returns_models(self):
        """Should return PackModel objects."""
        packs = [
            {"code": "core", "name": "Core Set", "cycle": "Genesis"},
        ]

        result = filter_packs(packs, "core")

        assert len(result) == 1
        assert isinstance(result[0], PackModel)
        assert result[0].code == "core"

    def test_filter_packs_with_ownership(self):
        """Should filter by ownership when specified."""
        packs = [
            {"code": "core", "name": "Core Set"},
            {"code": "wla", "name": "What Lies Ahead"},
            {"code": "sg", "name": "System Gateway"},
        ]

        owned_packs = {"core", "sg"}

        result = filter_packs(packs, "", owned_packs, show_owned_only=True)

        assert len(result) == 2
        assert {pack.code for pack in result} == {"core", "sg"}


class TestFilterCardsWithModels:
    """Test card filtering with CardModel objects."""

    def test_filter_cards_returns_models(self):
        """Should return CardModel objects."""
        cards = [
            {"code": "01001", "title": "Wyldside", "type_code": "resource"},
        ]

        result = filter_cards(cards, "wyld")

        assert len(result) == 1
        assert isinstance(result[0], CardModel)
        assert result[0].code == "01001"

    def test_filter_cards_with_expected(self):
        """Should filter by expected quantities when specified."""
        cards = [
            {"code": "01001", "title": "Wyldside"},
            {"code": "01002", "title": "Diesel"},
        ]

        expected_cards = {"01001": 3}  # Only Wyldside expected

        result = filter_cards(cards, "", expected_cards, show_expected_only=True)

        assert len(result) == 1
        assert result[0].code == "01001"


class TestCreateFilters:
    """Test filter function creation."""

    def test_create_pack_filter_basic(self):
        """Should create functional pack filter."""
        pack_model = Mock(spec=PackModel)
        pack_model.code = "core"

        filter_func = create_pack_filter()

        # Should always return True for basic filter
        assert filter_func(pack_model) is True

    def test_create_pack_filter_with_ownership(self):
        """Should create pack filter that respects ownership."""
        owned_packs = {"core", "sg"}
        filter_func = create_pack_filter(owned_packs, show_owned_only=True)

        # Test owned pack
        owned_pack = Mock(spec=PackModel)
        owned_pack.code = "core"
        assert filter_func(owned_pack) is True

        # Test unowned pack
        unowned_pack = Mock(spec=PackModel)
        unowned_pack.code = "wla"
        assert filter_func(unowned_pack) is False

    def test_create_card_filter_basic(self):
        """Should create functional card filter."""
        card_model = Mock(spec=CardModel)
        card_model.code = "01001"

        filter_func = create_card_filter()

        # Should always return True for basic filter
        assert filter_func(card_model) is True

    def test_create_card_filter_with_expected(self):
        """Should create card filter that respects expected quantities."""
        expected_cards = {"01001": 3}
        filter_func = create_card_filter(expected_cards, show_expected_only=True)

        # Test expected card
        expected_card = Mock(spec=CardModel)
        expected_card.code = "01001"
        assert filter_func(expected_card) is True

        # Test unexpected card
        unexpected_card = Mock(spec=CardModel)
        unexpected_card.code = "01002"
        assert filter_func(unexpected_card) is False


class TestFilterItemsGeneric:
    """Test generic item filtering."""

    def test_filter_items_with_matches_filter_method(self):
        """Should use matches_filter method when available."""
        # Mock items with matches_filter method
        item1 = Mock()
        item1.matches_filter.return_value = True

        item2 = Mock()
        item2.matches_filter.return_value = False

        items = [item1, item2]

        result = filter_items_generic(items, "test")

        assert len(result) == 1
        assert result[0] is item1

        # Verify matches_filter was called with lowercase
        item1.matches_filter.assert_called_with("test")
        item2.matches_filter.assert_called_with("test")

    def test_filter_items_fallback_to_string(self):
        """Should fall back to string representation when no matches_filter method."""
        # Mock items without matches_filter method
        item1 = Mock()
        item1.matches_filter = None  # No method
        del item1.matches_filter  # Remove attribute
        item1.__str__ = Mock(return_value="test content")

        item2 = Mock()
        item2.matches_filter = None
        del item2.matches_filter
        item2.__str__ = Mock(return_value="other content")

        items = [item1, item2]

        result = filter_items_generic(items, "test")

        assert len(result) == 1
        assert result[0] is item1

    def test_filter_items_empty_filter(self):
        """Should return all items when filter is empty."""
        items = [Mock(), Mock(), Mock()]

        result = filter_items_generic(items, "")

        assert result == items

    def test_filter_items_mixed_types(self):
        """Should handle mixed item types gracefully."""
        # Mix of items with and without matches_filter
        item_with_method = Mock()
        item_with_method.matches_filter.return_value = True

        item_without_method = Mock()
        del item_without_method.matches_filter
        item_without_method.__str__ = Mock(return_value="filter match")

        items = [item_with_method, item_without_method]

        result = filter_items_generic(items, "filter")

        assert len(result) == 2  # Both should match


class TestFilterEdgeCases:
    """Test edge cases and error conditions."""

    def test_filter_empty_lists(self):
        """Should handle empty input lists gracefully."""
        assert filter_packs_raw([], "test") == []
        assert filter_cards_raw([], "test") == []
        assert filter_packs([], "test") == []
        assert filter_cards([], "test") == []
        assert filter_items_generic([], "test") == []

    def test_filter_none_values(self):
        """Should handle None values in data gracefully."""
        packs = [
            {"code": None, "name": "Test Pack", "cycle": "Test"},
            {"code": "test", "name": None, "cycle": "Test"},
        ]

        # Should not crash
        result = filter_packs_raw(packs, "test")
        assert isinstance(result, list)

    def test_filter_special_characters(self):
        """Should handle special characters in filter text."""
        packs = [
            {"code": "core", "name": "Core Set: Revised", "cycle": "Genesis"},
        ]

        result = filter_packs_raw(packs, "Core Set:")
        assert len(result) == 1

        result = filter_packs_raw(packs, "Set:")
        assert len(result) == 1
