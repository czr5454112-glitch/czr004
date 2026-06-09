# Phase4B LAUR-LTM Update API Report

Date: 2026-05-26

Branch: `phase4-laur-ltm`

## Scope

This report covers only Phase4B from `phase4_6_laur_ltm_codex_execution_plan.md`.

Implemented:

- Minimal `czr004::ltm::UpdateParams` in `cpp/ltm/ltm.hpp`.
- New overload `DirectedTrafficMap::update_from_trace(events, params)`.
- Old `DirectedTrafficMap::update_from_trace(events)` preserved as a wrapper that calls `UpdateParams::additive()`.
- Force-additive parity smoke and Phase4B update API checks.
- Old Phase1 LTM and Phase0 smoke reruns.

Not implemented:

- No training.
- No raw trace export.
- No learned restart.
- No Phase4C record/probe/checkpoint schema work.

## UpdateParams API

The first Phase4B `UpdateParams` is intentionally small:

- `alpha_commit`
- `alpha_block`
- `alpha_wait_spillover`
- `rho_decay`
- `enable_contraflow_penalty`
- `contraflow_penalty`
- `enable_local_saturation`
- `force_additive`

`UpdateParams::additive()` sets all alpha/decay/penalty values to the old LTM-equivalent defaults and sets `force_additive=true`.

When `force_additive=true`, `update_from_trace(events, params)` first replaces the caller-supplied params with `UpdateParams::additive()`. This means non-default alpha, decay, local saturation, or contraflow values are ignored in force-additive mode.

## Old API Parity

The old API now delegates through the additive path:

```cpp
void DirectedTrafficMap::update_from_trace(
    const std::vector<TraceEvent>& events)
{
  update_from_trace(events, UpdateParams::additive());
}
```

The additive path preserves the old behavior:

- committed and blocked edge events add `1.0`;
- non-goal waits propagate `1.0` to outgoing edges;
- goal waits are ignored;
- `rho_decay=1.0` does not decay raw counts;
- max-count normalization remains unchanged;
- normalized weights remain clamped to `[lower_bound, upper_bound]`.

Local saturation is only a reserved switch in Phase4B; it is not active before Phase4C+ design work.

## New Smoke

Added:

- `cpp/ltm/phase4_laur_update_smoke.cpp`
- `scripts/build_phase4_laur_smoke.ps1`
- `scripts/phase4_laur_update_smoke.ps1`

The smoke checks:

- old wrapper vs `UpdateParams::additive()` raw and normalized parity;
- `force_additive=true` ignores non-default params and still matches old wrapper;
- old committed, wait-spillover, and goal-wait-ignore semantics;
- commit/block alpha weighting in non-additive mode;
- wait-spillover alpha weighting in non-additive mode;
- decay before processing new events when `rho_decay < 1.0`;
- contraflow remains off by default;
- normalized weights stay within bounds.

## Commands And Results

Final validation commands:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_phase4_laur_smoke.ps1
powershell -ExecutionPolicy Bypass -File scripts\phase4_laur_update_smoke.ps1
powershell -ExecutionPolicy Bypass -File scripts\build_phase1_ltm.ps1
powershell -ExecutionPolicy Bypass -File scripts\phase1_ltm_smoke.ps1
powershell -ExecutionPolicy Bypass -File scripts\phase0_smoke.ps1
```

Results:

- `build_phase4_laur_smoke.ps1`: passed; `phase4_laur_update_smoke.exe` built.
- `phase4_laur_update_smoke.ps1`: passed; output included `phase4_laur_update_smoke ok`.
- `build_phase1_ltm.ps1`: passed; rebuilt `phase1_ltm_smoke.exe`, `phase1a_batch.exe`, and `phase4_laur_update_smoke.exe`.
- `phase1_ltm_smoke.ps1`: passed.
  - `loop`: baseline sum of loss `15`, LTM sum of loss `15`, max weight `10`.
  - `random-32-32-10`: baseline sum of loss `76`, LTM sum of loss `76`, max weight `10`.
- `phase0_smoke.ps1`: passed.
  - upstream `test_all.exe`: `7/7` passed.
  - `phase0_smoke.exe`: `sum_of_loss=15`.

Operational note: an earlier accidental duplicate parallel build hit an MSVC/Ninja PDB write lock. The later single-command build and smoke runs passed; this was not an update API failure.

## Phase4B Gate

| Gate item | Result |
|---|---|
| Old Phase1 LTM smoke still passes | Pass |
| Phase0 upstream smoke still passes | Pass |
| Force-additive parity passes | Pass |
| Normalized weight bound passes | Pass |
| Goal wait ignore passes | Pass |

Phase4B gate is passed. Phase4C remains untouched in this change set.
