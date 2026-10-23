"""Performance tests for tier-based delta calculation system."""

import time
import statistics

import pytest

from sotd.report.delta_calculator import DeltaCalculator
from sotd.report.annual_delta_calculator import AnnualDeltaCalculator

# Wall-clock threshold asserts are load-sensitive; excluded in CI via `-m "not perf"`.
pytestmark = pytest.mark.perf


class TestTierDeltaPerformance:
    """Performance tests for tier-based delta calculation system."""

    def test_baseline_performance(self):
        """Test baseline performance characteristics."""
        # Create baseline dataset (100 items)
        current_data = []
        historical_data = []

        for i in range(100):
            rank = (i // 10) + 1  # 10 tiers
            current_data.append(
                {"name": f"Product {i:03d}", "shaves": 1000 - (i % 100), "rank": rank}
            )

            historical_data.append(
                {
                    "name": f"Product {i:03d}",
                    "shaves": 1000 - (i % 100) + (10 if i % 7 == 0 else 0),
                    "rank": rank + (1 if i % 5 == 0 else 0),
                }
            )

        calculator = DeltaCalculator()

        # Measure baseline performance
        start_time = time.time()
        results = calculator.calculate_tier_based_deltas(
            current_data, historical_data, max_items=100
        )
        end_time = time.time()

        baseline_time = end_time - start_time

        # Verify results
        assert len(results) == 100

        # Baseline performance: Should complete in under 1 second for 100 items
        assert baseline_time < 1.0

        # Store baseline for comparison
        self.baseline_time = baseline_time
        print(f"Baseline performance (100 items): {baseline_time:.4f} seconds")

    def test_scalability_performance(self):
        """Test performance scaling with data size."""
        calculator = DeltaCalculator()
        performance_data = []

        # Test various dataset sizes
        for size in [100, 500, 1000, 2000]:
            current_data = []
            historical_data = []

            for i in range(size):
                rank = (i // 20) + 1  # 50 tiers for 1000 items, 100 tiers for 2000 items
                current_data.append(
                    {"name": f"Product {i:04d}", "shaves": 1000 - (i % 100), "rank": rank}
                )

                historical_data.append(
                    {
                        "name": f"Product {i:04d}",
                        "shaves": 1000 - (i % 100) + (10 if i % 7 == 0 else 0),
                        "rank": rank + (1 if i % 5 == 0 else 0),
                    }
                )

            # Measure performance
            start_time = time.time()
            results = calculator.calculate_tier_based_deltas(
                current_data, historical_data, max_items=size
            )
            end_time = time.time()

            processing_time = end_time - start_time
            performance_data.append((size, processing_time))

            # Verify results
            assert len(results) == size

            print(f"Performance ({size} items): {processing_time:.4f} seconds")

        # Performance requirements: Should scale reasonably with data size
        # Linear scaling would be ideal, but some overhead is acceptable
        for size, time_taken in performance_data:
            if size == 100:
                # Baseline: 100 items should be fastest
                assert time_taken < 1.0
            elif size == 500:
                # 500 items should complete in reasonable time
                assert time_taken < 2.0
            elif size == 1000:
                # 1000 items should complete in reasonable time
                assert time_taken < 5.0
            elif size == 2000:
                # 2000 items should complete in reasonable time
                assert time_taken < 10.0

    def test_memory_usage_optimization(self):
        """Test memory usage characteristics."""
        import psutil
        import os

        # Get current process
        process = psutil.Process(os.getpid())

        # Measure memory before
        memory_before = process.memory_info().rss / 1024 / 1024  # MB

        # Create large dataset
        current_data = []
        historical_data = []

        for i in range(1000):
            rank = (i // 10) + 1
            current_data.append(
                {"name": f"Product {i:04d}", "shaves": 1000 - (i % 100), "rank": rank}
            )

            historical_data.append(
                {
                    "name": f"Product {i:04d}",
                    "shaves": 1000 - (i % 100) + (10 if i % 7 == 0 else 0),
                    "rank": rank + (1 if i % 5 == 0 else 0),
                }
            )

        calculator = DeltaCalculator()

        # Process data
        results = calculator.calculate_tier_based_deltas(
            current_data, historical_data, max_items=1000
        )

        # Measure memory after
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_used = memory_after - memory_before

        # Verify results
        assert len(results) == 1000

        # Memory usage should be reasonable (under 100MB increase)
        assert memory_used < 100.0

        print(f"Memory usage: {memory_used:.2f} MB")

    def test_optimization_impact(self):
        """Test impact of optimizations on performance."""
        calculator = DeltaCalculator()

        # Create dataset for optimization testing
        current_data = []
        historical_data = []

        for i in range(500):
            rank = (i // 10) + 1
            current_data.append(
                {"name": f"Product {i:04d}", "shaves": 1000 - (i % 100), "rank": rank}
            )

            historical_data.append(
                {
                    "name": f"Product {i:04d}",
                    "shaves": 1000 - (i % 100) + (10 if i % 7 == 0 else 0),
                    "rank": rank + (1 if i % 5 == 0 else 0),
                }
            )

        # Test multiple runs to measure consistency
        run_times = []

        for run in range(5):
            start_time = time.time()
            results = calculator.calculate_tier_based_deltas(
                current_data, historical_data, max_items=500
            )
            end_time = time.time()

            run_time = end_time - start_time
            run_times.append(run_time)

            # Verify results
            assert len(results) == 500

        # Calculate performance statistics
        avg_time = statistics.mean(run_times)
        std_time = statistics.stdev(run_times) if len(run_times) > 1 else 0

        # Performance should be consistent (low standard deviation)
        # For small time measurements, allow higher variation due to system noise
        max_variation = 0.5 if avg_time < 0.1 else 0.2  # 50% for <100ms, 20% for >=100ms
        assert std_time < avg_time * max_variation, (
            f"Performance too variable: std={std_time:.4f}s, "
            f"avg={avg_time:.4f}s, max_variation={max_variation}"
        )

        # Average performance should be good
        assert avg_time < 3.0  # Under 3 seconds for 500 items

        print(f"Performance consistency: avg={avg_time:.4f}s, std={std_time:.4f}s")

    def test_annual_delta_performance(self):
        """Test performance of annual delta calculations."""
        annual_calculator = AnnualDeltaCalculator()

        # Create annual dataset
        current_year_data = {"year": "2024", "data": {"razors": [], "blades": [], "soaps": []}}

        previous_year_data = {"year": "2023", "data": {"razors": [], "blades": [], "soaps": []}}

        # Populate with realistic data
        for category in ["razors", "blades", "soaps"]:
            for i in range(200):  # 200 items per category
                rank = (i // 20) + 1
                current_year_data["data"][category].append(
                    {
                        "name": f"{category.title()} {i:03d}",
                        "shaves": 1000 - (i % 100),
                        "rank": rank,
                    }
                )

                previous_year_data["data"][category].append(
                    {
                        "name": f"{category.title()} {i:03d}",
                        "shaves": 1000 - (i % 100) + (10 if i % 7 == 0 else 0),
                        "rank": rank + (1 if i % 5 == 0 else 0),
                    }
                )

        # Measure annual delta performance
        start_time = time.time()
        results = annual_calculator.calculate_tier_based_annual_deltas(
            current_year_data, previous_year_data, max_items=200
        )
        end_time = time.time()

        annual_time = end_time - start_time

        # Verify results
        assert "razors" in results
        assert "blades" in results
        assert "soaps" in results
        assert len(results["razors"]) == 200
        assert len(results["blades"]) == 200
        assert len(results["soaps"]) == 200

        # Annual delta calculation should complete in reasonable time
        # 600 total items across 3 categories
        assert annual_time < 10.0

        print(f"Annual delta performance (600 items): {annual_time:.4f} seconds")

    def test_production_scale_performance(self):
        """Test performance at production scale."""
        calculator = DeltaCalculator()

        # Create production-scale dataset (5000 items)
        current_data = []
        historical_data = []

        for i in range(5000):
            rank = (i // 50) + 1  # 100 tiers
            current_data.append(
                {"name": f"Product {i:05d}", "shaves": 1000 - (i % 100), "rank": rank}
            )

            historical_data.append(
                {
                    "name": f"Product {i:05d}",
                    "shaves": 1000 - (i % 100) + (10 if i % 7 == 0 else 0),
                    "rank": rank + (1 if i % 5 == 0 else 0),
                }
            )

        # Measure production-scale performance
        start_time = time.time()
        results = calculator.calculate_tier_based_deltas(
            current_data, historical_data, max_items=5000
        )
        end_time = time.time()

        production_time = end_time - start_time

        # Verify results
        assert len(results) == 5000

        # Production-scale performance: Should complete in under 30 seconds
        assert production_time < 30.0

        print(f"Production-scale performance (5000 items): {production_time:.4f} seconds")

        # Performance should scale reasonably
        # If 1000 items takes ~5s, 5000 items should take ~25s or less
        expected_max_time = 25.0
        assert production_time <= expected_max_time

        print(f"Performance scaling: {production_time:.4f}s vs expected max {expected_max_time}s")
