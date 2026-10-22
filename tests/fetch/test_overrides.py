"""Unit tests for YAML thread include/exclude overrides."""

from pathlib import Path
from unittest.mock import Mock

from sotd.fetch.overrides import (
    apply_thread_excludes,
    extract_thread_id_from_url,
    load_thread_exclude_ids,
    load_thread_overrides_data,
)


def test_extract_thread_id_from_url() -> None:
    assert (
        extract_thread_id_from_url(
            "https://www.reddit.com/r/Wetshaving/comments/1lk3ooa/wednesday_sotd_25_june/"
        )
        == "1lk3ooa"
    )
    assert (
        extract_thread_id_from_url(
            "https://www.reddit.com/r/Wetshaving/comments/1ttrafo/comment/op4r7jq/"
        )
        == "1ttrafo"
    )
    assert extract_thread_id_from_url("/r/wetshaving/comments/abc123/") == "abc123"
    assert extract_thread_id_from_url("not-a-url") is None
    assert extract_thread_id_from_url("") is None


def test_load_thread_exclude_ids(tmp_path: Path) -> None:
    path = tmp_path / "thread_overrides.yaml"
    path.write_text("""
include: {}
exclude:
  2026-06-01:
    - https://www.reddit.com/r/Wetshaving/comments/1ttrafo/monday_lather_games/
  2026-06-02:
    - https://www.reddit.com/r/Wetshaving/comments/otherid/other/
  2026-07-01:
    - https://www.reddit.com/r/Wetshaving/comments/julyid/july/
""")
    assert load_thread_exclude_ids("2026-06", path) == {"1ttrafo", "otherid"}
    assert load_thread_exclude_ids("2026-07", path) == {"julyid"}
    assert load_thread_exclude_ids("2025-01", path) == set()


def test_load_thread_exclude_ids_skips_bad_urls(tmp_path: Path, caplog) -> None:
    path = tmp_path / "thread_overrides.yaml"
    path.write_text("""
exclude:
  2026-06-01:
    - not-a-reddit-url
    - https://www.reddit.com/r/Wetshaving/comments/goodid/title/
""")
    with caplog.at_level("WARNING"):
        ids = load_thread_exclude_ids("2026-06", path)
    assert ids == {"goodid"}
    assert "Could not extract thread id" in caplog.text


def test_load_thread_exclude_ids_missing_file(tmp_path: Path) -> None:
    assert load_thread_exclude_ids("2026-06", tmp_path / "missing.yaml") == set()


def test_load_thread_exclude_ids_missing_exclude_key(tmp_path: Path) -> None:
    path = tmp_path / "thread_overrides.yaml"
    path.write_text("""
include:
  2025-06-25:
    - https://www.reddit.com/r/Wetshaving/comments/1lk3ooa/wednesday/
""")
    assert load_thread_exclude_ids("2025-06", path) == set()


def test_apply_thread_excludes_praw_and_dict() -> None:
    keep = Mock(id="keep")
    drop = Mock(id="1ttrafo")
    assert [t.id for t in apply_thread_excludes([keep, drop], {"1ttrafo"})] == ["keep"]

    threads = [{"id": "keep"}, {"id": "1ttrafo"}, {"id": "t3_other"}]
    result = apply_thread_excludes(threads, {"1ttrafo", "t3_other"})
    assert result == [{"id": "keep"}]


def test_apply_thread_excludes_empty_set_noop() -> None:
    threads = [{"id": "a"}, {"id": "b"}]
    assert apply_thread_excludes(threads, set()) == threads


def test_warn_on_legacy_root_date_keys(tmp_path: Path, caplog) -> None:
    path = tmp_path / "thread_overrides.yaml"
    path.write_text("""
2025-06-25:
  - https://www.reddit.com/r/Wetshaving/comments/1lk3ooa/wednesday/
""")
    with caplog.at_level("WARNING"):
        data = load_thread_overrides_data(path)
    keys = {k.isoformat() if hasattr(k, "isoformat") else str(k) for k in data}
    assert "2025-06-25" in keys
    assert "Legacy thread override schema" in caplog.text


def test_include_loader_reads_include_section_only(tmp_path: Path, monkeypatch) -> None:
    import sotd.fetch.overrides as overrides_mod
    from sotd.fetch.reddit import load_thread_overrides

    path = tmp_path / "thread_overrides.yaml"
    path.write_text("""
include:
  2025-06-25:
    - https://www.reddit.com/r/Wetshaving/comments/includeid/inc/
exclude:
  2025-06-25:
    - https://www.reddit.com/r/Wetshaving/comments/excludeid/exc/
2025-06-26:
  - https://www.reddit.com/r/Wetshaving/comments/legacyid/leg/
""")
    monkeypatch.setattr(overrides_mod, "OVERRIDE_PATH", path)

    urls = load_thread_overrides("2025-06")
    assert urls == ["https://www.reddit.com/r/Wetshaving/comments/includeid/inc/"]
    assert "legacyid" not in "".join(urls)
    assert "excludeid" not in "".join(urls)
