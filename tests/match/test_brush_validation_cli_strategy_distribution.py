from pathlib import Path
from unittest.mock import patch

from sotd.match.brush.validation.cli import BrushValidationCLI


class TestBrushValidationCLIStrategyDistribution:
    """Test strategy distribution statistics to expose the counting bug."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cli = BrushValidationCLI(data_path=Path("data"))
        self.test_month = "2025-06"

    def test_strategy_distribution_counts_individual_records_instead_of_unique_strings(self):
        """Test that exposes the bug: strategy distribution counts individual records, not unique strings."""
        # Mock data that simulates the real scenario:
        # - Multiple records with the same brush string
        # - Some with correct_complete_brush strategy
        # - Different all_strategies lengths
        mock_data = {
            "data": [
                # Record 1: "Declaration B2" with correct_complete_brush (should be counted as validated)
                {
                    "brush": {
                        "normalized": "declaration b2",
                        "matched": {
                            "strategy": "correct_complete_brush",
                            "score": 100,
                        },
                        "all_strategies": [{"strategy": "correct_complete_brush", "score": 100}],
                    }
                },
                # Record 2: Same "Declaration B2" but different comment (duplicate brush string)
                {
                    "brush": {
                        "normalized": "declaration b2",
                        "matched": {
                            "strategy": "correct_complete_brush",
                            "score": 100,
                        },
                        "all_strategies": [{"strategy": "correct_complete_brush", "score": 100}],
                    }
                },
                # Record 3: "Zenith B2" with single strategy (should count as unvalidated)
                {
                    "brush": {
                        "normalized": "zenith b2",
                        "matched": {
                            "strategy": "automated_split",
                            "score": 85,
                        },
                        "all_strategies": [{"strategy": "automated_split", "score": 85}],
                    }
                },
                # Record 4: "Simpson Chubby" with multiple strategies (should count as unvalidated)
                {
                    "brush": {
                        "normalized": "simpson chubby",
                        "matched": {
                            "strategy": "automated_split",
                            "score": 80,
                        },
                        "all_strategies": [
                            {"strategy": "automated_split", "score": 80},
                            {"strategy": "known_brush", "score": 75},
                        ],
                    }
                },
                # Record 5: "Unknown Brush" with no strategies (should count as missing)
                {
                    "brush": {
                        "normalized": "unknown brush",
                        "matched": None,
                        "all_strategies": None,
                    }
                },
            ]
        }

        with patch.object(self.cli.counting_service, "_load_matched_data", return_value=mock_data):
            stats = self.cli.get_all_entries_strategy_distribution_statistics(self.test_month)

        # ✅ FIXED: Now correctly counts unique brush strings (4) instead of individual records (5)
        assert stats["total_brush_records"] == 4  # Correct: counts unique brush strings

        # ✅ FIXED: Now correctly counts unique correct match strings (1) instead of individual records (2)
        assert stats["correct_matches_count"] == 1  # Correct: counts unique correct match strings

        # ✅ FIXED: remaining_entries calculation is now correct
        assert stats["remaining_entries"] == 3  # Correct: 4 - 1 = 3

        # ✅ FIXED: all_strategies_lengths now counts unique strings, not individual records
        assert stats["all_strategies_lengths"]["1"] == 2  # Correct: 2 unique strings with length 1

        assert stats["all_strategies_lengths"]["2"] == 1  # Current: 1 multiple strategy (CORRECT)
        assert stats["all_strategies_lengths"]["None"] == 1  # Current: 1 missing (CORRECT)

    def test_strategy_distribution_should_match_validation_statistics_logic(self):
        """Test that strategy distribution should use the same unique string counting logic as validation statistics."""
        # Mock the same data as above
        mock_data = {
            "data": [
                # Two records with same brush string
                {
                    "brush": {
                        "normalized": "declaration b2",
                        "strategy": "correct_complete_brush",
                        "all_strategies": [{"strategy": "correct_complete_brush", "score": 100}],
                    }
                },
                {
                    "brush": {
                        "normalized": "declaration b2",  # Same normalized text
                        "strategy": "correct_complete_brush",
                        "all_strategies": [{"strategy": "correct_complete_brush", "score": 100}],
                    }
                },
                # One unique unvalidated entry
                {
                    "brush": {
                        "normalized": "zenith b2",
                        "strategy": "automated_split",
                        "all_strategies": [{"strategy": "automated_split", "score": 85}],
                    }
                },
            ]
        }

        with patch.object(self.cli.counting_service, "_load_matched_data", return_value=mock_data):
            # Get both types of statistics
            strategy_stats = self.cli.get_strategy_distribution_statistics(self.test_month)

            # Mock user actions manager to get validation statistics
            with patch.object(self.cli, "user_actions_manager") as mock_manager:
                mock_manager.get_statistics.return_value = {
                    "validated_count": 0,
                    "overridden_count": 0,
                }
                validation_stats = self.cli.get_validation_statistics_no_matcher(self.test_month)

        # ✅ FIXED: Strategy distribution now correctly counts unique strings
        assert strategy_stats["total_brush_records"] == 2  # Correct: counts unique brush strings

        # Validation statistics correctly count unique strings
        assert validation_stats["total_entries"] == 2  # Correct: counts unique brush strings

        # ✅ FIXED: The counts now match because both use the same unique string counting logic
        assert strategy_stats["total_brush_records"] == validation_stats["total_entries"]

    def test_strategy_distribution_should_use_unique_string_counting(self):
        """Test that strategy distribution should count unique brush strings, not individual records."""
        # Create test data with multiple records for the same brush strings
        mock_data = {
            "data": [
                # Multiple records for "Declaration B2" (should count as 1 unique)
                {
                    "brush": {
                        "normalized": "declaration b2",
                        "matched": {
                            "strategy": "correct_complete_brush",
                        },
                        "all_strategies": [{"strategy": "correct_complete_brush"}],
                    }
                },
                {
                    "brush": {
                        "normalized": "declaration b2",
                        "matched": {
                            "strategy": "correct_complete_brush",
                        },
                        "all_strategies": [{"strategy": "correct_complete_brush"}],
                    }
                },
                {
                    "brush": {
                        "normalized": "declaration b2",
                        "matched": {
                            "strategy": "correct_complete_brush",
                        },
                        "all_strategies": [{"strategy": "correct_complete_brush"}],
                    }
                },
                # Multiple records for "Zenith B2" (should count as 1 unique)
                {
                    "brush": {
                        "normalized": "zenith b2",
                        "matched": {
                            "strategy": "automated_split",
                        },
                        "all_strategies": [{"strategy": "automated_split"}],
                    }
                },
                {
                    "brush": {
                        "normalized": "zenith b2",
                        "matched": {
                            "strategy": "automated_split",
                        },
                        "all_strategies": [{"strategy": "automated_split"}],
                    }
                },
                # One record for "Simpson Chubby" (should count as 1 unique)
                {
                    "brush": {
                        "normalized": "simpson chubby",
                        "matched": {
                            "strategy": "automated_split",
                        },
                        "all_strategies": [
                            {"strategy": "automated_split"},
                            {"strategy": "known_brush"},
                        ],
                    }
                },
            ]
        }

        with patch.object(self.cli.counting_service, "_load_matched_data", return_value=mock_data):
            stats = self.cli.get_all_entries_strategy_distribution_statistics(self.test_month)

        # ✅ FIXED: Now correctly counts unique brush strings (3) instead of individual records (6)
        assert stats["total_brush_records"] == 3  # Correct: counts unique brush strings

        # ✅ FIXED: Now correctly counts unique correct match strings (1) instead of individual records (3)
        assert stats["correct_matches_count"] == 1  # Correct: counts unique correct match strings

        # ✅ FIXED: all_strategies_lengths now counts unique strings, not individual records
        assert stats["all_strategies_lengths"]["1"] == 2  # Correct: 2 unique strings with length 1

        assert stats["all_strategies_lengths"]["2"] == 1  # Current: 1 simpson chubby (CORRECT)
