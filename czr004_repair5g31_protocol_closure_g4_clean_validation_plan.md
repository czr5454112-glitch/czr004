# czr004 Repair5G.3.1/G4 Plan: Protocol-Parity Closure, Clean Flow-Shield Validation, and Learning-Enhanced UpdateLTM Bridge

**Branch:** `phase4f5p5-stable-attention-lau`
**Start after commit:** `834bc28 repair5g: broaden flow-shield validation and prepare learned selector`
**Status:** proposed next task after G3 broader validation produced strong directional flow-shield evidence but failed strict protocol gates
**Promotion status:** `phase5p5_allowed=false`, `phase6_allowed=false`
**Main project objective:** use learning-enhanced `UpdateLTM` to replace the coarse additive update in the LTM paper and eventually beat `LaCAM*+plain additive LTM` under closed-loop solver metrics, without changing LaCAM*/PIBT semantics.

---

## 0. Executive interpretation

Repair5G.3 is **not a scientific failure**. It is a **protocol failure with strong directional evidence**.

Preserve the facts:

```text
G3 determinism/repeat gate:
  passed
  expected rows = 3240
  missing rows = 0
  schema errors = 0
  solver crash count = 0
  true semantic parity mismatch count = 0
  selected sign stable = true
  selected mean delta < 0 in all 3 repeats
  selected success-worse groups = 0

G3 broader validation:
  completed rows = 6240 / 6240
  maps = random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
  agents = 50, 100
  instance_ids = 66..105
  missing rows = 0
  schema errors = 0
  solver crash count = 0
  true semantic parity mismatch count = 0

G3 selected method:
  repair5g2_frozen_static_or_selector
  better / equal / worse = 132 / 60 / 31
  mean_delta_ratio_vs_ltm = -0.019665489611971558
  bootstrap_probability_mean_delta_lt_0 = 1.0
  ratio_worse_than_ltm_groups = 0
  success_worse_than_ltm_groups = 0

G3 best static flow-shield:
  repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75
  better / equal / worse = 127 / 62 / 34
  mean_delta_ratio_vs_ltm = -0.02004726679608962
  bootstrap_probability_mean_delta_lt_0 = 1.0
  ratio_worse_than_ltm_groups = 0
  success_worse_than_ltm_groups = 0

G3 C-equiv/scalar baselines:
  repair5g2_c_equiv_best_frozen_baseline:
    mean_delta_ratio_vs_ltm = +0.0009849877360095744
  repair5f_static_c100_b100_w075_d090:
    mean_delta_ratio_vs_ltm = -0.0014563323262769946

G3 gate status:
  selected_gates_passed = true
  representation_gates_passed = true
  protocol_gates_passed = false
  decision = protocol_failed
```

The result is therefore:

```text
Good:
  Flow-shield representation survived another much larger new-ID validation.
  The effect size stayed near -2%.
  C-equiv/scalar congestion-only baselines remained much weaker.
  True semantic parity mismatch count stayed zero.
  The selected method and static flow-shield both have zero success-worse groups.

Bad / blocking:
  Strict exact parity fields for additive/disable/force-additive/dual-additive controls are false.
  G3 is protocol_failed.
  Stress and learning-bridge runtime evaluation were correctly not run.
  IDs 66..105 are now observed and cannot be reused as untouched final evidence.

Important interpretation:
  The goal-aware flow-shield dual-channel UpdateLTM representation is increasingly credible.
  The map-agent selector is not yet clearly better than the best static flow-shield rule.
  Current evidence supports "flow-shield representation works" more strongly than "selector intelligence works".
  The next step is not to tune more candidates. The next step is to close the protocol/parity issue.
```

---

## 1. Why G3 protocol failure matters

The exact control parity flags failed in P4:

```text
additive_parity_exact = false
laur_disable_parity_exact = false
laur_force_additive_direct_parity_exact = false
dual_additive_parity_exact = false
dual_c_equiv_additive_parity_exact = false
```

But:

```text
true_semantic_parity_mismatch_count = 0
missing_rows = 0
schema_errors = 0
solver_crash_count = 0
all_costs_finite = true
cost_bounds_respected = true
```

This strongly suggests a **time-budget / anytime-boundary / return-code-2 / reporting-equivalence** problem rather than a solver semantic change. However, this cannot be hand-waved. It is the exact kind of thing that can invalidate a closed-loop solver claim if not formally audited.

The next task must distinguish:

```text
A. true semantic mismatch
B. wall-clock anytime sensitivity
C. return-code-2 no-solution/timeout equivalence
D. run-order / parallel-worker scheduling sensitivity
E. pairwise comparison bug
F. gate-aggregation bug, including bool-as-int errors such as False == 0
G. raw JSONL duplication/resume/synthetic-row contamination
```

Only after this is closed should Codex run another clean validation or learned-selector evaluation.

---

## 2. Non-negotiable constraints

Do not:

```text
- modify external/lacam2/lacam2/**
- change PIBT legality, priority inheritance, backtracking, vertex conflict, or swap conflict semantics
- change LaCAM* candidate generation, child pruning, OPEN/EXPLORED, rewrite, incumbent pruning, or restart semantics
- introduce action prediction
- introduce learned restart
- output learned h_i(v)
- output learned edge action logits
- output learned priority overrides
- delete legal candidates
- claim Phase5.5 or Phase6
- silently loosen parity gates
- rerun IDs 46..105 and call them untouched final evidence
- use future clean validation IDs for tuning
```

Allowed:

```text
- protocol/parity audit scripts
- reproducibility and gate-type tests
- sequential control-only reproducers
- time-budget and return-code equivalence analysis
- project-owned runner/report fixes
- frozen G2/G3 flow-shield static/selector evaluation on new clean IDs after protocol closure
- offline learning-bridge dataset construction
- learned UpdateLTM parameter selector only if it stays inside UpdateLTM and uses pre-update features
```

Boundary remains:

```text
phase5p5_allowed=false
phase6_allowed=false
diagnostic_only=true
```

---

## 3. Split policy after G3

Observed and unavailable as untouched final evidence:

```text
IDs 1..25: support/training
IDs 26..45: G1/G2 development
IDs 46..65: G2 fresh final, now observed
IDs 66..105: G3 broader validation, now observed even though protocol_failed
```

Recommended next split:

```text
G3.1 protocol/parity diagnostic:
  Prefer to reuse observed IDs 66..105 and existing mismatch cases.
  If new cases are needed, use IDs 106..115 and mark them diagnostic-only.

G4 clean frozen validation:
  IDs 126..165
  Use only after protocol closure.
  Do not tune on these IDs.

Learning-bridge fresh evaluation:
  IDs 166..205 or next untouched range
  Use only after a learned/contextual selector is frozen.
```

If IDs 106..125 remain untouched after protocol closure, they may be reserved for learning-bridge holdout. If they are used for diagnostics, record that they are no longer final-clean.

---

## 4. Required work

## P0. Documentation and final interpretation

Add this plan to repo root:

```text
czr004_repair5g31_protocol_closure_g4_clean_validation_plan.md
```

Update:

```text
docs/codex-worklog.md
```

Write:

```text
outputs/reports/phase5p5_repair5g3_final_interpretation.md
outputs/reports/phase5p5_repair5g31_protocol_closure_overview.md
```

`phase5p5_repair5g3_final_interpretation.md` must state:

```text
- G3 is a protocol failure, not a representation failure.
- P3 determinism repeat passed.
- P4 broad validation completed all 6240 rows.
- selected and representation gates passed directionally.
- strict protocol parity gates failed.
- true semantic parity mismatch count was zero.
- stress and learning bridge were correctly not run.
- IDs 66..105 are now observed.
- phase5p5_allowed=false and phase6_allowed=false remain closed.
```

## P1. Gate and summary integrity audit

Implement:

```text
scripts/analyze_repair5g3_protocol_failure.py
```

Inputs:

```text
outputs/reports/phase5p5_repair5g3_determinism_repeat_summary.json
outputs/reports/phase5p5_repair5g3_broader_validation_summary.json
outputs/reports/phase5p5_repair5g3_broader_validation_audit.md
outputs/tables/phase5p5_repair5g3_broader_validation_paired.csv
outputs/tables/phase5p5_repair5g3_broader_validation_summary.csv
outputs/tables/phase5p5_repair5g3_broader_validation_by_map_agent.csv
outputs/logs/phase5p5_repair5g3_broader_validation/*.jsonl
outputs/logs/phase5p5_repair5g3_determinism_repeat/*.jsonl
```

Outputs:

```text
outputs/reports/phase5p5_repair5g3_protocol_failure_autopsy.md
outputs/reports/phase5p5_repair5g3_protocol_failure_autopsy_summary.json
outputs/tables/phase5p5_repair5g3_protocol_parity_mismatch_cases.csv
outputs/tables/phase5p5_repair5g3_protocol_returncode2_cases.csv
outputs/tables/phase5p5_repair5g3_protocol_gate_type_audit.csv
outputs/tables/phase5p5_repair5g3_protocol_resume_duplicate_audit.csv
```

Required analysis:

```text
1. Recompute all protocol gates from raw rows and committed tables.
2. Audit every boolean/numeric gate field type.
3. Detect bool-as-int mistakes:
     false must not satisfy "== 0" gates.
4. Separate:
     strict exact parity mismatch
     true semantic parity mismatch
     timeout-equivalent mismatch
     return-code-2/no-solution-equivalent mismatch
     missing row / duplicate row / synthetic-row contamination
5. For each control pair:
     lacam_star_ltm vs always_additive_defer
     lacam_star_ltm vs repair5f_candidate_additive_ltm
     lacam_star_ltm vs laur_disable
     lacam_star_ltm vs laur_force_additive_direct
     lacam_star_ltm vs repair5g_dual_additive_parity
     lacam_star_ltm vs repair5g_dual_c_equiv_additive
6. For each mismatch:
     map
     agents
     seed
     method
     returncode
     success
     sum_of_loss
     ratio
     makespan
     expanded_nodes
     time_to_first_solution_ms
     classification
     whether mismatch affects selected/flow-shield comparison
```

If any true semantic mismatch is found, stop and write:

```text
stop_for_semantic_parity_bug
```

## P2. Reproducer for strict parity failures

Implement:

```text
scripts/run_repair5g31_control_parity_reproducer.py
```

Run only control methods:

```text
lacam_star_ltm
always_additive_defer
repair5f_candidate_additive_ltm
laur_disable
laur_force_additive_direct
repair5g_dual_additive_parity
repair5g_dual_c_equiv_additive
```

Cases:

```text
- all mismatch cases from phase5p5_repair5g3_protocol_parity_mismatch_cases.csv
- plus a clean sentinel sample:
    maps = random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
    agents = 50, 100
    instance_ids = 106..115 if needed
```

Run modes:

```text
mode A: sequential, max_workers=1, time_limit_sec=3.0, repeats=3
mode B: sequential, max_workers=1, time_limit_sec=5.0, repeats=2
mode C: sequential, max_workers=1, time_limit_sec=10.0, repeats=1
mode D: original parallel order if needed, max_workers=8, time_limit_sec=3.0, repeats=1
```

Outputs:

```text
outputs/logs/phase5p5_repair5g31_control_parity_reproducer/phase5p5_repair5g31_control_parity_reproducer.jsonl
outputs/logs/phase5p5_repair5g31_control_parity_reproducer/phase5p5_repair5g31_control_parity_reproducer_commands.jsonl
outputs/tables/phase5p5_repair5g31_control_parity_reproducer_pairs.csv
outputs/tables/phase5p5_repair5g31_control_parity_reproducer_by_mode.csv
outputs/reports/phase5p5_repair5g31_control_parity_reproducer_report.md
outputs/reports/phase5p5_repair5g31_control_parity_reproducer_summary.json
```

Pass condition for proceeding:

```text
true_semantic_parity_mismatch_count = 0
all strict mismatches are classified as:
  time_budget_sensitivity
  timeout_equivalent
  returncode2_no_solution_equivalent
or reporting-only
```

If strict mismatches persist even at 10s sequential with different solutions, stop and inspect implementation.

## P3. Formal parity policy report

Write:

```text
outputs/reports/phase5p5_repair5g31_parity_policy.md
outputs/reports/phase5p5_repair5g31_parity_policy_summary.json
```

The report must be conservative.

It must define at least three layers:

```text
semantic parity:
  no UpdateLTM / solver semantics differ for controls.

strict wall-clock parity:
  exact rows match under a fixed time limit.

time-budget-equivalent parity:
  differences are only due to anytime boundary / timeout/no-solution classification and disappear or are classified under sequential/longer-budget reproduction.
```

Required decision:

```text
If strict parity can be restored by runner/reporting fixes:
  require strict parity for G4.

If strict wall-clock parity cannot be guaranteed because of anytime time checks:
  keep strict parity smoke gates.
  for broad validation, require semantic parity + time-budget-equivalence audit.
  explicitly label this as not sufficient for Phase5.5 until a final accepted parity policy exists.

Do not silently replace exact parity with semantic parity.
```

## P4. Gate tests and runner hardening

Implement tests or manual fallback checks for:

```text
- bool False never passes zero-count gates
- strict parity false implies protocol_gates_passed=false
- true_semantic_parity_mismatch_count=0 does not by itself imply strict exact parity
- synthetic diagnostic rows are not counted as raw solver rows on resume
- return code 2 is handled consistently as no-solution/timeout, not solver crash
- selected/representation gates cannot override protocol failure
```

Suggested files:

```text
tests/test_repair5g31_protocol_gates.py
```

If pytest is unavailable, the manual fallback harness must explicitly run these test functions and report them.

## P5. Only after protocol closure: G4 clean frozen validation

If and only if P1/P2/P3/P4 pass, run a new clean frozen validation. Do not use IDs 66..105.

Implement:

```text
scripts/run_repair5g4_clean_frozen_validation.py
```

Run:

```text
maps = random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
agents = 50, 100
instance_ids = 126..165
time_limit_sec = 3.0
ltm_max_iterations = 4
chunk_resume = true
```

Methods:

```text
Core controls:
  lacam_star_ltm
  always_additive_defer
  repair5f_candidate_additive_ltm
  laur_disable
  laur_force_additive_direct
  repair5g_dual_additive_parity
  repair5g_dual_c_equiv_additive

Scalar/C-equiv:
  repair5f_static_c100_b100_w075_d090
  repair5f4_best_static_c125_b125_w075_d095_diagnostic_only
  repair5g2_c_equiv_best_frozen_baseline
  repair5g_dual_c_equiv_c100_b100_w075_d095
  repair5g_dual_c_equiv_c100_b100_w075_d100

Frozen flow-shield:
  repair5g2_frozen_static_or_selector
  repair5g2_best_frozen_static_candidate
  repair5g2_g1_top_diagnostic_candidate
  repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75
  repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75
  repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p75
  repair5g1_shield_c100_b100_w075_d095_beta0p35_max0p75

Diagnostics:
  repair5g4_random_flow_shield_diagnostic_seed0
  repair5g4_random_flow_shield_diagnostic_seed1
  repair5g4_shuffled_flow_shield_diagnostic_seed0
  repair5g4_shuffled_goal_progress_diagnostic_seed0
```

Outputs:

```text
outputs/logs/phase5p5_repair5g4_clean_frozen_validation/phase5p5_repair5g4_clean_frozen_validation.jsonl
outputs/logs/phase5p5_repair5g4_clean_frozen_validation/phase5p5_repair5g4_clean_frozen_validation_commands.jsonl
outputs/logs/phase5p5_repair5g4_clean_frozen_validation/phase5p5_repair5g4_clean_frozen_validation_ltm_updates.jsonl
outputs/tables/phase5p5_repair5g4_clean_frozen_validation_paired.csv
outputs/tables/phase5p5_repair5g4_clean_frozen_validation_summary.csv
outputs/tables/phase5p5_repair5g4_clean_frozen_validation_by_map_agent.csv
outputs/tables/phase5p5_repair5g4_clean_frozen_validation_oracle_regret.csv
outputs/reports/phase5p5_repair5g4_clean_frozen_validation_report.md
outputs/reports/phase5p5_repair5g4_clean_frozen_validation_summary.json
outputs/reports/phase5p5_repair5g4_clean_frozen_validation_audit.md
```

G4 clean validation gates:

```text
protocol:
  expected_rows_full = true
  missing_rows = 0
  schema_errors = 0
  solver_crash_count = 0
  true_semantic_parity_mismatch_count = 0
  parity_policy_compliant = true
  all_costs_finite = true
  cost_bounds_respected = true
  no IDs <=125 used as G4 clean validation

selected/static:
  best_flow_shield_mean_delta_ratio_vs_ltm < -0.010
  best_flow_shield_bootstrap_probability_mean_delta_lt_0 >= 0.99
  best_flow_shield_ratio_worse_than_ltm_groups = 0
  best_flow_shield_success_worse_than_ltm_groups = 0

representation:
  best_c_equiv_at_least_0p006_worse_than_best_flow = true
  best_scalar_at_least_0p006_worse_than_best_flow = true
  flow_shield_family_beats_random_median = true
  flow_shield_family_beats_shuffled_goal_progress_median = true

selector:
  classify only:
    selector_beats_static
    static_beats_selector
    tied_within_0p001
```

Do not force selector to beat static. The current likely claim is:

```text
flow_shield_static_or_representation_validated
```

not:

```text
selector_policy_validated
```

## P6. Only after G4 protocol + representation pass: time/iteration stress

If P5 passes, run:

```text
scripts/run_repair5g4_time_iteration_stress.py
```

Run:

```text
instance_ids = 126..145
time_limit_sec in {1.0, 3.0, 5.0, 10.0}
ltm_max_iterations in {2, 4, 8}
methods:
  controls
  best static flow-shield
  frozen selector
  C-equiv baseline
  shuffled/random diagnostics
```

Outputs:

```text
outputs/reports/phase5p5_repair5g4_time_iteration_stress_report.md
outputs/reports/phase5p5_repair5g4_time_iteration_stress_summary.json
outputs/tables/phase5p5_repair5g4_time_iteration_stress_by_budget.csv
outputs/tables/phase5p5_repair5g4_time_iteration_stress_by_iteration.csv
```

Interpretation:

```text
- 1s may be noisy.
- 3s should reproduce G4 sign.
- 5s/10s should not reverse the sign.
- 8 iterations should not introduce broad harm.
```

## P7. Learning bridge: offline first, runtime later

Only after P1-P4 protocol closure. If G4 is not run, still allowed to build the offline dataset, but do not run a learned selector on fresh holdout.

Implement or update:

```text
scripts/create_repair5g4_learning_bridge_dataset.py
scripts/tune_repair5g4_contextual_flow_shield_selector.py
```

Purpose:

```text
Move from hand-coded static/map-agent flow-shield rules toward learning-enhanced UpdateLTM:
  pre-update trace/context features -> choose bounded flow-shield UpdateLTM parameters
```

Allowed features:

```text
map_width
map_height
obstacle_ratio
free_cells
agents
density
ltm_iterations
returned_solutions_count_so_far
has_incumbent_before
best_ratio_before
improved_last_iteration
committed_count
blocked_count
wait_event_count
progress_committed_count
nonprogress_committed_count
blocked_per_committed
wait_per_committed
blocked_per_agent
committed_per_agent
progress_ratio
c_update_count
f_update_count
c_nonzero_edges
f_nonzero_edges
c_flow_update_ratio
cost_min
cost_max
cost_span
cost_bounds_respected
```

Forbidden features:

```text
instance_id
seed
scen filename
held-out outcome columns
oracle label from held-out fold
future solver outcome after the chosen update
action labels
restart labels
priority labels
h_i(v)
candidate deletion labels
```

Selectors to test offline:

```text
best static flow-shield
G2 map-agent selector
risk-capped flow-shield selector
decision stump
small decision tree
linear score selector
margin selector with C-equiv/additive fallback
shuffled-label diagnostic
random-feature diagnostic
```

Learning bridge dev gates:

```text
learned_selector_uses_no_forbidden_features = true
learned_selector_not_map_agent_lookup_only = true
learned_selector_mean_delta_ratio_vs_ltm < -0.010 on cross-validation
learned_selector_bootstrap_probability_mean_delta_lt_0 >= 0.99
learned_selector_success_worse_than_ltm_groups = 0
learned_selector_beats_static_or_matches_within_0p001 = true
learned_selector_beats_shuffled_label_diagnostic = true
learned_selector_beats_random_feature_diagnostic = true
```

If runtime integration is not available, write:

```text
outputs/reports/phase5p5_repair5g4_contextual_selector_runtime_gap.md
```

Do not fake runtime results.

If learned selector is frozen and runtime integration is available, reserve a new clean range:

```text
learning fresh eval IDs = 166..205 or next untouched range
```

## P8. Final decision

Write:

```text
outputs/reports/phase5p5_repair5g31_g4_decision.md
outputs/reports/phase5p5_repair5g31_g4_decision_summary.json
```

Decision options:

```text
stop_for_semantic_parity_bug
stop_for_protocol_parity_unresolved
continue_g4_clean_validation
flow_shield_static_validated_protocol_clean
flow_shield_representation_valid_selector_unclear
continue_learning_bridge_offline
continue_learning_bridge_runtime_fresh_eval
return_to_representation_design
protocol_failed
```

The decision must answer:

```text
1. What exactly caused G3 strict parity failure?
2. Is it a true semantic mismatch or time-budget/reporting equivalence?
3. Is the protocol now clean enough for a new final validation?
4. Did G4 clean validation pass, if run?
5. Is static flow-shield enough?
6. Does selector add value over static?
7. Is a learned contextual UpdateLTM selector justified?
8. Which IDs are now observed?
9. Which clean IDs are reserved next?
```

---

## 5. Validation requirements

Run:

```text
python -m py_compile \
  scripts/analyze_repair5g3_protocol_failure.py \
  scripts/run_repair5g31_control_parity_reproducer.py \
  scripts/run_repair5g4_clean_frozen_validation.py \
  scripts/run_repair5g4_time_iteration_stress.py \
  scripts/create_repair5g4_learning_bridge_dataset.py \
  scripts/tune_repair5g4_contextual_flow_shield_selector.py
```

Run pytest if available. If unavailable, run manual fallback and explicitly list every test function.

If C++ changed:

```text
scripts/build_phase1a_batch.ps1
```

Always run:

```text
git diff --check
```

Commit only G3.1/G4-related tracked files and reports. Leave unrelated dirty/untracked files untouched. Large raw JSONL logs may remain ignored, but committed summaries/manifests must be sufficient to audit the run.

Commit message:

```text
repair5g: close protocol parity and validate flow-shield cleanly
```

---

# Codex prompt

Continue czr004 on branch `phase4f5p5-stable-attention-lau` after commit `834bc28 repair5g: broaden flow-shield validation and prepare learned selector`.

Goal:
Implement Repair5G.3.1 / G4: close the G3 protocol-parity failure, then only if the protocol is clean run a new clean frozen validation for goal-aware flow-shield dual-channel LTM. Prepare, but do not overclaim, the learning-enhanced UpdateLTM bridge.

Main project objective:
Use learning-enhanced `UpdateLTM` to replace the coarse additive update in the LTM paper and eventually beat `LaCAM*+plain additive LTM` under closed-loop solver metrics, without changing LaCAM*/PIBT semantics.

Read first:
```text
deep-research-report.md
phase4_6_laur_ltm_codex_execution_plan.md
czr004_repair5g2_flow_shield_selector_fresh_validation_plan.md
czr004_repair5g3_broader_validation_learning_bridge_plan.md
outputs/reports/phase5p5_repair5g2_final_interpretation.md
outputs/reports/phase5p5_repair5g3_protocol_overview.md
outputs/reports/phase5p5_repair5g3_determinism_repeat_summary.json
outputs/reports/phase5p5_repair5g3_broader_validation_summary.json
outputs/reports/phase5p5_repair5g3_broader_validation_audit.md
outputs/reports/phase5p5_repair5g3_decision.md
outputs/tables/phase5p5_repair5g3_broader_validation_paired.csv
outputs/tables/phase5p5_repair5g3_broader_validation_summary.csv
outputs/tables/phase5p5_repair5g3_broader_validation_by_map_agent.csv
```

Preserve this interpretation:
```text
- G3 is protocol_failed, not representation_failed.
- P3 determinism repeat passed.
- P4 broader validation completed all 6240 / 6240 rows.
- selected_gates_passed=true and representation_gates_passed=true.
- protocol_gates_passed=false because strict exact control parity flags are false.
- true_semantic_parity_mismatch_count=0.
- selected flow-shield result on IDs 66..105:
    repair5g2_frozen_static_or_selector
    132 / 60 / 31
    mean_delta_ratio_vs_ltm = -0.019665489611971558
- best static flow-shield:
    repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75
    127 / 62 / 34
    mean_delta_ratio_vs_ltm = -0.02004726679608962
- C-equiv/scalar baselines are much weaker.
- selector vs static is tied_within_0p001.
- Stress and learning-bridge runtime evaluation were correctly not run.
- IDs 1..105 are now observed. Do not reuse IDs 66..105 as untouched final evidence.
- phase5p5_allowed=false and phase6_allowed=false remain mandatory.
```

Do not:
```text
- modify external/lacam2/lacam2/**
- change PIBT, LaCAM*, candidate generation, conflict, pruning, OPEN/EXPLORED, rewrite, incumbent, or restart semantics
- introduce action prediction
- introduce learned restart
- output h_i(v), action logits, priority overrides, or candidate deletion
- silently loosen parity gates
- claim Phase5.5 or Phase6
- treat IDs 66..105 as clean final evidence
- use future clean validation IDs for tuning
```

Tasks:

1. Add `czr004_repair5g31_protocol_closure_g4_clean_validation_plan.md` to repo root and update `docs/codex-worklog.md`.

2. Write:
```text
outputs/reports/phase5p5_repair5g3_final_interpretation.md
outputs/reports/phase5p5_repair5g31_protocol_closure_overview.md
```

3. Implement `scripts/analyze_repair5g3_protocol_failure.py`.

Write:
```text
outputs/reports/phase5p5_repair5g3_protocol_failure_autopsy.md
outputs/reports/phase5p5_repair5g3_protocol_failure_autopsy_summary.json
outputs/tables/phase5p5_repair5g3_protocol_parity_mismatch_cases.csv
outputs/tables/phase5p5_repair5g3_protocol_returncode2_cases.csv
outputs/tables/phase5p5_repair5g3_protocol_gate_type_audit.csv
outputs/tables/phase5p5_repair5g3_protocol_resume_duplicate_audit.csv
```

Must classify every strict parity mismatch and detect bool-as-int gate bugs.

4. Implement `scripts/run_repair5g31_control_parity_reproducer.py`.

Run mismatch cases and sentinel cases sequentially:
```text
time_limit_sec = 3.0, 5.0, 10.0
max_workers = 1 for sequential modes
repeats according to the plan
control methods only
```

If a true semantic mismatch appears, stop.

5. Write:
```text
outputs/reports/phase5p5_repair5g31_parity_policy.md
outputs/reports/phase5p5_repair5g31_parity_policy_summary.json
```

Do not silently replace exact parity with semantic parity. Explain the policy.

6. Add protocol gate tests:
```text
tests/test_repair5g31_protocol_gates.py
```

Required checks:
```text
False does not pass zero-count gates.
strict parity false implies protocol_gates_passed=false.
true semantic mismatch count zero does not imply exact parity.
selected/representation gates cannot override protocol failure.
synthetic rows are not raw solver rows on resume.
return code 2 is classified consistently.
```

7. Only if protocol closure passes, implement and run:
```text
scripts/run_repair5g4_clean_frozen_validation.py
```

Use clean IDs:
```text
instance_ids = 126..165
maps = random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
agents = 50, 100
time_limit_sec = 3.0
ltm_max_iterations = 4
```

Use the method set in the plan. Do not tune on these IDs.

8. Only if G4 clean validation passes, run:
```text
scripts/run_repair5g4_time_iteration_stress.py
```

9. Build the offline learning bridge only after protocol closure:
```text
scripts/create_repair5g4_learning_bridge_dataset.py
scripts/tune_repair5g4_contextual_flow_shield_selector.py
```

This must stay inside `UpdateLTM` parameter selection. If runtime integration is not available, write a runtime-gap report and do not fake a runtime learned-selector result.

10. Write:
```text
outputs/reports/phase5p5_repair5g31_g4_decision.md
outputs/reports/phase5p5_repair5g31_g4_decision_summary.json
```

Decision options:
```text
stop_for_semantic_parity_bug
stop_for_protocol_parity_unresolved
continue_g4_clean_validation
flow_shield_static_validated_protocol_clean
flow_shield_representation_valid_selector_unclear
continue_learning_bridge_offline
continue_learning_bridge_runtime_fresh_eval
return_to_representation_design
protocol_failed
```

Validation:
```text
py_compile all new/modified Python scripts
pytest if available; otherwise manual fallback harness over all relevant tests
if C++ changed, run scripts/build_phase1a_batch.ps1
git diff --check
commit and push only G3.1/G4-related tracked files and reports
leave unrelated dirty/untracked files untouched
```

Commit message:
```text
repair5g: close protocol parity and validate flow-shield cleanly
```
