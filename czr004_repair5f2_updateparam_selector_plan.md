# czr004 Repair5F.2 Plan: Support-Trained Bounded UpdateParams Selector Diagnostic

**Branch:** `phase4f5p5-stable-attention-lau`
**Start after commit:** `30a457a76e6692400ff985ee3b8603195e3ae12e`
**Status:** proposed next diagnostic step
**Promotion status:** `phase5p5_allowed=false`, `phase6_allowed=false`
**Main project objective:** use learning-enhanced `UpdateLTM` to replace the coarse additive update in the LTM paper and beat `LaCAM*+LTM` under closed-loop solver metrics.

---

## 0. Why F2 exists

Repair5F.1 closed the safety-parity blocker from F1.

Post-fix rerun result:

```text
always_additive_defer:
  0 / 30 / 0
  mean_delta_ratio_vs_ltm = 0.0

repair5f_candidate_additive_ltm:
  0 / 30 / 0
  mean_delta_ratio_vs_ltm = 0.0

repair5f_candidate_lattice_oracle_static_proxy:
  17 / 13 / 0
  mean_delta_ratio_vs_ltm = -0.018311948514033324
  ratio_worse_than_ltm_groups = 0
  success_worse_than_ltm_groups = 0
```

The safety gates now pass:

```text
force_additive_parity_exact = true
exact_additive_candidate_parity_exact = true
safety_gates_passed = true
support_eval_leakage = false
solver_semantic_changes = false
```

This changes the research state. We no longer need to ask whether a bounded `UpdateParams` space contains useful headroom. It does, at least in the F1 final-holdout diagnostic. The next question is whether a selector can recover that headroom from training/support evidence without seeing holdout outcomes.

---

## 1. Current interpretation

### 1.1 What is now positive

Repair5F has produced the strongest signal so far that the project goal is technically reachable inside `UpdateLTM`.

The strong result is not a selector claim. It is an oracle/headroom claim:

```text
There exist bounded UpdateParams candidates that beat the additive LTM update
on closed-loop holdout metrics.
```

This is directly aligned with the project goal because it keeps the intervention inside:

```text
PIBT trace -> UpdateLTM -> DirectedTrafficMap -> WeightedDistanceTable -> LTM guidance
```

### 1.2 What remains unsolved

The method is not done because the oracle used holdout outcomes to choose the best candidate. A real learned/data-driven method must choose candidates from support data only.

The hard question is now:

```text
Can a selector trained/tuned only on support IDs 1..20 choose bounded UpdateParams
that improve held-out IDs 21..25 better than random/shuffled controls?
```

### 1.3 Why not export runtime immediately

Do not export selector/runtime yet.

The F1 oracle is a static proxy over already-probed candidates. It proves the candidate family has headroom. It does not prove:

```text
- a support-trained selector can choose the right candidate
- the selector signal beats random/shuffled controls
- a C++ runtime artifact can reproduce the table-level diagnostic
- a dynamic per-update policy is safe
```

F2 must therefore be a selector diagnostic first, and only then a runtime export.

---

## 2. F2 scope

### 2.1 Name

```text
Repair5F.2: Support-Trained Bounded UpdateParams Selector Diagnostic
```

### 2.2 Allowed intervention

F2 may choose a bounded `UpdateParams` candidate, but it must not change solver semantics.

Allowed:

```text
choose alpha_commit
choose alpha_block
choose alpha_wait_spillover
choose rho_decay
defer to exact additive
calibrated abstention / fallback
support-trained KNN or listwise utility scoring
```

Forbidden:

```text
modifying PIBT
modifying LaCAM*
changing candidate generation
changing pruning
changing conflict semantics
learned restart
action prediction
richer LTM representation
exact map/agent/instance lookup as selector
using final-holdout outcomes while building the selector
claiming Phase5.5 or Phase6
```

### 2.3 Selector type

The first F2 selector should be conservative and interpretable:

```text
deterministic KNN / radius-neighbor utility selector
or small table-level listwise/risk-calibrated selector
```

Do **not** start with a neural-only dependency. A neural selector can be considered only after a deterministic support-trained selector shows non-spurious signal.

---

## 3. Required inputs

Existing F1/F1.1 inputs:

```text
outputs/reports/phase5p5_repair5f_candidate_probe_rerun_report.md
outputs/reports/phase5p5_repair5f_candidate_probe_rerun_summary.json
outputs/reports/phase5p5_repair5f_candidate_probe_rerun_audit.md
outputs/tables/phase5p5_repair5f_updateparam_utility_rerun_long.csv
outputs/tables/phase5p5_repair5f_updateparam_utility_rerun_wide.csv
outputs/logs/phase5p5_repair5f_candidate_probe_rerun/*.jsonl
```

F2 must generate new support candidate evidence over IDs `1..20`, because the current rerun utility table covers final holdout IDs `21..25`.

---

## 4. Required F2 work

## F2-A. Generate support candidate probe table

Implement or extend:

```text
scripts/run_repair5f_updateparam_probe_table.py
```

Run the same 47-candidate bounded lattice over support IDs:

```text
maps:
  random-32-32-20
  maze-32-32-4
  warehouse-10-20-10-2-1

agents:
  50
  100

support_instance_ids:
  1..20

time_limit_sec:
  3.0

ltm_max_iterations:
  4
```

Write:

```text
outputs/logs/phase5p5_repair5f_selector_support_probe/phase5p5_repair5f_selector_support_probe.jsonl
outputs/logs/phase5p5_repair5f_selector_support_probe/phase5p5_repair5f_selector_support_probe_commands.jsonl
outputs/logs/phase5p5_repair5f_selector_support_probe/phase5p5_repair5f_selector_support_probe_laur_updates.jsonl

outputs/tables/phase5p5_repair5f_selector_support_utility_long.csv
outputs/tables/phase5p5_repair5f_selector_support_utility_wide.csv

outputs/reports/phase5p5_repair5f_selector_support_probe_report.md
outputs/reports/phase5p5_repair5f_selector_support_probe_summary.json
outputs/reports/phase5p5_repair5f_selector_support_probe_audit.md
```

Required checks:

```text
expected rows = maps * agent_counts * support_ids * candidate_count
missing rows = 0
schema errors = 0
force-additive parity exact on support controls
exact additive candidate parity exact
support/final overlap = 0
```

---

## F2-B. Build selector training table

Implement:

```text
scripts/create_repair5f_selector_training_table.py
```

Inputs:

```text
outputs/tables/phase5p5_repair5f_selector_support_utility_long.csv
outputs/tables/phase5p5_repair5f_selector_support_utility_wide.csv
outputs/logs/phase5p5_repair5f_selector_support_probe/phase5p5_repair5f_selector_support_probe_laur_updates.jsonl
outputs/tables/phase5p5_repair5f_updateparam_utility_rerun_long.csv
outputs/tables/phase5p5_repair5f_updateparam_utility_rerun_wide.csv
outputs/logs/phase5p5_repair5f_candidate_probe_rerun/phase5p5_repair5f_candidate_probe_rerun_laur_updates.jsonl
```

Outputs:

```text
outputs/tables/phase5p5_repair5f_selector_train_contexts.csv
outputs/tables/phase5p5_repair5f_selector_holdout_contexts.csv
outputs/reports/phase5p5_repair5f_selector_training_table_report.md
outputs/reports/phase5p5_repair5f_selector_training_table_summary.json
```

For each context, include only selector-available features:

```text
map_width
map_height
obstacle_ratio
agents
iteration-level aggregate runtime features if available
traffic_before summary
trace summary
best_ratio_before
has_solution_before
improved_last_iteration
time remaining
```

Exclude leakage fields:

```text
instance_id as a decision feature
seed as a decision feature
candidate outcome columns from holdout
best candidate from holdout
ratio_delta_vs_ltm from holdout
success_delta from holdout
any final solver outcome not available before choosing
```

It is acceptable to keep `map_family` or map-size features for diagnostics, but the selector report must explicitly distinguish:

```text
feature-based selection
vs exact map/agent recovery
```

---

## F2-C. Train/tune conservative selector

Implement:

```text
scripts/tune_repair5f_updateparam_selector.py
```

Selector candidates:

```text
1. conservative KNN utility selector
2. radius-neighbor selector with abstention
3. group-balanced utility selector
4. candidate-risk-capped selector
```

Required selector hyperparameters:

```text
min_support_count
min_effective_neighbors
max_neighbor_distance
min_predicted_margin
max_candidate_worse_rate
max_group_worse_rate
min_fold_agreement if OOF support is available
non_additive_budget
additive_fallback_threshold
candidate whitelist / blacklist
```

Important: candidate selection must be based on support utility only, never final holdout utility.

Outputs:

```text
outputs/reports/phase5p5_repair5f_selector_threshold_sweep_report.md
outputs/reports/phase5p5_repair5f_selector_threshold_sweep_summary.json
outputs/tables/phase5p5_repair5f_selector_threshold_sweep.csv
```

Primary tuning target on support/OOF diagnostics:

```text
better > worse
mean_delta_ratio_vs_ltm < 0
ratio_worse_than_ltm_groups <= 1
success_worse_than_ltm_groups = 0
selected_nonadditive_cases > 0
```

But do not use final holdout to tune thresholds.

---

## F2-D. Final holdout selector simulation

Implement:

```text
scripts/evaluate_repair5f_updateparam_selector_simulation.py
```

This is a table-level simulation: the selector chooses a candidate for each final holdout case using only permitted features and support-trained thresholds; the evaluator then joins to the already-probed final-holdout candidate outcome.

Inputs:

```text
selector artifact or selector spec from support training
outputs/tables/phase5p5_repair5f_updateparam_utility_rerun_wide.csv
outputs/tables/phase5p5_repair5f_selector_holdout_contexts.csv
```

Outputs:

```text
outputs/tables/phase5p5_repair5f_selector_simulation_paired.csv
outputs/tables/phase5p5_repair5f_selector_simulation_decisions.csv
outputs/reports/phase5p5_repair5f_selector_simulation_report.md
outputs/reports/phase5p5_repair5f_selector_simulation_summary.json
```

Compare:

```text
repair5f_support_trained_selector_simulation
repair5f_candidate_lattice_oracle_static_proxy
repair5f_random_candidate_diagnostic
repair5f_shuffled_utility_diagnostic
repair5e5_crossfold_utility_reranker
repair5e5_shuffled_labels_diagnostic
always_additive_defer
repair5f_candidate_additive_ltm
```

Required metrics:

```text
better / equal / worse
mean_delta_ratio_vs_ltm
ratio_worse_than_ltm_groups
success_worse_than_ltm_groups
zero_nonadditive_groups
selected candidate distribution
abstention/additive fallback rate
candidate-specific realized risk
support margin vs realized delta
nearest distance vs realized delta
map/agent breakdown
```

---

## F2-E. Only if table simulation passes: export runtime artifact

Do **not** export C++ runtime until the table-level selector simulation passes.

If it passes, implement:

```text
scripts/create_repair5f_updateparam_selector_runtime.py
artifacts/models/laur_ltm/repair5f_bounded_updateparam_selector/
```

The runtime artifact must include:

```text
candidate_lattice.csv
candidate utility support table hash
selector thresholds
feature stats
allowed feature list
forbidden feature list
support IDs
forbidden final holdout IDs
script hashes
git provenance
diagnostic_only=true
phase5p5_allowed=false
phase6_allowed=false
solver_semantic_changes=false
```

C++ runtime requirements:

```text
- load candidate UpdateParams, not only 8 rule IDs
- log selected alpha_commit, alpha_block, alpha_wait_spillover, rho_decay
- exact additive fallback remains exact
- --laur-force-additive remains canonical additive LTM path
- do not dynamically change candidate after each update unless explicitly tested
```

Recommended first runtime behavior:

```text
select one bounded candidate at the first eligible post-first-solution update,
then lock that candidate for the run
```

This keeps runtime behavior closest to the static candidate-probe evidence. Fully dynamic per-update switching is deferred.

Runtime validation outputs:

```text
outputs/reports/phase5p5_repair5f_selector_runtime_report.md
outputs/reports/phase5p5_repair5f_selector_runtime_summary.json
outputs/tables/phase5p5_repair5f_selector_runtime_paired.csv
outputs/logs/phase5p5_repair5f_selector_runtime/*.jsonl
```

---

## 5. F2 pass criteria

### 5.1 Table-level selector simulation pass

F2 simulation is useful only if:

```text
support/final leakage = false
selector better > worse
selector mean_delta_ratio_vs_ltm < 0
selector ratio_worse_than_ltm_groups <= 1
selector success_worse_than_ltm_groups = 0
selector beats random candidate diagnostic
selector beats shuffled utility diagnostic
selector beats or clearly improves over E5 real selector
selector does not collapse to additive parity
phase5p5_allowed=false
phase6_allowed=false
```

Strong target:

```text
better - worse >= 3
mean_delta_ratio_vs_ltm <= -0.003
ratio_worse_than_ltm_groups = 0
```

### 5.2 Runtime pass

Runtime export is useful only if:

```text
force-additive parity exact
exact additive candidate parity exact
runtime selector reproduces table-level decision policy
actual runtime better > worse
actual runtime mean_delta_ratio_vs_ltm < 0
actual runtime ratio_worse_than_ltm_groups <= 1
actual runtime success_worse_than_ltm_groups = 0
random/shuffled diagnostics remain weaker
```

Still do not set `phase5p5_allowed=true`.

---

## 6. Decision table after F2

### Case A: table selector passes and runtime passes

Proceed to larger multi-map validation and clean provenance reruns.

### Case B: table selector passes but runtime fails

The table signal may be real, but runtime implementation or dynamic context mismatch is the issue. Fix runtime, do not change solver semantics.

### Case C: oracle remains strong but selector simulation fails

The candidate family is good, but features/objective are insufficient. Next step should be better feature representation or listwise/pairwise selector, not richer LTM yet.

### Case D: selector passes but random/shuffled also passes

Treat as spurious. Diagnose group bias and feature leakage. Do not promote.

### Case E: support probe contradicts final oracle

The F1 final-holdout oracle may be sample-specific. Expand cross-fold and map coverage before selector work.

---

## 7. Codex prompt

```text
Continue czr004 on branch phase4f5p5-stable-attention-lau after commit 30a457a76e6692400ff985ee3b8603195e3ae12e.

Goal:
  Implement Repair5F.2: support-trained bounded UpdateParams selector diagnostic. Do not export runtime until table-level selector simulation passes.

Main project objective:
  Use learning-enhanced UpdateLTM to replace LTM's coarse additive update and eventually beat LaCAM*+plain additive LTM under closed-loop solver metrics, without changing LaCAM*/PIBT semantics.

Read first:
  deep-research-report.md
  phase4_6_laur_ltm_codex_execution_plan.md
  czr004_repair5f_bounded_updateparams_decision_plan.md
  czr004_repair5f1_safety_parity_closure_plan.md
  czr004_repair5f2_updateparam_selector_plan.md
  outputs/reports/phase5p5_repair5f_candidate_probe_rerun_report.md
  outputs/reports/phase5p5_repair5f_candidate_probe_rerun_summary.json
  outputs/reports/phase5p5_repair5f_candidate_probe_rerun_audit.md
  outputs/tables/phase5p5_repair5f_updateparam_utility_rerun_long.csv
  outputs/tables/phase5p5_repair5f_updateparam_utility_rerun_wide.csv

Preserve this interpretation:
  Repair5F.1 closed the safety parity blocker.
  always_additive_defer = 0 / 30 / 0, mean 0.0.
  repair5f_candidate_additive_ltm = 0 / 30 / 0, mean 0.0.
  repair5f_candidate_lattice_oracle_static_proxy = 17 / 13 / 0, mean -0.018311948514033324.
  random candidate diagnostic = 6 / 18 / 6, mean 0.001419514395033339.
  shuffled utility diagnostic = 4 / 19 / 7, mean 0.0009148892173333441.
  Therefore the bounded UpdateParams family has strong oracle headroom, but no selector/runtime claim exists yet.
  phase5p5_allowed=false and phase6_allowed=false remain mandatory.

Do not:
  - claim Phase5.5 or Phase6
  - modify external/lacam2/lacam2/**
  - change PIBT, LaCAM*, candidate generation, pruning, conflict semantics, OPEN/EXPLORED, incumbent pruning, or restart semantics
  - introduce action prediction
  - introduce learned restart
  - introduce richer LTM representation
  - use exact map/agent/instance recovery table as selector
  - use final holdout outcomes while training/tuning selector thresholds
  - export runtime before table-level selector simulation passes

Tasks:
  1. Add czr004_repair5f2_updateparam_selector_plan.md to the repository root and update docs/codex-worklog.md.

  2. Generate support candidate probe evidence for IDs 1..20 using the same 47 bounded UpdateParams candidates.
     Write:
       outputs/logs/phase5p5_repair5f_selector_support_probe/phase5p5_repair5f_selector_support_probe.jsonl
       outputs/logs/phase5p5_repair5f_selector_support_probe/phase5p5_repair5f_selector_support_probe_commands.jsonl
       outputs/logs/phase5p5_repair5f_selector_support_probe/phase5p5_repair5f_selector_support_probe_laur_updates.jsonl
       outputs/tables/phase5p5_repair5f_selector_support_utility_long.csv
       outputs/tables/phase5p5_repair5f_selector_support_utility_wide.csv
       outputs/reports/phase5p5_repair5f_selector_support_probe_report.md
       outputs/reports/phase5p5_repair5f_selector_support_probe_summary.json
       outputs/reports/phase5p5_repair5f_selector_support_probe_audit.md
     Required checks:
       expected rows complete
       missing rows = 0
       schema errors = 0
       force-additive parity exact
       exact additive candidate parity exact
       support/final overlap = 0

  3. Implement scripts/create_repair5f_selector_training_table.py.
     Build selector-available support and holdout context tables.
     Write:
       outputs/tables/phase5p5_repair5f_selector_train_contexts.csv
       outputs/tables/phase5p5_repair5f_selector_holdout_contexts.csv
       outputs/reports/phase5p5_repair5f_selector_training_table_report.md
       outputs/reports/phase5p5_repair5f_selector_training_table_summary.json
     Exclude leakage fields:
       instance_id as decision feature
       seed as decision feature
       holdout candidate outcomes
       holdout best candidate
       holdout ratio_delta/success_delta
       final solver outcome not available before choosing

  4. Implement scripts/tune_repair5f_updateparam_selector.py.
     Train/tune conservative deterministic selectors using support data only:
       KNN utility selector
       radius-neighbor selector with abstention
       group-balanced utility selector
       candidate-risk-capped selector
     Sweep:
       min_support_count
       min_effective_neighbors
       max_neighbor_distance
       min_predicted_margin
       max_candidate_worse_rate
       max_group_worse_rate
       non_additive_budget
       additive_fallback_threshold
     Write:
       outputs/reports/phase5p5_repair5f_selector_threshold_sweep_report.md
       outputs/reports/phase5p5_repair5f_selector_threshold_sweep_summary.json
       outputs/tables/phase5p5_repair5f_selector_threshold_sweep.csv

  5. Implement scripts/evaluate_repair5f_updateparam_selector_simulation.py.
     Evaluate final holdout by joining the selector's chosen candidate to already-probed holdout outcomes.
     The selector must not use holdout outcomes to make decisions.
     Write:
       outputs/tables/phase5p5_repair5f_selector_simulation_paired.csv
       outputs/tables/phase5p5_repair5f_selector_simulation_decisions.csv
       outputs/reports/phase5p5_repair5f_selector_simulation_report.md
       outputs/reports/phase5p5_repair5f_selector_simulation_summary.json
     Compare against:
       repair5f_candidate_lattice_oracle_static_proxy
       repair5f_random_candidate_diagnostic
       repair5f_shuffled_utility_diagnostic
       repair5e5_crossfold_utility_reranker
       repair5e5_shuffled_labels_diagnostic
       always_additive_defer
       repair5f_candidate_additive_ltm

  6. Do not export runtime unless table-level selector simulation passes:
       support/final leakage = false
       selector better > worse
       selector mean_delta_ratio_vs_ltm < 0
       selector ratio_worse_than_ltm_groups <= 1
       selector success_worse_than_ltm_groups = 0
       selector beats random candidate diagnostic
       selector beats shuffled utility diagnostic
       selector improves over E5 real selector
       selector does not collapse to additive parity

  7. If table-level selector simulation passes, create a follow-up report recommending runtime export, but do not export runtime in this same commit unless explicitly safe and scoped.

Validation:
  - py_compile all new/modified Python scripts
  - run python -m pytest tests/test_repair5f_updateparams.py if available
  - run conda czr004 pytest path if default pytest is unavailable
  - run git diff --check
  - run scripts/build_phase1a_batch.ps1 if C++ changed
  - commit and push only Repair5F.2-related files and records
  - leave unrelated dirty/untracked files untouched

Commit message:
  repair5f: add support-trained updateparam selector diagnostic
```
