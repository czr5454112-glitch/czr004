# G5.28 Exact Failure Logging Static Verification

- decision: `exact_failure_logging_patch_static_verified`
- audit precision: `partial`
- external/lacam2/lacam2 clean: `True`
- pibt_failure_audit key present: `True`
- semantics: audit carrier is separate from `TraceEvent` and UpdateLTM still consumes `collector.events()`.
