# Repair5G.5.46 Plan: Real Continuous-Theta Replay + Risk-Calibrated Neural UpdateParams Generator

Project: `czr004`
Branch: `codex/g531-slice-pilot`
Starting commit: `0ed77ba` (`model: add G5.45 neural theta generator pipeline`)
Round name: `Repair5G.5.46 real continuous theta replay and neural generator closure`

## 0. Why G5.46 exists

G5.45 was useful, but it was not a research success. It created the neural continuous `UpdateParams` pipeline, canonical dataset, surrogate models, generator, sampling plan, and generated-theta aliases. However, it did **not** run the required new continuous-theta solver replay:

```text
G5.45:
  dataset_rows = 64968
  contexts = 5751
  distinct_theta_rows = 276
  continuous_sampling_plan_rows = 46080
  generated_theta_rows = 5760
  new_continuous_probe_rows = 0
  targeted_rows = 0
  blind_rows = 0
  decision = g545_dataset_or_materialization_blocked_continue_infrastructure
```

Therefore G5.46 must not repeat an infrastructure-only completion. The main deliverable is real solver evidence for continuous neural / active theta generation.

G5.46 continues the corrected strategic direction:

```text
Do not learn a static baseline selector.
Do not keep expanding hand-designed alias sweeps as the main method.
Learn or optimize bounded continuous static-flow / dual-channel UpdateParams.
Evaluate generated theta by real solver replay.
```

## 1. Main hypothesis

The project goal is to replace the LTM paper's coarse additive update with a learning-enhanced `UpdateLTM`.

The G5.46 hypothesis is:

```text
A risk-calibrated neural / surrogate-guided generator can propose bounded continuous
dual-channel UpdateParams theta that are safer and more useful than discrete
hand-designed aliases, when trained and evaluated with real solver evidence.
```

This is **not** a selector over:

```text
additive_ltm
static_flow_shield
best_fixed_static_goal_aware
frozen_family_static_goal_aware
```

Those are diagnostic baselines and fallback references only.

The learned object is:

```text
context / trace features -> theta
theta -> UpdateParams
```

where theta contains bounded continuous fields such as:

```text
alpha_cong_commit_progress
alpha_cong_commit_nonprogress
alpha_cong_block
alpha_cong_wait_progress
alpha_cong_wait_nonprogress
alpha_flow_commit_progress
alpha_flow_wait_progress
rho_cong_decay
rho_flow_decay
lambda_cong
lambda_flow
flow_shield_beta
max_flow_shield
min_edge_cost
max_edge_cost
goal_projection_mode logits / one-hot
```

## 2. Lessons to import from recent successful work

Use these as engineering patterns, not as permission to change solver semantics.

### 2.1 Guidance optimization, not solver replacement

GGO-style work optimizes guidance edge weights / update models while leaving the MAPF solver intact. This matches czr004: optimize `UpdateLTM` guidance, do not replace LaCAM* or PIBT.

G5.46 should therefore implement:

```text
theta proposal -> solver evaluator -> risk/utility update -> theta proposal
```

not:

```text
neural action policy
neural collision handling
neural replacement for LaCAM*
```

### 2.2 Generate multiple candidates, then evaluate

Diffusion / neural CO systems often generate multiple candidate solutions and rely on inference-time selection or downstream validation. G5.46 should not trust one deterministic theta. It should generate or optimize K candidates per context:

```text
G(context, z_1..z_K) -> theta_1..theta_K
R(context, theta_k) -> risk
U(context, theta_k) -> utility
select lowest-risk, highest-pessimistic-utility theta
or abstain to fixed static_flow
```

### 2.3 Data first, model second

CL-LNS / learning-guided MAPF patterns separate data collection, model training, and solver evaluation. G5.46 must separate:

```text
prior retrospective data
new continuous theta probe data
surrogate training data
generated-theta targeted replay data
blind replay data
```

A model trained only on retrospective G5.39-G5.43 rows is diagnostic, not validated.

### 2.4 Surrogate-guided active learning

G5.45 produced a sampling plan but did not execute it. G5.46 must turn the plan into real solver data and use active sampling:

```text
broad Sobol/LHS theta samples
local perturbations near static_flow
generator top-K theta
risk-boundary theta
utility-disagreement theta
negative controls
```

## 3. Non-negotiable guardrails

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

Do not claim:

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

Do not train or present a static baseline selector as the method. If any static-only policy wins, label it:

```text
static_selector_baseline_gain_not_laur_progress
```

A positive G5.46 result requires **generated non-static theta usage**.

## 4. Required strategic note and worklog

Append a G5.46 note to:

```text
deep-research-report.md
phase4_6_laur_ltm_codex_execution_plan.md
docs/goal_aware_dual_channel_ltm_research_strategy.md
docs/codex-worklog.md
```

Required strategic statement:

```text
G5.45 built the neural continuous theta infrastructure but did not run new continuous-theta solver replay. From G5.46 onward, neural UpdateParams evidence requires real newly materialized continuous-theta solver rows. Retrospective rows may train diagnostic surrogates, but cannot satisfy generator or replay gates.
```

Worklog must explicitly say:

```text
G5.46 is not allowed to finish as "done" unless either:
  (1) real G5.46 continuous theta solver replay is executed, or
  (2) a concrete binary/materialization blocker is found and documented with a failing command.
```

## 5. Required files

Create:

```text
czr004_g546_real_continuous_theta_replay_neural_generator_closure_plan.md

scripts/repair5g546_common.py
scripts/verify_repair5g546_g545_artifacts.py
scripts/audit_repair5g546_g545_feature_and_model_validity.py
scripts/verify_repair5g546_theta_materialization_smoke.py
scripts/create_repair5g546_active_theta_replay_plan.py
scripts/run_repair5g546_real_continuous_theta_probe.py
scripts/analyze_repair5g546_real_continuous_theta_evidence.py
scripts/train_eval_repair5g546_risk_utility_surrogates.py
scripts/train_eval_repair5g546_generator_and_cem_optimizer.py
scripts/materialize_repair5g546_generated_theta_aliases.py
scripts/run_repair5g546_generated_theta_targeted_replay.py
scripts/analyze_repair5g546_generated_theta_targeted_evidence.py
scripts/run_repair5g546_generated_theta_blind_replay_if_warranted.py
scripts/analyze_repair5g546_blind_evidence.py
scripts/write_repair5g546_decision.py
```

Expected outputs:

```text
outputs/reports/phase5p5_repair5g546_*.md
outputs/reports/phase5p5_repair5g546_*_summary.json
outputs/tables/phase5p5_repair5g546_*.csv
outputs/logs/phase5p5_repair5g546_* local raw logs
artifacts/models/laur_ltm/repair5g546_* only if trained
```

## 6. Stage A — Verify G5.45 and audit whether the dataset is model-valid

### A.1 Verify G5.45 artifacts

Required artifacts:

```text
outputs/reports/phase5p5_repair5g545_decision_summary.json
outputs/reports/phase5p5_repair5g545_dataset_coverage_summary.json
outputs/reports/phase5p5_repair5g545_continuous_sampling_plan_summary.json
outputs/reports/phase5p5_repair5g545_continuous_param_evidence_summary.json
outputs/reports/phase5p5_repair5g545_risk_utility_surrogates_summary.json
outputs/reports/phase5p5_repair5g545_neural_theta_generator_summary.json
outputs/tables/phase5p5_repair5g545_param_replay_dataset.csv
outputs/tables/phase5p5_repair5g545_continuous_param_sampling_plan.csv
outputs/tables/phase5p5_repair5g545_generated_theta_candidates.csv
outputs/tables/phase5p5_repair5g545_generated_theta_alias_map.csv
artifacts/models/laur_ltm/repair5g545_model_manifest.json
```

### A.2 Audit G5.45 failure

Write:

```text
outputs/reports/phase5p5_repair5g546_g545_failure_autopsy.md
outputs/reports/phase5p5_repair5g546_g545_failure_autopsy_summary.json
outputs/tables/phase5p5_repair5g546_g545_gate_audit.csv
```

Answer:

```text
Did G5.45 execute new continuous-probe solver rows? expected: no.
Did run_repair5g545_continuous_param_probe only write retrospective rows? expected: yes.
Was the sampling plan executable? expected: inspect methods and context fields.
Were generated theta aliases executable by current adapter grammar? expected: verify.
Why did risk_gate_pass_rate become 0? over-conservative tau, label imbalance, leakage guard, or invalid generated theta?
Does the feature set include post-solver counters that are not available before theta choice?
```

### A.3 Feature leakage / availability audit

This is critical. G5.45 feature columns included fields such as:

```text
feature_expanded_nodes
feature_high_level_expansions
feature_low_level_pibt_calls
feature_expansions_per_agent
```

These may be post-solver counters if they come from the evaluated candidate row. They are not valid pre-choice runtime features unless explicitly sourced from a fixed pre-run baseline trace.

Classify every feature as:

```text
pre_context_static
pre_trace_from_fixed_fallback
post_solver_leakage
ambiguous_needs_removal
```

Create:

```text
outputs/tables/phase5p5_repair5g546_feature_validity_audit.csv
outputs/tables/phase5p5_repair5g546_feature_sets.csv
```

Feature sets:

```text
F0_static_context_only:
  map_family, agents, budget, obstacle/corridor/junction proxies

F1_fixed_staticflow_trace:
  F0 + trace aggregates from fixed static_flow or additive fallback only

F2_full_diagnostic_not_runtime:
  includes post-solver counters, for diagnostics only, never for runtime claims
```

No positive result may use F2 as model-facing runtime feature.

## 7. Stage B — Materialization smoke: prove generated theta can really run

Before large replay, run a tiny real-solver smoke.

Create:

```text
outputs/tables/phase5p5_repair5g546_theta_materialization_smoke_plan.csv
outputs/tables/phase5p5_repair5g546_theta_materialization_smoke_results.csv
outputs/reports/phase5p5_repair5g546_theta_materialization_smoke_summary.json
```

Requirements:

```text
contexts >= 12
theta candidates/context >= 4
baselines/context >= static_flow + additive + family_static when available
new_solver_rows >= 48 generated-theta rows
all generated theta method strings recognized by adapter
cost audit finite / bounded
no external/lacam2 edits
force-additive parity unaffected
```

If this stage cannot run, stop with:

```text
g546_materialization_blocker_stop
```

and include the exact failing command, stderr excerpt, and suspected file/function.

## 8. Stage C — Real continuous theta probe, not retrospective replay

This is the main stage. It must execute actual solver commands for theta rows.

### C.1 Build an active replay plan

Use G5.45's 46,080 planned rows as a base, but improve the sampling mix.

Create:

```text
outputs/tables/phase5p5_repair5g546_active_theta_replay_plan.csv
outputs/reports/phase5p5_repair5g546_active_theta_replay_plan_summary.json
```

Minimum local profile:

```text
contexts >= 1440
theta rows >= 46080
samples/context >= 32
map families = maze, random, warehouse
agents = 50, 100
budgets = 500, 1000, 2000
fresh seeds not reused by G5.39-G5.45 when feasible
```

Preferred long profile:

```text
contexts >= 2160
theta rows >= 92160
samples/context >= 32 or 48
```

Sampling mixture:

```text
25% broad Sobol/LHS bounded theta
20% local static_flow perturbations
20% prior-safe / G5.43 signal-near theta
15% risk-boundary theta from G5.45/G5.46 surrogate uncertainty
10% generator top-K theta
5% utility-disagreement theta
5% negative controls
```

Each theta row must include:

```text
theta vector
sampling_policy
context_id
fresh_seed_block
materialized_method
expected_adapter_family
requires_real_solver_replay = true
```

### C.2 Execute real solver replay

Create a real runner using existing G5.40/G5.41/G5.43 solver materialization helpers. Do not just copy prior dataset rows.

Outputs:

```text
outputs/tables/phase5p5_repair5g546_real_continuous_theta_probe_results.csv
outputs/tables/phase5p5_repair5g546_real_continuous_theta_selected_vs_static_flow.csv
outputs/tables/phase5p5_repair5g546_real_continuous_theta_selected_vs_family_static.csv
outputs/tables/phase5p5_repair5g546_real_continuous_theta_selected_vs_additive.csv
outputs/tables/phase5p5_repair5g546_real_continuous_theta_failure_cases.csv
outputs/reports/phase5p5_repair5g546_real_continuous_theta_evidence.md
outputs/reports/phase5p5_repair5g546_real_continuous_theta_evidence_summary.json
```

Hard minimum:

```text
new_continuous_probe_solver_rows >= 30000
contexts >= 1080
distinct_theta_rows >= 1000
candidate_theta_rows >= 25000
baseline_rows_materialized >= 3000
```

Preferred:

```text
new_continuous_probe_solver_rows >= 60000
contexts >= 1440
distinct_theta_rows >= 3000
```

Long local PC target:

```text
new_continuous_probe_solver_rows >= 100000
```

If runtime is long, implement checkpointing every 500 rows and resume support.

## 9. Stage D — Analyze real continuous theta evidence

This stage determines whether neural continuous theta is viable.

Create:

```text
outputs/tables/phase5p5_repair5g546_theta_region_leaderboard.csv
outputs/tables/phase5p5_repair5g546_theta_safety_frontier.csv
outputs/tables/phase5p5_repair5g546_theta_sampling_policy_breakdown.csv
outputs/tables/phase5p5_repair5g546_theta_parameter_sensitivity.csv
outputs/tables/phase5p5_repair5g546_theta_false_safe_regions.csv
outputs/tables/phase5p5_repair5g546_theta_true_gain_regions.csv
```

Classify theta regions into:

```text
true_safe_gain:
  zero success regression vs static_flow and paired family/additive baselines
  quality delta < 0
  better > worse
  support >= 120
  seed_block_support >= 3

safe_but_no_gain:
  zero regression but quality weak or equality-only

unsafe_but_useful:
  has quality gain but success regression > 0

staticflow_equivalent:
  no meaningful difference from static_flow

negative_control:
  expected bad / sanity check
```

Report by sampling policy:

```text
broad Sobol/LHS
local static_flow perturb
prior-safe
risk-boundary
generator top-K
utility-disagreement
negative controls
```

The most important question:

```text
Does the continuous parameter space contain stable true_safe_gain regions that were missed by hand-designed aliases?
```

## 10. Stage E — Train calibrated risk and utility surrogates on real G5.46 data

Train models on:

```text
G5.39-G5.43 retrospective data
+ G5.46 real continuous theta probe data
```

But report both:

```text
retrospective-only performance
real-G5.46-only performance
combined performance
```

Models:

```text
risk_model:
  logistic / calibrated HistGradientBoosting / MLP if available
  target = any success regression vs required baselines

utility_model:
  robust regressor / quantile regressor
  target = quality_delta_vs_static_flow or safety-envelope delta

pessimistic_utility_model:
  lower confidence bound / quantile model
```

Splits:

```text
seed-block holdout
map-family holdout
source-round holdout
fresh-G5.46 holdout
```

Gates:

```text
risk false-safe count at chosen tau = 0 on validation and test
risk gate pass rate > 0.01 and < 0.50
AUPRC / recall reported, but false-safe is the hard gate
utility sign accuracy on safe rows > static baseline
```

If `risk_gate_pass_rate = 0`, do not call the generator failed. Diagnose:

```text
risk threshold too conservative
label imbalance
feature invalidity
no safe regions
model calibration issue
```

## 11. Stage F — Train generator and surrogate-guided optimizer

Train/evaluate at least three proposal mechanisms:

```text
G1 supervised theta generator:
  context -> theta, trained on true_safe_gain / safe_but_no_gain weighted targets

G2 conditional top-K generator:
  context + latent z -> K diverse theta candidates

G3 surrogate-guided CEM / BO:
  optimize theta under R(context, theta) <= tau and pessimistic U minimal
```

Do not rely on a single deterministic MLP.

For each context:

```text
generate K = 16 or 32 theta candidates
risk-filter candidates
rank by pessimistic utility
abstain to fixed static_flow if no candidate passes
```

Outputs:

```text
outputs/tables/phase5p5_repair5g546_generated_theta_candidates.csv
outputs/tables/phase5p5_repair5g546_generated_theta_alias_map.csv
outputs/tables/phase5p5_repair5g546_generator_eval.csv
outputs/reports/phase5p5_repair5g546_generator_summary.json
artifacts/models/laur_ltm/repair5g546_* if warranted
```

Generator positive offline gate:

```text
generated_theta_rows >= 5000
risk_gate_pass_rate > 0.01
non_static_theta_usage_rate > 0.05
predicted_pessimistic_utility_mean < 0
diversity: distinct_theta_rows >= 500
not collapsed to static_flow theta
```

## 12. Stage G — Generated theta targeted replay

Only after Stage F gate passes.

Targeted replay contexts:

```text
G5.43 refinement failure strata
G5.42/G5.43 staticflow regression strata
all map_family x agents x budget strata
fresh seeds after G5.45
risk-boundary contexts
high predicted utility contexts
random holdout contexts
```

Minimum:

```text
targeted_new_solver_rows >= 14400
generated_theta_contexts >= 720
baselines materialized for every context
```

Preferred:

```text
targeted_new_solver_rows >= 28800
generated_theta_contexts >= 1440
```

Outputs:

```text
outputs/tables/phase5p5_repair5g546_generated_theta_targeted_replay_results.csv
outputs/tables/phase5p5_repair5g546_targeted_selected_vs_static_flow.csv
outputs/tables/phase5p5_repair5g546_targeted_selected_vs_family_static.csv
outputs/tables/phase5p5_repair5g546_targeted_selected_vs_additive.csv
outputs/tables/phase5p5_repair5g546_targeted_failure_cases.csv
outputs/reports/phase5p5_repair5g546_generated_theta_targeted_evidence_summary.json
```

Targeted positive gate:

```text
success_regression_vs_static_flow = 0
success_regression_vs_family_static = 0 where paired
success_regression_vs_additive = 0 where paired
generated_theta_usage_rate > 0.05
quality_only_mean_delta_vs_static_flow < 0
better_count_vs_static_flow >= worse_count_vs_static_flow
safe_high_margin_count > 0
underpowered = false
```

If targeted replay fails, classify:

```text
generator_false_safe
surrogate_utility_miscalibrated
theta_materialization_mismatch
continuous_space_no_stable_gain
feature_insufficient
baseline_conflict_not_residual
```

## 13. Stage H — Blind replay only if warranted

Only run blind replay if targeted gate passes.

Blind minimum:

```text
blind_new_solver_rows >= 14400
blind_pairs_vs_static_flow >= 1440
```

Preferred:

```text
blind_new_solver_rows >= 28800
```

Blind gate:

```text
zero success regression vs static_flow
zero success regression vs family_static where paired
quality_only_mean_delta_vs_static_flow < 0
better >= worse
non_static generated theta usage > 0.05
```

If blind gate passes, still keep all claim flags closed but report:

```text
g546_generated_theta_blind_positive_continue_runtime_preflight
```

Runtime/Phase5.5 remains closed until a separate export/parity/runtime round.

## 14. Final decision schema

Write:

```text
outputs/reports/phase5p5_repair5g546_decision.md
outputs/reports/phase5p5_repair5g546_decision_summary.json
```

Allowed decisions:

```text
g546_materialization_blocker_stop
g546_real_probe_executed_no_stable_continuous_signal
g546_real_probe_safe_regions_found_generator_failed
g546_surrogate_false_safe_blocks_generator
g546_generated_theta_targeted_regression_continue_model_repair
g546_generated_theta_targeted_positive_blind_not_warranted_or_not_run
g546_generated_theta_blind_positive_continue_runtime_preflight
g546_dataset_or_feature_invalid_rebuild_required
```

The final decision must answer:

```text
1. Did G5.46 actually run new real continuous theta solver rows?
2. Is the continuous UpdateParams search space viable?
3. Did neural/surrogate generation outperform broad/random/local sampling?
4. Are failures caused by materialization, feature leakage, risk false-safety, generator collapse, or absence of solver signal?
5. Is the project still on learned UpdateLTM, not static selector?
```

## 15. Validation commands

Codex should run a validation sequence like:

```bash
python -m py_compile scripts/repair5g546_common.py scripts/verify_repair5g546_g545_artifacts.py scripts/audit_repair5g546_g545_feature_and_model_validity.py scripts/verify_repair5g546_theta_materialization_smoke.py scripts/create_repair5g546_active_theta_replay_plan.py scripts/run_repair5g546_real_continuous_theta_probe.py scripts/analyze_repair5g546_real_continuous_theta_evidence.py scripts/train_eval_repair5g546_risk_utility_surrogates.py scripts/train_eval_repair5g546_generator_and_cem_optimizer.py scripts/materialize_repair5g546_generated_theta_aliases.py scripts/run_repair5g546_generated_theta_targeted_replay.py scripts/analyze_repair5g546_generated_theta_targeted_evidence.py scripts/run_repair5g546_generated_theta_blind_replay_if_warranted.py scripts/analyze_repair5g546_blind_evidence.py scripts/write_repair5g546_decision.py

python scripts/verify_repair5g546_g545_artifacts.py
python scripts/audit_repair5g546_g545_feature_and_model_validity.py
python scripts/verify_repair5g546_theta_materialization_smoke.py --overwrite
python scripts/create_repair5g546_active_theta_replay_plan.py --samples-per-context 32
python scripts/run_repair5g546_real_continuous_theta_probe.py --overwrite --max-workers 1
python scripts/analyze_repair5g546_real_continuous_theta_evidence.py
python scripts/train_eval_repair5g546_risk_utility_surrogates.py --bootstrap-samples 300
python scripts/train_eval_repair5g546_generator_and_cem_optimizer.py --k-samples 32
python scripts/materialize_repair5g546_generated_theta_aliases.py
python scripts/run_repair5g546_generated_theta_targeted_replay.py --overwrite --max-workers 1
python scripts/analyze_repair5g546_generated_theta_targeted_evidence.py
python scripts/run_repair5g546_generated_theta_blind_replay_if_warranted.py --overwrite --max-workers 1
python scripts/analyze_repair5g546_blind_evidence.py
python scripts/write_repair5g546_decision.py
python - <<'PY'
import json, pathlib
for p in pathlib.Path("outputs/reports").glob("phase5p5_repair5g546_*summary.json"):
    obj=json.loads(p.read_text())
    assert obj.get("phase5p5_allowed") is False
    assert obj.get("phase6_allowed") is False
    assert obj.get("runtime_claim_allowed") is False
    assert obj.get("learned_runtime_policy_validated") is False
    assert obj.get("aaai_ready") is False
print("G5.46 summaries parsed and claims closed")
PY
git diff --check
git status --short -- external/lacam2/lacam2
```

If a full long run is too slow, Codex may run:

```bash
python scripts/run_repair5g546_real_continuous_theta_probe.py --overwrite --max-workers 1 --row-limit 30000
```

but must not claim preferred-profile completion.

## 16. Explicit stop conditions

Stop early only for:

```text
materialization smoke cannot execute generated theta
binary missing or solver invocation broken, with exact failing command
external/lacam2 dirty
reserved ID guard violation
feature audit finds unavoidable leakage in all available feature sets
```

Do **not** stop merely because scripts and models were created.

G5.46 is not complete until:

```text
new_continuous_probe_solver_rows >= 30000
```

or an explicit blocker is documented.
