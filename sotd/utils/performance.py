"""
General performance monitoring for the SOTD Pipeline.

This module provides general performance monitoring functionality by extending
the base performance monitoring classes.
"""

import logging
from typing import Dict

from sotd.utils.performance_base import (
    BasePerformanceMetrics,
    BasePerformanceMonitor,
    PipelinePerformanceTracker,
    TimingContext,
)

logger = logging.getLogger(__name__)


class GeneralPerformanceMetrics(BasePerformanceMetrics):
    """Performance metrics for general pipeline phases."""

    # Use the base phase_times field for general phase operations
    # No additional fields needed for general performance monitoring

    def to_dict(self) -> Dict:
        """Convert metrics to dictionary for JSON serialization."""
        return super().to_dict()


class PerformanceMonitor(BasePerformanceMonitor):
    """Performance monitoring utility for general pipeline phases."""

    def __init__(self, phase_name: str = "unknown", parallel_workers: int = 1):
        super().__init__(phase_name, parallel_workers)
        # Type annotation to help type checker
        self.metrics: GeneralPerformanceMetrics = self.metrics

    def _create_metrics(self, phase_name: str, parallel_workers: int) -> GeneralPerformanceMetrics:
        """Create general performance metrics instance."""
        return GeneralPerformanceMetrics(phase_name=phase_name, parallel_workers=parallel_workers)

    def print_summary(self) -> None:
        """Print a human-readable performance summary."""
        logger.info("\n" + "=" * 60)
        logger.info(f"{self.metrics.phase_name.upper()} PHASE PERFORMANCE SUMMARY")
        logger.info("=" * 60)

        logger.info(f"Total Processing Time: {self.metrics.total_processing_time:.2f}s")
        logger.info(f"Records Processed: {self.metrics.record_count:,}")
        logger.info(f"Processing Rate: {self.metrics.records_per_second:.1f} records/second")
        logger.info(f"Average Time per Record: {self.metrics.avg_time_per_record * 1000:.1f}ms")

        if self.metrics.parallel_workers > 1:
            logger.info(f"Parallel Workers: {self.metrics.parallel_workers}")

        logger.info("\nTiming Breakdown:")
        io_percent = (
            self.metrics.file_io_time / self.metrics.total_processing_time * 100
            if self.metrics.total_processing_time > 0
            else 0
        )
        processing_percent = (
            self.metrics.processing_time / self.metrics.total_processing_time * 100
            if self.metrics.total_processing_time > 0
            else 0
        )
        logger.info(f"  File I/O: {self.metrics.file_io_time:.2f}s ({io_percent:.1f}%)")
        logger.info(
            f"  Processing: {self.metrics.processing_time:.2f}s ({processing_percent:.1f}%)"
        )

        if self.metrics.phase_times:
            logger.info("\nPhase Performance:")
            for phase, stats in self.metrics.phase_times.items():
                logger.info(f"  {phase}: {stats.avg_time * 1000:.1f}ms avg ({stats.count} calls)")

        logger.info("\nMemory Usage:")
        logger.info(f"  Peak: {self.metrics.peak_memory_mb:.1f}MB")
        logger.info(f"  Final: {self.metrics.final_memory_mb:.1f}MB")

        logger.info("\nFile Sizes:")
        logger.info(f"  Input: {self.metrics.input_file_size_mb:.1f}MB")
        if self.metrics.output_file_size_mb > 0:
            logger.info(f"  Output: {self.metrics.output_file_size_mb:.1f}MB")

        logger.info("=" * 60)


class PipelineOutputFormatter:
    """Standardized output formatting for pipeline phases."""

    @staticmethod
    def format_single_month_summary(phase: str, month: str, stats: Dict) -> str:
        """Format summary for single month processing."""
        if phase == "fetch":
            missing_days = stats.get("missing_days", 0)
            return (
                f"SOTD {phase} complete for {month}: "
                f"{stats.get('threads', 0)} threads, "
                f"{stats.get('comments', 0)} comments, "
                f"{missing_days} missing day{'s' if missing_days != 1 else ''}"
            )
        elif phase == "extract":
            return (
                f"SOTD {phase} complete for {month}: "
                f"{stats.get('shave_count', 0)} shaves extracted, "
                f"{stats.get('skipped_count', 0)} skipped"
            )
        elif phase == "match":
            return (
                f"SOTD {phase} complete for {month}: "
                f"{stats.get('records_processed', 0):,} records processed"
            )
        elif phase == "enrich":
            return (
                f"SOTD {phase} complete for {month}: "
                f"{stats.get('records_processed', 0):,} records enriched"
            )
        elif phase == "aggregate":
            return (
                f"SOTD {phase} complete for {month}: "
                f"{stats.get('record_count', 0):,} records aggregated"
            )
        elif phase == "report":
            return (
                f"SOTD {phase} complete for {month}: "
                f"{stats.get('report_type', 'hardware')} report generated"
            )
        else:
            return f"SOTD {phase} complete for {month}"

    @staticmethod
    def format_multi_month_summary(
        phase: str, start_month: str, end_month: str, stats: Dict
    ) -> str:
        """Format summary for multi-month processing."""
        if phase == "fetch":
            total_missing = stats.get("total_missing_days", 0)
            return (
                f"SOTD {phase} complete for {start_month}…{end_month}: "
                f"{stats.get('total_threads', 0)} threads, "
                f"{stats.get('total_comments', 0)} comments, "
                f"{total_missing} missing day{'s' if total_missing != 1 else ''}"
            )
        elif phase == "extract":
            return (
                f"SOTD {phase} complete for {start_month}…{end_month}: "
                f"{stats.get('total_records', 0):,} records processed, "
                f"{stats.get('total_skipped', 0):,} skipped"
            )
        else:
            return (
                f"SOTD {phase} complete for {start_month}…{end_month}: "
                f"{stats.get('total_records', 0):,} records processed"
            )

    @staticmethod
    def format_progress_bar(desc: str, total: int, unit: str = "month") -> str:
        """Format standardized progress bar description."""
        return f"{desc.capitalize()} {total} {unit}{'s' if total != 1 else ''}"

    @staticmethod
    def format_parallel_summary(
        completed: int, skipped: int, errors: int, total_records: int, total_time: float
    ) -> str:
        """Format parallel processing summary."""
        avg_records_per_sec = total_records / total_time if total_time > 0 else 0

        summary = "\nParallel processing summary:\n"
        summary += f"  Completed: {completed} months\n"
        summary += f"  Skipped: {skipped} months\n"
        summary += f"  Errors: {errors} months\n"
        summary += "\nPerformance Summary:\n"
        summary += f"  Total Records: {total_records:,}\n"
        summary += f"  Total Processing Time: {total_time:.2f}s\n"
        summary += f"  Average Throughput: {avg_records_per_sec:.0f} records/sec"

        return summary


__all__ = [
    "PerformanceMonitor",
    "GeneralPerformanceMetrics",
    "TimingContext",
    "PipelinePerformanceTracker",
    "PipelineOutputFormatter",
]
