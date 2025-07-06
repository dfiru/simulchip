"""Basic tests to ensure the test infrastructure works."""

# First-party imports
from simulchip.utils import extract_decklist_id, get_faction_symbol


def test_extract_decklist_id_basic() -> None:
    """Test basic decklist ID extraction."""
    url = "https://netrunnerdb.com/en/decklist/12345"
    result = extract_decklist_id(url)
    assert result == "12345"


def test_get_faction_symbol_basic() -> None:
    """Test basic faction symbol retrieval."""
    assert get_faction_symbol("anarch") == "[A]"
    assert get_faction_symbol("criminal") == "[C]"


def test_imports_work() -> None:
    """Test that all main modules can be imported."""
    # First-party imports
    from simulchip.api.netrunnerdb import NetrunnerDBAPI
    from simulchip.collection.manager import CollectionManager
    from simulchip.comparison import DecklistComparer
    from simulchip.pdf.generator import ProxyPDFGenerator

    # Just test that we can create instances (don't actually use them)
    assert NetrunnerDBAPI is not None
    assert CollectionManager is not None
    assert DecklistComparer is not None
    assert ProxyPDFGenerator is not None


def test_math_works() -> None:
    """Sanity check that pytest is working."""
    assert 2 + 2 == 4
    assert 1 + 1 == 2
