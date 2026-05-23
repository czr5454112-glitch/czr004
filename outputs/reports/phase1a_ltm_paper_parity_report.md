# Phase1a LTM Paper Parity Report

Date: 2026-05-23
Status: server full batch complete; integrity pass; base paper-parity results ready for final comparison

## Code State

- project commit used by server full batch: `65984dbf729e90177cb72cecab49cc222bd1bd1f`
- branch: `phase1a-ltm-paper-parity`
- workspace state recorded by server full batch: `clean`
- external/lacam2 commit: `61a4c40ce91ce18c06eb2fe070aa9f1951eecb8d`
- upstream solver source policy: `external/lacam2/lacam2/**` was not modified

## Experiment Setting

- paper setting: classic one-shot MAPF
- full target maps: 8 maps frozen in `configs/phase1a/manifest.yaml`
- full target instances: 25 deterministic generated random instances per map from `outputs/tmp/phase1a/generated/phase1a-generated-random.zip`
- optional extension: `configs/phase1a/manifest_plus_3000.jsonl` adds a 3000-agent stress-test point on four eligible maps, for 3800 total solver runs
- full target time limit: 30s per run
- objective: sum-of-loss
- metric: `sum_of_loss_ratio = sum_of_loss / sum_of_costs_lower_bound`
- server platform: Linux server package via ssh-skill tmux

## Methods Run

| Method | Status | Notes |
| --- | --- | --- |
| `LaCAM*` | full server batch complete | project-owned batch runner calls upstream library API, not upstream CLI |
| `LaCAM*+LTM` | full server batch complete | paper-faithful local reimplementation |
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

## Server Full Batch Results

Downloaded server artifacts:

- Raw JSONL: `outputs/logs/phase1a/phase1a_plus_3000_runs.jsonl` (ignored by git)
- Summary CSV: `outputs/tables/phase1a_plus_3000_ratio_by_map.csv`
- Summary figure: `outputs/figures/phase1a_plus_3000_ratio_by_map.png`
- Integrity report: `outputs/reports/phase1a_server_full_integrity_report.md`

Structural checks passed:

- JSONL rows: 3800 / 3800.
- Unique `(map, agents, seed, method)` keys: 3800.
- Missing expected rows: 0.
- Duplicate rows: 0.
- `valid_instance=true`: 3800.
- Time limit: 30s for all rows.
- stderr: empty.
- Re-summarized local CSV matches the downloaded server CSV hash.

Base paper-parity subset:

| Metric | Result |
| --- | ---: |
| Rows | 3600 |
| `lacam_star` successes | 1799 / 1800 |
| `lacam_star_ltm` successes | 1787 / 1800 |
| Paired successful instances | 1787 |
| LTM better paired instances | 1758 / 1787 |
| Average LaCAM* ratio on paired successes | 2.884359 |
| Average LTM ratio on paired successes | 2.440896 |
| Relative ratio improvement | 15.3747% |
| Group-level mean-ratio wins | 72 / 72 base map-agent groups |

The plus-3000 extension is complete but mixed, and is not part of the base paper-parity claim.

## Known Deviations From Paper

- The frozen base paper-parity subset contains 72 map-agent points x 25 instances x 2 required methods = 3600 solver runs, now completed on the server as part of the plus-3000 manifest.
- The original public `scen-random.zip` source is insufficient for several frozen agent counts. The current manifest uses generated scenarios instead, with metadata in `outputs/reports/phase1a_generated_scenarios_manifest.json`.
- The local LTM adapter currently uses root restart for one-shot MAPF, as recorded in Phase1.
- Weighted distance uses `1 + normalized_ltm_weight`; exact official source is unavailable.
- Hardware/platform differs from the paper workstation.
- `TO/SUO` are explicitly unavailable rather than casually reimplemented.

## Parity Gate

Current judgement: `full execution complete / candidate paper-parity pass pending final figure-level comparison`.

The dry-run gate is satisfied:

- `lacam_star` solved and emitted valid JSONL.
- `lacam_star_ltm` solved and emitted valid JSONL.
- ratio values are finite and positive.
- Phase0 and Phase1 regression smoke passed after adding the Phase1a runner.

The full Phase1a server execution is complete and structurally valid. The base 72-point paper-parity subset shows the expected LTM direction: lower mean ratio than LaCAM* on all base map-agent groups. Before entering Phase2, make an explicit final signoff against the LTM paper figures and keep the plus-3000 points reported as an extension.

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
