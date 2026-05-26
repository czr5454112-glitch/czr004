# Phase4D LAU Update-Rule Probe Label Report

Date: 2026-05-26 12:13:31 
Status: passed

## Scope

Phase4D runs short-budget counterfactual probes for fixed update rules and builds checkpoint-level best-rule labels. It does not train a model, modify `cpp/ntm`, or implement learned restart.

## Code State

- branch: `phase4-laur-ltm`
- commit: `4b45964`
- dirty: `tracked-dirty`
- config: `configs\phase4\laur_ltm.yaml`

## Smoke Run

- map: `random-32-32-10`
- agents: 50
- seed: 1
- base time_limit_sec: 3
- max_iterations: 4
- short_budget_sec: 1.0
- max_checkpoints_per_run: 4
- rules: `additive_ltm,commit_heavy,block_heavy,block_light,wait_light,wait_heavy,decay_095,decay_090`
- probe exit code: 0

## Command

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_phase4_laur_probe.ps1
C:\PROGRAMING\czr004\build\phase4-laur-ltm\phase4_laur_probe.exe --map C:\PROGRAMING\czr004\external\lacam2\assets\random-32-32-10.map --scen C:\PROGRAMING\czr004\external\lacam2\assets\random-32-32-10-random-1.scen --map-name random-32-32-10 --split train --agents 50 --seed 1 --time-limit-sec 3 --max-iterations 4 --run-id random-32-32-10__a50__s1__phase4c_smoke --probe-output-jsonl C:\PROGRAMING\czr004\artifacts\teacher\laur\probes\phase4_laur_probe_smoke.jsonl --probe-short-budget-sec 1.0 --max-checkpoints-per-run 4 --checkpoint-topk-edges 16 --harmful-delta-ratio-threshold -0.02 --rule-set additive_ltm,commit_heavy,block_heavy,block_light,wait_light,wait_heavy,decay_095,decay_090 --branch phase4-laur-ltm --commit 4b45964 --dirty tracked-dirty
```

## Outputs

- probe JSONL: `artifacts\teacher\laur\probes\phase4_laur_probe_smoke.jsonl` (36537 bytes)
- best-rule labels: `artifacts\teacher\laur\update_labels\phase4_laur_best_rule_labels_smoke.jsonl` (2661 bytes)
- summary JSON: `outputs\reports\phase4_laur_probe_label_summary.json` (913 bytes)

## Audit Result

- probe rows: 32
- checkpoint count: 4
- best-label rows: 4
- schema errors: 0
- grouping errors: 0
- non-neutral checkpoints: 4
- harmful update rows: 2
- label distribution: `{'block_heavy': 1, 'commit_heavy': 1, 'decay_090': 1, 'wait_light': 1}`
- best-rule histogram: `{'block_heavy': 1, 'commit_heavy': 1, 'decay_090': 1, 'wait_light': 1}`
- audit passed: True

## Probe Stdout

```text
phase4_laur_probe run_id=random-32-32-10__a50__s1__phase4c_smoke map=random-32-32-10 agents=50 seed=1 checkpoints=4 rules=8 probe_rows=32 probe_output_jsonl=C:\PROGRAMING\czr004\artifacts\teacher\laur\probes\phase4_laur_probe_smoke.jsonl
```

