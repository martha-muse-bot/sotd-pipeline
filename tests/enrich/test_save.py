"""Tests for the enrich save module."""

import json
import tempfile
from pathlib import Path

import pytest

from sotd.enrich.save import (
    calculate_enrichment_stats,
    load_matched_data,
    save_enriched_data,
)


class TestLoadMatchedData:
    """Test the load_matched_data function."""

    def test_load_valid_matched_data(self):
        """Test loading valid matched data."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            test_data = {
                "meta": {
                    "month": "2025-01",
                    "extracted_at": "2025-01-21T18:40:00Z",
                    "comment_count": 100,
                },
                "data": [
                    {"id": "1", "author": "user1", "body": "test"},
                    {"id": "2", "author": "user2", "body": "test2"},
                ],
            }
            json.dump(test_data, f, ensure_ascii=False)

        try:
            result = load_matched_data(Path(f.name))
            assert result is not None
            metadata, data = result
            assert metadata["month"] == "2025-01"
            assert metadata["extracted_at"] == "2025-01-21T18:40:00Z"
            assert len(data) == 2
            assert data[0]["id"] == "1"
            assert data[1]["id"] == "2"
        finally:
            Path(f.name).unlink()

    def test_load_nonexistent_file(self):
        """Test loading a file that doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Matched data file not found"):
            load_matched_data(Path("/nonexistent/file.json"))

    def test_load_invalid_json(self):
        """Test loading invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content")

        try:
            with pytest.raises(ValueError, match="Invalid JSON in matched data file"):
                load_matched_data(Path(f.name))
        finally:
            Path(f.name).unlink()

    def test_load_missing_data_section(self):
        """Test loading file missing data section."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            test_data = {"meta": {"month": "2025-01"}}
            json.dump(test_data, f, ensure_ascii=False)

        try:
            with pytest.raises(ValueError, match="Missing 'data' section"):
                load_matched_data(Path(f.name))
        finally:
            Path(f.name).unlink()

    def test_load_invalid_data_type(self):
        """Test loading file with invalid data type."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            test_data = {"meta": {"month": "2025-01"}, "data": "not a list"}
            json.dump(test_data, f, ensure_ascii=False)

        try:
            with pytest.raises(ValueError, match="Expected list for 'data'"):
                load_matched_data(Path(f.name))
        finally:
            Path(f.name).unlink()


class TestSaveEnrichedData:
    """Test the save_enriched_data function."""

    def test_save_enriched_data_preserves_extracted_at(self):
        """Test that save_enriched_data preserves the extracted_at field."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "enriched" / "2025-01.json"

            # Sample enriched data
            enriched_data = [
                {
                    "id": "1",
                    "author": "user1",
                    "body": "test",
                    "enriched": {"razor": {"_enriched_by": "RazorEnricher"}},
                }
            ]

            # Original metadata with extracted_at
            original_metadata = {
                "month": "2025-01",
                "extracted_at": "2025-01-21T18:40:00Z",
                "comment_count": 100,
            }

            enrichment_stats = {
                "blade_enriched": 0,
                "razor_enriched": 1,
                "brush_enriched": 0,
                "soap_enriched": 0,
                "total_enriched": 1,
            }

            # Save enriched data
            save_enriched_data(output_path, enriched_data, original_metadata, enrichment_stats)

            # Verify file was created
            assert output_path.exists()

            # Load and verify the saved data
            with output_path.open("r") as f:
                saved_data = json.load(f)

            # Check metadata structure
            assert "meta" in saved_data
            assert "data" in saved_data

            metadata = saved_data["meta"]
            assert metadata["month"] == "2025-01"
            assert metadata["extracted_at"] == "2025-01-21T18:40:00Z"  # Preserved!
            assert "enriched_at" in metadata  # New field added
            assert metadata["records_input"] == 1
            assert metadata["record_count"] == 1
            assert metadata["razor_enriched"] == 1
            assert metadata["total_enriched"] == 1

            # Check data structure
            assert len(saved_data["data"]) == 1
            assert saved_data["data"][0]["id"] == "1"

    def test_save_enriched_data_missing_extracted_at(self):
        """Test that save_enriched_data handles missing extracted_at gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "enriched" / "2025-01.json"

            enriched_data = [
                {
                    "id": "1",
                    "author": "user1",
                    "body": "test",
                }
            ]

            # Original metadata without extracted_at
            original_metadata = {
                "month": "2025-01",
                "comment_count": 100,
            }

            enrichment_stats = {
                "blade_enriched": 0,
                "razor_enriched": 0,
                "brush_enriched": 0,
                "soap_enriched": 0,
                "total_enriched": 0,
            }

            # Save enriched data
            save_enriched_data(output_path, enriched_data, original_metadata, enrichment_stats)

            # Load and verify
            with output_path.open("r") as f:
                saved_data = json.load(f)

            metadata = saved_data["meta"]
            assert metadata["month"] == "2025-01"
            assert metadata["extracted_at"] == ""  # Empty string when missing
            assert "enriched_at" in metadata

    def test_save_enriched_data_force_overwrite(self):
        """Test that save_enriched_data can force overwrite existing files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "enriched" / "2025-01.json"

            # Create initial file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("w") as f:
                json.dump({"old": "data"}, f, ensure_ascii=False)

            assert output_path.exists()

            # Save with force=True
            enriched_data = [{"id": "1", "author": "user1", "body": "test"}]
            original_metadata = {
                "month": "2025-01",
                "extracted_at": "2025-01-21T18:40:00Z",
            }
            enrichment_stats = {
                "blade_enriched": 0,
                "razor_enriched": 0,
                "brush_enriched": 0,
                "soap_enriched": 0,
                "total_enriched": 0,
            }

            save_enriched_data(
                output_path, enriched_data, original_metadata, enrichment_stats, force=True
            )

            # Verify file was overwritten
            with output_path.open("r") as f:
                saved_data = json.load(f)

            assert "meta" in saved_data
            assert "data" in saved_data
            assert saved_data["meta"]["month"] == "2025-01"

    def test_save_enriched_data_creates_directory(self):
        """Test that save_enriched_data creates the output directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "nonexistent" / "subdir" / "2025-01.json"

            enriched_data = [{"id": "1", "author": "user1", "body": "test"}]
            original_metadata = {
                "month": "2025-01",
                "extracted_at": "2025-01-21T18:40:00Z",
            }
            enrichment_stats = {
                "blade_enriched": 0,
                "razor_enriched": 0,
                "brush_enriched": 0,
                "soap_enriched": 0,
                "total_enriched": 0,
            }

            # This should create the directory structure
            save_enriched_data(output_path, enriched_data, original_metadata, enrichment_stats)

            assert output_path.exists()
            assert output_path.parent.exists()


class TestCalculateEnrichmentStats:
    """Test the calculate_enrichment_stats function."""

    def test_calculate_enrichment_stats_empty_data(self):
        """Test calculating stats for empty data."""
        stats = calculate_enrichment_stats([])
        assert stats["blade_enriched"] == 0
        assert stats["razor_enriched"] == 0
        assert stats["brush_enriched"] == 0
        assert stats["soap_enriched"] == 0
        assert stats["total_enriched"] == 0

    def test_calculate_enrichment_stats_no_enriched_data(self):
        """Test calculating stats for data without enriched fields."""
        data = [
            {"id": "1", "author": "user1", "body": "test"},
            {"id": "2", "author": "user2", "body": "test2"},
        ]
        stats = calculate_enrichment_stats(data)
        assert stats["blade_enriched"] == 0
        assert stats["razor_enriched"] == 0
        assert stats["brush_enriched"] == 0
        assert stats["soap_enriched"] == 0
        assert stats["total_enriched"] == 0

    def test_calculate_enrichment_stats_with_enriched_data(self):
        """Test calculating stats for data with enriched fields."""
        data = [
            {
                "id": "1",
                "author": "user1",
                "body": "test",
                "razor": {"enriched": {"_enriched_by": "RazorEnricher"}},
                "blade": {"enriched": {"_enriched_by": "BladeEnricher"}},
            },
            {
                "id": "2",
                "author": "user2",
                "body": "test2",
                "brush": {"enriched": {"_enriched_by": "BrushEnricher"}},
                "soap": {"enriched": {"_enriched_by": "SoapEnricher"}},
            },
            {
                "id": "3",
                "author": "user3",
                "body": "test3",
                "razor": {"enriched": {"_enriched_by": "RazorEnricher"}},
                "soap": {"enriched": {"_enriched_by": "SoapEnricher"}},
            },
        ]
        stats = calculate_enrichment_stats(data)
        assert stats["blade_enriched"] == 1
        assert stats["razor_enriched"] == 2
        assert stats["brush_enriched"] == 1
        assert stats["soap_enriched"] == 2
        assert stats["total_enriched"] == 3

    def test_calculate_enrichment_stats_mixed_data(self):
        """Test calculating stats for mixed data (some enriched, some not)."""
        data = [
            {
                "id": "1",
                "author": "user1",
                "body": "test",
                "razor": {"enriched": {"_enriched_by": "RazorEnricher"}},
            },
            {"id": "2", "author": "user2", "body": "test2"},  # No enriched data
            {
                "id": "3",
                "author": "user3",
                "body": "test3",
                "blade": {"enriched": {"_enriched_by": "BladeEnricher"}},
            },
        ]
        stats = calculate_enrichment_stats(data)
        assert stats["blade_enriched"] == 1
        assert stats["razor_enriched"] == 1
        assert stats["brush_enriched"] == 0
        assert stats["soap_enriched"] == 0
        assert stats["total_enriched"] == 2
