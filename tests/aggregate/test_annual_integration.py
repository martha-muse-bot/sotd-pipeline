"""
Integration tests for annual aggregation components.

Tests the complete annual aggregation workflow including CLI integration,
component interaction, data flow, logging, and error handling.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from sotd.aggregate.annual_engine import (
    AnnualAggregationEngine,
    process_annual,
    process_single_annual,
)
from sotd.aggregate.annual_loader import load_annual_data
from sotd.utils.file_io import save_json_data


class TestAnnualAggregatorIntegration:
    """Test end-to-end annual aggregation workflow."""

    @pytest.fixture
    def temp_data_dir(self):
        """Create temporary data directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / "data" / "aggregated"
            data_dir.mkdir(parents=True)
            yield data_dir

    @pytest.fixture
    def sample_monthly_data(self):
        """Sample monthly aggregated data for testing."""
        return {
            "2024-01": {
                "meta": {
                    "month": "2024-01",
                    "total_shaves": 100,
                    "unique_shavers": 50,
                    "avg_shaves_per_user": 2.0,
                },
                "data": {
                    "razors": [
                        {"name": "Rockwell 6C", "shaves": 20, "unique_users": 15, "position": 1},
                        {"name": "Merkur 34C", "shaves": 15, "unique_users": 12, "position": 2},
                    ],
                    "blades": [
                        {
                            "name": "Astra Superior Platinum",
                            "shaves": 25,
                            "unique_users": 20,
                            "position": 1,
                        },
                        {
                            "name": "Feather Hi-Stainless",
                            "shaves": 20,
                            "unique_users": 18,
                            "position": 2,
                        },
                    ],
                    "brushes": [
                        {
                            "name": "Simpson Chubby 2",
                            "shaves": 10,
                            "unique_users": 8,
                            "position": 1,
                        },
                        {"name": "Omega 10049", "shaves": 8, "unique_users": 6, "position": 2},
                    ],
                    "soaps": [
                        {
                            "name": "Barrister and Mann Seville",
                            "shaves": 12,
                            "unique_users": 10,
                            "position": 1,
                        },
                        {
                            "name": "Stirling Executive Man",
                            "shaves": 10,
                            "unique_users": 8,
                            "position": 2,
                        },
                    ],
                },
            },
            "2024-02": {
                "meta": {
                    "month": "2024-02",
                    "total_shaves": 120,
                    "unique_shavers": 60,
                    "avg_shaves_per_user": 2.0,
                },
                "data": {
                    "razors": [
                        {"name": "Rockwell 6C", "shaves": 25, "unique_users": 20, "position": 1},
                        {"name": "Merkur 34C", "shaves": 18, "unique_users": 15, "position": 2},
                    ],
                    "blades": [
                        {
                            "name": "Astra Superior Platinum",
                            "shaves": 30,
                            "unique_users": 25,
                            "position": 1,
                        },
                        {
                            "name": "Feather Hi-Stainless",
                            "shaves": 22,
                            "unique_users": 20,
                            "position": 2,
                        },
                    ],
                    "brushes": [
                        {
                            "name": "Simpson Chubby 2",
                            "shaves": 12,
                            "unique_users": 10,
                            "position": 1,
                        },
                        {"name": "Omega 10049", "shaves": 10, "unique_users": 8, "position": 2},
                    ],
                    "soaps": [
                        {
                            "name": "Barrister and Mann Seville",
                            "shaves": 15,
                            "unique_users": 12,
                            "position": 1,
                        },
                        {
                            "name": "Stirling Executive Man",
                            "shaves": 12,
                            "unique_users": 10,
                            "position": 2,
                        },
                    ],
                },
            },
        }

    @patch("sotd.aggregate.annual_engine.AnnualAggregationEngine._load_enriched_records")
    def test_end_to_end_annual_aggregation_workflow(
        self, mock_load_enriched, temp_data_dir, sample_monthly_data
    ):
        """Test complete annual aggregation workflow from CLI to output."""
        # Create sample monthly files
        for month, data in sample_monthly_data.items():
            month_file = temp_data_dir / f"{month}.json"
            save_json_data(data, month_file)

        # Mock enriched records - need 110 unique authors total (50 + 60)
        enriched_records = [{"author": f"user_{i}"} for i in range(110)]
        mock_load_enriched.return_value = enriched_records

        # Mock CLI arguments
        args = Mock()
        args.year = "2024"
        args.force = True
        args.verbose = False
        args.data_dir = temp_data_dir

        # Run annual aggregation
        with patch("sotd.aggregate.annual_engine.save_annual_data") as mock_save:
            # Pass the parent directory since process_annual expects data_dir/aggregated
            process_annual("2024", temp_data_dir.parent, debug=False, force=True)

            # Verify save was called with correct data
            mock_save.assert_called_once()
            call_args = mock_save.call_args
            assert call_args[0][0] is not None  # aggregated_data
            assert call_args[0][1] == "2024"  # year

            saved_data = call_args[0][0]  # aggregated_data
            assert "metadata" in saved_data
            assert "razors" in saved_data
            assert "blades" in saved_data
            assert "brushes" in saved_data
            assert "soaps" in saved_data

            # Verify metadata
            metadata = saved_data["metadata"]
            assert metadata["year"] == "2024"
            assert metadata["total_shaves"] == 220  # 100 + 120
            assert metadata["unique_shavers"] == 110  # 50 + 60
            assert "2024-01" in metadata["included_months"]
            assert "2024-02" in metadata["included_months"]
            assert len(metadata["missing_months"]) == 10  # 12 - 2

    @patch("sotd.aggregate.annual_engine.AnnualAggregationEngine._load_enriched_records")
    def test_cli_integration_with_missing_months(
        self, mock_load_enriched, temp_data_dir, sample_monthly_data
    ):
        """Test CLI integration when some months are missing."""
        # Create only one month of data
        month_file = temp_data_dir / "2024-01.json"
        save_json_data(sample_monthly_data["2024-01"], month_file)

        # Mock enriched records - need 50 unique authors
        enriched_records = [{"author": f"user_{i}"} for i in range(50)]
        mock_load_enriched.return_value = enriched_records

        with patch("sotd.aggregate.annual_engine.save_annual_data") as mock_save:
            # Pass the parent directory since process_annual expects data_dir/aggregated
            process_annual("2024", temp_data_dir.parent, debug=False, force=True)

            mock_save.assert_called_once()

            saved_data = mock_save.call_args[0][0]  # aggregated_data
            metadata = saved_data["metadata"]
            assert metadata["year"] == "2024"
            assert metadata["total_shaves"] == 100
            assert metadata["unique_shavers"] == 50
            assert "2024-01" in metadata["included_months"]
            assert len(metadata["missing_months"]) == 11  # 12 - 1

    def test_cli_integration_with_no_data(self, temp_data_dir):
        """Test CLI integration when no monthly data exists.

        A year with no loadable months writes no annual file: an empty
        year is not an aggregation, and the file would be mistaken for a
        complete year by skip-if-exists on later runs.
        """
        with patch("sotd.aggregate.annual_engine.save_annual_data") as mock_save:
            result = process_annual("2024", temp_data_dir, debug=False, force=True)

            mock_save.assert_not_called()
            assert result is False

    def test_second_run_without_force_does_not_overwrite(
        self, temp_data_dir, sample_monthly_data
    ):
        """Second process_annual with force=False leaves the existing file alone."""
        for month, data in sample_monthly_data.items():
            month_file = temp_data_dir / f"{month}.json"
            save_json_data(data, month_file)

        annual_file = temp_data_dir / "annual" / "2024.json"

        # First run writes the annual file.
        assert process_annual("2024", temp_data_dir.parent, debug=False, force=True) is True
        assert annual_file.exists()

        # Sentinel-modify it, then re-run without force.
        saved = json.loads(annual_file.read_text())
        saved["_sentinel"] = "do-not-overwrite"
        annual_file.write_text(json.dumps(saved))

        assert process_annual("2024", temp_data_dir.parent, debug=False, force=False) is False
        assert json.loads(annual_file.read_text()).get("_sentinel") == "do-not-overwrite"

        # ...while force=True still regenerates it.
        assert process_annual("2024", temp_data_dir.parent, debug=False, force=True) is True
        assert "_sentinel" not in json.loads(annual_file.read_text())

    def test_empty_year_writes_no_file(self, temp_data_dir):
        """process_annual on a year with no monthly files writes no annual file."""
        annual_file = temp_data_dir / "annual" / "2025.json"

        assert process_annual("2025", temp_data_dir.parent, debug=False, force=True) is False
        assert not annual_file.exists()

    def test_process_single_annual_returns_none_when_skipped(self, temp_data_dir):
        """Skipped years report None (not 'completed') to the parallel path."""
        assert (
            process_single_annual("2025", temp_data_dir.parent, debug=False, force=True)
            is None
        )

    def test_component_interaction_and_data_flow(self, temp_data_dir, sample_monthly_data):
        """Test interaction between loader, engine, and saver components."""
        # Create sample monthly files
        for month, data in sample_monthly_data.items():
            month_file = temp_data_dir / f"{month}.json"
            save_json_data(data, month_file)

        # Test loader component
        loaded_data = load_annual_data("2024", temp_data_dir)

        assert "2024-01" in loaded_data["monthly_data"]
        assert "2024-02" in loaded_data["monthly_data"]
        assert len(loaded_data["missing_months"]) == 10
        assert len(loaded_data["validation_errors"]) == 0

        # Test engine component
        engine = AnnualAggregationEngine("2024", temp_data_dir)
        annual_data = engine.aggregate_all_categories(
            loaded_data["monthly_data"],
            loaded_data["included_months"],
            loaded_data["missing_months"],
        )

        assert "metadata" in annual_data
        assert "razors" in annual_data
        assert "blades" in annual_data
        assert "brushes" in annual_data
        assert "soaps" in annual_data

        # Verify aggregated data
        razors = annual_data["razors"]
        assert len(razors) == 2
        rockwell_6c = next(r for r in razors if "Rockwell 6C" in r["name"])
        assert rockwell_6c["shaves"] == 45  # 20 + 25

    def test_logging_and_progress_reporting(self, temp_data_dir, sample_monthly_data, caplog):
        """Test logging and progress reporting during annual aggregation."""
        # Create sample monthly files
        for month, data in sample_monthly_data.items():
            month_file = temp_data_dir / f"{month}.json"
            save_json_data(data, month_file)

        with patch("sotd.aggregate.annual_engine.save_annual_data"):
            with caplog.at_level("DEBUG"):
                # Pass the parent directory since process_annual expects data_dir/aggregated
                process_annual("2024", temp_data_dir.parent, debug=True, force=True)

            # Verify debug output contains expected messages in logs
            log_output = caplog.text
            assert "Processing annual aggregation for 2024" in log_output
            assert "Loaded 2 months of data" in log_output
            assert "Annual aggregation for 2024 completed" in log_output

    def test_error_handling_across_components(
        self, temp_data_dir, sample_monthly_data
    ):
        """Test error handling across all components."""
        # Create corrupted monthly file
        corrupted_file = temp_data_dir / "2024-01.json"
        corrupted_file.write_text("invalid json content")

        # ...plus one valid month, so the year is not empty and the
        # aggregation proceeds with the corrupted month listed missing.
        month_file = temp_data_dir / "2024-02.json"
        save_json_data(sample_monthly_data["2024-02"], month_file)

        with patch("sotd.aggregate.annual_engine.save_annual_data") as mock_save:
            # Should handle JSONDecodeError gracefully
            # Pass the parent directory since process_annual expects data_dir/aggregated
            process_annual("2024", temp_data_dir.parent, debug=False, force=True)

            # Should still save data with missing month
            mock_save.assert_called_once()
            saved_data = mock_save.call_args[0][0]  # aggregated_data
            metadata = saved_data["metadata"]
            assert "2024-01" in metadata["missing_months"]
            assert "2024-02" in metadata["included_months"]

    def test_performance_of_complete_workflow(self, temp_data_dir):
        """Test performance of complete annual aggregation workflow."""
        # Create large dataset (12 months with substantial data)
        large_monthly_data = {}
        for month_num in range(1, 13):
            month = f"2024-{month_num:02d}"
            large_monthly_data[month] = {
                "meta": {
                    "month": month,
                    "total_shaves": 1000,
                    "unique_shavers": 500,
                    "avg_shaves_per_user": 2.0,
                },
                "data": {
                    "razors": [
                        {
                            "name": f"Brand{i} Model{i}",
                            "shaves": 50,
                            "unique_users": 40,
                            "position": i,
                        }
                        for i in range(1, 21)  # 20 razors per month
                    ],
                    "blades": [
                        {
                            "name": f"BladeBrand{i} BladeModel{i}",
                            "shaves": 60,
                            "unique_users": 50,
                            "position": i,
                        }
                        for i in range(1, 31)  # 30 blades per month
                    ],
                    "brushes": [
                        {
                            "name": f"BrushBrand{i} BrushModel{i}",
                            "shaves": 40,
                            "unique_users": 35,
                            "position": i,
                        }
                        for i in range(1, 16)  # 15 brushes per month
                    ],
                    "soaps": [
                        {
                            "name": f"SoapBrand{i} SoapModel{i}",
                            "shaves": 45,
                            "unique_users": 40,
                            "position": i,
                        }
                        for i in range(1, 26)  # 25 soaps per month
                    ],
                },
            }

        # Create all monthly files
        for month, data in large_monthly_data.items():
            month_file = temp_data_dir / f"{month}.json"
            save_json_data(data, month_file)

        # Mock enriched records - need 6000 unique authors total (12 * 500)
        enriched_records = [{"author": f"user_{i}"} for i in range(6000)]

        with (
            patch("sotd.aggregate.annual_engine.save_annual_data") as mock_save,
            patch(
                "sotd.aggregate.annual_engine.AnnualAggregationEngine._load_enriched_records",
                return_value=enriched_records,
            ),
        ):
            import time

            start_time = time.time()

            # Pass the parent directory since process_annual expects data_dir/aggregated
            process_annual("2024", temp_data_dir.parent, debug=False, force=True)

            end_time = time.time()
            execution_time = end_time - start_time

            mock_save.assert_called_once()

            # Verify performance (should complete within reasonable time)
            assert execution_time < 10.0  # Should complete within 10 seconds

            # Verify data integrity
            saved_data = mock_save.call_args[0][0]  # aggregated_data
            metadata = saved_data["metadata"]
            assert metadata["year"] == "2024"
            assert metadata["total_shaves"] == 12000  # 12 * 1000
            assert metadata["unique_shavers"] == 6000  # 12 * 500
            assert len(metadata["included_months"]) == 12
            assert len(metadata["missing_months"]) == 0

    def test_integration_with_existing_aggregate_module(self, temp_data_dir, sample_monthly_data):
        """Test integration with existing aggregate module patterns."""
        # Create sample monthly files
        for month, data in sample_monthly_data.items():
            month_file = temp_data_dir / f"{month}.json"
            save_json_data(data, month_file)

        with patch("sotd.aggregate.annual_engine.save_annual_data") as mock_save:
            # Test that annual aggregation follows same patterns as monthly
            # Pass the parent directory since process_annual expects data_dir/aggregated
            process_annual("2024", temp_data_dir.parent, debug=False, force=True)

            mock_save.assert_called_once()

            # Verify data structure matches existing patterns
            saved_data = mock_save.call_args[0][0]  # aggregated_data

            # Check that product data follows existing aggregation patterns
            for product_type in ["razors", "blades", "brushes", "soaps"]:
                assert product_type in saved_data
                assert isinstance(saved_data[product_type], list)
                # Each product should have name, shaves, unique_users, rank
                # (annual rows rank with `rank`, not the monthly `position`)
                if saved_data[product_type]:
                    product = saved_data[product_type][0]
                    assert "name" in product
                    assert "shaves" in product
                    assert "unique_users" in product
                    assert "rank" in product

    def test_cli_error_flow_handling(self, temp_data_dir):
        """Test CLI error flow handling for various error scenarios."""
        # Test with invalid year format
        with pytest.raises(ValueError, match="Year must be numeric"):
            AnnualAggregationEngine("invalid", temp_data_dir)

        # Test with non-existent data directory
        non_existent_dir = temp_data_dir / "nonexistent"

        with patch("sotd.aggregate.annual_engine.save_annual_data") as mock_save:
            result = process_annual("2024", non_existent_dir, debug=False, force=True)

            # No monthly data exists, so no annual file is written.
            mock_save.assert_not_called()
            assert result is False

    def test_comprehensive_range_functionality_validation(self, temp_data_dir, sample_monthly_data):
        """Test comprehensive validation of annual aggregation functionality."""
        # Create sample monthly files
        for month, data in sample_monthly_data.items():
            month_file = temp_data_dir / f"{month}.json"
            save_json_data(data, month_file)

        with patch("sotd.aggregate.annual_engine.save_annual_data") as mock_save:
            # Pass the parent directory since process_annual expects data_dir/aggregated
            process_annual("2024", temp_data_dir.parent, debug=False, force=True)

            mock_save.assert_called_once()

            saved_data = mock_save.call_args[0][0]  # aggregated_data

            # Comprehensive validation of output structure
            required_keys = ["metadata", "razors", "blades", "brushes", "soaps"]
            for key in required_keys:
                assert key in saved_data

            # Validate metadata structure
            metadata = saved_data["metadata"]
            assert "year" in metadata
            assert "total_shaves" in metadata
            assert "unique_shavers" in metadata
            assert "included_months" in metadata
            assert "missing_months" in metadata

            # Validate product data structure
            for product_type in ["razors", "blades", "brushes", "soaps"]:
                products = saved_data[product_type]
                assert isinstance(products, list)
                # Products should be sorted by shaves desc, unique_users desc
                if len(products) > 1:
                    assert products[0]["shaves"] >= products[1]["shaves"]
                    if products[0]["shaves"] == products[1]["shaves"]:
                        assert products[0]["unique_users"] >= products[1]["unique_users"]
