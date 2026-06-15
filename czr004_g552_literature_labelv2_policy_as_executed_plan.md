# Repair5G.5.52 Plan 鈥?Literature-Grounded Label-v2 + Policy-as-Executed SafeGate Repair for Learned UpdateParams

Project: `czr004`
Branch: `codex/g531-slice-pilot`
Start point: after G5.51 commit `0ab51f8` (`repair5g: finish g551 safegate replay`)
Round name: `Repair5G.5.52 literature-grounded Label-v2 and policy-as-executed SafeGate repair`

---

## 0. Executive interpretation

G5.51 is not a deployable learned UpdateLTM success. It is a strong diagnostic result showing that the current learning pipeline still has a **selector-era label / replay semantics mismatch**.

The key evidence from G5.51 is:

```text
G5.51 final decision:
  g551_targeted_regression_persists_continue_safety_training

Iteration-label expansion:
  new_iteration_counterfactual_solver_rows = 64011
  counterfactual_contexts = 3367
  finite_ratio_rows = 54471
  safe_useful_contexts = 2218
  safe_useful_context_rate = 0.658746658747
  mean_best_oracle_delta_vs_static_flow = -0.0337898984235
  targeted_failure_theta_reproduced = true

Offline checkpoint policy:
  offline_gate_passed = true
  generator_policy_family_best = checkpoint_risk_classifier_utility_ranker_abstention
  policy_families_evaluated = 11
  risk_false_safe_count_on_all_hard_negative_holdouts = 0
  success_regression_rate_predicted_safe = 0
  predicted_safe_utility_mean_delta_vs_static_flow = -0.023971062781
  generated_non_static_theta_usage_rate = 0.18

Fresh targeted replay:
  new_targeted_solver_rows = 60012
  generated_theta_rows = 50010
  both_success_quality_pairs_vs_static_flow = 37842
  success_regression_count_vs_static_flow = 352
  success_regression_count_vs_additive = 300
  quality_only_mean_delta_vs_static_flow = +0.0054865163785
  better_count_vs_static_flow = 14998
  worse_count_vs_static_flow = 17905
  generated_non_static_theta_usage_rate = 0.833333333333
  fulltheta_fingerprint_match_rate = 0.967426514697
  gate_passed = false

Blind replay:
  skipped because targeted gate failed
```

This is a serious failure of the current learned policy. It does **not** invalidate the broader `goal_aware_dual_channel_ltm` direction because the iteration/checkpoint oracle gap is still large. It does indicate that the current pipeline has not yet correctly learned or evaluated a **policy-as-executed** bounded UpdateParams controller.

The central G5.52 hypothesis is:

```text
The project moved from finite candidate selector learning to continuous/bounded
UpdateParams policy learning, but label generation and targeted replay still
retain selector-era semantics.

Therefore the next repair is not "train a bigger model" and not "run another
broad fulltheta sweep." The next repair is Label-v2:
same-checkpoint counterfactual labels + hard-negative forbidden-theta labels +
support-aware abstention + policy-as-executed replay.
```

The primary research question for G5.52 is:

```text
Can literature-grounded Label-v2 and policy-as-executed SafeGate turn the
checkpoint-level oracle signal into a conservative learned UpdateParams policy
that has:
  1. zero success regressions versus static_flow_shield,
  2. zero success regressions versus additive_ltm,
  3. fulltheta_fingerprint_match_rate = 1,
  4. policy-as-executed targeted replay rather than theta-slate replay,
  5. nontrivial but controlled non-static usage,
  6. and at least small positive quality improvement over static_flow_shield?
```

---

## 1. Literature-grounded motivation

G5.52 should explicitly audit recent MAPF / LMAPF learning and guidance-optimization work before implementing new labels. This is not for citation padding; it is to correct the learning target.

### 1.1 Guidance Graph Optimization: optimize guidance parameters through solver outcomes

GGO frames lifelong MAPF guidance as a directed weighted guidance graph and optimizes edge weights. It includes both direct edge-weight optimization and an update model capable of generating edge weights. The official GGO repository is the IJCAI 2024 implementation and includes CMA-ES and PIU/update-model configurations for PIBT on random, warehouse, room, maze, empty, and other maps.

Project lesson for `czr004`:

```text
When learning guidance parameters, the target is not a static selector label.
The target must be solver-facing guidance performance under a defined simulator
or replay protocol.
```

Relevant design implications:

```text
- Keep the guidance layer separate from solver semantics.
- Optimize/label parameters through closed-loop or counterfactual solver outcomes.
- Treat manually designed guidance as a strong baseline, not an obstacle to learning.
- Use update-model style labels when the learned component generates guidance.
- Preserve exact map / agent / horizon / seed provenance.
```

### 1.2 Online GGO: dynamic guidance should depend on traffic patterns

Online guidance optimization for LMAPF focuses on dynamically guiding agents based on real-time traffic patterns and improving PIBT with an optimized guidance policy.

Project lesson:

```text
A learned UpdateLTM policy should be conditioned on checkpoint/traffic/trace
state, not only on map_family/agents/budget or final-run hindsight.
```

G5.51 already moved toward checkpoint labels, but the replay still appears to evaluate generated theta slates rather than actual context-level policy actions. G5.52 must bridge that gap.

### 1.3 CS-PIBT / learning-MAPF shield lesson: learned outputs need a safety shield

Recent MAPF learning results such as CS-PIBT-style work show that simple imitation learning alone may not be sufficient; learned predictions become much stronger when wrapped in a collision/repair shield and compared against strong greedy/PIBT baselines.

Project lesson:

```text
czr004 must not copy action-policy methods, because this project is not allowed
to learn agent actions or PIBT conflict decisions. However, the shield idea is
directly relevant:
  learned UpdateParams must be wrapped in an UpdateParams shield.
```

The UpdateParams shield should include:

```text
- ABSTAIN_TO_STATIC_FLOW fallback;
- forbidden theta list;
- hard-negative rejector;
- support-distance gate;
- fingerprint/cost finite checks;
- additive_ltm and static_flow_shield success floors;
- exact policy-as-executed action logging.
```

### 1.4 MAPF-LNS benchmark lesson: evaluation protocol and executable learned policy matter

The recent LNS benchmark paper and repository emphasize pitfalls such as incorrect baseline performance, lack of unified evaluation settings, and lack of executable models for supervised-learning methods.

Project lesson:

```text
G5.52 must make the learned policy executable in evaluation:
  one context -> one action:
    ABSTAIN_TO_STATIC_FLOW
    or ALLOW_THETA(theta_id)

A generated theta slate is not an executable learned policy.
```

G5.51 likely violated this distinction: offline usage was `0.18`, while targeted usage was `0.833333333333`. This is a large semantic mismatch and must be audited before any new scientific claim.

### 1.5 LaCAM2 / LaCAM* lesson: preserve the search base

LaCAM2 is the upstream LaCAM* base. The project must keep the solver/search/PIBT semantics untouched.

Project lesson:

```text
The learned component must only affect LTM/UpdateParams guidance.
It must not alter:
  agent actions,
  PIBT conflict semantics,
  candidate domain,
  priorities,
  h-values,
  restart,
  OPEN/EXPLORED,
  rewrite,
  incumbent pruning,
  or candidate deletion.
```

### 1.6 Standing literature notes to write into the project docs

G5.52 should append a short note to:

```text
deep-research-report.md
docs/aaai_quality_requirements.md
docs/goal_aware_dual_channel_ltm_research_strategy.md
phase4_6_laur_ltm_codex_execution_plan.md
```

Required governance statement:

```text
G5.52 adopts a literature-grounded Label-v2 interpretation for learned
UpdateParams. Recent guidance-optimization and learning-MAPF work suggests that
continuous guidance policies must be trained and evaluated through solver-facing
counterfactual outcomes, shielded by strong baselines, and replayed as executable
policies. Therefore czr004 no longer treats a fulltheta replay region or generated
theta slate as a learned policy. A learned UpdateParams method must emit exactly
one policy action per context: ABSTAIN_TO_STATIC_FLOW or ALLOW_THETA(theta_id),
with bounded theta materialization, hard-negative safety checks, and zero
success regression versus static_flow_shield and additive_ltm before blind or
runtime claims.
```

---

## 2. Non-negotiable baseline and SafeGate interpretation

The baseline policy is unchanged.

```text
primary baseline:
  static_flow_shield

paper/parity floor:
  additive_ltm

diagnostic baselines:
  frozen_family_static_goal_aware
  best_fixed_static_goal_aware
  family_static variants
```

SafeGate is tightened, not relaxed:

```text
Offline success is not sufficient.
Generated-theta candidate quality is not sufficient.
Fulltheta region hindsight is not sufficient.
A theta slate is not a learned policy.

Promotion requires policy-as-executed fresh targeted replay:
  exactly one action per context:
    ABSTAIN_TO_STATIC_FLOW
    or ALLOW_THETA(theta_id)

Targeted promotion gates:
  success_regression_count_vs_static_flow = 0
  success_regression_count_vs_additive = 0
  fulltheta_fingerprint_match_rate = 1
  candidate_recognized_all = true
  cost_finite_all = true
  static_flow abstention rows do not count as learned gain
  realized targeted non-static usage matches offline action log
  quality delta over non-static both-success rows is negative
  negative controls fail
```

All claim flags remain closed:

```json
{
  "phase5p5_allowed": false,
  "phase6_allowed": false,
  "runtime_claim_allowed": false,
  "learned_runtime_policy_validated": false,
  "aaai_ready": false
}
```

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

Do not use reserved IDs:

```text
166..205
```

---

## 3. Required worklog entry

Before coding, append to `docs/codex-worklog.md`:

```markdown
## 2026-06-15 - Repair5G.5.52 Label-v2 policy-as-executed SafeGate repair

- Request:
  Continue after G5.51 commit 0ab51f8. G5.51 scaled iteration labels and passed
  an offline checkpoint policy gate, but fresh targeted replay failed:
  60,012 targeted rows, 352 success regressions vs static_flow_shield, 300 vs
  additive_ltm, positive/worse quality delta +0.0054865163785, and fingerprint
  match rate only 0.967426514697.

- Interpretation:
  G5.51 is not a deployable learned UpdateLTM success. The likely blocker is not
  absence of oracle signal but a selector-era label/replay mismatch. Offline usage
  was 0.18, while targeted usage was 0.833333333333, suggesting targeted replay
  evaluated a generated theta slate rather than a policy-as-executed action log.

- Literature-grounded repair:
  Recent guidance-optimization and learning-MAPF work suggests that learned
  guidance policies need solver-facing counterfactual labels, strong baseline
  shields, and executable policy evaluation. G5.52 introduces Label-v2:
  same-checkpoint counterfactual labels, hard-negative forbidden theta labels,
  support-aware abstention, and policy-as-executed targeted replay.

- Baseline and SafeGate:
  static_flow_shield remains primary. additive_ltm remains the paper/parity and
  safety floor. Strong static variants remain diagnostics. SafeGate is tightened:
  targeted replay must be policy-as-executed with zero success regressions vs
  static_flow_shield and additive_ltm, fingerprint match rate = 1, and no solver
  semantic changes.

- Constraints:
  No external/lacam2/lacam2 edits, no solver semantic changes, no static selector
  masquerading as learned UpdateLTM, no IDs 166..205, no runtime/Phase5.5/Phase6/
  AAAI claims.
```

---

## 4. Required files

Create:

```text
czr004_g552_literature_labelv2_policy_as_executed_plan.md

scripts/repair5g552_common.py
scripts/verify_repair5g552_g551_artifacts.py
scripts/analyze_repair5g552_literature_label_audit.py
scripts/analyze_repair5g552_g551_raw_consistency.py
scripts/analyze_repair5g552_staticflow_vs_additive_margin.py
scripts/analyze_repair5g552_g551_targeted_regression_autopsy.py
scripts/create_repair5g552_label_v2_schema.py
scripts/create_repair5g552_hard_negative_label_expansion_plan.py
scripts/run_repair5g552_hard_negative_label_expansion.py
scripts/analyze_repair5g552_label_v2_dataset.py
scripts/create_repair5g552_safe_theta_library.py
scripts/train_eval_repair5g552_policy_as_executed_models.py
scripts/create_repair5g552_policy_as_executed_targeted_plan.py
scripts/run_repair5g552_policy_as_executed_targeted.py
scripts/analyze_repair5g552_policy_as_executed_targeted.py
scripts/create_repair5g552_blind_replay_if_warranted.py
scripts/run_repair5g552_blind_replay_if_warranted.py
scripts/analyze_repair5g552_blind_replay_if_warranted.py
scripts/write_repair5g552_decision.py
```

Outputs:

```text
outputs/reports/phase5p5_repair5g552_*
outputs/tables/phase5p5_repair5g552_*
artifacts/models/laur_ltm/repair5g552_*
```

Large raw files:

```text
outputs/logs/phase5p5_repair5g552_*
```

Do not commit files larger than 50 MB. Commit only:

```text
compact summaries
sample previews
policy manifests
sha256 hashes
exact resume commands
large-artifact manifest
```

---

## 5. Stage A 鈥?Verify G5.51 and audit artifact consistency

### A.1 Inputs

Verify the following files from G5.51:

```text
outputs/reports/phase5p5_repair5g551_decision_summary.json
outputs/reports/phase5p5_repair5g551_iteration_label_expansion_summary.json
outputs/reports/phase5p5_repair5g551_checkpoint_policy_summary.json
outputs/reports/phase5p5_repair5g551_generated_theta_targeted_summary.json
outputs/reports/phase5p5_repair5g551_targeted_failure_autopsy_summary.json

outputs/tables/phase5p5_repair5g551_policy_family_eval.csv
outputs/tables/phase5p5_repair5g551_generated_theta_candidates.csv
outputs/tables/phase5p5_repair5g551_generated_theta_targeted_by_stratum.csv
outputs/tables/phase5p5_repair5g551_generated_theta_targeted_failure_cases.csv
outputs/tables/phase5p5_repair5g551_iteration_oracle_gap_by_stratum.csv
outputs/tables/phase5p5_repair5g551_iteration_hard_negative_cases.csv
outputs/tables/phase5p5_repair5g551_iteration_safe_useful_cases.csv
```

### A.2 Outputs

Write:

```text
outputs/reports/phase5p5_repair5g552_g551_verification.md
outputs/reports/phase5p5_repair5g552_g551_verification_summary.json
outputs/reports/phase5p5_repair5g552_g551_raw_consistency_audit.md
outputs/reports/phase5p5_repair5g552_g551_raw_consistency_summary.json
outputs/tables/phase5p5_repair5g552_g551_artifact_audit.csv
outputs/tables/phase5p5_repair5g552_summary_field_consistency.csv
outputs/tables/phase5p5_repair5g552_claim_flag_audit.csv
```

### A.3 Required consistency checks

Check and report:

```text
decision_summary.decision == g551_targeted_regression_persists_continue_safety_training
targeted_summary.decision == g551_targeted_regression_persists_continue_safety_training
targeted_summary.new_targeted_solver_rows == 60012
targeted_summary.success_regression_count_vs_static_flow == 352
targeted_summary.success_regression_count_vs_additive == 300
targeted_summary.quality_only_mean_delta_vs_static_flow == 0.0054865163785
targeted_summary.fulltheta_fingerprint_match_rate == 0.967426514697
targeted_summary.generated_non_static_theta_usage_rate == 0.833333333333
checkpoint_policy_summary.generated_non_static_theta_usage_rate == 0.18
checkpoint_policy_summary.offline_gate_passed == true
iteration_summary.new_iteration_counterfactual_solver_rows == 64011
iteration_summary.mean_best_oracle_delta_vs_static_flow == -0.0337898984235
```

Also audit the G5.51 autopsy inconsistency:

```text
G5.51 autopsy summary contains a field targeted_success_regression_count_vs_static_flow.
If it disagrees with final/targeted summary, mark:
  g551_autopsy_summary_field_inconsistent = true
and do not use that field for downstream science.
```

The consistency report must answer:

```text
1. Which summary fields are authoritative?
2. Are raw targeted failure rows consistent with 352 static_flow regressions?
3. Are additive regressions consistent with 300?
4. Are all claim flags closed?
5. Are any committed compact summaries empty or misleading?
6. Is fingerprint mismatch localized to certain theta IDs or contexts?
```

If summary/raw consistency fails, decision should be:

```text
g552_blocked_g551_artifact_consistency_repair_required
```

unless the script can repair derived summaries from raw logs without modifying raw evidence.

---

## 6. Stage B 鈥?Literature and label-generation audit

Create:

```text
scripts/analyze_repair5g552_literature_label_audit.py
```

Write:

```text
outputs/reports/phase5p5_repair5g552_literature_label_audit.md
outputs/reports/phase5p5_repair5g552_literature_label_audit_summary.json
outputs/tables/phase5p5_repair5g552_literature_to_design_mapping.csv
outputs/tables/phase5p5_repair5g552_label_v1_vs_label_v2_conceptual_diff.csv
```

The report must include a table:

| Source family | Lesson | G5.52 design change |
|---|---|---|
| Guidance Graph Optimization | guidance parameters should be optimized/evaluated through solver outcomes | use same-checkpoint counterfactual labels, not selector labels |
| Online GGO | guidance can depend on traffic patterns | include traffic_before / trace_window / checkpoint features |
| CS-PIBT-style learning MAPF | learned outputs need shields and strong baselines | UpdateParams shield, forbidden theta, ABSTAIN_TO_STATIC_FLOW |
| MAPF-LNS benchmark | fair baselines and executable learned policies matter | policy-as-executed replay, static_flow vs additive margin |
| LaCAM2/LaCAM* | preserve search/PIBT semantics | only UpdateLTM guidance layer is learnable |

Required conclusion:

```text
Label-v1 is insufficient for continuous/bounded UpdateParams because it treats
theta candidates like selector actions. Label-v2 must separate safety,
abstention, support, and utility; utility labels are only valid after safety
labels pass.
```

---

## 7. Stage C 鈥?StaticFlow vs Additive baseline margin audit

This is required because the user asked whether static_flow already has a large gain over additive LTM.

Create:

```text
scripts/analyze_repair5g552_staticflow_vs_additive_margin.py
```

Write:

```text
outputs/reports/phase5p5_repair5g552_staticflow_vs_additive_margin.md
outputs/reports/phase5p5_repair5g552_staticflow_vs_additive_margin_summary.json
outputs/tables/phase5p5_repair5g552_staticflow_vs_additive_by_stratum.csv
outputs/tables/phase5p5_repair5g552_staticflow_vs_additive_by_horizon.csv
outputs/tables/phase5p5_repair5g552_staticflow_vs_additive_failure_cases.csv
```

Use all available G5.49/G5.50/G5.51 paired baseline rows where both `static_flow_shield` and `additive_ltm` are materialized under the same:

```text
map
map_family
agents
seed
nominal_budget_ms
horizon_id
short_budget_ms
base_time_limit_sec
ltm_max_iterations
traffic_before_hash if available
```

Required metrics:

```text
paired_rows
both_success_rows
static_flow_success_rate
additive_success_rate
success_gain_count_static_over_additive
success_regression_count_static_vs_additive
mean_ratio_static_flow
mean_ratio_additive
absolute_delta_static_minus_additive
relative_improvement_pct = (additive_mean - static_mean) / additive_mean * 100
median_delta
bootstrap_CI_95
by_map_family
by_agents
by_budget
by_horizon
```

Required answers:

```text
1. Is static_flow_shield stronger than additive_ltm on the current calibrated local evidence?
2. Is the margin >= 1%?
3. Is the margin concentrated in random/maze/warehouse, 50/100 agents, or 2000ms budgets?
4. How large must a learned theta improvement over static_flow be to be scientifically meaningful?
5. Do any strata show static_flow weaker than additive_ltm?
```

Do not allow learned policy reports to omit this baseline margin. If the learned method only beats additive but not static_flow, classify:

```text
paper_floor_only_not_learned_update_success
```

---

## 8. Stage D 鈥?G5.51 targeted regression autopsy v2

Create:

```text
scripts/analyze_repair5g552_g551_targeted_regression_autopsy.py
```

Write:

```text
outputs/reports/phase5p5_repair5g552_g551_targeted_regression_autopsy_v2.md
outputs/reports/phase5p5_repair5g552_g551_targeted_regression_autopsy_v2_summary.json
outputs/tables/phase5p5_repair5g552_g551_regressions_by_stratum.csv
outputs/tables/phase5p5_repair5g552_g551_regressions_by_theta.csv
outputs/tables/phase5p5_repair5g552_g551_regressions_by_seed_block.csv
outputs/tables/phase5p5_repair5g552_g551_regressions_by_horizon.csv
outputs/tables/phase5p5_repair5g552_g551_regressions_by_policy_action.csv
outputs/tables/phase5p5_repair5g552_g551_fingerprint_mismatch_audit.csv
outputs/tables/phase5p5_repair5g552_g551_usage_shift_audit.csv
outputs/tables/phase5p5_repair5g552_g551_regression_theta_neighborhoods.csv
```

Required checks:

```text
1. Count the 352 static_flow regressions by:
   - map_family
   - agents
   - nominal_budget_ms
   - horizon_id
   - short_budget_ms
   - base_time_limit_sec
   - ltm_max_iterations
   - seed_block
   - selected_candidate
   - theta cluster / nearest G5.49 region
   - fingerprint match / mismatch status

2. Count the 300 additive regressions similarly.

3. Report mean quality delta and better/worse counts separately for:
   - all targeted rows
   - static_flow both-success rows only
   - non-static rows only
   - abstention/static_flow rows only
   - fingerprint-matched rows only
   - fingerprint-mismatched rows only

4. Explain usage mismatch:
   - offline_non_static_usage = 0.18
   - targeted_non_static_usage = 0.833333333333
   - realized_usage_delta = 0.653333333333
   - identify whether targeted evaluated all generated theta candidates rather than policy actions.

5. Explain fingerprint mismatch:
   - fulltheta_fingerprint_match_rate = 0.967426514697
   - count mismatched theta IDs
   - count mismatched contexts
   - list fields mismatched
   - mark all mismatched theta as forbidden.

6. Identify policy execution bug if present:
   - candidate table contains ABSTAIN probability but target plan still runs theta
   - theta slate replay is not equivalent to policy-as-executed replay
```

If the autopsy finds policy-as-executed mismatch, the decision should not blame model architecture first. It should write:

```text
g551_targeted_replay_semantics_confounded_by_theta_slate_usage
```

as a component diagnosis.

---

## 9. Stage E 鈥?Define Label-v2 schema

Create:

```text
scripts/create_repair5g552_label_v2_schema.py
```

Write:

```text
outputs/reports/phase5p5_repair5g552_label_v2_schema.md
outputs/reports/phase5p5_repair5g552_label_v2_schema_summary.json
outputs/tables/phase5p5_repair5g552_label_v2_field_manifest.csv
outputs/tables/phase5p5_repair5g552_label_v2_decision_rules.csv
```

### E.1 Training unit

The Label-v2 training unit is:

```text
same context
same checkpoint
same traffic_before
same trace_window
same horizon
same short probe budget

compare:
  static_flow_shield
  additive_ltm
  candidate bounded theta
  optional family_static diagnostic
```

Required identifiers:

```text
context_id
checkpoint_id
checkpoint_iteration
map
map_family
agents
seed
nominal_budget_ms
horizon_id
short_budget_ms
base_time_limit_sec
ltm_max_iterations
traffic_before_hash
trace_window_hash
update_checkpoint_hash
candidate_id
theta_fingerprint
theta_params
```

### E.2 Required outcome fields

```text
static_flow_success
additive_success
candidate_success
family_static_success_optional

static_flow_ratio
additive_ratio
candidate_ratio
family_static_ratio_optional

candidate_minus_static_ratio_delta
candidate_minus_additive_ratio_delta

success_regression_vs_static_flow
success_regression_vs_additive
success_gain_vs_static_flow
success_gain_vs_additive
both_success_vs_static_flow
both_success_vs_additive
both_fail_vs_static_flow
```

### E.3 Required safety fields

```text
fingerprint_match
candidate_recognized
cost_finite_all
cost_within_bounds_all
theta_in_bounds
theta_in_safe_library
theta_in_forbidden_library
support_distance_to_safe_positive
support_distance_to_hard_negative
near_hard_negative
out_of_distribution_context
```

### E.4 Required label heads

```text
hard_negative_success_regression_vs_static_flow
hard_negative_success_regression_vs_additive
hard_negative_fingerprint_or_cost
hard_negative_out_of_support

safe_candidate
useful_candidate
safe_useful_candidate
quality_gain_candidate
quality_worse_candidate

forbidden_theta
abstain_to_static_flow
allow_theta

risk_score_label
utility_score_label
support_score_label
policy_action_label
```

### E.5 Label-v2 decision rules

Hard safety rules:

```python
if not candidate_recognized:
    forbidden_theta = 1
    allow_theta = 0

if fingerprint_match != 1:
    forbidden_theta = 1
    allow_theta = 0

if not cost_finite_all or not cost_within_bounds_all:
    forbidden_theta = 1
    allow_theta = 0

if success_regression_vs_static_flow:
    forbidden_theta = 1
    hard_negative_success_regression_vs_static_flow = 1
    allow_theta = 0

if success_regression_vs_additive:
    forbidden_theta = 1
    hard_negative_success_regression_vs_additive = 1
    allow_theta = 0

if near_hard_negative and support_distance_to_safe_positive is weak:
    abstain_to_static_flow = 1
    allow_theta = 0
```

Utility is only evaluated after safety:

```python
if safety_pass and both_success_vs_static_flow:
    utility_score_label = static_flow_ratio - candidate_ratio
    useful_candidate = utility_score_label >= utility_margin

if safety_pass and useful_candidate:
    safe_useful_candidate = 1
```

Policy action label:

```python
if no safe_useful_candidate in context:
    policy_action_label = ABSTAIN_TO_STATIC_FLOW
elif safety_confidence < threshold:
    policy_action_label = ABSTAIN_TO_STATIC_FLOW
elif support_distance_to_hard_negative <= hard_negative_radius:
    policy_action_label = ABSTAIN_TO_STATIC_FLOW
else:
    policy_action_label = ALLOW_THETA(best_safe_useful_theta_id)
```

Margins to sweep:

```text
utility_margin_abs in {0.0005, 0.001, 0.0025, 0.005, 0.01}
hard_negative_radius quantiles in {0.01, 0.02, 0.05, 0.10}
risk_threshold in {0.0001, 0.0005, 0.001, 0.0025, 0.005}
support_threshold in {p50, p75, p90, p95}
```

---

## 10. Stage F 鈥?Hard-negative Label-v2 expansion plan

Create:

```text
scripts/create_repair5g552_hard_negative_label_expansion_plan.py
```

Write:

```text
outputs/reports/phase5p5_repair5g552_hard_negative_label_expansion_plan.md
outputs/reports/phase5p5_repair5g552_hard_negative_label_expansion_plan_summary.json
outputs/tables/phase5p5_repair5g552_label_expansion_plan_preview.csv
outputs/tables/phase5p5_repair5g552_label_expansion_context_breakdown.csv
outputs/tables/phase5p5_repair5g552_label_expansion_theta_family_breakdown.csv
```

Full raw plan:

```text
outputs/logs/phase5p5_repair5g552_label_expansion/label_expansion_plan.csv
```

### F.1 Required context sources

Oversample:

```text
1. G5.51 static_flow regressions:
   - all 352 regression contexts if scenario availability allows
   - all 300 additive regression contexts if available

2. G5.50 regressions:
   - all 216 static_flow regression contexts

3. Failure-neighbor seeds:
   - same map_family / agents / horizon
   - seeds within same seed_block and adjacent seed blocks

4. High-risk strata:
   - maze, agents 100, nominal_budget_ms 2000
   - random, agents 100, nominal_budget_ms 2000
   - all G5.51 horizons where regressions occurred

5. Low-regression but quality-bad strata:
   - random, agents 50, nominal_budget_ms 2000
   - cases with zero regression but positive/worse quality delta

6. Positive safe-useful contexts:
   - from G5.51 iteration safe_useful cases
   - from G5.50 active true/safe regions
   - from G5.49 true safe-gain regions, only as weak prior, not as promotion evidence

7. Diagnostics:
   - maze 50 / random 50 / random 100 / maze 100 transfer
   - warehouse long-horizon diagnostics, nonblocking
```

### F.2 Required theta candidate families

Include:

```text
static_flow_shield baseline
additive_ltm baseline
family_static diagnostic

G5.51 failed theta IDs
G5.51 failed theta local neighbors
G5.50 failed theta IDs
G5.49 true-region theta examples
G5.50 active best-region theta
conservative shrinkage around static_flow
bounded residuals around static_flow
safe expert mixture centroids
hard-negative boundary probes
negative random/Sobol theta controls
fingerprint stress controls
```

### F.3 Row targets

Local PC heavy but feasible:

```text
hard minimum:
  new_label_v2_solver_rows >= 128000
  hard_negative_contexts >= 500
  safe_positive_contexts >= 1000
  candidate_theta_per_context >= 16

preferred:
  new_label_v2_solver_rows >= 256000
  hard_negative_contexts >= 1000
  safe_positive_contexts >= 2000
  candidate_theta_per_context >= 24

stretch if stable:
  new_label_v2_solver_rows >= 400000
  hard_negative_contexts >= 1500
  safe_positive_contexts >= 3000
```

Run with resumable chunks:

```bash
python scripts/run_repair5g552_hard_negative_label_expansion.py --row-limit 64000 --max-workers 16
python scripts/run_repair5g552_hard_negative_label_expansion.py --row-limit 128000 --max-workers 16
python scripts/run_repair5g552_hard_negative_label_expansion.py --row-limit 256000 --max-workers 20
```

Do not block the whole round if local PC cannot reach preferred target. But if below hard minimum, decision must be:

```text
g552_label_v2_expansion_underpowered_continue
```

---

## 11. Stage G 鈥?Run and analyze Label-v2 dataset

Create:

```text
scripts/run_repair5g552_hard_negative_label_expansion.py
scripts/analyze_repair5g552_label_v2_dataset.py
```

Write:

```text
outputs/reports/phase5p5_repair5g552_label_v2_dataset.md
outputs/reports/phase5p5_repair5g552_label_v2_dataset_summary.json
outputs/tables/phase5p5_repair5g552_label_v2_dataset_sample.csv
outputs/tables/phase5p5_repair5g552_label_v2_by_stratum.csv
outputs/tables/phase5p5_repair5g552_label_v2_by_theta_family.csv
outputs/tables/phase5p5_repair5g552_label_v2_hard_negative_cases.csv
outputs/tables/phase5p5_repair5g552_label_v2_safe_useful_cases.csv
outputs/tables/phase5p5_repair5g552_label_v2_forbidden_theta_cases.csv
outputs/tables/phase5p5_repair5g552_label_v2_support_distance_stats.csv
outputs/tables/phase5p5_repair5g552_label_v1_vs_label_v2_overlap.csv
outputs/tables/phase5p5_repair5g552_label_v2_feature_leakage_audit.csv
```

Required summary metrics:

```text
new_label_v2_solver_rows
contexts
finite_ratio_rows
both_success_pairs_vs_static_flow
hard_negative_success_regression_vs_static_flow_rows
hard_negative_success_regression_vs_additive_rows
safe_useful_candidate_rows
forbidden_theta_rows
abstain_label_rate
allow_theta_label_rate
fingerprint_mismatch_rows
cost_invalid_rows
support_distance_available_rate
feature_leakage_found
candidate_recognized_all
fulltheta_fingerprint_match_rate
```

Required answer:

```text
How many G5.51 ALLOW_THETA candidates become forbidden under Label-v2?
```

This is critical. If a large fraction of G5.51 ALLOW_THETA candidates are forbidden under Label-v2, the diagnosis is:

```text
selector_era_labeling_caused_false_safe_theta_actions
```

---

## 12. Stage H 鈥?Safe theta library and forbidden theta list

Create:

```text
scripts/create_repair5g552_safe_theta_library.py
```

Write:

```text
outputs/reports/phase5p5_repair5g552_safe_theta_library.md
outputs/reports/phase5p5_repair5g552_safe_theta_library_summary.json
outputs/tables/phase5p5_repair5g552_safe_theta_library.csv
outputs/tables/phase5p5_repair5g552_forbidden_theta_list.csv
outputs/tables/phase5p5_repair5g552_theta_support_intervals.csv
outputs/tables/phase5p5_repair5g552_theta_neighbor_risk.csv
outputs/tables/phase5p5_repair5g552_theta_library_by_stratum.csv
```

A theta is forbidden if any of the following occurs:

```text
ever success regression vs static_flow_shield on hard-negative holdout
ever success regression vs additive_ltm on hard-negative holdout
fingerprint mismatch
candidate not recognized
non-finite cost
cost outside configured bounds
repeated quality worsening in both-success rows
near hard-negative support boundary without strong safe-positive support
```

A theta may enter safe library only if:

```text
fingerprint_match_rate = 1
candidate_recognized_all = true
hard_negative_regression_count_vs_static_flow = 0
hard_negative_regression_count_vs_additive = 0
cost_finite_all = true
minimum safe-positive support met
support not concentrated in one seed only
not merely static baseline ID
```

Safe library should include:

```text
theta_id
theta_params
support_strata
safe_positive_support
hard_negative_support
support_distance_threshold
utility_mean
utility_CI
forbidden_reason if forbidden
```

---

## 13. Stage I 鈥?Train policy-as-executed models

Create:

```text
scripts/train_eval_repair5g552_policy_as_executed_models.py
```

Write:

```text
outputs/reports/phase5p5_repair5g552_policy_as_executed_training.md
outputs/reports/phase5p5_repair5g552_policy_as_executed_summary.json
outputs/reports/phase5p5_repair5g552_policy_failure_modes.md
outputs/tables/phase5p5_repair5g552_policy_feature_manifest.csv
outputs/tables/phase5p5_repair5g552_policy_feature_leakage_audit.csv
outputs/tables/phase5p5_repair5g552_policy_family_eval.csv
outputs/tables/phase5p5_repair5g552_policy_threshold_sweep.csv
outputs/tables/phase5p5_repair5g552_policy_calibration_curves.csv
outputs/tables/phase5p5_repair5g552_policy_oof_predictions_sample.csv
outputs/tables/phase5p5_repair5g552_policy_action_log_offline.csv
outputs/tables/phase5p5_repair5g552_policy_generated_theta_candidates.csv
artifacts/models/laur_ltm/repair5g552_model_manifest.json
```

### I.1 Feature restrictions

Allowed runtime-available pre-update features:

```text
map_family
agents
nominal_budget_ms
short_budget_ms
base_time_limit_sec
ltm_max_iterations
iteration index
traffic snapshot summary before update
trace window counts:
  committed
  blocked
  wait
  progress
  nonprogress
  conflict categories
dual-channel current summary:
  congestion nonzero
  flow nonzero
  max raw counts
  topk edge stats
rank/audit aggregate features if available before update
static_flow predicted status features only if computed before candidate theta outcome
support-distance features computed from training safe/negative libraries
```

Forbidden leakage features:

```text
candidate outcome in same replay row
candidate ratio
candidate success
static_flow ratio after candidate replay
oracle best label from same context as feature
future solver outcome
baseline success from same fresh targeted context if unavailable at runtime
seed ID as a direct continuous feature unless bucketed only for split auditing
candidate_id one-hot as the primary learned action
```

### I.2 Policy families to evaluate

Evaluate at least 10 policy families:

```text
1. abstain_first_hard_negative_rejector
2. risk_classifier_then_utility_ranker
3. conformal_risk_bound_abstention_policy
4. ensemble_disagreement_abstention_policy
5. support_distance_knn_abstention_policy
6. map_agent_horizon_calibrated_threshold_policy
7. safe_theta_library_selector
8. bounded_residual_shrinkage_policy
9. two_stage_success_risk_then_quality_policy
10. conservative_bandit_policy_as_executed
11. random_feature_negative_control
12. shuffled_label_negative_control
13. random_theta_negative_control
14. static_only_selector_like_invalid_control
```

### I.3 Required policy output format

Every policy must output an action log:

```text
context_key
checkpoint_key
policy_family
policy_action  # ABSTAIN_TO_STATIC_FLOW or ALLOW_THETA
selected_theta_id
selected_theta_fingerprint
abstain_probability
risk_score
risk_upper_bound
utility_score
support_distance_to_safe
support_distance_to_hard_negative
reason_code
```

Allowed actions:

```text
ABSTAIN_TO_STATIC_FLOW
ALLOW_THETA(theta_id)
```

Forbidden actions:

```text
additive_ltm as learned action
static_flow_shield as learned action
best_fixed_static_goal_aware as learned action
frozen_family_static_goal_aware as learned action
multiple theta slate actions for same context
```

Fallback to static_flow is allowed only via:

```text
policy_action = ABSTAIN_TO_STATIC_FLOW
```

### I.4 Usage caps

Do not start with 18% or 83% non-static usage. Sweep conservative caps:

```text
usage_cap:
  0.005
  0.01
  0.02
  0.05
  0.10  # diagnostic only after strict caps pass
```

Each cap must have a separate offline action log and targeted replay plan.

### I.5 Offline gate

A policy can enter targeted replay only if:

```text
feature_leakage_found = false
negative_controls_do_not_pass = true
candidate_recognized_all = true
fulltheta_fingerprint_match_rate = 1
selected_theta_all_in_safe_library = true
selected_theta_none_in_forbidden_list = true
hard_negative_false_safe_count_vs_static_flow = 0
hard_negative_false_safe_count_vs_additive = 0
success_regression_rate_upper_confidence_bound <= configured threshold
offline_non_static_usage <= usage_cap
offline_non_static_usage >= min_usage_for_cap
policy_action_log_exists = true
one_action_per_context = true
```

If no policy passes, decision:

```text
g552_label_v2_offline_policy_not_safe_continue_label_design
```

---

## 14. Stage J 鈥?Policy-as-executed targeted replay plan

Create:

```text
scripts/create_repair5g552_policy_as_executed_targeted_plan.py
```

Write:

```text
outputs/reports/phase5p5_repair5g552_policy_as_executed_targeted_plan.md
outputs/reports/phase5p5_repair5g552_policy_as_executed_targeted_plan_summary.json
outputs/tables/phase5p5_repair5g552_targeted_plan_preview.csv
outputs/tables/phase5p5_repair5g552_targeted_policy_action_breakdown.csv
outputs/tables/phase5p5_repair5g552_targeted_expected_usage_by_stratum.csv
```

Raw plan:

```text
outputs/logs/phase5p5_repair5g552_policy_as_executed_targeted/targeted_plan.csv
```

This plan must be policy-as-executed:

```text
For each context:
  if policy_action == ABSTAIN_TO_STATIC_FLOW:
      run static_flow_shield as selected policy action
      count as abstention row
      do not count quality improvement as learned theta gain

  if policy_action == ALLOW_THETA(theta_id):
      run exactly that theta_id
      compare against static_flow_shield and additive_ltm baselines
```

Do **not** run all generated theta candidates per context as if they were policy actions.

Required targeted strata:

```text
G5.51 failure stress:
  maze, 100, 2000
  random, 100, 2000

G5.51 low-regression quality-bad:
  random, 50, 2000

Transfer:
  maze, 50, 2000

Diagnostics:
  warehouse long horizons, nonblocking

Horizon variants:
  short_budget_ms in {1000, 2000, 5000}
  base_time_limit_sec in {0.5, 1.0}
  ltm_max_iterations in {2, 4}
```

Minimum targeted size:

```text
policy_as_executed_targeted_solver_rows >= 60000
fresh_contexts >= 3000
baseline_static_flow_rows >= 10000
baseline_additive_rows >= 10000
ALLOW_THETA rows depend on usage cap
ABSTAIN rows must be explicitly counted
```

Preferred if local PC stable:

```text
policy_as_executed_targeted_solver_rows >= 120000
```

---

## 15. Stage K 鈥?Run and analyze policy-as-executed targeted replay

Create:

```text
scripts/run_repair5g552_policy_as_executed_targeted.py
scripts/analyze_repair5g552_policy_as_executed_targeted.py
```

Write:

```text
outputs/reports/phase5p5_repair5g552_policy_as_executed_targeted.md
outputs/reports/phase5p5_repair5g552_policy_as_executed_targeted_summary.json
outputs/tables/phase5p5_repair5g552_policy_as_executed_targeted_results_sample.csv
outputs/tables/phase5p5_repair5g552_policy_as_executed_vs_static_flow.csv
outputs/tables/phase5p5_repair5g552_policy_as_executed_vs_additive.csv
outputs/tables/phase5p5_repair5g552_policy_as_executed_by_stratum.csv
outputs/tables/phase5p5_repair5g552_policy_as_executed_by_action.csv
outputs/tables/phase5p5_repair5g552_policy_as_executed_failure_cases.csv
outputs/tables/phase5p5_repair5g552_policy_as_executed_usage_realized.csv
outputs/tables/phase5p5_repair5g552_policy_as_executed_abstention_audit.csv
outputs/tables/phase5p5_repair5g552_policy_as_executed_fingerprint_audit.csv
```

### K.1 Targeted gate

Targeted passes only if:

```text
targeted_replay_run = true
policy_as_executed = true
one_action_per_context = true
candidate_recognized_all = true
fulltheta_fingerprint_match_rate = 1
success_regression_count_vs_static_flow = 0
success_regression_count_vs_additive = 0
ALLOW_THETA_success_regression_count_vs_static_flow = 0
ALLOW_THETA_success_regression_count_vs_additive = 0
realized_non_static_usage <= planned_usage_cap + tolerance
realized_non_static_usage >= min_non_static_usage
quality_delta_vs_static_flow_all_policy_rows <= 0
quality_delta_vs_static_flow_ALLOW_THETA_rows <= -0.001
better_count_vs_static_flow_ALLOW_THETA > worse_count_vs_static_flow_ALLOW_THETA
static_flow_abstention_rows_not_counted_as_learned_gain = true
negative_controls_do_not_pass = true
```

Start with strict caps. If `0.5%` cap passes, test `1%`. If `1%` passes, test `2%`. If `2%` passes, test `5%`. If any cap fails with success regression, stop higher caps and report the safe frontier.

If targeted fails, decision should be one of:

```text
g552_policy_as_executed_targeted_success_regression_block
g552_policy_as_executed_fingerprint_block
g552_policy_as_executed_usage_mismatch_block
g552_policy_as_executed_quality_no_gain_continue_label_design
g552_policy_as_executed_zero_regression_low_usage_continue_safe_expansion
```

If targeted passes with zero regressions but low usage, that is still meaningful:

```text
g552_policy_as_executed_zero_regression_low_usage_candidate
```

Do not require large usage in the first successful safety repair. A `0.5%` or `1%` safe learned theta usage rate with negative quality delta is more important than unsafe `18%` usage.

---

## 16. Stage L 鈥?Blind replay if warranted

Create:

```text
scripts/create_repair5g552_blind_replay_if_warranted.py
scripts/run_repair5g552_blind_replay_if_warranted.py
scripts/analyze_repair5g552_blind_replay_if_warranted.py
```

Blind may run only if targeted passes.

Write:

```text
outputs/reports/phase5p5_repair5g552_blind_replay_plan.md
outputs/reports/phase5p5_repair5g552_blind_replay_summary.json
outputs/reports/phase5p5_repair5g552_blind_replay.md
outputs/tables/phase5p5_repair5g552_blind_results_sample.csv
outputs/tables/phase5p5_repair5g552_blind_vs_static_flow.csv
outputs/tables/phase5p5_repair5g552_blind_vs_additive.csv
outputs/tables/phase5p5_repair5g552_blind_by_stratum.csv
outputs/tables/phase5p5_repair5g552_blind_by_action.csv
outputs/tables/phase5p5_repair5g552_blind_failure_cases.csv
```

Blind requirements:

```text
fresh blind seeds not used in G5.49/G5.50/G5.51/G5.52 training
policy frozen before blind plan
policy action log generated before solver outcomes
no threshold changes after blind outcomes
policy_as_executed = true
one action per context
fingerprint_match_rate = 1
success_regression_count_vs_static_flow = 0
success_regression_count_vs_additive = 0
quality_delta_ALLOW_THETA_vs_static_flow <= -0.001
negative controls fail
```

Blind size:

```text
hard minimum:
  blind_solver_rows >= 60000

preferred:
  blind_solver_rows >= 120000
```

If targeted does not pass, write skip artifacts:

```text
g552_blind_skipped_targeted_gate_not_met
```

---

## 17. Stage M 鈥?Final decision and claim ledger

Create:

```text
scripts/write_repair5g552_decision.py
```

Write:

```text
outputs/reports/phase5p5_repair5g552_decision.md
outputs/reports/phase5p5_repair5g552_decision_summary.json
outputs/tables/phase5p5_repair5g552_gate_matrix.csv
outputs/tables/phase5p5_repair5g552_claim_ledger.csv
outputs/tables/phase5p5_repair5g552_large_artifact_manifest.csv
```

Decision taxonomy:

```text
g552_blocked_g551_artifact_consistency_repair_required
g552_label_v2_expansion_underpowered_continue
g552_label_v2_offline_policy_not_safe_continue_label_design
g552_policy_as_executed_targeted_success_regression_block
g552_policy_as_executed_fingerprint_block
g552_policy_as_executed_usage_mismatch_block
g552_policy_as_executed_quality_no_gain_continue_label_design
g552_policy_as_executed_zero_regression_low_usage_candidate
g552_policy_as_executed_targeted_passed_continue_blind
g552_policy_as_executed_blind_failed_continue_safety_training
g552_policy_as_executed_blind_zero_regression_candidate_no_runtime_claim
```

Required final answers:

```text
1. Did G5.51 fail because of label/replay semantics mismatch?
2. Did Label-v2 forbid G5.51 false-safe theta actions?
3. What is the static_flow_shield vs additive_ltm margin?
4. Did any policy-as-executed model pass targeted zero-regression?
5. What non-static usage cap is safe?
6. Did fingerprint match reach exactly 1?
7. Did blind replay run?
8. Is learned runtime policy validated?
9. Are Phase5.5/Phase6/runtime/AAAI flags closed?
10. What is the next scientific step?
```

Claim ledger must explicitly state:

```text
No runtime claim is allowed.
No Phase5.5 claim is allowed.
No Phase6 claim is allowed.
No AAAI-ready claim is allowed.
A zero-regression targeted candidate is a development candidate only.
Static_flow_shield remains the primary baseline.
Additive_ltm remains the paper/parity and safety floor.
Strong static variants remain diagnostics.
```

---

## 18. Validation

Run:

```bash
python -m py_compile \
  scripts/repair5g552_common.py \
  scripts/verify_repair5g552_g551_artifacts.py \
  scripts/analyze_repair5g552_literature_label_audit.py \
  scripts/analyze_repair5g552_g551_raw_consistency.py \
  scripts/analyze_repair5g552_staticflow_vs_additive_margin.py \
  scripts/analyze_repair5g552_g551_targeted_regression_autopsy.py \
  scripts/create_repair5g552_label_v2_schema.py \
  scripts/create_repair5g552_hard_negative_label_expansion_plan.py \
  scripts/run_repair5g552_hard_negative_label_expansion.py \
  scripts/analyze_repair5g552_label_v2_dataset.py \
  scripts/create_repair5g552_safe_theta_library.py \
  scripts/train_eval_repair5g552_policy_as_executed_models.py \
  scripts/create_repair5g552_policy_as_executed_targeted_plan.py \
  scripts/run_repair5g552_policy_as_executed_targeted.py \
  scripts/analyze_repair5g552_policy_as_executed_targeted.py \
  scripts/create_repair5g552_blind_replay_if_warranted.py \
  scripts/run_repair5g552_blind_replay_if_warranted.py \
  scripts/analyze_repair5g552_blind_replay_if_warranted.py \
  scripts/write_repair5g552_decision.py

git diff --check

python -m pytest tests -q
```

If existing unrelated tests fail due to pre-existing missing G5/G5.1 artifacts, report them separately and do not claim they are caused by G5.52.

Also run summary sanity:

```bash
python - <<'PY'
import json
from pathlib import Path
p = Path("outputs/reports/phase5p5_repair5g552_decision_summary.json")
s = json.loads(p.read_text())
assert s["phase5p5_allowed"] is False
assert s["phase6_allowed"] is False
assert s["runtime_claim_allowed"] is False
assert s["learned_runtime_policy_validated"] is False
assert s["aaai_ready"] is False
print(s["decision"])
PY
```

---

## 19. Suggested local execution sequence

Use staged resumable commands:

```bash
python scripts/verify_repair5g552_g551_artifacts.py
python scripts/analyze_repair5g552_literature_label_audit.py
python scripts/analyze_repair5g552_g551_raw_consistency.py
python scripts/analyze_repair5g552_staticflow_vs_additive_margin.py
python scripts/analyze_repair5g552_g551_targeted_regression_autopsy.py

python scripts/create_repair5g552_label_v2_schema.py
python scripts/create_repair5g552_hard_negative_label_expansion_plan.py

python scripts/run_repair5g552_hard_negative_label_expansion.py --row-limit 64000 --max-workers 16
python scripts/analyze_repair5g552_label_v2_dataset.py

python scripts/run_repair5g552_hard_negative_label_expansion.py --row-limit 128000 --max-workers 16
python scripts/analyze_repair5g552_label_v2_dataset.py

python scripts/run_repair5g552_hard_negative_label_expansion.py --row-limit 256000 --max-workers 20
python scripts/analyze_repair5g552_label_v2_dataset.py

python scripts/create_repair5g552_safe_theta_library.py
python scripts/train_eval_repair5g552_policy_as_executed_models.py

python scripts/create_repair5g552_policy_as_executed_targeted_plan.py --usage-cap 0.005
python scripts/run_repair5g552_policy_as_executed_targeted.py --row-limit 60000 --max-workers 20
python scripts/analyze_repair5g552_policy_as_executed_targeted.py

# Only if 0.5% cap passes:
python scripts/create_repair5g552_policy_as_executed_targeted_plan.py --usage-cap 0.01
python scripts/run_repair5g552_policy_as_executed_targeted.py --row-limit 120000 --max-workers 20
python scripts/analyze_repair5g552_policy_as_executed_targeted.py

# Only if targeted passes:
python scripts/create_repair5g552_blind_replay_if_warranted.py
python scripts/run_repair5g552_blind_replay_if_warranted.py --row-limit 60000 --max-workers 20
python scripts/analyze_repair5g552_blind_replay_if_warranted.py

python scripts/write_repair5g552_decision.py
```

---

## 20. Codex short prompt embedded in this MD

```text
Continue czr004 after G5.51 commit 0ab51f8 on branch codex/g531-slice-pilot. Implement Repair5G.5.52 using this MD: Literature-Grounded Label-v2 + Policy-as-Executed SafeGate Repair.

Interpretation: G5.51 is not a deployable learned UpdateLTM success. It scaled iteration labels to 64,011 rows and passed an offline checkpoint policy gate, but fresh targeted replay failed with 352 success regressions vs static_flow_shield, 300 vs additive_ltm, positive/worse quality delta +0.0054865163785, targeted non-static usage 0.8333 despite offline usage 0.18, and fingerprint match only 0.9674. Blind replay correctly stayed closed. This likely indicates a selector-era label/replay mismatch, not absence of UpdateParams oracle signal.

Do not run another broad fulltheta sweep as the main work. First audit G5.51 raw/summary consistency, static_flow vs additive margin, 352 regression anatomy, usage mismatch, and fingerprint mismatch. Then implement Label-v2: same-checkpoint counterfactual labels with safety heads, hard-negative success-regression labels, forbidden theta labels, support-distance abstention, and utility labels only after safety. Build safe theta library and forbidden theta list. Train policy-as-executed models that output exactly one action per context: ABSTAIN_TO_STATIC_FLOW or ALLOW_THETA(theta_id). Do not evaluate a generated theta slate as policy actions.

Use static_flow_shield as primary baseline, additive_ltm as paper/parity and safety floor, strong static variants as diagnostics. SafeGate is tightened: targeted replay must be policy-as-executed, fingerprint match rate exactly 1, candidate recognition true, zero success regressions vs static_flow and additive, realized usage consistent with offline action log, and static_flow abstention rows must not count as learned gain. Start with strict usage caps 0.5%, 1%, 2%, 5%; do not replay another 18% or 83% usage policy first.

Run at least 128k Label-v2 hard-negative/checkpoint solver rows locally if feasible, preferably 256k. Then run at least 60k policy-as-executed targeted rows for the strictest passing usage cap. Run blind replay only if targeted passes. Keep phase5p5_allowed=false, phase6_allowed=false, runtime_claim_allowed=false, learned_runtime_policy_validated=false, aaai_ready=false. Do not touch external/lacam2/lacam2. Do not change solver semantics, PIBT conflict semantics, candidate domain, priorities, h-values, restart, OPEN/EXPLORED, rewrite, incumbent pruning, or candidate deletion. Do not use reserved IDs 166..205. Do not commit raw CSVs larger than 50 MB; use ignored logs and compact summaries/manifests/hashes.
```

---

## 21. References for the literature audit

Use these as source starting points. Do not import external code into `czr004` unless explicitly approved; this stage is for design lessons and protocol alignment.

```text
Guidance Graph Optimization for Lifelong Multi-Agent Path Finding
  arXiv: https://arxiv.org/abs/2402.01446
  GitHub: https://github.com/lunjohnzhang/ggo_public

Online Guidance Graph Optimization for Lifelong Multi-Agent Path Finding
  arXiv: https://arxiv.org/abs/2411.16506

Optimization of Edge Directions and Weights for Mixed Guidance Graphs in Lifelong MAPF
  arXiv: https://arxiv.org/abs/2602.23468

Work Smarter Not Harder: Simple Imitation Learning with CS-PIBT Outperforms Large Scale Imitation Learning for MAPF
  arXiv: https://arxiv.org/abs/2409.14491

Benchmarking Large Neighborhood Search for Multi-Agent Path Finding
  arXiv: https://arxiv.org/abs/2407.09451
  GitHub: https://github.com/ChristinaTan0704/mapf-lns-benchmark

LaCAM2 / LaCAM*
  GitHub: https://github.com/Kei18/lacam2

Where Paths Collide: A Comprehensive Survey of Classic and Learning-Based Multi-Agent Pathfinding
  arXiv: https://arxiv.org/abs/2505.19219
```
