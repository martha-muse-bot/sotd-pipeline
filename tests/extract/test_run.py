import json
import tempfile
import yaml
from pathlib import Path
from sotd.extract.run import run_extraction_for_month


def test_run_extraction_for_month_valid(monkeypatch):
    comments = [
        {"id": "1", "body": "* **Razor:** Blackbird"},
        {"id": "2", "body": "* **Blade:** Feather"},
        {"id": "3", "body": "No product listed here"},
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "data/comments/2025-04.json"
        path.parent.mkdir(parents=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"data": comments}, f, ensure_ascii=False)

        monkeypatch.chdir(tmpdir)
        result = run_extraction_for_month("2025-04")

        assert result is not None

        assert result["meta"]["shave_count"] == 2
        assert result["meta"]["skipped_count"] == 1
        assert result["meta"]["comment_count"] == 3
        assert result["meta"]["field_coverage"]["razor"] == 1
        assert result["meta"]["field_coverage"]["blade"] == 1
        assert len(result["data"]) == 2
        assert len(result["skipped"]) == 1

        # Check that extracted data has structured format
        razor_data = result["data"][0]
        blade_data = result["data"][1]

        assert "razor" in razor_data
        assert razor_data["razor"]["original"] == "Blackbird"
        assert razor_data["razor"]["normalized"] == "Blackbird"

        assert "blade" in blade_data
        assert blade_data["blade"]["original"] == "Feather"
        assert blade_data["blade"]["normalized"] == "Feather"


def test_run_extraction_for_month_file_not_found():
    result = run_extraction_for_month("1900-01")
    assert result is None


def test_run_extraction_for_month_with_normalization(monkeypatch):
    """Test that normalization works correctly during extraction."""
    comments = [
        {"id": "1", "body": "* **Razor:** Blackbird $DOORKNOB"},
        {"id": "2", "body": "* **Blade:** Feather (3x)"},
        {"id": "3", "body": "* **Soap:** Tabac (sample)"},
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create data directory structure
        data_dir = Path(tmpdir) / "data"
        data_dir.mkdir(parents=True)

        # Create competition tags file in the right location
        competition_tags = {"strip_tags": ["DOORKNOB", "CNC", "ARTISTCLUB"], "preserve_tags": []}
        tags_path = Path(tmpdir) / "data/competition_tags.yaml"
        with open(tags_path, "w", encoding="utf-8") as f:
            yaml.dump(competition_tags, f)

        # Create comments file
        path = data_dir / "comments/2025-04.json"
        path.parent.mkdir(parents=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"data": comments}, f, ensure_ascii=False)

        monkeypatch.chdir(tmpdir)

        # Clear competition tags cache to ensure fresh loading
        from sotd.utils.competition_tags import clear_competition_tags_cache

        clear_competition_tags_cache()

        result = run_extraction_for_month("2025-04")

        assert result is not None
        assert len(result["data"]) == 3

        # Check normalization results
        razor_data = result["data"][0]
        blade_data = result["data"][1]
        soap_data = result["data"][2]

        # Razor: competition tags should be stripped
        assert razor_data["razor"]["original"] == "Blackbird $DOORKNOB"
        assert razor_data["razor"]["normalized"] == "Blackbird"

        # Blade: usage count should be stripped
        assert blade_data["blade"]["original"] == "Feather (3x)"
        assert blade_data["blade"]["normalized"] == "Feather"

        # Soap: sample marker should be stripped
        assert soap_data["soap"]["original"] == "Tabac (sample)"
        assert soap_data["soap"]["normalized"] == "Tabac"


def test_blade_normalization_country_origin(monkeypatch):
    """Test that country of origin patterns are normalized out during blade extraction."""
    comments = [
        {"id": "1", "body": "* **Blade:** Astra Green (Indian)"},
        {"id": "2", "body": "* **Blade:** Gillette Platinum (Russia)"},
        {"id": "3", "body": "* **Blade:** Wilkinson Sword (Made in Germany)"},
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "data/comments/2025-04.json"
        path.parent.mkdir(parents=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"data": comments}, f, ensure_ascii=False)

        monkeypatch.chdir(tmpdir)
        result = run_extraction_for_month("2025-04")

        assert result is not None
        assert len(result["data"]) == 3

        # Check that country of origin patterns are normalized out
        blade_data_1 = result["data"][0]
        blade_data_2 = result["data"][1]
        blade_data_3 = result["data"][2]

        # Astra Green (Indian) -> Astra Green
        assert blade_data_1["blade"]["original"] == "Astra Green (Indian)"
        assert blade_data_1["blade"]["normalized"] == "Astra Green"

        # Gillette Platinum (Russia) -> Gillette Platinum
        assert blade_data_2["blade"]["original"] == "Gillette Platinum (Russia)"
        assert blade_data_2["blade"]["normalized"] == "Gillette Platinum"

        # Wilkinson Sword (Made in Germany) -> Wilkinson Sword
        assert blade_data_3["blade"]["original"] == "Wilkinson Sword (Made in Germany)"
        assert blade_data_3["blade"]["normalized"] == "Wilkinson Sword"


def test_blade_normalization_decimal_usage_counts(monkeypatch):
    """Test that decimal usage count patterns are normalized out during blade extraction."""
    comments = [
        {
            "id": "1",
            "body": "* **Blade:** Astra - SP Green [3.5] / Gillette 7 O'Clock SharpEdge [.5]",
        },
        {"id": "2", "body": "* **Blade:** Gillette Slim Adjustable (I 2) [2.5]"},
        {"id": "3", "body": "* **Blade:** Personna Super (1.5)"},
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "data/comments/2025-04.json"
        path.parent.mkdir(parents=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"data": comments}, f, ensure_ascii=False)

        monkeypatch.chdir(tmpdir)
        result = run_extraction_for_month("2025-04")

        assert result is not None
        assert len(result["data"]) == 3

        # Check that decimal usage count patterns are normalized out
        blade_data_1 = result["data"][0]
        blade_data_2 = result["data"][1]
        blade_data_3 = result["data"][2]

        # Astra - SP Green [3.5] / Gillette 7 O'Clock SharpEdge [.5] ->
        # Astra - SP Green / Gillette 7 O'Clock SharpEdge
        original_1 = "Astra - SP Green [3.5] / Gillette 7 O'Clock SharpEdge [.5]"
        assert blade_data_1["blade"]["original"] == original_1
        assert (
            blade_data_1["blade"]["normalized"] == "Astra - SP Green / Gillette 7 O'Clock SharpEdge"
        )

        # Gillette Slim Adjustable (I 2) [2.5] -> Gillette Slim Adjustable (I 2)
        original_2 = "Gillette Slim Adjustable (I 2) [2.5]"
        assert blade_data_2["blade"]["original"] == original_2
        assert blade_data_2["blade"]["normalized"] == "Gillette Slim Adjustable (I 2)"

        # Personna Super (1.5) -> Personna Super
        original_3 = "Personna Super (1.5)"
        assert blade_data_3["blade"]["original"] == original_3
        assert blade_data_3["blade"]["normalized"] == "Personna Super"


def test_blade_normalization_hash_usage_counts(monkeypatch):
    """Test that hash usage count patterns are normalized out during blade extraction."""
    comments = [
        {"id": "1", "body": "* **Blade:** Gillette Silver Blue (#3)"},
        {"id": "2", "body": "* **Blade:** Feather (#12)"},
        {"id": "3", "body": "* **Blade:** Astra (shave #5)"},
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "data/comments/2025-04.json"
        path.parent.mkdir(parents=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"data": comments}, f, ensure_ascii=False)

        # Create competition tags file in the right location
        competition_tags = {"strip_tags": ["DOORKNOB", "CNC", "ARTISTCLUB"], "preserve_tags": []}
        tags_path = Path(tmpdir) / "data/competition_tags.yaml"
        with open(tags_path, "w", encoding="utf-8") as f:
            yaml.dump(competition_tags, f)

        monkeypatch.chdir(tmpdir)
        result = run_extraction_for_month("2025-04")

        assert result is not None
        assert len(result["data"]) == 3

        # Check that hash usage count patterns are normalized out
        blade_data_1 = result["data"][0]
        blade_data_2 = result["data"][1]
        blade_data_3 = result["data"][2]

        # Gillette Silver Blue (#3) -> Gillette Silver Blue
        assert blade_data_1["blade"]["original"] == "Gillette Silver Blue (#3)"
        assert blade_data_1["blade"]["normalized"] == "Gillette Silver Blue"

        # Feather (#12) -> Feather
        assert blade_data_2["blade"]["original"] == "Feather (#12)"
        assert blade_data_2["blade"]["normalized"] == "Feather"

        # Astra (shave #5) -> Astra
        assert blade_data_3["blade"]["original"] == "Astra (shave #5)"
        assert blade_data_3["blade"]["normalized"] == "Astra"


def test_blade_normalization_approximate_numbers(monkeypatch):
    """Test that approximate number patterns are normalized out during blade extraction."""
    comments = [
        {"id": "1", "body": "* **Blade:** Wizamet Iridium Super Extra Stainless (10ish)"},
        {"id": "2", "body": "* **Blade:** Gilette Platinum (10ish?)"},
        {"id": "3", "body": "* **Blade:** Feather (5ish)"},
        {"id": "4", "body": "* **Blade:** Kai Captain (11-ish)"},
        {"id": "5", "body": "* **Blade:** Astra [3ish]"},
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "data/comments/2025-04.json"
        path.parent.mkdir(parents=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"data": comments}, f, ensure_ascii=False)

        # Create competition tags file in the right location
        competition_tags = {"strip_tags": ["DOORKNOB", "CNC", "ARTISTCLUB"], "preserve_tags": []}
        tags_path = Path(tmpdir) / "data/competition_tags.yaml"
        with open(tags_path, "w", encoding="utf-8") as f:
            yaml.dump(competition_tags, f)

        monkeypatch.chdir(tmpdir)
        result = run_extraction_for_month("2025-04")

        assert result is not None
        assert len(result["data"]) == 5

        # Check that approximate number patterns are normalized out
        blade_data_1 = result["data"][0]
        blade_data_2 = result["data"][1]
        blade_data_3 = result["data"][2]
        blade_data_4 = result["data"][3]
        blade_data_5 = result["data"][4]

        # Wizamet Iridium Super Extra Stainless (10ish) -> Wizamet Iridium Super Extra Stainless
        assert blade_data_1["blade"]["original"] == "Wizamet Iridium Super Extra Stainless (10ish)"
        assert blade_data_1["blade"]["normalized"] == "Wizamet Iridium Super Extra Stainless"

        # Gilette Platinum (10ish?) -> Gilette Platinum
        assert blade_data_2["blade"]["original"] == "Gilette Platinum (10ish?)"
        assert blade_data_2["blade"]["normalized"] == "Gilette Platinum"

        # Feather (5ish) -> Feather
        assert blade_data_3["blade"]["original"] == "Feather (5ish)"
        assert blade_data_3["blade"]["normalized"] == "Feather"

        # Kai Captain (11-ish) -> Kai Captain
        assert blade_data_4["blade"]["original"] == "Kai Captain (11-ish)"
        assert blade_data_4["blade"]["normalized"] == "Kai Captain"

        # Astra [3ish] -> Astra
        assert blade_data_5["blade"]["original"] == "Astra [3ish]"
        assert blade_data_5["blade"]["normalized"] == "Astra"


def test_blade_normalization_asterisk_stripping(monkeypatch):
    """Test that asterisks are stripped during blade normalization."""
    comments = [
        {"id": "1", "body": "* **Blade:** * **Gillette - Nacet** (Marathon) (541)"},
        {"id": "2", "body": "* **Blade:** Razo*Rock Mission"},
        {"id": "3", "body": "* **Blade:** * **Timeless - Stainless Steel .68** Open Comb"},
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "data/comments/2025-04.json"
        path.parent.mkdir(parents=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"data": comments}, f, ensure_ascii=False)

        # Create competition tags file in the right location
        competition_tags = {"strip_tags": ["DOORKNOB", "CNC", "ARTISTCLUB"], "preserve_tags": []}
        tags_path = Path(tmpdir) / "data/competition_tags.yaml"
        with open(tags_path, "w", encoding="utf-8") as f:
            yaml.dump(competition_tags, f)

        monkeypatch.chdir(tmpdir)
        result = run_extraction_for_month("2025-04")

        assert result is not None
        assert len(result["data"]) == 3

        # Check that asterisks are stripped
        blade_data_1 = result["data"][0]
        blade_data_2 = result["data"][1]
        blade_data_3 = result["data"][2]

        # * **Gillette - Nacet** (Marathon) (541) -> Gillette - Nacet (Marathon)
        assert blade_data_1["blade"]["original"] == "* **Gillette - Nacet** (Marathon) (541)"
        assert blade_data_1["blade"]["normalized"] == "Gillette - Nacet (Marathon)"

        # Razo*Rock Mission -> RazoRock Mission
        assert blade_data_2["blade"]["original"] == "Razo*Rock Mission"
        assert blade_data_2["blade"]["normalized"] == "RazoRock Mission"

        # * **Timeless - Stainless Steel .68** Open Comb -> Timeless - Stainless Steel .68 Open Comb
        assert blade_data_3["blade"]["original"] == "* **Timeless - Stainless Steel .68** Open Comb"
        assert blade_data_3["blade"]["normalized"] == "Timeless - Stainless Steel .68 Open Comb"


def test_blade_normalization_x_usage_counts():
    """Test normalization of X usage count patterns like (16X), (17X)"""
    from sotd.utils.extract_normalization import strip_usage_count_patterns

    test_cases = [
        ("FROMM Hair Shaper Blade (16X)", "FROMM Hair Shaper Blade"),
        ("Wilkinson (16X)", "Wilkinson"),
        ("KAI PINK Feather Cut Blade (16X)", "KAI PINK Feather Cut Blade"),
        ("Cloud A77 Full Blade (16X)", "Cloud A77 Full Blade"),
        ("Cloud A77 Mini Blade (17X)", "Cloud A77 Mini Blade"),
        ("KAI PINK Feather Cut Blade (17X)", "KAI PINK Feather Cut Blade"),
        ("Wilkinson (17X)", "Wilkinson"),
    ]

    for original, expected in test_cases:
        result = strip_usage_count_patterns(original)
        assert result == expected, f"Expected '{expected}', got '{result}' for '{original}'"


def test_blade_normalization_maybe_usage_counts():
    """Test normalization of maybe usage count patterns like (17 maybe)"""
    from sotd.utils.extract_normalization import strip_usage_count_patterns

    test_cases = [
        ("Gillette Silver Blue (17 maybe)", "Gillette Silver Blue"),
        ("Astra SP (5 maybe)", "Astra SP"),
        ("Feather (10 maybe)", "Feather"),
    ]

    for original, expected in test_cases:
        result = strip_usage_count_patterns(original)
        assert result == expected, f"Expected '{expected}', got '{result}' for '{original}'"


def test_blade_normalization_comprehensive_shave_counts(monkeypatch):
    """Test that all comprehensive shave count patterns are
    normalized out during blade extraction."""
    comments = [
        # Basic usage counts
        {"id": "1", "body": "* **Blade:** Parker (1 use)"},
        {"id": "2", "body": "* **Blade:** Gillette Nacet (2 use)"},
        {"id": "3", "body": "* **Blade:** Parker (#2 use)"},
        # Ordinal usage patterns
        {"id": "4", "body": "* **Blade:** Wizamet (1st shave)"},
        {"id": "5", "body": "* **Blade:** Feather (2nd shave)"},
        {"id": "6", "body": "* **Blade:** Accuforge GEM (10th shave)"},
        {"id": "7", "body": "* **Blade:** Schick (13th shave)"},
        {"id": "8", "body": "* **Blade:** Dorco ST300 (16th shave)"},
        # Completion/status indicators
        {"id": "9", "body": "* **Blade:** Treet Falcon (1 and done)"},
        {"id": "10", "body": "* **Blade:** Van der Hagen (1 and last)"},
        {"id": "11", "body": "* **Blade:** Personna Hair Shaper (1st and final)"},
        {"id": "12", "body": "* **Blade:** Personna Red (2nd and last)"},
        {"id": "13", "body": "* **Blade:** Gillette Goal (11 and final)"},
        {"id": "14", "body": "* **Blade:** Shaving Revolution (11 and probably last)"},
        # User speculation/approximation
        {"id": "15", "body": "* **Blade:** Personna GEM PTFE (10 I think)"},
        {"id": "16", "body": "* **Blade:** Voshkod (3 I think)"},
        {"id": "17", "body": "* **Blade:** Kai Captain (7, I think)"},
        {"id": "18", "body": "* **Blade:** Blue Sword Platinum (30+ I think)"},
        {"id": "19", "body": "* **Blade:** Persona platinum (5? I think)"},
        # Complex usage descriptions
        {"id": "20", "body": "* **Blade:** Rapira Platinum Lux (10+?; At least four months old)"},
        {"id": "21", "body": "* **Blade:** Astra (100...woohoo!)"},
        {"id": "22", "body": "* **Blade:** Pro 500 (1st use and done)"},
        {"id": "23", "body": "* **Blade:** Seagull (<1 and done)"},
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "data/comments/2025-04.json"
        path.parent.mkdir(parents=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"data": comments}, f, ensure_ascii=False)

        # Create competition tags file in the right location
        competition_tags = {"strip_tags": ["DOORKNOB", "CNC", "ARTISTCLUB"], "preserve_tags": []}
        tags_path = Path(tmpdir) / "data/competition_tags.yaml"
        with open(tags_path, "w", encoding="utf-8") as f:
            yaml.dump(competition_tags, f)

        monkeypatch.chdir(tmpdir)
        result = run_extraction_for_month("2025-04")

        assert result is not None
        assert len(result["data"]) == 23

        # Check that all shave count patterns are normalized out
        # Basic usage counts
        assert result["data"][0]["blade"]["normalized"] == "Parker"
        assert result["data"][1]["blade"]["normalized"] == "Gillette Nacet"
        assert result["data"][2]["blade"]["normalized"] == "Parker"

        # Ordinal usage patterns
        assert result["data"][3]["blade"]["normalized"] == "Wizamet"
        assert result["data"][4]["blade"]["normalized"] == "Feather"
        assert result["data"][5]["blade"]["normalized"] == "Accuforge GEM"
        assert result["data"][6]["blade"]["normalized"] == "Schick"
        assert result["data"][7]["blade"]["normalized"] == "Dorco ST300"

        # Completion/status indicators
        assert result["data"][8]["blade"]["normalized"] == "Treet Falcon"
        assert result["data"][9]["blade"]["normalized"] == "Van der Hagen"
        assert result["data"][10]["blade"]["normalized"] == "Personna Hair Shaper"
        assert result["data"][11]["blade"]["normalized"] == "Personna Red"
        assert result["data"][12]["blade"]["normalized"] == "Gillette Goal"
        assert result["data"][13]["blade"]["normalized"] == "Shaving Revolution"

        # User speculation/approximation
        assert result["data"][14]["blade"]["normalized"] == "Personna GEM PTFE"
        assert result["data"][15]["blade"]["normalized"] == "Voshkod"
        assert result["data"][16]["blade"]["normalized"] == "Kai Captain"
        assert result["data"][17]["blade"]["normalized"] == "Blue Sword Platinum"
        assert result["data"][18]["blade"]["normalized"] == "Persona platinum"

        # Complex usage descriptions
        assert result["data"][19]["blade"]["normalized"] == "Rapira Platinum Lux"
        assert result["data"][20]["blade"]["normalized"] == "Astra"
        assert result["data"][21]["blade"]["normalized"] == "Pro 500"
        assert result["data"][22]["blade"]["normalized"] == "Seagull"


# --- C10 #19: extract summary must report the true loss -------------------
# _process_month used to re-split run_extraction_for_month's "data" (which
# already holds only successfully parsed comments), so "missing" was always
# empty, and the multi-month total_skipped summed missing_count (always 0)
# instead of skipped_count. There is now one honest number: skipped_count.


def _write_comments_file(base: Path, month: str, comments: list[dict]) -> None:
    path = base / "comments" / f"{month}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"data": comments}, f, ensure_ascii=False)


def test_process_month_counts_unparsed_comments_as_skipped_not_missing(tmp_path):
    """A field-less comment is skipped, never 'missing' (no missing bucket)."""
    from sotd.extract.run import _process_month

    _write_comments_file(
        tmp_path,
        "2025-01",
        [
            {"id": "1", "body": "* **Razor:** Blackbird"},
            {"id": "2", "body": "No product listed here"},
        ],
    )

    result = _process_month(2025, 1, tmp_path, debug=False, force=True)

    assert result is not None
    assert result["meta"]["shave_count"] == 1
    assert result["meta"]["skipped_count"] == 1
    # The dead "missing" bucket is gone: one honest number, not two.
    assert "missing_count" not in result["meta"]
    assert "missing" not in result
    assert len(result["skipped"]) == 1
    assert result["skipped"][0]["id"] == "2"


def test_multi_month_summary_reports_true_total_skipped(tmp_path, caplog):
    """2 months with known skipped counts -> summary matches per-file meta."""
    import logging

    from sotd.extract.cli import get_parser
    from sotd.extract.run import run

    _write_comments_file(
        tmp_path,
        "2025-01",
        [
            {"id": "j1", "body": "* **Razor:** Blackbird"},
            {"id": "j2", "body": "No product listed here"},
        ],
    )
    _write_comments_file(
        tmp_path,
        "2025-02",
        [
            {"id": "f1", "body": "* **Soap:** Tabac"},
            {"id": "f2", "body": "just chatting"},
            {"id": "f3", "body": "another non-shave comment"},
        ],
    )

    args = get_parser().parse_args(
        [
            "--sequential",
            "--delta-months",
            "2025-01,2025-02",
            "--data-dir",
            str(tmp_path),
        ]
    )
    with caplog.at_level(logging.INFO):
        run(args)

    # Ground truth from the per-file meta: 1 + 2 skipped.
    total_skipped = 0
    for month in ("2025-01", "2025-02"):
        with open(tmp_path / "extracted" / f"{month}.json", encoding="utf-8") as f:
            total_skipped += json.load(f)["meta"]["skipped_count"]
    assert total_skipped == 3

    summary = "\n".join(caplog.messages)
    assert "SOTD extract complete for 2025-01…2025-02: 2 records processed, 3 skipped" in summary


def test_dropped_month_warned_in_summary(tmp_path, caplog):
    """A month with no comments file is named in a warning, not silently dropped."""
    import logging

    from sotd.extract.cli import get_parser
    from sotd.extract.run import run

    _write_comments_file(
        tmp_path,
        "2025-01",
        [{"id": "j1", "body": "* **Razor:** Blackbird"}],
    )
    # No comments/2025-02.json on purpose.

    args = get_parser().parse_args(
        [
            "--sequential",
            "--delta-months",
            "2025-01,2025-02",
            "--data-dir",
            str(tmp_path),
        ]
    )
    with caplog.at_level(logging.WARNING):
        run(args)

    assert "Skipped 1 month(s) with missing input files: 2025-02" in caplog.text
    # The present month still processed.
    assert (tmp_path / "extracted" / "2025-01.json").exists()
