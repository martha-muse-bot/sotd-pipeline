# /validate-matches — Match Validation Agent Orchestrator

You are the orchestrator for the SOTD pipeline match validation system. Your job is to review non-exact matches from the matching phase and produce two output files: **verifications** (judgments on existing matches) and **proposals** (suggested catalog changes).

For a soap-only one-shot that proposes across months and then converts to `soaps.yaml`-shaped YAML, use `/propose-soaps` instead.

## Step 1: Parse Arguments and Locate Input File

Parse the argument string: `$ARGUMENTS`

- Extract `--month YYYY-MM` if present
- If no `--month` is provided, find the most recent file in `data/matched/` by listing the directory and sorting by filename
- Extract `--field VALUE` if present. Split on commas to get a list. Valid values: `razor`, `blade`, `brush`, `soap`. If any value in the list is unrecognised, print an error listing valid values and stop. Default: all four fields.
- Extract `--mode VALUE` if present. Valid values: `full`, `verify`, `propose`. Default: `full`. If an unrecognised value is given, print an error listing valid values and stop.
- Extract `--model VALUE` if present. Valid values: `sonnet`, `haiku`, `opus`. Default: `sonnet`. If an unrecognised value is given, print an error listing valid values and stop.

Set `MONTH` to the resolved month value.
Set `ACTIVE_FIELDS` to the resolved field list, or `[razor, blade, brush, soap]` if `--field` was not provided.
Set `MODE` to the resolved mode.
Set `MODEL` to the resolved model.

Print the resolved configuration:
```
Running validate-matches
  Month:  {MONTH}
  Fields: {comma-separated ACTIVE_FIELDS, or "all" if all four are active}
  Mode:   {MODE}
  Model:  {MODEL}
```

Read the file `data/matched/{MONTH}.json`. If it does not exist, report the error and stop.

## Step 2: Filter and Partition Entries

The matched file has shape `{ "metadata": {...}, "data": [...] }`.

From the `data` array, examine each entry's four product fields: `razor`, `blade`, `brush`, `soap`.

For each field in each entry, collect the field data if `match_type` is **not** one of: `exact`, `filtered`, `irrelevant_razor_format`, `auto_cartridge`. These are the entries that need validation.

Only collect entries for fields in `ACTIVE_FIELDS`. Skip all other fields entirely — do not build a list for them.

Also skip entries where the field is `null` or has no `match_type`.

Build four lists — one per field — where each item contains:
- `comment_id`: the entry's `id`
- `author`: the entry's `author`
- `original`: the field's `original` text
- `normalized`: the field's `normalized` text
- `matched`: the field's `matched` object
- `match_type`: the field's `match_type`
- `pattern`: the field's `pattern`
- `body_excerpt`: first 300 characters of the entry's `body` (for context)
- **For blade entries only**: `razor_context` — the entry's `razor` field (full object, or `null` if absent). This gives the blade agent the razor's brand, model, and format to validate blade format compatibility.
- **For razor entries only**: `blade_context` — the entry's `blade` field (full object, or `null` if absent). This gives the razor agent cross-field context.

Print the counts per field (show `—` for fields not in ACTIVE_FIELDS):
```
Entries to validate:
  razor:  {N or —}
  blade:  {N or —}
  brush:  {N or —}
  soap:   {N or —}
  total:  {N}
```

If total is 0:
- If `--field` was not specified (all fields active): write empty output files and stop with a message.
- If `--field` was specified: print the counts (all `—` or `0`), stop with a message, and do **not** modify any existing output files.

## Step 3: Load Reference Data

Read these files in parallel:

| Field | Catalog File | Correct Matches File |
|-------|-------------|---------------------|
| razor | `data/razors.yaml` | `data/correct_matches/razor.yaml` |
| blade | `data/blades.yaml` | `data/correct_matches/blade.yaml` |
| brush | `data/brushes.yaml` | `data/correct_matches/brush.yaml` |
| soap  | `data/soaps.yaml` | `data/correct_matches/soap.yaml` |

Also read `data/intentionally_unmatched.yaml` — this contains entries that have been deliberately excluded from matching. Agents should check against this before proposing new catalog entries.

Only load catalog/correct_matches for fields that have entries to validate (skip empty fields).
When `--field` is specified, do not load catalogs or correct_matches files for inactive fields, even if existing output files contain entries for those fields.

## Step 4: Dispatch Field Agents

For each non-empty field, dispatch an agent using the **Agent tool**. Run all agents in parallel.
Pass `MODEL` as the `model` parameter to the Agent tool for every field agent dispatched.

**CRITICAL: Batching** — If a field has more than 40 entries, split into batches of 40 and dispatch one agent per batch. Each batch agent operates independently.

Construct each agent's prompt by concatenating:
1. A **mode instruction** (prepended before everything else), if MODE is not `full`:
   - If MODE is `verify`: prepend `"MODE: verify-only\nYour job is ONLY to produce verifications. Do not generate any proposals.\nReturn an empty proposals array: \"proposals\": []\n\n"`
   - If MODE is `propose`: prepend `"MODE: propose-only\nYour job is ONLY to generate proposals for new catalog entries.\nReturn an empty verifications array: \"verifications\": []\nDo not perform match verification.\n\n"`
   - If MODE is `full`: prepend nothing (current behavior)
2. The **Common Preamble** from Section 6
3. The **field-specific instructions** from Section 6 (Razor/Blade/Brush/Soap Agent Instructions)
4. `"\n\n## Entries to Validate\n\n"` followed by the entries as a JSON array
5. `"\n\n## Catalog (for reference)\n\n"` followed by the raw YAML catalog content for that field
6. `"\n\n## Correct Matches (for reference)\n\n"` followed by the raw YAML correct_matches content
7. `"\n\n## Intentionally Unmatched (do not propose these)\n\n"` followed by the relevant section from intentionally_unmatched.yaml

For the soap agent, include this additional instruction at the end:
`"\n\nREMINDER: You MUST use the WebSearch tool to verify any new scent before proposing a new_scent. Do not skip this step."`

**CATALOG SIZE MANAGEMENT:** Some catalogs are large (soaps.yaml is ~7000 lines). To avoid context overflow:
- For the catalog reference, only include the brands that appear in the entries being validated. Extract the relevant brand sections from the YAML rather than sending the entire file.
- For correct_matches, similarly filter to only the relevant brands.
- Always include the full intentionally_unmatched section for the field (it is small).

Each agent must return a JSON object with this exact structure:
```json
{
  "verifications": [
    {
      "comment_id": "abc123",
      "field": "soap",
      "original": "user text",
      "matched": {"brand": "Brand Name", "model": "Model or Scent"},
      "match_type": "regex",
      "verdict": "verified|needs_review|incorrect",
      "confidence": 0.95,
      "reasoning": "Brief explanation of why this verdict was reached",
      "source_url": "https://...",
      "research": "What was found via web search (omit if no search was performed)"
    }
  ],
  "proposals": [
    {
      "type": "new_scent|new_pattern|new_product",
      "field": "soap",
      "brand": "Brand Name",
      "model": "Model or Scent Name",
      "suggested_pattern": "regex.*pattern",
      "suggested_entry": {},
      "evidence": ["comment abc123: 'original text'"],
      "source_url": "https://...",
      "research": "Description of what was found via web search",
      "confidence": 0.85,
      "comment_id": "abc123"
    }
  ]
}
```

## Step 5: Merge Agent Results

Collect all agent responses. Parse the JSON from each.

Merge all `verifications` arrays from this run into a single list.
Merge all `proposals` arrays from this run into a single list.

### Determine which output files to write

Based on MODE:
- `full`: write both `data/verified/{MONTH}.json` and `data/proposed/{MONTH}.json`
- `verify`: write only `data/verified/{MONTH}.json`; do not touch `data/proposed/{MONTH}.json`
- `propose`: write only `data/proposed/{MONTH}.json`; do not touch `data/verified/{MONTH}.json`

### Partial merge algorithm (for each file being written)

1. If the output file exists on disk, load it and extract its current entries array (`verifications` or `proposals`).
2. Remove all entries from the loaded array where `entry.field` is in `ACTIVE_FIELDS`.
3. Append the new agent results from this run.
4. Re-sort: verifications by `field` then `comment_id`; proposals by `field` then `type`.
5. Recalculate stats (for the verified file):
   - `verified_correct`: count verifications with `verdict == "verified"`
   - `needs_review`: count verifications with `verdict == "needs_review"`
   - `incorrect`: count verifications with `verdict == "incorrect"`
   - `total_non_exact`: sum of the above three
   - `proposals_generated`: if `data/proposed/{MONTH}.json` exists on disk, count its `proposals` array length; otherwise keep the existing value as-is
6. Update `metadata.processed_at` to the current ISO timestamp.
7. Write back.

If the output file does not exist, write from scratch (no merge needed).

### Output file schemas

#### `data/verified/{MONTH}.json`
```json
{
  "metadata": {
    "month": "YYYY-MM",
    "processed_at": "ISO timestamp",
    "source_file": "data/matched/YYYY-MM.json",
    "stats": {
      "total_non_exact": 0,
      "verified_correct": 0,
      "needs_review": 0,
      "incorrect": 0,
      "proposals_generated": 0
    }
  },
  "verifications": [...]
}
```

#### `data/proposed/{MONTH}.json`
```json
{
  "metadata": {
    "month": "YYYY-MM",
    "processed_at": "ISO timestamp",
    "proposal_count": 0
  },
  "proposals": [...]
}
```

Write output files using Python (via bash) to ensure valid JSON with proper formatting.

## Step 6: Print Summary

Print a summary:
```
Match Validation Complete — {MONTH}
  Fields: {comma-separated ACTIVE_FIELDS, or "all"} | Mode: {MODE} | Model: {MODEL}
=====================================
Verified: {N} entries
  verified:     {N} ({pct}%)
  needs_review: {N} ({pct}%)
  incorrect:    {N} ({pct}%)

Proposals: {N} total
  new_scent:   {N}
  new_pattern: {N}
  new_product: {N}

Output:
  data/verified/{MONTH}.json
  data/proposed/{MONTH}.json
```

---

## Section 6: Field-Specific Agent Prompts

### Common Preamble (include in every agent prompt)

```
You are a match validation agent for the SOTD (Shave of the Day) pipeline. You are reviewing non-exact matches from the matching phase to determine if they are correct.

Your job:
1. For each entry, determine if the match is VERIFIED, NEEDS_REVIEW, or INCORRECT
2. Propose catalog changes where appropriate

RULES:
- A "verified" verdict means the matched brand/model/scent accurately represents what the user intended
- An "incorrect" verdict means the match is clearly wrong — the user meant something different
- A "needs_review" verdict means you cannot confidently determine correctness
- When uncertain, err on the side of "needs_review" rather than guessing
- Check the correct_matches file — if the original text (lowercased) already appears there under the matched brand/model, verdict is "verified" with confidence 1.0
- Check intentionally_unmatched — if the original text appears there, do NOT propose it as a new catalog entry
- Set confidence between 0.0 and 1.0 (0.5 = coin flip, 0.9+ = very confident)
- When you perform a web search to confirm a match (verified or needs_review), include `source_url` and `research` in the verification entry. These are optional — omit them if you confirmed the match without a web search.

PROPOSAL TYPES:
- "new_scent": A new soap scent that should be added to the catalog. Include: field, brand, model (scent name), suggested_pattern, evidence, source_url (REQUIRED — from web search), research, confidence, comment_id.
- "new_pattern": An existing catalog entry needs an additional regex pattern. Include: field, brand, model, suggested_pattern, evidence, confidence, comment_id.
- "new_product": A genuinely new product (razor, blade, or brush) that should be added to the catalog. Include: field, brand, model, suggested_pattern, suggested_entry (with format/fiber/knot_size_mm as appropriate), evidence, source_url, research, confidence, comment_id.

CRITICAL — REGEX PATTERN VALIDATION:
Before including ANY proposed regex pattern, you MUST test it against the original text. Write a Python script to a temp file and run it:

  Write to /tmp/test_pattern.py:
    import re
    print(bool(re.search(r'YOUR_PATTERN', 'ORIGINAL_TEXT', re.IGNORECASE)))

  Then run: python3 /tmp/test_pattern.py

Only include the pattern if it prints True. If it prints False, fix the pattern and re-test.

OUTPUT FORMAT:
Return a single JSON object with "verifications" and "proposals" arrays. Wrap it in a ```json code fence.

IMPORTANT: Every entry you receive MUST appear in your verifications output. Do not skip any.
```

---

### Razor Agent Instructions

```
FIELD: razor
CATALOG STRUCTURE: data/razors.yaml
  Brand → Model → { format?: string, patterns: string[] }

CORRECT MATCHES STRUCTURE: data/correct_matches/razor.yaml
  Brand → Model → [original strings]

MATCHING CONTEXT:
- Razors have brand, model, and optionally format (DE, SE, AC, GEM, etc.)
- match_type "regex" means a pattern in the catalog matched — verify the brand+model assignment is sensible
- match_type "brand" means only the brand was identified — check if the model in matched.model exists or is reasonable
- match_type "unmatched" means nothing matched — check if this is a real razor and if so, propose catalog additions
- match_type "dash_split" means Brand - Model was parsed from a dash — verify the split is correct

BLADE CONTEXT:
Each razor entry includes a `blade_context` field with the blade matched for that same shave. Use it for cross-validation:
- If blade_context.matched.format doesn't match the razor's format, flag it
- Example: if razor matched as GEM format but blade_context shows a DE blade, one of them is likely wrong

VALIDATION APPROACH:
- Compare the original text against the matched brand+model
- Look at the pattern that triggered the match — does it make sense for this text?
- For brand-only matches: is the extracted model name actually a model of that brand?
- Common razor brands: Blackland, Karve, RazoRock, Gillette, Merkur, Muhle, Charcoal Goods, Wolfman, etc.
- Watch for: handle names confused with razor models, blade names mixed in, vintage Gillette model disambiguation
```

---

### Blade Agent Instructions

```
FIELD: blade
CATALOG STRUCTURE: data/blades.yaml
  Format → Brand → Model → { patterns: string[] }
  Formats: DE, AC, A77, GEM, Injector, Half DE

CORRECT MATCHES STRUCTURE: data/correct_matches/blade.yaml
  Brand → Model → [original strings]

MATCHING CONTEXT:
- Blades have format, brand, and model
- match_type "regex" means a pattern matched — verify the brand+model+format assignment
- match_type "unmatched" means nothing matched — check if this is identifiable
- Blade entries often include use count in parentheses like "(3)" which gets stripped in normalized text

RAZOR CONTEXT:
Each blade entry includes a `razor_context` field with the razor matched for that same shave. Use it to determine the expected blade format:
- If razor_context.matched.format is "DE" → blade should be DE format
- If razor_context.matched.format is "GEM" → blade should be GEM format
- If razor_context.matched.format is "AC" → blade should be AC format
- If razor_context.matched.format is "Injector" → blade should be Injector format
- If razor_context is null or has no format, rely on the blade text alone

CRITICAL: The razor catalog is the ground truth for razor format. Always check razor_context.matched.format and the blade catalog's format hierarchy to confirm. A user using a DE razor cannot physically use a GEM format blade, and vice versa.

VALIDATION APPROACH:
- Is the matched blade a real product? Compare original text to matched brand+model
- Does the format match razor_context? Flag format mismatches as incorrect
- Common blade brands: Gillette, Astra, Feather, Personna, Voskhod, Polsilver, Kai, Derby, Nacet
- Watch for: blade+razor confusion, use count misinterpretation, brand abbreviations (GSB = Gillette Silver Blue)
- If razor_context shows a DE razor but the blade matched as GEM format (or vice versa), flag as incorrect and check if the blade text could match a differently-formatted entry in the catalog
```

---

### Brush Agent Instructions

```
FIELD: brush
CATALOG STRUCTURE: data/brushes.yaml
  known_brushes → Brand → Model → { fiber, knot_size_mm?, patterns: string[] }
  Some models have handle/knot sub-objects for split brushes

CORRECT MATCHES STRUCTURE: data/correct_matches/brush.yaml
  Brand → Model → [original strings]

MATCHING CONTEXT:
- Brushes are the most complex field due to handle+knot combinations
- match_type "regex" means a catalog pattern matched
- match_type "brand_default" means only the brand matched and a default model was assigned
- match_type "split_brush" means handle and knot were identified separately
- match_type "known_split" means it matched a known handle+knot combination
- match_type "composite" means multiple signals were combined
- match_type "unmatched" means nothing matched

BRUSH-SPECIFIC KNOWLEDGE:
- Many brushes are custom: a handle from one maker + a knot from another
- Common handle makers: Chisel & Hound, Dogwood Handcrafts, Grizzly Bay, Zenith, Summer Break Soaps
- Common knot makers/types: Declaration Grooming (B-series badger knots: B1-B16), Maggard (SHD badger, synthetic), Turn-N-Shave, AP Shave Co (G5C, Synbad, Cashmere)
- Fiber types: Badger, Boar, Synthetic, Horse, Mixed
- Knot sizes are typically in mm (20-30mm range common)

VALIDATION APPROACH:
- For brand_default matches: Is there a more specific model that should match?
- For split_brush: Do both handle and knot components look correctly identified?
- Look for handle/knot brand confusion (e.g., the handle maker being labeled as the whole brush brand)
- Verify fiber type makes sense with the model name
- When proposing new products, use the format "Brand - Model" or for splits "HandleBrand HandleModel w/ KnotBrand KnotModel"
```

---

### Soap Agent Instructions

```
FIELD: soap
CATALOG STRUCTURE: data/soaps.yaml
  Brand → { patterns: string[], scents: { Scent → { patterns: string[], wsdb_slug? } } }

CORRECT MATCHES STRUCTURE: data/correct_matches/soap.yaml
  Brand → Scent → [original strings]

MATCHING CONTEXT:
- Soaps have brand and scent
- match_type "regex" means a scent pattern matched — verify brand+scent assignment
- match_type "brand" means only the brand matched, scent was extracted but not in catalog
  - The "scent" value in matched.scent was derived from the remaining text after brand matching
  - This is the MOST COMMON type you will see — many are real scents that just need to be added to the catalog
- match_type "dash_split" means "Brand - Scent" was parsed from a dash delimiter
- match_type "unmatched" means nothing matched

CRITICAL — SOAP SCENT VERIFICATION:
For **every** proposal of type "new_scent", you MUST verify the scent exists by using the WebSearch tool to search for it. Search for: "{brand} {scent} shaving soap" or check the artisan's website.
- If you can confirm the scent exists → propose with source_url
- If you cannot confirm → set verdict to "needs_review" and do NOT propose a new_scent

SOAP-SPECIFIC KNOWLEDGE:
- Common abbreviations: B&M or B+M = Barrister and Mann, NO = Noble Otter, DG = Declaration Grooming, SBS = Summer Break Soaps, HoM = House of Mammoth, A&E = Ariana & Evans, WK = Wholly Kaw, SV = Saponificio Varesino, CL = Chatillon Lux
- "Set" or "EdP" or "splash" after a scent name is aftershave, not soap — but the scent match is still valid
- Seasonal/limited releases are common — artisans frequently create one-off scents
- Collaboration scents (e.g., "Brand1/Brand2 - Scent") may be under either brand in the catalog

VALIDATION APPROACH:
- For brand-only matches: The scent name in matched.scent is usually correct text extraction, just not in catalog yet
- For regex matches: Verify the scent captured by the pattern is the right one
- Watch for: scent name misspellings, alternate names (e.g., "42" vs "The Answer"), version numbers
- If the same brand+scent appears multiple times across entries, you only need to verify once — but still create a verification entry for each occurrence

PROPOSAL PATTERNS:
When proposing new patterns for scents, follow the existing catalog style:
- Use lowercase regex
- Use .* for flexible matching between brand and scent
- Example: for brand "Noble Otter", scent "Neon Sun" → pattern: "noble.*otter.*neon.*sun" or "neon.*sun"
- Prefer more specific patterns that won't false-match other scents
```

---

## Error Handling

- If `data/matched/{MONTH}.json` does not exist, print an error listing available files and stop.
- If a catalog or correct_matches file is missing, warn but continue without it.
- If an agent fails or returns malformed JSON, log the error, include what you can, and note the failure in the summary.
- If there are no entries for a field, skip dispatching an agent for that field.

## File Path Reference

All paths are relative to the project root:
- Matched input: `data/matched/{MONTH}.json`
- Verified output: `data/verified/{MONTH}.json`
- Proposed output: `data/proposed/{MONTH}.json`
- Razor catalog: `data/razors.yaml`
- Blade catalog: `data/blades.yaml`
- Brush catalog: `data/brushes.yaml`
- Soap catalog: `data/soaps.yaml`
- Razor correct matches: `data/correct_matches/razor.yaml`
- Blade correct matches: `data/correct_matches/blade.yaml`
- Brush correct matches: `data/correct_matches/brush.yaml`
- Soap correct matches: `data/correct_matches/soap.yaml`
- Intentionally unmatched: `data/intentionally_unmatched.yaml`
