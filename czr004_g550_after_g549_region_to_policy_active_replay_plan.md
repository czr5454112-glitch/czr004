# Repair5G.5.50 Plan — From G5.49 True Safe-Gain Regions to a Learned UpdateLTM Policy

Project: `czr004`
Branch: `codex/g531-slice-pilot`
Start commit: `cfa36a3` (`repair5g549 calibration fulltheta replay`)
Round name: `Repair5G.5.50 region-to-policy active replay + safe learned UpdateParams generator`

## 0. Why G5.50 exists

G5.49 is the first round that produced real static-flow-relative fulltheta signal:

```text
new_calibration_solver_rows = 8220
cumulative_calibration_solver_rows = 11874
cumulative_finite_ratio_rows = 9780
cumulative_both_success_quality_pairs_vs_static_flow = 7643
unique_evaluable_stratum_count = 4
warehouse_non_evaluable_on_local_budget = true
new_fulltheta_solver_rows = 30282
fulltheta_candidate_rows = 29400
finite_ratio_rows = 20547
both_success_quality_pairs_vs_static_flow = 18514
true_safe_gain_regions = 10
generator decision = g549_generator_offline_gate_failed_continue_model_design
targeted/blind replay = skipped by gate
```

Interpretation:

```text
G5.49 is a positive existence result, not a deployable learned policy.
It shows that fulltheta UpdateParams can safely improve over static_flow_shield
in calibrated core conditions, but the signal is narrow and still hindsight-based.
```

The main G5.50 question:

```text
Can the G5.49 replay-region signal be transformed into a learned, context-conditioned,
bounded UpdateParams policy or safe expert-mixture policy that survives fresh targeted
and blind replay against static_flow_shield?
```

G5.50 must not stop after a small generator table. It must explore several plausible routes, run fresh replay when gates permit, and produce enough diagnostic evidence to decide whether the bottleneck is:

```text
1. true signal too narrow;
2. replay data insufficient;
3. features insufficient;
4. generator/model design too weak;
5. SafeGate too conservative but correctly blocking deployment;
6. evaluator/horizon coverage too narrow;
7. fulltheta regions are real but not learnable from runtime-available context.
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
OPEN / EXPLORED / rewrite / incumbent pruning
restart semantics
candidate deletion semantics
LaCAM* high-level search
```

Keep all claim flags closed unless a later formal gate explicitly says otherwise:

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

A learned method may output:

```text
bounded continuous UpdateParams theta
bounded residuals around static_flow_shield theta
safe mixture weights over bounded UpdateParams experts
ALLOW_THETA / ABSTAIN_TO_STATIC_FLOW
```

A learned method must not output:

```text
additive_ltm
static_flow_shield
best_fixed_static_goal_aware
frozen_family_static_goal_aware
```

as discrete learned actions. If an expert mixture is used, materialize the mixture into a bounded `UpdateParams` vector and log the weights; do not call it a static ID selector.

## 2. Data and repository hygiene

G5.49 pushed `outputs/tables/phase5p5_repair5g549_fulltheta_replay_plan.csv` at about 87 MB. G5.50 must not add another large tracked CSV by accident.

Required policy:

```text
Do not commit generated tables larger than 50 MB.
Large raw plans/results should be written under ignored logs or compressed artifacts.
Commit only:
  - summary JSON
  - schema report
  - row-count manifest
  - file hash manifest
  - policy breakdown table
  - sampled preview table <= 1000 rows
  - analysis tables that are compact enough to review
```

Create:

```text
outputs/reports/phase5p5_repair5g550_large_artifact_manifest.json
outputs/reports/phase5p5_repair5g550_large_artifact_policy.md
outputs/tables/phase5p5_repair5g550_committed_table_size_audit.csv
```

If any planned committed file exceeds 50 MB, the G5.50 decision must include:

```text
large_artifact_commit_blocked_or_redirected_to_logs
```

## 3. Required worklog entry

Append before code:

```markdown
## 2026-06-14 - Repair5G.5.50 region-to-policy active replay

- Request:
  Continue after G5.49 commit cfa36a3. G5.49 found 10 true safe-gain fulltheta regions versus static_flow_shield, but only in a calibrated-core development subset. The generator did not produce a deployable non-static theta policy, targeted/blind replay were skipped, unique evaluable strata stayed at 4, and warehouse remained non-evaluable locally. G5.50 must expand/replicate the signal, diagnose region concentration, build multiple learned UpdateParams generator routes, and run fresh targeted/blind replay only by gate.
- Scientific target:
  Convert fulltheta replay-region evidence into a learned bounded UpdateParams or safe expert-mixture policy that improves over static_flow_shield without changing solver semantics.
- Constraints:
  No external/lacam2/lacam2 edits, no solver semantic changes, no static selector method, no IDs 166..205, no Phase5.5/Phase6/runtime/AAAI claims.
```

## 4. Stage A — Verify G5.49 and audit the evidence semantics

Create:

```text
scripts/verify_repair5g550_g549_artifacts.py
scripts/audit_repair5g550_g549_signal_semantics.py
```

Expected outputs:

```text
outputs/reports/phase5p5_repair5g550_g549_verification.md
outputs/reports/phase5p5_repair5g550_g549_verification_summary.json
outputs/reports/phase5p5_repair5g550_g549_signal_semantics.md
outputs/reports/phase5p5_repair5g550_g549_signal_semantics_summary.json
outputs/tables/phase5p5_repair5g550_g549_artifact_audit.csv
outputs/tables/phase5p5_repair5g550_g549_true_gain_region_audit.csv
outputs/tables/phase5p5_repair5g550_g549_generator_gate_audit.csv
outputs/tables/phase5p5_repair5g550_g549_plan_vs_executed_audit.csv
outputs/tables/phase5p5_repair5g550_g549_claim_flag_audit.csv
```

Required checks:

1. Verify G5.49 commit and summaries:

```text
commit = cfa36a3
final decision = g549_fulltheta_true_safe_gain_regions_found_continue_generator
primary_baseline = static_flow_shield
true_safe_gain_regions = 10
new_fulltheta_solver_rows = 30282
generator decision = g549_generator_offline_gate_failed_continue_model_design
targeted/blind new solver rows = 0
phase5p5_allowed = false
phase6_allowed = false
runtime_claim_allowed = false
aaai_ready = false
```

2. Distinguish all of these:

```text
selected_evaluable_horizon_rows
unique_evaluable_stratum_count
true_safe_gain_region_count
unique true-gain strata
unique true-gain horizons
unique true-gain theta clusters
unique true-gain candidate rows
```

3. Report concentration explicitly:

```text
Which map_family / agent / nominal_budget / horizon combinations produced true gain?
Are all true gains concentrated in random-100-2000?
Did maze have safe/no-gain but not true gain?
Did random-50 have no true gain despite evaluability?
Did warehouse remain non-evaluable?
```

4. Plan-vs-executed audit:

```text
G5.49 fulltheta replay plan rows vs executed rows
planned contexts vs executed contexts
planned candidate rows vs executed candidate rows
whether the 87 MB plan was fully or partially consumed
whether remaining planned rows should be resumed, regenerated, or ignored
```

5. Generator gate audit:

```text
Why generated_non_static_theta_usage_rate = 0?
Did risk model pass but generator fail because no deployable policy was promoted?
Did the offline gate fail because candidates are hindsight replay regions only?
Which features were available to the generator?
Which labels were replay-region labels vs runtime-available counterfactual labels?
```

## 5. Stage B — Forensic analysis of G5.49 true safe-gain regions

Create:

```text
scripts/analyze_repair5g550_true_gain_forensics.py
```

Expected outputs:

```text
outputs/reports/phase5p5_repair5g550_true_gain_forensics.md
outputs/reports/phase5p5_repair5g550_true_gain_forensics_summary.json
outputs/tables/phase5p5_repair5g550_true_gain_region_stats.csv
outputs/tables/phase5p5_repair5g550_true_gain_theta_intervals.csv
outputs/tables/phase5p5_repair5g550_true_gain_candidate_examples.csv
outputs/tables/phase5p5_repair5g550_true_gain_vs_family_static_diagnostic.csv
outputs/tables/phase5p5_repair5g550_safe_no_gain_region_stats.csv
outputs/tables/phase5p5_repair5g550_unsafe_useful_region_stats.csv
outputs/tables/phase5p5_repair5g550_non_evaluable_region_stats.csv
outputs/tables/phase5p5_repair5g550_region_bootstrap_ci.csv
```

Compute, at minimum:

```text
support_pairs
pair_rows
seed_block_support
success_regression_count
success_regression_rate
quality_only_mean_delta_vs_static_flow
better_count_vs_static_flow
worse_count_vs_static_flow
bootstrap 95% CI for mean delta
per-seed-block delta
per-horizon delta
family_static diagnostic gap
additive floor gap
```

Important interpretation rules:

```text
negative quality delta means lower ratio / better quality if that is the established metric convention;
zero success regression versus static_flow is required for true_safe_gain;
losing to family_static is a diagnostic gap, not automatic failure;
beating additive but not static_flow is not learned UpdateLTM success.
```

If the 10 true-safe-gain regions all collapse to one stratum/horizon family, write:

```text
true_gain_exists_but_is_concentrated
```

not:

```text
broad learned UpdateLTM success
```

## 6. Stage C — Resume and expand fulltheta replay beyond the narrow G5.49 subset

Create:

```text
scripts/create_repair5g550_fulltheta_expansion_plan.py
scripts/run_repair5g550_fulltheta_expansion.py
scripts/analyze_repair5g550_fulltheta_expansion.py
```

Expected outputs:

```text
outputs/reports/phase5p5_repair5g550_fulltheta_expansion_plan.md
outputs/reports/phase5p5_repair5g550_fulltheta_expansion_plan_summary.json
outputs/reports/phase5p5_repair5g550_fulltheta_expansion_summary.json
outputs/reports/phase5p5_repair5g550_fulltheta_expansion.md
outputs/tables/phase5p5_repair5g550_fulltheta_expansion_policy_breakdown.csv
outputs/tables/phase5p5_repair5g550_fulltheta_expansion_preview.csv
outputs/tables/phase5p5_repair5g550_fulltheta_expansion_results_sample.csv
outputs/tables/phase5p5_repair5g550_fulltheta_expansion_selected_vs_static_flow.csv
outputs/tables/phase5p5_repair5g550_fulltheta_expansion_true_safe_gain_regions.csv
outputs/tables/phase5p5_repair5g550_fulltheta_expansion_replication_by_stratum.csv
```

Do not commit huge raw result files. Put full raw results under ignored logs and commit a manifest/hash.

### C.1 Core replication

Replicate every G5.49 true-safe-gain region on fresh seeds:

```text
seeds: 1520..1599 or another non-reserved fresh block
map_family: random
agents: 100
nominal_budget_ms: 2000
horizons: c0_short2000_t050_i2 and c0_short5000_t050_i2
baseline: static_flow_shield primary
additive_ltm and family_static diagnostics
```

Minimum:

```text
new_replication_solver_rows >= 30000
new_replication_contexts >= 300
both_success_quality_pairs_vs_static_flow >= 10000
```

Preferred local PC target:

```text
new_replication_solver_rows >= 60000
new_replication_contexts >= 600
```

### C.2 Neighbor-stratum transfer

Test whether the signal transfers to evaluable neighbor strata:

```text
random, agents 50, nominal_budget_ms 2000
maze, agents 50/100, nominal_budget_ms 2000
same short budgets where evaluable
```

Minimum:

```text
neighbor_transfer_solver_rows >= 30000
```

### C.3 Hard-stratum diagnostic continuation

Keep warehouse and 500/1000ms budgets as diagnostic, not a blocker:

```text
warehouse 50/100, budgets 500/1000/2000
short_budget_ms in {5000, 10000, 20000}
base_time_limit_sec in {1.0, 2.0, 5.0, 10.0}
ltm_max_iterations in {4, 8, 12}
```

If still non-evaluable, write:

```text
warehouse_remains_non_evaluable_under_g550_local_budget
```

and continue with no broad claim.

### C.4 Controls

Include:

```text
static_flow_shield primary baseline
additive_ltm paper floor
family_static diagnostic
random theta negative controls
shuffled theta-label controls
static-flow-local perturbation baseline
G5.49 true-region replay oracle diagnostic
```

Decision labels:

```text
g550_true_gain_replicates_core
g550_true_gain_transfers_to_neighbor_strata
g550_true_gain_core_only_no_transfer
g550_true_gain_failed_to_replicate_under_powered_or_negative
g550_hard_strata_non_evaluable_continue_evaluator_design
```

## 7. Stage D — Active theta search around G5.49 safe-gain regions

Create:

```text
scripts/create_repair5g550_active_theta_search_plan.py
scripts/run_repair5g550_active_theta_search.py
scripts/analyze_repair5g550_active_theta_search.py
```

Expected outputs:

```text
outputs/reports/phase5p5_repair5g550_active_theta_search_plan.md
outputs/reports/phase5p5_repair5g550_active_theta_search_summary.json
outputs/reports/phase5p5_repair5g550_active_theta_search.md
outputs/tables/phase5p5_repair5g550_active_theta_search_policy_breakdown.csv
outputs/tables/phase5p5_repair5g550_active_theta_search_best_regions.csv
outputs/tables/phase5p5_repair5g550_active_theta_search_theta_intervals.csv
outputs/tables/phase5p5_repair5g550_active_theta_search_failure_cases.csv
```

Search families:

```text
1. Dense local perturbations around each G5.49 true region centroid
2. Latin hypercube / Sobol-style bounded sampling around promising intervals
3. Coordinate sweeps on lambda_flow, lambda_cong, alpha_flow_wait_progress, min/max edge cost
4. Goal projection mode ablations
5. Conservative shrinkage toward static_flow_shield
6. Risky expansions to learn failure boundary
7. Negative random controls matched by parameter range
```

Every proposed theta must be bounded and materialized through the fulltheta registry/fingerprint path.

Minimum:

```text
active_theta_candidates >= 4096
active_theta_solver_rows >= 50000
both_success_quality_pairs_vs_static_flow >= 15000
full_only_field_variation_rate >= 0.40
fulltheta_fingerprint_match_rate = 1
```

Preferred local PC target:

```text
active_theta_candidates >= 8192
active_theta_solver_rows >= 100000
```

Do not stop active search just because one generator model fails. The goal is to map useful/safe/unsafe boundaries for the next learned policy.

## 8. Stage E — Build multiple learned UpdateParams policy routes

Create:

```text
scripts/create_repair5g550_policy_features.py
scripts/train_eval_repair5g550_policy_family_suite.py
scripts/analyze_repair5g550_policy_failure_modes.py
```

Expected outputs:

```text
outputs/reports/phase5p5_repair5g550_policy_feature_audit.md
outputs/reports/phase5p5_repair5g550_policy_family_suite_summary.json
outputs/reports/phase5p5_repair5g550_policy_failure_modes.md
outputs/tables/phase5p5_repair5g550_policy_feature_manifest.csv
outputs/tables/phase5p5_repair5g550_policy_leakage_audit.csv
outputs/tables/phase5p5_repair5g550_policy_family_eval.csv
outputs/tables/phase5p5_repair5g550_policy_family_ablation.csv
outputs/tables/phase5p5_repair5g550_policy_oof_predictions.csv
outputs/tables/phase5p5_repair5g550_generated_theta_candidates.csv
artifacts/models/laur_ltm/repair5g550_model_manifest.json
```

### E.1 Feature requirements

Use only runtime-available pre-update features:

```text
map family / map statistics
agent count / density
nominal budget and horizon metadata
traffic_before summary
trace event counts
committed / blocked / wait progress summaries
C-channel/F-channel update stats
rank-audit aggregates if available before applying the candidate theta
checkpoint traffic snapshot summaries
```

Forbidden model-facing features:

```text
future solver outcome
candidate quality delta
static_flow solved flag from the same counterfactual replay
oracle / posthoc labels as raw features
theta_cluster true label as raw feature
any feature that directly encodes heldout outcome
```

Write a leakage audit. If leakage is found, regenerate features and mark the leaked run invalid.

### E.2 Required policy families

Train/evaluate at least these families. If a dependency is unavailable, implement a simple numpy/pure-Python fallback and document it.

#### Family 1 — Safe expert mixture with abstention, preferred immediate route

Input:

```text
runtime-available context/trace features
```

Output:

```text
mixture weights over bounded theta experts
+ ABSTAIN_TO_STATIC_FLOW probability
```

Materialization:

```text
UpdateParams = convex mixture of bounded theta experts
```

This is allowed because the deployed action is a bounded theta vector, not a static baseline ID selector.

#### Family 2 — Bounded residual over static_flow_shield theta

Input:

```text
runtime-available context/trace features
```

Output:

```text
delta theta around static_flow_shield
clipped into verified theta bounds
+ abstention probability
```

Use small residual bounds first. Do not jump to arbitrary unrestricted theta.

#### Family 3 — Pairwise safe utility ranker

Train to rank candidate theta vectors for a context while predicting success-regression risk. It may propose theta only when:

```text
risk <= threshold
utility_margin_vs_static_flow >= threshold
uncertainty <= threshold
```

#### Family 4 — kNN / prototype policy over true-safe regions

Use G5.49/G5.50 true region prototypes as theta proposals with calibrated distance-to-support and abstention. This is diagnostic and may become a bridge if it generalizes.

#### Family 5 — Negative controls

Train controls using:

```text
shuffled labels
random features
random theta proposals
static-only selector-like action space
```

The real policy must beat these controls offline and, if promoted, in targeted replay.

### E.3 Splits and gates

Use out-of-fold evaluation:

```text
leave-seed-block-out
leave-horizon-out
leave-map-family-out where possible
leave-true-region-cluster-out diagnostic
```

Offline policy gate:

```text
risk_false_safe_count_on_validation = 0
success_regression_rate_predicted_safe = 0
predicted_safe_utility_mean_delta_vs_static_flow < 0
predicted_safe_utility_CI_upper < 0 if bootstrap available
generated_non_static_theta_usage_rate >= 0.05
beats shuffled-label and random-feature controls
candidate_recognized_all = true
fulltheta_fingerprint_match_rate = 1
```

If no family passes, do not stop with a one-line generator failure. Write a failure decomposition:

```text
feature_insufficient
label_insufficient
signal_too_concentrated
risk_gate_too_conservative_but_correct
policy_family_too_weak
needs_iteration_level_counterfactual_labels
```

## 9. Stage F — Fresh targeted replay of promoted generated theta

Create:

```text
scripts/create_repair5g550_generated_theta_targeted_plan.py
scripts/run_repair5g550_generated_theta_targeted.py
scripts/analyze_repair5g550_generated_theta_targeted.py
```

Only run if at least one learned policy family passes the offline gate. If none passes, create skip artifacts plus detailed model-design failure report.

Expected outputs:

```text
outputs/reports/phase5p5_repair5g550_generated_theta_targeted_plan.md
outputs/reports/phase5p5_repair5g550_generated_theta_targeted_summary.json
outputs/reports/phase5p5_repair5g550_generated_theta_targeted.md
outputs/tables/phase5p5_repair5g550_generated_theta_targeted_results_sample.csv
outputs/tables/phase5p5_repair5g550_generated_theta_targeted_vs_static_flow.csv
outputs/tables/phase5p5_repair5g550_generated_theta_targeted_vs_additive.csv
outputs/tables/phase5p5_repair5g550_generated_theta_targeted_vs_family_static.csv
outputs/tables/phase5p5_repair5g550_generated_theta_targeted_failure_cases.csv
```

Targeted replay must use fresh seeds not used in training/evaluation:

```text
fresh targeted seeds: 1600..1699 or equivalent non-reserved block
core: random-100-2000 true-gain replication
transfer: random-50-2000 and maze-50/100-2000 if evaluable
hard diagnostic: warehouse if any horizon becomes evaluable
```

Minimum targeted replay:

```text
new_targeted_solver_rows >= 30000
generated_theta_rows >= 20000
baseline_rows >= 4000
both_success_quality_pairs_vs_static_flow >= 8000
```

Targeted gate:

```text
success_regression_count_vs_static_flow = 0
quality_only_mean_delta_vs_static_flow < 0
better_count_vs_static_flow > worse_count_vs_static_flow
generated_non_static_theta_usage_rate >= 0.05
beats random theta and shuffled controls
fulltheta_fingerprint_match_rate = 1
```

If targeted passes only on random-100-2000, label:

```text
targeted_core_only_signal_not_broad_claim
```

## 10. Stage G — Blind replay only if targeted passes

Create:

```text
scripts/create_repair5g550_blind_replay_plan.py
scripts/run_repair5g550_blind_replay.py
scripts/analyze_repair5g550_blind_replay.py
```

Blind replay conditions:

```text
fresh blind seeds disjoint from calibration/topup/fulltheta/targeted/model splits
no access to blind outcomes during generator design
static_flow_shield remains primary baseline
additive and family_static remain diagnostics
```

Minimum blind replay:

```text
new_blind_solver_rows >= 30000
both_success_quality_pairs_vs_static_flow >= 8000
```

Blind pass requires:

```text
success_regression_count_vs_static_flow = 0
quality_only_mean_delta_vs_static_flow < 0
bootstrap CI upper <= 0 when enough support exists
generated_non_static_theta_usage_rate >= 0.05
no solver semantic changes
```

Even if blind passes, keep:

```text
phase5p5_allowed=false
phase6_allowed=false
runtime_claim_allowed=false
aaai_ready=false
```

unless a separate promotion plan is created and approved.

## 11. Stage H — Iteration-level counterfactual label preflight

G5.49/G5.50 full-run region labels are useful but can remain too coarse for a learned UpdateLTM policy. Start a diagnostic preflight for true counterfactual UpdateLTM labels:

Create:

```text
scripts/create_repair5g550_iteration_counterfactual_label_plan.py
scripts/run_repair5g550_iteration_counterfactual_label_probe.py
scripts/analyze_repair5g550_iteration_counterfactual_labels.py
```

Expected outputs:

```text
outputs/reports/phase5p5_repair5g550_iteration_counterfactual_label_plan.md
outputs/reports/phase5p5_repair5g550_iteration_counterfactual_label_summary.json
outputs/reports/phase5p5_repair5g550_iteration_counterfactual_labels.md
outputs/tables/phase5p5_repair5g550_iteration_counterfactual_contexts.csv
outputs/tables/phase5p5_repair5g550_iteration_counterfactual_label_sample.csv
outputs/tables/phase5p5_repair5g550_iteration_counterfactual_oracle_gap.csv
outputs/tables/phase5p5_repair5g550_iteration_counterfactual_feature_leakage_audit.csv
```

Target schema:

```text
same traffic_before + same trace_events + same checkpoint
apply theta A -> downstream short-probe outcome A
apply theta B -> downstream short-probe outcome B
compute A-vs-B and A-vs-static_flow labels
```

This stage is diagnostic if heavy. Minimum useful preflight:

```text
counterfactual_contexts >= 200
candidate_theta_per_context >= 16
solver_rows >= 3200
```

Preferred local PC target:

```text
counterfactual_contexts >= 1000
candidate_theta_per_context >= 32
solver_rows >= 32000
```

If completed, answer:

```text
Do runtime-available trace/checkpoint features predict which theta region is safe/useful?
Is the oracle gap large enough to justify learned policy design?
Are G5.49 true regions tied to identifiable trace states or just stratum IDs?
```

## 12. Final decision writer

Create:

```text
scripts/write_repair5g550_decision.py
```

Expected outputs:

```text
outputs/reports/phase5p5_repair5g550_decision.md
outputs/reports/phase5p5_repair5g550_decision_summary.json
outputs/tables/phase5p5_repair5g550_decision_evidence_matrix.csv
```

Decision categories:

```text
g550_true_gain_replicated_but_generator_not_ready_continue_policy_design
g550_generator_offline_passed_continue_targeted_replay
g550_targeted_true_safe_gain_continue_blind_replay
g550_blind_true_safe_gain_development_success_continue_promotion_design
g550_signal_core_only_continue_transfer_and_label_collection
g550_signal_failed_to_replicate_underpowered_continue_replay
g550_signal_failed_to_replicate_sufficiently_powered_negative_for_current_region
g550_hard_strata_non_evaluable_continue_horizon_design
g550_iteration_counterfactual_labels_needed_before_generator
g550_blocked_with_exact_commands
```

The decision summary must include:

```json
{
  "primary_baseline": "static_flow_shield",
  "additive_ltm_role": "paper-faithful floor",
  "strong_static_role": "diagnostic only",
  "g549_true_safe_gain_regions_replicated": null,
  "generator_policy_family_best": "...",
  "generated_non_static_theta_usage_rate": "...",
  "targeted_replay_run": false,
  "blind_replay_run": false,
  "unique_evaluable_stratum_count": 0,
  "warehouse_non_evaluable": true,
  "success_regression_count_vs_static_flow": 0,
  "quality_delta_vs_static_flow": "...",
  "runtime_claim_allowed": false,
  "phase5p5_allowed": false,
  "phase6_allowed": false,
  "aaai_ready": false
}
```

## 13. Suggested local execution sequence

Codex should implement the scripts and then run a meaningful local sequence. Use row limits high enough to generate new evidence, but write resumable checkpoints/status JSON after each context group.

```bash
git status --short
git checkout codex/g531-slice-pilot
git pull origin codex/g531-slice-pilot

python scripts/verify_repair5g550_g549_artifacts.py
python scripts/audit_repair5g550_g549_signal_semantics.py
python scripts/analyze_repair5g550_true_gain_forensics.py

python scripts/create_repair5g550_fulltheta_expansion_plan.py
python scripts/run_repair5g550_fulltheta_expansion.py --row-limit 60000 --max-workers 1
python scripts/analyze_repair5g550_fulltheta_expansion.py

python scripts/create_repair5g550_active_theta_search_plan.py
python scripts/run_repair5g550_active_theta_search.py --row-limit 50000 --max-workers 1
python scripts/analyze_repair5g550_active_theta_search.py

python scripts/create_repair5g550_policy_features.py
python scripts/train_eval_repair5g550_policy_family_suite.py
python scripts/analyze_repair5g550_policy_failure_modes.py

python scripts/create_repair5g550_generated_theta_targeted_plan.py
python scripts/run_repair5g550_generated_theta_targeted.py --row-limit 30000 --max-workers 1
python scripts/analyze_repair5g550_generated_theta_targeted.py

python scripts/create_repair5g550_blind_replay_plan.py
python scripts/run_repair5g550_blind_replay.py --row-limit 30000 --max-workers 1
python scripts/analyze_repair5g550_blind_replay.py

python scripts/create_repair5g550_iteration_counterfactual_label_plan.py
python scripts/run_repair5g550_iteration_counterfactual_label_probe.py --row-limit 32000 --max-workers 1
python scripts/analyze_repair5g550_iteration_counterfactual_labels.py

python scripts/write_repair5g550_decision.py
python -m py_compile scripts/repair5g550_common.py scripts/*repair5g550*.py
python -m pytest tests -q
git diff --check
git status --short
```

If the local PC cannot finish all replay rows in one invocation, do not reduce the scientific goal to table generation. The scripts must be resumable, and the committed decision must state exactly which stages ran, row counts, gates, and exact failing commands for any blockers.

## 14. What would count as good G5.50 progress?

Good but not deployable:

```text
G5.49 true regions replicate on fresh random-100-2000 seeds;
neighbor transfer remains weak;
generator still fails but failure mode is clear;
iteration-level counterfactual labels look predictive.
```

Very good:

```text
true safe-gain replicates and transfers to at least one neighbor stratum;
a safe mixture or bounded residual policy passes offline;
targeted replay runs and beats static_flow_shield with zero success regression.
```

Exceptional but still not final:

```text
targeted and blind replay both pass on fresh seeds;
learned non-static theta usage is nontrivial;
static_flow_shield is beaten safely in multiple unique strata;
AAAI gates remain closed pending a separate promotion and paper-grade validation plan.
```
