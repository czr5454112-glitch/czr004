# G5.47 Full-Theta Materialization + Budget-Calibrated Neural UpdateParams Exploration

Project: `czr004`
Branch: `codex/g531-slice-pilot`
Starting point: after G5.46 commit `c9ab4bb`
Round name: `Repair5G.5.47 full-theta materialization and budget-calibrated neural UpdateParams exploration`

## 0. Why G5.47 exists

G5.46 is an important engineering closure but **not** a decisive negative result for the neural continuous `UpdateParams` idea.

G5.46 finally executed real continuous-theta replay:

```text
new_continuous_probe_solver_rows = 34286
contexts = 1106
candidate_theta_rows = 30968
distinct_theta_rows = 27653
baseline_rows_materialized = 3318
```

The formal G5.46 decision was:

```text
g546_real_probe_executed_no_stable_continuous_signal
```

However, the committed evidence reveals two confounders that must be fixed before declaring the neural continuous UpdateParams direction ineffective:

```text
1. The real G5.46 probe had finite_ratio_rate = 0 and finite_ratio_rows = 0.
   All summary better/worse/quality deltas were blank or zero because the probe horizon
   did not produce finite solution-quality comparisons.

2. G5.46 materialized continuous theta through the old repair5g518_grid alias path.
   That path only executes a subset of the 18 theta dimensions:
     c, b, f, w, dc, df, beta, max_shield, c_only.
   It does not faithfully execute the full neural theta vector:
     lambda_flow, lambda_cong, alpha_flow_wait_progress, min_edge_cost,
     max_edge_cost, full goal_projection_mode, etc.
```

Therefore G5.47 must not be "more rows of the same G5.46 probe." It must answer a stricter question:

```text
If we execute the full bounded continuous UpdateParams vector,
and evaluate it at a calibrated budget where baselines produce finite paired outcomes,
does neural / active continuous theta optimization find safe solver-level improvement?
```

## 1. Non-negotiable strategic correction

G5.47 remains on the main czr004 route:

```text
learned UpdateLTM / LAU-LTM
not static selector
not choosing among additive/static_flow/best_fixed/family_static
not agent-action policy
not learned restart
not solver semantic rewrite
```

The learned object is:

```text
context / fixed-fallback trace -> bounded continuous UpdateParams theta
```

A positive result requires non-static generated theta usage and real solver evidence. A static-only policy, a baseline selector, or a hand-written alias lookup cannot count as learned UpdateLTM progress.

## 2. Hard guardrails

Do not modify:

```text
external/lacam2/lacam2/**
PIBT vertex / edge-swap conflict semantics
candidate domain
agent actions
agent priorities
h-values
OPEN / EXPLORED / rewrite / incumbent pruning
LaCAM* high-level search
restart semantics
candidate deletion
```

Allowed:

```text
project-owned cpp/ltm / adapter / phase1a_batch parsing
project-owned counterfactual UpdateLTM probe
project-owned theta registry / method materialization path
Python training/evaluation scripts
reports/tables/artifacts under outputs/ and artifacts/models/laur_ltm/
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

## 3. Required worklog entry before code

Append to `docs/codex-worklog.md`:

```markdown
## 2026-06-14 - Repair5G.5.47 full-theta materialization and budget-calibrated neural UpdateParams exploration

- Request:
  Continue after G5.46 commit c9ab4bb. G5.46 finally ran real continuous-theta solver replay, but the evidence is confounded: finite_ratio_rate was zero, quality deltas were blank, and generated theta was materialized through the old repair5g518_grid alias grammar that only executes a subset of the 18 theta fields. G5.47 must first make full theta executable, then calibrate replay budgets so paired finite outcomes exist, and only then test neural / active continuous UpdateParams generation.
- Planned files:
  - czr004_g547_fulltheta_budget_calibrated_neural_updateparams_plan.md
  - scripts/repair5g547_common.py
  - scripts/verify_repair5g547_g546_artifacts.py
  - scripts/audit_repair5g547_g546_probe_confounds.py
  - scripts/create_repair5g547_fulltheta_registry.py
  - scripts/verify_repair5g547_fulltheta_materialization.py
  - scripts/run_repair5g547_budget_calibration_sentinel.py
  - scripts/analyze_repair5g547_budget_calibration.py
  - scripts/create_repair5g547_active_fulltheta_probe_plan.py
  - scripts/run_repair5g547_fulltheta_real_probe.py
  - scripts/analyze_repair5g547_fulltheta_real_evidence.py
  - scripts/train_eval_repair5g547_risk_utility_generator.py
  - scripts/materialize_repair5g547_generated_theta.py
  - scripts/run_repair5g547_generated_theta_targeted_replay.py
  - scripts/analyze_repair5g547_generated_theta_targeted_evidence.py
  - scripts/run_repair5g547_generated_theta_blind_if_warranted.py
  - scripts/analyze_repair5g547_blind_evidence.py
  - scripts/write_repair5g547_decision.py
  - project-owned cpp/ltm or phase1a adapter files only if full-theta registry requires it
  - outputs/reports/phase5p5_repair5g547_*
  - outputs/tables/phase5p5_repair5g547_*
  - outputs/logs/phase5p5_repair5g547_* local/ignored raw logs
  - artifacts/models/laur_ltm/repair5g547_* manifest/model files only when warranted
- Constraints:
  No external/lacam2/lacam2 edits, no solver semantic changes, no static selector as learned method, no reserved IDs 166..205, all Phase5.5/Phase6/runtime/AAAI claims closed.
- Pre-experiment statement:
  G5.47 is not allowed to conclude "continuous theta has no signal" unless full theta is actually executed and paired finite solver outcomes exist at calibrated budgets.
```

## 4. Stage A — Verify G5.46 and audit why its negative is confounded

Create:

```text
scripts/verify_repair5g547_g546_artifacts.py
scripts/audit_repair5g547_g546_probe_confounds.py
```

Required input artifacts:

```text
outputs/reports/phase5p5_repair5g546_decision_summary.json
outputs/reports/phase5p5_repair5g546_real_continuous_theta_evidence_summary.json
outputs/reports/phase5p5_repair5g546_theta_materialization_smoke_summary.json
outputs/reports/phase5p5_repair5g546_risk_utility_surrogates_summary.json
outputs/reports/phase5p5_repair5g546_generator_summary.json
outputs/tables/phase5p5_repair5g546_real_continuous_theta_probe_results.csv
outputs/tables/phase5p5_repair5g546_theta_materialization_smoke_results.csv
outputs/tables/phase5p5_repair5g546_theta_safety_frontier.csv
outputs/tables/phase5p5_repair5g546_theta_region_leaderboard.csv
scripts/repair5g546_common.py
scripts/repair5g545_common.py
```

Audit questions:

```text
A1. Did G5.46 meet the row-count gate? yes/no.
A2. Did G5.46 produce any finite ratio rows? exact count and rate.
A3. Did baselines solve enough contexts to allow quality comparison? per stratum.
A4. How many contexts were both-fail for additive/static_flow/family_static?
A5. Was the effective short_budget_ms 25ms even for nominal 500/1000/2000ms contexts?
A6. Did `context_key` budget disagree with `budget_ms`?
A7. Was `candidate_recognized_all` false in the real probe but true in smoke?
A8. Which theta fields were actually executed by the materialized method?
A9. Which theta fields were ignored/collapsed by `repair5g518_grid` materialization?
A10. Can G5.46's "no signal" be interpreted as a real negative, or only as budget/materialization confounded?
```

Expected outputs:

```text
outputs/reports/phase5p5_repair5g547_g546_verification.md
outputs/reports/phase5p5_repair5g547_g546_verification_summary.json
outputs/reports/phase5p5_repair5g547_g546_probe_confounds.md
outputs/reports/phase5p5_repair5g547_g546_probe_confounds_summary.json
outputs/tables/phase5p5_repair5g547_g546_artifact_audit.csv
outputs/tables/phase5p5_repair5g547_g546_budget_mismatch_audit.csv
outputs/tables/phase5p5_repair5g547_g546_effective_theta_field_audit.csv
outputs/tables/phase5p5_repair5g547_g546_finite_ratio_by_stratum.csv
outputs/tables/phase5p5_repair5g547_g546_bothfail_by_stratum.csv
```

G5.47 must explicitly record:

```json
{
  "g546_real_probe_rows": 34286,
  "g546_finite_ratio_rows": 0,
  "g546_negative_conclusion_confounded": true
}
```

if confirmed.

## 5. Stage B — Full-theta materialization, not old grid alias compression

The current materialization path collapses continuous theta into a compact grid method. G5.47 must implement a path that faithfully executes the full bounded theta vector.

### B.1 Required executable theta fields

The full theta registry must support:

```text
theta_alpha_cong_commit_progress
theta_alpha_cong_commit_nonprogress
theta_alpha_cong_block
theta_alpha_cong_wait_progress
theta_alpha_cong_wait_nonprogress
theta_alpha_flow_commit_progress
theta_alpha_flow_wait_progress
theta_rho_cong_decay
theta_rho_flow_decay
theta_lambda_cong
theta_lambda_flow
theta_flow_shield_beta
theta_max_flow_shield
theta_min_edge_cost
theta_max_edge_cost
theta_goal_projection_mode_flow_shield
theta_goal_projection_mode_agent_progress
theta_goal_projection_mode_none
```

The materialized `UpdateParams` fingerprint must reflect all active fields.

### B.2 Preferred implementation

Preferred design:

```text
outputs/tables/phase5p5_repair5g547_fulltheta_registry.csv
outputs/reports/phase5p5_repair5g547_fulltheta_registry.json
```

with candidate IDs like:

```text
repair5g547_theta_000001
repair5g547_theta_000002
...
```

and a project-owned runtime/probe option such as:

```text
--repair5g-counterfactual-updateparams-registry <registry_path>
```

or an equivalent project-owned adapter extension that maps candidate IDs to full `UpdateParams`.

This must be implemented only in project-owned code. Do not edit `external/lacam2/lacam2/**`.

If a direct registry is too invasive, extend the project-owned method grammar to a `repair5g547_fulltheta_*` form, but only if every theta field above can be represented and parsed.

### B.3 Verification smoke

Create:

```text
scripts/create_repair5g547_fulltheta_registry.py
scripts/verify_repair5g547_fulltheta_materialization.py
```

The smoke must include deliberate theta pairs that differ only in one field:

```text
lambda_flow only
lambda_cong only
alpha_flow_wait_progress only
min_edge_cost only
max_edge_cost only
goal_projection_mode only
alpha_cong_commit_nonprogress only
```

For each pair, verify:

```text
candidate_recognized = true
updateparams_fingerprint contains the intended field value
updateparams_hash differs when the field changes
force_additive parity is unaffected
default / disabled path reproduces previous behavior
external/lacam2/lacam2 remains clean
```

Minimum smoke:

```text
contexts >= 24
fulltheta candidates >= 16
baseline rows >= 72
generated fulltheta rows >= 384
finite_ratio_rows not required here
candidate_recognized_all = true
fulltheta_fingerprint_match_rate = 1.0
```

Expected outputs:

```text
outputs/reports/phase5p5_repair5g547_fulltheta_registry.md
outputs/reports/phase5p5_repair5g547_fulltheta_registry_summary.json
outputs/reports/phase5p5_repair5g547_fulltheta_materialization_smoke.md
outputs/reports/phase5p5_repair5g547_fulltheta_materialization_smoke_summary.json
outputs/tables/phase5p5_repair5g547_fulltheta_registry.csv
outputs/tables/phase5p5_repair5g547_fulltheta_field_match_audit.csv
outputs/tables/phase5p5_repair5g547_fulltheta_materialization_smoke_results.csv
outputs/tables/phase5p5_repair5g547_fulltheta_materialization_failure_cases.csv
```

If full-theta materialization fails, stop with:

```text
g547_fulltheta_materialization_blocked
```

Do not run large replay using the old grid alias path.

## 6. Stage C — Budget calibration sentinel

G5.46 evaluated a very short counterfactual horizon, producing no finite ratios. G5.47 must select evaluation budgets where paired outcomes exist.

Create:

```text
scripts/run_repair5g547_budget_calibration_sentinel.py
scripts/analyze_repair5g547_budget_calibration.py
```

### C.1 Calibration grid

Run additive, static_flow, family_static, and a small set of fulltheta smoke candidates over:

```text
maps:
  maze-32-32-4
  random-32-32-20
  warehouse-10-20-10-2-1

agents:
  50
  100

nominal context budgets:
  500
  1000
  2000

counterfactual short_budget_ms:
  25
  50
  100
  250
  500
  1000
  2000

base_time_limit_sec:
  0.20
  0.50
  1.00
  2.00
```

Avoid reserved IDs `166..205`.

### C.2 Select evaluable horizons

For each stratum, select at least one:

```text
quality_horizon:
  both_success_pair_rate(static_flow, candidate) >= 0.25
  finite_ratio_rate >= 0.25
  static_flow_success_rate >= 0.25
  additive or family baseline available

success_horizon:
  static_flow_success_rate between 0.10 and 0.90
  family/additive paired where possible
```

If no horizon produces finite outcomes for a stratum, mark that stratum as non-evaluable for G5.47 and do not use it for quality claims.

Expected outputs:

```text
outputs/reports/phase5p5_repair5g547_budget_calibration.md
outputs/reports/phase5p5_repair5g547_budget_calibration_summary.json
outputs/tables/phase5p5_repair5g547_budget_calibration_results.csv
outputs/tables/phase5p5_repair5g547_budget_horizon_selection.csv
outputs/tables/phase5p5_repair5g547_non_evaluable_strata.csv
```

Hard gate:

```text
calibrated_evaluable_strata >= 9
quality_horizon_contexts >= 360
finite_ratio_rate_overall >= 0.20
```

If this fails, stop with:

```text
g547_budget_calibration_blocked_no_evaluable_quality_horizon
```

Do not report "continuous theta no signal."

## 7. Stage D — Active full-theta probe plan

Only after Stages B and C pass, create a full-theta replay plan.

Create:

```text
scripts/create_repair5g547_active_fulltheta_probe_plan.py
```

Sampling policies:

```text
1. broad_sobol_fulltheta
2. local_staticflow_fulltheta_perturb
3. g543_signal_near_fulltheta
4. g546_risk_boundary_repaired
5. fulltheta_lambda_flow_sweep
6. fulltheta_wait_flow_sweep
7. fulltheta_cost_clamp_sweep
8. goal_projection_mode_ablation
9. surrogate_guided_cem
10. negative_controls
```

Important: at least 40% of the plan must vary fields that G5.46 did not faithfully execute:

```text
lambda_flow
lambda_cong
alpha_flow_wait_progress
min_edge_cost
max_edge_cost
goal_projection_mode
alpha_cong_commit_nonprogress
```

Minimum plan:

```text
contexts >= 1080
theta candidates per context >= 24
baseline rows >= 3240
fulltheta candidate rows >= 25920
distinct fulltheta rows >= 3000
evaluable horizon rows only
```

Preferred local PC plan:

```text
contexts >= 1440
theta candidates per context >= 32
fulltheta candidate rows >= 46080
baseline rows >= 4320
```

Long local PC plan:

```text
new solver rows >= 100000
```

Expected outputs:

```text
outputs/reports/phase5p5_repair5g547_active_fulltheta_probe_plan.md
outputs/reports/phase5p5_repair5g547_active_fulltheta_probe_plan_summary.json
outputs/tables/phase5p5_repair5g547_active_fulltheta_probe_plan.csv
outputs/tables/phase5p5_repair5g547_fulltheta_sampling_policy_breakdown.csv
```

## 8. Stage E — Real full-theta solver replay

Create:

```text
scripts/run_repair5g547_fulltheta_real_probe.py
scripts/analyze_repair5g547_fulltheta_real_evidence.py
```

### E.1 Minimum execution gate

G5.47 is not complete unless either this gate passes or an explicit blocker is documented:

```text
new_fulltheta_solver_rows >= 40000
fulltheta_candidate_rows >= 30000
baseline_rows >= 5000
contexts >= 1080
distinct_fulltheta_rows >= 3000
candidate_recognized_all = true
fulltheta_fingerprint_match_rate = 1.0
finite_ratio_rows >= 3000
finite_ratio_rate >= 0.15
both_success_quality_pairs_vs_static_flow >= 2000
```

Preferred:

```text
new_fulltheta_solver_rows >= 80000
finite_ratio_rows >= 8000
both_success_quality_pairs_vs_static_flow >= 5000
```

Long local PC profile:

```text
new_fulltheta_solver_rows >= 120000
```

### E.2 Evidence classification

Classify regions by:

```text
true_safe_gain:
  support_pairs >= 120
  seed_block_support >= 3
  vs_static_flow_success_regression_count = 0
  vs_family_static_success_regression_count = 0 when paired
  vs_additive_success_regression_count = 0 when paired
  quality_only_mean_delta_vs_static_flow < 0
  better_count > worse_count
  safe_high_margin_count > 0

safe_but_no_gain:
  zero success regression but no quality improvement

unsafe_but_useful:
  quality improvement but success regression exists

no_signal:
  neither safety nor quality

non_evaluable:
  insufficient finite paired outcomes
```

Expected outputs:

```text
outputs/reports/phase5p5_repair5g547_fulltheta_real_evidence.md
outputs/reports/phase5p5_repair5g547_fulltheta_real_evidence_summary.json
outputs/tables/phase5p5_repair5g547_fulltheta_real_probe_results.csv
outputs/tables/phase5p5_repair5g547_fulltheta_selected_vs_static_flow.csv
outputs/tables/phase5p5_repair5g547_fulltheta_selected_vs_family_static.csv
outputs/tables/phase5p5_repair5g547_fulltheta_selected_vs_additive.csv
outputs/tables/phase5p5_repair5g547_fulltheta_true_safe_gain_regions.csv
outputs/tables/phase5p5_repair5g547_fulltheta_safe_but_no_gain_regions.csv
outputs/tables/phase5p5_repair5g547_fulltheta_unsafe_but_useful_regions.csv
outputs/tables/phase5p5_repair5g547_fulltheta_non_evaluable_regions.csv
outputs/tables/phase5p5_repair5g547_fulltheta_parameter_sensitivity.csv
outputs/tables/phase5p5_repair5g547_fulltheta_failure_cases.csv
```

## 9. Stage F — Train risk / utility / generator only after meaningful replay

Create:

```text
scripts/train_eval_repair5g547_risk_utility_generator.py
```

Training data:

```text
G5.47 fulltheta real probe rows
plus G5.46 / G5.45 prior rows only as prior/augmentation
```

Do not train positive policy claims on G5.46 alone.

Feature sets:

```text
F0_static_context_only:
  map_family, agents, budget, topology proxies

F1_fixed_staticflow_trace:
  F0 + trace_event_count, trace_events_per_agent, pibt_failure_audit_count
  derived only from fixed static_flow fallback trace before choosing generated theta

F2_diagnostic_only:
  may include post-solver counters, never runtime-facing
```

Model-facing positive generators may use F0 or F1 only.

Models to train/evaluate:

```text
risk_model:
  calibrated classifier for success regression risk

utility_model:
  robust regressor / quantile lower-confidence utility

theta_generator:
  G(context, z) -> K bounded theta candidates

surrogate_guided_optimizer:
  CEM / BO / random-shooting using risk+utility surrogate
```

Evaluate:

```text
false_safe_count
false_safe_rate
risk_gate_pass_rate
utility calibration
generated_theta_diversity
non_static_theta_usage_rate
offline expected gain
whether generated theta covers true_safe_gain regions
```

Gates:

```text
false_safe_count = 0 on validation/test split
0.01 <= risk_gate_pass_rate <= 0.50
offline_generated_true_gain_capture_rate > static_flow_neighborhood_baseline
generated_theta_diversity_effective >= 16
```

Expected outputs:

```text
outputs/reports/phase5p5_repair5g547_risk_utility_generator.md
outputs/reports/phase5p5_repair5g547_risk_utility_generator_summary.json
outputs/tables/phase5p5_repair5g547_risk_model_eval.csv
outputs/tables/phase5p5_repair5g547_utility_model_eval.csv
outputs/tables/phase5p5_repair5g547_generator_eval.csv
outputs/tables/phase5p5_repair5g547_generated_theta_candidates.csv
artifacts/models/laur_ltm/repair5g547_* only when warranted
```

If there are zero true_safe_gain regions and no meaningful near-miss regions in Stage E, skip generator targeted replay and report:

```text
g547_fulltheta_real_probe_no_safe_gain_continue_design
```

## 10. Stage G — Generated-theta targeted replay

Only run if Stage F passes offline gates.

Create:

```text
scripts/materialize_repair5g547_generated_theta.py
scripts/run_repair5g547_generated_theta_targeted_replay.py
scripts/analyze_repair5g547_generated_theta_targeted_evidence.py
```

Targeted replay minimum:

```text
new_solver_rows >= 15000
contexts >= 720
generated_theta_usage_rate > 0.05
finite_ratio_rows >= 2000
success_regression_vs_static_flow = 0
success_regression_vs_family_static = 0 when paired
success_regression_vs_additive = 0 when paired
quality_only_mean_delta_vs_static_flow < 0
better_count > worse_count
```

Preferred:

```text
new_solver_rows >= 30000
contexts >= 1080
```

Expected outputs:

```text
outputs/reports/phase5p5_repair5g547_generated_theta_targeted_evidence.md
outputs/reports/phase5p5_repair5g547_generated_theta_targeted_evidence_summary.json
outputs/tables/phase5p5_repair5g547_generated_theta_targeted_results.csv
outputs/tables/phase5p5_repair5g547_generated_theta_targeted_vs_static_flow.csv
outputs/tables/phase5p5_repair5g547_generated_theta_targeted_vs_family_static.csv
outputs/tables/phase5p5_repair5g547_generated_theta_targeted_vs_additive.csv
outputs/tables/phase5p5_repair5g547_generated_theta_targeted_failure_cases.csv
```

## 11. Stage H — Blind replay only if targeted passes

Create:

```text
scripts/run_repair5g547_generated_theta_blind_if_warranted.py
scripts/analyze_repair5g547_blind_evidence.py
```

Blind minimum if warranted:

```text
new_solver_rows >= 14400
contexts >= 720
fresh seeds not used in G5.47 training or targeted replay
success_regression_vs_static_flow = 0
success_regression_vs_family_static = 0 when paired
quality_only_mean_delta_vs_static_flow < 0
better_count >= worse_count
```

Preferred:

```text
new_solver_rows >= 28800
contexts >= 1440
```

If targeted gate fails, write explicit skipped summary with reason.

## 12. Final decision taxonomy

Create:

```text
scripts/write_repair5g547_decision.py
```

Allowed decisions:

```text
g547_fulltheta_materialization_blocked
g547_budget_calibration_blocked_no_evaluable_quality_horizon
g547_fulltheta_real_probe_executed_non_evaluable
g547_fulltheta_real_probe_no_safe_gain_continue_design
g547_fulltheta_safe_gain_regions_found_continue_generator
g547_generator_offline_gate_failed_continue_model_design
g547_generated_theta_targeted_positive_continue_blind
g547_generated_theta_blind_positive_continue_refinement
g547_generated_theta_blind_regressed_continue_design
```

Required final answers:

```text
1. Did G5.46's negative remain valid after fixing materialization and budget?
2. Did full-theta execution create finite paired outcomes?
3. Which theta fields actually matter?
4. Did active search find any true_safe_gain regions?
5. Did neural generator outperform random/local/staticflow perturbation?
6. Is the bottleneck:
   materialization,
   budget/evaluability,
   theta space,
   risk model,
   utility model,
   generator,
   trace features,
   or absence of solver signal?
7. Should the next round:
   scale on server,
   improve trace encoder,
   expand UpdateParams expressivity,
   move to per-edge continuous weights,
   or stop continuous theta and return to different learned UpdateLTM formulation?
```

## 13. Validation

Run:

```text
python -m py_compile scripts/repair5g547_common.py scripts/verify_repair5g547_g546_artifacts.py scripts/audit_repair5g547_g546_probe_confounds.py scripts/create_repair5g547_fulltheta_registry.py scripts/verify_repair5g547_fulltheta_materialization.py scripts/run_repair5g547_budget_calibration_sentinel.py scripts/analyze_repair5g547_budget_calibration.py scripts/create_repair5g547_active_fulltheta_probe_plan.py scripts/run_repair5g547_fulltheta_real_probe.py scripts/analyze_repair5g547_fulltheta_real_evidence.py scripts/train_eval_repair5g547_risk_utility_generator.py scripts/materialize_repair5g547_generated_theta.py scripts/run_repair5g547_generated_theta_targeted_replay.py scripts/analyze_repair5g547_generated_theta_targeted_evidence.py scripts/run_repair5g547_generated_theta_blind_if_warranted.py scripts/analyze_repair5g547_blind_evidence.py scripts/write_repair5g547_decision.py
```

Then run the full G5.47 sequence. Parse all JSON summaries and assert:

```text
phase5p5_allowed == false
phase6_allowed == false
runtime_claim_allowed == false
learned_runtime_policy_validated == false
aaai_ready == false
```

Run:

```text
git diff --check
git status --short -- external/lacam2/lacam2
```

If pytest is available, run focused G5.47 tests. If not, write manual validation notes.

## 14. Important stop rules

Do not proceed to large real probe if:

```text
fulltheta_fingerprint_match_rate < 1.0
candidate_recognized_all = false
external_lacam2/lacam2 dirty
budget calibration finite_ratio_rate < 0.20
```

Do not train/gate a positive generator if:

```text
true_safe_gain_regions = 0
finite_ratio_rows too low
risk gate pass rate = 0 or 1 with no useful calibration
false_safe_count > 0
```

Do not call the idea dead if:

```text
the probe is non-evaluable,
full theta was not actually executed,
or all baselines failed at the chosen horizon.
```

In those cases, report the blocker precisely.
