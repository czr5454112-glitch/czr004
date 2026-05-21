# Phase1 LTM Reimplementation Report

Date: 2026-05-21  
Project: `C:\PROGRAMING\czr004`  
Branch: `phase1-ltm-reimpl`

## Goal

Complete the Phase1 structural gate from the project guide: add a paper-faithful LaCAM*+LTM reimplementation layer while keeping the upstream LaCAM* source tree unchanged.

## Code State

- Upstream LaCAM* submodule: `61a4c40ce91ce18c06eb2fe070aa9f1951eecb8d`
- Upstream recursive submodules:
  - `scripts`: `09a158196e513252cfb468ad46e33568787c1e92`
  - `third_party/argparse`: `e9ae471ea46a0f3dcd2bbbd26fa3d14433ec7884`
  - `third_party/googletest`: `5376968f6948923e2411081fd9372e71a59d8e77`
- Upstream source policy: no edits under `external/lacam2/lacam2`.
- Local implementation path: `cpp/ltm`.

## Implemented

- `DirectedTrafficMap`
  - directed edge records for every ordered graph neighbor edge
  - raw traffic counts
  - normalized weights in `[0,10]`
  - non-goal wait propagation to outgoing edges
  - goal-wait ignore
- `PibtTraceCollector`
  - committed PIBT actions
  - blocked higher-ranked candidate actions
- `WeightedDistanceTable`
  - Dijkstra over reverse directed adjacency
  - recomputed after each LTM update
- LTM-guided LaCAM* adapter
  - local project copy of the planner control structure
  - weighted distances used in PIBT ranking, root priorities, and swap checks
  - frequent restart wrapper
  - first iteration without node budget
  - later iterations with `10 * current_best_makespan`
- Phase1 build and smoke scripts:
  - `scripts/build_phase1_ltm.ps1`
  - `scripts/phase1_ltm_smoke.ps1`

## Validation

Build:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_phase1_ltm.ps1
```

Result: build succeeded and generated `build\phase1-ltm\phase1_ltm_smoke.exe`.

Phase1 smoke:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase1_ltm_smoke.ps1
```

Result:

```text
phase1_ltm_case ok label=loop agents=3 baseline_sum_of_loss=15 ltm_sum_of_loss=15 iterations=3 committed=1305 blocked=367 nonzero_edges=24 max_weight=10
phase1_ltm_case ok label=random-32-32-10 agents=3 baseline_sum_of_loss=76 ltm_sum_of_loss=76 iterations=3 committed=333 blocked=0 nonzero_edges=233 max_weight=10
phase1_ltm_smoke ok
Phase1 LTM smoke passed.
```

Baseline regression:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase0_smoke.ps1
```

Result: upstream `test_all.exe` passed 7/7 tests, and `phase0_smoke.exe` returned `sum_of_loss=15`.

## Interpretation

The Phase1 structural gate is satisfied: the LTM loop runs, edge weights update from PIBT history, fallback baseline smoke is intact, weighted distances are used by the local adapter, and the small benchmark smoke does not regress against LaCAM* on the checked cases.

This is not yet the final paper-parity benchmark. The current quantitative check covers one tiny map and one `random-32-32-10` representative smoke instance. Full parity still requires the paper-style eight grid maps, 25 random instances per map, and 30s setting.

## Recorded Deviations

- The official LTM source is not available locally; this implementation is a paper-faithful reimplementation.
- The adapter is implemented in project code under `cpp/ltm`, rather than modifying upstream LaCAM* files.
- Weighted traversal distance uses `1 + normalized_ltm_weight`; normalized traffic itself remains bounded in `[0,10]`.
- Current one-shot restart selection restarts from the root. More advanced `SelectRestartNode(H)` variants are deferred until the metrics harness is ready.
- Planning-and-execution MAPF is not part of this Phase1 smoke.

## Next Steps

1. Add a metrics harness around `cpp/ltm` so Phase2 can compute SoL ratio, AUC, returned-solution count, and expansion statistics consistently.
2. Promote Phase1 smoke to a batch benchmark on paper representative grid families.
3. Use the LTM traces and normalized weights as the future Phase3 teacher-data source.
