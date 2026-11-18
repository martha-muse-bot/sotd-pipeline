import pytest

from sotd.match.types import MatchResult


def match_result_to_dict(match_result: MatchResult) -> dict:
    """Convert MatchResult to dict for backward compatibility in tests."""
    return {
        "original": match_result.original,
        "matched": match_result.matched,
        "match_type": match_result.match_type,
        "pattern": match_result.pattern,
    }


@pytest.fixture
def convert_match_result():
    """Fixture to convert MatchResult to dict for backward compatibility."""
    return match_result_to_dict
