"""Tests for NetrunnerDB API functionality."""

# Standard library imports
from unittest.mock import Mock, patch

# Third-party imports
import pytest
import requests

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


class TestAPIErrorHandling:
    """Test error handling in API requests."""

    @patch("simulchip.api.netrunnerdb.requests.get")
    def test_request_timeout(self, mock_get: Mock) -> None:
        """Test handling of request timeout."""
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

        api = NetrunnerDBAPI()
        with pytest.raises(APIError) as exc_info:
            api._make_request("cards")

        assert "Request failed" in str(exc_info.value)
        assert "Request timed out" in str(exc_info.value)
        assert exc_info.value.url == "https://netrunnerdb.com/api/2.0/public/cards"

    @patch("simulchip.api.netrunnerdb.requests.get")
    def test_request_connection_error(self, mock_get: Mock) -> None:
        """Test handling of connection errors."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        api = NetrunnerDBAPI()
        with pytest.raises(APIError) as exc_info:
            api._make_request("cards")

        assert "Request failed" in str(exc_info.value)
        assert "Connection failed" in str(exc_info.value)

    @patch("simulchip.api.netrunnerdb.requests.get")
    def test_http_error_404(self, mock_get: Mock) -> None:
        """Test handling of HTTP 404 error."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Not Found"
        )
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        # Create the exception with response attribute
        error = requests.exceptions.HTTPError("404 Not Found")
        error.response = mock_response
        mock_response.raise_for_status.side_effect = error

        api = NetrunnerDBAPI()
        with pytest.raises(APIError) as exc_info:
            api._make_request("invalid_endpoint")

        assert exc_info.value.status_code == 404
        assert "Request failed" in str(exc_info.value)

    @patch("simulchip.api.netrunnerdb.requests.get")
    def test_invalid_json_response(self, mock_get: Mock) -> None:
        """Test handling of invalid JSON response."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        api = NetrunnerDBAPI()
        with pytest.raises(APIError) as exc_info:
            api._make_request("cards")

        assert "Invalid JSON response" in str(exc_info.value)

    @patch("simulchip.api.netrunnerdb.requests.get")
    def test_non_dict_response(self, mock_get: Mock) -> None:
        """Test handling of non-dict JSON response."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = ["not", "a", "dict"]
        mock_get.return_value = mock_response

        api = NetrunnerDBAPI()
        with pytest.raises(APIError) as exc_info:
            api._make_request("cards")

        assert "Expected dict response" in str(exc_info.value)


class TestAPISpecificMethods:
    """Test specific API methods."""

    @patch("simulchip.api.netrunnerdb.NetrunnerDBAPI.get_all_cards")
    def test_get_all_cards_list(self, mock_get_all_cards: Mock) -> None:
        """Test get_all_cards_list method."""
        mock_cards = {
            "01001": {"code": "01001", "title": "Card 1"},
            "01002": {"code": "01002", "title": "Card 2"},
        }
        mock_get_all_cards.return_value = mock_cards

        api = NetrunnerDBAPI()
        result = api.get_all_cards_list()

        assert len(result) == 2
        assert result[0]["title"] == "Card 1"
        assert result[1]["title"] == "Card 2"

    @patch("simulchip.api.netrunnerdb.NetrunnerDBAPI._make_request")
    def test_get_all_cards_with_malformed_response(self, mock_request: Mock) -> None:
        """Test get_all_cards with malformed API response."""
        # Test with non-list data field
        mock_request.return_value = {"data": {"not": "a list"}}

        api = NetrunnerDBAPI()
        with pytest.raises(APIError) as exc_info:
            api.get_all_cards()
        assert "Expected list in 'data' field" in str(exc_info.value)


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limit_delay_setting(self) -> None:
        """Test rate limit delay configuration."""
        # Default rate limit
        api1 = NetrunnerDBAPI()
        assert api1.rate_limit_delay == 0.5

        # Custom rate limit
        api2 = NetrunnerDBAPI(rate_limit_delay=2.0)
        assert api2.rate_limit_delay == 2.0

        # Zero rate limit (no delay)
        api3 = NetrunnerDBAPI(rate_limit_delay=0)
        assert api3.rate_limit_delay == 0


class TestPackMethods:
    """Test pack-related methods."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.test_packs = [
            {"code": "core", "name": "Core Set", "date_release": "2012-09-06"},
            {"code": "wla", "name": "What Lies Ahead", "date_release": "2012-12-14"},
            {"code": "future", "name": "Future Pack", "date_release": "2024-01-01"},
            {"code": "draft", "name": "Draft Pack", "date_release": None},
        ]

    @patch("simulchip.api.netrunnerdb.NetrunnerDBAPI.get_all_packs")
    def test_get_packs_by_release_date(self, mock_get_packs: Mock) -> None:
        """Test getting packs sorted by release date."""
        mock_get_packs.return_value = self.test_packs

        api = NetrunnerDBAPI()

        # Test newest first
        result = api.get_packs_by_release_date(newest_first=True)
        assert result[0]["code"] == "future"
        assert result[-1]["code"] == "draft"  # Packs without date go last

        # Test oldest first
        result = api.get_packs_by_release_date(newest_first=False)
        assert result[0]["code"] == "core"
        assert result[-1]["code"] == "draft"

    @patch("simulchip.api.netrunnerdb.NetrunnerDBAPI.get_all_packs")
    def test_get_pack_by_code(self, mock_get_packs: Mock) -> None:
        """Test getting a specific pack by code."""
        mock_get_packs.return_value = self.test_packs

        api = NetrunnerDBAPI()

        # Test existing pack
        result = api.get_pack_by_code("core")
        assert result is not None
        assert result["name"] == "Core Set"

        # Test non-existing pack
        result = api.get_pack_by_code("nonexistent")
        assert result is None


class TestCardMethods:
    """Test card-related methods."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.test_cards = {
            "01001": {"code": "01001", "title": "Sure Gamble", "pack_code": "core"},
            "01002": {"code": "01002", "title": "Desperado", "pack_code": "core"},
            "02001": {"code": "02001", "title": "New Card", "pack_code": "wla"},
        }

    @patch("simulchip.api.netrunnerdb.NetrunnerDBAPI.get_all_cards")
    def test_get_cards_by_pack(self, mock_get_cards: Mock) -> None:
        """Test getting cards filtered by pack."""
        mock_get_cards.return_value = self.test_cards

        api = NetrunnerDBAPI()

        # Test getting cards from core
        result = api.get_cards_by_pack("core")
        assert len(result) == 2
        assert all(card["pack_code"] == "core" for card in result)

        # Test getting cards from wla
        result = api.get_cards_by_pack("wla")
        assert len(result) == 1
        assert result[0]["code"] == "02001"

        # Test non-existing pack
        result = api.get_cards_by_pack("nonexistent")
        assert len(result) == 0

        # Test empty pack code
        with pytest.raises(ValueError):
            api.get_cards_by_pack("")

    @patch("simulchip.api.netrunnerdb.NetrunnerDBAPI.get_all_cards")
    def test_get_card_by_code(self, mock_get_cards: Mock) -> None:
        """Test getting a specific card by code."""
        mock_get_cards.return_value = self.test_cards

        api = NetrunnerDBAPI()

        # Test existing card
        result = api.get_card_by_code("01001")
        assert result is not None
        assert result["title"] == "Sure Gamble"

        # Test non-existing card
        result = api.get_card_by_code("99999")
        assert result is None


class TestDecklistMethods:
    """Test decklist-related methods."""

    @patch("simulchip.api.netrunnerdb.NetrunnerDBAPI._make_request")
    def test_get_decklist_success(self, mock_request: Mock) -> None:
        """Test successful decklist fetching."""
        mock_decklist = {
            "data": [
                {"id": 12345, "name": "Test Deck", "cards": {"01001": 3, "01002": 2}}
            ]
        }
        mock_request.return_value = mock_decklist

        api = NetrunnerDBAPI()
        result = api.get_decklist("12345")

        assert result["name"] == "Test Deck"
        assert result["cards"]["01001"] == 3
        mock_request.assert_called_with("decklist/12345")

    @patch("simulchip.api.netrunnerdb.NetrunnerDBAPI._make_request")
    def test_get_decklist_not_found(self, mock_request: Mock) -> None:
        """Test decklist not found."""
        mock_request.return_value = {"data": []}

        api = NetrunnerDBAPI()
        with pytest.raises(APIError) as exc_info:
            api.get_decklist("99999")

        assert "Decklist not found" in str(exc_info.value)

    @patch("simulchip.api.netrunnerdb.NetrunnerDBAPI._make_request")
    def test_get_decklist_missing_data_field(self, mock_request: Mock) -> None:
        """Test decklist with missing data field."""
        mock_request.return_value = {"something": "else"}

        api = NetrunnerDBAPI()
        with pytest.raises(APIError) as exc_info:
            api.get_decklist("12345")

        assert "Missing 'data' field" in str(exc_info.value)


class TestOfflineMode:
    """Test offline mode functionality."""

    def test_offline_mode_prevents_all_requests(self) -> None:
        """Test that offline mode prevents all API requests."""
        api = NetrunnerDBAPI()
        api.set_offline_mode(True)

        with pytest.raises(APIError) as exc_info:
            api._make_request("any_endpoint")

        assert "Offline mode enabled" in str(exc_info.value)

    def test_offline_mode_state(self) -> None:
        """Test offline mode state management."""
        api = NetrunnerDBAPI()

        # Initially offline mode should be False
        assert not api.is_offline_mode()

        # Set offline mode
        api.set_offline_mode(True)
        assert api.is_offline_mode()

        # Unset offline mode
        api.set_offline_mode(False)
        assert not api.is_offline_mode()


class TestValidationMethods:
    """Test input validation methods."""

    def test_get_decklist_invalid_id(self) -> None:
        """Test get_decklist with invalid IDs."""
        api = NetrunnerDBAPI()

        # Empty ID
        with pytest.raises(ValueError) as exc_info:
            api.get_decklist("")
        assert "empty" in str(exc_info.value)

        # Invalid characters
        with pytest.raises(ValueError) as exc_info:
            api.get_decklist("../../etc/passwd")
        assert "Invalid decklist ID format" in str(exc_info.value)

    def test_get_card_by_code_edge_cases(self) -> None:
        """Test get_card_by_code with edge cases."""
        api = NetrunnerDBAPI()

        with patch.object(api, "get_all_cards", return_value={}):
            # Non-existent card returns None
            result = api.get_card_by_code("99999")
            assert result is None


class TestCacheValidityMethods:
    """Test cache validity checking methods."""

    @patch("simulchip.api.netrunnerdb.NetrunnerDBAPI._make_request")
    @patch("simulchip.cache.CacheManager.is_cache_valid")
    def test_check_cache_validity(
        self, mock_cache_is_valid: Mock, mock_request: Mock
    ) -> None:
        """Test checking cache validity."""
        # Test when cache is valid
        mock_request.return_value = {"data": [{"code": "core", "name": "Core Set"}]}
        mock_cache_is_valid.return_value = True

        api = NetrunnerDBAPI()
        result = api.check_cache_validity()
        assert result is True
        mock_request.assert_called_with("packs")

    @patch("simulchip.api.netrunnerdb.NetrunnerDBAPI._make_request")
    def test_check_cache_validity_bad_response(self, mock_request: Mock) -> None:
        """Test cache validity check with bad response."""
        # Missing data field
        mock_request.return_value = {"error": "something"}

        api = NetrunnerDBAPI()
        result = api.check_cache_validity()
        assert result is False

    @patch("simulchip.api.netrunnerdb.NetrunnerDBAPI._make_request")
    def test_check_cache_validity_exception(self, mock_request: Mock) -> None:
        """Test cache validity check when exception occurs."""
        mock_request.side_effect = Exception("Network error")

        api = NetrunnerDBAPI()
        result = api.check_cache_validity()
        # Should return True on exception (assume valid)
        assert result is True

    def test_check_cache_validity_offline_mode(self) -> None:
        """Test cache validity in offline mode."""
        api = NetrunnerDBAPI()
        api.set_offline_mode(True)

        # Should always return True in offline mode
        result = api.check_cache_validity()
        assert result is True

    @patch("simulchip.cache.CacheManager.get_cache_metadata")
    def test_check_cache_validity_with_reason_no_metadata(
        self, mock_get_metadata: Mock
    ) -> None:
        """Test cache validity reason when no metadata exists."""
        mock_get_metadata.return_value = {}

        api = NetrunnerDBAPI()
        result = api.check_cache_validity_with_reason()

        assert "valid" in result
        assert result["valid"] is False
        assert "reason" in result
        assert "No cache metadata found" in result["reason"]


class TestNormalizePackData:
    """Test pack data normalization."""

    def test_normalize_pack_data(self) -> None:
        """Test normalizing pack data."""
        api = NetrunnerDBAPI()

        # Test with packs having and missing date_release
        raw_packs = [
            {"code": "core", "name": "Core Set", "date_release": "2012-09-06"},
            {"code": "draft", "name": "Draft Pack", "date_release": None},
            {"code": "no_date", "name": "No Date Pack"},
        ]

        result = api._normalize_pack_data(raw_packs)

        # All packs should have date_release field
        assert len(result) == 3
        assert result[0]["date_release"] == "2012-09-06"
        assert result[1]["date_release"] == ""
        assert result[2]["date_release"] == ""


class TestMiscellaneousMethods:
    """Test miscellaneous uncovered methods."""

    def test_endpoint_validation(self) -> None:
        """Test endpoint validation in _make_request."""
        api = NetrunnerDBAPI()

        # Empty endpoint should raise error
        with pytest.raises(APIError) as exc_info:
            api._make_request("")
        assert "Endpoint cannot be empty" in str(exc_info.value)

    def test_empty_endpoint_raises_error(self) -> None:
        """Test that empty endpoint raises an error."""
        api = NetrunnerDBAPI()

        # Should raise error for empty endpoint
        with pytest.raises(APIError) as exc_info:
            api._make_request("")
        assert "Endpoint cannot be empty" in str(exc_info.value)

    @patch("simulchip.cache.CacheManager.get_cached_packs")
    @patch("simulchip.cache.CacheManager.get_cache_metadata")
    def test_get_all_packs_from_internal_cache(
        self, mock_metadata: Mock, mock_cache: Mock
    ) -> None:
        """Test that get_all_packs returns from internal cache when available."""
        # Set up to show cache is valid
        mock_cache.return_value = None
        mock_metadata.return_value = {"timestamp": 1234567890}

        api = NetrunnerDBAPI()
        # Set internal cache
        test_packs = [{"code": "core", "name": "Core Set", "date_release": ""}]
        api._packs_cache = test_packs

        # Should return from internal cache
        result = api.get_all_packs()
        assert result == test_packs
