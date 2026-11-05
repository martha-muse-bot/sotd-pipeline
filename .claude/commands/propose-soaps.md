---
description: Propose soap catalog candidates across months, then convert to soaps.yaml-shaped YAML
---

# Propose Soaps (one-shot)

One-shot soap catalog candidate flow:

1. Run **propose agents** for every requested month (`soap` field only).
2. After **all** months have `data/proposed/{MONTH}.json`, run **one** convert to YAML.

Do **not** modify `data/soaps.yaml`. Output YAML is for manual review/paste only.

## Arguments

`$ARGUMENTS` — parse these flags:

| Flag | Required | Notes |
|------|----------|--------|
| `--month YYYY-MM` | one of month/range | Single month |
| `--range YYYY-MM:YYYY-MM` | one of month/range | Inclusive span |
| `--force` | no | Passed through to the convert CLI |
| `--model sonnet\|haiku\|opus` | no | Default `sonnet`; passed to propose agents |

Rules:

- Exactly one of `--month` or `--range` is required. If neither (or both), stop with an error.
- If `--model` is present and not one of `sonnet`, `haiku`, `opus`, stop with an error.

## Step 0: Resolve months

Activate the project venv if needed (`source .venv/bin/activate`).

Resolve the ordered month list with Python (do not invent months by hand).

If `--month YYYY-MM` was given:

```bash
python -c "from sotd.match.tools.proposed_soaps_to_yaml import months_for_args; print('\n'.join(months_for_args(month='YYYY-MM', range_str=None)))"
```

If `--range START:END` was given:

```bash
python -c "from sotd.match.tools.proposed_soaps_to_yaml import months_for_args; print('\n'.join(months_for_args(month=None, range_str='START:END')))"
```

Substitute the real month/range values from `$ARGUMENTS`.

Print the resolved plan:

```
Running propose-soaps
  Months: {comma-separated YYYY-MM list}
  Mode:   propose (soap only)
  Model:  {MODEL}
  Convert: once after all proposals
  Force:  {yes|no}
```

For each month, confirm `data/matched/{MONTH}.json` exists. If any are missing, list them and stop **before** proposing.

## Step 1: Propose across all months (agents first)

For **each** month in order, execute the full orchestrator in `.claude/commands/validate-matches.md` as if the user had run:

```text
/validate-matches --month {MONTH} --mode propose --field soap --model {MODEL}
```

Constraints for this one-shot:

- Always `--mode propose` and `--field soap` (do not widen to other fields).
- Complete **all** months' propose runs before any YAML convert.
- Do not interleave convert between months.
- If a month's propose fails, report it and continue with remaining months when safe.

After each month, confirm `data/proposed/{MONTH}.json` exists and print its proposal count.

## Step 2: Single convert pass

After Step 1 finishes for every month, run **one** convert using the same `--month` or `--range` the user passed (do not issue per-month convert calls):

If the user passed `--month`:

```bash
python -m sotd.match.tools.proposed_soaps_to_yaml --month {MONTH} [--force]
```

→ writes `data/proposed/soaps/{MONTH}.yaml`

If the user passed `--range`:

```bash
python -m sotd.match.tools.proposed_soaps_to_yaml --range {START}:{END} [--force]
```

→ merges all months into **one** `data/proposed/soaps.yaml`

Include `--force` only when the user passed it.

Missing `data/proposed/{MONTH}.json` files are reported on stderr; present months are still merged (exit `1` if any were missing). Print the CLI stdout/stderr.

## Step 3: Wrap up

Remind the user:

- Review `data/proposed/soaps.yaml` (range) or `data/proposed/soaps/{MONTH}.yaml` (single month).
- Copy accepted brands/scents into `data/soaps.yaml` manually.
- This command never edits `data/soaps.yaml`.

## Contrast

| Command | What it does |
|---------|----------------|
| `/propose-soaps` | Propose agents (soap) across months, **then** one YAML convert |
| `/propose-soaps-yaml` | Convert existing `data/proposed/*.json` only (no agents) |
| `/validate-matches --mode propose` | Propose JSON only (any fields); no YAML convert |
