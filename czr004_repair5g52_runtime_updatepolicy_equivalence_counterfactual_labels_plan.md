# czr004 Repair5G.5.2 Plan: Runtime UpdatePolicy Equivalence, Replayable Checkpoints, and Counterfactual UpdateLTM Labels

**Branch:** `phase4f5p5-stable-attention-lau`  
**Start after commit:** `f8dd079 repair5g: diagnose runtime selector failure and add safe bridge`  
**Status:** proposed next diagnostic research wave after Repair5G.5.1 found `runtime_hook_bug_blocks_learning`  
**Promotion status:** `phase5p5_allowed=false`, `phase6_allowed=false`  
**AAAI status:** `aaai_ready=false`  
**Main project objective:** use learning-enhanced `UpdateLTM` to replace the coarse additive update in the LTM paper and eventually beat `LaCAM*+plain additive LTM` under closed-loop solver metrics, without changing LaCAM*/PIBT semantics.

---

## 0. Executive interpretation

Repair5G.5.1 is a **very useful failure**.

It proves that the next blocker is not "we need a bigger neural net." The next blocker is:

```text
The runtime UpdatePolicy hook cannot yet reproduce known-safe static/map-agent flow-shield behavior.
```

Preserve the facts:

```text
G5.1 decision:
  runtime_hook_bug_blocks_learning

Why G5 failed:
  offline_to_runtime_selector_transfer_failure

Runtime selector failure:
  G5 learned runtime selector:
    8 / 27 / 23
    mean_delta_ratio_vs_ltm = +0.00350549546894118

G5.1 autopsy:
  early C-equiv branch updates = 147
  late static-branch updates = 0
  selector rule:
    feature = ltm_iterations
    threshold = 2.5
    left_method = repair5g_dual_c_equiv_c100_b100_w100_d090
    right_method = repair5g2_best_frozen_static_candidate
  diagnosis:
    offline run-level stump became an early-update switch at runtime and suppressed early flow-shield updates.

Runtime hook sanity:
  always_static_matches_or_policy_equivalent = false
  always_static_max_regret_vs_static = 0.16188178529000008
  always_map_agent_matches_or_policy_equivalent = false
  always_map_agent_max_regret_vs_map_agent = 0.15150784077000012
  always_additive_matches_additive_under_parity_policy = true
  bad_g5_stump_classified_failed_or_weak = true
  runtime_hook_sanity_passed = false

Policy controls:
  disable_policy_compliant = true
  force_additive_policy_compliant = false
  policy_control_reproducer_passed = false

Counterfactual labels:
  context_count = 1496
  available true counterfactual label rows = 0
  gap = true counterfactual labels are unavailable without replayable pre-update traffic snapshots

Fresh learned-runtime final:
  IDs 166..205 remain reserved and untouched.
```

Interpretation:

```text
Flow-shield representation:
  still strong.

Static/map-agent flow-shield:
  still the reliable runtime candidate.

Learned runtime selector:
  failed.

Safe selector:
  correctly blocked because runtime hook sanity failed.

Small neural selector:
  not justified yet.

Next scientific step:
  fix or explain runtime UpdatePolicy equivalence,
  then export replayable UpdateLTM checkpoints,
  then collect counterfactual UpdateLTM labels,
  then return to safe selector / small neural policy.
```

This is exactly the kind of rigor that increases AAAI/ICLR/ICML/NeurIPS/ICRA credibility. It prevents the project from claiming learning before the runtime hook and causal labels are correct.

---

## 1. Working failure hypothesis

There are now two separate blockers.

### Blocker A: Runtime UpdatePolicy equivalence bug

If a runtime selector always returns:

```text
repair5g2_best_frozen_static_candidate
```

then it should reproduce, or be policy-equivalent to:

```text
repair5g2_best_frozen_static_candidate
```

But G5.1 found:

```text
always_static runtime mean = -0.006495710798846173
static baseline mean = -0.015455739176862769
always_static max regret vs static = 0.16188178529000008
```

Similarly, always-map-agent did not reproduce map-agent baseline.

Therefore one or more of the following is likely true:

```text
1. Candidate alias mapping differs between static method and runtime selector path.
2. Runtime selector returns a candidate ID that maps to a different UpdateParams object.
3. UpdatePolicy is invoked at different iteration timing than the fixed method path.
4. The fixed method applies UpdateParams at initialization or first update, but runtime selector applies later.
5. The traffic map state differs before the first selected update.
6. The selector path uses different dual-channel instance/projection data.
7. Flow-shield cost parameters are not fully transferred through the selector path.
8. A fallback-to-additive branch triggers silently when a candidate name is unsupported.
9. Method alias is only for reporting while the actual method uses a different path.
10. Runtime logging is present but execution policy is not identical to the logged candidate.
```

This must be solved before any learned selector is meaningful.

### Blocker B: No replayable counterfactual UpdateLTM labels

G5.1 created contexts but found no true counterfactual labels:

```text
true counterfactual labels are unavailable without replayable pre-update traffic snapshots
```

A learned parameter policy needs labels of the form:

```text
same instance
same pre-update traffic_before
same trace_events
candidate UpdateParams A -> short-probe outcome A
candidate UpdateParams B -> short-probe outcome B
```

Without these labels, training from full-run outcomes is confounded. It can produce bad rules like:

```text
if ltm_iterations <= 2.5:
    choose weak C-equiv
else:
    choose static flow-shield
```

The project must now build replayable checkpoint infrastructure.

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
- run IDs 166..205 before runtime hook equivalence and safe smoke pass
- train a bigger neural net before replayable counterfactual labels exist
- hide or minimize the runtime hook bug
```

Allowed:

```text
- project-owned C++/Python fixes for runtime UpdatePolicy equivalence
- candidate registry / UpdateParams dump
- runtime selector shadow mode
- replayable LTM checkpoint export
- short counterfactual UpdateLTM probes
- observed-ID sanity/smoke runs
- safe selector only after hook equivalence passes
```

---

## 3. Split policy

Observed:

```text
IDs 1..25      support/training
IDs 26..45     G1/G2 development
IDs 46..65     G2 fresh final
IDs 66..105    G3 broader/protocol diagnostics
IDs 106..115   possible G3.1 diagnostic sentinel; audit before reuse
IDs 126..165   G4 clean validation; G5/G5.1 smoke/sanity used 126..145
```

Allowed in G5.2:

```text
runtime equivalence / checkpoint / label infrastructure:
  observed IDs only, preferably 136..165 or existing G5/G5.1 logs

additional observed-ID smoke:
  IDs 146..165
```

Reserved:

```text
IDs 166..205:
  learned-runtime final holdout.
  Do not touch until:
    runtime hook equivalence passes,
    policy controls pass,
    safe runtime smoke passes,
    selector is frozen.
```

---

## 4. Required work

## P0. Documentation and decision hygiene

Add this plan to repo root:

```text
czr004_repair5g52_runtime_updatepolicy_equivalence_counterfactual_labels_plan.md
```

Update:

```text
docs/codex-worklog.md
```

Write:

```text
outputs/reports/phase5p5_repair5g51_final_interpretation.md
outputs/reports/phase5p5_repair5g52_protocol_overview.md
```

`phase5p5_repair5g51_final_interpretation.md` must state:

```text
- G5.1 found runtime_hook_bug_blocks_learning.
- The original learned selector failed due to offline-to-runtime transfer failure.
- The runtime hook did not reproduce always-static / map-agent safe policies.
- Force-additive policy control is still non-compliant.
- No safe selector smoke was run.
- True counterfactual labels are unavailable without replayable pre-update traffic snapshots.
- IDs 166..205 remain reserved.
- phase5p5_allowed=false, phase6_allowed=false, aaai_ready=false.
```

Update AAAI readiness artifacts:

```text
outputs/reports/phase5p5_repair5g_aaai_readiness_audit.md
outputs/reports/phase5p5_repair5g_aaai_readiness_summary.json
outputs/tables/phase5p5_repair5g_aaai_evidence_matrix.csv
outputs/tables/phase5p5_repair5g_claim_ledger.csv
```

Required status:

```text
runtime_selector_integration = partial
runtime_hook_equivalence = failed
policy_controls = failed_force_additive
counterfactual_labels = missing
learned_runtime_selector = failed
learned_runtime_fresh_holdout = blocked_not_run
aaai_ready = false
```

## P1. Candidate registry and UpdateParams equivalence audit

Implement a single source of truth for Repair5G candidate-to-UpdateParams mapping.

Suggested files:

```text
scripts/repair5g_candidate_registry.py
outputs/tables/phase5p5_repair5g_candidate_registry.csv
outputs/reports/phase5p5_repair5g_candidate_registry_summary.json
```

The registry must include:

```text
method_name
canonical_candidate_id
component
enable_dual_channel
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
min_edge_cost
max_edge_cost
goal_projection_mode
flow_shield_beta
max_flow_shield
fallback_behavior
is_alias
alias_target
```

Implement:

```text
scripts/analyze_repair5g52_updateparams_equivalence.py
```

Inputs:

```text
outputs/reports/phase5p5_repair5g5_runtime_contextual_selector_spec.json
artifacts/models/laur_ltm/repair5g5_contextual_flow_shield_selector/selector_spec.json
outputs/tables/phase5p5_repair5g5_runtime_smoke_summary.csv
outputs/tables/phase5p5_repair5g51_runtime_hook_sanity_summary.csv
```

Outputs:

```text
outputs/reports/phase5p5_repair5g52_updateparams_equivalence.md
outputs/reports/phase5p5_repair5g52_updateparams_equivalence_summary.json
outputs/tables/phase5p5_repair5g52_updateparams_dump.csv
outputs/tables/phase5p5_repair5g52_alias_resolution_audit.csv
```

Required checks:

```text
1. `repair5g2_best_frozen_static_candidate` resolves to exactly the same UpdateParams everywhere.
2. Runtime selector candidate ID resolves to the same UpdateParams as the fixed method path.
3. Aliases:
     repair5g2_best_frozen_static_candidate
     repair5g2_g1_top_diagnostic_candidate
     repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75
   are consistent.
4. Unsupported candidates never silently fall back without a logged fallback reason.
5. C-equiv and additive fallbacks are explicitly identified.
```

If alias or params mismatch is found, fix registry/runtime mapping before any solver smoke.

## P2. C++ runtime UpdatePolicy equivalence instrumentation

Modify only project-owned C++ if required:

```text
cpp/tools/phase1a_batch.cpp
cpp/ltm/ltm.hpp
cpp/ltm/ltm.cpp
```

Add or extend logs so each LTM update can record:

```text
iteration
method
runtime_selector_active
selector_name
selector_policy_mode
selected_candidate_id
selected_candidate_resolved_method
selected_candidate_params_hash
all UpdateParams scalar fields
fallback_reason
force_additive_active
disable_active
dual_channel_enabled
goal_projection_mode
flow_shield_beta
max_flow_shield
traffic_before hash
traffic_after hash
trace_event_count
C/F update counts
C/F nonzero edges
cost audit
```

Add a mode if feasible:

```text
repair5g52_runtime_selector_shadow_static
```

Behavior:

```text
logs what a selector would choose,
but executes repair5g2_best_frozen_static_candidate.
```

Add another mode:

```text
repair5g52_runtime_always_static_exact
```

Behavior:

```text
uses the same code path as runtime selector but should be bitwise/policy-equivalent to repair5g2_best_frozen_static_candidate.
```

The key diagnostic is:

```text
If runtime_always_static_exact does not match static baseline,
then learning is blocked by runtime UpdatePolicy path mismatch.
```

## P3. Minimal equivalence reproducer

Implement:

```text
scripts/run_repair5g52_updatepolicy_equivalence_reproducer.py
```

Run observed IDs only:

```text
maps = random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
agents = 50, 100
instance_ids = 146..155
time_limit_sec = 3.0
ltm_max_iterations = 4
max_workers = 1 first, then optional 8
```

Methods:

```text
lacam_star_ltm
repair5g2_best_frozen_static_candidate
repair5g2_frozen_static_or_selector
repair5g52_runtime_always_static_exact
repair5g52_runtime_always_map_agent_exact
repair5g52_runtime_selector_shadow_static
repair5g51_runtime_always_static_flow_shield  # previous bug reproducer
repair5g51_runtime_bad_g5_stump              # negative control
always_additive_defer
repair5f_candidate_additive_ltm
laur_disable
laur_force_additive_direct
repair5g_dual_additive_parity
repair5g_dual_c_equiv_additive
repair5g5_contextual_flow_shield_selector_force_additive_parity
repair5g5_contextual_flow_shield_selector_disable
```

Outputs:

```text
outputs/logs/phase5p5_repair5g52_updatepolicy_equivalence/phase5p5_repair5g52_updatepolicy_equivalence.jsonl
outputs/logs/phase5p5_repair5g52_updatepolicy_equivalence/phase5p5_repair5g52_updatepolicy_equivalence_commands.jsonl
outputs/logs/phase5p5_repair5g52_updatepolicy_equivalence/phase5p5_repair5g52_updatepolicy_equivalence_ltm_updates.jsonl
outputs/reports/phase5p5_repair5g52_updatepolicy_equivalence_report.md
outputs/reports/phase5p5_repair5g52_updatepolicy_equivalence_summary.json
outputs/tables/phase5p5_repair5g52_updatepolicy_equivalence_paired.csv
outputs/tables/phase5p5_repair5g52_updatepolicy_equivalence_by_map_agent.csv
outputs/tables/phase5p5_repair5g52_updatepolicy_equivalence_update_hashes.csv
outputs/tables/phase5p5_repair5g52_updatepolicy_equivalence_mismatch_cases.csv
```

Gate:

```text
runtime_always_static_exact_matches_static = true
runtime_always_map_agent_exact_matches_map_agent = true
selector_shadow_static_matches_static = true
force_additive_policy_compliant = true
disable_policy_compliant = true
semantic_parity_mismatch_count = 0
selector_logs_present = true
selected_params_hash_matches_expected = true
fallback_reason_logged_for_all_fallbacks = true
```

If this gate fails:

```text
stop.
Do not train.
Do not run safe selector.
Do not run IDs 166..205.
Decision = runtime_updatepolicy_equivalence_failed.
```

## P4. Force-additive / disable policy closure

G5.1 had:

```text
disable_policy_compliant = true
force_additive_policy_compliant = false
```

Implement or fix:

```text
scripts/run_repair5g52_policy_closure.py
```

Run:

```text
instance_ids = 146..155
methods:
  lacam_star_ltm
  always_additive_defer
  repair5f_candidate_additive_ltm
  laur_disable
  laur_force_additive_direct
  repair5g_dual_additive_parity
  repair5g_dual_c_equiv_additive
  repair5g5_contextual_flow_shield_selector_force_additive_parity
  repair5g5_contextual_flow_shield_selector_disable
  repair5g52_runtime_force_additive_exact
  repair5g52_runtime_disable_exact
```

Outputs:

```text
outputs/reports/phase5p5_repair5g52_policy_closure_report.md
outputs/reports/phase5p5_repair5g52_policy_closure_summary.json
outputs/tables/phase5p5_repair5g52_policy_closure_cases.csv
```

Gate:

```text
force_additive_policy_compliant = true
disable_policy_compliant = true
time_budget_equivalent_mismatches_classified = true
true_semantic_mismatch_count = 0
```

## P5. Replayable pre-update checkpoint export

Only after P3/P4 pass.

Implement checkpoint export that can support counterfactual UpdateLTM probes.

Suggested C++/runtime output:

```text
--repair5g-export-update-checkpoints-jsonl <path>
```

Each row should include enough to replay:

```text
schema_version
map
agents
seed
scen
method
iteration
node_budget
time_remaining_sec
best_ratio_before
has_incumbent_before
returned_solutions_count_so_far
trace_events
traffic_before:
  C raw counts for nonzero edges
  F raw counts for nonzero edges
  normalized C/F if needed
traffic_before_hash
update_stats_before
cost_audit_before
current UpdateParams / candidate
allowed feature vector
forbidden feature audit
```

If full traffic map export is too large, provide an explicit compressed format:

```text
edge list:
  from_id
  to_id
  c_raw
  f_raw
```

Implement:

```text
scripts/run_repair5g52_checkpoint_export_smoke.py
scripts/analyze_repair5g52_checkpoint_replayability.py
```

Run observed IDs only:

```text
maps = random-32-32-20, maze-32-32-4
agents = 50, 100
instance_ids = 146..150
methods:
  repair5g2_best_frozen_static_candidate
  repair5g2_frozen_static_or_selector
```

Outputs:

```text
outputs/logs/phase5p5_repair5g52_checkpoint_export/phase5p5_repair5g52_update_checkpoints.jsonl
outputs/reports/phase5p5_repair5g52_checkpoint_replayability_report.md
outputs/reports/phase5p5_repair5g52_checkpoint_replayability_summary.json
outputs/tables/phase5p5_repair5g52_checkpoint_manifest.csv
```

Gate:

```text
checkpoint_rows > 0
trace_events_present = true
traffic_before_present = true
traffic_before_hash_present = true
feature_vector_present = true
no forbidden features = true
estimated_size_acceptable = true
```

## P6. Counterfactual UpdateLTM probe labels

Only after P5 passes.

Implement:

```text
scripts/run_repair5g52_counterfactual_update_probe.py
scripts/analyze_repair5g52_counterfactual_labels.py
```

Candidate set:

```text
repair5g2_best_frozen_static_candidate
repair5g2_frozen_static_or_selector
repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75
repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75
repair5g_dual_c_equiv_additive
repair5g2_c_equiv_best_frozen_baseline
```

For each checkpoint:

```text
same instance
same traffic_before
same trace_events
apply candidate UpdateParams
run short one-shot / next-iteration probe if available
record outcome:
  success
  ratio
  expanded nodes
  low-level PIBT calls
  time
```

Outputs:

```text
outputs/tables/phase5p5_repair5g52_counterfactual_update_labels.csv
outputs/tables/phase5p5_repair5g52_counterfactual_oracle_by_context.csv
outputs/reports/phase5p5_repair5g52_counterfactual_label_report.md
outputs/reports/phase5p5_repair5g52_counterfactual_label_summary.json
```

Gate:

```text
label_rows > 0
candidate_coverage_complete = true
oracle_gap_over_static_measured = true
feature_leakage_audit_passes = true
labels_are_contextual_not_run_level = true
```

If no labels can be produced, write a hard gap report and stop learning work.

## P7. Only after labels: safe mixture / residual selector design

Do not train a large model in this phase.

If P6 passes, design but do not necessarily run fresh validation:

```text
outputs/reports/phase5p5_repair5g52_safe_mixture_policy_design.md
outputs/reports/phase5p5_repair5g52_safe_mixture_policy_spec.json
```

Preferred G6 method:

```text
safe mixture over experts:
  expert_1 = static flow-shield
  expert_2 = map-agent flow-shield
  expert_3 = additive / C-equiv fallback

with:
  confidence / abstention
  bounded residuals only if counterfactual labels are stable
```

This is the next AAAI-relevant learned component.

## P8. Decision

Write:

```text
outputs/reports/phase5p5_repair5g52_decision.md
outputs/reports/phase5p5_repair5g52_decision_summary.json
```

Decision options:

```text
runtime_updatepolicy_equivalence_failed
policy_controls_failed
checkpoint_export_failed
counterfactual_labels_unavailable
continue_counterfactual_label_collection
continue_safe_mixture_policy_design
continue_g6_learned_dual_channel_parameter_policy
stop_for_protocol_or_semantic_bug
```

Decision must answer:

```text
1. Did runtime always-static reproduce static baseline?
2. Did runtime always-map-agent reproduce map-agent baseline?
3. Did selector shadow mode reproduce static while logging decisions?
4. Is force-additive policy fixed?
5. Is disable policy fixed?
6. Are UpdateParams hashes consistent?
7. Are replayable traffic_before + trace checkpoints available?
8. Are true counterfactual labels available?
9. Is G6 learned mixture/residual policy justified?
10. Are IDs 166..205 still untouched?
```

---

## 5. Validation requirements

Run:

```text
python -m py_compile \
  scripts/repair5g_candidate_registry.py \
  scripts/analyze_repair5g52_updateparams_equivalence.py \
  scripts/run_repair5g52_updatepolicy_equivalence_reproducer.py \
  scripts/run_repair5g52_policy_closure.py \
  scripts/run_repair5g52_checkpoint_export_smoke.py \
  scripts/analyze_repair5g52_checkpoint_replayability.py \
  scripts/run_repair5g52_counterfactual_update_probe.py \
  scripts/analyze_repair5g52_counterfactual_labels.py
```

If C++ changed:

```text
scripts/build_phase1a_batch.ps1
```

Run tests:

```text
pytest if available
otherwise manual fallback harness over all relevant Repair5G.5/G5.1/G5.2 protocol and runtime tests
```

Suggested tests:

```text
tests/test_repair5g52_candidate_registry.py
tests/test_repair5g52_updatepolicy_equivalence.py
tests/test_repair5g52_checkpoint_schema.py
```

Always run:

```text
git diff --check
```

Commit only G5.2-related tracked files and reports. Leave unrelated dirty/untracked files untouched. Large raw JSONL/checkpoint logs may remain ignored, but committed summaries/manifests must be sufficient.

Commit message:

```text
repair5g: fix updatepolicy equivalence and export counterfactual checkpoints
```

---

# Codex prompt

Continue czr004 on branch `phase4f5p5-stable-attention-lau` after commit `f8dd079 repair5g: diagnose runtime selector failure and add safe bridge`.

Goal:
Implement Repair5G.5.2: fix or explain runtime UpdatePolicy equivalence, close force-additive/disable policy controls, export replayable pre-update UpdateLTM checkpoints, and produce true counterfactual UpdateLTM labels. Do not train a large neural network and do not run fresh IDs 166..205.

Main project objective:
Use learning-enhanced `UpdateLTM` to replace the coarse additive update in the LTM paper and eventually beat `LaCAM*+plain additive LTM` under closed-loop solver metrics, without changing LaCAM*/PIBT semantics.

Read first:
```text
deep-research-report.md
phase4_6_laur_ltm_codex_execution_plan.md
docs/aaai_quality_requirements.md
czr004_repair5g5_aaai_learned_flow_shield_runtime_plan.md
czr004_repair5g51_runtime_selector_failure_safe_bridge_plan.md
outputs/reports/phase5p5_repair5g51_decision.md
outputs/reports/phase5p5_repair5g5_runtime_selector_failure_autopsy_summary.json
outputs/reports/phase5p5_repair5g51_runtime_hook_sanity_summary.json
outputs/reports/phase5p5_repair5g51_policy_control_reproducer_summary.json
outputs/reports/phase5p5_repair5g51_counterfactual_label_quality_summary.json
```

Preserve this interpretation:
```text
- G5.1 found runtime_hook_bug_blocks_learning.
- G5 failed due to offline-to-runtime selector transfer failure.
- The bad stump overused weak C-equiv in early runtime iterations:
    early C-equiv branch updates = 147
    late static branch updates = 0
- Flow-shield representation remains validated by G2/G4.
- Runtime hook sanity failed:
    always_static_matches_or_policy_equivalent = false
    always_static_max_regret_vs_static = 0.16188178529000008
    always_map_agent_matches_or_policy_equivalent = false
    always_map_agent_max_regret_vs_map_agent = 0.15150784077000012
- Force-additive policy remains non-compliant:
    force_additive_policy_compliant = false
- Disable policy is compliant.
- Counterfactual context rows exist but true counterfactual labels are unavailable:
    context_count = 1496
    available_label_rows = 0
    gap = true counterfactual labels are unavailable without replayable pre-update traffic snapshots
- IDs 166..205 remain reserved and untouched.
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
- train a bigger neural net before runtime UpdatePolicy equivalence and counterfactual labels exist
```

Tasks:

1. Add `czr004_repair5g52_runtime_updatepolicy_equivalence_counterfactual_labels_plan.md` to repo root and update `docs/codex-worklog.md`.

2. Write:
```text
outputs/reports/phase5p5_repair5g51_final_interpretation.md
outputs/reports/phase5p5_repair5g52_protocol_overview.md
```

3. Update AAAI readiness artifacts:
```text
runtime_hook_equivalence = failed
policy_controls = failed_force_additive
counterfactual_labels = missing
learned_runtime_fresh_holdout = blocked_not_run
aaai_ready = false
```

4. Implement candidate registry and UpdateParams equivalence audit:
```text
scripts/repair5g_candidate_registry.py
scripts/analyze_repair5g52_updateparams_equivalence.py
```

5. Instrument runtime UpdatePolicy equivalence in project-owned C++ if needed:
```text
cpp/tools/phase1a_batch.cpp
cpp/ltm/ltm.hpp
cpp/ltm/ltm.cpp
```

Add logs for selected candidate ID, resolved method, UpdateParams hash, all UpdateParams fields, fallback reason, force/disable active, traffic_before/after hash, and C/F update stats.

6. Implement and run:
```text
scripts/run_repair5g52_updatepolicy_equivalence_reproducer.py
```

Use observed IDs 146..155. Gate requires runtime-always-static and runtime-always-map-agent to reproduce their baselines under parity policy.

7. Implement and run:
```text
scripts/run_repair5g52_policy_closure.py
```

Gate requires force-additive and disable policy compliance.

8. Only if P6/P7 pass, implement replayable pre-update checkpoint export:
```text
--repair5g-export-update-checkpoints-jsonl <path>
scripts/run_repair5g52_checkpoint_export_smoke.py
scripts/analyze_repair5g52_checkpoint_replayability.py
```

9. Only if checkpoints pass, implement counterfactual UpdateLTM probe labels:
```text
scripts/run_repair5g52_counterfactual_update_probe.py
scripts/analyze_repair5g52_counterfactual_labels.py
```

10. Do not train a large neural model. If counterfactual labels pass, write only the G6 safe mixture/residual policy design:
```text
outputs/reports/phase5p5_repair5g52_safe_mixture_policy_design.md
outputs/reports/phase5p5_repair5g52_safe_mixture_policy_spec.json
```

11. Write:
```text
outputs/reports/phase5p5_repair5g52_decision.md
outputs/reports/phase5p5_repair5g52_decision_summary.json
```

Decision options:
```text
runtime_updatepolicy_equivalence_failed
policy_controls_failed
checkpoint_export_failed
counterfactual_labels_unavailable
continue_counterfactual_label_collection
continue_safe_mixture_policy_design
continue_g6_learned_dual_channel_parameter_policy
stop_for_protocol_or_semantic_bug
```

Validation:
```text
py_compile all new/modified Python scripts
if C++ changed, run scripts/build_phase1a_batch.ps1
pytest if available; otherwise manual fallback harness
git diff --check
commit and push only G5.2-related tracked files and reports
leave unrelated dirty/untracked files untouched
```

Commit message:
```text
repair5g: fix updatepolicy equivalence and export counterfactual checkpoints
```
