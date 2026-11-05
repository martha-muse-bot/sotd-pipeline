from pathlib import Path

import pytest
import yaml

from sotd.match.base_matcher import BaseMatcher, clear_catalog_cache


def write_temp_yaml(path, data):
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f)


class TestBaseMatcher:
    """Test cases for BaseMatcher structured data handling."""

    @pytest.fixture(autouse=True)
    def _clear_catalog_cache(self):
        clear_catalog_cache()
        yield
        clear_catalog_cache()

    @pytest.fixture
    def temp_catalog(self, tmp_path):
        catalog = {"TestBrand": {"TestModel": {"patterns": ["test"]}}}
        catalog_path = tmp_path / "razors.yaml"
        write_temp_yaml(catalog_path, catalog)
        return catalog_path

    @pytest.fixture
    def temp_tags(self, tmp_path):
        tags = {
            "strip_tags": ["FLIPTOP", "CNC", "STAINLESSLESS", "RAINBOW", "REVENANT", "MACHINEAGE"],
            "preserve_tags": ["MODERNGEM", "KAMISORI"],
        }
        tags_path = tmp_path / "competition_tags.yaml"
        write_temp_yaml(tags_path, tags)
        return tags_path

    def make_matcher(
        self,
        catalog_path,
        tags_path,
        correct_matches_path: Path | None = None,
    ):
        class TempMatcher(BaseMatcher):
            def _load_competition_tags(self):
                return yaml.safe_load(open(tags_path, "r", encoding="utf-8"))

        return TempMatcher(
            catalog_path,
            "razor",
            correct_matches_path=correct_matches_path,
        )

    def test_get_normalized_text_structured(self, temp_catalog, temp_tags):
        matcher = self.make_matcher(temp_catalog, temp_tags)
        value = "Blackbird"
        result = matcher._get_normalized_text(value)
        assert result == "Blackbird"

    def test_get_normalized_text_string_raises_error(self, temp_catalog, temp_tags):
        matcher = self.make_matcher(temp_catalog, temp_tags)
        value = "Blackbird"
        # Should not raise error - just returns the string
        result = matcher._get_normalized_text(value)
        assert result == "Blackbird"

    def test_get_normalized_text_none_raises_error(self, temp_catalog, temp_tags):
        matcher = self.make_matcher(temp_catalog, temp_tags)
        # Should not raise error - just returns None
        result = matcher._get_normalized_text(None)  # type: ignore
        assert result is None

    def test_get_original_text_structured(self, temp_catalog, temp_tags):
        matcher = self.make_matcher(temp_catalog, temp_tags)
        value = "Blackbird $DOORKNOB"
        result = matcher._get_original_text(value)
        assert result == "Blackbird $DOORKNOB"

    def test_get_original_text_string_raises_error(self, temp_catalog, temp_tags):
        matcher = self.make_matcher(temp_catalog, temp_tags)
        value = "Blackbird"
        # Should not raise error - just returns the string
        result = matcher._get_original_text(value)  # type: ignore
        assert result == "Blackbird"

    def test_get_original_text_none_raises_error(self, temp_catalog, temp_tags):
        matcher = self.make_matcher(temp_catalog, temp_tags)
        # Should not raise error - just returns None
        result = matcher._get_original_text(None)  # type: ignore
        assert result is None

    def test_normalize_deprecated_returns_as_is(self, temp_catalog, temp_tags):
        matcher = self.make_matcher(temp_catalog, temp_tags)
        input_text = "Blackbird $DOORKNOB"
        result = matcher.normalize(input_text)
        # normalize method is deprecated and now returns the value as-is
        assert result == input_text

    def test_normalize_deprecated_none_input(self, temp_catalog, temp_tags):
        matcher = self.make_matcher(temp_catalog, temp_tags)
        result = matcher.normalize(None)
        assert result is None

    def test_normalize_deprecated_empty_string(self, temp_catalog, temp_tags):
        matcher = self.make_matcher(temp_catalog, temp_tags)
        result = matcher.normalize("")
        assert result == ""

    def test_check_correct_matches_with_normalized_text(self, temp_catalog, temp_tags):
        matcher = self.make_matcher(temp_catalog, temp_tags)
        # Add a correct match to the matcher
        matcher.correct_matches = {"TestBrand": {"TestModel": ["Blackbird"]}}
        result = matcher._check_correct_matches("Blackbird")
        assert result is not None
        assert result["brand"] == "TestBrand"
        assert result["model"] == "TestModel"

    def test_check_correct_matches_no_match(self, temp_catalog, temp_tags):
        matcher = self.make_matcher(temp_catalog, temp_tags)
        result = matcher._check_correct_matches("UnknownRazor")
        assert result is None

    def test_check_correct_matches_empty_string(self, temp_catalog, temp_tags):
        matcher = self.make_matcher(temp_catalog, temp_tags)
        result = matcher._check_correct_matches("")
        assert result is None

    def test_check_correct_matches_none_input(self, temp_catalog, temp_tags):
        matcher = self.make_matcher(temp_catalog, temp_tags)
        result = matcher._check_correct_matches("")
        assert result is None

    def test_corrupt_correct_matches_file_raises(self, temp_catalog, temp_tags, tmp_path):
        """Malformed correct_matches YAML must fail fast, not silently return {}."""
        cm_dir = tmp_path / "correct_matches"
        cm_dir.mkdir()
        # Tab-indented YAML triggers yaml.scanner.ScannerError
        (cm_dir / "razor.yaml").write_text("Brand:\n\tModel: []\n", encoding="utf-8")

        with pytest.raises(ValueError, match="Failed to load correct matches file"):
            self.make_matcher(temp_catalog, temp_tags, correct_matches_path=cm_dir)

    def test_missing_correct_matches_file_returns_empty(self, temp_catalog, temp_tags, tmp_path):
        """Missing field file is fine — continue with empty correct_matches."""
        cm_dir = tmp_path / "correct_matches"
        cm_dir.mkdir()

        matcher = self.make_matcher(temp_catalog, temp_tags, correct_matches_path=cm_dir)
        assert matcher.correct_matches == {}
