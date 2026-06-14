# G5.48 Prompt: Evaluable-Horizon FullTheta Neural UpdateParams Replay

Project: `czr004`
Branch: `codex/g531-slice-pilot`
Start commit: `2ae2386` (`eval/model: G5.47 full-theta + SafeGate v2`)
Round name: `Repair5G.5.48 evaluable-horizon fulltheta neural UpdateParams replay`

## 0. Why G5.48 exists

G5.47 is not a positive result, but it is also not a valid negative result for the neural continuous `UpdateParams` generator.

G5.47 established two important facts:

```text
1. Full-theta materialization now exists and passed smoke:
   candidate_recognized_all = true
   fulltheta_fingerprint_match_rate = 1.0
   default-disabled path preserves previous behavior
   force-additive parity remains unaffected

2. The experiment is still blocked by evaluability:
   finite_ratio_rate_overall = 0
   finite_ratio_rows = 0
   calibrated_evaluable_strata = 0
   active fulltheta replay / generator / targeted / blind were skipped
```

Therefore G5.48 must not repeat G5.46's mistake of running many rows in a non-evaluable horizon, and must not repeat G5.47's mistake of writing a declared calibration grid without actually running enough calibration horizons.

The next scientific bottleneck is:

```text
Find real solver horizons where static_flow_shield and fulltheta candidates
produce finite paired quality outcomes, then run fulltheta neural UpdateParams
search against static_flow_shield as the primary baseline.
```

The user's clarified baseline is:

```text
The primary baseline is the hand-designed static_flow_shield that was previously
shown stronger than paper-faithful additive LTM.
```

This means G5.48 should evaluate learned fulltheta `UpdateParams` primarily against:

```text
static_flow_shield
```

not against a selector over static baselines. `additive_ltm` remains the paper/parity floor. `frozen_family_static_goal_aware` and `best_fixed_static_goal_aware` remain strong diagnostics only unless G5.48 explicitly claims dominance over them. Do not count static baseline selection as learned UpdateLTM progress.

## 1. Hard interpretation of G5.47

Before coding, write a worklog entry saying:

```text
G5.47 fixed materialization but did not run an evaluable fulltheta experiment.
The next round is not "try more neural models"; it is "make the replay horizon evaluable".
A positive or negative claim about neural continuous UpdateParams requires
finite paired quality outcomes versus static_flow_shield.
```

Also append a short strategy note to:

```text
deep-research-report.md
docs/goal_aware_dual_channel_ltm_research_strategy.md
phase4_6_laur_ltm_codex_execution_plan.md
```

Required strategic statement:

```text
From G5.48 onward, static_flow_shield is the primary fixed baseline for neural
continuous UpdateParams. The gate asks whether learned/fulltheta UpdateLTM can
safely improve over this hand-designed static-flow LTM variant. Additive LTM is
a paper-faithful floor. Strong family/static variants are diagnostic baselines,
not the primary target and not selector actions.
```

## 2. Non-negotiable guardrails

Do not modify:

```text
external/lacam2/lacam2/**
PIBT conflict semantics
candidate domain
agent actions
agent priorities
h-values
candidate deletion
LaCAM* high-level search
OPEN / EXPLORED / rewrite / incumbent pruning
restart semantics
```

Keep closed:

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

A learned method must output:

```text
bounded continuous UpdateParams theta
```

or:

```text
ALLOW_THETA / ABSTAIN_TO_STATIC_FLOW
```

It must not output:

```text
additive_ltm / static_flow_shield / best_fixed_static_goal_aware / frozen_family_static_goal_aware
```

as a learned action.

## 3. Required files

Create:

```text
czr004_g548_evaluable_horizon_fulltheta_neural_updateparams_replay_plan.md

scripts/repair5g548_common.py
scripts/verify_repair5g548_g547_artifacts.py
scripts/audit_repair5g548_g547_evaluability_blocker.py
scripts/create_repair5g548_real_budget_calibration_plan.py
scripts/run_repair5g548_real_budget_calibration.py
scripts/analyze_repair5g548_real_budget_calibration.py
scripts/create_repair5g548_staticflow_primary_fulltheta_probe_plan.py
scripts/run_repair5g548_staticflow_primary_fulltheta_probe.py
scripts/analyze_repair5g548_staticflow_primary_fulltheta_evidence.py
scripts/train_eval_repair5g548_risk_utility_generator_if_warranted.py
scripts/run_repair5g548_generated_theta_targeted_if_warranted.py
scripts/analyze_repair5g548_generated_theta_targeted_evidence.py
scripts/run_repair5g548_blind_if_warranted.py
scripts/analyze_repair5g548_blind_evidence.py
scripts/write_repair5g548_decision.py
```

Reports/tables:

```text
outputs/reports/phase5p5_repair5g548_*
outputs/tables/phase5p5_repair5g548_*
```

Raw logs may go under:

```text
outputs/logs/phase5p5_repair5g548_*
```

## 4. Stage A — Verify G5.47 and classify it correctly

Verify:

```text
outputs/reports/phase5p5_repair5g547_decision_summary.json
outputs/reports/phase5p5_repair5g547_fulltheta_materialization_smoke_summary.json
outputs/reports/phase5p5_repair5g547_budget_calibration_summary.json
outputs/reports/phase5p5_repair5g547_gate_reassessment_summary.json
outputs/reports/phase5p5_repair5g547_g546_probe_confounds_summary.json
outputs/tables/phase5p5_repair5g547_fulltheta_registry.csv
outputs/tables/phase5p5_repair5g547_fulltheta_materialization_smoke_results.csv
outputs/tables/phase5p5_repair5g547_baseline_role_policy.csv
cpp/tools/phase1a_batch.cpp
scripts/repair5g547_common.py
```

Write:

```text
outputs/reports/phase5p5_repair5g548_g547_verification.md
outputs/reports/phase5p5_repair5g548_g547_verification_summary.json
outputs/tables/phase5p5_repair5g548_g547_artifact_audit.csv
```

Required summary keys:

```json
{
  "g547_decision": "...",
  "fulltheta_materialization_passed": true,
  "fulltheta_fingerprint_match_rate": "1",
  "g547_finite_ratio_rows": 0,
  "g547_active_real_probe_executed": false,
  "g547_negative_is_not_algorithmic": true,
  "g548_must_run_real_budget_calibration": true
}
```

## 5. Stage B — Audit the G5.47 evaluability blocker

Create:

```text
outputs/reports/phase5p5_repair5g548_g547_evaluability_blocker.md
outputs/reports/phase5p5_repair5g548_g547_evaluability_blocker_summary.json
outputs/tables/phase5p5_repair5g548_g547_calibration_audit.csv
outputs/tables/phase5p5_repair5g548_g547_no_solution_context_audit.csv
outputs/tables/phase5p5_repair5g548_g547_budget_field_consistency_audit.csv
```

Answer explicitly:

```text
Did G5.47 actually run the calibration grid or only declare it?
How many calibration rows had solver_rows_materialized > 0?
How many had source = calibration_grid_declared_not_long_run_locally?
Were the G5.47 finite_ratio rows zero because horizons were too short, because rows were not run, or because parsing failed?
Do context_key, nominal_budget_ms, short_budget_ms, and actual counterfactual budget agree?
Did baseline static_flow solve at any calibration horizon?
Did additive/family_static solve at any calibration horizon?
```

If the audit finds that G5.47 calibration was only declared, then the decision must use:

```text
g547_budget_calibration_not_executed_continue_real_calibration
```

not:

```text
no_evaluable_quality_horizon_found
```

## 6. Stage C — Real budget/horizon calibration, not declared grid

This is the main required work. Do not skip it.

Build a real calibration plan over a small but representative panel first.

### C.1 Calibration strata

Use these primary strata:

```text
map_family: maze, random, warehouse
agents: 50, 100
nominal_budget_ms: 500, 1000, 2000
```

That is 18 target strata.

For each stratum, select at least:

```text
calibration_seed_count >= 6
```

Use fresh seeds outside the previous G5.39-G5.47 probe seed ranges where practical, but do not use IDs 166..205. If fresh seeds are not practical, document reuse. Each selected context must include baselines:

```text
additive_ltm
static_flow_shield
frozen_family_static_goal_aware
```

and at least 4 fulltheta smoke candidates that deliberately vary fields G5.46 could not test:

```text
lambda_flow
lambda_cong
alpha_flow_wait_progress
min_edge_cost
max_edge_cost
goal_projection_mode
alpha_cong_commit_nonprogress
```

### C.2 Calibration horizons

Run actual solver commands for a staged horizon grid:

```text
short_budget_ms:
  250, 500, 1000, 2000, 5000

base_time_limit_sec:
  0.50, 1.00, 2.00, 5.00, 10.00

ltm_max_iterations:
  2, 4, 8
```

If this is too heavy locally, use staged early stopping:

```text
Stage C0 smoke:
  18 strata x 2 seeds x selected cheap horizons

Stage C1 calibration:
  only horizons from C0 that showed any finite ratio

Stage C2 confirmation:
  18 strata x >=6 seeds on selected horizons
```

But the final G5.48 decision must clearly report the actual solver rows run. Do not write a declared grid with zero materialized solver rows.

### C.3 Calibration minimum

A real calibration attempt is complete only if:

```text
budget_calibration_solver_rows >= 3000
calibration_contexts >= 180
baseline_static_flow_rows >= 500
```

If these are not met, decision should be:

```text
g548_budget_calibration_underpowered_continue_calibration
```

not algorithmic failure.

### C.4 Evaluability success criteria

A stratum-horizon is evaluable if:

```text
static_flow_success_rate >= 0.20
finite_ratio_rate >= 0.20
both_success_quality_pairs_vs_static_flow >= 20
candidate_recognized_all = true
```

Overall calibration gate passes if:

```text
calibrated_evaluable_strata >= 9
quality_horizon_contexts >= 360
finite_ratio_rows >= 3000
finite_ratio_rate_overall >= 0.20
```

If no target 50/100-agent horizon is evaluable, add a diagnostic low-density panel:

```text
agents: 20, 30, 40
```

This diagnostic panel must not count as final primary evidence, but it tells us whether the issue is:

```text
horizon too short
density too hard
probe parser/ratio issue
fulltheta method issue
```

### C.5 Outputs

Write:

```text
outputs/tables/phase5p5_repair5g548_budget_calibration_plan.csv
outputs/tables/phase5p5_repair5g548_budget_calibration_results.csv
outputs/tables/phase5p5_repair5g548_budget_horizon_selection.csv
outputs/tables/phase5p5_repair5g548_calibration_by_stratum.csv
outputs/tables/phase5p5_repair5g548_non_evaluable_strata.csv
outputs/tables/phase5p5_repair5g548_low_density_diagnostic_if_needed.csv
outputs/reports/phase5p5_repair5g548_budget_calibration.md
outputs/reports/phase5p5_repair5g548_budget_calibration_summary.json
```

## 7. Stage D — Fulltheta replay against static_flow primary baseline

Only if Stage C passes evaluability.

Build the real fulltheta replay plan using selected horizons from Stage C.

Primary baseline:

```text
static_flow_shield
```

Required paired diagnostics where available:

```text
additive_ltm
frozen_family_static_goal_aware
```

But promotion and true signal should be judged first against:

```text
static_flow_shield
```

Do not require family_static dominance for exploration. If theta improves over static_flow but loses to family_static, label:

```text
primary_staticflow_signal_with_strong_static_gap
```

not automatic failure.

### D.1 Candidate families

Use fulltheta candidates that truly vary all fields, not old grid aliases:

```text
broad_fulltheta_sobol
local_staticflow_fulltheta_perturb
lambda_flow_sweep
alpha_flow_wait_progress_sweep
cost_clamp_sweep
goal_projection_ablation
g543_signal_near_fulltheta
g546_near_boundary_repaired
surrogate_guided_cem
negative_controls
```

At least 40% of generated candidates must vary fields that G5.46 did not faithfully execute:

```text
lambda_flow
lambda_cong
alpha_flow_wait_progress
min_edge_cost
max_edge_cost
goal_projection_mode
alpha_cong_commit_nonprogress
```

### D.2 Minimum replay

Minimum:

```text
new_fulltheta_solver_rows >= 40000
fulltheta_candidate_rows >= 30000
baseline_rows >= 5000
contexts >= 1080
distinct_fulltheta_rows >= 3000
finite_ratio_rows >= 3000
both_success_quality_pairs_vs_static_flow >= 2000
candidate_recognized_all = true
fulltheta_fingerprint_match_rate = 1.0
```

Preferred local-PC profile:

```text
new_fulltheta_solver_rows >= 80000
finite_ratio_rows >= 8000
both_success_quality_pairs_vs_static_flow >= 5000
```

Long local-PC profile:

```text
new_fulltheta_solver_rows >= 120000
```

### D.3 Region labels under SafeGate v2

Create separate labels:

```text
true_safe_gain_vs_staticflow:
  zero success regression vs static_flow
  quality_delta_vs_static_flow < 0
  better_count > worse_count
  support >= 80
  seed_block_support >= 3

safe_but_no_gain:
  zero success regression
  quality not improved

unsafe_useful:
  has regression but quality signal; allowed for risk learning only

non_evaluable:
  insufficient both-success or finite ratio

primary_signal_strong_static_gap:
  improves vs static_flow but loses vs family_static diagnostic
```

Do not discard unsafe_useful rows during dataset creation. They are valuable risk labels.

### D.4 Outputs

```text
outputs/tables/phase5p5_repair5g548_fulltheta_replay_plan.csv
outputs/tables/phase5p5_repair5g548_fulltheta_replay_results.csv
outputs/tables/phase5p5_repair5g548_fulltheta_selected_vs_static_flow.csv
outputs/tables/phase5p5_repair5g548_fulltheta_selected_vs_additive.csv
outputs/tables/phase5p5_repair5g548_fulltheta_selected_vs_family_static.csv
outputs/tables/phase5p5_repair5g548_fulltheta_true_safe_gain_regions.csv
outputs/tables/phase5p5_repair5g548_fulltheta_safe_but_no_gain_regions.csv
outputs/tables/phase5p5_repair5g548_fulltheta_unsafe_useful_regions.csv
outputs/tables/phase5p5_repair5g548_fulltheta_primary_signal_strong_static_gap.csv
outputs/tables/phase5p5_repair5g548_fulltheta_non_evaluable_regions.csv
outputs/tables/phase5p5_repair5g548_fulltheta_parameter_sensitivity.csv
outputs/reports/phase5p5_repair5g548_fulltheta_evidence.md
outputs/reports/phase5p5_repair5g548_fulltheta_evidence_summary.json
```

## 8. Stage E — Train generator only on evaluable replay

Only train new risk/utility/generator if:

```text
finite_ratio_rows >= 3000
both_success_quality_pairs_vs_static_flow >= 2000
```

Training data:

```text
features:
  F0 static context features
  F1 fixed static_flow trace features
  no post-solver leakage features

theta:
  full 18-dimensional UpdateParams theta

labels:
  success_regression_vs_static_flow
  quality_delta_vs_static_flow
  safe_high_margin_gain_vs_static_flow
  diagnostic family_static deltas
```

Models:

```text
risk_model(context, theta) -> P(success regression vs static_flow)
utility_model(context, theta) -> pessimistic quality delta vs static_flow
generator(context,z) -> K bounded fulltheta samples
```

Compare proposal mechanisms:

```text
G1 supervised safe-theta regressor
G2 context+latent top-K generator
G3 surrogate-guided CEM
G4 conservative staticflow-local generator
G5 negative/random controls
```

Gate:

```text
risk false-safe count on validation = 0 or explicitly bounded
risk gate pass rate between 0.01 and 0.50
generated theta usage rate >= 0.05
offline predicted utility < 0 for at least one proposal family
```

Outputs:

```text
outputs/tables/phase5p5_repair5g548_risk_model_eval.csv
outputs/tables/phase5p5_repair5g548_utility_model_eval.csv
outputs/tables/phase5p5_repair5g548_generator_eval.csv
outputs/tables/phase5p5_repair5g548_generated_theta_candidates.csv
outputs/reports/phase5p5_repair5g548_risk_utility_generator.md
outputs/reports/phase5p5_repair5g548_risk_utility_generator_summary.json
artifacts/models/laur_ltm/repair5g548_* only if warranted
```

## 9. Stage F — Generated-theta targeted replay

Only if Stage E passes.

Run generated-theta targeted replay on fresh contexts not used for Stage D training.

Minimum:

```text
targeted_solver_rows >= 7200
targeted_contexts >= 720
generated_theta_usage_rate >= 0.05
```

Primary gate:

```text
vs_static_flow_success_regression_count = 0
vs_static_flow_quality_only_mean_delta < 0
vs_static_flow_better_count > vs_static_flow_worse_count
```

Diagnostic:

```text
vs_additive
vs_family_static
```

Family-static regression does not automatically block exploration, but it blocks any claim of family-static dominance.

Outputs:

```text
outputs/tables/phase5p5_repair5g548_generated_theta_targeted_results.csv
outputs/tables/phase5p5_repair5g548_generated_theta_targeted_vs_static_flow.csv
outputs/tables/phase5p5_repair5g548_generated_theta_targeted_vs_additive.csv
outputs/tables/phase5p5_repair5g548_generated_theta_targeted_vs_family_static.csv
outputs/tables/phase5p5_repair5g548_targeted_failure_cases.csv
outputs/reports/phase5p5_repair5g548_generated_theta_targeted_evidence.md
outputs/reports/phase5p5_repair5g548_generated_theta_targeted_evidence_summary.json
```

## 10. Stage G — Blind replay only if warranted

Only if targeted gate passes.

Minimum:

```text
blind_solver_rows >= 14400
blind_contexts >= 1440
```

Primary gate:

```text
vs_static_flow_success_regression_count = 0
vs_static_flow_quality_only_mean_delta < 0
better_count > worse_count
```

Keep all promotion flags closed in G5.48 even if blind is positive. A positive blind result only warrants a later Phase5.5 preflight plan, not immediate promotion.

## 11. Final decision taxonomy

Use one of:

```text
g548_g547_verification_blocked
g548_fulltheta_materialization_regressed_stop
g548_budget_calibration_underpowered_continue_calibration
g548_budget_calibration_not_executed_continue_real_calibration
g548_no_evaluable_quality_horizon_continue_horizon_design
g548_evaluable_horizon_found_continue_fulltheta_replay
g548_fulltheta_replay_no_signal_with_evaluable_quality
g548_fulltheta_primary_staticflow_signal_continue_generator
g548_fulltheta_primary_signal_strong_static_gap_continue_diagnostics
g548_generator_offline_gate_failed_continue_model_design
g548_generated_theta_targeted_positive_continue_blind
g548_generated_theta_blind_positive_continue_phase5p5_preflight_planning
```

Do not write a final decision that says "continuous UpdateParams is not viable" unless:

```text
finite_ratio_rows >= 3000
both_success_quality_pairs_vs_static_flow >= 2000
fulltheta_fingerprint_match_rate = 1.0
new_fulltheta_solver_rows >= 40000
candidate_recognized_all = true
```

## 12. Validation sequence

Run:

```text
python -m py_compile scripts/repair5g548_common.py scripts/verify_repair5g548_g547_artifacts.py scripts/audit_repair5g548_g547_evaluability_blocker.py scripts/create_repair5g548_real_budget_calibration_plan.py scripts/run_repair5g548_real_budget_calibration.py scripts/analyze_repair5g548_real_budget_calibration.py scripts/create_repair5g548_staticflow_primary_fulltheta_probe_plan.py scripts/run_repair5g548_staticflow_primary_fulltheta_probe.py scripts/analyze_repair5g548_staticflow_primary_fulltheta_evidence.py scripts/train_eval_repair5g548_risk_utility_generator_if_warranted.py scripts/run_repair5g548_generated_theta_targeted_if_warranted.py scripts/analyze_repair5g548_generated_theta_targeted_evidence.py scripts/run_repair5g548_blind_if_warranted.py scripts/analyze_repair5g548_blind_evidence.py scripts/write_repair5g548_decision.py
python scripts/verify_repair5g548_g547_artifacts.py
python scripts/audit_repair5g548_g547_evaluability_blocker.py
python scripts/create_repair5g548_real_budget_calibration_plan.py --max-contexts 0
python scripts/run_repair5g548_real_budget_calibration.py --overwrite --max-workers 1
python scripts/analyze_repair5g548_real_budget_calibration.py
# only if calibration passes:
python scripts/create_repair5g548_staticflow_primary_fulltheta_probe_plan.py
python scripts/run_repair5g548_staticflow_primary_fulltheta_probe.py --overwrite --max-workers 1
python scripts/analyze_repair5g548_staticflow_primary_fulltheta_evidence.py
python scripts/train_eval_repair5g548_risk_utility_generator_if_warranted.py
python scripts/run_repair5g548_generated_theta_targeted_if_warranted.py --overwrite --max-workers 1
python scripts/analyze_repair5g548_generated_theta_targeted_evidence.py
python scripts/run_repair5g548_blind_if_warranted.py --overwrite --max-workers 1
python scripts/analyze_repair5g548_blind_evidence.py
python scripts/write_repair5g548_decision.py
git diff --check
git status --short -- external/lacam2/lacam2
```

If pytest is available:

```text
python -m pytest tests -q
```

At minimum, run focused existing tests touched by G5.47/G5.48.

## 13. Important behavioral instruction to Codex

Do not stop after creating reports and skip tables.

G5.48 is not complete until at least one of the following is true:

```text
1. real budget calibration solver rows >= 3000 and a final decision is written;
2. an exact binary/materialization/parser blocker is documented with failing command;
3. user interrupts the run.
```

If calibration passes, G5.48 should continue into fulltheta replay. If calibration fails after real solver rows, document why.

The most valuable negative result is not "no signal"; it is an exact diagnosis:

```text
no finite ratio because no solution
no finite ratio because parsing bug
short_budget too small
base_time_limit too small
trace not collected before counterfactual
fulltheta registry not respected
static_flow primary baseline itself fails too often
fulltheta candidates all match static_flow behavior
```
