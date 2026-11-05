"""Unit tests for proposed JSON → soaps.yaml-shaped YAML converter."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from sotd.match.tools.proposed_soaps_to_yaml import (
    build_catalog_fragment,
    convert_proposed_file,
    filter_soap_proposals,
    main,
    months_for_args,
    parse_month_range,
)


def _proposal(
    *,
    brand: str = "Noble Otter",
    model: str = "Neon Sun",
    pattern: str = "neon.*sun",
    ptype: str = "new_scent",
    field: str = "soap",
    status: str | None = None,
) -> dict:
    prop: dict = {
        "type": ptype,
        "field": field,
        "brand": brand,
        "model": model,
        "suggested_pattern": pattern,
        "comment_id": "abc123",
    }
    if status is not None:
        prop["_status"] = status
    return prop


class TestFilterSoapProposals:
    def test_keeps_new_scent_and_new_pattern(self) -> None:
        proposals = [
            _proposal(ptype="new_scent"),
            _proposal(ptype="new_pattern", model="Orbit", pattern="orbit"),
            _proposal(ptype="new_product", brand="X", model="Y", pattern="x.*y"),
        ]
        kept = filter_soap_proposals(proposals)
        assert len(kept) == 2
        assert {p["type"] for p in kept} == {"new_scent", "new_pattern"}

    def test_skips_non_soap_field(self) -> None:
        kept = filter_soap_proposals([_proposal(field="razor")])
        assert kept == []

    def test_skips_accepted_and_rejected(self) -> None:
        proposals = [
            _proposal(status="accepted"),
            _proposal(model="Orbit", pattern="orbit", status="rejected"),
            _proposal(model="Barrbarr", pattern="barrbarr"),
        ]
        kept = filter_soap_proposals(proposals)
        assert len(kept) == 1
        assert kept[0]["model"] == "Barrbarr"

    def test_skips_missing_required_fields(self) -> None:
        proposals = [
            {"type": "new_scent", "field": "soap", "brand": "A", "model": "B"},
            {
                "type": "new_scent",
                "field": "soap",
                "brand": "",
                "model": "B",
                "suggested_pattern": "b",
            },
            {
                "type": "new_scent",
                "field": "soap",
                "brand": "A",
                "model": "B",
                "suggested_pattern": "b",
            },
        ]
        kept = filter_soap_proposals(proposals)
        assert len(kept) == 1


class TestBuildCatalogFragment:
    def test_nested_scents_structure(self) -> None:
        fragment = build_catalog_fragment(
            [
                _proposal(brand="Noble Otter", model="Neon Sun", pattern="neon.*sun"),
                _proposal(
                    brand="Løthur",
                    model="Oregon",
                    pattern="oregon",
                    ptype="new_scent",
                ),
            ]
        )
        assert fragment == {
            "Løthur": {"scents": {"Oregon": {"patterns": ["oregon"]}}},
            "Noble Otter": {"scents": {"Neon Sun": {"patterns": ["neon.*sun"]}}},
        }

    def test_merges_patterns_for_same_scent(self) -> None:
        fragment = build_catalog_fragment(
            [
                _proposal(pattern="neon.*sun"),
                _proposal(pattern="noble.*otter.*neon.*sun"),
                _proposal(pattern="neon.*sun"),  # duplicate
            ]
        )
        patterns = fragment["Noble Otter"]["scents"]["Neon Sun"]["patterns"]
        assert patterns == ["neon.*sun", "noble.*otter.*neon.*sun"]

    def test_new_pattern_same_shape_as_new_scent(self) -> None:
        fragment = build_catalog_fragment(
            [
                _proposal(
                    brand="Stirling Soap Co.",
                    model="Lampassas",
                    pattern="lampassas",
                    ptype="new_pattern",
                )
            ]
        )
        assert "patterns" not in fragment["Stirling Soap Co."]
        assert fragment["Stirling Soap Co."]["scents"]["Lampassas"]["patterns"] == ["lampassas"]


class TestConvertProposedFile:
    def test_writes_yaml_and_skips_actioned(self, tmp_path: Path) -> None:
        proposed = {
            "metadata": {"month": "2026-10"},
            "proposals": [
                _proposal(brand="A", model="One", pattern="one"),
                _proposal(brand="A", model="Two", pattern="two", status="accepted"),
                _proposal(field="blade", brand="B", model="X", pattern="x"),
            ],
        }
        in_path = tmp_path / "2026-10.json"
        out_path = tmp_path / "out" / "2026-10.yaml"
        in_path.write_text(json.dumps(proposed), encoding="utf-8")

        stats = convert_proposed_file(in_path, out_path, force=True)

        assert out_path.exists()
        data = yaml.safe_load(out_path.read_text(encoding="utf-8"))
        assert data == {"A": {"scents": {"One": {"patterns": ["one"]}}}}
        assert stats["scents"] == 1
        assert stats["brands"] == 1
        assert stats["proposals_used"] == 1

    def test_refuses_overwrite_without_force(self, tmp_path: Path) -> None:
        in_path = tmp_path / "2026-10.json"
        out_path = tmp_path / "2026-10.yaml"
        in_path.write_text(
            json.dumps({"proposals": [_proposal()]}),
            encoding="utf-8",
        )
        out_path.write_text("existing: true\n", encoding="utf-8")

        with pytest.raises(FileExistsError):
            convert_proposed_file(in_path, out_path, force=False)


class TestParseMonthRange:
    def test_expands_inclusive_range(self) -> None:
        assert parse_month_range("2026-10:2026-11") == ["2026-10", "2026-11"]

    def test_single_month_range(self) -> None:
        assert parse_month_range("2026-10:2026-10") == ["2026-10"]

    def test_rejects_invalid_format(self) -> None:
        with pytest.raises(ValueError, match="YYYY-MM:YYYY-MM"):
            parse_month_range("2026-10")


class TestMonthsForArgs:
    def test_month_only(self) -> None:
        assert months_for_args(month="2026-10", range_str=None) == ["2026-10"]

    def test_range_only(self) -> None:
        assert months_for_args(month=None, range_str="2026-10:2026-11") == [
            "2026-10",
            "2026-11",
        ]

    def test_requires_month_or_range(self) -> None:
        with pytest.raises(ValueError, match="--month or --range"):
            months_for_args(month=None, range_str=None)


class TestMainRange:
    def test_range_writes_single_merged_soaps_yaml(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        proposed_dir = tmp_path / "proposed"
        proposed_dir.mkdir()
        for month, model in (("2026-10", "OctScent"), ("2026-11", "NovScent")):
            (proposed_dir / f"{month}.json").write_text(
                json.dumps({"proposals": [_proposal(model=model, pattern=model.lower())]}),
                encoding="utf-8",
            )

        rc = main(
            [
                "--range",
                "2026-10:2026-11",
                "--data-dir",
                str(tmp_path),
                "--force",
            ]
        )
        assert rc == 0
        out_path = proposed_dir / "soaps.yaml"
        assert out_path.exists()
        assert not (proposed_dir / "soaps" / "2026-10.yaml").exists()
        data = yaml.safe_load(out_path.read_text(encoding="utf-8"))
        assert "OctScent" in data["Noble Otter"]["scents"]
        assert "NovScent" in data["Noble Otter"]["scents"]
        captured = capsys.readouterr().out
        assert "soaps.yaml" in captured

    def test_range_merges_patterns_across_months(self, tmp_path: Path) -> None:
        proposed_dir = tmp_path / "proposed"
        proposed_dir.mkdir()
        (proposed_dir / "2026-10.json").write_text(
            json.dumps({"proposals": [_proposal(pattern="neon.*sun")]}),
            encoding="utf-8",
        )
        (proposed_dir / "2026-11.json").write_text(
            json.dumps(
                {
                    "proposals": [
                        _proposal(pattern="noble.*otter.*neon.*sun"),
                        _proposal(model="Orbit", pattern="orbit"),
                    ]
                }
            ),
            encoding="utf-8",
        )

        assert (
            main(
                [
                    "--range",
                    "2026-10:2026-11",
                    "--data-dir",
                    str(tmp_path),
                    "--force",
                ]
            )
            == 0
        )
        data = yaml.safe_load((proposed_dir / "soaps.yaml").read_text(encoding="utf-8"))
        assert data["Noble Otter"]["scents"]["Neon Sun"]["patterns"] == [
            "neon.*sun",
            "noble.*otter.*neon.*sun",
        ]
        assert data["Noble Otter"]["scents"]["Orbit"]["patterns"] == ["orbit"]

    def test_range_skips_missing_and_still_merges(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        proposed_dir = tmp_path / "proposed"
        proposed_dir.mkdir()
        (proposed_dir / "2026-11.json").write_text(
            json.dumps({"proposals": [_proposal(model="NovScent", pattern="novscent")]}),
            encoding="utf-8",
        )

        rc = main(
            [
                "--range",
                "2026-10:2026-11",
                "--data-dir",
                str(tmp_path),
                "--force",
            ]
        )
        assert rc == 1
        out_path = proposed_dir / "soaps.yaml"
        assert out_path.exists()
        data = yaml.safe_load(out_path.read_text(encoding="utf-8"))
        assert "NovScent" in data["Noble Otter"]["scents"]
        err = capsys.readouterr().err
        assert "2026-10" in err

    def test_range_rejects_in_override(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = main(
            [
                "--range",
                "2026-10:2026-11",
                "--in",
                "x.json",
            ]
        )
        assert rc == 2
        assert "--in" in capsys.readouterr().err

    def test_range_allows_out_override(self, tmp_path: Path) -> None:
        proposed_dir = tmp_path / "proposed"
        proposed_dir.mkdir()
        (proposed_dir / "2026-10.json").write_text(
            json.dumps({"proposals": [_proposal()]}),
            encoding="utf-8",
        )
        custom = tmp_path / "custom.yaml"
        rc = main(
            [
                "--range",
                "2026-10:2026-10",
                "--data-dir",
                str(tmp_path),
                "--out",
                str(custom),
                "--force",
            ]
        )
        assert rc == 0
        assert custom.exists()
        assert not (proposed_dir / "soaps.yaml").exists()
