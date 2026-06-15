# Repair5G.5.51 Plan — Iteration-Counterfactual SafeGate Repair + Learned UpdateParams Policy Replay

Project: `czr004`
Branch: `codex/g531-slice-pilot`
Start point: G5.50 commit `a7779c5` (`repair5g: finish g550 active replay gates`)
Round name: `Repair5G.5.51 iteration-counterfactual SafeGate repair for learned UpdateParams`

## 0. Executive interpretation

G5.50 is not a dead end. It is the most useful diagnostic round so far because it moved the project from "does fulltheta contain signal?" to "why does a learned policy that looks safe offline fail fresh targeted replay?"

Treat G5.50 as:

```text
Engineering result:
  good — the G5.50 pipeline ran through expansion, active theta search,
  offline policy, targeted replay, and iteration-counterfactual preflight.

Scientific result:
  mixed/negative for the current policy — offline safe expert mixture passed,
  but fresh targeted replay had 216 success regressions vs static_flow_shield.

Safety result:
  good — SafeGate correctly blocked blind/runtime/Phase5.5/Phase6/AAAI claims.

Research direction:
  still promising — iteration-level counterfactual preflight found a large oracle gap
  and high safe/useful context rate, so the next bottleneck is label granularity
  and risk prediction, not the absence of learnable UpdateLTM signal.
```

G5.51 must therefore **not** simply run another broad fulltheta sweep. G5.50 already did enough to show that replay-region hindsight and offline region-level gates are insufficient. The next round must convert checkpoint-level counterfactual evidence into a safer learned UpdateParams policy.

The primary research question for G5.51 is:

```text
Can iteration/checkpoint-level counterfactual labels repair the risk/abstention model
so that a learned bounded UpdateParams policy achieves zero success regressions
against static_flow_shield on fresh targeted replay while preserving nontrivial
quality improvement or useful non-static usage?
```

## 1. Non-negotiable interpretation of G5.50

Before coding, write this interpretation into `docs/codex-worklog.md`:

```markdown
## 2026-06-15 - Repair5G.5.51 iteration-counterfactual SafeGate repair

- Request:
  Continue after G5.50 commit a7779c5. G5.50 completed the local replay chain:
  68,570 fulltheta expansion rows, 50,065 active theta-search rows, offline
  safe_expert_mixture_with_abstention gate pass, 30,006 fresh targeted
  generated-theta rows, and 3,800 iteration-counterfactual preflight rows.
- Interpretation:
  G5.50 is not a deployable learned UpdateLTM success. The offline policy
  passed but targeted replay failed SafeGate with 216 success regressions
  versus static_flow_shield. Blind replay stayed closed. The current blocker is
  not fulltheta materialization, not calibration, and not a lack of oracle signal.
  The blocker is risk/abstention generalization from replay-region hindsight to
  fresh targeted contexts.
- Next scientific step:
  Use iteration-level counterfactual labels to train and calibrate a checkpoint
  risk/utility/abstention policy. Fresh targeted replay must be passed before any
  blind/runtime/Phase5.5/Phase6/AAAI claim can open.
- Baseline and SafeGate:
  static_flow_shield remains the primary baseline. additive_ltm is only the
  paper-faithful floor. strong static variants are diagnostics. SafeGate is
  tightened around targeted success-regression blocking; it is not relaxed.
- Constraints:
  No external/lacam2/lacam2 edits, no solver semantic changes, no candidate or
  PIBT conflict changes, no static selector as learned method, no IDs 166..205,
  no runtime/Phase5.5/Phase6/AAAI claims.
```

Also append a short governance update to:

```text
deep-research-report.md
docs/aaai_quality_requirements.md
docs/goal_aware_dual_channel_ltm_research_strategy.md
phase4_6_laur_ltm_codex_execution_plan.md
```

Required statement:

```text
G5.51 keeps static_flow_shield as the primary baseline and tightens SafeGate after
G5.50 targeted replay failures. Offline generator success is no longer sufficient
for promotion. A learned bounded UpdateParams policy must pass fresh targeted
replay with zero success regressions versus static_flow_shield before blind replay
or runtime claims. The next valid learning signal is iteration/checkpoint-level
counterfactual labels, not final full-run hindsight alone.
```

If any baseline or SafeGate rule is changed beyond this tightening, update all project-level governance docs in the same commit.

## 2. Guardrails

Do not modify:

```text
external/lacam2/lacam2/**
PIBT conflict semantics
candidate domain
agent actions
agent priorities
h-values
OPEN / EXPLORED
LaCAM* high-level search
rewrite / incumbent pruning
restart semantics
candidate deletion semantics
```

Keep all claim flags closed:

```json
{
  "phase5p5_allowed": false,
  "phase6_allowed": false,
  "runtime_claim_allowed": false,
  "learned_runtime_policy_validated": false,
  "aaai_ready": false
}
```

Do not use reserved IDs `166..205`.

A learned method may output only:

```text
bounded continuous UpdateParams theta
bounded residuals around static_flow_shield theta
safe expert-mixture weights materialized as bounded UpdateParams theta
ALLOW_THETA / ABSTAIN_TO_STATIC_FLOW
```

A learned method must not output static baseline IDs as its learned action:

```text
additive_ltm
static_flow_shield
best_fixed_static_goal_aware
frozen_family_static_goal_aware
```

Fallback to `static_flow_shield` is allowed only as abstention / safety fallback, not as a claimed learned non-static action.

## 3. Required files

Create:

```text
czr004_g551_iteration_counterfactual_safegate_repair_plan.md

scripts/repair5g551_common.py
scripts/verify_repair5g551_g550_artifacts.py
scripts/analyze_repair5g551_g550_failure_autopsy.py
scripts/create_repair5g551_iteration_label_expansion_plan.py
scripts/run_repair5g551_iteration_label_expansion.py
scripts/analyze_repair5g551_iteration_label_expansion.py
scripts/train_eval_repair5g551_checkpoint_policies.py
scripts/create_repair5g551_generated_theta_targeted_plan.py
scripts/run_repair5g551_generated_theta_targeted.py
scripts/analyze_repair5g551_generated_theta_targeted.py
scripts/create_repair5g551_blind_replay_if_warranted.py
scripts/run_repair5g551_blind_replay_if_warranted.py
scripts/analyze_repair5g551_blind_replay_if_warranted.py
scripts/write_repair5g551_decision.py
```

Outputs:

```text
outputs/reports/phase5p5_repair5g551_*
outputs/tables/phase5p5_repair5g551_*
artifacts/models/laur_ltm/repair5g551_*
```

Large raw plans/results must go under ignored logs:

```text
outputs/logs/phase5p5_repair5g551_*
```

Do not commit raw CSV files larger than 50 MB. Commit only:

```text
compact summaries
sample previews
policy manifests
sha256 hashes
exact resume commands
```

This is mandatory because G5.49 already pushed an oversized 87.55 MB CSV.

## 4. Stage A — Verify G5.50 and lock the interpretation

Create:

```text
scripts/verify_repair5g551_g550_artifacts.py
scripts/analyze_repair5g551_g550_failure_autopsy.py
```

Required inputs:

```text
outputs/reports/phase5p5_repair5g550_decision_summary.json
outputs/reports/phase5p5_repair5g550_fulltheta_expansion_summary.json
outputs/reports/phase5p5_repair5g550_active_theta_search_summary.json
outputs/reports/phase5p5_repair5g550_policy_family_suite_summary.json
outputs/reports/phase5p5_repair5g550_generated_theta_targeted_summary.json
outputs/reports/phase5p5_repair5g550_iteration_counterfactual_label_summary.json
outputs/tables/phase5p5_repair5g550_generated_theta_targeted_failure_cases.csv
outputs/tables/phase5p5_repair5g550_fulltheta_expansion_replication_by_stratum.csv
outputs/tables/phase5p5_repair5g550_active_theta_search_best_regions.csv
outputs/tables/phase5p5_repair5g550_policy_family_eval.csv
```

Write:

```text
outputs/reports/phase5p5_repair5g551_g550_verification.md
outputs/reports/phase5p5_repair5g551_g550_verification_summary.json
outputs/reports/phase5p5_repair5g551_targeted_failure_autopsy.md
outputs/reports/phase5p5_repair5g551_targeted_failure_autopsy_summary.json
outputs/tables/phase5p5_repair5g551_g550_artifact_audit.csv
outputs/tables/phase5p5_repair5g551_targeted_failure_by_stratum.csv
outputs/tables/phase5p5_repair5g551_targeted_failure_by_theta.csv
outputs/tables/phase5p5_repair5g551_targeted_failure_by_seed_block.csv
outputs/tables/phase5p5_repair5g551_offline_vs_targeted_shift.csv
outputs/tables/phase5p5_repair5g551_g550_claim_flag_audit.csv
```

Required checks:

```text
g550_decision = g550_iteration_counterfactual_labels_needed_before_generator
fulltheta_expansion_rows = 68570
active_theta_search_rows = 50065
offline_gate_passed = true
generator_policy_family_best = safe_expert_mixture_with_abstention
targeted_replay_run = true
targeted_new_solver_rows = 30006
targeted_success_regression_count_vs_static_flow = 216
targeted_quality_delta_vs_static_flow = -0.00097632372215
blind_replay_run = false
iteration_counterfactual_solver_rows = 3800
iteration_safe_useful_context_rate = 0.825
mean_best_oracle_delta_vs_static_flow = -0.0322337902086
warehouse_non_evaluable = true
all claim flags closed
```

The failure autopsy must answer:

```text
1. Were the 216 regressions concentrated in random-50 transfer, maze, random-100, or another stratum?
2. Were regressions concentrated in a few generated theta IDs?
3. Did targeted non-static usage (0.8333) exceed offline non-static usage (0.1973)?
4. Did the offline policy fail because of thresholding, distribution shift, missing checkpoint features, or target-plan oversampling?
5. Did G5.50 expansion fail to replicate G5.49 true regions because the region was narrow, because fresh seeds differ, or because the policy generated too broad a mixture?
6. Which failure cases are baseline-solved but theta-unsolved, and therefore hard negative safety labels?
7. Which targeted contexts show quality gain without success regression and should remain positive labels?
```

Do not proceed to policy training until Stage A writes the failure autopsy.

## 5. Stage B — Iteration-counterfactual label expansion plan

G5.50 preflight already showed that iteration-level labels are useful:

```text
counterfactual_contexts = 200
solver_rows = 3800
safe_useful_contexts = 165
safe_useful_context_rate = 0.825
mean_best_oracle_delta_vs_static_flow = -0.0322337902086
oracle_gap_large_enough_for_policy_design = true
```

G5.51 must scale this into a real training dataset.

Create:

```text
scripts/create_repair5g551_iteration_label_expansion_plan.py
```

Write:

```text
outputs/reports/phase5p5_repair5g551_iteration_label_expansion_plan.md
outputs/reports/phase5p5_repair5g551_iteration_label_expansion_plan_summary.json
outputs/tables/phase5p5_repair5g551_iteration_label_expansion_plan_preview.csv
outputs/tables/phase5p5_repair5g551_iteration_candidate_family_breakdown.csv
outputs/tables/phase5p5_repair5g551_iteration_context_sampling_breakdown.csv
```

Raw full plan goes to:

```text
outputs/logs/phase5p5_repair5g551_iteration_label_expansion/iteration_label_expansion_plan.csv
```

### B.1 Context strata

Include at least:

```text
Core calibrated/evaluable:
  random, agents 100, nominal_budget_ms 2000
  random, agents 50, nominal_budget_ms 2000
  maze, agents 50, nominal_budget_ms 2000
  maze, agents 100, nominal_budget_ms 2000

Targeted failure strata:
  random, agents 50, nominal_budget_ms 2000
  all seed blocks implicated by G5.50 targeted failures
  exact G5.50 failure seeds where scenario availability allows

Transfer diagnostics:
  maze/random 500/1000 nominal_budget_ms where finite ratios existed but pair support was weak
  warehouse with long diagnostic horizons, non-blocking

Horizon variants:
  short_budget_ms in {1000, 2000, 5000}
  base_time_limit_sec in {0.5, 1.0}
  ltm_max_iterations in {2, 4}
```

Warehouse remains diagnostic and must not block local development.

### B.2 Candidate theta families

Use checkpoint-level counterfactual candidates, not only full-run region clusters.

Include:

```text
1. static_flow_shield baseline theta
2. additive_ltm paper floor
3. G5.49 true-region best examples
4. G5.50 active-search true/safe examples
5. G5.50 unsafe-useful examples as hard risk negatives
6. G5.50 targeted failure theta IDs as hard negative safety labels
7. conservative shrinkage variants: 10%, 25%, 50%, 75% toward static_flow_shield
8. bounded residual variants around static_flow_shield
9. safe expert-mixture candidates with lower non-static usage
10. risk-control ablation candidates
11. random/Sobol negative controls
12. no-op / force-additive parity controls
```

At least 50% of candidate rows must vary fields that matter to `goal_aware_dual_channel_ltm`:

```text
theta_alpha_flow_wait_progress
theta_lambda_flow
theta_lambda_cong
theta_flow_shield_beta
theta_max_flow_shield
theta_min_edge_cost
theta_max_edge_cost
theta_goal_projection_mode_*
theta_alpha_cong_commit_nonprogress
```

### B.3 Dataset size

Hard local minimum:

```text
planned_iteration_counterfactual_solver_rows >= 64000
planned_contexts >= 3200
candidate_theta_per_context >= 16
failure-focused_context_fraction >= 0.25
fresh_seed_blocks >= 8
```

Preferred local target:

```text
planned_iteration_counterfactual_solver_rows >= 128000
planned_contexts >= 6400
candidate_theta_per_context >= 20
fresh_seed_blocks >= 12
```

Stretch target if local PC remains stable:

```text
planned_iteration_counterfactual_solver_rows >= 256000
```

If local runtime is high, use row-limit chunks and resume, but do not stop after writing the plan. G5.51 must run at least the hard local minimum unless there is a concrete failing command.

## 6. Stage C — Run and analyze iteration-counterfactual labels

Create:

```text
scripts/run_repair5g551_iteration_label_expansion.py
scripts/analyze_repair5g551_iteration_label_expansion.py
```

Write compact tracked outputs:

```text
outputs/reports/phase5p5_repair5g551_iteration_label_expansion.md
outputs/reports/phase5p5_repair5g551_iteration_label_expansion_summary.json
outputs/tables/phase5p5_repair5g551_iteration_label_sample.csv
outputs/tables/phase5p5_repair5g551_iteration_contexts_sample.csv
outputs/tables/phase5p5_repair5g551_iteration_oracle_gap_by_stratum.csv
outputs/tables/phase5p5_repair5g551_iteration_safety_by_theta_family.csv
outputs/tables/phase5p5_repair5g551_iteration_hard_negative_cases.csv
outputs/tables/phase5p5_repair5g551_iteration_safe_useful_cases.csv
outputs/tables/phase5p5_repair5g551_iteration_feature_leakage_audit.csv
outputs/tables/phase5p5_repair5g551_iteration_distribution_shift_audit.csv
```

Raw results go to:

```text
outputs/logs/phase5p5_repair5g551_iteration_label_expansion/iteration_label_expansion_results.csv
outputs/logs/phase5p5_repair5g551_iteration_label_expansion/iteration_label_expansion_results.raw.csv
```

Required summary keys:

```json
{
  "new_iteration_counterfactual_solver_rows": "...",
  "counterfactual_contexts": "...",
  "finite_ratio_rows": "...",
  "safe_useful_contexts": "...",
  "safe_useful_context_rate": "...",
  "mean_best_oracle_delta_vs_static_flow": "...",
  "hard_negative_success_regression_rows": "...",
  "failure_reproduction_rows": "...",
  "targeted_failure_theta_reproduced": true,
  "runtime_feature_leakage_found": false,
  "oracle_gap_large_enough_for_policy_design": true,
  "decision": "..."
}
```

Hard gate to train checkpoint policies:

```text
new_iteration_counterfactual_solver_rows >= 64000
counterfactual_contexts >= 3200
finite_ratio_rows >= 50000
safe_useful_contexts >= 500
hard_negative_success_regression_rows >= 100
runtime_feature_leakage_found = false
oracle_gap_large_enough_for_policy_design = true
```

If hard negatives are fewer than 100, run targeted failure oversampling until at least 100 hard negatives exist or document that the G5.50 regressions could not be reproduced.

## 7. Stage D — Train checkpoint-level risk/utility/abstention policies

Create:

```text
scripts/train_eval_repair5g551_checkpoint_policies.py
```

Inputs:

```text
G5.51 iteration-counterfactual label expansion
G5.50 targeted failure cases
G5.50 active search regions
G5.49 true/safe regions
```

Write:

```text
outputs/reports/phase5p5_repair5g551_checkpoint_policy_training.md
outputs/reports/phase5p5_repair5g551_checkpoint_policy_summary.json
outputs/reports/phase5p5_repair5g551_policy_failure_modes.md
outputs/tables/phase5p5_repair5g551_policy_feature_manifest.csv
outputs/tables/phase5p5_repair5g551_policy_leakage_audit.csv
outputs/tables/phase5p5_repair5g551_policy_family_eval.csv
outputs/tables/phase5p5_repair5g551_policy_calibration_curves.csv
outputs/tables/phase5p5_repair5g551_policy_oof_predictions_sample.csv
outputs/tables/phase5p5_repair5g551_policy_threshold_sweep.csv
outputs/tables/phase5p5_repair5g551_policy_ablation.csv
outputs/tables/phase5p5_repair5g551_generated_theta_candidates.csv
artifacts/models/laur_ltm/repair5g551_model_manifest.json
```

### D.1 Runtime-available feature rule

Allowed feature groups:

```text
map_family
agents
nominal_budget_ms
horizon metadata
pre-update checkpoint traffic snapshot
trace event counts
committed/blocked/wait counts
goal-progress trace features
C-channel summary
F-channel summary
rank/audit aggregate features available before applying candidate theta
candidate theta values
distance-to-safe-region prototype computed from theta only
```

Forbidden feature groups:

```text
selected_ratio
baseline_ratio
success/failure outcome
oracle label
quality_delta
both_success
future traffic_after
post-update solver result
candidate rank after outcome
any direct label column
seed ID as a memorized categorical feature
```

Write an explicit leakage audit. If leakage is found, decision must be:

```text
g551_policy_training_blocked_feature_leakage
```

### D.2 Policy families to train/evaluate

At minimum evaluate:

```text
1. checkpoint_risk_classifier + utility_ranker + abstention
2. conformal_safe_expert_mixture_with_abstention
3. bounded_residual_over_static_flow_with_shrinkage
4. pairwise_safe_utility_ranker
5. prototype/kNN support policy with distance-to-support abstention
6. map-agent calibrated threshold policy
7. ensemble disagreement abstention policy
8. static-only selector-like invalid control
9. shuffled-label negative control
10. random-feature negative control
11. random-theta negative control
```

The method promoted to targeted replay must output bounded theta or abstain:

```text
ALLOW_THETA(theta)
ABSTAIN_TO_STATIC_FLOW
```

### D.3 Validation splits

Use all of:

```text
leave-seed-block-out
leave-map-agent-stratum-out
G5.50-targeted-failure holdout
G5.49/G5.50 active-region holdout
time/horizon holdout where feasible
```

Do not accept a policy that only passes random row split.

### D.4 Offline gate

A policy may enter fresh targeted replay only if:

```text
risk_false_safe_count_on_all_hard_negative_holdouts = 0
success_regression_rate_predicted_safe = 0
upper_confidence_bound_success_regression_rate <= 0.005
predicted_safe_utility_mean_delta_vs_static_flow < -0.002
generated_non_static_theta_usage_rate >= 0.02
generated_non_static_theta_usage_rate <= 0.25
negative_controls_do_not_pass = true
candidate_recognized_all = true
fulltheta_fingerprint_match_rate = 1
feature_leakage_found = false
```

If the only passing policy has `generated_non_static_theta_usage_rate < 0.02`, label it:

```text
safe_but_trivial_abstention
```

and do not treat it as learned UpdateLTM progress.

## 8. Stage E — Fresh generated-theta targeted replay

Only run targeted replay if Stage D passes.

Create:

```text
scripts/create_repair5g551_generated_theta_targeted_plan.py
scripts/run_repair5g551_generated_theta_targeted.py
scripts/analyze_repair5g551_generated_theta_targeted.py
```

Write:

```text
outputs/reports/phase5p5_repair5g551_generated_theta_targeted_plan.md
outputs/reports/phase5p5_repair5g551_generated_theta_targeted_summary.json
outputs/reports/phase5p5_repair5g551_generated_theta_targeted.md
outputs/tables/phase5p5_repair5g551_generated_theta_targeted_results_sample.csv
outputs/tables/phase5p5_repair5g551_generated_theta_targeted_vs_static_flow.csv
outputs/tables/phase5p5_repair5g551_generated_theta_targeted_vs_additive.csv
outputs/tables/phase5p5_repair5g551_generated_theta_targeted_vs_family_static.csv
outputs/tables/phase5p5_repair5g551_generated_theta_targeted_failure_cases.csv
outputs/tables/phase5p5_repair5g551_generated_theta_targeted_by_stratum.csv
outputs/tables/phase5p5_repair5g551_generated_theta_targeted_policy_usage.csv
```

Raw plan/results go to:

```text
outputs/logs/phase5p5_repair5g551_generated_theta_targeted/
```

### E.1 Targeted replay strata

Use fresh seeds disjoint from G5.49/G5.50 where practical. Do not use IDs 166..205.

Include:

```text
Core replication:
  random, 100, 2000
  horizons: short2000, short5000

Known transfer/failure:
  random, 50, 2000
  include seed blocks analogous to G5.50 targeted failures

Maze transfer:
  maze, 50, 2000
  maze, 100, 2000

Hard diagnostic:
  warehouse, 50/100, 500/1000/2000 with long horizon
  diagnostic only; does not block development-only targeted claim

Budget stress:
  random/maze, 500/1000 nominal budgets where finite ratios exist
```

### E.2 Targeted replay size

Hard minimum:

```text
new_targeted_solver_rows >= 60000
generated_theta_rows >= 48000
baseline_rows >= 10000
both_success_quality_pairs_vs_static_flow >= 15000
fresh_contexts >= 1200
generated_non_static_theta_usage_rate >= 0.02
```

Preferred:

```text
new_targeted_solver_rows >= 100000
fresh_contexts >= 2000
```

### E.3 Targeted replay gate

Targeted passes only if:

```text
success_regression_count_vs_static_flow = 0
success_regression_count_vs_additive = 0
candidate_recognized_all = true
fulltheta_fingerprint_match_rate = 1
quality_only_mean_delta_vs_static_flow < 0
better_count_vs_static_flow > worse_count_vs_static_flow
generated_non_static_theta_usage_rate >= 0.02
not_static_selector_action = true
all claim flags closed
```

If success regressions are >0 but much lower than G5.50, write a detailed regression reduction report and keep blind closed:

```text
g551_targeted_regression_reduced_but_not_zero_continue_safety_training
```

If targeted passes with zero regressions but low utility, label:

```text
g551_targeted_safe_low_utility_continue_policy_design
```

If targeted passes with zero regressions and nontrivial utility, continue to blind:

```text
g551_targeted_passed_continue_blind_replay
```

## 9. Stage F — Blind replay only if targeted passes

Only if Stage E passes.

Create:

```text
scripts/create_repair5g551_blind_replay_if_warranted.py
scripts/run_repair5g551_blind_replay_if_warranted.py
scripts/analyze_repair5g551_blind_replay_if_warranted.py
```

Write:

```text
outputs/reports/phase5p5_repair5g551_blind_replay_plan.md
outputs/reports/phase5p5_repair5g551_blind_replay_summary.json
outputs/reports/phase5p5_repair5g551_blind_replay.md
outputs/tables/phase5p5_repair5g551_blind_results_sample.csv
outputs/tables/phase5p5_repair5g551_blind_vs_static_flow.csv
outputs/tables/phase5p5_repair5g551_blind_vs_additive.csv
outputs/tables/phase5p5_repair5g551_blind_vs_family_static.csv
outputs/tables/phase5p5_repair5g551_blind_failure_cases.csv
outputs/tables/phase5p5_repair5g551_blind_by_stratum.csv
```

Blind replay hard minimum:

```text
new_blind_solver_rows >= 60000
fresh_contexts >= 1200
both_success_quality_pairs_vs_static_flow >= 15000
```

Blind gate:

```text
success_regression_count_vs_static_flow = 0
success_regression_count_vs_additive = 0
quality_only_mean_delta_vs_static_flow < 0
better_count_vs_static_flow > worse_count_vs_static_flow
generated_non_static_theta_usage_rate >= 0.02
candidate_recognized_all = true
fulltheta_fingerprint_match_rate = 1
```

Even if blind passes, keep:

```text
phase5p5_allowed=false
phase6_allowed=false
runtime_claim_allowed=false
learned_runtime_policy_validated=false
aaai_ready=false
```

A later runtime-integration preflight is required before those can open.

## 10. Stage G — Decision

Create:

```text
scripts/write_repair5g551_decision.py
```

Write:

```text
outputs/reports/phase5p5_repair5g551_decision.md
outputs/reports/phase5p5_repair5g551_decision_summary.json
outputs/tables/phase5p5_repair5g551_gate_matrix.csv
outputs/tables/phase5p5_repair5g551_claim_ledger.csv
outputs/tables/phase5p5_repair5g551_large_artifact_manifest.csv
```

Decision labels:

```text
g551_iteration_label_underpowered_continue
g551_policy_training_blocked_feature_leakage
g551_no_offline_policy_passed_continue_label_design
g551_targeted_regression_persists_continue_safety_training
g551_targeted_regression_reduced_but_not_zero_continue_safety_training
g551_targeted_safe_low_utility_continue_policy_design
g551_targeted_passed_continue_blind_replay
g551_blind_replay_failed_continue_policy_design
g551_blind_safe_gain_candidate_continue_runtime_preflight
```

Required final answers:

```json
{
  "did_g551_use_iteration_counterfactual_labels": true,
  "did_g551_reproduce_g550_targeted_regressions_as hard negatives": "...",
  "did_any_checkpoint_policy_pass_offline": "...",
  "did_targeted_replay_run": "...",
  "targeted_success_regression_count_vs_static_flow": "...",
  "targeted_quality_delta_vs_static_flow": "...",
  "did_blind_replay_run": "...",
  "blind_success_regression_count_vs_static_flow": "...",
  "generated_non_static_theta_usage_rate": "...",
  "primary_baseline": "static_flow_shield",
  "warehouse_non_evaluable_or_recovered": "...",
  "next_step": "..."
}
```

## 11. Validation commands

Run:

```bash
python -m py_compile \
  scripts/repair5g551_common.py \
  scripts/verify_repair5g551_g550_artifacts.py \
  scripts/analyze_repair5g551_g550_failure_autopsy.py \
  scripts/create_repair5g551_iteration_label_expansion_plan.py \
  scripts/run_repair5g551_iteration_label_expansion.py \
  scripts/analyze_repair5g551_iteration_label_expansion.py \
  scripts/train_eval_repair5g551_checkpoint_policies.py \
  scripts/create_repair5g551_generated_theta_targeted_plan.py \
  scripts/run_repair5g551_generated_theta_targeted.py \
  scripts/analyze_repair5g551_generated_theta_targeted.py \
  scripts/create_repair5g551_blind_replay_if_warranted.py \
  scripts/run_repair5g551_blind_replay_if_warranted.py \
  scripts/analyze_repair5g551_blind_replay_if_warranted.py \
  scripts/write_repair5g551_decision.py

git diff --check

python -m pytest tests -q
```

If global pytest still has pre-existing unrelated missing-artifact failures, record:

```text
pre_existing_unrelated_test_failures
```

and also run focused tests for G5.51 scripts and any modified helper modules.

## 12. Required execution sequence

Use this sequence unless an exact blocker occurs:

```bash
python scripts/verify_repair5g551_g550_artifacts.py
python scripts/analyze_repair5g551_g550_failure_autopsy.py

python scripts/create_repair5g551_iteration_label_expansion_plan.py
python scripts/run_repair5g551_iteration_label_expansion.py --row-limit 64000 --max-workers 16
python scripts/analyze_repair5g551_iteration_label_expansion.py

python scripts/train_eval_repair5g551_checkpoint_policies.py

python scripts/create_repair5g551_generated_theta_targeted_plan.py
python scripts/run_repair5g551_generated_theta_targeted.py --row-limit 60000 --max-workers 20
python scripts/analyze_repair5g551_generated_theta_targeted.py

python scripts/create_repair5g551_blind_replay_if_warranted.py
python scripts/run_repair5g551_blind_replay_if_warranted.py --row-limit 60000 --max-workers 20
python scripts/analyze_repair5g551_blind_replay_if_warranted.py

python scripts/write_repair5g551_decision.py
```

If the 64k iteration-label minimum finishes quickly, continue to the preferred label target before training:

```bash
python scripts/run_repair5g551_iteration_label_expansion.py --row-limit 128000 --max-workers 16
python scripts/analyze_repair5g551_iteration_label_expansion.py
```

If targeted passes and blind starts, use fresh seeds not used in targeted.

## 13. What G5.51 must not do

Do not:

```text
- declare G5.50 a learned policy success;
- rerun only region-level fulltheta replay and stop;
- train from final full-run hindsight labels only;
- use solver outcomes as runtime features;
- lower SafeGate to allow success regressions;
- count quality-only gain when selected fails and static_flow succeeds;
- count static_flow fallback as non-static learned usage;
- let warehouse diagnostics block all core development;
- commit huge raw CSVs;
- open runtime/Phase5.5/Phase6/AAAI claims.
```

## 14. Desired scientific outcome

The best possible G5.51 outcome is:

```text
Iteration-level labels repair safety prediction.
A checkpoint-level learned UpdateParams policy abstains often but uses bounded
non-static theta in supported contexts.
Fresh targeted replay has zero success regressions vs static_flow_shield and
nontrivial quality gain.
Blind replay is either reached or correctly kept closed by strict gate.
```

A still-useful negative outcome is:

```text
Even with iteration-level labels, fresh targeted replay has success regressions.
Then the project learns that the current feature set, label horizon, or policy
family cannot safely generalize, and G5.52 should focus on richer checkpoint
features or stricter causal labels before any generator work continues.
```

This round should produce enough evidence to distinguish:

```text
A. label granularity was the main blocker;
B. runtime features are insufficient;
C. policy family is still too weak;
D. SafeGate is correctly conservative;
E. true signal is too narrow for learned deployment;
F. a safe but low-coverage learned UpdateParams policy is viable.
```
