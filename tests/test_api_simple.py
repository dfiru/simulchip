"""Simple tests for NetrunnerDB API functionality."""

# Standard library imports
from unittest.mock import Mock, patch

# Third-party imports
import pytest

# First-party imports
from simulchip.api.netrunnerdb import APIError, NetrunnerDBAPI


class TestNetrunnerDBAPISimple:
    """Simple tests for API client that don't require complex mocking."""

    def test_api_initialization(self) -> None:
        """Test API client initialization."""
        api = NetrunnerDBAPI()
        assert api.rate_limit_delay == NetrunnerDBAPI.DEFAULT_RATE_LIMIT
        assert api.cache is not None

    def test_api_initialization_with_params(self) -> None:
        """Test API client initialization with custom parameters."""
        api = NetrunnerDBAPI(rate_limit_delay=1.0)
        assert api.rate_limit_delay == 1.0

    def test_invalid_rate_limit(self) -> None:
        """Test that negative rate limit raises error."""
        with pytest.raises(ValueError, match="rate_limit_delay must be non-negative"):
            NetrunnerDBAPI(rate_limit_delay=-1.0)

    def test_api_error_creation(self) -> None:
        """Test APIError exception creation."""
        error = APIError("Test error", 404, "https://example.com")

        # The actual string representation might include all parameters
        assert "Test error" in str(error)
        assert error.message == "Test error"
        assert error.status_code == 404
        assert error.url == "https://example.com"

    def test_api_error_minimal(self) -> None:
        """Test APIError with minimal parameters."""
        error = APIError("Test error")

        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.status_code is None
        assert error.url is None

    @patch("simulchip.api.netrunnerdb.NetrunnerDBAPI._make_request")
    @patch("simulchip.cache.CacheManager.get_cached_packs")
    @patch("simulchip.cache.CacheManager.get_cached_cards")
    def test_get_all_cards_uses_cache(
        self, mock_cache_get_cards: Mock, mock_cache_get_packs: Mock, mock_request: Mock
    ) -> None:
        """Test that get_all_cards uses caching."""
        # Mock cache to return None initially (no cached data)
        mock_cache_get_cards.return_value = None
        mock_cache_get_packs.return_value = None

        # Mock the response format for different endpoints
        def side_effect(endpoint: str, *args, **kwargs):
            if endpoint == "cards":
                return {"data": [{"code": "01001", "title": "Test Card"}]}
            elif endpoint == "packs":
                return {
                    "data": [
                        {
                            "code": "core",
                            "name": "Core Set",
                            "date_release": "2023-01-01",
                        }
                    ]
                }
            return {"data": []}

        mock_request.side_effect = side_effect

        api = NetrunnerDBAPI()

        # First call should hit the API twice (cards + packs for cache metadata)
        result1 = api.get_all_cards()
        assert "01001" in result1
        assert mock_request.call_count == 2  # Cards + Packs

        # Second call should use internal cache (not hit API again)
        result2 = api.get_all_cards()
        assert result2 == result1
        assert mock_request.call_count == 2  # Still only called twice total

    @patch("simulchip.api.netrunnerdb.NetrunnerDBAPI._make_request")
    @patch("simulchip.cache.CacheManager.get_cached_packs")
    def test_get_all_packs_uses_cache(
        self, mock_cache_get: Mock, mock_request: Mock
    ) -> None:
        """Test that get_all_packs uses caching."""
        # Mock cache to return None initially
        mock_cache_get.return_value = None

        # Mock the response format
        mock_request.return_value = {"data": [{"code": "core", "name": "Core Set"}]}

        api = NetrunnerDBAPI()

        # First call should hit the API
        result1 = api.get_all_packs()
        assert len(result1) == 1
        assert result1[0]["code"] == "core"
        assert mock_request.call_count == 1

        # Second call should use internal cache (not hit API again)
        result2 = api.get_all_packs()
        assert result2 == result1
        assert mock_request.call_count == 1  # Still only called once
