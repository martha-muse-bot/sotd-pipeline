"""
Performance Tests for Split Brush Functionality

This module tests the performance characteristics of split brush functionality
to ensure efficient component lookup and acceptable performance.
"""

import time
from pathlib import Path
from typing import Any, Dict, List

import pytest
from rich.console import Console

from sotd.match.tools.analyzers.mismatch_analyzer import MismatchAnalyzer
from sotd.match.tools.managers.correct_matches_manager import CorrectMatchesManager


class TestSplitBrushPerformance:
    """Test performance characteristics of split brush functionality."""

    @pytest.fixture
    def large_split_brush_dataset(self) -> List[Dict[str, Any]]:
        """Create a large dataset of split brushes for performance testing."""
        dataset = []

        # Create 1000 split brushes with various combinations
        for i in range(1000):
            handle_num = i % 50  # 50 different handles
            knot_num = i % 20  # 20 different knots

            dataset.append(
                {
                    "id": f"test_{i}",
                    "brush": {
                        "original": f"handle_{handle_num} w/ knot_{knot_num}",
                        "normalized": f"handle_{handle_num} w/ knot_{knot_num}",
                        "matched": {
                            "brand": None,
                            "model": None,
                            "handle": {
                                "brand": f"HandleMaker_{handle_num}",
                                "model": f"Model_{handle_num}",
                                "normalized": f"handlemaker_{handle_num} model_{handle_num}",
                            },
                            "knot": {
                                "brand": f"KnotMaker_{knot_num}",
                                "model": f"Knot_{knot_num}",
                                "normalized": f"knotmaker_{knot_num} knot_{knot_num}",
                            },
                        },
                        "match_type": "split_detection",
                        "confidence": 0.8,
                    },
                }
            )

        return dataset

    @pytest.fixture
    def temp_data_dir(self, tmp_path) -> Path:
        """Create temporary data directory for testing."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        return data_dir

    @pytest.fixture
    def temp_correct_matches_file(self, temp_data_dir) -> Path:
        """Create temporary correct_matches.yaml file."""
        correct_matches_file = temp_data_dir / "correct_matches.yaml"
        correct_matches_file.write_text("brush: {}\nhandle: {}\nknot: {}\nsplit_brush: {}")
        return correct_matches_file

    def test_mismatch_analyzer_performance(
        self, large_split_brush_dataset, temp_correct_matches_file
    ):
        """Test performance of mismatch analyzer with large split brush dataset."""

        # Create data structure expected by MismatchAnalyzer
        data = {"data": large_split_brush_dataset}

        # Create analyzer
        console = Console()
        analyzer = MismatchAnalyzer(console)
        analyzer._set_test_correct_matches_file(str(temp_correct_matches_file))

        # Mock args object
        class MockArgs:
            debug = False
            threshold = 3
            limit = 50

        args = MockArgs()

        # Measure performance
        start_time = time.time()
        mismatches = analyzer.identify_mismatches(data, "brush", args)
        end_time = time.time()

        processing_time = end_time - start_time

        # Performance requirements:
        # - Should process 1000 items in less than 5 seconds
        # - Should detect all split brushes correctly
        assert (
            processing_time < 5.0
        ), f"Performance test failed: {processing_time:.2f}s for 1000 items"

        # Verify all split brushes were detected
        split_brush_mismatches = []
        for category in mismatches.values():
            for mismatch in category:
                if mismatch.get("is_split_brush"):
                    split_brush_mismatches.append(mismatch)

        # Should detect all 1000 split brushes
        assert (
            len(split_brush_mismatches) == 1000
        ), f"Expected 1000 split brushes, got {len(split_brush_mismatches)}"

        print(f"✅ MismatchAnalyzer performance: {processing_time:.2f}s for 1000 items")

    def test_correct_matches_manager_performance(self, temp_correct_matches_file):
        """Test performance of CorrectMatchesManager with many split brush operations."""

        console = Console()
        manager = CorrectMatchesManager(console, temp_correct_matches_file)

        # Measure performance of multiple split brush operations
        start_time = time.time()

        # Add 100 split brush entries
        for i in range(100):
            match_data = {
                "original": f"test_handle_{i} w/ test_knot_{i}",
                "matched": {
                    "brand": None,
                    "model": None,
                    "handle": {
                        "brand": f"HandleMaker_{i}",
                        "model": f"Model_{i}",
                    },
                    "knot": {
                        "brand": f"KnotMaker_{i}",
                        "model": f"Knot_{i}",
                    },
                },
                "field": "brush",
            }

            match_key = manager.create_match_key(
                "brush", match_data["original"], match_data["matched"]
            )
            manager.mark_match_as_correct(match_key, match_data)

        # Save all changes
        manager.save_correct_matches()

        end_time = time.time()
        processing_time = end_time - start_time

        # Performance requirements:
        # - Should process 100 split brush operations in less than 2 seconds
        assert (
            processing_time < 2.0
        ), f"Performance test failed: {processing_time:.2f}s for 100 operations"

        print(f"✅ CorrectMatchesManager performance: {processing_time:.2f}s for 100 operations")

    def test_memory_usage(self, large_split_brush_dataset, temp_correct_matches_file):
        """Test memory usage with large datasets."""

        import os

        import psutil

        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create data structure
        data = {"data": large_split_brush_dataset}

        # Create analyzer and process data
        console = Console()
        analyzer = MismatchAnalyzer(console)
        analyzer._set_test_correct_matches_file(str(temp_correct_matches_file))

        class MockArgs:
            debug = False
            threshold = 3
            limit = 50

        args = MockArgs()

        # Process data
        mismatches = analyzer.identify_mismatches(data, "brush", args)

        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory requirements:
        # - Should not increase memory usage by more than 100MB for 1000 items
        assert memory_increase < 100.0, f"Memory usage increased by {memory_increase:.1f}MB"

        print(f"✅ Memory usage: {memory_increase:.1f}MB increase for 1000 items")

    def test_component_lookup_efficiency(self, temp_correct_matches_file):
        """Test efficiency of component lookup operations."""

        console = Console()
        manager = CorrectMatchesManager(console, temp_correct_matches_file)

        # Add many split brushes with shared components
        start_time = time.time()

        # Create 20 handle makers, 10 knot makers
        for handle_maker in range(20):
            for knot_maker in range(10):
                match_data = {
                    "original": f"handle_{handle_maker} w/ knot_{knot_maker}",
                    "matched": {
                        "brand": None,
                        "model": None,
                        "handle": {
                            "brand": f"HandleMaker_{handle_maker}",
                            "model": f"Model_{handle_maker}",
                        },
                        "knot": {
                            "brand": f"KnotMaker_{knot_maker}",
                            "model": f"Knot_{knot_maker}",
                        },
                    },
                    "field": "brush",
                }

                match_key = manager.create_match_key(
                    "brush", match_data["original"], match_data["matched"]
                )
                manager.mark_match_as_correct(match_key, match_data)

        manager.save_correct_matches()

        end_time = time.time()
        processing_time = end_time - start_time

        # Should handle 200 split brush operations efficiently
        assert (
            processing_time < 3.0
        ), f"Component lookup test failed: {processing_time:.2f}s for 200 operations"

        print(f"✅ Component lookup efficiency: {processing_time:.2f}s for 200 operations")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
