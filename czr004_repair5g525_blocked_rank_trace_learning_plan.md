# Repair5G.5.25 Blocked-Rank Trace Learning Plan

Date: 2026-06-09

## Objective

Run a local, semantic-preserving G5.25 diagnostic round for blocked-reason,
competing-neighbor-rank, and candidate-specific rank-effect features.

## Scope

- Verify the G5.24 blocked learning state.
- Treat the old raw checkpoint SHA mismatch as a provenance warning.
- Add only project-owned trace/audit logging fields.
- Generate fresh G5.25 trace logs and verified manifests.
- Build leakage-clean rank-effect feature and teacher tables.
- Evaluate rank-effect models, update surrogates, failure autopsy, and final
  decision.

## Guardrails

```text
phase5p5_allowed=false
phase6_allowed=false
runtime_claim_allowed=false
learned_runtime_policy_validated=false
aaai_ready=false
```

No `external/lacam2/lacam2/**` edits, no IDs `166..205`, no solver semantic
changes, no MAPF action/priority/restart/h-value/candidate-deletion learning,
and no outcome/oracle/delta labels in `feature_*`.

## Execution Notes

The G5.25 C++ change adds audit metadata to trace events that are already
recorded by the project-owned LTM/PIBT wrapper. It does not add or remove
committed/blocked trace events, so UpdateLTM receives the same event sequence.

The enriched G5.25 probe writes fresh checkpoint trace logs. Candidate-budget
outcomes are reused from committed G5.23/G5.24 derived tables, not mined from
the mismatched old raw checkpoint.
