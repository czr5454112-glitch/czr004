# Phase1a Prelaunch Code Review

Date: 2026-05-22
Status: blocked before full batch restart

## Summary

The server full batch must not be restarted from the current manifest yet. The runner failure from the first server attempt exposed one expected-control-flow bug, and the prelaunch review found a more important benchmark data issue.

## Findings

1. `phase1a_batch` returns exit code `2` when it has written a valid `success=false` JSONL row. This is an expected benchmark outcome for invalid/no-solution/timeout rows, not a driver crash. The Python and PowerShell drivers now allow return codes `0` and `2`, while still raising on other nonzero codes.

2. The current `scen-random.zip` source does not contain enough start-goal rows for many frozen paper Figure 1 agent counts. A full paper schedule run would therefore emit many `valid_instance=false` rows and would not be a valid paper-parity run.

| Map | Scenario row capacity | Frozen max agents | Invalid frozen counts |
| --- | ---: | ---: | --- |
| `empty-32-32` | 512 | 1000 | 600, 700, 800, 900, 1000 |
| `empty-48-48` | 1000 | 2000 | 1200, 1400, 1600, 1800, 2000 |
| `random-32-32-20` | 409 | 700 | 500, 600, 700 |
| `maze-32-32-4` | 395 | 500 | 400, 500 |
| `random-64-64-20` | 1000 | 2000 | 1200, 1400, 1600, 1800, 2000 |
| `room-64-64-8` | 1000 | 2000 | 1200, 1400, 1600, 1800, 2000 |
| `warehouse-10-20-10-2-1` | 1000 | 2000 | 1200, 1400, 1600, 1800, 2000 |
| `warehouse-10-20-10-2-2` | 1000 | 2000 | 1200, 1400, 1600, 1800, 2000 |

3. A preflight gate is now added to both runners. It checks map existence, scenario existence, and scenario capacity before non-dry-run execution. The current full manifest correctly fails preflight with 200 scenario-capacity issues.

## Validation

- `python -m py_compile scripts\run_phase1a_batch.py`: passed.
- Python preflight on the current full manifest: failed as expected with scenario-capacity errors.
- PowerShell preflight on `empty-32-32`, 600 agents, instance 1: failed as expected.
- Python valid subset probe on `empty-32-32`, 500 agents, instance 1, both methods: preflight passed and two JSONL rows were written.
- Python and PowerShell `--skip-preflight` / `-SkipPreflight` probes confirm exit code `2` no longer stops the driver.

## Recommendation

Use one of two explicit paths before restarting the server batch:

- Recommended: generate deterministic random scenario files with enough unique start-goal pairs for every frozen Figure 1 agent count. This keeps the 72 map-agent points and 3600-run paper-scale structure, but must be labeled as generated random instances rather than exact MAPF benchmark `scen-random.zip` instances.
- Conservative subset: cap each map's agent counts to the capacity of the existing `scen-random.zip` files. This would be useful for debugging but would reduce the benchmark to 37 map-agent points and would not satisfy Phase1a paper parity.

No new full server batch was launched after this review.
