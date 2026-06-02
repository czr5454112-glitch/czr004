# czr004 Repair5F.3 Plan: Runtime Export + Static-Candidate Ablation for Bounded UpdateParams

**Branch:** `phase4f5p5-stable-attention-lau`
**Start after commit:** `41958611e35ee3993e7e1cfdf393c04d64f80a4a`
**Previous main implementation commit:** `f3d102b repair5f: add support-trained updateparam selector diagnostic`
**Artifact refresh commit:** `4195861 repair5f: refresh selector sweep artifacts`
**Status:** completed / diagnostic-only; runtime gates failed on parity controls
**Promotion status:** `phase5p5_allowed=false`, `phase6_allowed=false`

## Execution result, 2026-06-02

Repair5F.3 completed the requested runtime export, static-candidate ablation, final-holdout runtime evaluation, and table-vs-runtime audit without enabling Phase5.5 or Phase6.

Key outcome:

```text
repair5f_bounded_updateparam_selector_runtime:
  selected c100_b100_w075_d090 on all 30 final-holdout runtime cases
  better / equal / worse = 6 / 18 / 5
  mean_delta_ratio_vs_ltm = -0.0028361091041379303
  ratio_worse_than_ltm_groups = 1
  success_worse_than_ltm_groups = 0

repair5f_static_c100_b100_w075_d090:
  metric-identical to selector runtime
  candidate policy identical on eligible update cases

runtime-vs-table audit:
  mismatch_count = 0
  runtime_selected_candidate_matches_table_policy = true
  runtime_updateparams_match_artifact = true
  runtime_outcomes_match_table_when_deterministic = true
```

Interpretation:

```text
The Repair5F.3 artifact is a support-trained static bounded UpdateParams
replacement around c100_b100_w075_d090. It is not context-adaptive evidence.
```

Runtime gates did not pass:

```text
force_additive_parity_exact = false
exact_additive_candidate_parity_exact = false
runtime_gates_passed = false
phase5p5_allowed = false
phase6_allowed = false
```

The parity failure is isolated to runtime control disagreement rather than a table-policy mismatch: the selector/runtime artifact matched the F2 table policy with zero mismatches, but additive/force-additive runtime controls were not exactly equal to the baseline under the 3 second final-holdout run.

## 0. Project objective

The czr004 objective remains:

```text
Use learning-enhanced UpdateLTM to replace the coarse additive LTM update
from the LTM paper, and beat LaCAM*+plain additive LTM under closed-loop
solver metrics without changing LaCAM*/PIBT semantics.
```

Repair5F.3 must stay inside:

```text
PIBT trace
  -> UpdateLTM
  -> DirectedTrafficMap raw_count / normalized_weight
  -> WeightedDistanceTable
  -> existing LTM guidance path
```

Do not change:

```text
PIBT semantics
LaCAM* high-level search
candidate generation
conflict handling
OPEN/EXPLORED/rewrite semantics
incumbent pruning
restart semantics
external/lacam2/lacam2/**
```

## 1. Current evidence after Repair5F.2

### 1.1 Repair5F.1 closed the safety gate

Repair5F.1 rerun showed:

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
```

Safety gates:

```text
force_additive_parity_exact = true
exact_additive_candidate_parity_exact = true
safety_gates_passed = true
candidate_lattice_oracle_gate_passed = true
support_eval_leakage = false
phase5p5_allowed = false
phase6_allowed = false
```

Interpretation:

```text
The bounded UpdateParams lattice contains real closed-loop headroom.
The previous force-additive discrepancy is fixed.
```

### 1.2 Repair5F.2 table-level selector passed its F2 gates

Support probe:

```text
support IDs = 1..20
candidate rows = 5640 / 5640
missing rows = 0
schema errors = 0
force-additive parity exact = true
exact additive candidate parity exact = true
support/final overlap = 0
```

Support-only threshold sweep selected:

```text
selector_type = group_balanced_utility
min_support_count = 5
min_effective_neighbors = 3
max_neighbor_distance = 999.0
min_predicted_margin = 0.0
max_candidate_worse_rate = 0.5
max_group_worse_rate = 0.5
non_additive_budget = 1.0
```

Final holdout table simulation:

```text
repair5f_support_trained_selector_simulation:
  better / equal / worse = 6 / 19 / 5
  mean_delta_ratio_vs_ltm = -0.0027415721339999993
  ratio_worse_than_ltm_groups = 1
  success_worse_than_ltm_groups = 0
  selected_nonadditive_cases = 30
  additive_fallback_rate = 0.0
  table_simulation_passed = true
```

The selector beats the Repair5F random and shuffled diagnostics in this table-level evaluation:

```text
random candidate diagnostic:
  6 / 18 / 6
  mean_delta_ratio_vs_ltm = 0.001419514395033339

shuffled utility diagnostic:
  4 / 19 / 7
  mean_delta_ratio_vs_ltm = 0.0009148892173333441
```

### 1.3 Important limitation: the selector collapsed to one candidate

The selected candidate distribution is:

```text
c100_b100_w075_d090: 30 / 30 final holdout decisions
```

This means the current "selector" is effectively a support-trained static bounded UpdateParams choice:

```text
alpha_commit         = 1.00
alpha_block          = 1.00
alpha_wait_spillover = 0.75
rho_decay            = 0.90
```

This is still useful and aligned with the UpdateLTM objective, because it is a data-driven replacement of the additive update. But it is not yet strong evidence for context-adaptive selection.

Repair5F.3 must therefore include a static-candidate ablation. If the runtime selector exactly equals a fixed global candidate, the report must say so plainly.

### 1.4 Another limitation: E5 shuffled remains numerically strong

The final holdout comparator still includes:

```text
repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic:
  7 / 20 / 3
  mean_delta_ratio_vs_ltm = -0.0039024738501666654
```

This is not the same diagnostic family as Repair5F random/shuffled, but it remains a cautionary comparator. Do not claim a broad learned-utility victory merely because F2 passed its own table gates.

## 2. Repair5F.3 objective

Call the next step:

```text
Repair5F.3: Runtime Export + Static-Candidate Ablation
```

Primary question:

```text
Does the support-trained bounded UpdateParams policy reproduce its table-level
gain in actual closed-loop runtime, while preserving exact additive fallback
and beating Repair5F random/shuffled controls?
```

Secondary question:

```text
Is the current benefit best described as:
  A. support-trained global/static UpdateParams replacement, or
  B. genuinely context-adaptive UpdateParams selection?
```

Based on F2, expect A unless the runtime export or an improved selector introduces nontrivial decision diversity without leakage.

## 3. Required work

## P0. Documentation and worklog

Create/update:

```text
czr004_repair5f3_runtime_export_static_ablation_plan.md
docs/codex-worklog.md
outputs/reports/phase5p5_repair5f2_final_interpretation.md
```

The F2 final interpretation must state:

```text
- F2 table-level selector passed the predeclared gates.
- F2 was support-only tuned and final_holdout_used_for_tuning=false.
- The selected policy chose c100_b100_w075_d090 on all final holdout cases.
- Therefore the current result is best viewed as a support-trained static bounded UpdateParams rule unless runtime or later selectors prove context adaptivity.
- Runtime export is allowed only as diagnostic follow-up.
- phase5p5_allowed=false and phase6_allowed=false remain mandatory.
```

## P1. Runtime artifact export

Implement:

```text
scripts/create_repair5f_updateparam_selector_runtime.py
artifacts/models/laur_ltm/repair5f_bounded_updateparam_selector/
```

The runtime artifact must record:

```text
schema_version
source commit
selector_type
selected spec
allowed feature names
forbidden feature names
candidate lattice hash
support utility table hash
threshold sweep hash
simulation summary hash
selected candidate ID(s)
UpdateParams for every selectable candidate
additive fallback candidate
phase5p5_allowed=false
phase6_allowed=false
runtime_export_created=true
diagnostic_only=true
```

Runtime behavior for the first export:

```text
- Select one bounded candidate at the first eligible post-first-solution update.
- Lock that candidate for the run.
- Preserve exact additive fallback.
- Log selected candidate ID and UpdateParams.
- Log selector source, support count, nearest distance or group utility evidence.
```

Because F2 selected one candidate on every holdout case, the first runtime may be implemented as a support-trained static candidate policy, but it must not be falsely described as context-adaptive.

## P2. C++ runtime integration

Add or extend runtime support so `phase1a_batch` can run:

```text
repair5f_bounded_updateparam_selector_runtime
repair5f_bounded_updateparam_selector_force_additive_parity
repair5f_static_c100_b100_w075_d090
repair5f_runtime_random_candidate_diagnostic
repair5f_runtime_shuffled_utility_diagnostic
```

Do not modify `external/lacam2/lacam2/**`.

Required CLI/config behavior:

```text
--laur-enable with repair5f runtime artifact
--laur-force-additive preserves exact LaCAM*+LTM parity
--laur-disable preserves exact LaCAM*+LTM behavior
runtime artifact path is recorded in JSONL
selected candidate and UpdateParams are recorded in JSONL
```

## P3. Runtime final-holdout evaluation

Run actual closed-loop runtime on the same F2 final holdout scope:

```text
maps:
  random-32-32-20
  maze-32-32-4
  warehouse-10-20-10-2-1

agents:
  50
  100

instance_ids:
  21..25

time_limit_sec:
  3.0

ltm_max_iterations:
  4
```

Methods:

```text
lacam_star_ltm
always_additive_defer
repair5f_candidate_additive_ltm
repair5f_static_c100_b100_w075_d090
repair5f_bounded_updateparam_selector_runtime
repair5f_bounded_updateparam_selector_force_additive_parity
repair5f_runtime_random_candidate_diagnostic
repair5f_runtime_shuffled_utility_diagnostic
repair5e5_crossfold_utility_reranker
repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic
```

Write:

```text
outputs/logs/phase5p5_repair5f_runtime_export_eval/phase5p5_repair5f_runtime_export_eval.jsonl
outputs/logs/phase5p5_repair5f_runtime_export_eval/phase5p5_repair5f_runtime_export_eval_commands.jsonl
outputs/logs/phase5p5_repair5f_runtime_export_eval/phase5p5_repair5f_runtime_export_eval_laur_updates.jsonl
outputs/tables/phase5p5_repair5f_runtime_export_eval_paired.csv
outputs/tables/phase5p5_repair5f_runtime_export_eval_summary.csv
outputs/reports/phase5p5_repair5f_runtime_export_eval_report.md
outputs/reports/phase5p5_repair5f_runtime_export_eval_summary.json
outputs/reports/phase5p5_repair5f_runtime_export_eval_audit.md
```

## P4. Table-vs-runtime reproduction audit

Implement:

```text
scripts/audit_repair5f_runtime_vs_table.py
```

Inputs:

```text
outputs/tables/phase5p5_repair5f_selector_simulation_decisions.csv
outputs/tables/phase5p5_repair5f_selector_simulation_paired.csv
outputs/logs/phase5p5_repair5f_runtime_export_eval/phase5p5_repair5f_runtime_export_eval.jsonl
outputs/logs/phase5p5_repair5f_runtime_export_eval/phase5p5_repair5f_runtime_export_eval_laur_updates.jsonl
```

Write:

```text
outputs/reports/phase5p5_repair5f_runtime_vs_table_audit.md
outputs/reports/phase5p5_repair5f_runtime_vs_table_audit_summary.json
outputs/tables/phase5p5_repair5f_runtime_vs_table_mismatches.csv
```

Required checks:

```text
- runtime selected candidate matches table selected candidate for each case
- runtime UpdateParams match artifact UpdateParams
- runtime SoL / ratio match table-joined candidate outcome where deterministic
- if mismatch exists, classify it as timing/runtime overhead/nondeterminism/policy divergence
- force-additive parity exact
- exact additive candidate parity exact
```

## P5. Static-candidate ablation

Since F2 selected `c100_b100_w075_d090` for every final holdout case, report a direct ablation:

```text
repair5f_static_c100_b100_w075_d090
vs
repair5f_bounded_updateparam_selector_runtime
```

Required interpretation:

```text
If static candidate == selector runtime:
  claim only "support-trained static bounded UpdateParams replacement"
  do not claim context-adaptive UpdateParams selection.

If selector runtime beats static candidate:
  inspect why; only then discuss context adaptivity.

If static candidate beats selector runtime:
  selector machinery is unnecessary and should be simplified.
```

## 4. Runtime gates

Runtime export evaluation passes only if:

```text
force_additive_parity_exact = true
exact_additive_candidate_parity_exact = true
support_final_leakage = false
runtime_selected_candidate_matches_table_policy = true
runtime selector better > worse
runtime selector mean_delta_ratio_vs_ltm < 0
runtime selector ratio_worse_than_ltm_groups <= 1
runtime selector success_worse_than_ltm_groups = 0
runtime selector beats Repair5F random diagnostic
runtime selector beats Repair5F shuffled utility diagnostic
runtime selector improves over E5 real selector
runtime selector does not collapse to additive parity
phase5p5_allowed = false
phase6_allowed = false
```

Strong runtime result:

```text
runtime selector better - worse >= 2
runtime selector mean_delta_ratio_vs_ltm <= -0.002
no success-regression groups
```

## 5. Decision table after F3

### Case A: runtime reproduces F2 and static candidate equals selector

Proceed to larger validation with honest naming:

```text
Repair5F-static-support-tuned UpdateParams
```

Do not claim adaptive selector.

### Case B: runtime reproduces F2 and selector beats static candidate

Proceed to larger validation as:

```text
Repair5F support-trained bounded UpdateParams selector
```

Still no Phase6 claim.

### Case C: runtime fails to reproduce table-level result

Fix runtime/table discrepancy before any further learning work.

### Case D: runtime passes only because random/shuffled also pass

Treat as spurious. Diagnose data split and group bias.

## 6. Validation requirements

Run:

```text
python -m py_compile <all new/modified Python scripts>
python -m pytest tests/test_repair5f_updateparams.py -q
# If default Python lacks pytest, use the czr004 conda environment and record both results.
powershell -ExecutionPolicy Bypass -File scripts/build_phase1a_batch.ps1
git diff --check
```

If C++ changes, the build is required.

Commit and push only Repair5F.3-related files and records. Leave unrelated dirty/untracked files untouched.

## 7. Codex prompt

```text
Continue czr004 on branch phase4f5p5-stable-attention-lau after commit 41958611e35ee3993e7e1cfdf393c04d64f80a4a.

Goal:
  Implement Repair5F.3: runtime export plus static-candidate ablation for the support-trained bounded UpdateParams selector. Do not claim Phase5.5 or Phase6.

Main objective:
  Use learning-enhanced UpdateLTM to replace LTM's coarse additive update and eventually beat LaCAM*+plain additive LTM under closed-loop solver metrics, without changing LaCAM*/PIBT semantics.

Read first:
  deep-research-report.md
  phase4_6_laur_ltm_codex_execution_plan.md
  czr004_repair5f_bounded_updateparams_decision_plan.md
  czr004_repair5f1_safety_parity_closure_plan.md
  czr004_repair5f2_updateparam_selector_plan.md
  czr004_repair5f3_runtime_export_static_ablation_plan.md
  outputs/reports/phase5p5_repair5f_selector_support_probe_report.md
  outputs/reports/phase5p5_repair5f_selector_threshold_sweep_summary.json
  outputs/reports/phase5p5_repair5f_selector_simulation_summary.json
  outputs/reports/phase5p5_repair5f_selector_runtime_export_recommendation.md

Preserve this interpretation:
  - Repair5F.1 proved bounded UpdateParams oracle headroom:
      lattice oracle = 17 / 13 / 0, mean_delta_ratio_vs_ltm = -0.018311948514033324.
  - Repair5F.2 table-level support-trained selector passed:
      selector = 6 / 19 / 5, mean_delta_ratio_vs_ltm = -0.0027415721339999993.
  - F2 was support-only tuned:
      final_holdout_used_for_tuning=false, support_final_overlap_count=0.
  - F2 selected c100_b100_w075_d090 for all 30 holdout cases.
  - Therefore current evidence supports a data-driven static bounded UpdateParams replacement, but not yet context-adaptive selection.
  - phase5p5_allowed=false and phase6_allowed=false remain mandatory.

Do not:
  - modify external/lacam2/lacam2/**
  - change PIBT, LaCAM*, candidate generation, pruning, conflict semantics, OPEN/EXPLORED, incumbent pruning, or restart semantics
  - introduce action prediction
  - introduce learned restart
  - introduce richer LTM representation
  - claim context-adaptive selection unless the selector actually differs from the static candidate and wins
  - claim Phase5.5 or Phase6

Tasks:
  1. Add czr004_repair5f3_runtime_export_static_ablation_plan.md to the repository root and update docs/codex-worklog.md.
  2. Write outputs/reports/phase5p5_repair5f2_final_interpretation.md.
  3. Implement scripts/create_repair5f_updateparam_selector_runtime.py and export:
       artifacts/models/laur_ltm/repair5f_bounded_updateparam_selector/
     The artifact must preserve diagnostic_only=true, phase5p5_allowed=false, phase6_allowed=false.
  4. Extend phase1a_batch / runtime wiring as needed to run:
       repair5f_bounded_updateparam_selector_runtime
       repair5f_bounded_updateparam_selector_force_additive_parity
       repair5f_static_c100_b100_w075_d090
       repair5f_runtime_random_candidate_diagnostic
       repair5f_runtime_shuffled_utility_diagnostic
     Do not modify external/lacam2/lacam2/**.
  5. Run actual runtime final-holdout evaluation on:
       maps = random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
       agents = 50, 100
       instance_ids = 21..25
       time_limit_sec = 3.0
       ltm_max_iterations = 4
     Write:
       outputs/logs/phase5p5_repair5f_runtime_export_eval/phase5p5_repair5f_runtime_export_eval.jsonl
       outputs/logs/phase5p5_repair5f_runtime_export_eval/phase5p5_repair5f_runtime_export_eval_commands.jsonl
       outputs/logs/phase5p5_repair5f_runtime_export_eval/phase5p5_repair5f_runtime_export_eval_laur_updates.jsonl
       outputs/tables/phase5p5_repair5f_runtime_export_eval_paired.csv
       outputs/tables/phase5p5_repair5f_runtime_export_eval_summary.csv
       outputs/reports/phase5p5_repair5f_runtime_export_eval_report.md
       outputs/reports/phase5p5_repair5f_runtime_export_eval_summary.json
       outputs/reports/phase5p5_repair5f_runtime_export_eval_audit.md
  6. Implement scripts/audit_repair5f_runtime_vs_table.py.
     Compare runtime choices and outcomes against table-level simulation decisions.
     Write:
       outputs/reports/phase5p5_repair5f_runtime_vs_table_audit.md
       outputs/reports/phase5p5_repair5f_runtime_vs_table_audit_summary.json
       outputs/tables/phase5p5_repair5f_runtime_vs_table_mismatches.csv
  7. Include a static-candidate ablation:
       repair5f_static_c100_b100_w075_d090
     If this equals the selector runtime, report the result as support-trained static bounded UpdateParams, not context-adaptive selection.

Runtime gates:
  - force_additive_parity_exact=true
  - exact_additive_candidate_parity_exact=true
  - support_final_leakage=false
  - runtime_selected_candidate_matches_table_policy=true
  - runtime selector better > worse
  - runtime selector mean_delta_ratio_vs_ltm < 0
  - runtime selector ratio_worse_than_ltm_groups <= 1
  - runtime selector success_worse_than_ltm_groups = 0
  - runtime selector beats Repair5F random diagnostic
  - runtime selector beats Repair5F shuffled utility diagnostic
  - runtime selector improves over E5 real selector
  - runtime selector does not collapse to additive parity
  - phase5p5_allowed=false
  - phase6_allowed=false

Validation:
  - py_compile all new/modified Python scripts
  - pytest tests/test_repair5f_updateparams.py -q
  - if default Python lacks pytest, run the czr004 conda pytest and record both
  - scripts/build_phase1a_batch.ps1 if C++ changed
  - git diff --check
  - commit and push only Repair5F.3-related files and records
  - leave unrelated dirty/untracked files untouched

Commit message:
  repair5f: export bounded updateparam selector runtime diagnostic
```
