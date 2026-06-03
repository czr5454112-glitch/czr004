# czr004 Repair5G.2 Plan: Flow-Shield Selector Protocol and Fresh Validation for Goal-Aware Dual-Channel LTM

**Branch:** `phase4f5p5-stable-attention-lau`
**Start after commit:** `19663c6 repair5g: close c-channel parity and probe agent-aware dual ltm`
**Status:** completed diagnostic / frozen selector fresh validation passed
**Promotion status:** `phase5p5_allowed=false`, `phase6_allowed=false`
**Main project objective:** use learning-enhanced `UpdateLTM` to replace the coarse additive LTM update from the LTM paper and eventually beat `LaCAM*+plain additive LTM` under closed-loop solver metrics, without changing LaCAM*/PIBT semantics.

---

## 0. Executive decision

Repair5G.1 is the first genuinely strong positive signal for the goal-aware dual-channel LTM direction.

The key shift is:

```text
G0 global flow bonus:
  failed; no oracle headroom.

G1 agent-aware / flow-shielded dual channel:
  strong development oracle and strong static candidates.
```

Repair5G.2 should **not** jump to Phase5.5, Phase6, or a paper claim. It should now answer the next scientific question:

```text
Can a non-leaky selector or static-candidate protocol recover the G1 flow-shield headroom
on a fresh final holdout that was not used for candidate design or selector tuning?
```

The central candidate family to carry forward is `flow_shield`, especially candidates around:

```text
repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75
repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75
repair5g1_shield_c100_b100_w075_d095_beta0p35_max0p75
repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p75
```

But these were identified using IDs `26..45`, so they are **diagnostic-only until validated under a frozen protocol on untouched IDs**.

---

## 1. Current evidence to preserve

### 1.1 Repair5F.4.1: scalar bounded UpdateParams still has headroom

Repair5F.4.1 showed the scalar bounded lattice has strong development oracle headroom:

```text
F4 full-lattice oracle on IDs 26..45:
  better / equal / worse = 67 / 53 / 0
  mean_delta_ratio_vs_ltm = -0.017388555948699997
  ratio_worse_than_ltm_groups = 0
  success_worse_than_ltm_groups = 0
```

It also showed the old support selector objective was unreliable:

```text
support-vs-F4 Spearman = 0.18987049028677153
locked support rank = 1
locked F4 rank = 27
```

Interpretation:

```text
UpdateLTM has headroom, but the previous support-only static selector overfit or used a weak objective.
```

### 1.2 Repair5G.0: global flow bonus failed

Repair5G.0 implemented a simple dual-channel design:

```text
C[e] = congestion / blockage / wait-risk evidence
F[e] = successful goal-progress flow / corridor evidence
cost(e) = clip(1 + lambda_cong*C(e) - lambda_flow*F(e))
```

This failed:

```text
G0 dual-channel oracle:
  better / equal / worse = 29 / 55 / 36
  mean_delta_ratio_vs_ltm = +0.001879629688233328
```

Interpretation:

```text
A global edge-level flow bonus is not safe: a flow edge useful for one agent can be harmful for another.
```

### 1.3 Repair5G.1: C-channel equivalence + flow-shield worked

Repair5G.1 fixed the important semantic issue:

```text
G0 committed progress -> F only
G1 committed progress -> C and optionally F
```

G1 also added projection modes:

```text
none
agent_progress
flow_shield
```

Smoke gates passed exactly:

```text
additive_parity_exact = true
laur_disable_parity_exact = true
laur_force_additive_direct_parity_exact = true
dual_additive_parity_exact = true
dual_c_equiv_additive_parity_exact = true
dual_c_equiv_locked_matches_scalar = true
dual_c_equiv_best_f4_static_matches_scalar = true
```

G1 development oracle on IDs `26..45` was strong:

```text
repair5g1_agent_aware_dual_channel_oracle_static_proxy:
  better / equal / worse = 82 / 38 / 0
  mean_delta_ratio_vs_ltm = -0.033505006472296615
  bootstrap CI = [-0.038997441793415265, -0.028073538158008476]
```

The best component family was flow-shield:

```text
flow_shield:
  candidates = 36
  best mean delta = -0.014306860332393171
  mean of means = -0.004100773448490892
  total better = 1561
  total worse = 940
```

Top observed candidate:

```text
repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75:
  better / equal / worse = 67 / 37 / 16
  mean_delta_ratio_vs_ltm = -0.014306860332393171
```

Interpretation:

```text
Flow-shield is currently the strongest Repair5 signal. It does not make edges globally cheap;
it uses flow/corridor evidence to reduce over-penalization of current-agent progress edges.
```

### 1.4 Caveat: full dev report parity fields need cleanup

The G1 sequential smoke closes parity and C-equivalence. The G1 oracle summary also reports `dual_c_equiv_closed=true`.

However, the full development report still records some bulk-run parity fields as false. Treat this as a reporting/protocol issue that must be audited before any final claim.

G2 must therefore include a **post-G1 parity and determinism audit** and, if needed, rerun controls under the sequential protocol used by the smoke test.

---

## 2. Scientific interpretation

Repair5G.1 supports the following hypothesis:

```text
The useful goal-aware dual-channel operation is not a direct flow bonus.
It is a flow-shield:
  C-channel stores congestion penalty;
  F-channel stores successful goal-progress / corridor evidence;
  F does not directly attract all agents;
  F reduces C's over-penalty only for the current agent's progress edges.
```

This keeps the project aligned with the main goal:

```text
Learn how to update the traffic map and transform trace evidence into search guidance,
without learning actions, priorities, restarts, or modifying LaCAM*/PIBT semantics.
```

Repair5G.2 should not introduce neural networks yet. First, it should determine whether a deterministic, non-leaky selector or static protocol can recover the G1 headroom.

---

## 3. Non-negotiable constraints

Do not:

```text
- modify external/lacam2/lacam2/**
- change PIBT legality or priority-inheritance semantics
- change LaCAM* candidate generation
- change vertex/swap conflict handling
- change OPEN/EXPLORED/rewrite semantics
- change incumbent pruning
- change restart semantics
- introduce action prediction
- introduce learned restart
- output learned h_i(v), action logits, priority overrides, or candidate deletion
- claim context-adaptive learned heuristic
- claim Phase5.5 or Phase6
- promote any candidate selected using IDs 26..45 without untouched final validation
```

Must preserve:

```text
- exact additive fallback
- laur-disable parity
- force-additive parity
- dual-additive parity
- dual C-equivalence for scalar candidates
- bounded finite costs
- no solver crashes
- diagnostic_only=true until a future formal promotion gate
```

---

## 4. Repair5G.2 objective

Primary question:

```text
Can a frozen Repair5G flow-shield candidate or selector, trained/tuned only on development data,
beat additive LTM on untouched fresh IDs?
```

Secondary questions:

```text
1. Is the top flow-shield candidate robust, or did it overfit IDs 26..45?
2. Is a static candidate enough, or is map/agent group-aware selection needed?
3. Does flow-shield consistently beat C-equivalent congestion-only candidates?
4. Does flow-shield beat shuffled/random dual-channel diagnostics?
5. Does flow-shield keep success regressions at zero?
```

---

## 5. Data split policy

Use three tiers:

```text
Development support:
  IDs 1..25
  Allowed for candidate support probe and selector training.

Development validation:
  IDs 26..45
  Already observed by F4/G1. Allowed for model-selection diagnostics and selector development.
  Not allowed as final evidence.

Untouched final candidate validation:
  Prefer IDs 46..65.
  Use only after a selector/static protocol is frozen.
  If IDs 46..65 are unavailable, deterministically generate them using the existing scenario generator and record the generation manifest.
```

If IDs 46..65 are used in G2, they become observed and must not be reused as untouched final in later G3 unless explicitly relabeled. If G2 final passes, later broader validation should move to IDs 66..85 or another fresh range.

---

## 6. Required work

## P0. Documentation and carry-forward interpretation

Add/update:

```text
czr004_repair5g2_flow_shield_selector_fresh_validation_plan.md
docs/codex-worklog.md
outputs/reports/phase5p5_repair5g1_final_interpretation.md
outputs/reports/phase5p5_repair5g2_protocol_overview.md
```

The interpretation must say:

```text
- G0 global flow bonus failed.
- G1 flow-shield produced strong development headroom.
- G1 top candidates are diagnostic-only because IDs 26..45 were observed.
- G2 must use a non-leaky selector/static protocol and untouched final IDs.
- phase5p5_allowed=false and phase6_allowed=false remain closed.
```

## P1. Post-G1 parity / determinism audit

Implement:

```text
scripts/analyze_repair5g1_parity_determinism.py
```

Inputs:

```text
outputs/reports/phase5p5_repair5g1_smoke_summary.json
outputs/reports/phase5p5_repair5g1_dev_probe_summary.json
outputs/reports/phase5p5_repair5g1_agent_aware_dual_channel_oracle_summary.json
outputs/tables/phase5p5_repair5g1_dev_utility_long.csv
outputs/tables/phase5p5_repair5g1_dev_utility_wide.csv
```

Outputs:

```text
outputs/reports/phase5p5_repair5g1_parity_determinism_audit.md
outputs/reports/phase5p5_repair5g1_parity_determinism_audit_summary.json
outputs/tables/phase5p5_repair5g1_parity_mismatch_cases.csv
```

Required checks:

```text
- smoke additive parity exact
- smoke dual C-equivalence exact
- bulk dev parity discrepancy classified
- whether discrepancy is reporting-only, time-budget sensitivity, missing row, or true semantic mismatch
- whether top G1 flow-shield conclusions are robust to the sequential smoke controls
```

If there is a true semantic mismatch, stop before final validation.

## P2. Create a G2 candidate subset

Implement:

```text
scripts/create_repair5g2_candidate_subset.py
```

Candidate subset should include about 32-64 methods, not the full 136 unless runtime is acceptable.

Include:

```text
Controls:
  lacam_star_ltm
  always_additive_defer
  repair5f_candidate_additive_ltm
  laur_disable
  laur_force_additive_direct
  repair5g_dual_additive_parity
  repair5g_dual_c_equiv_additive

C-equivalent baselines:
  repair5g_dual_c_equiv_c100_b125_w075_d100
  repair5g_dual_c_equiv_c125_b125_w075_d095
  repair5g_dual_c_equiv_c100_b100_w075_d095
  repair5g_dual_c_equiv_c100_b100_w075_d100
  repair5g_dual_c_equiv_c100_b100_w075_d090

Flow-shield top family:
  top 24-36 flow_shield candidates from G1 ranking.
  Must include beta in {0.05, 0.1, 0.2, 0.35} and max_shield in {0.25, 0.5, 0.75} around:
    c125_b125_w075_d095
    c100_b125_w075_d100
    c100_b100_w075_d095

Agent-progress F diagnostics:
  top 4-8 agent_progress_f candidates.

Diagnostics:
  deterministic random candidate diagnostic
  shuffled goal-progress diagnostic
  shuffled flow-shield diagnostic if cheap
```

Write:

```text
outputs/tables/phase5p5_repair5g2_candidate_subset.csv
outputs/reports/phase5p5_repair5g2_candidate_subset_report.md
outputs/reports/phase5p5_repair5g2_candidate_subset_summary.json
```

## P3. Run support probe for G2 candidate subset on IDs 1..25

Implement or extend:

```text
scripts/run_repair5g2_flow_shield_selector_protocol.py
```

Run:

```text
maps = random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
agents = 50, 100
instance_ids = 1..25
candidate_subset = from P2
time_limit_sec = 3.0
ltm_max_iterations = 4
```

Use chunk/resume. Write:

```text
outputs/logs/phase5p5_repair5g2_support_probe/phase5p5_repair5g2_support_probe.jsonl
outputs/logs/phase5p5_repair5g2_support_probe/phase5p5_repair5g2_support_probe_commands.jsonl
outputs/logs/phase5p5_repair5g2_support_probe/phase5p5_repair5g2_support_probe_ltm_updates.jsonl
outputs/tables/phase5p5_repair5g2_support_utility_long.csv
outputs/tables/phase5p5_repair5g2_support_utility_wide.csv
outputs/reports/phase5p5_repair5g2_support_probe_report.md
outputs/reports/phase5p5_repair5g2_support_probe_summary.json
outputs/reports/phase5p5_repair5g2_support_probe_audit.md
```

Required support gates:

```text
missing_rows = 0
schema_errors = 0
additive parity exact
laur-disable parity exact
force-additive parity exact
dual-additive parity exact
dual C-equivalence controls exact
cost bounds respected
no solver crashes
```

## P4. Build selector training table from IDs 1..45

Use:

```text
support IDs 1..25 from P3
existing G1 dev IDs 26..45
```

Implement:

```text
scripts/create_repair5g2_selector_training_table.py
```

Allowed selector features:

```text
map family / map dimensions / obstacle ratio
agents / density
iteration stats available before update
trace counts: committed, blocked, wait
progress counts and ratios
C-channel summary
F-channel summary
cost audit summary
best_ratio_before / has_incumbent_before / improved_last_iteration
```

Forbidden features:

```text
instance_id as decision feature
seed as decision feature
candidate outcome columns from held-out evaluation fold
final solver outcome not available before update
F4/G1 oracle label as a runtime decision feature
```

Write:

```text
outputs/tables/phase5p5_repair5g2_selector_train_contexts.csv
outputs/reports/phase5p5_repair5g2_selector_training_table_report.md
outputs/reports/phase5p5_repair5g2_selector_training_table_summary.json
```

## P5. Tune deterministic selectors on development data only

Implement:

```text
scripts/tune_repair5g2_flow_shield_selector.py
```

Selectors to evaluate:

```text
1. support-best static candidate
2. risk-capped static candidate
3. map-agent group static selector
4. leave-one-group robust selector
5. flow-shield-family-only selector
6. margin selector with additive fallback
7. C-equiv fallback selector
8. random/shuffled utility diagnostics
```

Use crossfold diagnostics:

```text
- leave-one-ID-block
- leave-one-map-agent group
- train IDs 1..25 -> validate IDs 26..45
- train IDs 1..20 + 26..35 -> validate IDs 36..45, if data exists
```

Write:

```text
outputs/tables/phase5p5_repair5g2_selector_sweep.csv
outputs/tables/phase5p5_repair5g2_selector_decisions_dev.csv
outputs/tables/phase5p5_repair5g2_selector_paired_dev.csv
outputs/reports/phase5p5_repair5g2_selector_sweep_report.md
outputs/reports/phase5p5_repair5g2_selector_sweep_summary.json
```

Development gates before any fresh final validation:

```text
selector_better_gt_worse = true
selector_mean_delta_ratio_vs_ltm < -0.003
selector_bootstrap_probability_mean_delta_lt_0 >= 0.95
selector_ratio_worse_than_ltm_groups <= 1
selector_success_worse_than_ltm_groups = 0
selector_beats_random_diagnostic = true
selector_beats_shuffled_diagnostic = true
selector_uses_no_forbidden_features = true
```

If these gates fail, stop. Do not run fresh final validation. Write failure diagnosis.

## P6. Freeze selected protocol

If P5 passes, write a frozen selector spec:

```text
outputs/reports/phase5p5_repair5g2_frozen_selector_spec.json
outputs/reports/phase5p5_repair5g2_frozen_selector_report.md
```

It must include:

```text
selected selector type
selected candidates / group rules
support/dev data used
forbidden final IDs not used
all candidate parameters
fallback rules
phase5p5_allowed=false
phase6_allowed=false
```

Do not modify the frozen selector after looking at final IDs.

## P7. Fresh final validation on untouched IDs 46..65

Only run if P5 passes.

Scope:

```text
maps = random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
agents = 50, 100
instance_ids = 46..65
time_limit_sec = 3.0
ltm_max_iterations = 4
```

Methods:

```text
lacam_star_ltm
always_additive_defer
repair5f_candidate_additive_ltm
laur_disable
laur_force_additive_direct
repair5g_dual_additive_parity
repair5g_dual_c_equiv_additive
repair5g2_frozen_static_or_selector
best frozen static candidate, if different
best frozen group selector, if different
C-equiv best frozen baseline
G1 top diagnostic candidate, for comparator only
repair5g2_random_candidate_diagnostic
repair5g2_shuffled_goal_or_flow_diagnostic
```

Write:

```text
outputs/logs/phase5p5_repair5g2_fresh_final_eval/phase5p5_repair5g2_fresh_final_eval.jsonl
outputs/logs/phase5p5_repair5g2_fresh_final_eval/phase5p5_repair5g2_fresh_final_eval_commands.jsonl
outputs/logs/phase5p5_repair5g2_fresh_final_eval/phase5p5_repair5g2_fresh_final_eval_ltm_updates.jsonl
outputs/tables/phase5p5_repair5g2_fresh_final_eval_paired.csv
outputs/tables/phase5p5_repair5g2_fresh_final_eval_summary.csv
outputs/tables/phase5p5_repair5g2_fresh_final_eval_by_map_agent.csv
outputs/reports/phase5p5_repair5g2_fresh_final_eval_report.md
outputs/reports/phase5p5_repair5g2_fresh_final_eval_summary.json
outputs/reports/phase5p5_repair5g2_fresh_final_eval_audit.md
```

Fresh final gates:

```text
full_expected_rows = true
missing_rows = 0
schema_errors = 0
final_ids_not_used_in_tuning = true
additive parity exact = true
laur-disable parity exact = true
force-additive parity exact = true
dual-additive parity exact = true
cost bounds respected = true
selected method better > worse
selected method mean_delta_ratio_vs_ltm < 0
selected method bootstrap_probability_mean_delta_lt_0 >= 0.95
selected method ratio_worse_than_ltm_groups <= 1
selected method success_worse_than_ltm_groups = 0
selected method beats random diagnostic
selected method beats shuffled diagnostic
phase5p5_allowed=false
phase6_allowed=false
```

If final passes, do not claim Phase5.5. Recommend Repair5G.3 broader validation on fresh IDs/time budgets. If final fails, diagnose and do not retune on IDs 46..65.

## P8. Optional robustness stress if final passes early

Only if P7 passes and time remains, run a small stress panel on the frozen method and controls:

```text
time_limit_sec in {1.0, 5.0}
instance_ids = 46..55
methods = baseline controls + frozen selected method + random/shuffled diagnostics
```

Write under:

```text
outputs/logs/phase5p5_repair5g2_time_stress_smoke/
outputs/reports/phase5p5_repair5g2_time_stress_smoke_report.md
```

This is supplemental only, not a replacement for P7.

## P9. Decision report

Write:

```text
outputs/reports/phase5p5_repair5g2_decision.md
```

Decision options:

```text
1. continue_repair5g3_broader_validation
   if fresh final passes.

2. selector_protocol_failed_dev
   if P5 gates fail.

3. selector_failed_fresh_final
   if P7 fails.

4. stop_repair5g_or_return_to_representation_design
   if parity/cost/semantic gates fail.
```

The report must explicitly state:

```text
- phase5p5_allowed=false
- phase6_allowed=false
- no learned actions
- no learned restart
- no LaCAM*/PIBT semantic change
- whether G2 supports the AAAI-style story of learning goal-aware UpdateLTM dynamics
```

---

## 7. Validation requirements

Run:

```text
python -m py_compile scripts/create_repair5g2_candidate_subset.py \
  scripts/run_repair5g2_flow_shield_selector_protocol.py \
  scripts/create_repair5g2_selector_training_table.py \
  scripts/tune_repair5g2_flow_shield_selector.py \
  scripts/analyze_repair5g2_fresh_final_eval.py

python -m pytest tests/test_repair5g_dual_channel_ltm.py tests/test_repair5f_updateparams.py -q
```

If pytest is unavailable, record it and run the manual fallback harness over all relevant tests.

If C++ changed, run:

```text
powershell -ExecutionPolicy Bypass -File scripts/build_phase1a_batch.ps1
```

Always run:

```text
git diff --check
```

Commit and push only Repair5G.2-related files and records. Leave unrelated dirty/untracked files untouched.

Commit message:

```text
repair5g: validate flow-shield selector on fresh holdout
```

---

## Completion record - 2026-06-03

Repair5G.2 completed the frozen selector protocol.

Key records:

```text
P1 parity/determinism audit:
  outputs/reports/phase5p5_repair5g1_parity_determinism_audit.md
  true_semantic_mismatch = false
  proceed_to_g2_selector_protocol = true

P2 candidate subset:
  outputs/tables/phase5p5_repair5g2_candidate_subset.csv

P3 support probe:
  outputs/reports/phase5p5_repair5g2_support_probe_summary.json
  rows = 9000 / 9000
  missing_rows = 0
  schema_errors = 0
  solver_crash_count = 0
  strict parity mismatches = 85
  true semantic parity mismatches = 0
  classification = time_budget_sensitivity only

P4/P5 selector development:
  outputs/reports/phase5p5_repair5g2_selector_sweep_summary.json
  selected selector = map_agent_group_static_selector
  dev better / equal / worse = 65 / 45 / 10
  dev mean_delta_ratio_vs_ltm = -0.014155347174674999
  dev bootstrap probability mean < 0 = 1.0

P6 frozen spec:
  outputs/reports/phase5p5_repair5g2_frozen_selector_spec.json

P7 fresh final:
  outputs/reports/phase5p5_repair5g2_fresh_final_eval_summary.json
  IDs = 46..65
  rows = 2520 / 2520
  final protocol gates passed = true
  selected better / equal / worse = 62 / 44 / 14
  selected mean_delta_ratio_vs_ltm = -0.020112979571774988
  selected bootstrap probability mean < 0 = 1.0
  selected ratio_worse_than_ltm_groups = 0
  selected success_worse_than_ltm_groups = 0

P9 decision:
  outputs/reports/phase5p5_repair5g2_decision.md
  decision = continue_repair5g3_broader_validation
```

Interpretation:

```text
G0 global flow bonus failed.
G1 flow-shield produced strong development headroom.
G1 top candidates were diagnostic-only before G2 because IDs 26..45 had been observed.
G2 froze a non-leaky selector before looking at IDs 46..65.
Fresh final IDs support the frozen flow-shield selector.
This does not promote Phase5.5 or Phase6.
```
