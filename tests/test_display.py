"""Tests for display utilities and calculations."""

# Standard library imports
from unittest.mock import Mock

# First-party imports
from simulchip.display import (
    calculate_viewport_size,
    calculate_viewport_window,
    format_viewport_status,
    get_completion_color,
)


class TestCalculateViewportSize:
    """Test viewport size calculation logic."""

    def test_pack_interface_viewport_size(self):
        """Should calculate correct viewport size for pack interface."""
        mock_console = Mock()
        mock_console.size.height = 30

        result = calculate_viewport_size(mock_console, "pack")

        # Terminal height 30 - reserved lines 9 = 21
        assert result == 21

    def test_card_interface_viewport_size(self):
        """Should calculate correct viewport size for card interface."""
        mock_console = Mock()
        mock_console.size.height = 40

        result = calculate_viewport_size(mock_console, "card")

        # Terminal height 40 - reserved lines 11 = 29
        assert result == 29

    def test_default_interface_viewport_size(self):
        """Should calculate correct viewport size for default interface."""
        mock_console = Mock()
        mock_console.size.height = 25

        result = calculate_viewport_size(mock_console, "default")

        # Terminal height 25 - reserved lines 10 = 15
        assert result == 15

    def test_unknown_interface_uses_default(self):
        """Should use default reserved lines for unknown interface types."""
        mock_console = Mock()
        mock_console.size.height = 25

        result = calculate_viewport_size(mock_console, "unknown_type")

        # Should use default reserved lines (10)
        assert result == 15

    def test_minimum_viewport_size(self):
        """Should enforce minimum viewport size of 5."""
        mock_console = Mock()
        mock_console.size.height = 10  # Very small terminal

        result = calculate_viewport_size(mock_console, "pack")

        # Even though calculation would be 10 - 9 = 1, minimum is 5
        assert result == 5

    def test_very_small_terminal(self):
        """Should handle very small terminals gracefully."""
        mock_console = Mock()
        mock_console.size.height = 5

        result = calculate_viewport_size(mock_console, "card")

        # 5 - 11 would be negative, but minimum is 5
        assert result == 5


class TestCalculateViewportWindow:
    """Test viewport window calculation logic."""

    def test_normal_viewport_window(self):
        """Should calculate correct viewport window for normal cases."""
        result = calculate_viewport_window(
            selected_idx=10, total_items=50, viewport_size=20
        )

        # Selected 10, viewport 20, so start at 10 - 20//2 = 0
        assert result["start"] == 0
        assert result["end"] == 20

    def test_centered_viewport_window(self):
        """Should center viewport around selected item."""
        result = calculate_viewport_window(
            selected_idx=25, total_items=50, viewport_size=10
        )

        # Selected 25, viewport 10, so start at 25 - 10//2 = 20
        assert result["start"] == 20
        assert result["end"] == 30

    def test_viewport_at_beginning(self):
        """Should handle viewport at beginning of list."""
        result = calculate_viewport_window(
            selected_idx=2, total_items=50, viewport_size=10
        )

        # Selected 2, would start at 2 - 5 = -3, corrected to 0
        assert result["start"] == 0
        assert result["end"] == 10

    def test_viewport_at_end(self):
        """Should handle viewport at end of list."""
        result = calculate_viewport_window(
            selected_idx=47, total_items=50, viewport_size=10
        )

        # Should adjust to show end of list
        assert result["start"] == 40
        assert result["end"] == 50

    def test_viewport_larger_than_items(self):
        """Should handle viewport larger than total items."""
        result = calculate_viewport_window(
            selected_idx=2, total_items=5, viewport_size=10
        )

        assert result["start"] == 0
        assert result["end"] == 5

    def test_empty_list(self):
        """Should handle empty list gracefully."""
        result = calculate_viewport_window(
            selected_idx=0, total_items=0, viewport_size=10
        )

        assert result["start"] == 0
        assert result["end"] == 0

    def test_single_item(self):
        """Should handle single item list."""
        result = calculate_viewport_window(
            selected_idx=0, total_items=1, viewport_size=10
        )

        assert result["start"] == 0
        assert result["end"] == 1


class TestFormatViewportStatus:
    """Test viewport status formatting."""

    def test_format_viewport_status_normal(self):
        """Should format viewport status correctly for normal cases."""
        result = format_viewport_status(
            selected_idx=4,
            total_items=20,
            viewport_start=0,
            viewport_end=10,
            viewport_size=10,
        )

        # Selected index 4 = position 5 (1-based)
        assert result == "5/20 (showing 1-10)"

    def test_format_viewport_status_no_viewport_info(self):
        """Should not show viewport info when all items visible."""
        result = format_viewport_status(
            selected_idx=2,
            total_items=5,
            viewport_start=0,
            viewport_end=5,
            viewport_size=10,
        )

        # Total items (5) <= viewport size (10), so no viewport info
        assert result == "3/5"

    def test_format_viewport_status_empty_list(self):
        """Should handle empty list gracefully."""
        result = format_viewport_status(
            selected_idx=0,
            total_items=0,
            viewport_start=0,
            viewport_end=0,
            viewport_size=10,
        )

        assert result == "0/0"

    def test_format_viewport_status_middle_of_list(self):
        """Should show viewport info when scrolled in middle."""
        result = format_viewport_status(
            selected_idx=24,
            total_items=100,
            viewport_start=20,
            viewport_end=30,
            viewport_size=10,
        )

        assert result == "25/100 (showing 21-30)"

    def test_format_viewport_status_at_end(self):
        """Should format correctly when at end of list."""
        result = format_viewport_status(
            selected_idx=99,
            total_items=100,
            viewport_start=90,
            viewport_end=100,
            viewport_size=10,
        )

        assert result == "100/100 (showing 91-100)"


class TestGetCompletionColor:
    """Test completion percentage color logic."""

    def test_perfect_completion_is_green(self):
        """Should return green for 100% completion."""
        assert get_completion_color(100.0) == "green"
        assert get_completion_color(100) == "green"

    def test_high_completion_is_yellow(self):
        """Should return yellow for 80-99% completion."""
        assert get_completion_color(99.9) == "yellow"
        assert get_completion_color(90.0) == "yellow"
        assert get_completion_color(80.0) == "yellow"
        assert get_completion_color(80.1) == "yellow"

    def test_low_completion_is_red(self):
        """Should return red for less than 80% completion."""
        assert get_completion_color(79.9) == "red"
        assert get_completion_color(50.0) == "red"
        assert get_completion_color(0.0) == "red"
        assert get_completion_color(10.5) == "red"

    def test_edge_cases(self):
        """Should handle edge cases correctly."""
        # Exactly 80% should be yellow
        assert get_completion_color(80.0) == "yellow"

        # Just below 80% should be red
        assert get_completion_color(79.999) == "red"

        # Just below 100% should be yellow
        assert get_completion_color(99.999) == "yellow"

    def test_invalid_percentages(self):
        """Should handle invalid percentages gracefully."""
        # Negative percentages should be red
        assert get_completion_color(-10) == "red"

        # Over 100% should follow the same logic (150 >= 80, so yellow)
        assert get_completion_color(150) == "yellow"


class TestDisplayEdgeCases:
    """Test edge cases and error conditions."""

    def test_console_size_edge_cases(self):
        """Should handle unusual console sizes."""
        # Zero height console
        mock_console = Mock()
        mock_console.size.height = 0
        result = calculate_viewport_size(mock_console, "default")
        assert result == 5  # Minimum enforced

        # Very large console
        mock_console.size.height = 1000
        result = calculate_viewport_size(mock_console, "pack")
        assert result == 991  # 1000 - 9 reserved

    def test_viewport_window_edge_indices(self):
        """Should handle edge case indices correctly."""
        # Negative selected index (shouldn't happen but handle gracefully)
        result = calculate_viewport_window(-1, 10, 5)
        assert result["start"] >= 0
        assert result["end"] >= result["start"]

        # Selected index beyond total items
        result = calculate_viewport_window(20, 10, 5)
        assert result["start"] >= 0
        assert result["end"] <= 10

    def test_status_formatting_with_extreme_values(self):
        """Should handle extreme values in status formatting."""
        # Very large numbers
        result = format_viewport_status(999, 1000, 0, 1000, 1000)
        assert "1000/1000" in result

        # Zero-based edge case
        result = format_viewport_status(0, 1, 0, 1, 1)
        assert "1/1" in result
