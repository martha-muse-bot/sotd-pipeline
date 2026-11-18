"""
Tests for brush matching exception types.
"""

from sotd.match.exceptions import (
    BrushMatchingError,
    CacheError,
    CatalogLoadError,
    ConfigurationError,
    InvalidMatchDataError,
    ValidationError,
)


class TestBrushMatchingExceptions:
    """Test the custom exception hierarchy."""

    def test_base_exception_with_context(self):
        """Test that base exception includes context in string representation."""
        error = BrushMatchingError(
            "Test error", context={"path": "/test/path", "operation": "test_op"}
        )

        assert "Test error" in str(error)
        assert "path=/test/path" in str(error)
        assert "operation=test_op" in str(error)

    def test_base_exception_without_context(self):
        """Test that base exception works without context."""
        error = BrushMatchingError("Test error")

        assert str(error) == "Test error"

    def test_catalog_load_error(self):
        """Test CatalogLoadError with context."""
        error = CatalogLoadError(
            "Failed to load catalog",
            context={"path": "/data/catalog.yaml", "operation": "load_catalog"},
        )

        assert isinstance(error, BrushMatchingError)
        assert "Failed to load catalog" in str(error)
        assert "path=/data/catalog.yaml" in str(error)

    def test_configuration_error(self):
        """Test ConfigurationError."""
        error = ConfigurationError("Invalid configuration")

        assert isinstance(error, BrushMatchingError)
        assert str(error) == "Invalid configuration"

    def test_invalid_match_data_error(self):
        """Test InvalidMatchDataError."""
        error = InvalidMatchDataError("Invalid match data")

        assert isinstance(error, BrushMatchingError)
        assert str(error) == "Invalid match data"

    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError("Validation failed")

        assert isinstance(error, BrushMatchingError)
        assert str(error) == "Validation failed"

    def test_cache_error(self):
        """Test CacheError."""
        error = CacheError("Cache operation failed")

        assert isinstance(error, BrushMatchingError)
        assert str(error) == "Cache operation failed"
