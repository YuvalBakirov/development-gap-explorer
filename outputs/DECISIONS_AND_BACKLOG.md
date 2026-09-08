# Decisions and future improvements

## Current reliability and publication policy

The pipeline never silently alters a source observation. Missing values remain
missing, are counted in the quality report, and do not stop a run.

- An exact duplicate is recorded and one identical copy is retained.
- A conflicting duplicate is recorded, its analytical value is left missing,
  and it counts toward the quarantine threshold.
- An invalid numeric value or an out-of-range value is recorded, left missing,
  and counts toward that threshold.
- An unmapped entity is a broken relationship and stops the run immediately.
- If quarantined records exceed 1% of possible indicator cells (minimum 5), the
  run stops rather than publishing data with an unexpectedly large quality loss.

The processed `latest_run.json` pointer is updated only after transformation,
validation, and metrics all succeed. If any later stage fails, the dashboard
continues to read the previous successful run.

## Future improvement: review workflow for quarantine records

Add a small reviewer-facing page or report that groups quarantined records by
reason, indicator, and country, and records a deliberate resolution. The current
quality report preserves enough context to build this without changing source data.

## Future improvement: richer duplicate policy

If a source later provides trustworthy version metadata, consider selecting a
documented latest version. Until then, conflicting observations remain missing
and visible for investigation.
