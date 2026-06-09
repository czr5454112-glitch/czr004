# czr004 Repair5F.3.1 Plan: Runtime Parity Closure Before Larger Validation

**Branch:** `phase4f5p5-stable-attention-lau`  
**Start after commit:** `f80dd49d1750b983dda00245f5958aba732945d5`  
**Status:** proposed next diagnostic step  
**Promotion status:** `phase5p5_allowed=false`, `phase6_allowed=false`  

## 0. Decision

Repair5F.3 is a useful result, but it is not a promotion result. The actual runtime selector reproduced the F2 table policy and selected `c100_b100_w075_d090` on all 30 final-holdout cases, with positive closed-loop metrics:

```text
repair5f_bounded_updateparam_selector_runtime:
  better / equal / worse = 6 / 18 / 5
  mean_delta_ratio_vs_ltm = -0.0028361091041379303
  ratio_worse_than_ltm_groups = 1
  success_worse_than_ltm_groups = 0
```

The static ablation matched the selector runtime, so the honest interpretation is:

```text
support-trained static bounded UpdateParams replacement
```

not:

```text
context-adaptive UpdateParams selector
```

However, F3 runtime gates failed because both additive parity controls failed:

```text
force_additive_parity_exact = false
exact_additive_candidate_parity_exact = false
runtime_gates_passed = false
phase5p5_allowed = false
phase6_allowed = false
```

Therefore the next step is not larger validation and not new learning. The next step is a tightly scoped parity autopsy and closure pass.

## 1. Why this matters

The main project goal is to replace LTM's coarse additive update with a learned/data-driven UpdateLTM rule while preserving LaCAM*/PIBT semantics. The current static bounded candidate is scientifically promising because it changes only:

```text
alpha_commit         = 1.00
alpha_block          = 1.00
alpha_wait_spillover = 0.75
rho_decay            = 0.90
```

and it improves over plain additive LTM in actual runtime final-holdout metrics. But without exact additive parity, we cannot be sure the measured gain is isolated to the bounded UpdateParams rule rather than timing, wrapper, command, logging, or runtime-path differences.

## 2. Required interpretation to preserve

Keep these facts fixed:

```text
Repair5F.1:
  lattice oracle = 17 / 13 / 0
  mean_delta_ratio_vs_ltm = -0.018311948514033324
  parity controls closed after F1.1

Repair5F.2:
  support-only selector passed table gates
  final_holdout_used_for_tuning = false
  support_final_overlap_count = 0
  selected c100_b100_w075_d090 on all 30 holdout cases

Repair5F.3:
  runtime selector = 6 / 18 / 5
  mean_delta_ratio_vs_ltm = -0.0028361091041379303
  runtime-vs-table mismatch_count = 0
  runtime_updateparams_match_artifact = true
  static ablation matched selector runtime
  force_additive_parity_exact = false
  exact_additive_candidate_parity_exact = false
```

Do not claim Phase5.5, Phase6, or context-adaptive learning.

## 3. Required work

### P0. Add this plan and update worklog

Create/update:

```text
czr004_repair5f31_runtime_parity_closure_plan.md
docs/codex-worklog.md
outputs/reports/phase5p5_repair5f3_final_interpretation.md
```

The final interpretation must state that F3 is positive runtime evidence for a support-trained static bounded UpdateParams rule, but runtime gates failed because additive parity controls failed.

### P1. Implement runtime parity autopsy

Implement:

```text
scripts/analyze_repair5f3_runtime_parity.py
```

Inputs:

```text
outputs/logs/phase5p5_repair5f_runtime_export_eval/phase5p5_repair5f_runtime_export_eval.jsonl
outputs/logs/phase5p5_repair5f_runtime_export_eval/phase5p5_repair5f_runtime_export_eval_commands.jsonl
outputs/logs/phase5p5_repair5f_runtime_export_eval/phase5p5_repair5f_runtime_export_eval_laur_updates.jsonl
outputs/tables/phase5p5_repair5f_runtime_export_eval_paired.csv
outputs/reports/phase5p5_repair5f_runtime_export_eval_summary.json
outputs/reports/phase5p5_repair5f_runtime_vs_table_audit_summary.json
```

Compare `lacam_star_ltm` against:

```text
always_additive_defer
repair5f_candidate_additive_ltm
repair5f_bounded_updateparam_selector_force_additive_parity
laur_force_additive_direct, if available or added
laur_disable, if available or added
```

For every case and method, report exact field equality for:

```text
success
feasible
sum_of_loss
lower_bound
sum_of_loss_ratio
makespan
returned_solutions_count
ltm_iterations
expanded_nodes
high_level_expansions
low_level_pibt_calls
selected_candidate_id
laur_update_mode
laur_force_additive
laur_model_path
method alias
return code
command line
```

Also classify whether the mismatch is:

```text
missing row
success mismatch
finite/nonfinite ratio mismatch
sum_of_loss mismatch
makespan mismatch
lower_bound mismatch
wrapper/method alias mismatch
runtime artifact loaded when it should have been bypassed
update log / feature extraction executed in a parity path
selected-candidate labeling-only mismatch
time-budget / nondeterministic rerun difference
```

Write:

```text
outputs/reports/phase5p5_repair5f3_runtime_parity_autopsy.md
outputs/reports/phase5p5_repair5f3_runtime_parity_autopsy_summary.json
outputs/tables/phase5p5_repair5f3_runtime_parity_mismatches.csv
```

### P2. Add minimal parity reproducer

Implement:

```text
scripts/run_repair5f3_runtime_parity_reproducer.py
```

It must rerun only the mismatching case(s) found by P1, plus one known-good control case. Run each method at least three times if runtime budget allows:

```text
lacam_star_ltm
always_additive_defer
repair5f_candidate_additive_ltm
repair5f_bounded_updateparam_selector_force_additive_parity
laur_disable
laur_force_additive_direct
```

Write:

```text
outputs/logs/phase5p5_repair5f3_runtime_parity_reproducer/phase5p5_repair5f3_runtime_parity_reproducer.jsonl
outputs/logs/phase5p5_repair5f3_runtime_parity_reproducer/phase5p5_repair5f3_runtime_parity_reproducer_commands.jsonl
outputs/reports/phase5p5_repair5f3_runtime_parity_reproducer_report.md
outputs/reports/phase5p5_repair5f3_runtime_parity_reproducer_summary.json
outputs/tables/phase5p5_repair5f3_runtime_parity_reproducer_paired.csv
```

### P3. Fix only parity/wrapper issues

Allowed fixes:

```text
- Make force-additive parity methods bypass runtime feature extraction, runtime prediction, artifact loading, and LAUR update logging.
- Make exact additive candidate parity use canonical additive UpdateLTM when the candidate artifact is the exact additive candidate.
- Ensure selected_candidate_id labeling for force-additive parity reports additive_ltm rather than empty string when appropriate.
- Add laur_disable and laur_force_additive_direct control aliases if missing.
- Tighten tests for Repair5F.3 parity wrappers.
```

Forbidden fixes:

```text
- Do not change PIBT, LaCAM*, conflict handling, candidate generation, OPEN/EXPLORED, rewrite, incumbent pruning, or restart semantics.
- Do not weaken parity gates.
- Do not delete the parity controls.
- Do not ignore failed cases.
- Do not tune c100_b100_w075_d090 on the final holdout.
- Do not introduce learned restart, action prediction, or richer traffic-map state.
```

### P4. Rerun F3 runtime evaluation after parity fix

Rerun the same F3 final-holdout scope:

```text
maps = random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
agents = 50, 100
instance_ids = 21..25
time_limit_sec = 3.0
ltm_max_iterations = 4
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
laur_disable
laur_force_additive_direct
```

Write refreshed outputs under a new directory, not overwriting F3:

```text
outputs/logs/phase5p5_repair5f3_parity_closure_eval/
outputs/tables/phase5p5_repair5f3_parity_closure_eval_paired.csv
outputs/tables/phase5p5_repair5f3_parity_closure_eval_summary.csv
outputs/reports/phase5p5_repair5f3_parity_closure_eval_report.md
outputs/reports/phase5p5_repair5f3_parity_closure_eval_summary.json
outputs/reports/phase5p5_repair5f3_parity_closure_eval_audit.md
```

Required gates:

```text
force_additive_parity_exact = true
exact_additive_candidate_parity_exact = true
laur_disable_parity_exact = true
laur_force_additive_direct_parity_exact = true
support_final_leakage_false = true
runtime_selected_candidate_matches_table_policy = true
runtime_updateparams_match_artifact = true
runtime selector better > worse
runtime selector mean_delta_ratio_vs_ltm < 0
runtime selector ratio_worse_than_ltm_groups <= 1
runtime selector success_worse_than_ltm_groups = 0
runtime selector beats Repair5F random diagnostic
runtime selector beats Repair5F shuffled utility diagnostic
runtime selector improves over E5 real selector
phase5p5_allowed = false
phase6_allowed = false
```

### P5. Decide the next branch after parity closure

If parity closes and runtime still shows positive static-rule metrics, write:

```text
outputs/reports/phase5p5_repair5f3_parity_closure_decision.md
```

Decision:

```text
Proceed to Repair5F.4 larger validation of support-trained static bounded UpdateParams.
```

If parity does not close, write:

```text
Do not run larger validation. Continue parity autopsy or revert the F3 runtime wrapper changes.
```

## 4. Validation

Run:

```text
python -m py_compile scripts/analyze_repair5f3_runtime_parity.py scripts/run_repair5f3_runtime_parity_reproducer.py scripts/run_repair5f_runtime_export_eval.py scripts/audit_repair5f_runtime_vs_table.py scripts/create_repair5f_updateparam_selector_runtime.py tests/test_repair5f_updateparams.py
python -m pytest tests/test_repair5f_updateparams.py -q
```

If pytest is unavailable, record the failure and run a manual fallback harness over all test functions in `tests/test_repair5f_updateparams.py`, then report both results.

If C++ changes:

```text
powershell -ExecutionPolicy Bypass -File scripts/build_phase1a_batch.ps1
```

Also run:

```text
git diff --check
```

Commit and push only Repair5F.3.1 parity-closure files and records. Leave unrelated dirty/untracked files untouched.

## 5. Commit message

```text
repair5f: close runtime parity controls before validation
```
