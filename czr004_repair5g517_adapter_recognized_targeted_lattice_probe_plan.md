# Repair5G.5.17 Adapter-Recognized Targeted Lattice Probe Plan

Date: 2026-06-08

## Scope

Implement a real G5.17 execution round:

- add project-owned adapter recognition for the ten G5.16 `repair5g516_*` update-parameter candidates;
- build and smoke the adapter before any solver probe;
- run the 20-context targeted local counterfactual probe only after adapter gates pass;
- compare the old 14-candidate oracle with the new 24-candidate oracle;
- continue to full-primary/ranker/safety work only if the targeted candidate-space oracle improves.

## Hard Constraints

- Do not modify `external/lacam2/lacam2/**`.
- Do not change PIBT, LaCAM*, candidate generation, conflicts, pruning, OPEN/EXPLORED, rewrite, incumbent, or restart semantics.
- Do not introduce action prediction, priority prediction, learned restart, h-values, candidate deletion, MAPF action logits, or learned solver control.
- Do not run or inspect IDs `166..205`.
- Use local PC execution and `--max-workers 1`.
- Use isolated `phase5p5_repair5g517_*` output paths.
- Keep runtime, Phase5.5, Phase6, and AAAI claims closed.

## Execution Gates

1. Adapter recognition verifier must produce `adapter_recognition_passed_continue_local_probe`.
2. `phase1a_batch` must build after the C++ adapter change.
3. Adapter smoke must prove all ten repair candidates are recognized and have update-parameter fingerprints.
4. Targeted probe integrity must prove exactly 960 rows or stop with `targeted_probe_integrity_failed`.
5. Oracle reassessment must prove repair candidate-space gain before full-primary or ranker work continues.
6. If there is no oracle gain, stop with `targeted_repair_lattice_no_oracle_gain_continue_lattice_design`.

## Planned Commands

```text
python scripts\verify_repair5g517_adapter_recognition.py
scripts\build_phase1a_batch.ps1
python scripts\run_repair5g517_adapter_smoke.py --overwrite
python scripts\run_repair5g517_targeted_probe.py --overwrite --max-workers 1
python scripts\analyze_repair5g517_targeted_lattice_oracle.py
python scripts\run_repair5g517_full_primary_probe.py --overwrite --max-workers 1
python scripts\write_repair5g517_safety_update.py
python scripts\write_repair5g517_decision.py
```

Validation also includes `python -m py_compile` for new/modified Python scripts, JSON parse checks, CSV row-count checks, reserved-ID guard rejection for `166`, leakage checks when a feature matrix exists, and `git diff --check`.
