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
  - The LTM paper states `LaCAM*+LTM` is built on the original LaCAM* codebase, not LaCAM3.
  - The paper does not directly compare against hybrid LaCAM3 because LaCAM3 performance depends on parallelization and LNS integration; when parallelism is disabled, LaCAM3 is treated as equivalent to LaCAM*+SUO.
  - The LTM paper states the experimental LTM edge-weight range as `[0,10]`; the rough guide's `[1,5]` should be corrected.
- Tests / validation:
  - Document-only step. No solver tests were run.
- Follow-up:
  - Initialize git and commit project hygiene files.
  - Update `czr004` conda environment from `environment.yml`.
  - Select and record upstream LaCAM* and LaCAM3 repositories before writing solver code.
