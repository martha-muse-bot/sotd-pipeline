---
description: Convert proposed soap JSON into soaps.yaml-shaped YAML for copy/paste
---

# Propose Soaps YAML

Convert `data/proposed/YYYY-MM.json` into a catalog-shaped YAML fragment for manual review and paste into `data/soaps.yaml`.

This is a **thin wrapper** around a deterministic Python CLI. Do **not** dispatch agents, run web search, or modify `data/soaps.yaml`.

## Arguments

`$ARGUMENTS` — expected: `--month YYYY-MM` **or** `--range YYYY-MM:YYYY-MM` (optional `--force`)

Parse `--month` or `--range`. If neither is present, stop with an error.

## Steps

1. Activate the project venv if needed (`source .venv/bin/activate`).
2. Run one of:

```bash
python -m sotd.match.tools.proposed_soaps_to_yaml --month {MONTH} [--force]
# → data/proposed/soaps/{MONTH}.yaml

python -m sotd.match.tools.proposed_soaps_to_yaml --range {START}:{END} [--force]
# → data/proposed/soaps.yaml (merged across months)
```

3. Print the CLI stdout (output path + counts).
4. Remind the user: review the written YAML, then copy accepted brands/scents into `data/soaps.yaml`.

## Contrast

- `/propose-soaps` — one-shot: propose agents (soap) across months, **then** one YAML convert
- `/validate-matches --mode propose` — LLM agents produce `data/proposed/YYYY-MM.json` only
- `/propose-soaps-yaml` — converts that JSON into paste-friendly YAML (no LLM)
