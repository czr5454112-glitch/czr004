# Phase5.5 Repair5G.3.1 Protocol Closure Overview

Repair5G.3.1 closes only the G3 protocol question. It does not claim Phase5.5 or Phase6 permission.

## Question

The G3 broad run produced strong directional flow-shield evidence, but strict exact parity flags failed for additive/disabled/force-additive controls. The closure task must distinguish:

- true solver semantic mismatch
- wall-clock anytime sensitivity
- return-code-2 timeout/no-solution equivalence
- run-order or parallel scheduling sensitivity
- comparison or gate aggregation bugs
- bool-as-int mistakes
- resume duplicate or synthetic-row contamination

## Closure Sequence

1. Recompute protocol gates from raw G3 rows, committed tables, command logs, and summaries.
2. Audit gate field types so boolean `False` cannot pass numeric zero-count checks.
3. Write mismatch, return-code-2, gate-type, and resume/duplicate audit tables.
4. Reproduce strict mismatch cases with control-only sequential runs at longer budgets.
5. Write a conservative parity policy that keeps exact parity visible and does not silently replace it with semantic parity.
6. Run protocol gate tests.
7. Only if closure passes, use IDs `126..165` for G4 clean frozen validation.

## Boundary

- `phase5p5_allowed=false`
- `phase6_allowed=false`
- `diagnostic_only=true`
- no LaCAM*/PIBT/search semantic changes
- no learned actions, learned restart, learned priorities, learned heuristic values, or candidate deletion
- no clean-validation reuse of IDs `66..105`
