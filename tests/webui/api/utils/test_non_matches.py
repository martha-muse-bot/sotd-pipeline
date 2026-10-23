"""Tests for non-matches utility module."""

import os

import yaml

from webui.api.utils.non_matches import (
    get_non_matches_dir,
    load_non_matches,
    save_brand_non_match,
    save_cross_brand_scent_non_match,
    save_scent_non_match,
)


class TestGetNonMatchesDir:
    """Test get_non_matches_dir function."""

    def test_default_directory(self):
        """Test that default directory is data/overrides/."""
        result = get_non_matches_dir()
        assert result.name == "overrides"
        assert result.parent.name == "data"

    def test_sotd_data_dir_support(self, tmp_path):
        """Test that SOTD_DATA_DIR environment variable is respected."""
        os.environ["SOTD_DATA_DIR"] = str(tmp_path)
        try:
            result = get_non_matches_dir()
            assert result == tmp_path / "overrides"
        finally:
            os.environ.pop("SOTD_DATA_DIR", None)


class TestLoadNonMatches:
    """Test load_non_matches function."""

    def test_load_all_files(self, tmp_path):
        """Test loading all three non-match files."""
        os.environ["SOTD_DATA_DIR"] = str(tmp_path)
        try:
            overrides_dir = tmp_path / "overrides"
            overrides_dir.mkdir(parents=True)

            # Create test files
            brands_file = overrides_dir / "non_matches_brands.yaml"
            with brands_file.open("w") as f:
                yaml.dump({"Brand A": ["Brand B", "Brand C"]}, f)

            scents_file = overrides_dir / "non_matches_scents.yaml"
            with scents_file.open("w") as f:
                yaml.dump({"Brand A": {"Scent 1": ["Scent 2"]}}, f)

            cross_brand_file = overrides_dir / "non_matches_scents_cross_brand.yaml"
            with cross_brand_file.open("w") as f:
                yaml.dump({"Lavender": [{"brand": "Brand A", "scent": "Lavender"}]}, f)

            result = load_non_matches()

            assert "brand_non_matches" in result
            assert "scent_non_matches" in result
            assert "scent_cross_brand_non_matches" in result
            assert result["brand_non_matches"]["Brand A"] == ["Brand B", "Brand C"]
            assert result["scent_non_matches"]["Brand A"]["Scent 1"] == ["Scent 2"]
            assert len(result["scent_cross_brand_non_matches"]["Lavender"]) == 1
        finally:
            os.environ.pop("SOTD_DATA_DIR", None)

    def test_load_missing_files(self, tmp_path):
        """Test graceful handling of missing files."""
        os.environ["SOTD_DATA_DIR"] = str(tmp_path)
        try:
            overrides_dir = tmp_path / "overrides"
            overrides_dir.mkdir(parents=True)

            result = load_non_matches()

            assert "brand_non_matches" in result
            assert "scent_non_matches" in result
            assert "scent_cross_brand_non_matches" in result
            assert result["brand_non_matches"] == {}
            assert result["scent_non_matches"] == {}
            assert result["scent_cross_brand_non_matches"] == {}
        finally:
            os.environ.pop("SOTD_DATA_DIR", None)


class TestSaveBrandNonMatch:
    """Test save_brand_non_match function."""

    def test_save_new_brand_non_match(self, tmp_path):
        """Test saving a new brand non-match."""
        os.environ["SOTD_DATA_DIR"] = str(tmp_path)
        try:
            overrides_dir = tmp_path / "overrides"
            overrides_dir.mkdir(parents=True)

            result = save_brand_non_match("Brand A", "Brand B")

            assert result["success"] is True
            assert "success" in result["message"].lower()

            # Verify file was created and contains the non-match
            brands_file = overrides_dir / "non_matches_brands.yaml"
            assert brands_file.exists()

            with brands_file.open("r") as f:
                data = yaml.safe_load(f)
                assert "Brand A" in data
                assert "Brand B" in data["Brand A"]
        finally:
            os.environ.pop("SOTD_DATA_DIR", None)

    def test_save_duplicate_brand_non_match(self, tmp_path):
        """Test that duplicate brand non-matches are not saved twice."""
        os.environ["SOTD_DATA_DIR"] = str(tmp_path)
        try:
            overrides_dir = tmp_path / "overrides"
            overrides_dir.mkdir(parents=True)

            # Save first time
            result1 = save_brand_non_match("Brand A", "Brand B")
            assert result1["success"] is True

            # Save duplicate
            result2 = save_brand_non_match("Brand A", "Brand B")
            assert result2["success"] is True
            assert "already exists" in result2["message"]

            # Verify only one entry
            brands_file = overrides_dir / "non_matches_brands.yaml"
            with brands_file.open("r") as f:
                data = yaml.safe_load(f)
                assert data["Brand A"].count("Brand B") == 1
        finally:
            os.environ.pop("SOTD_DATA_DIR", None)

    def test_alphabetical_sorting_brands(self, tmp_path):
        """Test that brand non-matches are saved in alphabetical order."""
        os.environ["SOTD_DATA_DIR"] = str(tmp_path)
        try:
            overrides_dir = tmp_path / "overrides"
            overrides_dir.mkdir(parents=True)

            # Add non-matches in non-alphabetical order
            save_brand_non_match("Zebra Brand", "Alpha Brand")
            save_brand_non_match("Zebra Brand", "Beta Brand")
            save_brand_non_match("Alpha Brand", "Zebra Brand")

            brands_file = overrides_dir / "non_matches_brands.yaml"
            with brands_file.open("r") as f:
                data = yaml.safe_load(f)

            # Check that keys are sorted
            keys = list(data.keys())
            assert keys == sorted(keys)

            # Check that lists are sorted
            for brand, non_matches in data.items():
                assert non_matches == sorted(non_matches)
        finally:
            os.environ.pop("SOTD_DATA_DIR", None)


class TestSaveScentNonMatch:
    """Test save_scent_non_match function."""

    def test_save_new_scent_non_match(self, tmp_path):
        """Test saving a new scent non-match."""
        os.environ["SOTD_DATA_DIR"] = str(tmp_path)
        try:
            overrides_dir = tmp_path / "overrides"
            overrides_dir.mkdir(parents=True)

            result = save_scent_non_match("Brand A", "Scent 1", "Scent 2")

            assert result["success"] is True

            # Verify file was created
            scents_file = overrides_dir / "non_matches_scents.yaml"
            assert scents_file.exists()

            with scents_file.open("r") as f:
                data = yaml.safe_load(f)
                assert "Brand A" in data
                assert "Scent 1" in data["Brand A"]
                assert "Scent 2" in data["Brand A"]["Scent 1"]
        finally:
            os.environ.pop("SOTD_DATA_DIR", None)

    def test_alphabetical_sorting_scents(self, tmp_path):
        """Test that scent non-matches are saved in alphabetical order."""
        os.environ["SOTD_DATA_DIR"] = str(tmp_path)
        try:
            overrides_dir = tmp_path / "overrides"
            overrides_dir.mkdir(parents=True)

            # Add non-matches in non-alphabetical order
            save_scent_non_match("Zebra Brand", "Zebra Scent", "Alpha Scent")
            save_scent_non_match("Zebra Brand", "Zebra Scent", "Beta Scent")
            save_scent_non_match("Alpha Brand", "Alpha Scent", "Zebra Scent")

            scents_file = overrides_dir / "non_matches_scents.yaml"
            with scents_file.open("r") as f:
                data = yaml.safe_load(f)

            # Check that brand keys are sorted
            brand_keys = list(data.keys())
            assert brand_keys == sorted(brand_keys)

            # Check that scent keys within each brand are sorted
            for brand, scents in data.items():
                scent_keys = list(scents.keys())
                assert scent_keys == sorted(scent_keys)

                # Check that non-match lists are sorted
                for scent, non_matches in scents.items():
                    assert non_matches == sorted(non_matches)
        finally:
            os.environ.pop("SOTD_DATA_DIR", None)


class TestSaveCrossBrandScentNonMatch:
    """Test save_cross_brand_scent_non_match function."""

    def test_save_new_cross_brand_scent_non_match(self, tmp_path):
        """Test saving a new cross-brand scent non-match."""
        os.environ["SOTD_DATA_DIR"] = str(tmp_path)
        try:
            overrides_dir = tmp_path / "overrides"
            overrides_dir.mkdir(parents=True)

            result = save_cross_brand_scent_non_match("Brand A", "Lavender", "Brand B", "Lavender")

            assert result["success"] is True

            # Verify file was created
            cross_brand_file = overrides_dir / "non_matches_scents_cross_brand.yaml"
            assert cross_brand_file.exists()

            with cross_brand_file.open("r") as f:
                data = yaml.safe_load(f)
                assert "Lavender" in data
                assert len(data["Lavender"]) == 2
                brands = [pair["brand"] for pair in data["Lavender"]]
                assert "Brand A" in brands
                assert "Brand B" in brands
        finally:
            os.environ.pop("SOTD_DATA_DIR", None)

    def test_alphabetical_sorting_cross_brand(self, tmp_path):
        """Test that cross-brand scent non-matches are saved in alphabetical order."""
        os.environ["SOTD_DATA_DIR"] = str(tmp_path)
        try:
            overrides_dir = tmp_path / "overrides"
            overrides_dir.mkdir(parents=True)

            # Add non-matches in non-alphabetical order
            save_cross_brand_scent_non_match("Zebra Brand", "Lavender", "Alpha Brand", "Lavender")
            save_cross_brand_scent_non_match("Beta Brand", "Lavender", "Zebra Brand", "Lavender")

            cross_brand_file = overrides_dir / "non_matches_scents_cross_brand.yaml"
            with cross_brand_file.open("r") as f:
                data = yaml.safe_load(f)

            # Check that scent name keys are sorted
            scent_keys = list(data.keys())
            assert scent_keys == sorted(scent_keys)

            # Check that brand-scent pairs within each scent are sorted by brand
            for scent_name, pairs in data.items():
                brands = [pair["brand"] for pair in pairs]
                assert brands == sorted(brands, key=str.lower)
        finally:
            os.environ.pop("SOTD_DATA_DIR", None)

    def test_atomic_write(self, tmp_path):
        """Test that atomic write pattern is used (temp file then replace)."""
        os.environ["SOTD_DATA_DIR"] = str(tmp_path)
        try:
            overrides_dir = tmp_path / "overrides"
            overrides_dir.mkdir(parents=True)

            # Save a non-match
            save_brand_non_match("Brand A", "Brand B")

            brands_file = overrides_dir / "non_matches_brands.yaml"
            assert brands_file.exists()

            # Verify temp file doesn't exist (should have been replaced)
            temp_file = brands_file.with_suffix(".tmp")
            assert not temp_file.exists()
        finally:
            os.environ.pop("SOTD_DATA_DIR", None)


class TestCanonicalStorage:
    """Test canonical storage (no duplication) for non-matches."""

    def test_save_brand_non_match_canonical(self, tmp_path):
        """Test that brand non-matches are saved with canonical key (alphabetically first)."""
        os.environ["SOTD_DATA_DIR"] = str(tmp_path)
        try:
            overrides_dir = tmp_path / "overrides"
            overrides_dir.mkdir(parents=True)

            # Save A != B (A is alphabetically first)
            result = save_brand_non_match("Brand A", "Brand B")
            assert result["success"] is True

            # Verify only A -> B exists (canonical storage)
            brands_file = overrides_dir / "non_matches_brands.yaml"
            with brands_file.open("r") as f:
                data = yaml.safe_load(f)

            assert "Brand A" in data
            assert "Brand B" in data["Brand A"]
            # B -> A should NOT exist (canonical storage)
            assert "Brand B" not in data or "Brand A" not in data.get("Brand B", [])

            # Test reverse: save B != A (should still use A as key)
            result2 = save_brand_non_match("Brand B", "Brand A")
            assert result2["success"] is True

            # Verify still only A -> B (no duplication)
            with brands_file.open("r") as f:
                data2 = yaml.safe_load(f)
            assert "Brand A" in data2
            assert "Brand B" in data2["Brand A"]
            assert data2["Brand A"].count("Brand B") == 1  # No duplicates
        finally:
            os.environ.pop("SOTD_DATA_DIR", None)

    def test_save_scent_non_match_canonical(self, tmp_path):
        """Test that scent non-matches are saved with canonical key (alphabetically first)."""
        os.environ["SOTD_DATA_DIR"] = str(tmp_path)
        try:
            overrides_dir = tmp_path / "overrides"
            overrides_dir.mkdir(parents=True)

            # Save A != B (A is alphabetically first)
            result = save_scent_non_match("Brand A", "Scent A", "Scent B")
            assert result["success"] is True

            # Verify only A -> B exists (canonical storage)
            scents_file = overrides_dir / "non_matches_scents.yaml"
            with scents_file.open("r") as f:
                data = yaml.safe_load(f)

            assert "Brand A" in data
            assert "Scent A" in data["Brand A"]
            assert "Scent B" in data["Brand A"]["Scent A"]
            # B -> A should NOT exist (canonical storage)
            assert "Scent B" not in data["Brand A"] or "Scent A" not in data["Brand A"].get(
                "Scent B", []
            )
        finally:
            os.environ.pop("SOTD_DATA_DIR", None)

    def test_save_cross_brand_scent_non_match_canonical(self, tmp_path):
        """Test that cross-brand scent non-matches use canonical key (alphabetically first)."""
        os.environ["SOTD_DATA_DIR"] = str(tmp_path)
        try:
            overrides_dir = tmp_path / "overrides"
            overrides_dir.mkdir(parents=True)

            # Save Leather != Heather (Heather is alphabetically first)
            result = save_cross_brand_scent_non_match(
                "Noble Otter", "Leather", "Barrister & Mann", "Heather"
            )
            assert result["success"] is True

            # Verify only Heather key exists (canonical storage)
            cross_brand_file = overrides_dir / "non_matches_scents_cross_brand.yaml"
            with cross_brand_file.open("r") as f:
                data = yaml.safe_load(f)

            assert "Heather" in data
            assert "Leather" not in data  # Should not have separate key
            # Verify both pairs are under Heather
            brands_in_group = [pair.get("brand") for pair in data["Heather"]]
            scents_in_group = [pair.get("scent") for pair in data["Heather"]]
            assert "Noble Otter" in brands_in_group
            assert "Barrister & Mann" in brands_in_group
            assert "Leather" in scents_in_group
            assert "Heather" in scents_in_group
        finally:
            os.environ.pop("SOTD_DATA_DIR", None)

    def test_load_canonicalizes_and_dedupes(self, tmp_path):
        """Test that loading canonicalizes and dedupes entries."""
        os.environ["SOTD_DATA_DIR"] = str(tmp_path)
        try:
            overrides_dir = tmp_path / "overrides"
            overrides_dir.mkdir(parents=True)

            # Manually create duplicate/non-canonical YAML (B -> A and A -> B)
            brands_file = overrides_dir / "non_matches_brands.yaml"
            with brands_file.open("w") as f:
                yaml.dump({"Brand A": ["Brand B"], "Brand B": ["Brand A"]}, f)

            # Load and verify canonicalization (only A -> B should remain)
            result = load_non_matches()

            # Verify canonicalization in memory
            assert "Brand A" in result["brand_non_matches"]
            assert "Brand B" in result["brand_non_matches"]["Brand A"]
            # B -> A should be removed (canonical storage)
            assert "Brand B" not in result["brand_non_matches"] or "Brand A" not in result[
                "brand_non_matches"
            ].get("Brand B", [])

            # Verify file is updated
            with brands_file.open("r") as f:
                saved_data = yaml.safe_load(f)
                assert "Brand A" in saved_data
                assert "Brand B" in saved_data["Brand A"]
                # B -> A should be removed
                assert "Brand B" not in saved_data or "Brand A" not in saved_data.get("Brand B", [])
        finally:
            os.environ.pop("SOTD_DATA_DIR", None)

    def test_canonicalization_on_existing_data(self, tmp_path):
        """Test that existing duplicate/non-canonical data is fixed."""
        os.environ["SOTD_DATA_DIR"] = str(tmp_path)
        try:
            overrides_dir = tmp_path / "overrides"
            overrides_dir.mkdir(parents=True)

            # Create duplicate scent data (both A -> B and B -> A)
            scents_file = overrides_dir / "non_matches_scents.yaml"
            with scents_file.open("w") as f:
                yaml.dump({"Brand A": {"Scent A": ["Scent B"], "Scent B": ["Scent A"]}}, f)

            # Load existing duplicate data
            result = load_non_matches()

            # Verify canonicalization (only A -> B should remain, A is alphabetically first)
            assert "Brand A" in result["scent_non_matches"]
            assert "Scent A" in result["scent_non_matches"]["Brand A"]
            assert "Scent B" in result["scent_non_matches"]["Brand A"]["Scent A"]
            # B -> A should be removed
            assert "Scent B" not in result["scent_non_matches"][
                "Brand A"
            ] or "Scent A" not in result["scent_non_matches"]["Brand A"].get("Scent B", [])

            # Verify file is updated with canonical entries
            with scents_file.open("r") as f:
                saved_data = yaml.safe_load(f)
                assert "Brand A" in saved_data
                assert "Scent A" in saved_data["Brand A"]
                assert "Scent B" in saved_data["Brand A"]["Scent A"]
                # B -> A should be removed
                assert "Scent B" not in saved_data["Brand A"] or "Scent A" not in saved_data[
                    "Brand A"
                ].get("Scent B", [])
        finally:
            os.environ.pop("SOTD_DATA_DIR", None)
