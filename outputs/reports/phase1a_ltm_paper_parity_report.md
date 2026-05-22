# Phase1a LTM Paper Parity Report

Date: 2026-05-21
Status: ready for server preflight -- reproducible Phase1a chain and 30s probe passed; deterministic generated random scenarios now pass the full 3600-task preflight locally. Full server batch has not been relaunched.

## Code State

- project commit used by recorded probe: `8e5bb57493f68a9302ca573754f83a1c870821ed`
- branch: `phase1a-ltm-paper-parity`
- workspace state during probe: `tracked-dirty` because Phase1a files were being added in this working session
- external/lacam2 commit: `61a4c40ce91ce18c06eb2fe070aa9f1951eecb8d`
- upstream solver source policy: `external/lacam2/lacam2/**` was not modified

## Experiment Setting

- paper setting: classic one-shot MAPF
- full target maps: 8 maps frozen in `configs/phase1a/manifest.yaml`
- full target instances: 25 deterministic generated random instances per map from `outputs/tmp/phase1a/generated/phase1a-generated-random.zip`
- full target time limit: 30s per run
- objective: sum-of-loss
- metric: `sum_of_loss_ratio = sum_of_loss / sum_of_costs_lower_bound`
- platform: Windows + PowerShell + MSVC-compatible local build

## Methods Run

| Method | Status | Notes |
| --- | --- | --- |
| `LaCAM*` | probe done | project-owned batch runner calls upstream library API, not upstream CLI |
| `LaCAM*+LTM` | probe done | paper-faithful local reimplementation |
| `LaCAM*+TO` | unavailable | no auditable upstream integration in `czr004` |
| `LaCAM*+SUO` | unavailable | no auditable upstream integration in `czr004` |

## Dry-Run And Probe Results

Raw files are intentionally under ignored logs:

- smoke dry-run: `outputs/logs/phase1a/phase1a_dry_run.jsonl`
- manifest 5s probe: `outputs/logs/phase1a/phase1a_manifest_probe.jsonl`
- manifest 30s probe: `outputs/logs/phase1a/phase1a_manifest_probe_30s.jsonl`

Generated tracked summaries:

- CSV: `outputs/tables/phase1a_ratio_by_map.csv`
- figure: `outputs/figures/phase1a_ratio_by_map.png`

30s manifest probe:

| Map | Agents | Instance | Method | Sum-of-loss | Lower bound | Ratio |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| `random-32-32-20` | 100 | 1 | `LaCAM*` | 2853 | 2253 | 1.26631158455 |
| `random-32-32-20` | 100 | 1 | `LaCAM*+LTM` | 2706 | 2253 | 1.20106524634 |

This single 30s probe is directionally consistent with the paper trend, but it is not enough for a Phase1a parity judgement.

## Known Deviations From Paper

- Full paper-scale execution is not complete in this report. The frozen full manifest contains 72 map-agent points x 25 instances x 2 required methods = 3600 solver runs.
- The original public `scen-random.zip` source is insufficient for several frozen agent counts. The current manifest uses generated scenarios instead, with metadata in `outputs/reports/phase1a_generated_scenarios_manifest.json`.
- The local LTM adapter currently uses root restart for one-shot MAPF, as recorded in Phase1.
- Weighted distance uses `1 + normalized_ltm_weight`; exact official source is unavailable.
- Hardware/platform differs from the paper workstation.
- `TO/SUO` are explicitly unavailable rather than casually reimplemented.

## Parity Gate

Current judgement: `partial / no parity pass yet`.

The dry-run gate is satisfied:

- `lacam_star` solved and emitted valid JSONL.
- `lacam_star_ltm` solved and emitted valid JSONL.
- ratio values are finite and positive.
- Phase0 and Phase1 regression smoke passed after adding the Phase1a runner.

The full Phase1a parity gate remains blocked until the generated-scenario manifest is run on the server for the full 30s batch and the results are summarized. Do not enter Phase2 from this report alone.

## Repro Commands

```powershell
powershell -ExecutionPolicy Bypass -File C:\PROGRAMING\czr004\scripts\build_phase1a_batch.ps1

powershell -ExecutionPolicy Bypass -File C:\PROGRAMING\czr004\scripts\run_phase1a_batch.ps1 -DryRun -OutputJsonl outputs\logs\phase1a\phase1a_dry_run.jsonl

powershell -ExecutionPolicy Bypass -File C:\PROGRAMING\czr004\scripts\run_phase1a_batch.ps1 -MapSubset random-32-32-20 -AgentSubset 100 -InstanceSubset 1 -MaxTasks 2 -TimeLimitSec 30 -OutputJsonl outputs\logs\phase1a\phase1a_manifest_probe_30s.jsonl

python C:\PROGRAMING\czr004\src\eval\phase1a_summarize.py --input C:\PROGRAMING\czr004\outputs\logs\phase1a\phase1a_manifest_probe_30s.jsonl --output-csv C:\PROGRAMING\czr004\outputs\tables\phase1a_ratio_by_map.csv --output-figure C:\PROGRAMING\czr004\outputs\figures\phase1a_ratio_by_map.png
```

Full batch command, for an overnight or scheduled run:

```powershell
powershell -ExecutionPolicy Bypass -File C:\PROGRAMING\czr004\scripts\run_phase1a_batch.ps1 -Full -OutputJsonl outputs\logs\phase1a\phase1a_runs.jsonl
python C:\PROGRAMING\czr004\src\eval\phase1a_summarize.py --input C:\PROGRAMING\czr004\outputs\logs\phase1a\phase1a_runs.jsonl
```

Linux server command:

```bash
bash scripts/build_phase1a_batch.sh
python3 scripts/run_phase1a_batch.py --dry-run --output-jsonl outputs/logs/phase1a/phase1a_linux_dry_run.jsonl
python3 scripts/run_phase1a_batch.py --full --output-jsonl outputs/logs/phase1a/phase1a_runs.jsonl
python3 src/eval/phase1a_summarize.py --input outputs/logs/phase1a/phase1a_runs.jsonl
```
