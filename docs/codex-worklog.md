# Codex Worklog

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
