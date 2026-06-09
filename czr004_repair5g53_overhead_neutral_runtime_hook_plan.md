# czr004 Repair5G.5.3 Plan: Overhead-Neutral Runtime Hook, UpdateLTM Transform Equivalence, and Performance/Audit Split

**Branch:** `phase4f5p5-stable-attention-lau`
**Start after commit:** `2e1d30c repair5g: fix updatepolicy equivalence and export counterfactual checkpoints`
**Status:** proposed next diagnostic research wave after G5.2 returned `runtime_updatepolicy_equivalence_failed`
**Promotion status:** `phase5p5_allowed=false`, `phase6_allowed=false`
**AAAI status:** `aaai_ready=false`
**Main project objective:** use learning-enhanced `UpdateLTM` to replace the coarse additive update in the LTM paper and eventually beat `LaCAM*+plain additive LTM` under closed-loop solver metrics, without changing LaCAM*/PIBT semantics.

---

## 0. Executive interpretation

G5.2 is **not a collapse of Repair5G** and **not evidence that goal-aware dual-channel LTM was broken**.

It is a partially successful infrastructure round:

```text
Fixed / improved:
  - Candidate registry and UpdateParams hashes are consistent.
  - Selected runtime params hash matches expected params.
  - Unsupported-candidate / fallback story is no longer the leading suspect.
  - Force-additive and disable policy closure passed in the G5.2 closure sweep.
  - Semantic parity mismatch count is 0.
  - Fixed static and map-agent flow-shield baselines still beat LTM on observed IDs.

Still failed:
  - Runtime exact/shadow selector paths still do not reproduce fixed static/map-agent baselines under the 3s closed-loop budget.
  - Checkpoint export remains blocked by the current gate order.
  - True counterfactual labels remain unavailable.
  - G6 learned mixture/residual policy is not yet justified.
```

G5.2 final facts to preserve:

```text
decision = runtime_updatepolicy_equivalence_failed
row_count = 1080
update_log_rows = 1058

runtime_always_static_exact_matches_static = false
runtime_always_static_max_regret_vs_static = 0.08146453089000016

runtime_always_map_agent_exact_matches_map_agent = false
runtime_always_map_agent_max_regret_vs_map_agent = 0.06535141799999988

selector_shadow_static_matches_static = false
semantic_parity_mismatch_count = 0
selected_params_hash_matches_expected = true

force_additive_policy_compliant = true
disable_policy_compliant = true
policy_closure_passed = true

checkpoint_export_passed = false
counterfactual_labels_passed = false
IDs 166..205 untouched
```

Static flow-shield remains strong in the G5.2 sweep:

```text
repair5g2_best_frozen_static_candidate:
  mean_delta_ratio_vs_ltm = -0.016159006723795923
  prob_mean_lt_0 = 1.0

repair5g2_frozen_static_or_selector:
  mean_delta_ratio_vs_ltm = -0.017933839279306123
  prob_mean_lt_0 = 1.0
```

Runtime exact flow-shield is weaker but still directionally positive:

```text
repair5g52_runtime_always_static_exact:
  mean_delta_ratio_vs_ltm = -0.009864137592367338
  prob_mean_lt_0 = 0.9895

repair5g52_runtime_always_map_agent_exact:
  mean_delta_ratio_vs_ltm = -0.011012938574408163
  prob_mean_lt_0 = 0.995
```

This pattern points away from "the dual-channel traffic map was corrupted" and toward:

```text
The runtime selector/audit path is consuming enough extra wall-clock budget
or doing enough extra work inside the LTM loop to change closed-loop outcomes
under the 3s budget.
```

---

## 1. Working failure diagnosis

G5.2's "exact" selector path appears exact in **UpdateParams**, but not exact in **runtime path cost**.

In `cpp/tools/phase1a_batch.cpp`, fixed Repair5G methods use the direct path:

```text
args.repair5g_enabled = true
options.update_params = args.repair5g_update_params
no selector feature construction
no per-update selector JSONL log
no per-update traffic hash
no selector candidate resolution inside UpdatePolicy
```

By contrast, the G5.2 exact/shadow selector path still enters `options.update_policy` and performs at least some of:

```text
repair5g5_build_features(...)
repair5g5_apply_feature_ablation(...)
repair5g5_select_candidate(...)
repair5g5_resolve_candidate_alias(...)
repair5g_method_spec(...)
append_laur_update_log_jsonl(...)
traffic_map_hash(...)
update_params_hash(...)
update_params_fingerprint(...)
JSONL file open/write/close per update
```

Most importantly, `repair5g5_build_features(...)` currently calls:

```text
traffic_map.cost_audit(&instance)
traffic_map.nonzero_raw_edges()
traffic_map.nonzero_flow_edges()
```

and the update log path computes traffic hash / params fingerprint and writes JSONL synchronously. These operations happen inside the same closed-loop `Deadline` window as the solver. Even if they do not change PIBT/LaCAM*/UpdateLTM semantics, they reduce time available for later one-shot iterations and can change outcome under 3 seconds.

This explains why:

```text
selected_params_hash_matches_expected = true
semantic_parity_mismatch_count = 0
but closed-loop exact/shadow matching fails
```

The likely failure class is now:

```text
runtime_hook_overhead_or_audit_path_budget_sensitivity
```

not:

```text
dual_channel_update_corrupted
unsupported_candidate_alias_bug
wrong_UpdateParams_hash
force_additive_policy_bug
```

---

## 2. Non-negotiable constraints

Do not:

```text
- modify external/lacam2/lacam2/**
- change PIBT legality, priority inheritance, backtracking, vertex conflict, or swap conflict semantics
- change LaCAM* candidate generation, child pruning, OPEN/EXPLORED, rewrite, incumbent pruning, or restart semantics
- introduce action prediction
- introduce learned restart
- output h_i(v), action logits, priority overrides, or candidate deletion
- claim Phase5.5, Phase6, or AAAI-ready
- run IDs 166..205
- train a learned selector / mixture / residual model before runtime hook and counterfactual labels pass
- hide the G5.2 failure as "just noise"
```

Allowed:

```text
- project-owned C++/Python diagnostic changes
- overhead-neutral UpdatePolicy hook variants
- per-component runtime overhead instrumentation
- UpdateLTM transform-equivalence tests on same traffic_before + trace_events
- diagnostic checkpoint export on observed IDs only
- performance-mode vs audit-mode split
- observed-ID sweeps on 146..165 only
```

---

## 3. New gate philosophy

G5.2 used one combined closed-loop equivalence gate. G5.3 should split it into three gates.

### Gate A: UpdateLTM transform equivalence

Question:

```text
Given the exact same:
  instance
  traffic_before
  trace_events
  candidate UpdateParams

does fixed/direct UpdateLTM produce the same traffic_after as the policy-returned UpdateParams path?
```

This must be tested outside closed-loop wall-clock sensitivity.

Expected pass condition:

```text
traffic_after_hash_direct == traffic_after_hash_policy
C/F update stats equal
cost audit equal
UpdateParams hash equal
```

If this fails, there is a real UpdateLTM semantics bug.

### Gate B: overhead-neutral closed-loop hook equivalence

Question:

```text
If the hook does nothing except return pre-resolved static/map-agent UpdateParams,
with no feature build, no cost audit, no traffic hash, and no JSONL write,
does it reproduce fixed static/map-agent under the 3s budget?
```

Expected pass condition:

```text
runtime_static_minimal_hook_matches_static = true
runtime_map_agent_minimal_hook_matches_map_agent = true
semantic_parity_mismatch_count = 0
```

If this passes but full-audit selector path fails, the bug is overhead/audit path, not semantics.

### Gate C: runtime overhead budget classification

Question:

```text
Which component causes the 3s divergence?
```

Test incrementally:

```text
fixed baseline
minimal hook no log
minimal hook in-memory counter only
minimal hook JSONL only
minimal hook traffic_hash only
minimal hook params_hash/fingerprint only
minimal hook cost_audit only
minimal hook feature_build_without_cost_audit
minimal hook full_feature_build
minimal hook full_feature_build + JSONL
shadow_static_deferred_log
shadow_static_full_log
```

Expected output:

```text
per_update_overhead_ms
total_update_policy_overhead_ms
max_regret_vs_static/map_agent
ltm_iterations
one_shot_loop_cnt
expanded_nodes
low_level_pibt_calls
time_remaining_before/after_update_policy
```

This should identify whether the dominant issue is:

```text
JSONL sync write
traffic hash
cost_audit
feature build
full shadow selector computation
checkpoint copying
other deadline accounting
```

---

## 4. Required work

## P0. Documentation and decision hygiene

Add this plan to repo root:

```text
czr004_repair5g53_overhead_neutral_runtime_hook_plan.md
```

Update:

```text
docs/codex-worklog.md
outputs/reports/phase5p5_repair5g52_final_interpretation.md
outputs/reports/phase5p5_repair5g53_protocol_overview.md
```

Update AAAI readiness artifacts:

```text
runtime_hook_equivalence = failed_overhead_or_budget_sensitivity
updateparams_hash_equivalence = passed
policy_controls = passed
counterfactual_labels = blocked
learned_runtime_fresh_holdout = blocked_not_run
aaai_ready = false
phase5p5_allowed = false
phase6_allowed = false
```

Preserve the interpretation:

```text
G5.2 did not break goal-aware dual-channel LTM.
Fixed static/map-agent flow-shield remain strong.
The blocker is overhead-neutral runtime hook equivalence and replayable label infrastructure.
```

---

## P1. Implement UpdateLTM transform-equivalence audit

Add:

```text
scripts/run_repair5g53_update_transform_equivalence.py
scripts/analyze_repair5g53_update_transform_equivalence.py
```

If needed, add project-owned C++ diagnostic support in:

```text
cpp/tools/phase1a_batch.cpp
cpp/ltm/ltm.hpp
cpp/ltm/ltm.cpp
```

Suggested C++ diagnostic mode:

```text
--repair5g-transform-audit-candidate <candidate_id>
--repair5g-transform-audit-jsonl <path>
```

During an observed-ID run, for each iteration checkpoint where `traffic_before_map` exists:

```text
1. Copy traffic_before_map.
2. Apply expected candidate UpdateParams to copy with the exact trace_events.
3. Compare expected traffic_after hash/stats against actual traffic_after_map/hash.
4. Emit transform audit row.
```

Audit fields:

```text
method
map
agents
seed
iteration
candidate_id
resolved_candidate_id
expected_params_hash
actual_params_hash
traffic_before_hash_full
expected_traffic_after_hash_full
actual_traffic_after_hash_full
traffic_after_hash_match
congestion_update_count_expected / actual
flow_update_count_expected / actual
congestion_delta_total_expected / actual
flow_delta_total_expected / actual
cost_min_expected / actual
cost_max_expected / actual
cost_bounds_expected / actual
trace_event_count
committed_count
blocked_count
```

Run on observed IDs only:

```text
maps = random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
agents = 50, 100
instance_ids = 146..155
time_limit_sec = 3.0
ltm_max_iterations = 4
```

Methods/candidates:

```text
repair5g2_best_frozen_static_candidate
repair5g2_frozen_static_or_selector
repair5g52_runtime_always_static_exact
repair5g52_runtime_always_map_agent_exact
repair5g_dual_additive_parity
repair5g_dual_c_equiv_additive
```

Gate:

```text
update_transform_equivalence_passed = true
traffic_after_hash_mismatch_count = 0
params_hash_mismatch_count = 0
true_semantic_mismatch_count = 0
```

If this fails, stop and fix UpdateLTM transform semantics before any runtime or learning work.

---

## P2. Implement overhead-neutral minimal hook methods

Add exact methods that bypass all unnecessary selector/audit work:

```text
repair5g53_runtime_always_static_minimal_hook
repair5g53_runtime_always_map_agent_minimal_hook
repair5g53_runtime_static_shadow_noop_minimal
```

Requirements:

```text
- Use options.update_policy only to return a pre-resolved UpdateParams.
- Do not build runtime selector features.
- Do not call cost_audit inside the hook.
- Do not compute traffic_map_hash inside the hook.
- Do not write JSONL inside the hook.
- Do not parse selector spec inside every iteration.
- Do not resolve candidate aliases inside every iteration.
- Pre-resolve candidate ID and UpdateParams once per run.
```

Implementation sketch:

```cpp
const auto fixed_params = repair5g_method_spec(resolved_candidate).params;
options.update_policy = [fixed_params](const LtmUpdateContext&) {
    return fixed_params;
};
```

For map-agent:

```text
resolved_candidate = repair5g5_group_selector_candidate(args)
fixed_params = repair5g_method_spec(resolved_candidate).params
```

This is the key test:

```text
If minimal hook matches fixed baseline:
  runtime hook semantics are fine.
  G5.2 failure is overhead/audit path.

If minimal hook does not match fixed baseline:
  hidden semantics/timing path bug remains.
```

---

## P3. Implement overhead ablation ladder

Add:

```text
scripts/run_repair5g53_hook_overhead_ablation.py
scripts/analyze_repair5g53_hook_overhead_ablation.py
```

Add methods or flags:

```text
repair5g53_static_hook_minimal
repair5g53_static_hook_memory_counter
repair5g53_static_hook_jsonl_log_only
repair5g53_static_hook_params_hash_only
repair5g53_static_hook_traffic_hash_only
repair5g53_static_hook_cost_audit_only
repair5g53_static_hook_features_no_cost_audit
repair5g53_static_hook_full_features_no_jsonl
repair5g53_static_hook_full_features_jsonl
repair5g53_shadow_static_deferred_log
repair5g53_shadow_static_full_log
```

Instrument component timing with `std::chrono::steady_clock`:

```text
feature_build_ms
cost_audit_ms
candidate_select_ms
alias_resolve_ms
params_hash_ms
traffic_hash_ms
json_write_ms
checkpoint_copy_ms
update_policy_total_ms
update_apply_ms
time_remaining_before_policy
time_remaining_after_policy
time_remaining_after_update
```

Output:

```text
outputs/reports/phase5p5_repair5g53_hook_overhead_ablation_report.md
outputs/reports/phase5p5_repair5g53_hook_overhead_ablation_summary.json
outputs/tables/phase5p5_repair5g53_hook_overhead_ablation_paired.csv
outputs/tables/phase5p5_repair5g53_hook_overhead_components.csv
outputs/tables/phase5p5_repair5g53_hook_overhead_regret_cases.csv
```

Run matrix:

```text
Primary:
  IDs 146..155
  time_limit_sec = 3.0
  ltm_max_iterations = 4

Budget sensitivity:
  IDs 146..155
  time_limit_sec = 5.0 and 10.0
  ltm_max_iterations = 4

If primary minimal-hook gate passes:
  optional observed confirmation IDs 156..165
```

Gate:

```text
minimal_hook_static_matches_static = true
minimal_hook_map_agent_matches_map_agent = true
full_audit_overhead_classified = true
dominant_overhead_component_identified = true
true_semantic_mismatch_count = 0
```

---

## P4. Split performance mode from audit mode

Add a runtime mode flag:

```text
--repair5g-runtime-audit-mode off|minimal|perf|audit|full
```

Rules:

```text
perf:
  For closed-loop performance evaluation.
  No sync JSONL writes in update_policy.
  No traffic hash in update_policy.
  No full cost_audit in feature vector.
  Only cheap runtime-available features.
  Inference overhead is counted.
  Debug logging is disabled or aggregated after solve.

audit:
  For observed-ID diagnostics.
  May write per-update JSONL.
  May compute hashes.
  May export checkpoint snapshots.
  Not used for performance claims.

full:
  For local diagnosis only.
  Heavy logs/checkpoints allowed.
  Never compare as if it were performance runtime.
```

Future learned selectors must report:

```text
perf_mode_runtime_overhead_ms_total
perf_mode_inference_ms_total
audit_mode_overhead_ms_total
```

Do not let debug/audit overhead decide whether the learned method beats LTM.

---

## P5. Cheap feature refactor

The current `repair5g5_build_features` should be split into cheap and expensive feature groups.

Add:

```cpp
repair5g5_build_features_perf(...)
repair5g5_build_features_audit(...)
```

`perf` may use:

```text
agents
map_width
map_height
obstacle_ratio
density
iteration
has_incumbent_before
best_ratio_before
returned_solutions_count_so_far
trace committed/blocked/wait/progress counts
traffic_map nonzero C/F counts if O(1) or cached
last update C/F stats if cached
```

`perf` must avoid:

```text
full graph cost_audit per update
full traffic hash
full edge scan unless already maintained incrementally
JSON serialization
checkpoint copying
```

`audit` may keep the expensive fields.

Add a feature availability report:

```text
outputs/reports/phase5p5_repair5g53_runtime_feature_cost_audit.md
outputs/reports/phase5p5_repair5g53_runtime_feature_cost_audit_summary.json
```

---

## P6. Reopen checkpoint export only after semantic/minimal gates

If P1 and P2 pass, allow diagnostic checkpoint export even if full audit path remains slow.

Run:

```text
scripts/run_repair5g53_checkpoint_export_smoke.py
scripts/analyze_repair5g53_checkpoint_replayability.py
```

Checkpoint export is diagnostic-only and must be labeled:

```text
not performance runtime
not learned selector validation
not Phase5.5
not Phase6
```

Gate:

```text
checkpoint_rows > 0
traffic_before_map_available = true
trace_events_available = true
update_params_hash_present = true
feature_vector_present = true
replayability_audit_passed = true
```

---

## P7. Counterfactual labels only after checkpoint replayability

Only if P6 passes:

```text
scripts/run_repair5g53_counterfactual_update_probe.py
scripts/analyze_repair5g53_counterfactual_labels.py
```

Candidate set:

```text
repair5g2_best_frozen_static_candidate
repair5g2_frozen_static_or_selector
repair5g_dual_c_equiv_additive
repair5g2_c_equiv_best_frozen_baseline
top 2 static flow-shield candidates
additive fallback
```

Label definition:

```text
same instance
same traffic_before
same trace_events
apply candidate A -> short-probe outcome A
apply candidate B -> short-probe outcome B
compare A vs B
```

Gate:

```text
true_counterfactual_labels_available = true
candidate_label_coverage_sufficient = true
oracle_gap_over_static_measured = true
label_leakage_audit_passes = true
runtime_feature_availability_audit_passes = true
```

Do not train G6 in this round. If labels pass, write only the G6 design.

---

## P8. Final decision

Write:

```text
outputs/reports/phase5p5_repair5g53_decision.md
outputs/reports/phase5p5_repair5g53_decision_summary.json
```

Allowed decisions:

```text
update_transform_semantic_bug
minimal_hook_semantic_bug
runtime_hook_overhead_classified
runtime_hook_perf_mode_passed
checkpoint_export_failed
checkpoint_replayability_passed
counterfactual_labels_unavailable
counterfactual_labels_available_continue_g6_design
stop_for_protocol_or_semantic_bug
```

Mandatory final fields:

```json
{
  "phase5p5_allowed": false,
  "phase6_allowed": false,
  "aaai_ready": false,
  "ids_166_205_untouched": true,
  "fixed_static_flow_shield_still_valid": true,
  "goal_aware_dual_channel_ltm_corrupted": false,
  "g6_training_allowed": false
}
```

---

## 5. Validation

Required validation:

```text
python -m py_compile all new/modified Python scripts
if C++ changed: scripts/build_phase1a_batch.ps1
pytest focused G5.3 tests if available
manual fallback harness if pytest unavailable
git diff --check
```

Add tests for:

```text
UpdateParams hash stability
minimal hook candidate resolution
audit/perf mode separation
feature cost grouping
checkpoint schema
no IDs 166..205 in generated commands
```

Commit message:

```text
repair5g: isolate updatepolicy overhead and validate transform equivalence
```

---

## 6. Codex prompt

Continue czr004 on branch `phase4f5p5-stable-attention-lau` after commit `2e1d30c repair5g: fix updatepolicy equivalence and export counterfactual checkpoints`.

Goal:

Implement Repair5G.5.3: isolate runtime UpdatePolicy overhead from true UpdateLTM semantics, prove or disprove overhead-neutral hook equivalence, split performance runtime from audit/checkpoint runtime, and only then reopen replayable checkpoint export and true counterfactual UpdateLTM labels. Do not train a selector or neural model. Do not run IDs 166..205.

Main project objective:

Use learning-enhanced `UpdateLTM` to replace the coarse additive update in the LTM paper and eventually beat `LaCAM*+plain additive LTM` under closed-loop solver metrics, without changing LaCAM*/PIBT semantics.

Read first:

```text
deep-research-report.md
phase4_6_laur_ltm_codex_execution_plan.md
docs/aaai_quality_requirements.md
czr004_repair5g52_runtime_updatepolicy_equivalence_counterfactual_labels_plan.md
outputs/reports/phase5p5_repair5g52_decision.md
outputs/reports/phase5p5_repair5g52_decision_summary.json
outputs/reports/phase5p5_repair5g52_updatepolicy_equivalence_summary.json
outputs/reports/phase5p5_repair5g52_updateparams_equivalence_summary.json
outputs/reports/phase5p5_repair5g52_policy_closure_summary.json
```

Preserve this interpretation:

```text
- G5.2 decision = runtime_updatepolicy_equivalence_failed.
- Candidate registry and UpdateParams hash equivalence passed.
- Selected params hash matches expected.
- Force-additive and disable policy closure passed.
- Semantic parity mismatch count is 0.
- Runtime exact/shadow selector paths still fail fixed static/map-agent reproduction under 3s:
    static exact max regret = 0.08146453089000016
    map-agent exact max regret = 0.06535141799999988
- The likely remaining issue is runtime selector/audit overhead or wall-clock budget sensitivity, not a dual-channel traffic-map corruption.
- Fixed static/map-agent flow-shield still beat LTM on observed IDs.
- Checkpoint export and counterfactual labels remain blocked until semantic/minimal hook gates pass.
- IDs 166..205 remain untouched.
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
- run IDs 166..205
- train a learned selector, mixture, residual model, MLP, GNN, or transformer in this round
- hide G5.2 as "just noise"
```

Tasks:

1. Add `czr004_repair5g53_overhead_neutral_runtime_hook_plan.md` to repo root and update `docs/codex-worklog.md`.

2. Write:
   ```text
   outputs/reports/phase5p5_repair5g52_final_interpretation.md
   outputs/reports/phase5p5_repair5g53_protocol_overview.md
   ```

3. Update AAAI readiness artifacts:
   ```text
   runtime_hook_equivalence = failed_overhead_or_budget_sensitivity
   updateparams_hash_equivalence = passed
   policy_controls = passed
   counterfactual_labels = blocked
   learned_runtime_fresh_holdout = blocked_not_run
   aaai_ready = false
   ```

4. Implement UpdateLTM transform-equivalence audit:
   ```text
   scripts/run_repair5g53_update_transform_equivalence.py
   scripts/analyze_repair5g53_update_transform_equivalence.py
   ```
   Add project-owned C++ support if needed. Gate: same traffic_before + trace_events + UpdateParams must yield identical traffic_after hashes and C/F update stats.

5. Implement overhead-neutral minimal hook methods:
   ```text
   repair5g53_runtime_always_static_minimal_hook
   repair5g53_runtime_always_map_agent_minimal_hook
   repair5g53_runtime_static_shadow_noop_minimal
   ```
   These must return pre-resolved UpdateParams only. No feature build, no cost audit, no traffic hash, no JSONL writes inside the hook.

6. Implement overhead ablation ladder:
   ```text
   scripts/run_repair5g53_hook_overhead_ablation.py
   scripts/analyze_repair5g53_hook_overhead_ablation.py
   ```
   Measure per-component overhead and closed-loop regret vs fixed static/map-agent.

7. Add performance/audit split:
   ```text
   --repair5g-runtime-audit-mode off|minimal|perf|audit|full
   ```
   Performance mode must not use sync JSONL, traffic hash, full cost audit, or checkpoint copying.

8. Split feature construction:
   ```text
   repair5g5_build_features_perf(...)
   repair5g5_build_features_audit(...)
   ```
   Perf features must be cheap and runtime-available. Audit features may be expensive.

9. Run observed-ID G5.3 matrix:
   ```text
   IDs 146..155
   maps random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
   agents 50,100
   time_limit_sec 3.0
   ltm_max_iterations 4
   ```
   If minimal hook passes, optionally confirm on IDs 156..165. Do not touch 166..205.

10. Only if transform equivalence and minimal hook equivalence pass, reopen diagnostic checkpoint export:
    ```text
    scripts/run_repair5g53_checkpoint_export_smoke.py
    scripts/analyze_repair5g53_checkpoint_replayability.py
    ```

11. Only if checkpoint replayability passes, collect true counterfactual labels:
    ```text
    scripts/run_repair5g53_counterfactual_update_probe.py
    scripts/analyze_repair5g53_counterfactual_labels.py
    ```

12. Do not train G6. If counterfactual labels become available, write only:
    ```text
    outputs/reports/phase5p5_repair5g53_g6_safe_mixture_readiness.md
    outputs/reports/phase5p5_repair5g53_g6_safe_mixture_readiness_summary.json
    ```

13. Write:
    ```text
    outputs/reports/phase5p5_repair5g53_decision.md
    outputs/reports/phase5p5_repair5g53_decision_summary.json
    ```

Decision options:

```text
update_transform_semantic_bug
minimal_hook_semantic_bug
runtime_hook_overhead_classified
runtime_hook_perf_mode_passed
checkpoint_export_failed
checkpoint_replayability_passed
counterfactual_labels_unavailable
counterfactual_labels_available_continue_g6_design
stop_for_protocol_or_semantic_bug
```

Validation:

```text
python -m py_compile all new/modified Python scripts
if C++ changed, run scripts/build_phase1a_batch.ps1
pytest focused G5.3 tests if available; otherwise manual fallback harness
git diff --check
commit and push only G5.3-related tracked files and reports
leave unrelated dirty/untracked files untouched
```

Commit message:

```text
repair5g: isolate updatepolicy overhead and validate transform equivalence
```
