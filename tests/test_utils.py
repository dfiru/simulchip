"""Tests for simulchip utility functions."""

# Third-party imports
import pytest

# First-party imports
from simulchip.utils import (
    FactionCode,
    extract_decklist_id,
    format_card_count,
    format_deck_size,
    get_faction_short_name,
    get_faction_symbol,
    parse_card_code,
    sanitize_filename,
)


class TestExtractDecklistId:
    """Test decklist ID extraction from URLs."""

    def test_extract_uuid_format(self) -> None:
        """Test extraction of UUID-format decklist IDs."""
        url = "https://netrunnerdb.com/en/decklist/7a9e2d43-bd55-45d0-bd2c-99cad2d17d4c/deck-name"
        expected = "7a9e2d43-bd55-45d0-bd2c-99cad2d17d4c"
        assert extract_decklist_id(url) == expected

    def test_extract_numeric_format(self) -> None:
        """Test extraction of numeric decklist IDs."""
        test_cases = [
            ("https://netrunnerdb.com/decklist/12345", "12345"),
            ("https://netrunnerdb.com/decklist/view/67890", "67890"),
            ("https://netrunnerdb.com/en/decklist/54321", "54321"),
        ]

        for url, expected in test_cases:
            assert extract_decklist_id(url) == expected

    def test_invalid_urls(self) -> None:
        """Test handling of invalid URLs."""
        invalid_urls = [
            "https://example.com/decklist/12345",  # Wrong domain
            "not-a-url",  # Not a URL
            "ftp://netrunnerdb.com/decklist/12345",  # Wrong protocol
            "https://netrunnerdb.com/something-else",  # No decklist pattern
        ]

        for url in invalid_urls:
            assert extract_decklist_id(url) is None

    def test_empty_url(self) -> None:
        """Test handling of empty URL."""
        with pytest.raises(ValueError, match="URL cannot be empty"):
            extract_decklist_id("")

    def test_whitespace_handling(self) -> None:
        """Test handling of URLs with whitespace."""
        url_with_spaces = "  https://netrunnerdb.com/en/decklist/12345  "
        assert extract_decklist_id(url_with_spaces) == "12345"


class TestGetFactionSymbol:
    """Test faction symbol retrieval."""

    def test_known_factions(self) -> None:
        """Test symbols for known factions."""
        test_cases = [
            ("anarch", "[A]"),
            ("criminal", "[C]"),
            ("shaper", "[S]"),
            ("haas-bioroid", "[HB]"),
            ("jinteki", "[J]"),
            ("nbn", "[N]"),
            ("weyland-consortium", "[W]"),
        ]

        for faction, expected in test_cases:
            assert get_faction_symbol(faction) == expected

    def test_case_insensitive(self) -> None:
        """Test that faction lookup is case-insensitive."""
        assert get_faction_symbol("ANARCH") == "[A]"
        assert get_faction_symbol("Haas-Bioroid") == "[HB]"

    def test_unknown_faction(self) -> None:
        """Test handling of unknown factions."""
        assert get_faction_symbol("unknown-faction") == "[UN]"

    def test_empty_faction(self) -> None:
        """Test handling of empty faction code."""
        assert get_faction_symbol("") == "[?]"
        assert (
            get_faction_symbol("   ") == "[]"
        )  # Stripped whitespace becomes empty, then [:2] gives []


class TestFormatCardCount:
    """Test card count formatting."""

    def test_valid_counts(self) -> None:
        """Test formatting of valid card counts."""
        test_cases = [
            (1, "Test Card", "1x Test Card"),
            (3, "Another Card", "3x Another Card"),
            (0, "Zero Card", "0x Zero Card"),
        ]

        for count, name, expected in test_cases:
            assert format_card_count(count, name) == expected

    def test_whitespace_handling(self) -> None:
        """Test handling of card names with whitespace."""
        assert format_card_count(2, "  Spaced Card  ") == "2x Spaced Card"

    def test_negative_count(self) -> None:
        """Test handling of negative counts."""
        with pytest.raises(ValueError, match="Count cannot be negative"):
            format_card_count(-1, "Test Card")

    def test_empty_card_name(self) -> None:
        """Test handling of empty card names."""
        with pytest.raises(ValueError, match="Card name cannot be empty"):
            format_card_count(1, "")

        with pytest.raises(ValueError, match="Card name cannot be empty"):
            format_card_count(1, "   ")


class TestSanitizeFilename:
    """Test filename sanitization."""

    def test_valid_filename(self) -> None:
        """Test sanitization of valid filenames."""
        assert sanitize_filename("Valid Filename 123") == "Valid_Filename_123"

    def test_invalid_characters(self) -> None:
        """Test removal of invalid characters."""
        assert sanitize_filename('file<>:"/|?*name') == "file_name"

    def test_length_truncation(self) -> None:
        """Test length truncation."""
        long_name = "a" * 100
        result = sanitize_filename(long_name, max_length=10)
        assert len(result) == 10
        assert result == "a" * 10

    def test_empty_filename(self) -> None:
        """Test handling of empty filenames."""
        with pytest.raises(ValueError, match="Filename cannot be empty"):
            sanitize_filename("")

    def test_sanitized_to_underscore(self) -> None:
        """Test handling of filenames with only special characters."""
        # Special characters get replaced with underscores, then collapsed to single underscore
        result = sanitize_filename("!@#$%^&*()")
        assert result == "_"


class TestGetFactionShortName:
    """Test faction short name generation."""

    def test_known_factions(self) -> None:
        """Test short names for known factions."""
        test_cases = [
            ("anarch", "ana"),
            ("criminal", "crim"),
            ("shaper", "shap"),
            ("haas-bioroid", "hb"),
            ("weyland-consortium", "wey"),
        ]

        for faction, expected in test_cases:
            assert get_faction_short_name(faction) == expected

    def test_unknown_faction(self) -> None:
        """Test short names for unknown factions."""
        assert get_faction_short_name("unknown-faction") == "unkn"
        assert get_faction_short_name("verylongfactionname") == "very"

    def test_empty_faction(self) -> None:
        """Test handling of empty faction code."""
        assert get_faction_short_name("") == "unkn"


class TestParseCardCode:
    """Test card code parsing."""

    def test_valid_card_codes(self) -> None:
        """Test parsing of valid card codes."""
        test_cases = [
            ("01001", ("01", "001")),
            ("12345", ("12", "345")),
            ("00999", ("00", "999")),
        ]

        for code, expected in test_cases:
            assert parse_card_code(code) == expected

    def test_invalid_card_codes(self) -> None:
        """Test handling of invalid card codes."""
        invalid_codes = [
            "1234",  # Too short
            "123456",  # Too long
            "abcde",  # Not numeric
            "01a34",  # Mixed characters
        ]

        for code in invalid_codes:
            with pytest.raises(ValueError, match="Card code must be 5 digits"):
                parse_card_code(code)

    def test_empty_card_code(self) -> None:
        """Test handling of empty card code."""
        with pytest.raises(ValueError, match="Card code cannot be empty"):
            parse_card_code("")


class TestFormatDeckSize:
    """Test deck size formatting."""

    def test_valid_deck_sizes(self) -> None:
        """Test formatting of valid deck sizes."""
        test_cases = [
            (0, "0 cards"),
            (1, "1 card"),
            (45, "45 cards"),
            (100, "100 cards"),
        ]

        for count, expected in test_cases:
            assert format_deck_size(count) == expected

    def test_negative_deck_size(self) -> None:
        """Test handling of negative deck sizes."""
        with pytest.raises(ValueError, match="Card count cannot be negative"):
            format_deck_size(-1)


class TestFactionCode:
    """Test FactionCode enum."""

    def test_runner_factions(self) -> None:
        """Test runner faction codes."""
        assert FactionCode.ANARCH.value == "anarch"
        assert FactionCode.CRIMINAL.value == "criminal"
        assert FactionCode.SHAPER.value == "shaper"

    def test_corp_factions(self) -> None:
        """Test corp faction codes."""
        assert FactionCode.HAAS_BIOROID.value == "haas-bioroid"
        assert FactionCode.JINTEKI.value == "jinteki"
        assert FactionCode.NBN.value == "nbn"
        assert FactionCode.WEYLAND.value == "weyland-consortium"

    def test_neutral_factions(self) -> None:
        """Test neutral faction codes."""
        assert FactionCode.NEUTRAL_CORP.value == "neutral-corp"
        assert FactionCode.NEUTRAL_RUNNER.value == "neutral-runner"

    def test_mini_factions(self) -> None:
        """Test mini faction codes."""
        assert FactionCode.ADAM.value == "adam"
        assert FactionCode.APEX.value == "apex"
        assert FactionCode.SUNNY_LEBEAU.value == "sunny-lebeau"
