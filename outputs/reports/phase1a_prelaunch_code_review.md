# Phase1a Prelaunch Code Review

Date: 2026-05-22
Status: resolved for generated-scenario path; server full batch still requires final server preflight before launch

## Summary

The first server full batch must not be interpreted as a valid Phase1a run. The runner failure exposed one expected-control-flow bug, and the prelaunch review found a more important benchmark data issue. The current manifest now points to deterministic generated scenarios rather than the insufficient public `scen-random.zip`.

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

3. A preflight gate is now added to both runners. It checks map existence, scenario existence, and scenario capacity before non-dry-run execution. The old public-scenario manifest correctly failed preflight with 200 scenario-capacity issues.

4. `scripts/generate_phase1a_scenarios.py` now generates 25 deterministic random scenarios per map with enough rows for every frozen Figure 1 agent count. It uses base seed `20260522`, samples starts and goals without replacement from each map's largest 4-neighbor connected free-cell component, and enforces `start != goal` for every agent.

## Validation

- `python -m py_compile scripts\run_phase1a_batch.py`: passed.
- Python preflight on the old public-scenario full manifest: failed as expected with scenario-capacity errors.
- Python preflight on the generated-scenario full manifest: passed with 3600 tasks.
- PowerShell preflight on `empty-32-32`, 600 agents, instance 1: failed as expected.
- Python valid subset probe on `empty-32-32`, 500 agents, instance 1, both methods: preflight passed and two JSONL rows were written.
- Python and PowerShell `--skip-preflight` / `-SkipPreflight` probes confirm exit code `2` no longer stops the driver.
- Python high-agent generated-scenario probe on `empty-32-32`, 1000 agents, instance 1, both methods: preflight passed and two JSONL rows were written.

## Recommendation

Before restarting the server batch, run the generator and preflight on the server:

```bash
python3 scripts/generate_phase1a_scenarios.py --overwrite
python3 scripts/run_phase1a_batch.py --preflight
```

No new full server batch was launched during this review.
