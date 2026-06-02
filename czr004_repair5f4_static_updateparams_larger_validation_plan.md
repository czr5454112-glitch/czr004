# czr004 Repair5F.4 Plan: Larger Validation for Support-Trained Static Bounded UpdateParams

**Branch:** `phase4f5p5-stable-attention-lau`
**Start after:** `5f777e05fd1658293b381b3ada13ef25ae3e5d89` or the current remote head if it contains the F3.1 parity-closure decision refresh
**Status:** proposed next diagnostic step
**Promotion status:** `phase5p5_allowed=false`, `phase6_allowed=false`
**Primary objective:** validate whether the support-trained static bounded `UpdateParams` rule can reliably replace LTM's coarse additive `UpdateLTM` update and beat `LaCAM*+plain additive LTM` under closed-loop solver metrics, without changing LaCAM*/PIBT semantics.

---

## 0. Current interpretation after Repair5F.3.1

Repair5F.3.1 closed the F3 runtime parity blocker on the same final-holdout scope used by F2/F3.

Closed gates:

```text
force_additive_parity_exact = true
exact_additive_candidate_parity_exact = true
laur_disable_parity_exact = true
laur_force_additive_direct_parity_exact = true
runtime_selected_candidate_matches_table_policy = true
runtime_updateparams_match_artifact = true
runtime-vs-table mismatch_count = 0
```

Runtime result preserved:

```text
repair5f_bounded_updateparam_selector_runtime:
  selected_candidate_distribution = c100_b100_w075_d090: 30 / 30
  better / equal / worse = 6 / 19 / 5
  mean_delta_ratio_vs_ltm = -0.0027415721339999993
  ratio_worse_than_ltm_groups = 1
  success_worse_than_ltm_groups = 0

repair5f_static_c100_b100_w075_d090:
  metric-identical to selector runtime
```

Therefore the honest current method name is:

```text
Repair5F-static-support-tuned bounded UpdateParams
```

or more descriptively:

```text
support-trained static bounded UpdateParams replacement for additive UpdateLTM
```

Do **not** call it context-adaptive selection. Context adaptivity would require the runtime selector to choose different candidates across contexts and beat the fixed static candidate.

---

## 1. Why F4 exists

F3.1 answers the engineering-control question: the runtime artifact now preserves exact additive fallback and reproduces the F2/F3 policy.

F4 must answer the scientific validation question:

```text
Does the locked support-trained static bounded UpdateParams rule generalize beyond the 30 diagnostic final-holdout cases?
```

The rule is locked before F4:

```text
candidate_id            = c100_b100_w075_d090
alpha_commit            = 1.00
alpha_block             = 1.00
alpha_wait_spillover    = 0.75
rho_decay               = 0.90
```

No F4 validation outcome may be used to retune this rule.

---

## 2. Scope

Run a fresh-ID larger validation that does not overlap support IDs `1..20` or the F2/F3 diagnostic final holdout `21..25`.

Default F4-A scope:

```text
maps:
  random-32-32-20
  maze-32-32-4
  warehouse-10-20-10-2-1

agents:
  50
  100

fresh_validation_instance_ids:
  26..45

time_limit_sec:
  3.0

ltm_max_iterations:
  4
```

This gives 120 fresh cases before method expansion. If scenario files for IDs `26..45` are not available, first audit availability and either:

1. generate the missing scenario files using the existing deterministic project scenario generator, recording the generator command and seed policy; or
2. use the largest contiguous available fresh range after 25 and report the reduced scope explicitly.

Do not include IDs `1..25` in the F4 primary validation summary.

---

## 3. Methods

Required baseline and parity controls:

```text
lacam_star_ltm
always_additive_defer
repair5f_candidate_additive_ltm
repair5f_bounded_updateparam_selector_force_additive_parity
laur_disable
laur_force_additive_direct
```

Required main method and static equality control:

```text
repair5f_bounded_updateparam_selector_runtime
repair5f_static_c100_b100_w075_d090
```

Required component/mechanism ablations:

```text
repair5f_static_c100_b100_w075_d100   # wait-spillover reduction only
repair5f_static_c100_b100_w100_d090   # decay 0.90 only
repair5f_static_c100_b100_w100_d095   # mild decay 0.95 only
repair5f_static_c100_b100_w075_d095   # wait reduction + mild decay
```

Required diagnostic control:

```text
repair5f_f4_deterministic_random_candidate_diagnostic
```

The F4 deterministic random diagnostic must choose a bounded candidate by stable hash over `(map, agents, seed)` and the locked candidate lattice, without using any F4 outcome. It is not a training baseline; it is a spurious-choice control.

Optional comparators if their artifacts are available and runtime cost is acceptable:

```text
repair5e5_crossfold_utility_reranker
repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic
```

---

## 4. Required implementation

### P0. Documentation

Add this plan to the repository root:

```text
czr004_repair5f4_static_updateparams_larger_validation_plan.md
```

Update:

```text
docs/codex-worklog.md
```

Write an F3.1 carry-forward summary:

```text
outputs/reports/phase5p5_repair5f31_carry_forward_to_f4.md
```

It must state:

```text
- F3.1 closed exact additive parity controls.
- F3.1 preserved the runtime positive signal.
- F3.1 supports only support-trained static bounded UpdateParams, not context-adaptive selection.
- F4 must not retune from validation outcomes.
- phase5p5_allowed=false and phase6_allowed=false remain mandatory.
```

### P1. Larger-validation runner

Implement or extend:

```text
scripts/run_repair5f4_static_updateparams_validation.py
```

The runner must support:

```text
--instance-ids 26 27 ... 45
--maps random-32-32-20 maze-32-32-4 warehouse-10-20-10-2-1
--agent-counts 50 100
--time-limit-sec 3.0
--ltm-max-iterations 4
--resume
--overwrite
--chunk-size
```

It should reuse existing candidate-runtime export helpers where possible, but the selected static rule must remain locked to `c100_b100_w075_d090`.

For component ablations, generate candidate runtime artifacts under:

```text
outputs/tmp/phase5p5_repair5f4_static_updateparams_validation_runtimes/
```

Do not modify `external/lacam2/lacam2/**`.

### P2. Validation outputs

Write:

```text
outputs/logs/phase5p5_repair5f4_static_updateparams_validation/phase5p5_repair5f4_static_updateparams_validation.jsonl
outputs/logs/phase5p5_repair5f4_static_updateparams_validation/phase5p5_repair5f4_static_updateparams_validation_commands.jsonl
outputs/logs/phase5p5_repair5f4_static_updateparams_validation/phase5p5_repair5f4_static_updateparams_validation_laur_updates.jsonl

outputs/tables/phase5p5_repair5f4_static_updateparams_validation_paired.csv
outputs/tables/phase5p5_repair5f4_static_updateparams_validation_summary.csv
outputs/tables/phase5p5_repair5f4_static_updateparams_validation_by_map_agent.csv
outputs/tables/phase5p5_repair5f4_static_updateparams_validation_component_ablation.csv

outputs/reports/phase5p5_repair5f4_static_updateparams_validation_report.md
outputs/reports/phase5p5_repair5f4_static_updateparams_validation_summary.json
outputs/reports/phase5p5_repair5f4_static_updateparams_validation_audit.md
```

### P3. Metrics and statistics

For every method, compute:

```text
rows
better / equal / worse vs lacam_star_ltm
mean_delta_ratio_vs_ltm
median_delta_ratio_vs_ltm
bootstrap_95ci_mean_delta_ratio_vs_ltm
ratio_worse_than_ltm_groups
success_worse_than_ltm_groups
selected_candidate_distribution
selected_nonadditive_cases
```

For the main method, also compute:

```text
paired sign-test count: better vs worse
bootstrap probability mean_delta < 0
per-map-agent mean delta
per-map-agent better/equal/worse
worst group and worst 5 cases
```

For component ablations, report whether the full selected rule beats or ties:

```text
wait-only c100_b100_w075_d100
decay-only c100_b100_w100_d090
mild decay c100_b100_w100_d095
wait + mild decay c100_b100_w075_d095
```

This is needed to explain whether the useful mechanism is wait-spillover reduction, decay, or their combination.

### P4. Freshness and leakage audit

Implement or extend an audit that checks:

```text
support IDs 1..20 not in F4 validation
F2/F3 diagnostic holdout IDs 21..25 not in F4 primary validation
F4 outcomes not used to choose c100_b100_w075_d090
runtime selector selected c100_b100_w075_d090 for every eligible update case
selector/static metrics are identical
all additive parity controls exact
schema errors = 0
missing rows = 0
```

Write:

```text
outputs/reports/phase5p5_repair5f4_static_updateparams_validation_freshness_audit.md
outputs/reports/phase5p5_repair5f4_static_updateparams_validation_freshness_audit_summary.json
```

---

## 5. F4 pass gates

F4-A passes only if all mandatory gates are true:

```text
full_expected_rows = true
schema_errors = 0
missing_rows = 0
support_validation_overlap_count = 0
f2f3_holdout_validation_overlap_count = 0
force_additive_parity_exact = true
exact_additive_candidate_parity_exact = true
laur_disable_parity_exact = true
laur_force_additive_direct_parity_exact = true
selector_static_runtime_metrics_equal = true
selector_selected_c100_b100_w075_d090_all_cases = true
main_static_better_gt_worse = true
main_static_mean_delta_ratio_vs_ltm < 0
main_static_bootstrap_ci_upper <= 0, or explicitly report if not achieved
main_static_ratio_worse_than_ltm_groups <= 1
main_static_success_worse_than_ltm_groups = 0
main_static_beats_deterministic_random_candidate_diagnostic = true
phase5p5_allowed = false
phase6_allowed = false
```

A strong F4-A result would be:

```text
main_static_better_minus_worse >= 5
mean_delta_ratio_vs_ltm <= -0.002
bootstrap_95ci_upper < 0
no success-regression groups
component ablation shows full rule is at least tied with the best single-component rule
```

---

## 6. Decision after F4-A

### Case A: F4-A passes cleanly

Proceed to Repair5F.4B time-budget and scope stress validation:

```text
same locked static rule
fresh IDs not used in F4-A if possible
time_limit_sec in {1.0, 3.0, 10.0}
additional maps / agent counts if available
```

Do not claim Phase5.5 or Phase6 yet.

### Case B: F4-A weak positive but not statistically stable

Keep the result as a promising diagnostic. Run targeted stratified analysis before expanding.

### Case C: F4-A fails mean/better-worse gates

Treat F3.1 as a small-holdout artifact. Do not promote. Analyze failure groups and return to support-trained selector design only after documenting why the static rule failed.

### Case D: parity or leakage fails

Stop validation and fix controls. Do not interpret performance.

---

## 7. Validation commands

Run:

```text
python -m py_compile scripts/run_repair5f4_static_updateparams_validation.py
python -m py_compile scripts/analyze_repair5f3_runtime_parity.py scripts/run_repair5f3_runtime_parity_reproducer.py scripts/audit_repair5f_runtime_vs_table.py
python -m pytest tests/test_repair5f_updateparams.py -q
# If pytest is unavailable, record that and run the manual fallback harness over all tests in tests/test_repair5f_updateparams.py.
# If C++ changed:
powershell -ExecutionPolicy Bypass -File scripts/build_phase1a_batch.ps1
git diff --check
```

Commit and push only Repair5F.4-related files and records. Leave unrelated dirty/untracked files untouched.

---

## 8. Codex prompt

```text
Continue czr004 on branch phase4f5p5-stable-attention-lau after commit 5f777e05fd1658293b381b3ada13ef25ae3e5d89, or the current remote head if it only contains the F3.1 parity-closure decision refresh.

Goal:
  Implement Repair5F.4-A: fresh-ID larger validation of the locked support-trained static bounded UpdateParams rule. Do not retune the rule. Do not claim context-adaptive selection, Phase5.5, or Phase6.

Main project objective:
  Use learning-enhanced UpdateLTM to replace the coarse additive update in the LTM paper and eventually beat LaCAM*+plain additive LTM under closed-loop solver metrics, without changing LaCAM*/PIBT semantics.

Read first:
  deep-research-report.md
  phase4_6_laur_ltm_codex_execution_plan.md
  czr004_repair5f_bounded_updateparams_decision_plan.md
  czr004_repair5f1_safety_parity_closure_plan.md
  czr004_repair5f2_updateparam_selector_plan.md
  czr004_repair5f3_runtime_export_static_ablation_plan.md
  czr004_repair5f31_runtime_parity_closure_plan.md
  czr004_repair5f4_static_updateparams_larger_validation_plan.md
  outputs/reports/phase5p5_repair5f3_parity_closure_decision.md
  outputs/reports/phase5p5_repair5f3_parity_closure_eval_report.md
  outputs/reports/phase5p5_repair5f3_parity_closure_eval_summary.json
  outputs/reports/phase5p5_repair5f3_parity_closure_eval_audit_summary.json

Preserve this interpretation:
  - Repair5F.3.1 closed the runtime parity blocker.
  - force_additive_parity_exact=true
  - exact_additive_candidate_parity_exact=true
  - laur_disable_parity_exact=true
  - laur_force_additive_direct_parity_exact=true
  - runtime-vs-table mismatch_count=0
  - Runtime selector and static c100_b100_w075_d090 are metric-identical.
  - Current evidence supports support-trained static bounded UpdateParams replacement, not context-adaptive selection.
  - phase5p5_allowed=false and phase6_allowed=false remain mandatory.

Locked main rule:
  candidate_id = c100_b100_w075_d090
  alpha_commit = 1.00
  alpha_block = 1.00
  alpha_wait_spillover = 0.75
  rho_decay = 0.90

Do not:
  - modify external/lacam2/lacam2/**
  - change PIBT, LaCAM*, candidate generation, pruning, conflict semantics, OPEN/EXPLORED, incumbent pruning, rewrite, or restart semantics
  - introduce action prediction
  - introduce learned restart
  - introduce richer LTM representation
  - use F4 validation outcomes to retune the rule
  - include IDs 1..25 in the F4 primary validation summary
  - claim context-adaptive selection
  - claim Phase5.5 or Phase6

Tasks:
  1. Add czr004_repair5f4_static_updateparams_larger_validation_plan.md to repository root and update docs/codex-worklog.md.

  2. Write outputs/reports/phase5p5_repair5f31_carry_forward_to_f4.md.
     It must state that F3.1 closed parity, preserved weak positive runtime signal, and supports only support-trained static bounded UpdateParams.

  3. Implement scripts/run_repair5f4_static_updateparams_validation.py with resume/chunk support.

  4. Run F4-A fresh-ID validation on:
       maps = random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
       agents = 50, 100
       instance_ids = 26..45
       time_limit_sec = 3.0
       ltm_max_iterations = 4

     If scenario files for 26..45 are missing, audit availability and either generate them deterministically using the existing project scenario generator or use the largest available contiguous fresh range after 25, recording the decision.

  5. Include methods:
       lacam_star_ltm
       always_additive_defer
       repair5f_candidate_additive_ltm
       repair5f_bounded_updateparam_selector_force_additive_parity
       laur_disable
       laur_force_additive_direct
       repair5f_bounded_updateparam_selector_runtime
       repair5f_static_c100_b100_w075_d090
       repair5f_static_c100_b100_w075_d100
       repair5f_static_c100_b100_w100_d090
       repair5f_static_c100_b100_w100_d095
       repair5f_static_c100_b100_w075_d095
       repair5f_f4_deterministic_random_candidate_diagnostic
       repair5e5_crossfold_utility_reranker, if artifact available
       repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic, if artifact available

  6. Write all F4 outputs under:
       outputs/logs/phase5p5_repair5f4_static_updateparams_validation/
       outputs/tables/phase5p5_repair5f4_static_updateparams_validation_*.csv
       outputs/reports/phase5p5_repair5f4_static_updateparams_validation_*.md/json

  7. Compute paired stats, per-map-agent stats, bootstrap 95% CI for mean delta, component ablation table, and freshness/leakage audit.

  8. Required gates:
       full_expected_rows=true
       missing_rows=0
       schema_errors=0
       support_validation_overlap_count=0
       f2f3_holdout_validation_overlap_count=0
       force_additive_parity_exact=true
       exact_additive_candidate_parity_exact=true
       laur_disable_parity_exact=true
       laur_force_additive_direct_parity_exact=true
       selector_static_runtime_metrics_equal=true
       selector_selected_c100_b100_w075_d090_all_cases=true
       main_static_better_gt_worse=true
       main_static_mean_delta_ratio_vs_ltm < 0
       main_static_ratio_worse_than_ltm_groups <= 1
       main_static_success_worse_than_ltm_groups = 0
       main_static_beats_deterministic_random_candidate_diagnostic=true
       phase5p5_allowed=false
       phase6_allowed=false

  9. Write outputs/reports/phase5p5_repair5f4_static_updateparams_validation_decision.md.
     If F4-A passes, recommend F4-B time-budget/scope stress validation.
     If F4-A fails, do not promote; analyze failure groups.

Validation:
  - py_compile all new/modified Python scripts
  - python -m pytest tests/test_repair5f_updateparams.py -q
  - if pytest unavailable, record it and run manual fallback harness over all tests/test_repair5f_updateparams.py tests
  - if C++ changed, run scripts/build_phase1a_batch.ps1
  - git diff --check
  - commit and push only Repair5F.4-related files and records
  - leave unrelated dirty/untracked files untouched

Commit message:
  repair5f: validate static updateparams on fresh holdout
```
