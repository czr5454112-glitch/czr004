# czr004 Repair5F.1 Plan: Safety-Parity Closure and Bounded UpdateParams Selector Gate

**Branch:** `phase4f5p5-stable-attention-lau`
**Start after pushed commit:** `c46ad63cc1e77a166ba39313b847c4ee9cff0d4d`
**Status:** completed diagnostic closure / selector still not exported
**Promotion status:** `phase5p5_allowed=false`, `phase6_allowed=false`

**Repair5F.1 execution result (2026-06-01):** the force-additive parity bug was fixed by routing `--laur-force-additive` through the canonical additive LTM update path without LAUR feature extraction/runtime prediction. The one-row reproducer closes the original warehouse mismatch, and the full final-holdout rerun closes both parity controls:

```text
always_additive_defer:
  better / equal / worse = 0 / 30 / 0
  mean_delta_ratio_vs_ltm = 0.0

repair5f_candidate_additive_ltm:
  better / equal / worse = 0 / 30 / 0
  mean_delta_ratio_vs_ltm = 0.0

repair5f_candidate_lattice_oracle_static_proxy:
  better / equal / worse = 17 / 13 / 0
  mean_delta_ratio_vs_ltm = -0.018311948514033324
```

The rerun reports `safety_gates_passed=true` and `candidate_lattice_oracle_gate_passed=true`, but this remains diagnostic-only. `phase5p5_allowed=false`, `phase6_allowed=false`, and no selector/runtime artifact has been exported.
**Primary project goal:** use learning-enhanced `UpdateLTM` to replace LTM’s coarse additive update and beat `LaCAM*+LTM` under closed-loop solver metrics, while preserving LaCAM*/PIBT semantics and exact fallback.

---

## 0. Executive decision

Repair5F-F1 produced the first strong evidence that the project is moving toward the main goal:

```text
repair5f_candidate_lattice_oracle_static_proxy:
  better / equal / worse = 17 / 13 / 0
  mean_delta_ratio_vs_ltm = -0.018311948514033324
  ratio_worse_than_ltm_groups = 0
  success_worse_than_ltm_groups = 0
```

This is much stronger than Repair5E.5 final holdout:

```text
repair5e5_crossfold_utility_reranker:
  better / equal / worse = 4 / 22 / 4
  mean_delta_ratio_vs_ltm = -0.0009245170596666741
```

It also beats the F1 random/shuffled diagnostics:

```text
random candidate diagnostic:
  6 / 17 / 7
  mean_delta_ratio_vs_ltm = +0.00297909950036667

shuffled utility diagnostic:
  4 / 17 / 9
  mean_delta_ratio_vs_ltm = +0.002559801023448285
```

Therefore, **bounded UpdateParams contains real closed-loop headroom**. This is the strongest Repair5 evidence so far.

However, F1 cannot promote because a strict safety gate failed:

```text
force_additive_parity_exact = false
exact_additive_candidate_parity_exact = true
safety_gates_passed = false
candidate_lattice_oracle_gate_passed = false
phase5p5_allowed = false
phase6_allowed = false
```

The correct next step is **not** to export a selector immediately. The correct next step is:

```text
Repair5F.1:
  close the force-additive / exact-additive parity discrepancy,
  rerun the bounded-lattice holdout under clean parity,
  and only then build a conservative selector.
```

---

## 1. Interpretation of the F1 result

### 1.1 What is genuinely good

F1 completed full final-holdout coverage:

```text
maps = random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
agent_counts = 50, 100
instance_ids = 21..25
candidate_count = 47
expected unique rows = 1530
deduped unique rows = 1530
missing rows = 0
```

The audit independently recomputed the paired stats and found that the report is consistent with raw logs and derived CSVs.

The important scientific result is:

```text
The bounded UpdateParams search space has much stronger oracle headroom
than the 8-rule Repair5E selector space.
```

That is direct progress toward replacing additive `UpdateLTM`.

### 1.2 What is blocked

The strict force-additive defer control failed:

```text
always_additive_defer:
  better / equal / worse = 0 / 29 / 1
  mean_delta_ratio_vs_ltm = +0.0015595851053333313
```

But the exact additive candidate was exact parity:

```text
repair5f_candidate_additive_ltm:
  better / equal / worse = 0 / 30 / 0
  mean_delta_ratio_vs_ltm = 0.0
```

This distinction matters. It suggests the bounded lattice itself is not necessarily unsafe. The discrepancy is probably in the control path, method wrapper, diagnostic runner, or `always_additive_defer` semantics.

Still, the project rule is clear:

```text
No selector/runtime export until fallback and force-additive parity are understood and exact.
```

---

## 2. Repair5F.1 objective

Primary question:

```text
Can we resolve the force-additive parity discrepancy without weakening the safety gate,
then safely proceed to a learned/data-driven bounded UpdateParams selector?
```

Repair5F.1 must not lower the gate. It must either:

```text
A. find and fix a real parity bug, then rerun;
B. prove `always_additive_defer` is not the correct parity control for F1 and replace it with a stricter canonical exact-additive control, with documentation and tests;
C. if neither is possible, stop Repair5F selector work.
```

---

## 3. Non-negotiable constraints

Do not:

```text
- claim Phase5.5 or Phase6
- export selector/runtime artifact before parity closure
- modify external/lacam2/lacam2/**
- change PIBT, LaCAM*, candidate generation, pruning, conflict semantics, OPEN/EXPLORED, incumbent pruning, or restart semantics
- introduce action prediction
- introduce learned restart
- introduce richer LTM representation
- use exact map/agent/instance recovery table as the selector
- consume final eval logs when creating runtime artifacts
```

Must preserve:

```text
--laur-disable equivalent to LaCAM*+LTM
--laur-force-additive exact additive LTM parity
exact additive UpdateParams candidate parity
support/eval leakage = false
phase5p5_allowed=false
phase6_allowed=false
```

---

## 4. Required F1.1 deliverables

### P0. Evidence freeze and provenance note

Create:

```text
outputs/reports/phase5p5_repair5f_f1_decision_report.md
outputs/reports/phase5p5_repair5f_f1_decision_summary.json
```

Record:

```text
- F1 oracle result: 17 / 13 / 0, mean -0.018311948514033324
- F1 random/shuffled diagnostics
- full raw coverage
- audit result
- safety blocker
- exact additive candidate parity
- force-additive parity failure
- no selector/runtime artifact exported
```

Update:

```text
docs/codex-worklog.md
czr004_repair5f_bounded_updateparams_decision_plan.md
```

### P1. Parity discrepancy autopsy

Implement:

```text
scripts/analyze_repair5f_force_additive_parity.py
```

Inputs:

```text
outputs/logs/phase5p5_repair5f_candidate_probe/phase5p5_repair5f_candidate_probe.jsonl
outputs/logs/phase5p5_repair5f_candidate_probe/phase5p5_repair5f_candidate_probe_laur_updates.jsonl
outputs/tables/phase5p5_repair5f_updateparam_utility_wide.csv
outputs/tables/phase5p5_repair5f_updateparam_utility_long.csv
outputs/reports/phase5p5_repair5f_candidate_probe_summary.json
```

Outputs:

```text
outputs/reports/phase5p5_repair5f_force_additive_parity_autopsy.md
outputs/reports/phase5p5_repair5f_force_additive_parity_autopsy_summary.json
outputs/tables/phase5p5_repair5f_force_additive_mismatch_rows.csv
```

Autopsy must identify:

```text
- exact mismatching map / agents / seed / method rows
- whether mismatch is only warehouse or also elsewhere
- difference between lacam_star_ltm, always_additive_defer, and repair5f_candidate_additive_ltm
- sum_of_loss, lower_bound, ratio, success, expanded_nodes, returned_solutions_count
- ltm_max_iterations, time_limit_sec, seed, node_budget_factor
- laur_enabled, laur_force_additive, laur_update_mode, laur_post_first_solution_only
- selected_rules and additive fallback counts
- whether method wrapper changed post-first-solution behavior
- whether duplicate raw rows affected the control row
```

### P2. Minimal reproducer

Implement or add a runner mode that reruns only the mismatch row(s):

```text
scripts/run_repair5f_force_additive_parity_reproducer.py
```

Outputs:

```text
outputs/logs/phase5p5_repair5f_force_additive_reproducer/*.jsonl
outputs/reports/phase5p5_repair5f_force_additive_reproducer_report.md
outputs/reports/phase5p5_repair5f_force_additive_reproducer_summary.json
```

Required rows for each mismatch case:

```text
lacam_star_ltm
always_additive_defer
repair5f_candidate_additive_ltm
laur-disable if available
laur-force-additive direct runner path if available
```

Run each with the exact same:

```text
map
agents
instance/seed
time_limit_sec
ltm_max_iterations
node_budget_factor
candidate lattice disabled/enabled as appropriate
```

### P3. Fix or redefine parity control

If the autopsy finds a real bug, fix it and add tests.

Possible bug classes to inspect:

```text
- always_additive_defer uses a different LAUR option set than exact additive candidate
- post_first_solution_only differs between controls
- force_additive path and candidate_additive path call different update-policy branches
- fallback/defer behavior changes update timing
- one control emits additive UpdateParams before first solution while the other defers
- duplicate writer path kept a stale row before dedupe
- method naming selects a wrong config branch
```

If `always_additive_defer` is intentionally not equivalent to canonical additive candidate, document that and replace the F1 safety gate with two explicit controls:

```text
canonical_exact_additive_candidate_parity = required exact
legacy_always_additive_defer_parity = diagnostic, not safety-defining
```

Only make this replacement if it is backed by code inspection and reproducer evidence. Do not weaken the safety gate silently.

### P4. Rerun F1 candidate probe after parity closure

After the parity fix or documented control replacement:

```text
rerun full final-holdout Repair5F candidate probe
```

Required outputs:

```text
outputs/reports/phase5p5_repair5f_candidate_probe_rerun_report.md
outputs/reports/phase5p5_repair5f_candidate_probe_rerun_summary.json
outputs/reports/phase5p5_repair5f_candidate_probe_rerun_audit.md
outputs/tables/phase5p5_repair5f_updateparam_utility_rerun_long.csv
outputs/tables/phase5p5_repair5f_updateparam_utility_rerun_wide.csv
```

Rerun gates:

```text
canonical exact additive parity = true
force-additive parity = true, unless formally replaced and justified
support/eval leakage = false
candidate_lattice_oracle better > worse
candidate_lattice_oracle mean_delta_ratio_vs_ltm <= -0.003
candidate_lattice_oracle ratio_worse_than_ltm_groups <= 1
candidate_lattice_oracle success_worse_than_ltm_groups = 0
random/shuffled diagnostics remain weaker than oracle
phase5p5_allowed=false
phase6_allowed=false
```

### P5. Selector is allowed only after P4 passes

If P4 passes, implement one conservative selector:

```text
scripts/create_repair5f_updateparam_selector_runtime.py
artifacts/models/laur_ltm/repair5f_bounded_updateparam_selector/
```

Recommended first selector:

```text
deterministic KNN / radius utility selector over bounded UpdateParams candidates
```

Do not start with a neural-only dependency.

Selector rules:

```text
- use support/train IDs 1..20 only
- do not consume final holdout 21..25 while creating artifact
- require margin over additive
- require support count
- require map-family / agent-count balance if possible
- abstain to exact additive when confidence is low
- cap risky candidates
- log selected candidate ID and UpdateParams
```

Selector evaluation must compare:

```text
lacam_star_ltm
repair5e5_crossfold_utility_reranker
repair5f_candidate_lattice_oracle_static_proxy
repair5f_bounded_updateparam_selector
repair5f_bounded_updateparam_selector_force_additive_parity
repair5f_bounded_updateparam_selector_random_candidate_diagnostic
repair5f_bounded_updateparam_selector_shuffled_utility_diagnostic
```

Selector useful gate:

```text
selector better > worse
selector mean_delta_ratio_vs_ltm < 0
selector ratio_worse_than_ltm_groups <= 1
selector success_worse_than_ltm_groups = 0
selector beats random and shuffled diagnostics
selector does not collapse to exact additive parity
force-additive parity remains exact
phase5p5_allowed=false
phase6_allowed=false
```

---

## 5. Decision table after Repair5F.1

### Case A: parity fixed, oracle remains strong

Proceed to conservative bounded UpdateParams selector.

### Case B: parity fixed, oracle disappears

Treat F1 oracle as contaminated by the control bug. Stop Repair5F selector and reassess.

### Case C: exact additive candidate remains exact, legacy always-additive is proven noncanonical

Use canonical exact additive candidate as the safety control, but only after recording a clear justification and adding tests. Then rerun F1.

### Case D: parity discrepancy cannot be explained

Stop selector/runtime export. Do not proceed to Phase5.5.

### Case E: selector positive but random/shuffled positive too

Treat as spurious; improve selector objective or stop.

---

## 6. Validation requirements

Run:

```text
python -m py_compile scripts/analyze_repair5f_force_additive_parity.py scripts/run_repair5f_force_additive_parity_reproducer.py scripts/run_repair5f_updateparam_probe_table.py
python -m pytest tests/test_repair5f_updateparams.py
git diff --check
```

If C++ changes:

```text
scripts/build_phase1a_batch.ps1
```

If pytest is unavailable, record it explicitly.

Commit only Repair5F.1-related files and records. Leave unrelated dirty/untracked files untouched.

---

## 7. Codex prompt

```text
Continue czr004 on branch phase4f5p5-stable-attention-lau after commit c46ad63cc1e77a166ba39313b847c4ee9cff0d4d.

Goal:
  Repair5F.1: close the force-additive parity discrepancy from the bounded UpdateParams candidate probe, then rerun the F1 lattice probe. Do not export a selector until safety parity is resolved.

Main project objective:
  Use learning-enhanced UpdateLTM to replace LTM's coarse additive update and eventually beat LaCAM*+plain additive LTM under closed-loop solver metrics, without changing LaCAM*/PIBT semantics.

Read first:
  deep-research-report.md
  phase4_6_laur_ltm_codex_execution_plan.md
  czr004_repair5f_bounded_updateparams_decision_plan.md
  outputs/reports/phase5p5_repair5f_candidate_probe_report.md
  outputs/reports/phase5p5_repair5f_candidate_probe_summary.json
  outputs/reports/phase5p5_repair5f_candidate_probe_audit.md
  outputs/tables/phase5p5_repair5f_updateparam_utility_long.csv
  outputs/tables/phase5p5_repair5f_updateparam_utility_wide.csv

Preserve this interpretation:
  - F1 bounded UpdateParams lattice oracle is strong:
      17 / 13 / 0, mean_delta_ratio_vs_ltm = -0.018311948514033324.
  - Random and shuffled F1 diagnostics are much weaker.
  - Exact additive candidate parity is exact:
      0 / 30 / 0, mean = 0.0.
  - The strict always_additive_defer / force-additive parity control failed:
      0 / 29 / 1, mean = +0.0015595851053333313.
  - Therefore Repair5F is promising but safety-blocked.
  - No selector/runtime artifact may be exported until parity is resolved.
  - phase5p5_allowed=false and phase6_allowed=false remain mandatory.

Do not:
  - claim Phase5.5 or Phase6
  - modify external/lacam2/lacam2/**
  - change PIBT, LaCAM*, candidate generation, pruning, conflict semantics, OPEN/EXPLORED, incumbent pruning, or restart semantics
  - introduce action prediction
  - introduce learned restart
  - introduce richer LTM representation
  - use exact map/agent/instance recovery table as the selector
  - consume eval logs while creating runtime artifacts

Tasks:
  1. Update docs/codex-worklog.md and write:
       outputs/reports/phase5p5_repair5f_f1_decision_report.md
       outputs/reports/phase5p5_repair5f_f1_decision_summary.json
     Record that the lattice oracle metric gate is strong but the safety gate is blocked.

  2. Implement:
       scripts/analyze_repair5f_force_additive_parity.py
     Inputs:
       outputs/logs/phase5p5_repair5f_candidate_probe/phase5p5_repair5f_candidate_probe.jsonl
       outputs/logs/phase5p5_repair5f_candidate_probe/phase5p5_repair5f_candidate_probe_laur_updates.jsonl
       outputs/tables/phase5p5_repair5f_updateparam_utility_long.csv
       outputs/tables/phase5p5_repair5f_updateparam_utility_wide.csv
       outputs/reports/phase5p5_repair5f_candidate_probe_summary.json
     Outputs:
       outputs/reports/phase5p5_repair5f_force_additive_parity_autopsy.md
       outputs/reports/phase5p5_repair5f_force_additive_parity_autopsy_summary.json
       outputs/tables/phase5p5_repair5f_force_additive_mismatch_rows.csv
     The autopsy must identify exact mismatching map/agents/seed rows and compare:
       lacam_star_ltm
       always_additive_defer
       repair5f_candidate_additive_ltm
     Include sum_of_loss, lower_bound, ratio, success, expanded_nodes, returned_solutions_count, laur options, selected_rules, fallback counts, and duplicate-row status.

  3. Implement a minimal reproducer:
       scripts/run_repair5f_force_additive_parity_reproducer.py
     Rerun only the mismatch row(s), with:
       lacam_star_ltm
       always_additive_defer
       repair5f_candidate_additive_ltm
       laur-disable if available
       laur-force-additive direct path if available
     Write:
       outputs/logs/phase5p5_repair5f_force_additive_reproducer/*.jsonl
       outputs/reports/phase5p5_repair5f_force_additive_reproducer_report.md
       outputs/reports/phase5p5_repair5f_force_additive_reproducer_summary.json

  4. If a real parity bug is found, fix it and add tests. Inspect especially:
       method wrapper differences
       post_first_solution_only differences
       force_additive vs exact additive candidate policy branches
       fallback/defer timing
       duplicate writer stale rows
       method naming/config branch selection

  5. If always_additive_defer is proven not to be the canonical parity control but exact additive candidate is canonical and parity-exact, document that clearly. Do not silently weaken the safety gate. Add tests and update reports to define:
       canonical_exact_additive_candidate_parity = required exact
       legacy_always_additive_defer_parity = diagnostic, not safety-defining
     Only do this if the reproducer and code audit justify it.

  6. Rerun full final-holdout Repair5F candidate probe after parity closure.
     Write:
       outputs/reports/phase5p5_repair5f_candidate_probe_rerun_report.md
       outputs/reports/phase5p5_repair5f_candidate_probe_rerun_summary.json
       outputs/reports/phase5p5_repair5f_candidate_probe_rerun_audit.md
       outputs/tables/phase5p5_repair5f_updateparam_utility_rerun_long.csv
       outputs/tables/phase5p5_repair5f_updateparam_utility_rerun_wide.csv

  7. Do not implement selector/runtime unless the rerun passes:
       canonical exact additive parity = true
       force-additive parity = true unless formally replaced and justified
       support/eval leakage = false
       candidate_lattice_oracle better > worse
       candidate_lattice_oracle mean_delta_ratio_vs_ltm <= -0.003
       candidate_lattice_oracle ratio_worse_than_ltm_groups <= 1
       candidate_lattice_oracle success_worse_than_ltm_groups = 0
       random/shuffled diagnostics remain weaker than oracle
       phase5p5_allowed=false
       phase6_allowed=false

Validation:
  - py_compile all new/modified Python scripts
  - python -m pytest tests/test_repair5f_updateparams.py if available
  - git diff --check
  - scripts/build_phase1a_batch.ps1 if C++ changed
  - commit and push only Repair5F.1-related files and records
  - leave unrelated dirty/untracked files untouched

Commit message:
  repair5f: close updateparam parity decision gate
```
