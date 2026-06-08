# Repair5G.5.16 Error-Driven Safety Bound and Lattice Repair Plan

Generated: 2026-06-08

## Scope

Repair5G.5.16 is a local exploration execution round, not a prompt-only handoff. It carries forward the G5.15 conclusion that the rich-by-candidate interaction ranker is useful and safe-ish, but not stronger than reproduced v4 under strict risk-adjusted utility.

The round keeps all runtime, Phase5.5, Phase6, learned runtime policy, and AAAI-ready claims closed.

## Constraints

- Do not modify `external/lacam2/lacam2/**`.
- Do not change PIBT, LaCAM*, candidate generation, conflicts, pruning, OPEN/EXPLORED, rewrite, incumbent, restart semantics, or solver control.
- Do not inspect or run IDs `166..205`.
- Default to local PC execution and `max_workers=1` for any local solver probe.
- Stop before solver execution if targeted repair candidate names are not recognized by the current C++ adapter.
- Commit only G5.16-related scripts, tables, reports, and worklog changes.

## Execution Steps

1. Verify G5.15 artifacts and the final no-better-than-v4 decision.
2. Write the G5.15 final interpretation used by G5.16.
3. Build an error bank from harmful false positives, missed helpful fallbacks, static-near boundary cases, high-uncertainty contexts, high oracle-gap contexts, and candidate disagreement contexts.
4. Design a small update-only targeted repair lattice with no more than 12 new candidates.
5. Plan a local targeted probe over no more than 20 contexts, current 14 candidates plus repair candidates, budgets `1000` and `2000`, and `max_workers=1`.
6. Skip solver execution if the targeted lattice is not executable by the current adapter, while still producing the no-run report.
7. Build table-only augmented targets and v6 features from existing v5 data plus error-bank annotations.
8. Train pessimistic safety-bound ranker diagnostics with `ultra_safe_bound`, `balanced_bound`, and `opportunity_diagnostic_not_for_promotion` variants, plus no-error-bank and no-bound ablations.
9. Evaluate seed OOF, leave-one-map-agent-group-out, and fixed `146..150` train / `151..155` dev splits against G5.15 and control baselines.
10. Write false-positive/missed-opportunity autopsy, safety-package update, and final decision.

## Expected Stop Condition

The likely local stop condition is:

```text
targeted_repair_lattice_requires_adapter_followup
```

because the new `repair5g516_*` lattice names are intentionally not added to the C++ adapter in this round. If that gate fires, solver execution remains skipped and table-only diagnostics continue.
