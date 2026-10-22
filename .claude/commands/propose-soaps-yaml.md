---
description: Convert proposed soap JSON into soaps.yaml-shaped YAML for copy/paste
---

# Propose Soaps YAML

Convert `data/proposed/YYYY-MM.json` into a catalog-shaped YAML fragment for manual review and paste into `data/soaps.yaml`.

This is a **thin wrapper** around a deterministic Python CLI. Do **not** dispatch agents, run web search, or modify `data/soaps.yaml`.

## Arguments

`$ARGUMENTS` — expected: `--month YYYY-MM` (optional `--force`)

Parse `--month`. If missing, stop with an error.

## Steps

1. Activate the project venv if needed (`source .venv/bin/activate`).
2. Run:

```bash
python -m sotd.match.tools.proposed_soaps_to_yaml --month {MONTH} [--force]
```

3. Print the CLI stdout (output path + counts).
4. Remind the user: edit `data/proposed/soaps/{MONTH}.yaml`, then copy accepted brands/scents into `data/soaps.yaml`.

## Contrast with `/validate-matches`

- `/validate-matches --mode propose` — LLM agents produce `data/proposed/YYYY-MM.json`
- `/propose-soaps-yaml` — converts that JSON into paste-friendly YAML (no LLM)
