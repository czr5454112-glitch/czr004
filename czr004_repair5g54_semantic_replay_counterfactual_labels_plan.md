# czr004 Repair5G.5.4 Plan: Semantic Replay, Counterfactual UpdateLTM Labels, and Budget-Robust Runtime Policy

**Branch:** `phase4f5p5-stable-attention-lau`
**Start after commit:** `60acc92 repair5g: isolate updatepolicy overhead and validate transform equivalence`
**Status:** proposed next diagnostic/research wave after G5.3 refined the remaining failure to `minimal_hook_time_budget_sensitivity`
**Promotion status:** `phase5p5_allowed=false`, `phase6_allowed=false`
**AAAI status:** `aaai_ready=false`
**Main project objective:** use learning-enhanced `UpdateLTM` to replace the coarse additive update in the LTM paper and eventually beat `LaCAM*+plain additive LTM` under closed-loop solver metrics, without changing LaCAM*/PIBT semantics.

---

## 0. Executive interpretation

G5.3 is a **positive diagnostic result**, even though the top-level decision stayed conservative.

It proves the most important semantic fact:

```text
UpdateLTM transform equivalence passed.
```

Observed evidence from G5.3:

```text
update_transform_rows = 870
params_hash_mismatch_count = 0
traffic_after_hash_mismatch_count = 0
C/F update-stat mismatch count = 0
true_semantic_mismatch_count = 0
```

This means the C/F dual-channel traffic-map transform is not corrupted. For the same:

```text
traffic_before
trace_events
UpdateParams
```

the runtime path and expected replay path produce the same `traffic_after` and the same C/F update stats.

The remaining failure is narrower:

```text
minimal_hook_time_budget_sensitivity
```

under the strict 3s closed-loop budget, concentrated in:

```text
map = warehouse-10-20-10-2-1
agents = 100
IDs = 146..155
```

G5.3 also showed:

```text
targeted warehouse/100 5s = passed
targeted warehouse/100 10s = passed
minimal-hook mismatches at 5s/10s = 0
true semantic mismatches = 0
dominant overhead component = cost_audit
```

Therefore, do not interpret G5.3 as:

```text
goal-aware dual-channel LTM failed
```

The correct interpretation is:

```text
The UpdateLTM transform is semantically safe.
The strict 3s exact minimal-hook reproduction gate is too sensitive for borderline warehouse/100 cases.
The project should now split:
  1. semantic replay / label infrastructure,
  2. budget-robust runtime benchmarking,
  3. learned UpdateLTM policy training readiness.
```

The project should stop treating 3s exact runtime-hook reproduction as the single gate for all downstream work. It remains a performance-stress gate for paper claims, but it should not block offline, observed-ID, diagnostic checkpoint/probe label construction now that transform equivalence has passed.

---

## 1. What this means for the research direction

The research direction remains:

```text
goal-aware dual-channel LTM
+
learned bounded UpdateLTM dynamics
```

not:

```text
learned MAPF action policy
```

The intended G6 method is still one of:

```text
safe mixture over validated UpdateLTM experts
learned abstention / fallback
bounded residual over flow-shield UpdateParams
```

Allowed learned outputs remain:

```text
bounded alpha_cong_* parameters
bounded alpha_flow_* parameters
bounded rho_* decay parameters
bounded flow_shield_beta
bounded max_flow_shield
safe expert mixture weights
abstention/fallback score
```

Forbidden outputs remain:

```text
agent actions
PIBT priorities
restart nodes
heuristic h_i(v)
candidate deletion
collision decisions
OPEN / EXPLORED / rewrite / incumbent decisions
```

G5.4 should move toward the learning target by collecting real counterfactual labels, not by training a model prematurely.

The causal label target is:

```text
same instance
same pre-update traffic_before
same trace_events

candidate A UpdateParams -> short-probe outcome A
candidate B UpdateParams -> short-probe outcome B
candidate C UpdateParams -> short-probe outcome C

compare candidate outcomes in the same context
```

---

## 2. Why G5.3 should unblock label infrastructure

Previous G5.2 gate order blocked checkpoints because runtime equivalence failed.

G5.3 refined that failure:

```text
transform equivalence passed
minimal-hook 3s exact reproduction failed only by time_budget_sensitivity
```

This distinction matters.

For counterfactual labels, the required invariant is transform/replay correctness, not 3s closed-loop exact reproduction under instrumentation overhead. Label generation can be explicitly marked:

```text
diagnostic-only
observed IDs only
not a runtime performance claim
not Phase5.5
not Phase6
```

Therefore G5.4 may reopen checkpoint/probe label infrastructure under strict constraints:

```text
allowed:
  observed IDs only
  transform-equivalence-backed checkpoints
  in-memory counterfactual probes
  replayability hashes
  no fresh IDs
  no learned runtime claim

still blocked:
  G6 training
  IDs 166..205
  learned-runtime fresh holdout
  AAAI-ready claims
```

---

## 3. Non-negotiable constraints

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
- run IDs 166..205
- train G6/G7 before counterfactual labels pass quality gates
- call static flow-shield a learned-method contribution
- hide the 3s warehouse/100 time-budget sensitivity
```

Allowed:

```text
- observed-ID semantic replay and checkpoint export
- in-memory counterfactual short probes from checkpoint traffic_before_map
- full sparse traffic-map export for reproducibility
- feature cost reduction
- budget-robust performance protocol design
- G6 safe mixture/residual readiness report only after labels pass
```

---

## 4. Split policy

Observed:

```text
IDs 1..25      support/training
IDs 26..45     G1/G2 development
IDs 46..65     G2 fresh final, now observed
IDs 66..105    G3 broader/protocol diagnostics, now observed
IDs 106..115   possible G3.1 diagnostic sentinel; audit before reuse
IDs 126..165   G4/G5/G5.1/G5.2/G5.3 observed diagnostics
```

Allowed in G5.4:

```text
primary checkpoint/probe label work:
  IDs 146..155 already used by G5.3
  optionally IDs 156..165 as observed extension

budget robustness confirmation:
  IDs 146..155 or 156..165 only

small debugging sentinel:
  any observed IDs <=165
```

Reserved:

```text
IDs 166..205:
  remain untouched.
  Do not run any command that expands or touches 166..205.
```

Add explicit guard tests that reject:

```text
--instance-ids 166
--instance-ids 166 167
--instance-ids 156 166
range including 166
```

---

## 5. Required work

### P0. Documentation and decision hygiene

Add this plan to repo root:

```text
czr004_repair5g54_semantic_replay_counterfactual_labels_plan.md
```

Update:

```text
docs/codex-worklog.md
```

Write:

```text
outputs/reports/phase5p5_repair5g53_final_interpretation.md
outputs/reports/phase5p5_repair5g54_protocol_overview.md
```

`phase5p5_repair5g53_final_interpretation.md` must state:

```text
- G5.3 is a positive diagnostic result.
- UpdateLTM transform equivalence passed.
- No evidence shows goal-aware dual-channel LTM corruption.
- The remaining primary 3s failure is minimal-hook time-budget sensitivity.
- The narrow failure set is warehouse/100 IDs 146..155.
- 5s and 10s targeted warehouse/100 checks passed.
- Checkpoint/probe label construction is allowed only as diagnostic observed-ID work, not as runtime promotion.
- G6 training remains blocked until true counterfactual labels pass quality gates.
- IDs 166..205 remain untouched.
```

Update AAAI readiness artifacts:

```text
update_transform_equivalence = passed
runtime_hook_3s_exact_equivalence = failed_time_budget_sensitivity
policy_controls = passed
checkpoint_labels = diagnostic_reopened_observed_only
learned_runtime_fresh_holdout = blocked_not_run
aaai_ready = false
phase5p5_allowed = false
phase6_allowed = false
```

### P1. Formalize semantic-vs-budget gate policy

Implement:

```text
scripts/write_repair5g54_semantic_vs_budget_gate_policy.py
```

Write:

```text
outputs/reports/phase5p5_repair5g54_semantic_vs_budget_gate_policy.md
outputs/reports/phase5p5_repair5g54_semantic_vs_budget_gate_policy_summary.json
```

The policy must distinguish:

```text
Hard semantic gate:
  UpdateLTM transform equivalence
  UpdateParams hash equivalence
  traffic_after hash equivalence
  C/F update-stat equivalence
  force-additive and disable controls

Budget-stress gate:
  3s exact minimal-hook reproduction
  5s/10s targeted sensitivity
  overhead attribution

Learning-label gate:
  replayable context availability
  same-context candidate probes
  leakage audit
  oracle gap over static
```

Do not let a classified 3s deadline flip block observed-ID diagnostic label collection once semantic replay passes.

### P2. Export replayable full/sparse traffic checkpoints

Current checkpoint exports are not enough if they only contain top-k edges. Implement a replayable export that includes all necessary traffic state.

Add or extend C++/Python support for:

```text
--repair5g-export-update-checkpoints-jsonl <path>
--repair5g-checkpoint-edge-filter all|nonzero
--repair5g-checkpoint-include-full-traffic true
```

Each checkpoint row must include:

```text
schema_version
map/scen/agents/seed/iteration
node_budget
time_remaining_sec
has_incumbent_before
best_ratio_before
best_ratio_after
returned_solutions_count_so_far
trace_events
current/applied UpdateParams fingerprint and hash
traffic_before full sparse C raw / C normalized / F raw / F normalized
traffic_after full sparse C raw / C normalized / F raw / F normalized
traffic_before_hash_full
traffic_after_hash_full
C/F update stats
cost audit summary
forbidden_feature_audit_passed
phase5p5_allowed=false
phase6_allowed=false
aaai_ready=false
```

Implement:

```text
scripts/run_repair5g54_checkpoint_export_observed.py
scripts/analyze_repair5g54_checkpoint_replayability.py
```

Gate:

```text
checkpoint_rows > 0
all rows observed IDs only
no IDs 166..205
traffic_before_hash_full present
traffic_after_hash_full present
trace_event_count present
UpdateParams hash present
replay transform from exported checkpoint reproduces traffic_after hash
no schema errors
```

### P3. Prefer in-memory counterfactual probes first

Because `DirectedTrafficMap` internals are C++ private and full JSON replay may be heavy, implement an in-memory counterfactual probe path inside the project-owned C++ runtime first.

Add:

```text
--repair5g-counterfactual-update-probe-jsonl <path>
--repair5g-counterfactual-candidates <comma-separated candidate IDs>
--repair5g-counterfactual-short-budget-ms <ms>
--repair5g-counterfactual-max-contexts <N>
```

During `iteration_callback`, use:

```text
run_one_shot_update_probe(
  instance,
  *checkpoint.traffic_before_map,
  checkpoint.trace_events,
  candidate UpdateParams
)
```

This already matches the causal label target:

```text
same traffic_before_map
same trace_events
candidate UpdateParams A/B/C
short-probe downstream outcome
```

Implement runners:

```text
scripts/run_repair5g54_counterfactual_update_probe_observed.py
scripts/analyze_repair5g54_counterfactual_labels.py
```

Candidate set:

```text
additive_ltm
repair5g2_best_frozen_static_candidate
repair5g2_frozen_static_or_selector
repair5g2_c_equiv_best_frozen_baseline
repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75
repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p5
repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75
```

The output label rows must include:

```text
context_id
candidate_id
resolved_candidate_id
UpdateParams hash/fingerprint
probe_solution_found
probe_feasible
probe_sum_of_loss
probe_lower_bound
probe_sum_of_loss_ratio
probe_runtime_ms
probe_expanded_nodes
probe_low_level_pibt_calls
delta_vs_additive_in_same_context
delta_vs_static_in_same_context
is_best_candidate_in_context
oracle_gap_vs_static
```

Gate:

```text
counterfactual_context_count > 0
candidate coverage complete
same-context labels exist for all candidates
no final full-run label leakage
runtime feature availability audit passes
oracle gap over static measured
at least one non-static candidate wins some contexts OR oracle gap report says static dominates
```

### P4. Oracle-gap and adaptive-value analysis

Implement:

```text
scripts/analyze_repair5g54_counterfactual_oracle_gap.py
```

Write:

```text
outputs/reports/phase5p5_repair5g54_counterfactual_oracle_gap.md
outputs/reports/phase5p5_repair5g54_counterfactual_oracle_gap_summary.json
outputs/tables/phase5p5_repair5g54_counterfactual_oracle_gap_by_map_agent.csv
outputs/tables/phase5p5_repair5g54_candidate_win_rates.csv
outputs/tables/phase5p5_repair5g54_context_feature_oracle_patterns.csv
```

Key questions:

```text
1. Does oracle best candidate beat static flow-shield in a meaningful fraction of contexts?
2. Does map-agent beat static because of adaptive map/agent selection or just warehouse fallback?
3. Are there contexts where C-equiv/additive is safer than flow-shield?
4. Are flow-shield beta/max variants context-dependent?
5. Is there enough adaptive gap to justify G6 safe mixture/residual learning?
```

Decision implications:

```text
If oracle_best_safe_candidate improves over static:
  continue G6 safe mixture policy design.

If static dominates every context:
  do not train a selector; design residual parameter perturbations or broaden candidate space.

If labels are too noisy:
  collect more observed contexts or improve probe budget before training.
```

### P5. Budget-robust runtime protocol

Implement:

```text
scripts/run_repair5g54_budget_robust_runtime_protocol.py
scripts/analyze_repair5g54_budget_robust_runtime_protocol.py
```

Observed IDs only. Compare:

```text
fixed static/map-agent
minimal hook static/map-agent
perf-mode selector path
audit-mode selector path
```

Budgets:

```text
3s primary stress
5s targeted robustness
10s targeted robustness
optional fixed-node-budget diagnostic if supported
```

Write:

```text
outputs/reports/phase5p5_repair5g54_budget_robust_runtime_protocol.md
outputs/reports/phase5p5_repair5g54_budget_robust_runtime_summary.json
```

This is not a G6 performance claim. It only defines how future learned runtime results should be judged:

```text
performance mode only for runtime claims
audit mode only for diagnostics
3s strict stress is reported separately from semantic correctness
5s/10s robustness distinguishes true policy harm from borderline deadline flips
```

### P6. G6 readiness report, but no training yet

Only if P2/P3/P4 pass, write:

```text
outputs/reports/phase5p5_repair5g54_g6_safe_mixture_readiness.md
outputs/reports/phase5p5_repair5g54_g6_safe_mixture_readiness_summary.json
```

Do not train a model in G5.4.

The G6 readiness report should specify:

```text
input features allowed at runtime
forbidden features
candidate experts
fallback policy
confidence/abstention policy
training labels
train/dev observed-ID split
fresh IDs still reserved
runtime performance protocol
```

### P7. Final decision

Write:

```text
outputs/reports/phase5p5_repair5g54_decision.md
outputs/reports/phase5p5_repair5g54_decision_summary.json
```

Decision options:

```text
semantic_replay_policy_failed
checkpoint_export_failed
checkpoint_replayability_failed
counterfactual_labels_unavailable
counterfactual_labels_available_static_dominates
counterfactual_labels_available_adaptive_gap_found
continue_g6_safe_mixture_design
continue_candidate_space_expansion_before_g6
stop_for_protocol_or_semantic_bug
```

Required final fields:

```json
{
  "update_transform_equivalence_prior": "passed_g53",
  "runtime_3s_minimal_hook_status": "failed_time_budget_sensitivity_g53",
  "checkpoint_export_passed": true,
  "checkpoint_replayability_passed": true,
  "counterfactual_labels_available": true,
  "oracle_gap_over_static_measured": true,
  "g6_training_allowed": false,
  "g6_design_allowed": true,
  "ids_166_205_untouched": true,
  "phase5p5_allowed": false,
  "phase6_allowed": false,
  "aaai_ready": false
}
```

Adjust booleans honestly based on results.

---

## 6. Validation

Run:

```text
python -m py_compile <all new/modified Python scripts>
```

If C++ changed:

```text
scripts/build_phase1a_batch.ps1
```

Run focused tests if pytest exists. If not, write and run a manual fallback harness.

Required tests:

```text
reserved-ID guard rejects 166
semantic-vs-budget policy JSON validates
checkpoint schema validates
counterfactual label schema validates
candidate coverage complete
no action/restart/priority/candidate-deletion fields
```

Run:

```text
git diff --check
```

Commit and push only G5.4-related tracked files and reports. Leave unrelated dirty/untracked files untouched.

Commit message:

```text
repair5g: collect semantic replay counterfactual update labels
```

---

# Codex Prompt

Continue czr004 on branch `phase4f5p5-stable-attention-lau` after commit `60acc92 repair5g: isolate updatepolicy overhead and validate transform equivalence`.

Goal:
Implement Repair5G.5.4: split semantic replay from 3s budget sensitivity, reopen observed-ID diagnostic checkpoint/probe infrastructure after G5.3 transform equivalence passed, collect true same-context counterfactual UpdateLTM labels for goal-aware dual-channel LTM, and produce an oracle-gap/G6-readiness report. Do not train G6. Do not run IDs 166..205.

Main project objective:
Use learning-enhanced UpdateLTM to replace the coarse additive update in the LTM paper and eventually beat LaCAM*+plain additive LTM under closed-loop solver metrics, without changing LaCAM*/PIBT semantics.

Read first:
  deep-research-report.md
  phase4_6_laur_ltm_codex_execution_plan.md
  docs/aaai_quality_requirements.md
  czr004_repair5g53_overhead_neutral_runtime_hook_plan.md
  outputs/reports/phase5p5_repair5g53_decision.md
  outputs/reports/phase5p5_repair5g53_decision_summary.json
  outputs/reports/phase5p5_repair5g53_protocol_overview.md
  outputs/reports/phase5p5_repair5g53_update_transform_equivalence_summary.json
  outputs/reports/phase5p5_repair5g53_hook_overhead_ablation_summary.json
  outputs/reports/phase5p5_repair5g53_runtime_feature_cost_audit_summary.json

Preserve this interpretation:
  - G5.3 is a positive diagnostic result.
  - UpdateLTM transform equivalence passed:
      rows = 870
      params hash mismatches = 0
      traffic-after hash mismatches = 0
      C/F update-stat mismatches = 0
      true semantic mismatches = 0
  - The goal-aware dual-channel traffic-map transform is not corrupted.
  - The remaining primary 3s failure is minimal_hook_time_budget_sensitivity.
  - The narrow failure set is warehouse-10-20-10-2-1, 100 agents, IDs 146..155.
  - Targeted warehouse/100 5s and 10s checks passed with 0 minimal-hook mismatches.
  - Dominant overhead component is cost_audit.
  - Fixed static/map-agent flow-shield remains a strong baseline.
  - Checkpoint/probe label construction is now allowed only as observed-ID diagnostic infrastructure because semantic transform equivalence passed.
  - Runtime learned performance claims remain blocked.
  - G6 training remains blocked until true counterfactual labels pass quality gates.
  - IDs 166..205 remain untouched.
  - phase5p5_allowed=false, phase6_allowed=false, aaai_ready=false remain mandatory.

Do not:
  - modify external/lacam2/lacam2/**
  - change PIBT, LaCAM*, candidate generation, conflict, pruning, OPEN/EXPLORED, rewrite, incumbent, or restart semantics
  - introduce action prediction
  - introduce learned restart
  - output h_i(v), action logits, priority overrides, or candidate deletion
  - claim Phase5.5 or Phase6
  - claim AAAI-ready
  - run IDs 166..205
  - train a learned selector, safe mixture, residual, MLP, GNN, or transformer in this round
  - call static flow-shield a learned-method contribution
  - treat 3s warehouse/100 deadline sensitivity as dual-channel LTM corruption

Tasks:
  1. Add `czr004_repair5g54_semantic_replay_counterfactual_labels_plan.md` to repo root and update `docs/codex-worklog.md`.

  2. Write:
     `outputs/reports/phase5p5_repair5g53_final_interpretation.md`
     `outputs/reports/phase5p5_repair5g54_protocol_overview.md`

  3. Write a semantic-vs-budget gate policy:
     `scripts/write_repair5g54_semantic_vs_budget_gate_policy.py`
     `outputs/reports/phase5p5_repair5g54_semantic_vs_budget_gate_policy.md`
     `outputs/reports/phase5p5_repair5g54_semantic_vs_budget_gate_policy_summary.json`

     The policy must distinguish semantic transform gates, budget-stress gates, and learning-label gates.

  4. Implement replayable checkpoint export on observed IDs only:
     `scripts/run_repair5g54_checkpoint_export_observed.py`
     `scripts/analyze_repair5g54_checkpoint_replayability.py`

     Export full sparse traffic state, not only top-k edges:
       C raw, C normalized, F raw, F normalized
       trace_events
       UpdateParams hash/fingerprint
       traffic_before_hash_full
       traffic_after_hash_full
       C/F update stats

  5. Implement in-memory counterfactual UpdateLTM probe labels:
     Add C++/runner support if needed:
       `--repair5g-counterfactual-update-probe-jsonl <path>`
       `--repair5g-counterfactual-candidates <comma-separated candidate IDs>`
       `--repair5g-counterfactual-short-budget-ms <ms>`
       `--repair5g-counterfactual-max-contexts <N>`

     Use `run_one_shot_update_probe(instance, *checkpoint.traffic_before_map, checkpoint.trace_events, candidate_options)` inside the project-owned callback path.

     Scripts:
       `scripts/run_repair5g54_counterfactual_update_probe_observed.py`
       `scripts/analyze_repair5g54_counterfactual_labels.py`

  6. Candidate set:
       additive_ltm
       repair5g2_best_frozen_static_candidate
       repair5g2_frozen_static_or_selector
       repair5g2_c_equiv_best_frozen_baseline
       repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75
       repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p5
       repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75

  7. Analyze oracle gap:
       `scripts/analyze_repair5g54_counterfactual_oracle_gap.py`
       `outputs/reports/phase5p5_repair5g54_counterfactual_oracle_gap.md`
       `outputs/reports/phase5p5_repair5g54_counterfactual_oracle_gap_summary.json`
       `outputs/tables/phase5p5_repair5g54_counterfactual_oracle_gap_by_map_agent.csv`
       `outputs/tables/phase5p5_repair5g54_candidate_win_rates.csv`

  8. Define budget-robust runtime protocol:
       `scripts/run_repair5g54_budget_robust_runtime_protocol.py`
       `scripts/analyze_repair5g54_budget_robust_runtime_protocol.py`
       `outputs/reports/phase5p5_repair5g54_budget_robust_runtime_protocol.md`
       `outputs/reports/phase5p5_repair5g54_budget_robust_runtime_summary.json`

     This is diagnostic only, not a G6 runtime claim.

  9. Only if checkpoint replayability and counterfactual labels pass, write G6 readiness only:
       `outputs/reports/phase5p5_repair5g54_g6_safe_mixture_readiness.md`
       `outputs/reports/phase5p5_repair5g54_g6_safe_mixture_readiness_summary.json`

     Do not train G6.

  10. Write:
       `outputs/reports/phase5p5_repair5g54_decision.md`
       `outputs/reports/phase5p5_repair5g54_decision_summary.json`

Decision options:
  semantic_replay_policy_failed
  checkpoint_export_failed
  checkpoint_replayability_failed
  counterfactual_labels_unavailable
  counterfactual_labels_available_static_dominates
  counterfactual_labels_available_adaptive_gap_found
  continue_g6_safe_mixture_design
  continue_candidate_space_expansion_before_g6
  stop_for_protocol_or_semantic_bug

Validation:
  python -m py_compile all new/modified Python scripts
  if C++ changed, run scripts/build_phase1a_batch.ps1
  pytest focused G5.4 tests if available; otherwise manual fallback harness
  reserved-ID guard must reject 166
  JSON summaries validate
  git diff --check
  commit and push only G5.4-related tracked files and reports
  leave unrelated dirty/untracked files untouched

Commit message:
  repair5g: collect semantic replay counterfactual update labels
