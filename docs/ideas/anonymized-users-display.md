# Future enhancement: pseudonymize users on request (public site)

**Status: idea only — build when first requested.** No user has complained about
their SOTD history being aggregated; this documents the agreed remedy channel so
the response is fast if one ever does ("gets chirpy", 2026-10-25).

## The remedy

User asks to not be publicly identifiable → replace their username with a
stable alias in **public** API responses and UI, everywhere it renders
(e.g. `jimm262` → `shaver-01` or `shaver-7f3a`). Metrics are NOT removed —
shaves, users, ranks, all aggregates stay intact; only the identity mapping
is hidden. Admin build keeps real names.

## Mechanism (when built)

- `data/anonymized_users.yaml` operator-override file, matching the existing
  `thread_overrides.yaml` / `intentionally_unmatched.yaml` pattern:

  ```yaml
  # user -> stable display alias; metrics unaffected
  jimm262: shaver-01
  ```

- Applied at the public-API presentation layer (public build only), not the
  data/aggregation layer — pipeline data stays untouched.
- Aliases must be deterministic (sorted order or hash-based) so cross-page
  links stay coherent: monthly-user-posts ↔ product-usage user tables ↔
  report-placement deep links all reference the same alias for a given user.

## Known limits

- Pseudonymization, not anonymity: SOTD comment links still point at real
  Reddit comments, so re-identification via those links remains possible. For
  the realistic complaint ("don't show my name in your tables") this is
  sufficient. True anonymity would additionally mean dropping that user's
  comment links — higher cost, only if pushed.
- New aliases change table ordering visuals (a name swap, not counts).

## NOT chosen

- Removing the user's data: metrics would break for everyone.
- Reddit OAuth login gate on the public site: breaks shareability, protects
  nothing (data is public on Reddit already), and the site has no per-user
  features to pay for it.