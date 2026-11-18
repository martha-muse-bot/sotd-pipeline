"""
Integration tests for general performance monitoring.

These tests verify that the general performance monitoring works correctly
in real-world scenarios across different pipeline phases.
"""

import time

from sotd.utils.performance import PerformanceMonitor


class TestGeneralPerformanceMonitoringIntegration:
    """Test general performance monitoring integration."""

    def test_extract_phase_performance_monitoring(self):
        """Test performance monitoring in extract phase simulation."""
        monitor = PerformanceMonitor("extract")

        # Simulate extract phase operations
        monitor.start_total_timing()

        # Simulate file I/O
        monitor.start_file_io_timing()
        time.sleep(0.01)  # Simulate file reading
        monitor.end_file_io_timing()

        # Simulate processing
        monitor.start_processing_timing()
        for i in range(100):
            time.sleep(0.001)  # Simulate record processing
        monitor.set_record_count(100)
        monitor.end_processing_timing()

        monitor.end_total_timing()

        # Verify metrics
        assert monitor.metrics.phase_name == "extract"
        assert monitor.metrics.record_count == 100
        assert monitor.metrics.total_processing_time > 0
        assert monitor.metrics.file_io_time > 0
        assert monitor.metrics.processing_time > 0
        assert monitor.metrics.records_per_second > 0

    def test_enrich_phase_performance_monitoring(self):
        """Test performance monitoring in enrich phase simulation."""
        monitor = PerformanceMonitor("enrich")

        # Simulate enrich phase operations
        monitor.start_total_timing()

        # Simulate multiple enrichers
        for enricher in ["blade", "razor", "brush", "soap"]:
            start_time = time.time()
            time.sleep(0.005)  # Simulate enricher processing
            duration = time.time() - start_time
            monitor.record_phase_timing(enricher, duration)

        # Simulate record processing
        monitor.start_processing_timing()
        for i in range(50):
            time.sleep(0.001)  # Simulate record processing
        monitor.set_record_count(50)
        monitor.end_processing_timing()

        monitor.end_total_timing()

        # Verify metrics
        assert monitor.metrics.phase_name == "enrich"
        assert monitor.metrics.record_count == 50
        assert len(monitor.metrics.phase_times) == 4
        assert "blade" in monitor.metrics.phase_times
        assert "razor" in monitor.metrics.phase_times
        assert "brush" in monitor.metrics.phase_times
        assert "soap" in monitor.metrics.phase_times

    def test_aggregate_phase_performance_monitoring(self):
        """Test performance monitoring in aggregate phase simulation."""
        monitor = PerformanceMonitor("aggregate", parallel_workers=2)

        # Simulate aggregate phase operations
        monitor.start_total_timing()

        # Simulate file I/O for loading data
        monitor.start_file_io_timing()
        time.sleep(0.01)  # Simulate loading data
        monitor.end_file_io_timing()

        # Simulate aggregation processing
        monitor.start_processing_timing()
        for i in range(200):
            time.sleep(0.0005)  # Simulate aggregation processing
        monitor.set_record_count(200)
        monitor.end_processing_timing()

        # Simulate file I/O for saving results
        monitor.start_file_io_timing()
        time.sleep(0.01)  # Simulate saving results
        monitor.end_file_io_timing()

        monitor.end_total_timing()

        # Verify metrics
        assert monitor.metrics.phase_name == "aggregate"
        assert monitor.metrics.parallel_workers == 2
        assert monitor.metrics.record_count == 200
        assert monitor.metrics.file_io_time > 0
        assert monitor.metrics.processing_time > 0

    def test_report_phase_performance_monitoring(self):
        """Test performance monitoring in report phase simulation."""
        monitor = PerformanceMonitor("report")

        # Simulate report phase operations
        monitor.start_total_timing()

        # Simulate template loading
        start_time = time.time()
        time.sleep(0.005)  # Simulate template loading
        duration = time.time() - start_time
        monitor.record_phase_timing("template_loading", duration)

        # Simulate data processing
        start_time = time.time()
        for i in range(75):
            time.sleep(0.001)  # Simulate data processing
        duration = time.time() - start_time
        monitor.record_phase_timing("data_processing", duration)
        monitor.set_record_count(75)

        # Simulate report generation
        start_time = time.time()
        time.sleep(0.01)  # Simulate report generation
        duration = time.time() - start_time
        monitor.record_phase_timing("report_generation", duration)

        monitor.end_total_timing()

        # Verify metrics
        assert monitor.metrics.phase_name == "report"
        assert monitor.metrics.record_count == 75
        assert len(monitor.metrics.phase_times) == 3
        assert "template_loading" in monitor.metrics.phase_times
        assert "data_processing" in monitor.metrics.phase_times
        assert "report_generation" in monitor.metrics.phase_times

    def test_memory_tracking_integration(self):
        """Test memory tracking integration."""
        monitor = PerformanceMonitor("memory_test")

        # Simulate memory-intensive operations
        monitor.start_total_timing()

        # Create some data to consume memory
        _ = [i for i in range(10000)]  # Use underscore to indicate intentionally unused
        monitor.set_record_count(1)

        # Simulate processing
        time.sleep(0.01)

        monitor.end_total_timing()

        # Verify memory metrics are tracked
        assert monitor.metrics.peak_memory_mb > 0
        assert monitor.metrics.final_memory_mb > 0

    def test_file_size_tracking_integration(self):
        """Test file size tracking integration."""
        monitor = PerformanceMonitor("file_test")

        # Simulate file operations with size tracking
        monitor.start_total_timing()

        # Simulate input file
        monitor.metrics.input_file_size_mb = 10.5

        # Simulate processing
        monitor.set_record_count(1)
        time.sleep(0.01)

        # Simulate output file
        monitor.metrics.output_file_size_mb = 15.2

        monitor.end_total_timing()

        # Verify file size metrics
        assert monitor.metrics.input_file_size_mb == 10.5
        assert monitor.metrics.output_file_size_mb == 15.2

    def test_performance_summary_output(self, caplog):
        """Test that performance summary can be printed without errors."""
        monitor = PerformanceMonitor("summary_test")

        # Add some data to the monitor
        monitor.start_total_timing()
        monitor.set_record_count(1)
        time.sleep(0.01)
        monitor.end_total_timing()

        # Verify summary can be printed (capture output to avoid cluttering test output)
        with caplog.at_level("INFO"):
            monitor.print_summary()

        # Verify that logger.info was called multiple times (indicating summary was generated)
        log_output = caplog.text
        assert "SUMMARY_TEST PHASE PERFORMANCE SUMMARY" in log_output
        assert "Total Processing Time:" in log_output
        assert "Records Processed:" in log_output

    def test_metrics_serialization(self):
        """Test that metrics can be serialized to dictionary."""
        monitor = PerformanceMonitor("serialization_test")

        # Add some data to the monitor
        monitor.start_total_timing()
        monitor.set_record_count(1)
        time.sleep(0.01)
        monitor.end_total_timing()

        # Convert to dictionary
        metrics_dict = monitor.metrics.to_dict()

        # Verify dictionary structure
        assert isinstance(metrics_dict, dict)
        assert "phase_name" in metrics_dict
        assert "record_count" in metrics_dict
        assert "total_processing_time_seconds" in metrics_dict
        assert "records_per_second" in metrics_dict
        assert "avg_time_per_record_seconds" in metrics_dict
        assert "file_io_time_seconds" in metrics_dict
        assert "processing_time_seconds" in metrics_dict
        assert "parallel_workers" in metrics_dict
        assert "memory_usage_mb" in metrics_dict
        assert "file_sizes_mb" in metrics_dict
        assert "phase_times" in metrics_dict

        # Verify values
        assert metrics_dict["phase_name"] == "serialization_test"
        assert metrics_dict["record_count"] == 1
        assert metrics_dict["parallel_workers"] == 1
