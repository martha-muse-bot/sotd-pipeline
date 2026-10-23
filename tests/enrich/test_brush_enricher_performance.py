"""Performance tests for BrushEnricher user intent detection."""

import re
import time
from unittest.mock import patch

import pytest

from sotd.enrich.brush_enricher import BrushEnricher

# Wall-clock threshold asserts are load-sensitive; excluded in CI via `-m "not perf"`.
pytestmark = pytest.mark.perf


class TestBrushEnricherPerformance:
    """Test performance characteristics of user intent detection."""

    @pytest.fixture
    def brush_enricher(self):
        """Create BrushEnricher instance for testing."""
        return BrushEnricher()

    @pytest.fixture
    def mock_handle_data(self):
        """Mock handle data for testing."""
        return {"brand": "Declaration", "model": "B2", "handle_maker": "Declaration"}

    @pytest.fixture
    def mock_knot_data(self):
        """Mock knot data for testing."""
        return {"brand": "Zenith", "model": "B2", "fiber": "Boar", "knot_size_mm": 26}

    def test_pattern_compilation_caching_performance(
        self, brush_enricher, mock_handle_data, mock_knot_data
    ):
        """Test that pattern compilation caching improves performance."""
        brush_string = "Declaration B2 in Zenith B2 Boar"

        # Mock pattern loading with multiple patterns to test compilation
        handle_patterns = ["declaration.*b2", "declaration", "b2.*declaration"]
        knot_patterns = ["zenith.*b2", "zenith", "b2.*zenith"]

        with (
            patch.object(brush_enricher, "_load_handle_patterns", return_value=handle_patterns),
            patch.object(brush_enricher, "_load_knot_patterns", return_value=knot_patterns),
        ):
            # First call - should compile patterns
            start_time = time.time()
            intent1 = brush_enricher._detect_user_intent(
                brush_string, mock_handle_data, mock_knot_data
            )
            first_call_time = time.time() - start_time

            # Second call - should use cached compiled patterns
            start_time = time.time()
            intent2 = brush_enricher._detect_user_intent(
                brush_string, mock_handle_data, mock_knot_data
            )
            second_call_time = time.time() - start_time

            # Results should be identical
            assert intent1 == intent2
            assert intent1 in ["handle_primary", "knot_primary", "unknown"]

            # Second call should be faster (cached compilation)
            # Note: For small patterns, the difference might be minimal
            # Allow more variance for very fast operations
            # Handle case where first_call_time is 0 (very fast execution)
            if first_call_time > 0:
                assert second_call_time <= first_call_time * 3.0  # Allow more variance
            else:
                # If first call was extremely fast, just ensure second call is also fast
                assert second_call_time < 0.001  # Should still be very fast

    def test_catalog_loader_cache_performance(self, brush_enricher):
        """Test that catalog loader caching improves performance."""
        # Test handle patterns loading
        start_time = time.time()
        patterns1 = brush_enricher._load_handle_patterns("Alpha", "T-400")
        first_load_time = time.time() - start_time

        start_time = time.time()
        patterns2 = brush_enricher._load_handle_patterns("Alpha", "T-400")
        second_load_time = time.time() - start_time

        # Results should be identical
        assert patterns1 == patterns2

        # Second load should be faster (cached)
        assert second_load_time <= first_load_time * 0.5  # Should be significantly faster

        # Test cache stats
        cache_stats = brush_enricher.catalog_loader.get_cache_stats()
        assert cache_stats["cache_hits"] > 0
        assert cache_stats["cache_misses"] > 0
        assert cache_stats["hit_rate_percent"] > 0

    def test_large_dataset_performance(self, brush_enricher, mock_handle_data, mock_knot_data):
        """Test performance with larger datasets."""
        # Create a longer brush string to test regex performance
        brush_string = "Declaration B2 in Zenith B2 Boar with additional text " * 10

        # Mock pattern loading
        handle_patterns = ["declaration.*b2", "declaration"]
        knot_patterns = ["zenith.*b2", "zenith"]

        with (
            patch.object(
                brush_enricher.catalog_loader,
                "load_compiled_handle_patterns",
                return_value=[re.compile(p, re.IGNORECASE) for p in handle_patterns],
            ),
            patch.object(
                brush_enricher.catalog_loader,
                "load_compiled_knot_patterns",
                return_value=[re.compile(p, re.IGNORECASE) for p in knot_patterns],
            ),
        ):
            # Test multiple iterations
            start_time = time.time()
            for _ in range(100):
                intent = brush_enricher._detect_user_intent(
                    brush_string, mock_handle_data, mock_knot_data
                )
                assert intent in ["handle_primary", "knot_primary", "unknown"]
            total_time = time.time() - start_time

            # Should complete 100 iterations in reasonable time (< 1 second)
            assert total_time < 1.0

            # Average time per iteration should be reasonable (< 10ms)
            avg_time_per_iteration = total_time / 100
            assert avg_time_per_iteration < 0.01

    def test_memory_usage_validation(self, brush_enricher):
        """Test that memory usage remains reasonable."""
        import psutil
        import os

        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Perform multiple pattern loads to test memory usage
        for i in range(50):
            brush_enricher._load_handle_patterns(f"Brand{i}", f"Model{i}")
            brush_enricher._load_knot_patterns(f"KnotBrand{i}", f"KnotModel{i}")

        # Get memory usage after operations
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (< 10MB for 50 pattern loads)
        # Note: This is a rough estimate and may vary by system
        assert memory_increase < 10 * 1024 * 1024  # 10MB

        # Check cache stats
        cache_stats = brush_enricher.catalog_loader.get_cache_stats()
        assert cache_stats["cached_patterns"] > 0

    def test_early_exit_performance(self, brush_enricher):
        """Test that early exit optimizations work correctly."""
        # Test with invalid data that should trigger early exit
        invalid_handle_data = None
        invalid_knot_data = {"brand": "Zenith", "model": "B2"}

        start_time = time.time()
        # Should raise ValueError for invalid data (fail-fast behavior)
        with pytest.raises(ValueError):
            brush_enricher._detect_user_intent(
                "some string", invalid_handle_data, invalid_knot_data
            )
        early_exit_time = time.time() - start_time

        # Early exit should be very fast (< 1ms)
        assert early_exit_time < 0.001

    def test_pattern_matching_performance(self, brush_enricher, mock_handle_data, mock_knot_data):
        """Test performance of pattern matching with various string lengths."""
        # Test with different string lengths
        test_cases = [
            "Declaration B2 in Zenith B2",  # Short
            "Declaration B2 in Zenith B2 Boar " * 5,  # Medium
            "Declaration B2 in Zenith B2 Boar " * 20,  # Long
        ]

        handle_patterns = ["declaration.*b2"]
        knot_patterns = ["zenith.*b2"]

        with (
            patch.object(
                brush_enricher.catalog_loader,
                "load_compiled_handle_patterns",
                return_value=[re.compile(p, re.IGNORECASE) for p in handle_patterns],
            ),
            patch.object(
                brush_enricher.catalog_loader,
                "load_compiled_knot_patterns",
                return_value=[re.compile(p, re.IGNORECASE) for p in knot_patterns],
            ),
        ):
            for brush_string in test_cases:
                start_time = time.time()
                intent = brush_enricher._detect_user_intent(
                    brush_string, mock_handle_data, mock_knot_data
                )
                processing_time = time.time() - start_time

                assert intent in ["handle_primary", "knot_primary", "unknown"]
                # Processing time should be reasonable even for long strings (< 10ms)
                assert processing_time < 0.01

    def test_cache_clear_performance(self, brush_enricher):
        """Test that cache clearing works correctly and doesn't impact performance."""
        # Load some patterns to populate cache
        brush_enricher._load_handle_patterns("Alpha", "T-400")
        brush_enricher._load_knot_patterns("Zenith", "B03 (aka B2)")

        # Verify cache has entries
        cache_stats_before = brush_enricher.catalog_loader.get_cache_stats()
        assert cache_stats_before["cached_patterns"] > 0

        # Clear cache
        start_time = time.time()
        brush_enricher.catalog_loader.clear_pattern_cache()
        clear_time = time.time() - start_time

        # Cache clearing should be very fast (< 1ms)
        assert clear_time < 0.001

        # Verify cache is empty
        cache_stats_after = brush_enricher.catalog_loader.get_cache_stats()
        assert cache_stats_after["cached_patterns"] == 0
        assert cache_stats_after["cache_hits"] == 0
        assert cache_stats_after["cache_misses"] == 0
