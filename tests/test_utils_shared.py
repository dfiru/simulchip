"""Shared test utilities and fixtures for more concise tests."""

# Standard library imports
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import Mock

# Third-party imports
import pytest


# Test data factories
def create_pack_data(
    code: str = "test",
    name: str = "Test Pack",
    cycle: str = "Test Cycle",
    date_release: str = "2023-01-01",
    **kwargs,
) -> Dict[str, Any]:
    """Create test pack data with defaults."""
    data = {
        "code": code,
        "name": name,
        "cycle": cycle,
        "date_release": date_release,
    }
    data.update(kwargs)
    return data


def create_card_data(
    code: str = "01001",
    title: str = "Test Card",
    type_code: str = "event",
    faction_code: str = "neutral",
    pack_code: str = "test",
    text: str = "Test card text",
    quantity: int = 3,
    **kwargs,
) -> Dict[str, Any]:
    """Create test card data with defaults."""
    data = {
        "code": code,
        "title": title,
        "type_code": type_code,
        "faction_code": faction_code,
        "pack_code": pack_code,
        "text": text,
        "quantity": quantity,
    }
    data.update(kwargs)
    return data


def create_multiple_packs(count: int, prefix: str = "pack") -> List[Dict[str, Any]]:
    """Create multiple test packs."""
    return [
        create_pack_data(
            code=f"{prefix}{i:02d}",
            name=f"Test Pack {i}",
            cycle=f"Cycle {(i-1)//3 + 1}",
        )
        for i in range(1, count + 1)
    ]


def create_multiple_cards(count: int, prefix: str = "card") -> List[Dict[str, Any]]:
    """Create multiple test cards."""
    types = ["event", "resource", "program", "hardware", "identity"]
    factions = ["anarch", "criminal", "shaper", "neutral"]

    return [
        create_card_data(
            code=f"{i:05d}",
            title=f"Test Card {i}",
            type_code=types[i % len(types)],
            faction_code=factions[i % len(factions)],
            pack_code=f"{prefix}{(i-1)//10 + 1:02d}",
        )
        for i in range(1, count + 1)
    ]


# Mock factories
def create_mock_console(height: int = 30, width: int = 80) -> Mock:
    """Create a mock Rich console."""
    console = Mock()
    console.size.height = height
    console.size.width = width
    return console


def create_mock_collection_manager(**methods) -> Mock:
    """Create a mock collection manager with optional method overrides."""
    manager = Mock()

    # Default methods
    manager.get_expected_card_count.return_value = 0
    manager.get_card_difference.return_value = 0
    manager.get_actual_card_count.return_value = 0
    manager.get_owned_packs.return_value = []
    manager.save_collection.return_value = None

    # Override with provided methods
    for method_name, return_value in methods.items():
        if callable(return_value):
            getattr(manager, method_name).side_effect = return_value
        else:
            getattr(manager, method_name).return_value = return_value

    return manager


def create_mock_api_client(
    packs: Optional[List[Dict]] = None, cards: Optional[Dict] = None
) -> Mock:
    """Create a mock API client."""
    api = Mock()

    # Default data
    api.get_all_packs.return_value = packs or []
    api.get_all_cards.return_value = cards or {}
    api.get_packs_by_release_date.return_value = packs or []

    return api


# File system utilities
@pytest.fixture
def temp_file():
    """Create a temporary file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        yield Path(f.name)
    # Cleanup
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def create_temp_file_with_content(content: str, suffix: str = ".txt") -> Path:
    """Create a temporary file with specific content."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=suffix) as f:
        f.write(content)
        f.flush()
        return Path(f.name)


# Assertion helpers
def assert_dict_contains(actual: Dict[str, Any], expected: Dict[str, Any]) -> None:
    """Assert that actual dict contains all key-value pairs from expected."""
    for key, value in expected.items():
        assert key in actual, f"Key '{key}' not found in actual dict"
        assert actual[key] == value, f"Expected {key}={value}, got {actual[key]}"


def assert_list_contains_items(actual: List[Any], expected_items: List[Any]) -> None:
    """Assert that actual list contains all expected items."""
    for item in expected_items:
        assert item in actual, f"Item {item} not found in actual list"


def assert_approximately_equal(
    actual: float, expected: float, tolerance: float = 0.01
) -> None:
    """Assert that two floats are approximately equal."""
    assert (
        abs(actual - expected) <= tolerance
    ), f"Expected {expected} ± {tolerance}, got {actual}"


# Parametrized test data generators
def generate_boundary_test_cases(valid_range: range) -> List[tuple]:
    """Generate boundary test cases for a valid range."""
    min_val, max_val = valid_range.start, valid_range.stop - 1
    return [
        # Valid boundaries
        (min_val, True),
        (max_val, True),
        # Invalid boundaries
        (min_val - 1, False),
        (max_val + 1, False),
        # Edge cases
        (0, min_val == 0),
        (-1, False),
    ]


def generate_string_filter_test_cases() -> List[tuple]:
    """Generate test cases for string filtering."""
    return [
        # (filter_text, should_match_items, description)
        ("", True, "empty filter matches all"),
        ("test", True, "exact match"),
        ("TEST", True, "case insensitive"),
        ("est", True, "partial match"),
        ("xyz", False, "no match"),
        ("123", False, "numeric no match"),
        ("!", False, "special char no match"),
    ]


# Common test patterns
class BaseTestCase:
    """Base test case class with common utilities."""

    @staticmethod
    def assert_valid_result(result, expected_type=None, min_items=None, max_items=None):
        """Assert that a result is valid."""
        if expected_type:
            assert isinstance(result, expected_type)

        if hasattr(result, "__len__"):
            if min_items is not None:
                assert len(result) >= min_items
            if max_items is not None:
                assert len(result) <= max_items

    @staticmethod
    def assert_no_side_effects(func, *args, **kwargs):
        """Assert that a function has no side effects on inputs."""
        # Make copies of mutable inputs
        original_args = [arg.copy() if hasattr(arg, "copy") else arg for arg in args]
        _ = {k: v.copy() if hasattr(v, "copy") else v for k, v in kwargs.items()}

        # Call function
        func(*args, **kwargs)

        # Check inputs unchanged
        for i, (original, current) in enumerate(zip(original_args, args)):
            if hasattr(original, "__eq__"):
                assert original == current, f"Argument {i} was modified"


# Performance test utilities
def measure_time(func, *args, **kwargs):
    """Measure execution time of a function."""
    # Standard library imports
    import time

    start = time.perf_counter()
    result = func(*args, **kwargs)
    end = time.perf_counter()
    return result, end - start


def assert_performance(func, max_time: float, *args, **kwargs):
    """Assert that a function completes within max_time seconds."""
    result, elapsed = measure_time(func, *args, **kwargs)
    assert elapsed <= max_time, f"Function took {elapsed:.3f}s, expected <= {max_time}s"
    return result


# Mock setup helpers
def setup_collection_manager_mock(
    owned_packs: Optional[List[str]] = None,
    expected_cards: Optional[Dict[str, int]] = None,
    card_diffs: Optional[Dict[str, int]] = None,
) -> Mock:
    """Set up a comprehensive collection manager mock."""
    manager = Mock()

    owned_packs = owned_packs or []
    expected_cards = expected_cards or {}
    card_diffs = card_diffs or {}

    manager.get_owned_packs.return_value = owned_packs
    manager.get_expected_card_count.side_effect = lambda code: expected_cards.get(
        code, 0
    )
    manager.get_card_difference.side_effect = lambda code: card_diffs.get(code, 0)
    manager.get_actual_card_count.side_effect = lambda code: max(
        0, expected_cards.get(code, 0) + card_diffs.get(code, 0)
    )

    return manager
