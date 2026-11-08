"""
Shared parallel processing utilities for SOTD Pipeline phases.

This module provides standardized parallel month processing functionality
to eliminate code duplication across extract, match, enrich, and other phases.
"""

import logging
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Tuple

from tqdm import tqdm

from sotd.utils.logging_config import should_disable_tqdm

logger = logging.getLogger(__name__)


class ParallelMonthProcessor:
    """
    Utility class for parallel month processing across pipeline phases.

    Provides standardized parallel processing logic that can be used by
    extract, match, enrich, aggregate, and other phases.
    """

    def __init__(self, phase_name: str):
        """
        Initialize the parallel processor.

        Args:
            phase_name: Name of the phase (e.g., "extract", "match", "enrich")
        """
        self.phase_name = phase_name

    def should_use_parallel(
        self, months: List[Tuple[int, int]], args: Any, debug: bool = False
    ) -> bool:
        """
        Determine if parallel processing should be used.

        Args:
            months: List of (year, month) tuples
            args: CLI arguments object
            debug: Whether debug mode is enabled

        Returns:
            True if parallel processing should be used
        """
        if hasattr(args, "sequential") and args.sequential:
            return False
        elif hasattr(args, "parallel") and args.parallel:
            return True
        else:
            return len(months) > 1 and not debug

    def get_max_workers(self, months: List[Tuple[int, int]], args: Any, default: int = 4) -> int:
        """
        Get the maximum number of workers for parallel processing.

        Args:
            months: List of (year, month) tuples
            args: CLI arguments object
            default: Default max workers if not specified

        Returns:
            Maximum number of workers
        """
        return min(len(months), getattr(args, "max_workers", default))

    def process_months_parallel(
        self,
        months: List[Tuple[int, int]],
        process_func: Callable,
        process_args: Tuple[Any, ...],
        max_workers: int,
        desc: str = "Processing",
    ) -> List[Dict[str, Any]]:
        """
        Process multiple months in parallel using ProcessPoolExecutor.

        Args:
            months: List of (year, month) tuples
            process_func: Function to call for each month
            process_args: Additional arguments to pass to process_func
            max_workers: Maximum number of parallel workers
            desc: Description for progress bar

        Returns:
            List of results from processing each month
        """
        logger.debug(f"Processing {len(months)} months in parallel...")

        # Start wall clock timing
        wall_clock_start = time.time()

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all month processing tasks
            future_to_month = {
                executor.submit(process_func, year, month, *process_args): f"{year:04d}-{month:02d}"
                for year, month in months
            }

            # Process results as they complete
            results = []
            for future in tqdm(
                as_completed(future_to_month),
                total=len(future_to_month),
                desc=desc,
                unit="month",
                disable=should_disable_tqdm(),
            ):
                month = future_to_month[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.error(f"Error processing {month}: {e}")
                    results.append({"month": month, "error": str(e)})

        # Calculate wall clock time
        wall_clock_time = time.time() - wall_clock_start

        # Add wall clock timing to results for summary
        self._add_wall_clock_timing(results, wall_clock_time, max_workers)

        return results

    def process_months_sequential(
        self,
        months: List[Tuple[int, int]],
        process_func: Callable,
        process_args: Tuple[Any, ...],
        desc: str = "Months",
    ) -> List[Dict[str, Any]]:
        """
        Process multiple months sequentially.

        Args:
            months: List of (year, month) tuples
            process_func: Function to call for each month
            process_args: Additional arguments to pass to process_func
            desc: Description for progress bar

        Returns:
            List of results from processing each month
        """
        logger.debug(f"Processing {len(months)} month{'s' if len(months) != 1 else ''}...")

        # Start wall clock timing
        wall_clock_start = time.time()

        results = []
        for year, month in tqdm(months, desc=desc, unit="month", disable=should_disable_tqdm()):
            result = process_func(year, month, *process_args)
            if result:
                results.append(result)

        # Calculate wall clock time
        wall_clock_time = time.time() - wall_clock_start

        # Add wall clock timing to results for summary
        self._add_wall_clock_timing(results, wall_clock_time, 1)

        return results

    def _add_wall_clock_timing(
        self, results: List[Dict[str, Any]], wall_clock_time: float, max_workers: int
    ) -> None:
        """
        Add wall clock timing information to results for summary generation.

        Args:
            results: List of processing results
            wall_clock_time: Total wall clock time in seconds
            max_workers: Number of parallel workers used
        """
        for result in results:
            if "error" not in result:
                # Add wall clock timing info
                if "wall_clock_timing" not in result:
                    result["wall_clock_timing"] = {}
                result["wall_clock_timing"].update(
                    {
                        "wall_clock_time_seconds": wall_clock_time,
                        "parallel_workers": max_workers,
                        "parallel_efficiency": self._calculate_parallel_efficiency(
                            result, wall_clock_time, max_workers
                        ),
                    }
                )

    def _calculate_parallel_efficiency(
        self, result: Dict[str, Any], wall_clock_time: float, max_workers: int
    ) -> float:
        """
        Calculate parallel efficiency as a percentage.

        Args:
            result: Processing result for a month
            wall_clock_time: Total wall clock time
            max_workers: Number of parallel workers used

        Returns:
            Parallel efficiency as percentage (100% = perfect parallelization)
        """
        if max_workers <= 1:
            return 100.0

        # Get individual month processing time if available
        individual_time = result.get("performance", {}).get("total_processing_time_seconds", 0)
        if individual_time <= 0:
            return 0.0

        # Calculate theoretical sequential time vs actual parallel time
        theoretical_parallel_time = individual_time / max_workers
        if theoretical_parallel_time <= 0:
            return 0.0

        efficiency = (theoretical_parallel_time / wall_clock_time) * 100
        return min(100.0, max(0.0, efficiency))

    def print_parallel_summary(self, results: List[Dict[str, Any]], phase_name: str) -> None:
        """
        Print a standardized summary for parallel processing results.

        Args:
            results: List of processing results
            phase_name: Name of the phase for display
        """
        completed = [r for r in results if "error" not in r]
        errors = [r for r in results if "error" in r]

        logger.info("\nParallel processing summary:")
        logger.info(f"  Completed: {len(completed)} months")
        logger.info(f"  Errors: {len(errors)} months")

        if completed:
            # Print phase-specific summary
            self._print_phase_summary(completed, phase_name)

    def _print_phase_summary(
        self, completed_results: List[Dict[str, Any]], phase_name: str
    ) -> None:
        """
        Print phase-specific summary information.

        Args:
            completed_results: List of completed results (no errors)
            phase_name: Name of the phase
        """
        if phase_name == "extract":
            total_shaves = sum(r.get("meta", {}).get("shave_count", 0) for r in completed_results)
            total_skipped = sum(
                r.get("meta", {}).get("skipped_count", 0) for r in completed_results
            )

            logger.info("\nExtraction Summary:")
            logger.info(f"  Total Shaves: {total_shaves:,}")
            logger.info(f"  Total Skipped: {total_skipped:,}")

        elif phase_name == "enrich":
            total_records = sum(r.get("records_processed", 0) for r in completed_results)
            total_enriched = sum(r.get("total_enriched", 0) for r in completed_results)

            logger.info("\nEnrichment Summary:")
            logger.info(f"  Total Records: {total_records:,}")
            logger.info(f"  Total Enriched: {total_enriched:,}")

        elif phase_name == "match":
            # Get wall clock timing from first result
            wall_clock_timing = completed_results[0].get("wall_clock_timing", {})
            wall_clock_time = wall_clock_timing.get("wall_clock_time_seconds", 0)
            parallel_workers = wall_clock_timing.get("parallel_workers", 1)
            parallel_efficiency = wall_clock_timing.get("parallel_efficiency", 0)

            # Calculate total records and individual processing times
            total_records = sum(r.get("records_processed", 0) for r in completed_results)
            total_individual_time = sum(
                r.get("performance", {}).get("total_processing_time_seconds", 0)
                for r in completed_results
            )

            # Calculate true throughput and speedup
            true_throughput = total_records / wall_clock_time if wall_clock_time > 0 else 0
            theoretical_sequential_time = total_individual_time
            speedup = theoretical_sequential_time / wall_clock_time if wall_clock_time > 0 else 1.0

            logger.info("\nPerformance Summary:")
            logger.info(f"  Total Records: {total_records:,}")
            logger.info(f"  Wall Clock Time: {wall_clock_time:.2f}s")
            logger.info(f"  Parallel Workers: {parallel_workers}")
            logger.info(f"  True Throughput: {true_throughput:.0f} records/sec")
            logger.info(f"  Parallel Speedup: {speedup:.2f}x")
            logger.info(f"  Parallel Efficiency: {parallel_efficiency:.1f}%")

            # Show individual month performance for comparison
            if len(completed_results) > 1:
                avg_individual_time = total_individual_time / len(completed_results)
                logger.info(f"  Avg Individual Month Time: {avg_individual_time:.2f}s")
                logger.info(f"  Theoretical Sequential Time: {theoretical_sequential_time:.2f}s")

            # Aggregate and display enhanced match statistics
            self._print_aggregated_match_statistics(completed_results)

    def _print_aggregated_match_statistics(self, completed_results: List[Dict[str, Any]]) -> None:
        """
        Aggregate and display enhanced match statistics across all months.

        Args:
            completed_results: List of completed processing results
        """
        from collections import Counter

        # Aggregate statistics across all months
        total_records = 0
        total_matched = 0
        total_unmatched = 0
        field_presence = Counter()
        match_type_counts = Counter()
        field_match_type_counts = {
            "razor": Counter(),
            "blade": Counter(),
            "brush": Counter(),
            "soap": Counter(),
        }

        # Collect statistics from each month
        for result in completed_results:
            performance = result.get("performance", {})
            match_stats = performance.get("match_statistics", {})

            if not match_stats:
                continue

            # Aggregate totals
            total_records += match_stats.get("total_records", 0)
            match_summary = match_stats.get("match_summary", {})
            total_matched += match_summary.get("total_matched", 0)
            total_unmatched += match_summary.get("total_unmatched", 0)

            # Aggregate field presence
            field_presence.update(match_stats.get("field_presence", {}))

            # Aggregate overall match types
            overall_types = match_stats.get("match_types", {}).get("overall", {})
            match_type_counts.update(overall_types)

            # Aggregate field-specific match types
            by_field = match_stats.get("match_types", {}).get("by_field", {})
            for field, field_types in by_field.items():
                if field in field_match_type_counts:
                    field_match_type_counts[field].update(field_types)

        # Calculate overall match rate
        overall_match_rate = (
            (total_matched / (total_matched + total_unmatched) * 100)
            if (total_matched + total_unmatched) > 0
            else 0
        )

        # Display aggregated statistics
        logger.info("\nMatch Statistics Summary:")
        logger.info("=" * 50)
        logger.info(f"Total Records: {total_records:,}")
        logger.info(f"Total Matched: {total_matched:,}")
        logger.info(f"Total Unmatched: {total_unmatched:,}")
        logger.info(f"Overall Match Rate: {overall_match_rate:.1f}%")

        # Field presence
        logger.info("\nField Presence:")
        for field, count in field_presence.most_common():
            logger.info(f"  {field.capitalize()}: {count:,}")

        # Overall match types
        logger.info("\nOverall Match Types:")
        for match_type, count in match_type_counts.most_common():
            logger.info(f"  {match_type}: {count:,}")

        # Field-specific analysis
        logger.info("\nField-Specific Analysis:")
        for field in ["razor", "blade", "brush", "soap"]:
            field_total = field_presence.get(field, 0)
            if field_total > 0:
                field_matches = field_match_type_counts[field]
                total_field_matches = sum(field_matches.values())
                success_rate = (total_field_matches / field_total * 100) if field_total > 0 else 0

                logger.info(f"\n  {field.capitalize()}:")
                logger.info(f"    Present: {field_total:,}")
                logger.info(f"    Success Rate: {success_rate:.1f}%")

                # Show all match types for this field
                for match_type, count in field_matches.most_common():
                    if count > 0:
                        percentage = (count / field_total * 100) if field_total > 0 else 0
                        logger.info(f"      {match_type}: {count:,} ({percentage:.1f}%)")


def create_parallel_processor(phase_name: str) -> ParallelMonthProcessor:
    """
    Factory function to create a parallel processor for a specific phase.

    Args:
        phase_name: Name of the phase (e.g., "extract", "match", "enrich")

    Returns:
        Configured ParallelMonthProcessor instance
    """
    return ParallelMonthProcessor(phase_name)
