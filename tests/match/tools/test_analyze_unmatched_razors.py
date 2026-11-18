"""Tests for analyze unmatched razors functionality."""

import json

from sotd.match.tools.analyzers.unmatched_analyzer import UnmatchedAnalyzer


def test_analyze_unmatched_razors_outputs_expected_counts(tmp_path):
    """Test that the unmatched analyzer correctly identifies unmatched razors across multiple months."""
    out_dir = tmp_path / "data" / "matched"
    out_dir.mkdir(parents=True)

    file1 = out_dir / "2025-04.json"
    file2 = out_dir / "2025-05.json"

    data1 = {
        "data": [
            {"razor": "Fancy Razor"},
            {"razor": {"original": "Another Razor", "matched": None}},
            {"razor": {"original": "Fancy Razor"}},
        ]
    }

    data2 = {
        "data": [
            {"razor": "Fancy Razor"},
            {"razor": {"original": "Another Razor"}},
            {"razor": {"original": "New Razor"}},
        ]
    }

    file1.write_text(json.dumps(data1))
    file2.write_text(json.dumps(data2))

    # Create analyzer and test with the data
    analyzer = UnmatchedAnalyzer()

    # Create mock args with range
    class MockArgs:
        def __init__(self):
            self.range = "2025-04:2025-05"
            self.out_dir = str(tmp_path / "data")
            self.field = "razor"
            self.month = None  # Don't set month when using range
            self.year = None  # Don't set year when using range
            self.delta_months = None  # Don't set delta_months when using range
            self.start = None  # Don't set start when using range
            self.end = None  # Don't set end when using range
            self.limit = 10
            self.debug = True  # Enable debug to see what's happening

    args = MockArgs()

    # Run the analysis
    results = analyzer.analyze_unmatched(args)

    # Debug output
    print(f"Results: {results}")

    # Verify results - should include items from both months
    assert "Fancy Razor" in results
    assert "Another Razor" in results

    # Check that we have the expected number of unmatched items
    # Fancy Razor appears in both months, Another Razor in first month, New Razor in second month
    assert len(results) >= 2  # At least 2 unique unmatched items
