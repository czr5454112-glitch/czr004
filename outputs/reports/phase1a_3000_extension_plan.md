# Phase1a 3000-Agent Extension Plan

Date: 2026-05-22
Status: running on server in tmux session `phase1a_full`

## Purpose

This extension keeps the full LTM paper-parity schedule intact and adds a stress-test point at 3000 agents where the map has enough free cells. The 3000-agent point is not part of the original Figure 1 parity claim and must be reported separately.

## Scope

- Base paper-parity schedule: 72 map-agent points.
- Extension schedule: 4 additional map-agent points.
- Instances: 25 deterministic generated random instances per map.
- Methods: `lacam_star`, `lacam_star_ltm`.
- Time limit: 30 seconds per run.
- Total solver runs: `(72 + 4) x 25 x 2 = 3800`.

## 3000-Agent Eligibility

| Map | Free cells | 3000-agent point |
| --- | ---: | --- |
| `empty-32-32` | 1024 | no |
| `empty-48-48` | 2304 | no |
| `random-32-32-20` | 819 | no |
| `maze-32-32-4` | 790 | no |
| `random-64-64-20` | 3270 | yes |
| `room-64-64-8` | 3232 | yes |
| `warehouse-10-20-10-2-1` | 5699 | yes |
| `warehouse-10-20-10-2-2` | 9776 | yes |

## Files

- Schedule: `configs/phase1a/agent_schedule_plus_3000.yaml`
- Runner manifest: `configs/phase1a/manifest_plus_3000.jsonl`
- Human manifest: `configs/phase1a/manifest_plus_3000.yaml`
- Scenario generator: `scripts/generate_phase1a_scenarios.py`
- Scenario metadata: `outputs/reports/phase1a_generated_scenarios_manifest.json`

## Validation

- `python -m py_compile scripts\generate_phase1a_scenarios.py scripts\run_phase1a_batch.py src\eval\phase1a_summarize.py`: passed.
- `python scripts\generate_phase1a_scenarios.py --manifest configs\phase1a\manifest_plus_3000.jsonl --overwrite`: generated 200 scenario files.
- `python scripts\run_phase1a_batch.py --manifest configs\phase1a\manifest_plus_3000.jsonl --preflight`: passed with 3800 tasks.
- `python scripts\run_phase1a_batch.py --manifest configs\phase1a\manifest_plus_3000.jsonl --map-subset random-64-64-20 --agent-subset 3000 --instance-subset 1 --max-tasks 1 --time-limit-sec 1`: wrote a valid JSONL row with `valid_instance=true`.
- Server launch check on 2026-05-22 10:15 +08:00: `/root/shared-nvme/server_start_phase1a_full.sh` created tmux session `phase1a_full`.
- Server preflight log: `Phase1a preflight passed. Tasks=3800`.
- Initial server output: `outputs/logs/phase1a/phase1a_plus_3000_runs.jsonl` had begun writing rows and `full_stderr.log` was empty.

## Server Rule

All server setup, preflight, dry-run, and full-batch execution must be launched inside `tmux`.

## Server Output Paths

- Work directory: `/root/shared-nvme/czr004_phase1a_65984db`
- JSONL: `outputs/logs/phase1a/phase1a_plus_3000_runs.jsonl`
- Stdout: `outputs/logs/phase1a/full_stdout.log`
- Stderr: `outputs/logs/phase1a/full_stderr.log`
- Summary CSV: `outputs/tables/phase1a_plus_3000_ratio_by_map.csv`
- Summary figure: `outputs/figures/phase1a_plus_3000_ratio_by_map.png`
