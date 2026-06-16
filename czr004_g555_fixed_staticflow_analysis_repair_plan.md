# Repair5G.5.55 Plan — Fixed Global StaticFlow Analysis-Gate Repair + Candidate Validation

Project: `czr004`
Branch: `codex/g531-slice-pilot`
Start point: after G5.54 commit `a584fa0` (`repair5g: finish g554 fixed staticflow replay`)
Round name: `Repair5G.5.55 fixed-global static_flow analysis repair and validation`

---

## 0. Executive interpretation

G5.54 should **not** be treated as a clean scientific negative for fixed global `static_flow_shield` coefficient optimization.

It ran substantial fresh replay:

```text
Stage1 fresh screening:
  stage1_new_solver_rows = 260096
  candidate_vectors_screened = 3000
  contexts = 1016
  zero_regression_candidates = 2933
  low_regression_high_gain_candidates = 1090
  stage1_validation_ready_candidates = 0

Stage2 near-miss expansion:
  stage2_new_solver_rows = 360013
  candidate_vectors_expanded = 170
  contexts = 2081
  best_candidate_id = g554_c00894
  best_candidate_success_regressions_vs_static_flow = 0
  best_candidate_quality_delta_vs_static_flow = -0.0315924946469
  stage2_validation_shortlist_count = 0
```

The suspicious part is that the Stage2 best candidate appears to satisfy the scientific promotion intuition:

```text
candidate_id = g554_c00894
candidate_rows = 2081
success_regression_count_vs_static_flow = 0
success_gain_count_vs_static_flow = 3
both_success_quality_pairs_vs_static_flow = 2078
both_success_quality_delta_mean_vs_static_flow = -0.0315924946469
bootstrap_ci_upper = -0.0298130815132
better_count_vs_static_flow = 1607
worse_count_vs_static_flow = 329
support_strata = 140
support_seed_blocks = 200
fingerprint_match_rate = 1
candidate_recognized_all = true
cost_finite_all = true
theta_in_bounds_all = true
```

Yet it was marked:

```text
shortlist_ready = false
not_ready_reason = materialization_gate_not_met
```

That is internally inconsistent because the same row says:

```text
fingerprint_match_rate = 1
candidate_recognized_all = true
cost_finite_all = true
theta_in_bounds_all = true
```

There is also a strong clue of an analysis bug:

```text
success_regression_count_vs_static_flow = 0
success_gain_count_vs_static_flow = 3
but
success_rate_delta_vs_static_flow = -0.998558385392
```

A candidate with zero success regressions and three success gains should not have a success-rate delta of approximately `-1`.

The likely issue is an analysis/schema mismatch in `leaderboard_from_results`:

```python
candidate_success = sum(1 for row in group if boolish(row.get("contender_success")))
static_success = sum(1 for row in group if boolish(row.get("baseline_success")))
success_rate_delta = (candidate_success - static_success) / max(1, len(group))
```

Past paired tables use fields such as:

```text
selected_success
baseline_success
success_regression
success_gain
both_success
```

If the pair rows in G5.54 do not contain `contender_success`, then `candidate_success` becomes zero for every candidate, producing fake huge negative success-rate deltas. The downstream `not_ready_reason` also labels anything that passes quality/support but fails the final readiness condition as `materialization_gate_not_met`, even when the actual blocker is success-rate-delta computation.

Therefore G5.55 is not a new broad search round. It is a **source-of-truth analysis repair and validation round**.

Primary hypothesis:

```text
G5.54 may have produced at least one fixed global coefficient vector that should
have entered validation, but a leaderboard/gate computation bug blocked it.
```

G5.55 must answer:

```text
After correcting pair schema and readiness gates, does any G5.54 fixed global
candidate pass Stage2 shortlist and fresh validation against current hand
static_flow_shield?
```

---

## 1. Scientific decision

Continue fixed global static_flow coefficient route for this round.

Do **not** switch back to dynamic learned UpdateParams policy yet.

Reason:

```text
G5.54 fresh replay produced suspiciously strong fixed-global candidate evidence.
The first priority is to repair analysis and validate candidates, not to abandon
the fixed-global line or resume dynamic policy.
```

Dynamic learned policy remains paused:

```text
contextual selector: paused
checkpoint policy: paused
abstention policy: paused
per-context theta generator: paused
Label-v2 dynamic policy training: paused
runtime learned policy: paused
```

Candidate object remains:

```text
one deterministic global fixed static_flow_shield coefficient vector
```

It is not allowed to depend on map, agents, seed, budget, horizon, checkpoint, trace, or runtime context.

---

## 2. Non-negotiable baseline and claims

Primary baseline:

```text
current C++-materialized hand static_flow_shield
candidate_id = repair5g59_static_flow_shield
```

Paper/parity floor and diagnostic safety baseline:

```text
additive_ltm
```

Diagnostic baselines:

```text
frozen_family_static_goal_aware
best_fixed_static_goal_aware
family_static variants
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

Even if a fixed vector passes validation/blind, it is only a stronger fixed baseline candidate, not a dynamic learned policy claim.

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

Before coding, append:

```markdown
## 2026-06-15 - Repair5G.5.55 fixed-global staticflow analysis-gate repair

- Request:
  Continue after G5.54 commit a584fa0. Do not resume dynamic learned policy yet. G5.54 ran a large fresh fixed-global search: 260,096 Stage1 rows and 360,013 Stage2 rows. The final decision kept hand static_flow_shield, but the Stage2 leaderboard contains suspicious candidate evidence: best candidate g554_c00894 has 0 success regressions, 3 success gains, mean quality delta -0.0315924946469, CI upper -0.0298130815132, better_count 1607 vs worse_count 329, support_strata 140, support_seed_blocks 200, fingerprint=1, recognized=true, cost_finite=true, yet shortlist_ready=false with not_ready_reason=materialization_gate_not_met.

- Interpretation:
  This is likely an analysis/gate schema bug, not a clean fixed-global negative. The leaderboard appears to compute candidate_success from `contender_success`, while pair rows use selected/candidate success fields. This can create fake success_rate_delta near -1 even when regressions=0 and gains>0. G5.55 must repair pair schema, recompute Stage1/Stage2 leaderboards from raw results, and only then decide whether fixed global coefficients failed.

- Baseline:
  Primary baseline remains current C++ hand static_flow_shield. additive_ltm remains paper/parity floor and diagnostic safety floor. Dynamic learned policy remains paused.

- Constraints:
  No external/lacam2/lacam2 edits, no solver semantic changes, no dynamic policy, no selector, no checkpoint policy, no abstention gate, no per-context theta, no IDs 166..205, no Phase5.5/Phase6/runtime/AAAI claims.
```

Update governance docs only if baseline/SafeGate wording changes:

```text
deep-research-report.md
docs/aaai_quality_requirements.md
docs/goal_aware_dual_channel_ltm_research_strategy.md
phase4_6_laur_ltm_codex_execution_plan.md
```

Required governance statement:

```text
G5.55 keeps dynamic learned UpdateParams policy paused and audits G5.54 fixed-global staticflow results. Because G5.54 Stage2 contains candidate rows with zero regressions and strong quality gains but inconsistent readiness labels, G5.55 treats the G5.54 no-promotion decision as analysis-confounded until pair-schema and shortlist gates are repaired. Current hand static_flow_shield remains primary unless corrected validation/blind replay promotes a fixed global vector.
```

---

## 4. Required files

Create:

```text
czr004_g555_fixed_staticflow_analysis_repair_plan.md

scripts/repair5g555_common.py
scripts/verify_repair5g555_g554_artifacts.py
scripts/audit_repair5g555_pair_schema_and_gate_bug.py
scripts/recompute_repair5g555_stage1_stage2_leaderboards.py
scripts/create_repair5g555_corrected_validation_plan.py
scripts/run_repair5g555_corrected_validation.py
scripts/analyze_repair5g555_corrected_validation.py
scripts/create_repair5g555_blind_if_warranted.py
scripts/run_repair5g555_blind_if_warranted.py
scripts/analyze_repair5g555_blind_if_warranted.py
scripts/write_repair5g555_decision.py
```

Outputs:

```text
outputs/reports/phase5p5_repair5g555_*
outputs/tables/phase5p5_repair5g555_*
outputs/logs/phase5p5_repair5g555_*
```

Do not commit raw CSVs >50MB. Commit compact summaries, leaderboards, previews, hashes, manifests, exact resume commands.

---

## 5. Stage A — Verify G5.54 artifacts

Create:

```text
scripts/verify_repair5g555_g554_artifacts.py
```

Inputs:

```text
outputs/reports/phase5p5_repair5g554_decision_summary.json
outputs/reports/phase5p5_repair5g554_stage0b_smoke_summary.json
outputs/reports/phase5p5_repair5g554_stage1_fresh_screening_summary.json
outputs/reports/phase5p5_repair5g554_stage2_nearmiss_expansion_summary.json
outputs/reports/phase5p5_repair5g554_validation_summary.json
outputs/tables/phase5p5_repair5g554_stage2_candidate_leaderboard.csv
outputs/tables/phase5p5_repair5g554_stage2_candidate_by_stratum.csv
outputs/tables/phase5p5_repair5g554_stage2_validation_shortlist.csv
outputs/logs/phase5p5_repair5g554_stage1_fresh_screening/stage1_fresh_screening_results.csv
outputs/logs/phase5p5_repair5g554_stage2_nearmiss_expansion/stage2_nearmiss_expansion_results.csv
```

If raw result CSVs are not present locally, use the compact package or exact server path manifest. If raw rows are missing and cannot be recomputed, write a blocker with exact missing files.

Write:

```text
outputs/reports/phase5p5_repair5g555_g554_verification.md
outputs/reports/phase5p5_repair5g555_g554_verification_summary.json
outputs/tables/phase5p5_repair5g555_g554_artifact_audit.csv
outputs/tables/phase5p5_repair5g555_g554_claim_flag_audit.csv
```

Required checks:

```text
g554_decision = g554_no_fixed_global_candidate_after_fresh_search_keep_hand_baseline
stage1_new_solver_rows = 260096
stage2_new_solver_rows = 360013
stage2_best_candidate_id = g554_c00894
stage2_best_candidate_regressions = 0
stage2_best_candidate_delta = -0.0315924946469
validation_new_solver_rows = 0
dynamic_learned_policy_paused = true
all claim flags closed
external_lacam2_clean = true
```

---

## 6. Stage B — Pair schema and gate bug audit

Create:

```text
scripts/audit_repair5g555_pair_schema_and_gate_bug.py
```

This is the most important stage.

Write:

```text
outputs/reports/phase5p5_repair5g555_pair_schema_gate_bug_audit.md
outputs/reports/phase5p5_repair5g555_pair_schema_gate_bug_audit_summary.json
outputs/tables/phase5p5_repair5g555_pair_schema_columns.csv
outputs/tables/phase5p5_repair5g555_success_field_mapping_audit.csv
outputs/tables/phase5p5_repair5g555_stage2_leaderboard_inconsistency_audit.csv
outputs/tables/phase5p5_repair5g555_not_ready_reason_audit.csv
```

Audit raw pair schema:

```text
Does pair row contain selected_success?
Does pair row contain contender_success?
Does pair row contain candidate_success?
Does pair row contain baseline_success?
Does pair row contain success_regression?
Does pair row contain success_gain?
Does pair row contain both_success?
```

For every Stage2 candidate, compute three versions:

```text
success_rate_delta_from_selected_baseline =
  (sum(selected_success) - sum(baseline_success)) / pair_rows

success_rate_delta_from_gain_regression =
  (success_gain_count - success_regression_count) / pair_rows

success_rate_delta_from_existing_g554 =
  existing leaderboard success_rate_delta_vs_static_flow
```

Required consistency:

```text
If success_regression_count = 0 and success_gain_count > 0,
then success_rate_delta_from_gain_regression > 0.

If existing_g554_delta is near -1 in this case,
mark g554_success_rate_delta_bug = true.
```

Audit `not_ready_reason`:

```text
If fingerprint_match_rate = 1,
candidate_recognized_all = true,
cost_finite_all = true,
theta_in_bounds_all = true,
but not_ready_reason = materialization_gate_not_met,
then mark not_ready_reason_misclassified = true.
```

Expected likely outcome:

```text
g554_leaderboard_success_rate_delta_bug = true
g554_not_ready_reason_misclassified = true
g554_no_promotion_decision_analysis_confounded = true
```

If this expected outcome is not found, document why.

---

## 7. Stage C — Corrected leaderboard recomputation

Create:

```text
scripts/recompute_repair5g555_stage1_stage2_leaderboards.py
```

Do not run new solver rows in this stage. Recompute from raw Stage1/Stage2 results.

Write:

```text
outputs/reports/phase5p5_repair5g555_corrected_leaderboard.md
outputs/reports/phase5p5_repair5g555_corrected_leaderboard_summary.json
outputs/tables/phase5p5_repair5g555_stage1_corrected_candidate_leaderboard.csv
outputs/tables/phase5p5_repair5g555_stage2_corrected_candidate_leaderboard.csv
outputs/tables/phase5p5_repair5g555_stage2_corrected_validation_shortlist.csv
outputs/tables/phase5p5_repair5g555_stage2_corrected_by_stratum.csv
outputs/tables/phase5p5_repair5g555_corrected_failure_cases.csv
```

Correct readiness gate:

```text
success_regression_count_vs_static_flow = 0
success_rate_delta_vs_static_flow >= 0
candidate_rows >= 2000
support_strata >= 6
support_seed_blocks >= 12
both_success_quality_delta_mean_vs_static_flow <= -0.001
bootstrap_ci_upper <= 0
better_count_vs_static_flow > worse_count_vs_static_flow
fulltheta_fingerprint_match_rate = 1
candidate_recognized_all = true
cost_finite_all = true
theta_in_bounds_all = true
```

Use corrected success-rate delta:

```text
success_rate_delta_vs_static_flow =
  (success_gain_count_vs_static_flow - success_regression_count_vs_static_flow)
  / pair_rows

or equivalent selected_success - baseline_success if both fields exist.
```

Do not use missing `contender_success` silently.

For each top corrected candidate, report:

```text
candidate_id
theta vector
candidate_family
support_strata
support_seed_blocks
pair_rows
regressions
gains
mean_delta
CI upper
better/worse
distance_from_current_static_flow
goal_projection_mode
active field deltas
```

If corrected shortlist count > 0, proceed to validation.

If corrected shortlist count = 0, write a true fixed-global negative for this round and do not run validation.

---

## 8. Stage D — Corrected validation plan

Create:

```text
scripts/create_repair5g555_corrected_validation_plan.py
```

Only if corrected shortlist exists.

Validate at most:

```text
top_candidates_to_validate <= 10
```

Prioritize:

```text
1. g554_c00894 if corrected shortlist-ready
2. top zero-regression candidates with strongest CI-bounded quality gain
3. candidates closest to current hand static_flow
4. candidates using flow_shield mode if any
5. candidates with agent_progress/none mode as diagnostic but label clearly
```

Important:

```text
If top candidates use goal_projection_mode_agent_progress or none,
do not call them static_flow_shield replacements without an explicit naming note.
They are still fixed global UpdateParams candidates, but may not be "flow_shield" variants.
Report this distinction.
```

Write:

```text
outputs/reports/phase5p5_repair5g555_corrected_validation_plan.md
outputs/reports/phase5p5_repair5g555_corrected_validation_plan_summary.json
outputs/tables/phase5p5_repair5g555_validation_plan_preview.csv
outputs/tables/phase5p5_repair5g555_validation_candidate_theta.csv
```

Raw validation plan:

```text
outputs/logs/phase5p5_repair5g555_validation/validation_plan.csv
```

Validation minimum:

```text
new_validation_solver_rows >= 120000
preferred >= 240000 if local/server remains stable
candidate_rows_per_candidate >= 10000
fresh heldout seeds
fresh heldout scenario hashes
random/maze primary
warehouse diagnostic
nominal_budget_ms in {2000, 1000, 500}
short_budget_ms in {1000, 2000, 5000}
base_time_limit_sec in {0.5, 1.0}
ltm_max_iterations in {2, 4}
```

---

## 9. Stage E — Corrected validation run and analysis

Create:

```text
scripts/run_repair5g555_corrected_validation.py
scripts/analyze_repair5g555_corrected_validation.py
```

Write:

```text
outputs/reports/phase5p5_repair5g555_corrected_validation.md
outputs/reports/phase5p5_repair5g555_corrected_validation_summary.json
outputs/tables/phase5p5_repair5g555_validation_candidate_leaderboard.csv
outputs/tables/phase5p5_repair5g555_validation_by_stratum.csv
outputs/tables/phase5p5_repair5g555_validation_vs_additive_diagnostic.csv
outputs/tables/phase5p5_repair5g555_validation_failure_cases.csv
```

Validation pass:

```text
success_regression_count_vs_static_flow = 0
success_rate_delta_vs_static_flow >= 0
both_success_quality_delta_mean_vs_static_flow <= -0.001
bootstrap_ci_upper <= 0
better_count > worse_count
candidate_recognized_all = true
fulltheta_fingerprint_match_rate = 1
cost_finite_all = true
theta_in_bounds_all = true
```

Additive diagnostics:

```text
success_regression_count_vs_additive
success_gain_count_vs_additive
quality_delta_vs_additive
whether candidate worsens or improves hand static_flow's additive safety profile
```

If validation fails, keep hand static_flow primary.

If validation passes, proceed to blind.

---

## 10. Stage F — Blind replay if warranted

Create:

```text
scripts/create_repair5g555_blind_if_warranted.py
scripts/run_repair5g555_blind_if_warranted.py
scripts/analyze_repair5g555_blind_if_warranted.py
```

Only if validation passes.

Blind:

```text
blind_candidate_count <= 3
new_blind_solver_rows >= 120000
preferred >= 240000
fresh seeds not used in search/validation
no tuning after blind plan generation
```

Blind pass:

```text
success_regression_count_vs_static_flow = 0
success_rate_delta_vs_static_flow >= 0
mean_quality_delta_vs_static_flow <= -0.001
bootstrap_ci_upper <= 0
better_count > worse_count
fingerprint_match_rate = 1
candidate_recognized_all = true
cost_finite_all = true
```

Even if blind passes:

```text
phase5p5_allowed = false
phase6_allowed = false
runtime_claim_allowed = false
learned_runtime_policy_validated = false
aaai_ready = false
```

It is a fixed baseline candidate only.

---

## 11. Stage G — Decision

Create:

```text
scripts/write_repair5g555_decision.py
```

Write:

```text
outputs/reports/phase5p5_repair5g555_decision.md
outputs/reports/phase5p5_repair5g555_decision_summary.json
outputs/tables/phase5p5_repair5g555_claim_ledger.csv
outputs/tables/phase5p5_repair5g555_final_candidate_theta.csv
outputs/tables/phase5p5_repair5g555_large_artifact_manifest.csv
```

Possible decisions:

```text
g555_g554_raw_artifacts_missing_recover_or_rerun
g555_g554_analysis_gate_bug_confirmed_recomputed_shortlist
g555_g554_analysis_gate_bug_not_found_keep_g554_negative
g555_no_corrected_shortlist_keep_hand_staticflow
g555_corrected_validation_failed_keep_hand_staticflow
g555_corrected_blind_failed_keep_hand_staticflow
g555_fixed_global_staticflow_candidate_validated_keep_claims_closed
g555_fixed_global_staticflow_candidate_blind_passed_keep_claims_closed
```

Final summary keys:

```json
{
  "decision": "...",
  "primary_baseline": "current hand static_flow_shield",
  "dynamic_learned_policy_paused": true,
  "g554_analysis_gate_bug_confirmed": false,
  "corrected_stage2_shortlist_count": 0,
  "best_corrected_candidate_id": "",
  "best_corrected_candidate_success_regressions_vs_static_flow": 0,
  "best_corrected_candidate_quality_delta_vs_static_flow": "",
  "validation_run": false,
  "validation_new_solver_rows": 0,
  "validation_passed": false,
  "blind_run": false,
  "blind_passed": false,
  "optimized_fixed_candidate_promoted": false,
  "should_hand_static_flow_remain_primary": true,
  "phase5p5_allowed": false,
  "phase6_allowed": false,
  "runtime_claim_allowed": false,
  "learned_runtime_policy_validated": false,
  "aaai_ready": false
}
```

---

## 12. Local / server commands

Recommended sequence:

```powershell
python scripts/verify_repair5g555_g554_artifacts.py
python scripts/audit_repair5g555_pair_schema_and_gate_bug.py
python scripts/recompute_repair5g555_stage1_stage2_leaderboards.py
python scripts/create_repair5g555_corrected_validation_plan.py
python scripts/run_repair5g555_corrected_validation.py --row-limit 120000 --max-workers 20
python scripts/analyze_repair5g555_corrected_validation.py
python scripts/create_repair5g555_blind_if_warranted.py
python scripts/run_repair5g555_blind_if_warranted.py --row-limit 120000 --max-workers 20
python scripts/analyze_repair5g555_blind_if_warranted.py
python scripts/write_repair5g555_decision.py
```

If raw Stage2 files are only on server, either:

```text
1. fetch compact/raw candidate-pair subsets needed for top candidates, or
2. rerun Stage2 candidate replay for corrected shortlist candidates only, or
3. write exact recovery commands.
```

Do not rerun full Stage1/Stage2 unless raw data cannot be recovered.

---

## 13. Success / failure interpretation

### If bug confirmed and validation passes

Then G5.54 actually found a fixed global candidate, but analysis blocked it. G5.55 may report:

```text
fixed global staticflow candidate validated
hand static_flow remains baseline until blind passes
all claims closed
```

### If bug confirmed but validation fails

Then G5.54 found search-set candidates that did not generalize. This is still useful and stronger than G5.54's current no-shortlist story.

### If no bug found

Then G5.54's negative is stronger. But the audit must explain why zero-regression + quality-gain rows were correctly rejected.

### If raw artifacts missing

Do not infer. Write recovery/rerun commands.

---

## 14. Forbidden shortcuts

Do not:

```text
resume dynamic policy
train a selector
change candidate object
relax zero-regression validation gate
ignore additive diagnostics
promote based only on search-set Stage2
promote a candidate with fingerprint < 1
trust G5.54 shortlist_ready without recomputation
trust not_ready_reason=materialization_gate_not_met without checking actual materialization fields
commit raw CSV > 50MB
```

---

## 15. Main scientific target

G5.55 should answer:

```text
Did G5.54 actually fail to find a fixed global coefficient vector,
or did an analysis/schema bug prevent strong Stage2 candidates from entering validation?
```

If corrected validation finds a candidate, continue fixed global route.

If corrected validation fails, then hand static_flow remains primary and the fixed-global line has a much stronger negative.

Either outcome is valuable.

---

## 16. Completion result

G5.55 found the G5.54 no-promotion decision was analysis-confounded. The pair-schema audit confirmed that the old leaderboard/readiness path used the wrong success field for fixed-global pair rows. Corrected Stage1/Stage2 recomputation produced `82` Stage2 validation-shortlist candidates.

The corrected replay was run on the KCS RTX4090 instance under tmux. Validation completed `120010` new solver rows and passed. Blind replay completed `120000` new solver rows and passed for `g554_c00051`.

Final decision:

```text
g555_fixed_global_staticflow_candidate_blind_passed_keep_claims_closed
```

Promoted fixed baseline candidate:

```text
candidate_id = g554_c00051
success_regression_count_vs_static_flow = 0
success_gain_count_vs_static_flow = 37
success_rate_delta_vs_static_flow = 0.00185
both_success_quality_delta_mean_vs_static_flow = -0.0210143833861
both_success_quality_delta_ci_upper_vs_static_flow = -0.0205820545487
better_count_vs_static_flow = 14244
worse_count_vs_static_flow = 3455
support_strata = 216
support_seed_blocks = 1000
fingerprint_match_rate = 1
```

Baseline governance changed for the fixed-global staticflow route: `g554_c00051` is the stronger fixed baseline candidate, and the previous hand `static_flow_shield` is the beaten comparison baseline. This does not validate a dynamic learned UpdateParams policy, selector, checkpoint policy, or runtime policy. Phase5.5, Phase6, runtime, learned-runtime, and AAAI claims remain closed.
