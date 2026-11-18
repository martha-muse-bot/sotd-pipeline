import json
import tempfile
from pathlib import Path

from sotd.extract.save import save_month_file


def test_save_extraction_result_writes_file_correctly():
    result = {
        "meta": {"month": "2025-04", "comment_count": 1},
        "data": [
            {"id": "abc123", "body": "* **Razor:** Blackbird", "extracted": {"razor": "Blackbird"}}
        ],
        "skipped": [],
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir) / "data/extracted"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "2025-04.json"

        save_month_file("2025-04", result, out_dir=out_dir)

        with open(out_file, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            assert loaded == result
