# Implementation Notes

This file records implementation decisions where the local code cannot be directly checked against an official LTM implementation.

## 2026-05-20 - initial constraints

- LTM public source is not available in the local materials.
- The project will describe its LTM implementation as `paper-faithful reimplementation`.
- The local PDF states the LTM experimental edge-weight range as `[0,10]`; this is the default until contradicted by a primary source.
- LaCAM* is the only solver base for this project.
- Any deviation from the PDF algorithm must be recorded here before it is used in experiments.

## Open Items

- Define quantitative parity tolerance after the first reproducible LTM smoke.
- Expand the Phase1 structural smoke into a full paper-parity benchmark: eight grid maps, 25 random instances per map, 30s setting.
- Decide whether later experiment scripts should use the current `cpp/ltm` adapter directly or a higher-level metrics harness entrypoint.

## 2026-05-20 - Phase0 environment retry

- Initial `conda env update` failed while extracting `pytorch-2.10.0` on Windows due to a long test-file path inside the package cache.
- Retrying with `CONDA_PKGS_DIRS=C:\tmp\conda_pkgs` initially installed `torch 2.5.1`, but later toolchain troubleshooting exposed an unstable DLL state.
- A later conda retry installed `pytorch-cuda=12.4` but still selected `conda-forge` CPU builds for `pytorch`/`libtorch`, so `torch.version.cuda` remained `None`.
- Final Phase0 decision: keep PyTorch as pip CUDA wheels inside the `czr004` conda environment, not as conda `pytorch` packages.

Accepted GPU stack:

```text
torch 2.5.1+cu124
torchvision 0.20.1+cu124
torchaudio 2.5.1+cu124
torch.version.cuda 12.4
torch.cuda.is_available() True
device NVIDIA GeForce RTX 4070 Laptop GPU
```

Install recipe used after removing the CPU conda packages:

```powershell
conda remove -n czr004 pytorch torchvision torchaudio libtorch -y
& "$env:USERPROFILE\.conda\envs\czr004\python.exe" -m pip install --index-url https://download.pytorch.org/whl/cu124 torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1
& "$env:USERPROFILE\.conda\envs\czr004\python.exe" -m pip install --force-reinstall pillow==10.4.0
```

The Pillow reinstall fixes a Windows DLL-load failure hit when importing `torchvision`.

## 2026-05-20 - LaCAM* Windows build shim

- Upstream `Kei18/lacam2` is kept unmodified as `external/lacam2`.
- The local MSVC build uses `cpp/compat/lacam2_windows_compat.hpp` through CMake `/FI`.
- The shim only defines Unix-style `uint`, maps the alternative token `or`, and undefines MSVC's `_MT` macro because upstream uses `_MT` as a parameter name.
- This is a build compatibility layer, not a solver semantic change.
- `test_all.exe` passes in the MSVC compatibility build.
- Upstream `main.exe` hangs on local CLI smoke even with `-t 0`; use library-level tests as Phase0 smoke and revisit the run entrypoint before Phase1 experiments.

## 2026-05-20 - Phase0 CLI hang diagnosis

- Current diagnosis: upstream `main.cpp` registers both argparse's default `-v/--version` and a custom `-v/--verbose` short flag, which makes README-style `-v` runs unsafe. The local timeout was also observed without relying on `-v`, so the exact CLI hang root cause remains unproven.
- `test_all.exe` and the project-owned `build/phase0-smoke/phase0_smoke.exe` are the accepted Phase0/Phase1 entrypoints.
- `scripts/phase0_smoke.ps1` runs `test_all.exe` plus `phase0_smoke.exe` from `external/lacam2` working directory.
- Do not use upstream `main.exe -v ...` in experiment scripts; prefer `--verbose` only after validating argparse behavior, or use the project smoke/adapter binary.

## 2026-05-21 - Phase1 LTM structural implementation

- Added a project-owned LTM layer under `cpp/ltm`; upstream `external/lacam2` source files remain unmodified.
- `DirectedTrafficMap` stores directed edge raw counts and normalized weights in the paper range `[0,10]`.
- Wait actions are not modeled as self-loops. Non-goal wait events propagate one increment to all outgoing edges of the waited vertex. Goal-wait events are ignored.
- `PibtTraceCollector` records committed actions and blocked actions. Blocked actions are implemented as higher-ranked PIBT candidates rejected before the selected action due to next-vertex occupancy, swap conflict, or failed priority-inheritance recursion.
- `WeightedDistanceTable` computes per-agent shortest-path distances over the directed LTM by Dijkstra on reverse adjacency after each LTM update.
- The Phase1 adapter copies the upstream LaCAM* planner structure into project code and swaps the distance table / trace collection / iteration budget logic. This is intentionally local code, not a patch to upstream solver files.
- The adapter uses `1 + normalized_ltm_weight` as the traversal cost for weighted distance. This keeps the unpenalized graph distance meaningful while preserving the `[0,10]` normalized traffic value as the congestion component. This is a paper-faithful engineering choice, but exact official code behavior is unavailable.
- The frequent-restart wrapper runs repeated one-shot LTM-guided searches until the time limit or `max_iterations` is reached. The first iteration has no node budget. Subsequent iterations use `10 * current_best_makespan`, matching the Phase1 guide.
- For the one-shot smoke, `SelectRestartNode` is implemented as root restart. The paper notes root restart generally converges well in one-shot MAPF given enough runtime; more advanced restart-node selection remains future work.
- Current Phase1 status is a structural gate plus lightweight quantitative smoke, not a claim of full paper benchmark parity.
