# Match Validation Agent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Claude Code skill that uses LLM judgment to verify non-exact matches and propose catalog changes, plus WebUI enhancements to review and apply agent output.

**Architecture:** A `/validate-matches` Claude Code command dispatches 4 parallel field agents (razor, blade, brush, soap). Each agent reads its field's entries, catalog, and correct_matches, then produces verifications and proposals. Output files are reviewed in the MatchAnalyzer WebUI with accept/reject actions that write directly to catalogs and correct_matches.

**Tech Stack:** Claude Code custom commands (markdown), Python/FastAPI backend, React/TypeScript frontend, YAML catalogs

**Design Doc:** `docs/plans/2026-03-09-match-validation-agent-design.md`

---

## Task 1: Output Directory Structure

**Files:**
- Create: `data/verified/.gitkeep`
- Create: `data/proposed/.gitkeep`
- Create: `data/validation/.gitkeep`

**Step 1: Create directories**

```bash
mkdir -p data/verified data/proposed data/validation
touch data/verified/.gitkeep data/proposed/.gitkeep data/validation/.gitkeep
```

**Step 2: Add to .gitignore if needed**

Check `.gitignore` — the JSON output files should NOT be gitignored (they're small, useful to track). Only `.gitkeep` is needed to ensure empty dirs exist.

**Step 3: Commit**

```bash
git add data/verified/.gitkeep data/proposed/.gitkeep data/validation/.gitkeep
git commit -m "chore: add output directories for match validation agent"
```

---

## Task 2: Claude Code `/validate-matches` Command

**Files:**
- Create: `.claude/commands/validate-matches.md`

This is the core agent skill — a markdown prompt file that Claude Code loads when the user runs `/validate-matches`.

**Step 1: Create the command file**

Create `.claude/commands/validate-matches.md` with the full orchestrator prompt. The command must:

1. Parse the `--month YYYY-MM` argument (or default to most recent matched file)
2. Read `data/matched/YYYY-MM.json` and filter to non-exact entries
3. Partition entries by field (razor, blade, brush, soap)
4. For each field, read its catalog and correct_matches file
5. Dispatch 4 parallel agents using the Agent tool
6. Each agent receives: field entries, catalog content, correct_matches content, and field-specific instructions
7. Each agent returns JSON with verifications and proposals
8. Orchestrator merges results into `data/verified/YYYY-MM.json` and `data/proposed/YYYY-MM.json`
9. Print summary statistics

**Command file content:**

```markdown
---
description: Validate non-exact matches and propose catalog changes for a month
---

# Match Validation Agent

You are validating matched SOTD (Shave of the Day) data. Your job is to:
1. Verify whether non-exact matches are correct
2. Propose catalog changes for misses

## Arguments

The user provides: `$ARGUMENTS` (expected format: `--month YYYY-MM`)

Parse the month from arguments. If no month provided, find the most recent file in `data/matched/`.

## Step 1: Load and Partition Data

Read `data/matched/{month}.json`. Extract all entries from the `data` array where any product field (razor, blade, brush, soap) has a `match_type` that is NOT `"exact"`.

For each non-exact field in each entry, create a record:
```json
{
  "comment_id": "...",
  "author": "...",
  "field": "razor|blade|brush|soap",
  "original": "the original text",
  "normalized": "normalized text",
  "matched": { "brand": "...", "model": "..." },
  "match_type": "regex|brand|filtered|unmatched|...",
  "pattern": "regex pattern or null",
  "body": "full comment body for context"
}
```

Partition these records into 4 lists by field.

## Step 2: Load Catalogs and Correct Matches

For each field, read:
- **Catalog**: `data/{field_catalog}.yaml` where field_catalog mapping is:
  - razor → `razors.yaml`
  - blade → `blades.yaml`
  - brush → `brushes.yaml`
  - soap → `soaps.yaml`
- **Correct matches**: `data/correct_matches/{field}.yaml`
- **For brushes also read**: `data/correct_matches/handle.yaml` and `data/correct_matches/knot.yaml`

## Step 3: Dispatch Parallel Field Agents

Launch 4 parallel agents using the Agent tool. Each agent receives its field's entries, catalog excerpt, and correct_matches.

**IMPORTANT**: If a field has more than 40 entries, split into batches of 40 and process sequentially within that agent to avoid context overflow.

### Agent Prompt Template (customize per field)

For each agent, use this prompt structure:

---

You are a {FIELD} match validation agent for the SOTD (Shave of the Day) pipeline. You analyze wet shaving product mentions from Reddit and determine whether the automated matching system got them right.

**Your tasks:**
1. For each entry, judge whether the match is correct → produce a verification
2. For incorrect or missing matches, propose catalog changes

**Context - Catalog Structure:**
{CATALOG_CONTENT — include relevant portion}

**Context - Correct Matches (examples of verified matches):**
{CORRECT_MATCHES_CONTENT — include relevant portion}

**Entries to validate:**
{JSON array of entries for this field}

### Verification Rules

For each entry, produce a verdict:
- **"verified"** — the match is correct. The matched brand/model accurately represents what the user wrote.
- **"needs_review"** — you're uncertain. The match might be right but you can't confirm.
- **"incorrect"** — the match is clearly wrong. The user meant a different product.

Include confidence (0.0-1.0) and brief reasoning for each verdict.

**What makes a match correct:**
- Abbreviations: "CB" → "Christopher Bradley", "WR" → "WR" series razors
- Common variations: "DG" → "Declaration Grooming", "HoM" → "House of Mammoth"
- Plate/variant suffixes: "SB-B", "OC", etc. are razor plate variants, not separate products
- The matched brand and model should be a real product that the original text clearly refers to

**What makes a match incorrect:**
- Wrong brand: user wrote brand X but matched to brand Y
- Wrong model: user wrote model A but matched to model B
- Non-existent product: the matched entry doesn't represent a real product

### Proposal Rules

For unmatched entries or incorrect matches, propose catalog changes:

**Proposal types:**
- **"new_scent"** (soap only): Brand exists in catalog but scent is missing
- **"new_pattern"**: Product exists in catalog but pattern doesn't catch this variation
- **"new_product"**: Product not in catalog at all

**Requirements:**
- Every proposed regex pattern MUST be tested: verify it matches the original text using Python regex semantics (case-insensitive)
- For new soap scents: You MUST use web search to verify the scent exists. Find the artisan's website or a retailer listing. Use the correct scent name (fix typos). If you cannot verify the scent exists, set the verdict to "needs_review" instead of creating a proposal.
- For new products (any field): Use web search to verify the product exists and gather details (format for razors, fiber for brushes, etc.)
- Follow existing naming conventions from the catalog and correct_matches

**Output format — return valid JSON:**

```json
{
  "field": "{FIELD}",
  "verifications": [
    {
      "comment_id": "abc123",
      "field": "{FIELD}",
      "original": "original text",
      "matched": {"brand": "...", "model": "..."},
      "match_type": "regex",
      "verdict": "verified|needs_review|incorrect",
      "confidence": 0.95,
      "reasoning": "Brief explanation"
    }
  ],
  "proposals": [
    {
      "type": "new_scent|new_pattern|new_product",
      "field": "{FIELD}",
      "brand": "Brand Name",
      "model": "Model/Scent Name",
      "suggested_pattern": "regex.*pattern",
      "suggested_entry": {},
      "evidence": ["comment abc: 'original text'"],
      "source_url": "https://...",
      "research": "Description of what was found",
      "confidence": 0.85
    }
  ]
}
```

Return ONLY the JSON object, no markdown fencing or extra text.

---

### Field-Specific Agent Instructions

**Razor agent additions:**
- Razors have a `format` field: DE, SE, SR, AC, GEM, Half DE, Injector, Cart
- When proposing new razors, determine the format from web research
- Catalog structure: `Brand → Model → {format?, patterns: []}`

**Blade agent additions:**
- Blades are organized by format: DE, AC, GEM, Injector, Half DE
- Catalog structure: `Format → Brand → Model → {patterns: []}`
- When proposing new blades, determine the format

**Brush agent additions:**
- Brushes can be simple (brand + model) or composite (handle + knot)
- Composite brushes have separate handle and knot components with independent brands
- Catalog structure: `known_brushes → Brand → Model → {fiber, knot_size_mm?, patterns: []}`
- Fiber types: Badger, Boar, Synthetic, Horse, Mixed Badger/Boar, Mixed Badger/Synthetic
- Also check `data/handles.yaml` and `data/knots.yaml` for component catalogs

**Soap agent additions:**
- Soaps have brand-level patterns and scent-level patterns
- Catalog structure: `Brand → {patterns: [], scents: {Scent → {patterns: [], wsdb_slug?}}}`
- CRITICAL: All new scent proposals MUST be verified via web search. Find the artisan's website or retailer. Use the correct scent name, fixing any user typos.
- Common soap artisans: Barrister and Mann, Declaration Grooming, House of Mammoth, Stirling, Noble Otter, Ariana & Evans, Wholly Kaw, Zingari Man, Spearhead Shaving, Chicago Grooming Co., etc.

## Step 4: Merge and Write Results

Collect JSON output from all 4 agents. Merge into two output files:

### `data/verified/{month}.json`

```json
{
  "metadata": {
    "month": "YYYY-MM",
    "processed_at": "ISO timestamp",
    "stats": {
      "total_non_exact": 0,
      "verified_correct": 0,
      "needs_review": 0,
      "incorrect": 0,
      "proposals_generated": 0
    }
  },
  "verifications": [ ...all verification objects from all agents... ]
}
```

### `data/proposed/{month}.json`

```json
{
  "metadata": {
    "month": "YYYY-MM",
    "processed_at": "ISO timestamp",
    "proposal_count": 0
  },
  "proposals": [ ...all proposal objects from all agents... ]
}
```

Write both files using the Write tool.

## Step 5: Print Summary

Print a summary table:

```
Match Validation Summary for YYYY-MM
=====================================
Field    | Verified | Review | Incorrect | Proposals
---------|----------|--------|-----------|----------
razor    |       12 |      3 |         1 |         2
blade    |        8 |      1 |         0 |         1
brush    |       25 |     10 |         3 |         8
soap     |       37 |      4 |         2 |         5
---------|----------|--------|-----------|----------
TOTAL    |       82 |     18 |         6 |        16
```
```

**Step 2: Test the command**

Run `/validate-matches --month 2026-02` (or a recent month with non-exact matches) and verify it produces output files.

**Step 3: Iterate on prompt quality**

Review agent output. Tune the prompt based on:
- Are verifications accurate?
- Are proposals well-formed with valid regex?
- Are web searches finding real products?
- Is the JSON output parseable?

**Step 4: Commit**

```bash
git add .claude/commands/validate-matches.md
git commit -m "feat: add /validate-matches Claude Code command"
```

---

## Task 3: Backend — CatalogUpdater Module

**Files:**
- Create: `webui/api/catalog_updater.py`
- Test: `webui/api/tests/test_catalog_updater.py`

This module writes to the catalog YAML files (`soaps.yaml`, `razors.yaml`, `blades.yaml`, `brushes.yaml`) when proposals are accepted.

**Step 1: Write the failing tests**

```python
# webui/api/tests/test_catalog_updater.py
import pytest
import yaml
from pathlib import Path
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


class TestAddSoapPattern:
    def test_adds_pattern_to_existing_scent(self, updater, tmp_data_dir):
        updater.add_soap_pattern("House of Mammoth", "Tobacconist", "hom.*tobac")
        catalog = yaml.safe_load((tmp_data_dir / "soaps.yaml").read_text())
        patterns = catalog["House of Mammoth"]["scents"]["Tobacconist"]["patterns"]
        assert "hom.*tobac" in patterns
        assert "mammoth.*tobacconist" in patterns  # original preserved


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
        """DE is the default format — should not be stored explicitly."""
        updater.add_razor_model("Karve", "New DE", ["karve.*new"], format="DE")
        catalog = yaml.safe_load((tmp_data_dir / "razors.yaml").read_text())
        assert "format" not in catalog["Karve"]["New DE"]

    def test_adds_new_brand(self, updater, tmp_data_dir):
        updater.add_razor_model("Yates", "921-H", ["yates.*921"], format="DE")
        catalog = yaml.safe_load((tmp_data_dir / "razors.yaml").read_text())
        assert "Yates" in catalog
        assert "921-H" in catalog["Yates"]


class TestAddRazorPattern:
    def test_adds_pattern_to_existing_model(self, updater, tmp_data_dir):
        updater.add_razor_pattern("Karve", "Christopher Bradley", "karve.*cb.*sb")
        catalog = yaml.safe_load((tmp_data_dir / "razors.yaml").read_text())
        patterns = catalog["Karve"]["Christopher Bradley"]["patterns"]
        assert "karve.*cb.*sb" in patterns


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

    def test_applies_new_pattern_proposal(self, updater, tmp_data_dir):
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
```

**Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=. pytest webui/api/tests/test_catalog_updater.py -v
```

Expected: ImportError — `catalog_updater` module doesn't exist yet.

**Step 3: Implement CatalogUpdater**

```python
# webui/api/catalog_updater.py
"""Write catalog changes (new scents, patterns, products) to YAML catalog files."""

import yaml
from pathlib import Path
from typing import Optional


class CatalogUpdater:
    """Applies accepted proposals to catalog YAML files."""

    CATALOG_FILES = {
        "soap": "soaps.yaml",
        "razor": "razors.yaml",
        "blade": "blades.yaml",
        "brush": "brushes.yaml",
    }

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)

    def _load_catalog(self, field: str) -> dict:
        path = self.data_dir / self.CATALOG_FILES[field]
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _save_catalog(self, field: str, data: dict) -> None:
        path = self.data_dir / self.CATALOG_FILES[field]
        tmp_path = path.with_suffix(".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            tmp_path.replace(path)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink()
            raise

    def add_soap_scent(self, brand: str, scent: str, patterns: list[str]) -> None:
        catalog = self._load_catalog("soap")
        if brand not in catalog:
            raise KeyError(f"Brand '{brand}' not found in soaps catalog")
        if scent in catalog[brand].get("scents", {}):
            raise ValueError(f"Scent '{scent}' already exists for brand '{brand}'")
        if "scents" not in catalog[brand]:
            catalog[brand]["scents"] = {}
        catalog[brand]["scents"][scent] = {"patterns": patterns}
        self._save_catalog("soap", catalog)

    def add_soap_pattern(self, brand: str, scent: str, pattern: str) -> None:
        catalog = self._load_catalog("soap")
        if brand not in catalog:
            raise KeyError(f"Brand '{brand}' not found in soaps catalog")
        if scent not in catalog[brand].get("scents", {}):
            raise KeyError(f"Scent '{scent}' not found for brand '{brand}'")
        catalog[brand]["scents"][scent]["patterns"].append(pattern)
        self._save_catalog("soap", catalog)

    def add_razor_model(
        self, brand: str, model: str, patterns: list[str], format: str = "DE"
    ) -> None:
        catalog = self._load_catalog("razor")
        if brand not in catalog:
            catalog[brand] = {}
        entry: dict = {"patterns": patterns}
        if format != "DE":
            entry["format"] = format
        catalog[brand][model] = entry
        self._save_catalog("razor", catalog)

    def add_razor_pattern(self, brand: str, model: str, pattern: str) -> None:
        catalog = self._load_catalog("razor")
        if brand not in catalog or model not in catalog[brand]:
            raise KeyError(f"Razor '{brand} / {model}' not found in catalog")
        catalog[brand][model]["patterns"].append(pattern)
        self._save_catalog("razor", catalog)

    def add_blade_model(self, format: str, brand: str, model: str, patterns: list[str]) -> None:
        catalog = self._load_catalog("blade")
        if format not in catalog:
            catalog[format] = {}
        if brand not in catalog[format]:
            catalog[format][brand] = {}
        catalog[format][brand][model] = {"patterns": patterns}
        self._save_catalog("blade", catalog)

    def add_blade_pattern(self, format: str, brand: str, model: str, pattern: str) -> None:
        catalog = self._load_catalog("blade")
        if (
            format not in catalog
            or brand not in catalog[format]
            or model not in catalog[format][brand]
        ):
            raise KeyError(f"Blade '{format} / {brand} / {model}' not found in catalog")
        catalog[format][brand][model]["patterns"].append(pattern)
        self._save_catalog("blade", catalog)

    def add_brush_model(
        self,
        brand: str,
        model: str,
        patterns: list[str],
        fiber: Optional[str] = None,
        knot_size_mm: Optional[int] = None,
    ) -> None:
        catalog = self._load_catalog("brush")
        if "known_brushes" not in catalog:
            catalog["known_brushes"] = {}
        if brand not in catalog["known_brushes"]:
            catalog["known_brushes"][brand] = {}
        entry: dict = {"patterns": patterns}
        if fiber:
            entry["fiber"] = fiber
        if knot_size_mm:
            entry["knot_size_mm"] = knot_size_mm
        catalog["known_brushes"][brand][model] = entry
        self._save_catalog("brush", catalog)

    def apply_proposal(self, proposal: dict) -> None:
        """Apply a single proposal from agent output. Dispatches to the appropriate method."""
        ptype = proposal["type"]
        field = proposal["field"]

        if ptype == "new_scent" and field == "soap":
            self.add_soap_scent(
                proposal["brand"],
                proposal["model"],
                [proposal["suggested_pattern"]],
            )
        elif ptype == "new_pattern":
            if field == "soap":
                self.add_soap_pattern(
                    proposal["brand"], proposal["model"], proposal["suggested_pattern"]
                )
            elif field == "razor":
                self.add_razor_pattern(
                    proposal["brand"], proposal["model"], proposal["suggested_pattern"]
                )
            elif field == "blade":
                entry = proposal.get("suggested_entry", {})
                fmt = entry.get("format", "DE")
                self.add_blade_pattern(
                    fmt, proposal["brand"], proposal["model"], proposal["suggested_pattern"]
                )
            elif field == "brush":
                # For brush patterns, we'd need to append to known_brushes
                catalog = self._load_catalog("brush")
                brand = proposal["brand"]
                model = proposal["model"]
                if (
                    brand in catalog.get("known_brushes", {})
                    and model in catalog["known_brushes"][brand]
                ):
                    catalog["known_brushes"][brand][model]["patterns"].append(
                        proposal["suggested_pattern"]
                    )
                    self._save_catalog("brush", catalog)
                else:
                    raise KeyError(f"Brush '{brand} / {model}' not found in catalog")
        elif ptype == "new_product":
            entry = proposal.get("suggested_entry", {})
            if field == "razor":
                self.add_razor_model(
                    proposal["brand"],
                    proposal["model"],
                    entry.get("patterns", [proposal["suggested_pattern"]]),
                    format=entry.get("format", "DE"),
                )
            elif field == "blade":
                self.add_blade_model(
                    entry.get("format", "DE"),
                    proposal["brand"],
                    proposal["model"],
                    entry.get("patterns", [proposal["suggested_pattern"]]),
                )
            elif field == "brush":
                self.add_brush_model(
                    proposal["brand"],
                    proposal["model"],
                    entry.get("patterns", [proposal["suggested_pattern"]]),
                    fiber=entry.get("fiber"),
                    knot_size_mm=entry.get("knot_size_mm"),
                )
            elif field == "soap":
                # New soap brand — unusual but possible
                self.add_soap_scent(
                    proposal["brand"],
                    proposal["model"],
                    [proposal["suggested_pattern"]],
                )
        else:
            raise ValueError(f"Unknown proposal type: {ptype} for field: {field}")
```

**Step 4: Run tests to verify they pass**

```bash
PYTHONPATH=. pytest webui/api/tests/test_catalog_updater.py -v
```

Expected: All tests PASS.

**Step 5: Commit**

```bash
git add webui/api/catalog_updater.py webui/api/tests/test_catalog_updater.py
git commit -m "feat: add CatalogUpdater for writing agent proposals to catalog YAML files"
```

---

## Task 4: Backend — Validation Router

**Files:**
- Create: `webui/api/routers/validation.py`
- Modify: `webui/api/main.py` (add router registration)
- Test: `webui/api/tests/test_validation_router.py`

This router serves agent output files and handles accept/reject actions.

**Step 1: Write failing tests**

```python
# webui/api/tests/test_validation_router.py
import pytest
import json
import yaml
from pathlib import Path
from fastapi.testclient import TestClient


@pytest.fixture
def sample_verified(tmp_path):
    """Create a sample verified file."""
    verified = {
        "metadata": {
            "month": "2026-02",
            "processed_at": "2026-03-09T12:00:00Z",
            "stats": {
                "total_non_exact": 10,
                "verified_correct": 7,
                "needs_review": 2,
                "incorrect": 1,
                "proposals_generated": 3,
            },
        },
        "verifications": [
            {
                "comment_id": "abc123",
                "field": "razor",
                "original": "Karve CB SB-B",
                "matched": {"brand": "Karve", "model": "Christopher Bradley"},
                "match_type": "regex",
                "verdict": "verified",
                "confidence": 0.95,
                "reasoning": "CB is abbreviation for Christopher Bradley",
            }
        ],
    }
    verified_dir = tmp_path / "verified"
    verified_dir.mkdir()
    (verified_dir / "2026-02.json").write_text(json.dumps(verified))
    return tmp_path


@pytest.fixture
def sample_proposed(tmp_path):
    """Create a sample proposed file."""
    proposed = {
        "metadata": {
            "month": "2026-02",
            "processed_at": "2026-03-09T12:00:00Z",
            "proposal_count": 1,
        },
        "proposals": [
            {
                "type": "new_scent",
                "field": "soap",
                "brand": "House of Mammoth",
                "model": "Cerulean",
                "suggested_pattern": "mammoth.*cerulean",
                "evidence": ["comment abc: 'HoM Cerulean'"],
                "source_url": "https://example.com",
                "confidence": 0.9,
            }
        ],
    }
    proposed_dir = tmp_path / "proposed"
    proposed_dir.mkdir()
    (proposed_dir / "2026-02.json").write_text(json.dumps(proposed))
    return tmp_path


def test_get_verified_returns_data(sample_verified):
    # Test that GET /api/validation/verified/2026-02 returns the verified file
    pass  # Implemented after router exists


def test_get_verified_404_for_missing_month():
    # Test that GET /api/validation/verified/2099-01 returns 404
    pass


def test_get_proposed_returns_data(sample_proposed):
    # Test that GET /api/validation/proposed/2026-02 returns the proposed file
    pass


def test_accept_proposal_writes_to_catalog():
    # Test that POST /api/validation/accept-proposal applies the proposal via CatalogUpdater
    pass


def test_reject_proposal_writes_to_rejections_file():
    # Test that POST /api/validation/reject-proposal appends to rejections.json
    pass


def test_bulk_approve_writes_to_correct_matches():
    # Test that POST /api/validation/bulk-approve uses existing mark-correct flow
    pass
```

Note: Full test implementations should use `TestClient` with the FastAPI app. The implementing agent should follow the existing test patterns in `webui/api/tests/` for app fixture setup.

**Step 2: Implement the validation router**

```python
# webui/api/routers/validation.py
"""API endpoints for agent match validation review."""

import json
import time
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from webui.api.catalog_updater import CatalogUpdater


router = APIRouter(prefix="/api/validation", tags=["validation"])

# Resolved at startup via configure()
_data_dir: Optional[Path] = None


def configure(data_dir: Path) -> None:
    """Set the data directory. Called from main.py at startup."""
    global _data_dir
    _data_dir = data_dir


def _get_data_dir() -> Path:
    if _data_dir is None:
        raise RuntimeError("Validation router not configured — call configure(data_dir) first")
    return _data_dir


# --- Request/Response Models ---


class AcceptProposalRequest(BaseModel):
    month: str
    proposal_index: int  # Index into the proposals array
    edited_proposal: Optional[dict] = None  # If user edited before accepting


class RejectProposalRequest(BaseModel):
    month: str
    proposal_index: int
    reason: Optional[str] = None


class BulkApproveRequest(BaseModel):
    field: str
    matches: list[dict[str, Any]]  # [{original, matched}] — same shape as mark-correct


# --- Endpoints ---


@router.get("/verified/{month}")
async def get_verified(month: str):
    """Load agent verification results for a month."""
    path = _get_data_dir() / "verified" / f"{month}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"No verified data for {month}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/proposed/{month}")
async def get_proposed(month: str):
    """Load agent proposals for a month."""
    path = _get_data_dir() / "proposed" / f"{month}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"No proposals for {month}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/months")
async def get_validated_months():
    """List months that have agent validation data."""
    data_dir = _get_data_dir()
    verified_dir = data_dir / "verified"
    proposed_dir = data_dir / "proposed"

    months = set()
    for d in [verified_dir, proposed_dir]:
        if d.exists():
            for f in d.glob("*.json"):
                months.add(f.stem)

    return {"months": sorted(months, reverse=True)}


@router.post("/accept-proposal")
async def accept_proposal(request: AcceptProposalRequest):
    """Accept an agent proposal — writes to the appropriate catalog file."""
    data_dir = _get_data_dir()
    proposed_path = data_dir / "proposed" / f"{request.month}.json"
    if not proposed_path.exists():
        raise HTTPException(status_code=404, detail=f"No proposals for {request.month}")

    with open(proposed_path, "r", encoding="utf-8") as f:
        proposed_data = json.load(f)

    proposals = proposed_data.get("proposals", [])
    if request.proposal_index < 0 or request.proposal_index >= len(proposals):
        raise HTTPException(status_code=400, detail="Invalid proposal index")

    proposal = request.edited_proposal or proposals[request.proposal_index]
    updater = CatalogUpdater(data_dir)

    try:
        updater.apply_proposal(proposal)
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Mark proposal as accepted in the file
    proposals[request.proposal_index]["_status"] = "accepted"
    proposals[request.proposal_index]["_accepted_at"] = time.time()
    with open(proposed_path, "w", encoding="utf-8") as f:
        json.dump(proposed_data, f, indent=2)

    return {"success": True, "message": f"Proposal accepted and applied to catalog"}


@router.post("/reject-proposal")
async def reject_proposal(request: RejectProposalRequest):
    """Reject an agent proposal — records to rejections.json."""
    data_dir = _get_data_dir()
    proposed_path = data_dir / "proposed" / f"{request.month}.json"
    if not proposed_path.exists():
        raise HTTPException(status_code=404, detail=f"No proposals for {request.month}")

    with open(proposed_path, "r", encoding="utf-8") as f:
        proposed_data = json.load(f)

    proposals = proposed_data.get("proposals", [])
    if request.proposal_index < 0 or request.proposal_index >= len(proposals):
        raise HTTPException(status_code=400, detail="Invalid proposal index")

    proposal = proposals[request.proposal_index]

    # Append to rejections file
    rejections_path = data_dir / "validation" / "rejections.json"
    rejections = []
    if rejections_path.exists():
        with open(rejections_path, "r", encoding="utf-8") as f:
            rejections = json.load(f)

    rejections.append(
        {
            "rejected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "month": request.month,
            "proposal": proposal,
            "reason": request.reason,
        }
    )

    with open(rejections_path, "w", encoding="utf-8") as f:
        json.dump(rejections, f, indent=2)

    # Mark proposal as rejected in the file
    proposals[request.proposal_index]["_status"] = "rejected"
    proposals[request.proposal_index]["_rejected_at"] = time.time()
    with open(proposed_path, "w", encoding="utf-8") as f:
        json.dump(proposed_data, f, indent=2)

    return {"success": True, "message": "Proposal rejected"}


@router.post("/bulk-approve")
async def bulk_approve(request: BulkApproveRequest):
    """Bulk approve verified matches — delegates to existing correct_matches queue.

    This reuses the existing QueueManager flow from analysis.py.
    """
    from webui.api.main import _queue_manager

    if _queue_manager is None:
        raise HTTPException(status_code=503, detail="Queue manager not available")

    operation_id = _queue_manager.add_operation(
        operation_type="mark_correct",
        field=request.field,
        matches=request.matches,
    )

    return {
        "success": True,
        "operation_id": operation_id,
        "message": f"Queued {len(request.matches)} entries for approval",
    }
```

**Step 3: Register the router in main.py**

Add to `webui/api/main.py`:

```python
from webui.api.routers.validation import (
    router as validation_router,
    configure as configure_validation,
)

# In the lifespan/startup section, after data_dir is resolved:
configure_validation(data_dir)

# In the router registration block:
app.include_router(validation_router)
```

**Step 4: Run tests**

```bash
PYTHONPATH=. pytest webui/api/tests/test_validation_router.py -v
```

**Step 5: Commit**

```bash
git add webui/api/routers/validation.py webui/api/tests/test_validation_router.py webui/api/main.py
git commit -m "feat: add validation router for agent review accept/reject endpoints"
```

---

## Task 5: Frontend — API Service Functions

**Files:**
- Modify: `webui/src/services/api.ts`

Add TypeScript types and API functions for the new validation endpoints.

**Step 1: Add types**

Add to the types section of `api.ts`:

```typescript
// --- Agent Validation Types ---

export interface VerificationItem {
  comment_id: string;
  field: string;
  original: string;
  matched: Record<string, unknown>;
  match_type: string;
  verdict: 'verified' | 'needs_review' | 'incorrect';
  confidence: number;
  reasoning: string;
}

export interface VerifiedData {
  metadata: {
    month: string;
    processed_at: string;
    stats: {
      total_non_exact: number;
      verified_correct: number;
      needs_review: number;
      incorrect: number;
      proposals_generated: number;
    };
  };
  verifications: VerificationItem[];
}

export interface ProposalItem {
  type: 'new_scent' | 'new_pattern' | 'new_product';
  field: string;
  brand: string;
  model: string;
  suggested_pattern: string;
  suggested_entry?: Record<string, unknown>;
  evidence: string[];
  source_url?: string;
  research?: string;
  confidence: number;
  _status?: 'accepted' | 'rejected';
  _accepted_at?: number;
  _rejected_at?: number;
}

export interface ProposedData {
  metadata: {
    month: string;
    processed_at: string;
    proposal_count: number;
  };
  proposals: ProposalItem[];
}

export interface ValidatedMonths {
  months: string[];
}
```

**Step 2: Add API functions**

```typescript
// --- Agent Validation API ---

export async function getVerifiedData(month: string): Promise<VerifiedData> {
  const response = await fetch(`${API_BASE}/validation/verified/${month}`);
  if (!response.ok) throw new Error(`Failed to load verified data: ${response.statusText}`);
  return response.json();
}

export async function getProposedData(month: string): Promise<ProposedData> {
  const response = await fetch(`${API_BASE}/validation/proposed/${month}`);
  if (!response.ok) throw new Error(`Failed to load proposals: ${response.statusText}`);
  return response.json();
}

export async function getValidatedMonths(): Promise<ValidatedMonths> {
  const response = await fetch(`${API_BASE}/validation/months`);
  if (!response.ok) throw new Error(`Failed to load validated months: ${response.statusText}`);
  return response.json();
}

export async function acceptProposal(
  month: string,
  proposalIndex: number,
  editedProposal?: Record<string, unknown>
): Promise<{ success: boolean; message: string }> {
  const response = await fetch(`${API_BASE}/validation/accept-proposal`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      month,
      proposal_index: proposalIndex,
      edited_proposal: editedProposal || null,
    }),
  });
  if (!response.ok) throw new Error(`Failed to accept proposal: ${response.statusText}`);
  return response.json();
}

export async function rejectProposal(
  month: string,
  proposalIndex: number,
  reason?: string
): Promise<{ success: boolean; message: string }> {
  const response = await fetch(`${API_BASE}/validation/reject-proposal`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      month,
      proposal_index: proposalIndex,
      reason: reason || null,
    }),
  });
  if (!response.ok) throw new Error(`Failed to reject proposal: ${response.statusText}`);
  return response.json();
}

export async function bulkApproveVerified(
  field: string,
  matches: Array<{ original: string; matched: Record<string, unknown> }>
): Promise<{ success: boolean; operation_id: string; message: string }> {
  const response = await fetch(`${API_BASE}/validation/bulk-approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ field, matches }),
  });
  if (!response.ok) throw new Error(`Failed to bulk approve: ${response.statusText}`);
  return response.json();
}
```

**Step 3: Commit**

```bash
git add webui/src/services/api.ts
git commit -m "feat: add frontend API types and functions for validation endpoints"
```

---

## Task 6: Frontend — Source Toggle in MatchAnalyzer

**Files:**
- Modify: `webui/src/pages/MatchAnalyzer.tsx`

Add a source toggle to switch between "Live" (existing behavior) and "Agent Review" mode.

**Step 1: Add state variables**

At the top of the component, add:

```typescript
const [reviewMode, setReviewMode] = useState<'live' | 'agent_review'>('live');
const [verifiedData, setVerifiedData] = useState<VerifiedData | null>(null);
const [proposedData, setProposedData] = useState<ProposedData | null>(null);
const [validatedMonths, setValidatedMonths] = useState<string[]>([]);
const [agentLoading, setAgentLoading] = useState(false);
```

**Step 2: Add mode toggle UI**

Add a toggle near the top of the controls section (follow the pattern used by `groupByMatched` checkbox or the WSDBAlignmentAnalyzer tabs). Use a simple button group or the existing shadcn Tabs component:

```tsx
<div className="flex items-center gap-2">
  <button
    className={`px-3 py-1 rounded ${reviewMode === 'live' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
    onClick={() => setReviewMode('live')}
  >
    Live
  </button>
  <button
    className={`px-3 py-1 rounded ${reviewMode === 'agent_review' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
    onClick={() => setReviewMode('agent_review')}
  >
    Agent Review
  </button>
</div>
```

**Step 3: Load agent data when switching to agent review mode**

Add a handler that loads verified/proposed data when the user selects Agent Review mode and a month:

```typescript
const loadAgentData = useCallback(async (month: string) => {
  setAgentLoading(true);
  try {
    const [verified, proposed] = await Promise.all([
      getVerifiedData(month),
      getProposedData(month),
    ]);
    setVerifiedData(verified);
    setProposedData(proposed);
  } catch (err) {
    console.error('Failed to load agent data:', err);
  } finally {
    setAgentLoading(false);
  }
}, []);
```

On mount, fetch available validated months:

```typescript
useEffect(() => {
  getValidatedMonths().then(data => setValidatedMonths(data.months)).catch(() => {});
}, []);
```

**Step 4: Conditionally render agent review content**

Wrap the existing table in a conditional. When `reviewMode === 'agent_review'`, render the agent review components (Tasks 7-8) instead of the existing mismatch table:

```tsx
{reviewMode === 'live' ? (
  // Existing MismatchAnalyzerDataTable / GroupedDataTable rendering
  // ... (current code, unchanged)
) : (
  // Agent review mode — implemented in Tasks 7-8
  <AgentReviewPanel
    verifiedData={verifiedData}
    proposedData={proposedData}
    loading={agentLoading}
    month={selectedMonths[0] || ''}
    onApprove={handleBulkApprove}
    onAcceptProposal={handleAcceptProposal}
    onRejectProposal={handleRejectProposal}
  />
)}
```

**Step 5: Commit**

```bash
git add webui/src/pages/MatchAnalyzer.tsx
git commit -m "feat: add source toggle for agent review mode in MatchAnalyzer"
```

---

## Task 7: Frontend — Agent Review Panel (Verifications)

**Files:**
- Create: `webui/src/components/data/AgentReviewPanel.tsx`

This component displays verifications and proposals in tabbed views.

**Step 1: Create the component**

Build a component with two tabs (Verifications / Proposals) using the existing shadcn Tabs component.

**Verifications tab features:**
- Table with columns: Field, Original, Matched, Verdict (color-coded badge), Confidence (progress bar or number), Reasoning, Checkbox for selection
- Color coding: green badge for "verified", yellow for "needs_review", red for "incorrect"
- Filter by field (razor/blade/brush/soap) and verdict (verified/needs_review/incorrect)
- Sort by confidence (ascending to surface low-confidence first)
- Select all / select filtered for bulk approve
- "Bulk Approve Selected" button — calls `bulkApproveVerified()` which delegates to existing correct_matches queue

**Key patterns to follow:**
- Use `@tanstack/react-table` DataTable like `MismatchAnalyzerDataTable.tsx`
- Use `HeaderFilter` component for column filtering (from `webui/src/components/ui/header-filter.tsx`)
- Use existing badge component (`webui/src/components/ui/badge.tsx`) for verdict display
- Reuse `DecisionToast` undo pattern for bulk approve actions

**Step 2: Wire up to MatchAnalyzer**

Import and render `AgentReviewPanel` in the agent review conditional from Task 6.

**Step 3: Commit**

```bash
git add webui/src/components/data/AgentReviewPanel.tsx webui/src/pages/MatchAnalyzer.tsx
git commit -m "feat: add AgentReviewPanel with verifications table and bulk approve"
```

---

## Task 8: Frontend — Proposals View with Actions

**Files:**
- Modify: `webui/src/components/data/AgentReviewPanel.tsx`

Add the Proposals tab to AgentReviewPanel.

**Step 1: Add proposals tab content**

**Proposals tab features:**
- Table or card layout with columns: Type (badge: new_scent / new_pattern / new_product), Field, Brand, Model/Scent, Suggested Pattern, Evidence (expandable), Research/Source URL (link), Confidence, Status, Actions
- Status column: pending / accepted / rejected (from `_status` field)
- Filter out already-accepted/rejected proposals by default (toggle to show all)
- Action buttons per row:
  - **Accept** — calls `acceptProposal(month, index)`, optimistically updates row status
  - **Edit + Accept** — opens a modal/inline editor to modify the proposal before accepting. Key editable fields: `model` (scent/model name), `suggested_pattern`, `suggested_entry` fields. After editing, calls `acceptProposal(month, index, editedProposal)`
  - **Reject** — opens a small input for reason, calls `rejectProposal(month, index, reason)`

**Key patterns to follow:**
- Use `ExpandablePatterns` component for showing evidence array
- For Edit+Accept modal, follow the pattern from `BrushSplitModal.tsx` or `EnrichPhaseModal.tsx`
- Source URL should render as a clickable external link

**Step 2: Handle accept/reject callbacks**

```typescript
const handleAcceptProposal = async (proposalIndex: number, edited?: Record<string, unknown>) => {
  try {
    await acceptProposal(month, proposalIndex, edited);
    // Refresh proposed data to reflect _status change
    const updated = await getProposedData(month);
    setProposedData(updated);
  } catch (err) {
    console.error('Failed to accept proposal:', err);
  }
};

const handleRejectProposal = async (proposalIndex: number, reason?: string) => {
  try {
    await rejectProposal(month, proposalIndex, reason);
    const updated = await getProposedData(month);
    setProposedData(updated);
  } catch (err) {
    console.error('Failed to reject proposal:', err);
  }
};
```

**Step 3: Commit**

```bash
git add webui/src/components/data/AgentReviewPanel.tsx
git commit -m "feat: add proposals tab with accept/edit/reject actions"
```

---

## Task 9: Integration Testing

**Files:**
- Test: `webui/api/tests/test_validation_integration.py`

**Step 1: Write end-to-end test**

Test the full flow:
1. Create sample verified + proposed files in a temp directory
2. Start the FastAPI app with the temp data directory
3. GET `/api/validation/verified/2026-02` → verify response shape
4. GET `/api/validation/proposed/2026-02` → verify response shape
5. POST `/api/validation/accept-proposal` with a new_scent proposal → verify catalog file was updated
6. POST `/api/validation/reject-proposal` → verify rejections.json was created
7. GET `/api/validation/months` → verify month appears

**Step 2: Run all tests**

```bash
PYTHONPATH=. pytest webui/api/tests/test_validation_router.py webui/api/tests/test_validation_integration.py webui/api/tests/test_catalog_updater.py -v
```

**Step 3: Run full test suite**

```bash
make test
```

**Step 4: Commit**

```bash
git add webui/api/tests/test_validation_integration.py
git commit -m "test: add integration tests for validation review flow"
```

---

## Task 10: Final Verification and Cleanup

**Step 1: Run the agent**

```bash
# In Claude Code:
/validate-matches --month 2026-02
```

Verify:
- `data/verified/2026-02.json` is created with valid structure
- `data/proposed/2026-02.json` is created with valid structure
- Summary statistics are printed

**Step 2: Test WebUI flow**

```bash
cd webui && npm run dev
```

- Open MatchAnalyzer
- Toggle to "Agent Review" mode
- Select the month that was validated
- Verify verifications table loads with correct data
- Verify proposals tab shows proposals
- Test: bulk approve a verified match → check `data/correct_matches/{field}.yaml`
- Test: accept a proposal → check the appropriate catalog YAML file
- Test: reject a proposal → check `data/validation/rejections.json`

**Step 3: Run full test suite one final time**

```bash
make all
```

**Step 4: Final commit if any cleanup was needed**

```bash
git add -A
git commit -m "chore: cleanup and polish match validation agent feature"
```
