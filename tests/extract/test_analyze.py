import json
import tempfile
from pathlib import Path

from sotd.extract.analyze import analyze_common_prefixes, analyze_skipped_patterns
from sotd.utils.aliases import FIELD_ALIASES


def test_analyze_skipped_patterns_outputs_expected(capsys):
    data = {
        "meta": {"month": "2025-04"},
        "data": [],
        "skipped": [
            {"id": "1", "body": "* Razor: Blackbird\n* Blade: Feather"},
            {"id": "2", "body": "Brush: Simpson"},
            {"id": "3", "body": ""},
            {"id": "4", "body": "Soap - Tabac"},
            {"id": "5", "body": "Random comment with no formatting"},
        ],
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "2025-04.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

        analyze_skipped_patterns([path], top_n=5, show_examples=1)
        out = capsys.readouterr().out

        assert "* markdown" in out
        assert "TitleCase colon" in out
        assert "generic colon line" in out or "contains dash" in out or "<other>" in out
        assert "—" in out


def test_analyze_common_prefixes_outputs_expected(capsys):
    data = {
        "meta": {"month": "2025-04"},
        "data": [],
        "skipped": [
            {"id": "1", "body": "* Razor: Blackbird\n* Blade: Feather"},
            {"id": "2", "body": "* Razor: Game Changer"},
            {"id": "3", "body": "* Brush: Simpson"},
            {"id": "4", "body": "* Brush: Zenith"},
            {"id": "5", "body": "* Soap: Tabac"},
            {"id": "6", "body": "* Soap: Arko"},
        ],
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "2025-04.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

        analyze_common_prefixes([path], show_examples=2)
        out = capsys.readouterr().out

        # Confirm expected full lines appear
        assert "* Razor: Blackbird" in out
        assert "* Brush: Simpson" in out
        assert "* Soap: Arko" in out

        # Extract only prefix summary lines for validation
        prefix_lines = [
            line for line in out.splitlines() if line.startswith("Prefix:") and "—" in line
        ]
        bucket_sizes = []
        for line in prefix_lines:
            parts = line.split("—")
            if len(parts) < 2:
                continue
            try:
                count = int(parts[1].strip().split()[0])
                bucket_sizes.append(count)
            except (IndexError, ValueError):
                continue

        # Validate sorting by: contains alias (True > False), then bucket size, then prefix length

        def sort_key(line):
            prefix = line.split("—")[0].replace("Prefix:", "").strip().lower()
            contains_alias = any(alias in prefix for alias in FIELD_ALIASES)
            length = len(prefix)
            try:
                count = int(line.split("—")[1].strip().split()[0])
            except (IndexError, ValueError):
                count = 0
            return (not contains_alias, -count, -length)

        sorted_prefix_lines = sorted(prefix_lines, key=sort_key)
        assert prefix_lines == sorted_prefix_lines
