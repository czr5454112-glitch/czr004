# Repair5G.5.49 Plan — Calibration Completion + StaticFlow-Primary FullTheta Neural UpdateParams Replay

Project: `czr004`  
Branch: `codex/g531-slice-pilot`  
Starting point: G5.48 commit `cda1a9d`  
Round name: `Repair5G.5.49 calibration-completion staticflow-primary fulltheta replay`

## 0. Why G5.49 exists

G5.48 was a useful infrastructure/calibration result, not a learned-UpdateLTM success. It changed the project state in three important ways:

1. Full-theta materialization is now usable:
   - `candidate_recognized_all = true`
   - `fulltheta_fingerprint_match_rate = 1`
   - default-disabled path and force-additive parity remained safe.

2. Real budget/horizon calibration was finally run:
   - `budget_calibration_solver_rows = 3654`
   - `calibration_contexts = 522`
   - `finite_ratio_rows = 1604`
   - `finite_ratio_rate_overall = 0.438970990695`
   - `both_success_quality_pairs_vs_static_flow = 283`

3. The calibration gate did not fully pass:
   - finite rows target was `>= 3000`
   - actual finite rows were `1604`
   - fulltheta replay / generator / targeted / blind were correctly skipped.

Therefore G5.49 must not reinterpret G5.48 as an algorithmic negative. G5.49 must complete the evaluability stage and then run the first real fulltheta replay on calibrated horizons.

Important project clarification:

```text
Primary baseline = hand-designed static_flow_shield.
additive_ltm = paper-faithful floor / parity floor.
frozen_family_static_goal_aware and best_fixed_static_goal_aware = strong diagnostic baselines only.
The learned method must output bounded continuous UpdateParams theta, not static baseline IDs.
```

The main question for G5.49:

```text
On horizons where static_flow_shield produces finite paired quality outcomes,
can fulltheta / neural continuous UpdateParams produce safe solver-level improvement
over static_flow_shield?
```

## 1. Non-negotiable guardrails

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

Do not train or present a static baseline selector as the method.

Do not count a static-only improvement as learned UpdateLTM progress.

## 2. Required worklog entry

Append to `docs/codex-worklog.md` before code:

```markdown
## 2026-06-14 - Repair5G.5.49 calibration-completion staticflow-primary fulltheta replay

- Request:
  Continue after G5.48 commit cda1a9d. G5.48 passed fulltheta materialization and ran real budget calibration, but ended underpowered: finite_ratio_rows=1604 below the >=3000 gate, both_success_quality_pairs_vs_static_flow=283, and fulltheta replay/generator/targeted/blind were skipped. G5.49 must finish evaluability calibration and then run static_flow-primary fulltheta replay on calibrated horizons.
- Primary baseline:
  static_flow_shield is the primary learned-theta baseline because it is the manually designed static-flow method previously shown stronger than paper-faithful additive LTM. additive_ltm is a parity floor. family_static/best_fixed are diagnostics.
- Planned work:
  verify G5.48, audit calibration semantics, deduplicate evaluable strata/horizon rows, top up calibration to at least 3000 finite rows, run fulltheta replay on calibrated horizons, analyze true safe-gain vs static_flow, train generator only if replay has usable signal, and run targeted/blind only by gate.
- Constraints:
  No external/lacam2/lacam2 edits, no solver semantic changes, no static selector method, no IDs 166..205, no Phase5.5/Phase6/runtime/AAAI claims.
```

## 3. Stage A — Verify and audit G5.48

Create / update:

```text
scripts/verify_repair5g549_g548_artifacts.py
scripts/audit_repair5g549_g548_calibration_semantics.py
```

Expected outputs:

```text
outputs/reports/phase5p5_repair5g549_g548_verification.md
outputs/reports/phase5p5_repair5g549_g548_verification_summary.json
outputs/reports/phase5p5_repair5g549_g548_calibration_semantics.md
outputs/reports/phase5p5_repair5g549_g548_calibration_semantics_summary.json
outputs/tables/phase5p5_repair5g549_g548_artifact_audit.csv
outputs/tables/phase5p5_repair5g549_g548_selected_horizon_audit.csv
outputs/tables/phase5p5_repair5g549_g548_unique_evaluable_strata.csv
outputs/tables/phase5p5_repair5g549_g548_non_evaluable_strata_audit.csv
```

Required checks:

1. Verify G5.48 decision:
   - `decision = g548_budget_calibration_underpowered_continue_calibration`
   - `fulltheta_fingerprint_match_rate = 1`
   - `budget_calibration_solver_rows >= 3000`
   - `finite_ratio_rows = 1604`
   - `both_success_quality_pairs_vs_static_flow = 283`

2. Audit whether `calibrated_evaluable_strata` counts:
   - unique `(map_family, agents, nominal_budget_ms)` strata, or
   - selected horizon rows.

3. Report both metrics separately:
   - `selected_evaluable_horizon_rows`
   - `unique_evaluable_stratum_count`

4. Identify coverage concentration:
   - which map families are evaluable;
   - which agent counts are evaluable;
   - which nominal budgets are evaluable;
   - whether warehouse remains entirely non-evaluable.

5. Do not let an overcounted horizon-row metric pass a unique-stratum gate silently.

## 4. Stage B — Calibration top-up plan

Create:

```text
scripts/create_repair5g549_calibration_topup_plan.py
```

Expected outputs:

```text
outputs/reports/phase5p5_repair5g549_calibration_topup_plan.md
outputs/reports/phase5p5_repair5g549_calibration_topup_plan_summary.json
outputs/tables/phase5p5_repair5g549_calibration_topup_plan.csv
outputs/tables/phase5p5_repair5g549_calibration_topup_policy_breakdown.csv
```

The top-up plan has two routes.

### Route B1 — Core evaluable top-up

Focus first on horizons already shown evaluable in G5.48:

```text
maze/random, agents 50/100, nominal_budget_ms 2000
short_budget_ms in {1000, 2000, 5000}
base_time_limit_sec = 0.5 initially, escalate to 1.0 if needed
ltm_max_iterations = 2 initially, then 4 if supported
```

Goal:

```text
finite_ratio_rows_total >= 3000
both_success_quality_pairs_vs_static_flow >= 1000
baseline_static_flow_rows >= 1000
```

### Route B2 — Hard-stratum recovery

Try to recover non-evaluable strata, especially warehouse and 500/1000ms budgets:

```text
warehouse, agents 50/100, nominal_budget_ms 500/1000/2000
maze/random 500/1000ms under-evaluable strata
short_budget_ms in {2000, 5000, 10000}
base_time_limit_sec in {1.0, 2.0, 5.0, 10.0}
ltm_max_iterations in {2, 4, 8}
```

This route is diagnostic. If warehouse remains non-evaluable after real runs, do not block all development replay forever. Instead report:

```text
warehouse_non_evaluable_on_local_budget
```

and continue development on calibrated core strata, with no final broad claim.

Minimum top-up plan:

```text
planned_solver_rows >= 8000
planned_contexts >= 720
planned_static_flow_rows >= 720
planned_fulltheta_smoke_rows >= 2500
```

Preferred top-up plan:

```text
planned_solver_rows >= 16000
planned_contexts >= 1200
```

## 5. Stage C — Run real calibration top-up

Create:

```text
scripts/run_repair5g549_calibration_topup.py
scripts/analyze_repair5g549_calibration_topup.py
```

Expected outputs:

```text
outputs/tables/phase5p5_repair5g549_calibration_topup_results.csv
outputs/tables/phase5p5_repair5g549_calibration_topup_results.raw.csv
outputs/tables/phase5p5_repair5g549_calibration_selected_horizons_v2.csv
outputs/tables/phase5p5_repair5g549_calibration_non_evaluable_strata_v2.csv
outputs/tables/phase5p5_repair5g549_calibration_by_map_family.csv
outputs/tables/phase5p5_repair5g549_calibration_by_budget.csv
outputs/reports/phase5p5_repair5g549_calibration_topup.md
outputs/reports/phase5p5_repair5g549_calibration_topup_summary.json
```

Hard minimum to proceed to fulltheta replay:

```text
new_calibration_solver_rows >= 8000
cumulative_finite_ratio_rows >= 3000
cumulative_finite_ratio_rate >= 0.20
cumulative_both_success_quality_pairs_vs_static_flow >= 1000
candidate_recognized_all = true
fulltheta_fingerprint_match_rate = 1
unique_evaluable_stratum_count >= 4
```

Development acceptable route:

If `unique_evaluable_stratum_count < 9` but all other gates pass, G5.49 may run fulltheta replay only on the calibrated subset and must label the result:

```text
calibrated_core_subset_development_only
```

No Phase5.5, runtime, or broad paper claim is allowed.

If `new_calibration_solver_rows < 8000`, decision must be:

```text
g549_calibration_topup_underpowered_continue
```

not algorithmic failure.

## 6. Stage D — StaticFlow-primary fulltheta replay plan

Create:

```text
scripts/create_repair5g549_fulltheta_replay_plan.py
```

Expected outputs:

```text
outputs/tables/phase5p5_repair5g549_fulltheta_replay_plan.csv
outputs/tables/phase5p5_repair5g549_fulltheta_replay_policy_breakdown.csv
outputs/reports/phase5p5_repair5g549_fulltheta_replay_plan.md
outputs/reports/phase5p5_repair5g549_fulltheta_replay_plan_summary.json
```

Use only selected evaluable horizons from Stage C.

Candidate groups must include:

```text
1. static_flow local perturbation fulltheta
2. lambda_flow / lambda_cong sweeps
3. alpha_flow_wait_progress sweeps
4. min/max edge cost clamp sweeps
5. goal_projection_mode ablations
6. alpha_cong_commit_nonprogress sweeps
7. G5.43 true/near signal neighborhoods
8. G5.46/G5.48 safe-but-no-gain neighborhoods
9. surrogate-guided theta if model exists
10. negative controls
```

At least 40% of theta rows must vary full-only fields not faithfully executed in G5.46:

```text
theta_lambda_flow
theta_lambda_cong
theta_alpha_flow_wait_progress
theta_min_edge_cost
theta_max_edge_cost
theta_goal_projection_mode_*
theta_alpha_cong_commit_nonprogress
```

Minimum fulltheta replay plan:

```text
planned_solver_rows >= 30000
planned_fulltheta_candidate_rows >= 24000
planned_baseline_rows >= 4000
planned_contexts >= 720
distinct_fulltheta_rows >= 2000
```

Preferred local PC plan:

```text
planned_solver_rows >= 60000
planned_fulltheta_candidate_rows >= 48000
planned_contexts >= 1080
distinct_fulltheta_rows >= 4000
```

## 7. Stage E — Run staticFlow-primary fulltheta replay

Create:

```text
scripts/run_repair5g549_fulltheta_replay.py
scripts/analyze_repair5g549_fulltheta_replay.py
```

Expected outputs:

```text
outputs/tables/phase5p5_repair5g549_fulltheta_replay_results.csv
outputs/tables/phase5p5_repair5g549_fulltheta_replay_results.raw.csv
outputs/tables/phase5p5_repair5g549_fulltheta_selected_vs_static_flow.csv
outputs/tables/phase5p5_repair5g549_fulltheta_selected_vs_additive.csv
outputs/tables/phase5p5_repair5g549_fulltheta_selected_vs_family_static.csv
outputs/tables/phase5p5_repair5g549_fulltheta_true_safe_gain_regions.csv
outputs/tables/phase5p5_repair5g549_fulltheta_safe_but_no_gain_regions.csv
outputs/tables/phase5p5_repair5g549_fulltheta_unsafe_but_useful_regions.csv
outputs/tables/phase5p5_repair5g549_fulltheta_non_evaluable_regions.csv
outputs/tables/phase5p5_repair5g549_fulltheta_parameter_sensitivity.csv
outputs/tables/phase5p5_repair5g549_fulltheta_failure_cases.csv
outputs/reports/phase5p5_repair5g549_fulltheta_replay.md
outputs/reports/phase5p5_repair5g549_fulltheta_replay_summary.json
```

Primary comparison:

```text
fulltheta candidate vs static_flow_shield
```

Other comparisons:

```text
vs additive_ltm = parity/floor diagnostic
vs family_static = strong diagnostic only
vs best_fixed = optional diagnostic
```

### Region classification

For each `(candidate/theta-cluster, map_family, agents, nominal_budget, horizon)`:

```text
true_safe_gain:
  support_pairs >= 80
  seed_block_support >= 3
  vs_static_flow_success_regression_count = 0
  vs_static_flow_quality_only_mean_delta < 0
  better_count_vs_static_flow > worse_count_vs_static_flow

safe_but_no_gain:
  support_pairs >= 80
  vs_static_flow_success_regression_count = 0
  no meaningful quality gain

unsafe_useful:
  quality signal exists but success regression > 0
  allowed only as risk-label data, not deployable

non_evaluable:
  insufficient finite paired quality outcomes
```

Development near-miss profile:

```text
support_pairs >= 120
vs_static_flow_success_regression_rate <= 0.005
quality_only_mean_delta < 0
better > worse
```

Near-miss can continue to refinement but cannot be frozen.

Hard minimum for G5.49 to be considered completed beyond calibration:

```text
new_fulltheta_solver_rows >= 30000
finite_ratio_rows >= 3000
both_success_quality_pairs_vs_static_flow >= 2000
fulltheta_fingerprint_match_rate = 1
candidate_recognized_all = true
```

## 8. Stage F — Risk/utility/generator after real fulltheta replay

Only if Stage E has enough finite paired outcomes.

Create:

```text
scripts/train_eval_repair5g549_risk_utility_generator.py
```

Expected outputs:

```text
outputs/tables/phase5p5_repair5g549_risk_model_eval.csv
outputs/tables/phase5p5_repair5g549_utility_model_eval.csv
outputs/tables/phase5p5_repair5g549_generator_eval.csv
outputs/tables/phase5p5_repair5g549_generated_theta_candidates.csv
outputs/reports/phase5p5_repair5g549_risk_utility_generator.md
outputs/reports/phase5p5_repair5g549_risk_utility_generator_summary.json
artifacts/models/laur_ltm/repair5g549_* only if warranted
```

Feature rules:

Allowed runtime-facing features:

```text
map_family
agents
nominal_budget
selected horizon id
topology proxies
fixed static_flow trace aggregates, if available before theta choice
```

Forbidden runtime-facing features:

```text
candidate outcome
oracle label
winner label
post-candidate expanded_nodes
post-candidate low_level_pibt_calls
quality_delta
success_regression label
seed as feature
candidate_id as feature
```

Models to compare:

```text
risk_model(context, theta) -> regression risk
utility_model(context, theta) -> quality delta
generator(context, z) -> K bounded fulltheta proposals
surrogate-guided CEM / BO theta proposal
risk-only abstaining generator
negative-control generator
```

Offline development gate:

```text
risk_false_safe_count_on_validation = 0
risk_gate_pass_rate between 0.01 and 0.50
predicted_safe_utility_candidates > 0
generated_non_static_theta_usage_rate > 0.05
```

## 9. Stage G — Targeted generated-theta replay

Only if Stage F passes.

Create:

```text
scripts/run_repair5g549_generated_theta_targeted.py
scripts/analyze_repair5g549_generated_theta_targeted.py
```

Expected outputs:

```text
outputs/tables/phase5p5_repair5g549_generated_theta_targeted_results.csv
outputs/tables/phase5p5_repair5g549_generated_theta_targeted_vs_static_flow.csv
outputs/tables/phase5p5_repair5g549_generated_theta_targeted_vs_additive.csv
outputs/tables/phase5p5_repair5g549_generated_theta_targeted_vs_family_static.csv
outputs/tables/phase5p5_repair5g549_generated_theta_targeted_failure_cases.csv
outputs/reports/phase5p5_repair5g549_generated_theta_targeted.md
outputs/reports/phase5p5_repair5g549_generated_theta_targeted_summary.json
```

Minimum targeted replay:

```text
targeted_solver_rows >= 7200
targeted_pairs_vs_static_flow >= 1000
generated_theta_usage_rate >= 0.05
vs_static_flow_success_regression_count = 0 for strict freeze
quality_only_mean_delta_vs_static_flow < 0
better_count_vs_static_flow > worse_count_vs_static_flow
```

If there are low-rate regressions but strong quality signal, report development-only near-miss; do not freeze.

## 10. Stage H — Blind replay only by gate

Blind replay is optional and only warranted if targeted strict gate passes.

Expected outputs:

```text
outputs/tables/phase5p5_repair5g549_blind_results.csv
outputs/tables/phase5p5_repair5g549_blind_selected_vs_static_flow.csv
outputs/tables/phase5p5_repair5g549_blind_selected_vs_additive.csv
outputs/tables/phase5p5_repair5g549_blind_selected_vs_family_static.csv
outputs/tables/phase5p5_repair5g549_blind_failure_cases.csv
outputs/reports/phase5p5_repair5g549_blind_evidence.md
outputs/reports/phase5p5_repair5g549_blind_evidence_summary.json
```

Minimum blind replay:

```text
blind_solver_rows >= 14400
blind_pairs_vs_static_flow >= 2000
success_regression_vs_static_flow = 0
quality_only_mean_delta_vs_static_flow < 0
better > worse
```

Even if blind passes, keep `phase5p5_allowed=false` unless explicitly instructed otherwise in a later round.

## 11. Final decision writer

Create:

```text
scripts/write_repair5g549_decision.py
```

Expected outputs:

```text
outputs/reports/phase5p5_repair5g549_decision.md
outputs/reports/phase5p5_repair5g549_decision_summary.json
```

Possible decisions:

```text
g549_calibration_topup_underpowered_continue
g549_calibration_evaluable_core_ready_fulltheta_replay_underpowered
g549_fulltheta_replay_no_primary_staticflow_signal_continue_design
g549_fulltheta_true_safe_gain_regions_found_continue_generator
g549_generator_offline_gate_failed_continue_model_design
g549_generated_theta_targeted_positive_continue_blind
g549_blind_positive_primary_staticflow_continue_validation
g549_fulltheta_primary_signal_with_strong_static_gap_continue_diagnostics
```

The decision summary must answer:

```text
- Did G5.49 reach >=3000 cumulative finite ratio rows?
- How many unique evaluable strata exist?
- Which strata remain non-evaluable, especially warehouse?
- Did fulltheta replay run?
- Did any fulltheta theta cluster beat static_flow safely?
- Were gains over additive only, or also over static_flow?
- Did family_static disagreement explain any gap?
- Did generator beat random/local static_flow perturbations?
- Is next step more calibration, fulltheta refinement, generator training, targeted replay, or server-scale replay?
```

## 12. Validation

Run:

```text
python -m py_compile scripts/repair5g549_common.py scripts/verify_repair5g549_g548_artifacts.py scripts/audit_repair5g549_g548_calibration_semantics.py scripts/create_repair5g549_calibration_topup_plan.py scripts/run_repair5g549_calibration_topup.py scripts/analyze_repair5g549_calibration_topup.py scripts/create_repair5g549_fulltheta_replay_plan.py scripts/run_repair5g549_fulltheta_replay.py scripts/analyze_repair5g549_fulltheta_replay.py scripts/train_eval_repair5g549_risk_utility_generator.py scripts/run_repair5g549_generated_theta_targeted.py scripts/analyze_repair5g549_generated_theta_targeted.py scripts/write_repair5g549_decision.py
```

Run the G5.49 pipeline scripts in order.

Run JSON parse sanity for all G5.49 summaries.

Run `git diff --check`.

Confirm:

```text
git status --short -- external/lacam2/lacam2
```

is clean.

Run focused pytest where practical. If full pytest fails due to pre-existing missing artifacts, record exactly which tests fail and why, and do not claim they are G5.49 failures unless caused by this round.

## 13. Stop rules

Stop early only if one of these occurs:

```text
1. Fulltheta materialization regresses:
   candidate_recognized_all=false or fulltheta_fingerprint_match_rate<1.

2. Calibration top-up cannot execute real solver rows:
   record exact failing command and blocker.

3. Calibration top-up remains underpowered:
   new_calibration_solver_rows < 8000.

4. Cumulative finite rows remain below 3000 after top-up:
   report g549_calibration_topup_underpowered_continue.

5. Fulltheta replay has insufficient finite paired outcomes:
   report non-evaluable, not algorithmic no-signal.
```

Do not stop after merely writing plans or skip tables unless a stop rule applies.
