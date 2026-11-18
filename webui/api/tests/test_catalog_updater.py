"""Tests for CatalogUpdater — writes accepted proposals to catalog YAML files."""

from unittest.mock import patch

import pytest
import yaml

from webui.api.catalog_updater import CatalogUpdater


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Create a temporary data directory with minimal catalog files."""
    # soaps.yaml
    soaps = {
        "House of Mammoth": {
            "patterns": ["(?:house of )?mammoth"],
            "scents": {"Tobacconist": {"patterns": ["mammoth.*tobacconist"]}},
        }
    }
    (tmp_path / "soaps.yaml").write_text(yaml.dump(soaps, default_flow_style=False))

    # razors.yaml
    razors = {"Karve": {"Christopher Bradley": {"patterns": ["karve.*(?:christopher|cb)"]}}}
    (tmp_path / "razors.yaml").write_text(yaml.dump(razors, default_flow_style=False))

    # blades.yaml
    blades = {
        "DE": {"Astra": {"Superior Platinum": {"patterns": ["astra.*(?:superior|sp|green)"]}}}
    }
    (tmp_path / "blades.yaml").write_text(yaml.dump(blades, default_flow_style=False))

    # brushes.yaml
    brushes = {
        "known_brushes": {
            "Chisel & Hound": {
                "V21 Fanchurian": {
                    "fiber": "Badger",
                    "knot_size_mm": 28,
                    "patterns": ["chisel.*hound.*v21.*fanchurian"],
                }
            }
        }
    }
    (tmp_path / "brushes.yaml").write_text(yaml.dump(brushes, default_flow_style=False))

    return tmp_path


@pytest.fixture
def updater(tmp_data_dir):
    return CatalogUpdater(tmp_data_dir)


# ---------------------------------------------------------------------------
# Soap scents
# ---------------------------------------------------------------------------
class TestAddSoapScent:
    def test_adds_scent_to_existing_brand(self, updater, tmp_data_dir):
        updater.add_soap_scent("House of Mammoth", "Cerulean", ["mammoth.*cerulean"])
        catalog = yaml.safe_load((tmp_data_dir / "soaps.yaml").read_text())
        assert "Cerulean" in catalog["House of Mammoth"]["scents"]
        assert catalog["House of Mammoth"]["scents"]["Cerulean"]["patterns"] == [
            "mammoth.*cerulean"
        ]

    def test_preserves_existing_scents(self, updater, tmp_data_dir):
        updater.add_soap_scent("House of Mammoth", "Cerulean", ["mammoth.*cerulean"])
        catalog = yaml.safe_load((tmp_data_dir / "soaps.yaml").read_text())
        assert "Tobacconist" in catalog["House of Mammoth"]["scents"]

    def test_raises_if_brand_not_found(self, updater):
        with pytest.raises(KeyError, match="Brand .* not found"):
            updater.add_soap_scent("Nonexistent Brand", "Scent", ["pattern"])

    def test_raises_if_scent_already_exists(self, updater):
        with pytest.raises(ValueError, match="already exists"):
            updater.add_soap_scent("House of Mammoth", "Tobacconist", ["new pattern"])

    def test_special_characters_in_scent_name(self, updater, tmp_data_dir):
        """Scent names with apostrophes, ampersands etc. should be preserved."""
        updater.add_soap_scent(
            "House of Mammoth", "You & I (Moonlit)", ["mammoth.*you.*i.*moonlit"]
        )
        catalog = yaml.safe_load((tmp_data_dir / "soaps.yaml").read_text())
        assert "You & I (Moonlit)" in catalog["House of Mammoth"]["scents"]

    def test_multiple_patterns(self, updater, tmp_data_dir):
        updater.add_soap_scent(
            "House of Mammoth",
            "Alive",
            ["mammoth.*alive", "hom.*alive"],
        )
        catalog = yaml.safe_load((tmp_data_dir / "soaps.yaml").read_text())
        assert len(catalog["House of Mammoth"]["scents"]["Alive"]["patterns"]) == 2


# ---------------------------------------------------------------------------
# Soap patterns
# ---------------------------------------------------------------------------
class TestAddSoapPattern:
    def test_adds_pattern_to_existing_scent(self, updater, tmp_data_dir):
        updater.add_soap_pattern("House of Mammoth", "Tobacconist", "hom.*tobac")
        catalog = yaml.safe_load((tmp_data_dir / "soaps.yaml").read_text())
        patterns = catalog["House of Mammoth"]["scents"]["Tobacconist"]["patterns"]
        assert "hom.*tobac" in patterns
        assert "mammoth.*tobacconist" in patterns  # original preserved

    def test_raises_if_brand_not_found(self, updater):
        with pytest.raises(KeyError, match="not found"):
            updater.add_soap_pattern("Nonexistent", "Scent", "pattern")

    def test_raises_if_scent_not_found(self, updater):
        with pytest.raises(KeyError, match="not found"):
            updater.add_soap_pattern("House of Mammoth", "Nonexistent Scent", "pattern")


# ---------------------------------------------------------------------------
# Razor models
# ---------------------------------------------------------------------------
class TestAddRazorModel:
    def test_adds_model_to_existing_brand(self, updater, tmp_data_dir):
        updater.add_razor_model("Karve", "Overlander", ["karve.*overlander"], format="DE")
        catalog = yaml.safe_load((tmp_data_dir / "razors.yaml").read_text())
        assert "Overlander" in catalog["Karve"]
        assert catalog["Karve"]["Overlander"]["patterns"] == ["karve.*overlander"]

    def test_adds_format_when_not_de(self, updater, tmp_data_dir):
        updater.add_razor_model("Karve", "GEM Model", ["karve.*gem"], format="GEM")
        catalog = yaml.safe_load((tmp_data_dir / "razors.yaml").read_text())
        assert catalog["Karve"]["GEM Model"]["format"] == "GEM"

    def test_no_format_key_when_de(self, updater, tmp_data_dir):
        """DE is the default format -- should not be stored explicitly."""
        updater.add_razor_model("Karve", "New DE", ["karve.*new"], format="DE")
        catalog = yaml.safe_load((tmp_data_dir / "razors.yaml").read_text())
        assert "format" not in catalog["Karve"]["New DE"]

    def test_adds_new_brand(self, updater, tmp_data_dir):
        updater.add_razor_model("Yates", "921-H", ["yates.*921"], format="DE")
        catalog = yaml.safe_load((tmp_data_dir / "razors.yaml").read_text())
        assert "Yates" in catalog
        assert "921-H" in catalog["Yates"]

    def test_preserves_existing_models(self, updater, tmp_data_dir):
        updater.add_razor_model("Karve", "Overlander", ["karve.*overlander"], format="DE")
        catalog = yaml.safe_load((tmp_data_dir / "razors.yaml").read_text())
        assert "Christopher Bradley" in catalog["Karve"]


# ---------------------------------------------------------------------------
# Razor patterns
# ---------------------------------------------------------------------------
class TestAddRazorPattern:
    def test_adds_pattern_to_existing_model(self, updater, tmp_data_dir):
        updater.add_razor_pattern("Karve", "Christopher Bradley", "karve.*cb.*sb")
        catalog = yaml.safe_load((tmp_data_dir / "razors.yaml").read_text())
        patterns = catalog["Karve"]["Christopher Bradley"]["patterns"]
        assert "karve.*cb.*sb" in patterns

    def test_raises_if_not_found(self, updater):
        with pytest.raises(KeyError, match="not found"):
            updater.add_razor_pattern("Nonexistent", "Model", "pattern")


# ---------------------------------------------------------------------------
# Blade models
# ---------------------------------------------------------------------------
class TestAddBladeModel:
    def test_adds_blade_to_existing_format_and_brand(self, updater, tmp_data_dir):
        updater.add_blade_model("DE", "Astra", "Superior Stainless", ["astra.*(?:stainless|blue)"])
        catalog = yaml.safe_load((tmp_data_dir / "blades.yaml").read_text())
        assert "Superior Stainless" in catalog["DE"]["Astra"]

    def test_adds_new_brand_under_format(self, updater, tmp_data_dir):
        updater.add_blade_model("DE", "Wizamet", "Super Iridium", ["wizamet"])
        catalog = yaml.safe_load((tmp_data_dir / "blades.yaml").read_text())
        assert "Wizamet" in catalog["DE"]
        assert "Super Iridium" in catalog["DE"]["Wizamet"]

    def test_adds_new_format(self, updater, tmp_data_dir):
        updater.add_blade_model("AC", "Schick", "Proline", ["schick.*proline"])
        catalog = yaml.safe_load((tmp_data_dir / "blades.yaml").read_text())
        assert "AC" in catalog
        assert "Schick" in catalog["AC"]

    def test_preserves_existing_entries(self, updater, tmp_data_dir):
        updater.add_blade_model("AC", "Schick", "Proline", ["schick.*proline"])
        catalog = yaml.safe_load((tmp_data_dir / "blades.yaml").read_text())
        assert "Superior Platinum" in catalog["DE"]["Astra"]


# ---------------------------------------------------------------------------
# Blade patterns
# ---------------------------------------------------------------------------
class TestAddBladePattern:
    def test_adds_pattern_to_existing_model(self, updater, tmp_data_dir):
        updater.add_blade_pattern("DE", "Astra", "Superior Platinum", "astra.*plat")
        catalog = yaml.safe_load((tmp_data_dir / "blades.yaml").read_text())
        patterns = catalog["DE"]["Astra"]["Superior Platinum"]["patterns"]
        assert "astra.*plat" in patterns
        assert "astra.*(?:superior|sp|green)" in patterns

    def test_raises_if_not_found(self, updater):
        with pytest.raises(KeyError, match="not found"):
            updater.add_blade_pattern("DE", "Nonexistent", "Model", "pattern")


# ---------------------------------------------------------------------------
# Brush models
# ---------------------------------------------------------------------------
class TestAddBrushModel:
    def test_adds_brush_to_existing_brand(self, updater, tmp_data_dir):
        updater.add_brush_model(
            "Chisel & Hound",
            "V23 Synth",
            ["chisel.*hound.*v23"],
            fiber="Synthetic",
            knot_size_mm=26,
        )
        catalog = yaml.safe_load((tmp_data_dir / "brushes.yaml").read_text())
        entry = catalog["known_brushes"]["Chisel & Hound"]["V23 Synth"]
        assert entry["fiber"] == "Synthetic"
        assert entry["knot_size_mm"] == 26
        assert entry["patterns"] == ["chisel.*hound.*v23"]

    def test_adds_new_brand(self, updater, tmp_data_dir):
        updater.add_brush_model("New Artisan", "Model 1", ["new.*artisan.*model.*1"], fiber="Boar")
        catalog = yaml.safe_load((tmp_data_dir / "brushes.yaml").read_text())
        assert "New Artisan" in catalog["known_brushes"]

    def test_preserves_existing_brushes(self, updater, tmp_data_dir):
        updater.add_brush_model(
            "Chisel & Hound", "V23 Synth", ["chisel.*hound.*v23"], fiber="Synthetic"
        )
        catalog = yaml.safe_load((tmp_data_dir / "brushes.yaml").read_text())
        assert "V21 Fanchurian" in catalog["known_brushes"]["Chisel & Hound"]

    def test_without_knot_size(self, updater, tmp_data_dir):
        updater.add_brush_model("New Artisan", "Model 1", ["new.*artisan.*model.*1"], fiber="Boar")
        catalog = yaml.safe_load((tmp_data_dir / "brushes.yaml").read_text())
        entry = catalog["known_brushes"]["New Artisan"]["Model 1"]
        assert "knot_size_mm" not in entry
        assert entry["fiber"] == "Boar"


# ---------------------------------------------------------------------------
# Brush patterns
# ---------------------------------------------------------------------------
class TestAddBrushPattern:
    def test_adds_pattern_to_existing_brush(self, updater, tmp_data_dir):
        updater.add_brush_pattern("Chisel & Hound", "V21 Fanchurian", "c.*h.*v21")
        catalog = yaml.safe_load((tmp_data_dir / "brushes.yaml").read_text())
        patterns = catalog["known_brushes"]["Chisel & Hound"]["V21 Fanchurian"]["patterns"]
        assert "c.*h.*v21" in patterns
        assert "chisel.*hound.*v21.*fanchurian" in patterns

    def test_raises_if_not_found(self, updater):
        with pytest.raises(KeyError, match="not found"):
            updater.add_brush_pattern("Nonexistent", "Model", "pattern")


# ---------------------------------------------------------------------------
# apply_proposal dispatch
# ---------------------------------------------------------------------------
class TestApplyProposal:
    def test_applies_new_scent_proposal(self, updater, tmp_data_dir):
        proposal = {
            "type": "new_scent",
            "field": "soap",
            "brand": "House of Mammoth",
            "model": "Cerulean",
            "suggested_pattern": "mammoth.*cerulean",
            "confidence": 0.9,
        }
        updater.apply_proposal(proposal)
        catalog = yaml.safe_load((tmp_data_dir / "soaps.yaml").read_text())
        assert "Cerulean" in catalog["House of Mammoth"]["scents"]

    def test_applies_new_pattern_proposal_soap(self, updater, tmp_data_dir):
        proposal = {
            "type": "new_pattern",
            "field": "soap",
            "brand": "House of Mammoth",
            "model": "Tobacconist",
            "suggested_pattern": "hom.*tobac",
            "confidence": 0.85,
        }
        updater.apply_proposal(proposal)
        catalog = yaml.safe_load((tmp_data_dir / "soaps.yaml").read_text())
        assert "hom.*tobac" in catalog["House of Mammoth"]["scents"]["Tobacconist"]["patterns"]

    def test_applies_new_pattern_proposal_razor(self, updater, tmp_data_dir):
        proposal = {
            "type": "new_pattern",
            "field": "razor",
            "brand": "Karve",
            "model": "Christopher Bradley",
            "suggested_pattern": "karve.*cb.*sb",
            "confidence": 0.85,
        }
        updater.apply_proposal(proposal)
        catalog = yaml.safe_load((tmp_data_dir / "razors.yaml").read_text())
        assert "karve.*cb.*sb" in catalog["Karve"]["Christopher Bradley"]["patterns"]

    def test_applies_new_pattern_proposal_blade(self, updater, tmp_data_dir):
        proposal = {
            "type": "new_pattern",
            "field": "blade",
            "brand": "Astra",
            "model": "Superior Platinum",
            "suggested_pattern": "astra.*plat",
            "suggested_entry": {"format": "DE"},
            "confidence": 0.85,
        }
        updater.apply_proposal(proposal)
        catalog = yaml.safe_load((tmp_data_dir / "blades.yaml").read_text())
        assert "astra.*plat" in catalog["DE"]["Astra"]["Superior Platinum"]["patterns"]

    def test_applies_new_pattern_proposal_brush(self, updater, tmp_data_dir):
        proposal = {
            "type": "new_pattern",
            "field": "brush",
            "brand": "Chisel & Hound",
            "model": "V21 Fanchurian",
            "suggested_pattern": "c.*h.*v21",
            "confidence": 0.85,
        }
        updater.apply_proposal(proposal)
        catalog = yaml.safe_load((tmp_data_dir / "brushes.yaml").read_text())
        assert (
            "c.*h.*v21" in catalog["known_brushes"]["Chisel & Hound"]["V21 Fanchurian"]["patterns"]
        )

    def test_applies_new_product_razor(self, updater, tmp_data_dir):
        proposal = {
            "type": "new_product",
            "field": "razor",
            "brand": "Yates",
            "model": "921-H",
            "suggested_pattern": "yates.*921",
            "suggested_entry": {"format": "DE", "patterns": ["yates.*921"]},
            "confidence": 0.75,
        }
        updater.apply_proposal(proposal)
        catalog = yaml.safe_load((tmp_data_dir / "razors.yaml").read_text())
        assert "Yates" in catalog
        assert "921-H" in catalog["Yates"]

    def test_applies_new_product_razor_non_de(self, updater, tmp_data_dir):
        proposal = {
            "type": "new_product",
            "field": "razor",
            "brand": "Mongoose",
            "model": "Mongoose",
            "suggested_pattern": "mongoose",
            "suggested_entry": {"format": "AC", "patterns": ["mongoose"]},
            "confidence": 0.8,
        }
        updater.apply_proposal(proposal)
        catalog = yaml.safe_load((tmp_data_dir / "razors.yaml").read_text())
        assert catalog["Mongoose"]["Mongoose"]["format"] == "AC"

    def test_applies_new_product_blade(self, updater, tmp_data_dir):
        proposal = {
            "type": "new_product",
            "field": "blade",
            "brand": "Wizamet",
            "model": "Super Iridium",
            "suggested_pattern": "wizamet",
            "suggested_entry": {"format": "DE", "patterns": ["wizamet"]},
            "confidence": 0.8,
        }
        updater.apply_proposal(proposal)
        catalog = yaml.safe_load((tmp_data_dir / "blades.yaml").read_text())
        assert "Wizamet" in catalog["DE"]

    def test_applies_new_product_brush(self, updater, tmp_data_dir):
        proposal = {
            "type": "new_product",
            "field": "brush",
            "brand": "New Artisan",
            "model": "The Brush",
            "suggested_pattern": "new.*artisan.*brush",
            "suggested_entry": {
                "fiber": "Badger",
                "knot_size_mm": 28,
                "patterns": ["new.*artisan.*brush"],
            },
            "confidence": 0.7,
        }
        updater.apply_proposal(proposal)
        catalog = yaml.safe_load((tmp_data_dir / "brushes.yaml").read_text())
        assert "New Artisan" in catalog["known_brushes"]
        entry = catalog["known_brushes"]["New Artisan"]["The Brush"]
        assert entry["fiber"] == "Badger"
        assert entry["knot_size_mm"] == 28

    def test_applies_new_product_soap(self, updater, tmp_data_dir):
        """new_product for soap with an existing brand adds a scent."""
        proposal = {
            "type": "new_product",
            "field": "soap",
            "brand": "House of Mammoth",
            "model": "Embrace",
            "suggested_pattern": "mammoth.*embrace",
            "suggested_entry": {"patterns": ["mammoth.*embrace"]},
            "confidence": 0.8,
        }
        updater.apply_proposal(proposal)
        catalog = yaml.safe_load((tmp_data_dir / "soaps.yaml").read_text())
        assert "Embrace" in catalog["House of Mammoth"]["scents"]

    def test_raises_on_unknown_proposal_type(self, updater):
        proposal = {"type": "unknown_type", "field": "soap"}
        with pytest.raises(ValueError, match="Unknown proposal type"):
            updater.apply_proposal(proposal)

    def test_raises_on_invalid_field_for_new_scent(self, updater):
        """new_scent is only valid for soap."""
        proposal = {
            "type": "new_scent",
            "field": "razor",
            "brand": "Karve",
            "model": "Something",
            "suggested_pattern": "karve.*something",
        }
        with pytest.raises(ValueError, match="new_scent is only valid for soap"):
            updater.apply_proposal(proposal)


# ---------------------------------------------------------------------------
# Atomic write safety
# ---------------------------------------------------------------------------
class TestAtomicWrites:
    def test_no_tmp_file_left_on_success(self, updater, tmp_data_dir):
        updater.add_soap_scent("House of Mammoth", "Cerulean", ["mammoth.*cerulean"])
        assert not (tmp_data_dir / "soaps.tmp").exists()

    def test_original_preserved_on_write_failure(self, updater, tmp_data_dir):
        """If yaml.dump raises, the original catalog should be untouched."""
        original_content = (tmp_data_dir / "soaps.yaml").read_text()

        with patch("yaml.dump", side_effect=IOError("disk full")):
            with pytest.raises(IOError):
                updater.add_soap_scent("House of Mammoth", "Cerulean", ["mammoth.*cerulean"])

        # Original file should be unchanged
        assert (tmp_data_dir / "soaps.yaml").read_text() == original_content
        # Tmp file should be cleaned up
        assert not (tmp_data_dir / "soaps.tmp").exists()

    def test_yaml_format_uses_block_style(self, updater, tmp_data_dir):
        """Verify YAML output uses block style (default_flow_style=False)."""
        updater.add_soap_scent("House of Mammoth", "Cerulean", ["mammoth.*cerulean"])
        content = (tmp_data_dir / "soaps.yaml").read_text()
        # Block-style lists use "- " prefix, flow style uses "["
        assert "- mammoth.*cerulean" in content
        assert "[" not in content or "patterns: [" not in content


# ---------------------------------------------------------------------------
# Catalog file mapping
# ---------------------------------------------------------------------------
class TestCatalogFiles:
    def test_catalog_file_mapping(self):
        assert CatalogUpdater.CATALOG_FILES == {
            "soap": "soaps.yaml",
            "razor": "razors.yaml",
            "blade": "blades.yaml",
            "brush": "brushes.yaml",
        }
