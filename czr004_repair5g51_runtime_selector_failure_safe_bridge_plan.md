# czr004 Repair5G.5.1 Plan: Runtime Selector Failure Autopsy, Safe Learned-Abstention Bridge, and Counterfactual UpdateLTM Labels

**Branch:** `phase4f5p5-stable-attention-lau`  
**Start after commit:** `0f6566a Add Repair5G.5 runtime selector validation`  
**Status:** proposed next diagnostic research wave after Repair5G.5 runtime selector integration smoke failed  
**Promotion status:** `phase5p5_allowed=false`, `phase6_allowed=false`  
**AAAI status:** `aaai_ready=false`  
**Main project objective:** use learning-enhanced `UpdateLTM` to replace the coarse additive update in the LTM paper and eventually beat `LaCAM*+plain additive LTM` under closed-loop solver metrics, without changing LaCAM*/PIBT semantics.

---

## 0. Executive interpretation

Repair5G.5 is a **mixed result**:

```text
Good:
  Runtime selector integration exists.
  Selector logs are present.
  Allowed/forbidden feature policy passed.
  Semantic parity mismatch count is 0.
  Solver crashes are 0.
  Schema errors are 0.
  AAAI quality-gate documents were added.
  The branch correctly did not touch learned-runtime final IDs 166..205.

Bad:
  The learned runtime selector failed observed-ID smoke.
  It was worse than plain LTM:
    better / equal / worse = 8 / 27 / 23
    mean_delta_ratio_vs_ltm = +0.00350549546894118
  It was dramatically worse than static/map-agent flow-shield:
    repair5g2_best_frozen_static_candidate mean = -0.02232529495036001
    repair5g2_frozen_static_or_selector mean = -0.026533959629559997
  The original runtime selector was also worse than random/shuffled diagnostics:
    random_feature_diagnostic mean = -0.020724342164560004
    shuffled_label_diagnostic mean = -0.020724342164560004
  disable_policy_compliant=false
  force_additive_policy_compliant=false
  runtime_smoke_gates_passed=false
  no frozen learned runtime selector was produced.
  no learned-runtime fresh validation was run.
```

This is **not** evidence against goal-aware dual-channel LTM or flow-shield. It is evidence against the current **offline-to-runtime selector transfer**.

Preserve the current scientific interpretation:

```text
Flow-shield representation:
  still strong and validated by G2/G4.

Static/map-agent flow-shield:
  still the reliable runtime candidate.

G5 runtime selector:
  failed smoke and must not be used for fresh IDs.

AAAI direction:
  still possible, but only after a learned runtime selector beats or safely matches static/map-agent flow-shield under clean smoke and fresh validation.

Immediate next step:
  do not run IDs 166..205.
  do not train a larger neural net blindly.
  first perform runtime selector failure autopsy and build a safe learned-abstention bridge.
```

---

## 1. Working failure hypothesis

The most likely failure is **label/feature granularity mismatch**.

The exported decision stump is:

```text
selector_name = decision_stump_selector
feature = ltm_iterations
threshold = 2.5
left_method = repair5g_dual_c_equiv_c100_b100_w100_d090
right_method = repair5g2_best_frozen_static_candidate
fallback_static = repair5g2_best_frozen_static_candidate
```

This is dangerous because:

```text
1. Offline bridge metrics were based on run-level method outcomes.
2. Runtime selector is invoked inside the LTM update loop, using per-update iteration context.
3. The meaning of `ltm_iterations` in offline rows may not match the meaning at runtime.
4. If early iterations select weak C-equiv and only later iterations select flow-shield,
   then the selector suppresses exactly the early flow-shield updates that created the G2/G4 gains.
5. In the smoke split, static/map-agent flow-shield is very strong on maze/random,
   while the runtime selector is weak or harmful there.
```

Example observed smoke pattern:

```text
maze-50:
  static/map-agent flow-shield mean ≈ -0.0297
  runtime learned selector mean ≈ +0.0003

maze-100:
  map-agent flow-shield mean ≈ -0.0276
  runtime learned selector mean ≈ +0.0085

random-100:
  map-agent flow-shield mean ≈ -0.0512
  runtime learned selector mean ≈ +0.0120
```

Interpretation:

```text
The runtime hook probably works mechanically,
but the learned rule is choosing the wrong candidate at the wrong time.
```

A secondary failure is **policy-control compliance**:

```text
disable_policy_compliant=false
force_additive_policy_compliant=false
```

Even with semantic mismatch count 0, this must be repaired or explained before any learned final validation.

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
- claim AAAI-ready
- run learned-runtime final IDs 166..205 until a corrected selector passes smoke and is frozen
- hide the G5 runtime selector failure
- train a larger neural network before diagnosing the runtime/offline mismatch
```

Allowed:

```text
- project-owned runtime-selector bug fixes
- selector-policy logging and autopsy
- safe selector export
- observed-ID smoke on already observed IDs only
- offline and observed-ID counterfactual UpdateLTM probe dataset construction
- small interpretable learned-abstention selector
- later small neural selector only after the safe bridge is validated
```

---

## 3. Split policy after G5

Observed:

```text
IDs 1..25      support/training
IDs 26..45     G1/G2 development
IDs 46..65     G2 fresh final
IDs 66..105    G3 broader/protocol diagnostic
IDs 106..115   possible G3.1 diagnostic sentinel; audit before reuse
IDs 126..165   G4 clean validation; G5 smoke used 126..135
```

Reserved:

```text
IDs 166..205:
  still reserved for learned-runtime fresh validation.
  Do not touch unless corrected selector passes observed-ID smoke and is frozen.

If any 166..205 were touched locally:
  move learned-runtime final holdout to next clean range 206..245.
```

G5.1 may use observed IDs:

```text
Runtime failure autopsy:
  IDs 126..135 from G5 smoke
  IDs 136..145 or 146..165 for additional observed-ID smoke if needed

Counterfactual/iteration diagnostics:
  observed IDs only, preferably 1..165
```

---

## 4. Required work

## P0. Documentation and decision hygiene

Add this plan to repo root:

```text
czr004_repair5g51_runtime_selector_failure_safe_bridge_plan.md
```

Update:

```text
docs/codex-worklog.md
```

Write:

```text
outputs/reports/phase5p5_repair5g5_final_interpretation.md
outputs/reports/phase5p5_repair5g51_protocol_overview.md
```

`phase5p5_repair5g5_final_interpretation.md` must state:

```text
- G5 runtime integration exists and is auditable.
- Runtime learned selector failed observed-ID smoke.
- The failure is selector/policy transfer failure, not a flow-shield representation failure.
- Static/map-agent flow-shield remains strong.
- Random/shuffled diagnostics were much stronger than the learned runtime selector.
- No frozen learned selector was produced.
- No fresh learned-runtime validation was run.
- IDs 166..205 remain reserved.
- AAAI-ready remains false.
- phase5p5_allowed=false and phase6_allowed=false remain closed.
```

Update AAAI artifacts:

```text
outputs/reports/phase5p5_repair5g_aaai_readiness_audit.md
outputs/reports/phase5p5_repair5g_aaai_readiness_summary.json
outputs/tables/phase5p5_repair5g_aaai_evidence_matrix.csv
outputs/tables/phase5p5_repair5g_claim_ledger.csv
docs/aaai_quality_requirements.md
deep-research-report.md
phase4_6_laur_ltm_codex_execution_plan.md
```

Required AAAI status correction:

```text
runtime_selector_integration = passed
runtime_selector_smoke = failed
learned_runtime_selector_performance = failed
learned_runtime_fresh_holdout = blocked_not_run
aaai_ready = false
static_flow_shield = strong_baseline_not_learned_claim
advanced_neural_network_stage = blocked_until_safe_runtime_selector_or_counterfactual_labels
```

## P1. Runtime selector failure autopsy

Implement:

```text
scripts/analyze_repair5g5_runtime_selector_failure.py
```

Inputs:

```text
outputs/reports/phase5p5_repair5g5_decision.md
outputs/reports/phase5p5_repair5g5_runtime_smoke_summary.json
outputs/reports/phase5p5_repair5g5_runtime_contextual_selector_spec.json
outputs/reports/phase5p5_repair5g5_runtime_smoke_audit.md
outputs/tables/phase5p5_repair5g5_runtime_smoke_paired.csv
outputs/tables/phase5p5_repair5g5_runtime_smoke_summary.csv
outputs/tables/phase5p5_repair5g5_runtime_smoke_by_map_agent.csv
outputs/logs/phase5p5_repair5g5_runtime_smoke/phase5p5_repair5g5_runtime_smoke_ltm_updates.jsonl
outputs/logs/phase5p5_repair5g5_runtime_smoke/phase5p5_repair5g5_runtime_smoke.jsonl
```

Outputs:

```text
outputs/reports/phase5p5_repair5g5_runtime_selector_failure_autopsy.md
outputs/reports/phase5p5_repair5g5_runtime_selector_failure_autopsy_summary.json
outputs/tables/phase5p5_repair5g5_selector_decision_distribution.csv
outputs/tables/phase5p5_repair5g5_selector_iteration_distribution.csv
outputs/tables/phase5p5_repair5g5_selector_vs_static_regret_cases.csv
outputs/tables/phase5p5_repair5g5_runtime_feature_drift.csv
outputs/tables/phase5p5_repair5g5_control_policy_failures.csv
outputs/tables/phase5p5_repair5g5_bad_stump_failure_cases.csv
```

Required analysis:

```text
1. Which candidates did the runtime selector actually choose?
2. How often did it choose:
     repair5g_dual_c_equiv_c100_b100_w100_d090
     repair5g2_best_frozen_static_candidate
     additive / fallback
3. Distribution by:
     map
     agents
     instance_id
     LTM iteration index
     success/failure
4. Compare per-case:
     runtime selector
     best frozen static
     map-agent selector
     random-feature diagnostic
     shuffled-label diagnostic
5. Quantify regret:
     runtime selector ratio - static ratio
     runtime selector ratio - map-agent ratio
     runtime selector ratio - best available smoke candidate ratio
6. Identify if the bad rule is mostly:
     early-iteration C-equiv overuse
     warehouse fallback issue
     map/agent misclassification
     selector spec export bug
     C++ candidate alias bug
     feature default/missing-value bug
7. Reconcile:
     offline decision_stump mean = -0.025178...
     runtime decision_stump mean = +0.003505...
   This reconciliation is mandatory.
8. Explain why random/shuffled diagnostics matched static flow-shield while the learned selector failed.
9. Explain disable/force-additive compliance failures.
```

If logs are missing because ignored/uncommitted, write a clear "raw log unavailable" section and compute what can be computed from committed tables.

## P2. Runtime hook sanity selectors

Before learning again, verify that the runtime hook can reproduce known safe policies.

Implement:

```text
scripts/export_repair5g51_sanity_selectors.py
scripts/run_repair5g51_runtime_hook_sanity.py
```

Export selector specs:

```text
always_static_flow_shield:
  always returns repair5g2_best_frozen_static_candidate

always_map_agent_selector:
  returns repair5g2_frozen_static_or_selector or its map-agent choices

always_additive:
  returns repair5g_dual_c_equiv_additive or canonical additive

bad_g5_stump:
  original G5 decision stump, kept as negative control
```

Run on observed IDs only:

```text
maps = random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
agents = 50, 100
instance_ids = 136..145
time_limit_sec = 3.0
ltm_max_iterations = 4
```

Methods:

```text
lacam_star_ltm
repair5g2_best_frozen_static_candidate
repair5g2_frozen_static_or_selector
repair5g51_runtime_always_static_flow_shield
repair5g51_runtime_always_map_agent_selector
repair5g51_runtime_always_additive_selector
repair5g51_runtime_bad_g5_stump
controls:
  always_additive_defer
  repair5f_candidate_additive_ltm
  laur_disable
  laur_force_additive_direct
  repair5g_dual_additive_parity
  repair5g_dual_c_equiv_additive
```

Outputs:

```text
outputs/reports/phase5p5_repair5g51_runtime_hook_sanity_report.md
outputs/reports/phase5p5_repair5g51_runtime_hook_sanity_summary.json
outputs/tables/phase5p5_repair5g51_runtime_hook_sanity_paired.csv
outputs/tables/phase5p5_repair5g51_runtime_hook_sanity_summary.csv
outputs/tables/phase5p5_repair5g51_runtime_hook_sanity_by_map_agent.csv
outputs/logs/phase5p5_repair5g51_runtime_hook_sanity/...
```

Gate:

```text
always_static_flow_shield matches or policy-equivalent matches static baseline
always_map_agent_selector matches or policy-equivalent matches map-agent baseline
always_additive matches additive/dual-additive baseline under parity policy
bad_g5_stump remains classified as failed or weak
selector logs present
candidate selection distribution matches expected policy
semantic parity mismatch count = 0
```

If sanity selectors fail, stop and fix runtime integration before learning.

## P3. Fix force-additive / disable policy compliance

The G5 smoke had:

```text
disable_policy_compliant=false
force_additive_policy_compliant=false
```

This must be repaired or formally classified.

Implement:

```text
scripts/analyze_repair5g5_policy_control_failures.py
scripts/run_repair5g51_policy_control_reproducer.py
```

If the issue is C++ runtime mapping, modify only project-owned code:

```text
cpp/tools/phase1a_batch.cpp
cpp/ltm/**
```

Expected behavior:

```text
repair5g5_contextual_flow_shield_selector_force_additive_parity:
  uses canonical additive UpdateParams and no learned selector effect.

repair5g5_contextual_flow_shield_selector_disable:
  maps to plain lacam_star_ltm / laur-disable equivalent and should not alter update rules.

repair5g5_contextual_flow_shield_selector_runtime:
  selector active.

repair5g5_contextual_flow_shield_selector_shadow:
  logs selector decisions while executing safe static baseline, if implemented.
```

Outputs:

```text
outputs/reports/phase5p5_repair5g51_policy_control_reproducer_report.md
outputs/reports/phase5p5_repair5g51_policy_control_reproducer_summary.json
outputs/tables/phase5p5_repair5g51_policy_control_reproducer_cases.csv
```

Gate:

```text
force_additive_policy_compliant = true
disable_policy_compliant = true
semantic_parity_mismatch_count = 0
```

If strict wall-clock differences remain, classify under existing parity policy; do not call exact parity restored unless it is exact.

## P4. Safe learned-abstention selector

Do not reuse the failed G5 stump. Build a safer selector whose default is the validated flow-shield baseline.

Implement:

```text
scripts/tune_repair5g51_safe_abstention_selector.py
scripts/export_repair5g51_safe_abstention_selector.py
```

Policy family:

```text
default:
  repair5g2_frozen_static_or_selector
or:
  repair5g2_best_frozen_static_candidate

allowed abstentions:
  additive / dual C-equiv additive
  repair5g2_c_equiv_best_frozen_baseline

allowed only if learned risk margin is high:
  C-equiv non-additive fallback

forbidden in first safe selector:
  choosing weak C-equiv in early iterations solely from ltm_iterations
  choosing any candidate not validated by G2/G4
  selecting from the entire 36-candidate flow-shield lattice at runtime
```

Selectors to test offline and in observed smoke:

```text
safe_static_default
safe_map_agent_default
safe_warehouse_abstention
safe_risk_abstention_tree
safe_margin_abstention_tree
bad_g5_stump_negative_control
random_feature_safe_abstention_diagnostic
shuffled_label_safe_abstention_diagnostic
```

Required offline gates:

```text
safe_selector_mean_delta_ratio_vs_ltm < -0.010
safe_selector_not_worse_than_static_by_more_than_0.001
safe_selector_ratio_worse_than_ltm_groups = 0
safe_selector_success_worse_than_ltm_groups = 0
safe_selector_beats_bad_g5_stump = true
safe_selector_uses_no_forbidden_features = true
safe_selector_default_is_validated_flow_shield = true
```

Export:

```text
artifacts/models/laur_ltm/repair5g51_safe_abstention_selector/selector_spec.json
artifacts/models/laur_ltm/repair5g51_safe_abstention_selector/export_manifest.json
outputs/reports/phase5p5_repair5g51_safe_abstention_selector_report.md
outputs/reports/phase5p5_repair5g51_safe_abstention_selector_summary.json
```

## P5. Safe selector observed-ID runtime smoke

Only if P2/P3/P4 pass.

Run:

```text
maps = random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
agents = 50, 100
instance_ids = 146..165
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

repair5g2_best_frozen_static_candidate
repair5g2_frozen_static_or_selector

repair5g5_contextual_flow_shield_selector_runtime  # bad original negative control
repair5g51_runtime_always_static_flow_shield
repair5g51_safe_abstention_selector_runtime
repair5g51_safe_abstention_selector_shadow_static
repair5g51_safe_abstention_selector_random_feature_diagnostic
repair5g51_safe_abstention_selector_shuffled_label_diagnostic
```

Outputs:

```text
outputs/reports/phase5p5_repair5g51_safe_selector_runtime_smoke_report.md
outputs/reports/phase5p5_repair5g51_safe_selector_runtime_smoke_summary.json
outputs/reports/phase5p5_repair5g51_safe_selector_runtime_smoke_audit.md
outputs/tables/phase5p5_repair5g51_safe_selector_runtime_smoke_paired.csv
outputs/tables/phase5p5_repair5g51_safe_selector_runtime_smoke_summary.csv
outputs/tables/phase5p5_repair5g51_safe_selector_runtime_smoke_by_map_agent.csv
outputs/tables/phase5p5_repair5g51_safe_selector_decision_log.csv
```

Gate:

```text
runtime_rows_full = true
missing_rows = 0
schema_errors = 0
solver_crash_count = 0
semantic_parity_mismatch_count = 0
selector_logs_present = true
allowed_feature_policy_passed = true
forbidden_feature_policy_passed = true
force_additive_policy_compliant = true
disable_policy_compliant = true

safe_selector_mean_delta_ratio_vs_ltm < -0.010
safe_selector_prob_mean_lt_0 >= 0.99
safe_selector_ratio_worse_than_ltm_groups = 0
safe_selector_success_worse_than_ltm_groups = 0
safe_selector_not_worse_than_static_by_more_than_0.0015 = true
safe_selector_beats_bad_g5_stump = true

Do not require safe selector to beat static.
First goal is safe learned runtime behavior.
```

If safe selector only matches static, decision should be:

```text
safe_runtime_bridge_passed_learning_advantage_unclear
```

not AAAI-ready.

## P6. Counterfactual UpdateLTM label dataset

To make later neural models meaningful, build a proper **iteration-level counterfactual label** dataset. This is the bridge toward a real advanced neural architecture.

Implement:

```text
scripts/create_repair5g51_iteration_context_dataset.py
scripts/run_repair5g51_counterfactual_update_probe.py
scripts/analyze_repair5g51_counterfactual_label_quality.py
```

Use observed IDs only:

```text
IDs 1..165
```

Candidate set:

```text
repair5g2_best_frozen_static_candidate
repair5g2_frozen_static_or_selector
repair5g_dual_c_equiv_additive
repair5g2_c_equiv_best_frozen_baseline
top 2 flow-shield static candidates
additive fallback
```

Context source:

```text
iteration checkpoints / update logs / LtmUpdateContext summaries
```

Labeling strategy:

```text
For each sampled pre-update context:
  replay or reconstruct current traffic_before + trace_events if available;
  apply candidate UpdateParams;
  evaluate a short one-shot / next-iteration probe if supported;
  otherwise record that true counterfactual labels are unavailable.

Do not invent labels from final full-run outcomes if they are not causally tied to the update context.
```

Outputs:

```text
outputs/tables/phase5p5_repair5g51_iteration_contexts.csv
outputs/tables/phase5p5_repair5g51_counterfactual_update_labels.csv
outputs/reports/phase5p5_repair5g51_counterfactual_label_quality.md
outputs/reports/phase5p5_repair5g51_counterfactual_label_quality_summary.json
```

Gate:

```text
counterfactual_context_count > 0
candidate_label_coverage sufficient for at least smoke training
label leakage audit passes
runtime feature availability audit passes
oracle gap over static measured
```

If counterfactual labels are unavailable due to missing traffic snapshots, write a gap report and propose the minimal C++ checkpoint export required.

## P7. Small neural selector only after P5/P6

Do not train a large network in this pass.

If P5 and P6 pass, optionally train a small neural selector:

```text
scripts/train_repair5g51_small_mlp_selector.py
```

Architecture:

```text
input: allowed pre-update context features
normalization: mean/std from training only
hidden: 32 or 64
activation: ReLU
output: candidate logits over safe candidate set
fallback: confidence/margin abstention to static flow-shield
```

Forbidden:

```text
GNN/Transformer in G5.1
action decoder
restart head
priority head
h-value head
candidate deletion head
```

Outputs:

```text
artifacts/models/laur_ltm/repair5g51_small_mlp_selector/
outputs/reports/phase5p5_repair5g51_small_mlp_selector_report.md
outputs/reports/phase5p5_repair5g51_small_mlp_selector_summary.json
```

Gate:

```text
small_mlp_beats_or_matches_safe_selector = true
small_mlp_beats_random_feature_diagnostic = true
small_mlp_beats_shuffled_label_diagnostic = true
small_mlp_uses_no_forbidden_features = true
```

If it does not beat safe selector, keep simple selector and postpone neural architecture.

## P8. Fresh learned-runtime validation remains blocked unless smoke passes

Do not run IDs 166..205 unless:

```text
P2 runtime hook sanity passed
P3 force/disable policy controls passed
P5 safe selector runtime smoke passed
selector frozen before final
```

If those pass, write a frozen spec:

```text
outputs/reports/phase5p5_repair5g51_frozen_safe_runtime_selector_spec.json
outputs/reports/phase5p5_repair5g51_frozen_safe_runtime_selector_report.md
```

Then and only then run:

```text
instance_ids = 166..205
```

If any 166..205 were touched, use next clean range 206..245.

## P9. Final decision

Write:

```text
outputs/reports/phase5p5_repair5g51_decision.md
outputs/reports/phase5p5_repair5g51_decision_summary.json
```

Decision options:

```text
runtime_hook_bug_blocks_learning
policy_control_bug_blocks_learning
safe_runtime_bridge_passed_learning_advantage_unclear
continue_safe_runtime_fresh_validation
continue_counterfactual_label_collection
continue_small_neural_selector
return_to_selector_feature_design
stop_for_protocol_or_semantic_bug
```

Decision must answer:

```text
1. Why did G5 learned runtime selector fail?
2. Did the runtime hook reproduce always-static and map-agent safe policies?
3. Were disable/force-additive policies fixed?
4. Did safe abstention runtime smoke pass?
5. Is learned selection actually adding value over static flow-shield?
6. Are counterfactual UpdateLTM labels available?
7. Is a small neural selector justified?
8. Are IDs 166..205 still clean?
9. What is the next AAAI-relevant step?
```

---

## 5. Validation requirements

Run:

```text
python -m py_compile \
  scripts/analyze_repair5g5_runtime_selector_failure.py \
  scripts/export_repair5g51_sanity_selectors.py \
  scripts/run_repair5g51_runtime_hook_sanity.py \
  scripts/analyze_repair5g5_policy_control_failures.py \
  scripts/run_repair5g51_policy_control_reproducer.py \
  scripts/tune_repair5g51_safe_abstention_selector.py \
  scripts/export_repair5g51_safe_abstention_selector.py \
  scripts/run_repair5g51_safe_selector_runtime_smoke.py \
  scripts/create_repair5g51_iteration_context_dataset.py \
  scripts/run_repair5g51_counterfactual_update_probe.py \
  scripts/analyze_repair5g51_counterfactual_label_quality.py \
  scripts/train_repair5g51_small_mlp_selector.py
```

If C++ changed:

```text
scripts/build_phase1a_batch.ps1
```

Run tests:

```text
pytest if available
otherwise manual fallback harness over all relevant Repair5G.3.1/G4/G5/G5.1 protocol and runtime tests
```

Add tests if runtime selector policy code changes:

```text
tests/test_repair5g51_runtime_hook_sanity.py
tests/test_repair5g51_policy_controls.py
tests/test_repair5g51_safe_selector.py
```

Always run:

```text
git diff --check
```

Commit only G5.1-related tracked files and reports. Leave unrelated dirty/untracked files untouched. Large raw JSONL logs may remain ignored, but committed summaries/manifests must be sufficient.

Commit message:

```text
repair5g: diagnose runtime selector failure and add safe bridge
```

---

# Codex prompt

Continue czr004 on branch `phase4f5p5-stable-attention-lau` after commit `0f6566a Add Repair5G.5 runtime selector validation`.

Goal:
Implement Repair5G.5.1: diagnose why the learned runtime selector failed observed-ID smoke, validate the runtime hook with sanity selectors, repair policy-control compliance, and build a safe learned-abstention bridge for goal-aware flow-shield UpdateLTM. Do not run fresh learned-runtime IDs 166..205 unless a corrected selector passes observed-ID smoke and is frozen.

Main project objective:
Use learning-enhanced `UpdateLTM` to replace the coarse additive update in the LTM paper and eventually beat `LaCAM*+plain additive LTM` under closed-loop solver metrics, without changing LaCAM*/PIBT semantics.

Read first:
```text
deep-research-report.md
phase4_6_laur_ltm_codex_execution_plan.md
docs/aaai_quality_requirements.md
czr004_repair5g5_aaai_learned_flow_shield_runtime_plan.md
outputs/reports/phase5p5_repair5g5_decision.md
outputs/reports/phase5p5_repair5g5_runtime_smoke_report.md
outputs/reports/phase5p5_repair5g5_runtime_smoke_summary.json
outputs/reports/phase5p5_repair5g5_runtime_contextual_selector_spec.json
outputs/reports/phase5p5_repair5g_aaai_readiness_summary.json
outputs/tables/phase5p5_repair5g5_runtime_smoke_paired.csv
outputs/tables/phase5p5_repair5g5_runtime_smoke_summary.csv
outputs/tables/phase5p5_repair5g5_runtime_smoke_by_map_agent.csv
```

Preserve this interpretation:
```text
- G5 runtime selector integration exists and is auditable.
- G5 learned runtime selector failed observed-ID smoke:
    8 / 27 / 23
    mean_delta_ratio_vs_ltm = +0.00350549546894118
    prob_mean_lt_0 = 0.014
    ratio_worse_than_ltm_groups = 2
- Static/map-agent flow-shield remained strong in the same smoke:
    repair5g2_best_frozen_static_candidate mean = -0.02232529495036001
    repair5g2_frozen_static_or_selector mean = -0.026533959629559997
- Random/shuffled diagnostics were also strong:
    mean = -0.020724342164560004
- The failure is not a flow-shield representation failure.
- The likely issue is offline-to-runtime selector transfer / feature-granularity mismatch:
    exported stump uses ltm_iterations threshold 2.5
    left_method = repair5g_dual_c_equiv_c100_b100_w100_d090
    right_method = repair5g2_best_frozen_static_candidate
- disable_policy_compliant=false and force_additive_policy_compliant=false must be repaired or classified.
- No frozen learned runtime selector exists.
- No learned-runtime fresh validation was run.
- IDs 166..205 must remain untouched unless a corrected selector passes observed-ID smoke and is frozen.
- phase5p5_allowed=false, phase6_allowed=false, aaai_ready=false remain mandatory.
```

Do not:
```text
- modify external/lacam2/lacam2/**
- change PIBT, LaCAM*, candidate generation, conflict, pruning, OPEN/EXPLORED, rewrite, incumbent, or restart semantics
- introduce action prediction
- introduce learned restart
- output h_i(v), action logits, priority overrides, or candidate deletion
- claim Phase5.5 or Phase6
- claim AAAI-ready
- run IDs 166..205 before corrected selector smoke passes and selector is frozen
- train a larger neural net before diagnosing the runtime/offline mismatch
- hide the G5 failure
```

Tasks:

1. Add `czr004_repair5g51_runtime_selector_failure_safe_bridge_plan.md` to repo root and update `docs/codex-worklog.md`.

2. Write:
```text
outputs/reports/phase5p5_repair5g5_final_interpretation.md
outputs/reports/phase5p5_repair5g51_protocol_overview.md
```

3. Update AAAI readiness artifacts to mark:
```text
runtime_selector_integration = passed
runtime_selector_smoke = failed
learned_runtime_selector_performance = failed
learned_runtime_fresh_holdout = blocked_not_run
aaai_ready = false
```

4. Implement `scripts/analyze_repair5g5_runtime_selector_failure.py`.

Write:
```text
outputs/reports/phase5p5_repair5g5_runtime_selector_failure_autopsy.md
outputs/reports/phase5p5_repair5g5_runtime_selector_failure_autopsy_summary.json
outputs/tables/phase5p5_repair5g5_selector_decision_distribution.csv
outputs/tables/phase5p5_repair5g5_selector_iteration_distribution.csv
outputs/tables/phase5p5_repair5g5_selector_vs_static_regret_cases.csv
outputs/tables/phase5p5_repair5g5_runtime_feature_drift.csv
outputs/tables/phase5p5_repair5g5_control_policy_failures.csv
outputs/tables/phase5p5_repair5g5_bad_stump_failure_cases.csv
```

5. Implement runtime hook sanity selector export and run:
```text
scripts/export_repair5g51_sanity_selectors.py
scripts/run_repair5g51_runtime_hook_sanity.py
```

Use observed IDs 136..145. Confirm always-static and map-agent runtime selectors reproduce their safe baselines under the parity policy.

6. Fix or classify policy-control compliance:
```text
scripts/analyze_repair5g5_policy_control_failures.py
scripts/run_repair5g51_policy_control_reproducer.py
```

If needed, modify only project-owned runtime code:
```text
cpp/tools/phase1a_batch.cpp
cpp/ltm/**
```

7. Build safe learned-abstention selector:
```text
scripts/tune_repair5g51_safe_abstention_selector.py
scripts/export_repair5g51_safe_abstention_selector.py
```

Safe selector defaults to validated flow-shield and only abstains to additive/C-equiv fallback under high learned risk. It must not select weak C-equiv purely from early `ltm_iterations`.

8. If P2/P3/P4 pass, run safe selector observed-ID smoke on IDs 146..165:
```text
scripts/run_repair5g51_safe_selector_runtime_smoke.py
```

Do not require safe selector to beat static yet. Require it to be safe, non-harmful, and much better than the bad G5 stump.

9. Build counterfactual UpdateLTM label dataset on observed IDs only:
```text
scripts/create_repair5g51_iteration_context_dataset.py
scripts/run_repair5g51_counterfactual_update_probe.py
scripts/analyze_repair5g51_counterfactual_label_quality.py
```

Use this to decide whether small neural selector training is justified.

10. Only if safe smoke and label quality pass, optionally train a small MLP selector:
```text
scripts/train_repair5g51_small_mlp_selector.py
```

No GNN/Transformer yet. No action/restart/priority/h-value heads.

11. Do not run fresh IDs 166..205 unless:
```text
runtime hook sanity passed
policy controls passed
safe selector smoke passed
selector frozen before final
```

12. Write:
```text
outputs/reports/phase5p5_repair5g51_decision.md
outputs/reports/phase5p5_repair5g51_decision_summary.json
```

Decision options:
```text
runtime_hook_bug_blocks_learning
policy_control_bug_blocks_learning
safe_runtime_bridge_passed_learning_advantage_unclear
continue_safe_runtime_fresh_validation
continue_counterfactual_label_collection
continue_small_neural_selector
return_to_selector_feature_design
stop_for_protocol_or_semantic_bug
```

Validation:
```text
py_compile all new/modified Python scripts
if C++ changed, run scripts/build_phase1a_batch.ps1
pytest if available; otherwise manual fallback harness
git diff --check
commit and push only G5.1-related tracked files and reports
leave unrelated dirty/untracked files untouched
```

Commit message:
```text
repair5g: diagnose runtime selector failure and add safe bridge
```
