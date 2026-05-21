# Codex Worklog

## 2026-05-21 20:02 - add Phase1a paper-level parity stage

- Request: Add a new Phase1a after Phase1 and before Phase2. Phase1a should perform full paper-level quantitative reproduction aligned with the LTM paper before entering Phase2.
- Files changed:
  - `deep-research-report.md`
  - `deep-research-report (1).md`
  - `docs/implementation-notes.md`
  - `docs/upstream-baseline.md`
  - `outputs/reports/phase1_ltm_reimpl_report.md`
  - `outputs/reports/phase1a_ltm_paper_parity_plan.md`
  - `docs/codex-worklog.md`
- Commands run:
  - `git status --short`
  - `git branch --show-current`
  - searched project guide, docs, and reports for Phase1/Phase2 references
- Key observations:
  - Phase1 currently means the LTM structural implementation gate and lightweight smoke.
  - The full paper-level quantitative parity benchmark was previously listed as a future expansion, but it now needs to become an explicit blocking phase.
  - Phase1a should allow only paper-route baselines. `TO/SUO` must be original/auditable or explicitly marked unavailable.
- Tests / validation:
  - Documentation-only change; no solver or benchmark commands were run.
- Follow-up:
  - Start Phase1a by re-reading the LTM experiment section and listing exact maps / agent schedules before writing batch code.

## 2026-05-21 19:44 - start Phase1 LTM reimplementation

- Request: Complete Phase1 in `C:\PROGRAMING\czr004`, strictly following the project guide, keeping records and git discipline.
- Files changed:
  - `cpp/ltm/ltm.hpp`
  - `cpp/ltm/ltm.cpp`
  - `cpp/ltm/CMakeLists.txt`
  - `cpp/ltm/phase1_ltm_smoke.cpp`
  - `scripts/build_phase1_ltm.ps1`
  - `scripts/phase1_ltm_smoke.ps1`
  - `docs/implementation-notes.md`
  - `outputs/reports/phase1_ltm_reimpl_report.md`
  - `docs/codex-worklog.md`
- Commands run:
  - `git status --short`
  - searched the project guide for Phase1 requirements
  - read Phase0 worklog, implementation notes, upstream baseline notes, and LaCAM* upstream interfaces
  - extracted relevant LTM paper text with `pdftotext`
  - `git switch -c phase1-ltm-reimpl`
  - `powershell -ExecutionPolicy Bypass -File scripts\build_phase1_ltm.ps1`
  - `powershell -ExecutionPolicy Bypass -File scripts\phase1_ltm_smoke.ps1`
  - `powershell -ExecutionPolicy Bypass -File scripts\phase0_smoke.ps1`
- Key observations:
  - Phase0 gate is recorded as satisfied; upstream LaCAM* commit is `61a4c40ce91ce18c06eb2fe070aa9f1951eecb8d`.
  - Phase1 must keep upstream solver sources unmodified and implement the LTM layer under `cpp/ltm`.
  - The paper requires directed LTM edge weights, committed and blocked PIBT history, wait propagation with goal-wait ignore, weighted distances, and frequent restarts.
  - The local LTM adapter uses project-owned code copied from the upstream planner structure so upstream LaCAM* files remain untouched.
  - Full paper benchmark parity is not claimed yet; this completes the Phase1 structural gate and lightweight quantitative smoke.
- Tests / validation:
  - Phase1 smoke passed on `loop` with `baseline_sum_of_loss=15`, `ltm_sum_of_loss=15`, `committed=1305`, `blocked=367`.
  - Phase1 smoke passed on `random-32-32-10` with `baseline_sum_of_loss=76`, `ltm_sum_of_loss=76`, `committed=333`.
  - Phase0 regression smoke passed: upstream `test_all.exe` 7/7 and project `phase0_smoke.exe` `sum_of_loss=15`.
- Follow-up:
  - Superseded on 2026-05-21: expand paper-style quantitative parity as Phase1a before Phase2.

## 2026-05-20 - initialize project guide and environment plan

- Request: 为 `C:\PROGRAMING\czr004` 写一份比粗略报告更细的项目指南，参考 `czr003` 的指南风格，并重新核实 LTM 的真实基座。
- Files changed:
  - `deep-research-report.md`
  - `environment.yml`
  - `.gitignore`
  - `docs/codex-worklog.md`
  - `outputs/reports/phase0_startup_plan.md`
- Commands run:
  - listed `czr004` files
  - checked `czr004` git status
  - read `czr004/deep-research-report (1).md`
  - read `czr003/deep-research-report.md`
  - extracted text from `2603.07891v1.pdf`
  - checked `czr004` conda environment and Python version
- Key observations:
  - `czr004` was not yet a git repository.
  - The existing `czr004` conda environment exists and uses Python `3.11.15`.
  - The LTM paper route should be treated as the only route for this project.
  - The LTM paper states the experimental LTM edge-weight range as `[0,10]`; the rough guide's `[1,5]` should be corrected.
- Tests / validation:
  - Document-only step. No solver tests were run.
- Follow-up:
  - Initialize git and commit project hygiene files.
  - Update `czr004` conda environment from `environment.yml`.
  - Select and record upstream LaCAM* before writing solver code.

## 2026-05-20 - correct route to LTM-to-NTM single line

- Request: Stop and correct the project guide. The project should not include an extra solver comparison or cross-base LTM/NTM migration. The goal is to advance from LTM to NTM on the LTM paper route.
- Files changed:
  - `deep-research-report.md`
  - `outputs/reports/phase0_startup_plan.md`
  - `docs/codex-worklog.md`
- Commands run:
  - searched project docs for cross-base and dual-line references
  - checked current `czr004` conda package list after interrupted install
- Key observations:
  - The previous guide incorrectly introduced a dual-line plan.
  - The corrected route is `LaCAM* -> LaCAM*+LTM -> LaCAM*+NTM`.
  - Baselines should stay within the LTM paper route.
  - The interrupted conda install did not add the requested packages; environment is still minimal Python 3.11.
- Tests / validation:
  - Document-only correction. No solver tests were run.
- Follow-up:
  - Commit this route correction.
  - Rerun dependency installation later if the user wants to proceed with environment setup.

## 2026-05-20 - scrub stale solver-route references from outlines

- Request: Recheck both the rough outline and detailed outline because stale old-route content remained.
- Files changed:
  - `deep-research-report (1).md`
  - `deep-research-report.md`
  - `outputs/reports/phase0_startup_plan.md`
  - `docs/codex-worklog.md`
- Commands run:
  - searched `C:\PROGRAMING\czr004` for stale old-route keywords
- Key observations:
  - The rough outline still contained many stale references from the original generated draft.
  - The detailed outline still contained explicit exclusion text that kept the stale route visible.
  - The rough outline is now rewritten as a corrected compact outline.
- Tests / validation:
  - Document-only cleanup. No solver tests were run.
- Follow-up:
  - Commit this cleanup.

## 2026-05-20 - incorporate review constraints and continue Phase0

- Request: Select objectively useful points from an external review, add them to the guide, and continue Phase0.
- Files changed:
  - `deep-research-report.md`
  - `deep-research-report (1).md`
  - `docs/implementation-notes.md`
  - `docs/upstream-baseline.md`
  - `docs/related-work-notes.md`
  - directory `.gitkeep` files
- Commands run:
  - checked git status
  - searched guide for phase and metric sections
  - created Phase0 directory skeleton
- Key observations:
  - Useful review points were about scientific story and measurement, not about changing the core route.
  - Added constraints to avoid pure LTM distillation.
  - Added expanded-node and high-level-expansion metrics for equal-node analysis.
  - Selected `Kei18/lacam2` as the LaCAM* upstream candidate, pending clone and exact commit record.
- Tests / validation:
  - Document and project hygiene only. No solver tests were run.
- Follow-up:
  - Install or update the `czr004` conda environment.
  - Clone `Kei18/lacam2` into `external/lacam2`.
  - Record exact upstream commit and run baseline smoke.

## 2026-05-20 - install Phase0 base environment and attempt upstream clone

- Request: Continue Phase0 after incorporating review constraints.
- Files changed:
  - `environment.yml`
  - `docs/implementation-notes.md`
  - `docs/upstream-baseline.md`
  - `outputs/reports/phase0_startup_plan.md`
  - `outputs/reports/phase0_environment_report.md`
- Commands run:
  - `conda env update -n czr004 -f environment.yml`
  - `conda run -n czr004` import checks
  - `cmake --version`, `ninja --version`, `git --version`
  - `git submodule add https://github.com/Kei18/lacam2.git external/lacam2`
- Key observations:
  - PyTorch extraction repeatedly failed on Windows due to a long package-cache path, so PyTorch was deferred out of the Phase0 base environment.
  - Phase0 C++/metrics dependencies installed and import checks passed.
  - The LaCAM* upstream submodule add failed because the shell could not resolve `github.com`.
  - No partial submodule state remained after the failed clone attempt.
- Tests / validation:
  - Verified Python imports for numpy, pandas, scipy, pyyaml, networkx, matplotlib, statsmodels, pytest, and pybind11.
  - Verified CMake, Ninja, and Git availability in `czr004`.
- Follow-up:
  - Retry `git submodule add` when shell DNS/network access is available.
  - Record exact `external/lacam2` commit before any solver edits.

## 2026-05-20 - complete Phase0 retry

- Request: Retry PyTorch after the Windows conda long-path issue and complete Phase0.
- Files changed:
  - `.gitignore`
  - `.gitmodules`
  - `environment.yml`
  - `cpp/compat/lacam2_windows_compat.hpp`
  - `docs/implementation-notes.md`
  - `docs/upstream-baseline.md`
  - `outputs/reports/phase0_startup_plan.md`
  - `outputs/reports/phase0_environment_report.md`
  - `docs/codex-worklog.md`
- Commands run:
  - retried PyTorch with `CONDA_PKGS_DIRS=C:\tmp\conda_pkgs`
  - rechecked `torch`, `torchvision`, and `torchaudio`
  - added `external/lacam2` as a git submodule
  - initialized recursive upstream submodules
  - installed C++ compiler dependencies
  - configured and built LaCAM* with MSVC/Ninja and a force-include compatibility header
  - ran `build-czr004-msvc-compat\test_all.exe`
  - attempted upstream `main.exe` CLI smoke on `assets/loop.*`
- Key observations:
  - PyTorch initially installed, but final `import torch` failed after toolchain troubleshooting; Phase0 does not accept PyTorch as ready.
  - Upstream LaCAM* commit is `61a4c40ce91ce18c06eb2fe070aa9f1951eecb8d`.
  - The upstream source tree is unmodified.
  - MSVC needs a build-only shim for Unix-style `uint`, the alternative token `or`, and MSVC's `_MT` macro collision.
  - The upstream library tests pass, but the upstream CLI timed out locally and is not yet a trusted experiment entrypoint.
- Tests / validation:
  - `test_all.exe`: 7 tests from 6 test suites passed.
  - Final PyTorch import check failed with a DLL load error; forced CPU reinstall was not run after approval was denied.
  - CLI loop smoke timed out and is recorded as a Phase1 entrypoint issue.
- Follow-up:
  - Start Phase1 by creating an LTM implementation checklist against the PDF.
  - Before benchmark experiments, choose either a local adapter CLI or a repaired upstream CLI path without changing LaCAM* search semantics.
  - Superseded on 2026-05-20: PyTorch is now fixed as GPU `cu124` wheels in the `czr004` environment.

## 2026-05-20 - fix Phase0 blockers (CLI hang + smoke + PyTorch)

- Request: Read latest Phase0 reports and fix outstanding problems.
- Files changed:
  - `cpp/tools/phase0_smoke.cpp`
  - `cpp/tools/CMakeLists.txt`
  - `scripts/build_lacam2_upstream.ps1`
  - `scripts/phase0_smoke.ps1`
  - `docs/implementation-notes.md`
  - `docs/upstream-baseline.md`
  - `outputs/reports/phase0_environment_report.md`
  - `outputs/reports/phase0_startup_plan.md`
  - `docs/codex-worklog.md`
- Commands run:
  - reproduced upstream `main.exe` hang and passing `test_planner.exe`
  - built `build/phase0-smoke/phase0_smoke.exe`
  - ran `scripts/phase0_smoke.ps1`
  - attempted a temporary PyTorch CPU-wheel recovery in `czr004`
- Key observations:
  - Upstream `main.exe` appears unreliable; argparse defines both `-v/--version` and `-v/--verbose`, but the full CLI timeout root cause was not proven.
  - Library-level solve path is healthy; project-owned `phase0_smoke.exe` completes loop-3 with `sum_of_loss=15`.
  - Superseded on 2026-05-20: the accepted PyTorch stack is now GPU `2.5.1+cu124`, not CPU.
- Tests / validation:
  - `test_all.exe`: 7/7 passed.
  - `phase0_smoke.exe`: exit 0, `sum_of_loss=15`.
  - `import torch`: success.
- Follow-up:
  - Start Phase1 LTM checklist against PDF.
  - Keep upstream sources unmodified; add LTM adapter layer under `cpp/ltm`.

## 2026-05-20 - fix czr004 GPU PyTorch environment

- Request: Solve the `czr004` conda environment now, using GPU PyTorch rather than CPU PyTorch, so Phase1 can start.
- Files changed:
  - `environment.yml`
  - `docs/implementation-notes.md`
  - `outputs/reports/phase0_environment_report.md`
  - `outputs/reports/phase0_startup_plan.md`
  - `docs/codex-worklog.md`
- Commands run:
  - checked `nvidia-smi` and existing `torch` CUDA state
  - removed conda CPU `pytorch`/`libtorch` packages
  - installed PyTorch from official CUDA 12.4 pip wheels
  - force-reinstalled `pillow==10.4.0` to fix `torchvision` DLL loading
  - ran `scripts/phase0_smoke.ps1`
- Key observations:
  - The machine has an NVIDIA GeForce RTX 4070 Laptop GPU and the driver reports CUDA 13.1 capability.
  - Conda had installed `pytorch-cuda=12.4` but still selected CPU `pytorch`/`libtorch`, so `torch.version.cuda` stayed `None`.
  - The accepted stack is `torch 2.5.1+cu124`, `torchvision 0.20.1+cu124`, and `torchaudio 2.5.1+cu124`.
- Tests / validation:
  - `torch.cuda.is_available()`: `True`.
  - CUDA tensor smoke ran on `cuda:0`.
  - GPU device: `NVIDIA GeForce RTX 4070 Laptop GPU`.
  - `test_all.exe`: 7/7 passed.
  - `phase0_smoke.exe`: exit 0, `sum_of_loss=15`.
- Follow-up:
  - Phase1 can start with LTM paper-faithful implementation planning and a project-owned adapter entrypoint.
