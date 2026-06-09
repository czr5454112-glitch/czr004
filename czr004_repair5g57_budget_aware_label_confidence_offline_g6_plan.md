# czr004 Repair5G.5.7 Plan: Budget-Aware Counterfactual Label Confidence and Offline G6 Safe-Mixture Gate

**Branch:** `phase4f5p5-stable-attention-lau`
**Start after commit:** `6b43301 repair5g: prepare budget-stable g6 safe mixture prototype`
**Status:** proposed next diagnostic/research wave after G5.6 passed label completion but blocked G6 training on overly small all-budget-stable subset
**Promotion status:** `phase5p5_allowed=false`, `phase6_allowed=false`
**AAAI status:** `aaai_ready=false`
**Main project objective:** use learning-enhanced `UpdateLTM` to replace the coarse additive update in the LTM paper and eventually beat `LaCAM*+plain additive LTM` under closed-loop solver metrics, without changing LaCAM*/PIBT semantics.

---

## 0. Executive interpretation

G5.6 is not a direction failure. It is a **good diagnostic result with a conservative training block**.

Preserve the key facts:

```text
G5.6 decision:
  probe_budget_instability_blocks_training

Label completion:
  context_count = 140
  label_rows = 980
  candidate_count = 7
  later_iteration_context_count = 20
  map/agent coverage complete = true
  checkpoint replayability still passes = true
  observed IDs only = true
  IDs 166..205 untouched = true

Adaptive gap:
  oracle_beats_static_contexts = 54
  oracle_beats_static_fraction = 0.38571428571428573
  mean_oracle_gap_over_static = -0.01113516710276

Probe-budget stability:
  measured_contexts = 30
  training_eligible_stable_contexts = 4
  unstable_contexts = 26
  budget grid = 250 / 500 / 1000 / 2000 ms

Warehouse classification:
  warehouse_contexts = 40
  no_solution_all_candidates = 35
  budget_sensitive_solution = 5

Feature policy:
  perf_feature_allowlist_passed = true
  cost_min / cost_max / cost_span / cost_bounds_respected are audit-only

Training:
  G6 targets not training ready
  offline G6 training skipped correctly
  phase5p5_allowed=false
  phase6_allowed=false
  aaai_ready=false
```

Correct interpretation:

```text
Good:
  The counterfactual label bank now has enough observed-ID coverage for serious analysis.
  It includes all three maps, both agent counts, 140 contexts, 980 labels, and 20 later-iteration contexts.
  Static flow-shield still does not dominate all contexts.
  Adaptive oracle gap remains meaningful.
  Feature leakage / runtime availability are controlled.
  Warehouse failures were classified instead of hidden.

Bad / blocker:
  The current all-budget stability rule is too strict for training permission.
  Only 4 contexts are stable across 250/500/1000/2000 ms.
  Many 250 ms probes appear to be solver-time artifacts rather than stable UpdateLTM preferences.
  Warehouse contexts are mostly no-solution at the current probe setup.

Scientific conclusion:
  Goal-aware dual-channel LTM is still valid.
  The learning direction is still valid.
  The next problem is label-confidence modeling and budget-aware training eligibility, not abandoning the method.
```

G5.7 must therefore separate:

```text
1. micro-budget stress instability at 250 ms;
2. primary-label stability at 1000/2000 ms;
3. no-solution / infeasible probe contexts;
4. stable high-margin contexts suitable for offline G6;
5. abstention/static-fallback contexts suitable for conservative policy learning.
```

Do **not** require every label to be stable across 250 ms before any offline learning can be considered. A 250 ms probe is a stress diagnostic, not necessarily the correct training target for a downstream UpdateLTM policy.

---

## 1. Why G5.6 does not contradict the grand plan

The grand plan wants learning-enhanced `UpdateLTM`, not learned MAPF actions. G5.6 is aligned with that because all labels are same-context counterfactual UpdateLTM probes:

```text
same traffic_before
same trace_events
candidate UpdateParams A/B/C
short-probe outcome A/B/C
```

The evidence still favors goal-aware dual-channel LTM:

```text
additive_ltm oracle_win_rate = 0.0
C-equiv oracle_win_rate = 0.0
flow-shield variants dominate oracle wins
static flow-shield remains strong but not universally optimal
```

The problem is not that C/F dual-channel traffic map failed. The problem is that short-horizon MAPF probes are noisy and time-budget-dependent, especially at 250 ms and in warehouse/100-like no-solution regimes. This must be handled with confidence, abstention, and stable-label filters.

---

## 2. Main research questions for G5.7

G5.7 must answer:

```text
Q1. If 250 ms is treated as stress-only, how many contexts are stable between 1000 and 2000 ms?

Q2. If 500 ms is included only when it agrees with 1000/2000 ms, how many training-eligible contexts remain?

Q3. Are adaptive oracle wins high-margin enough to train a safe mixture policy, or mostly low-margin/noisy?

Q4. Can unstable contexts be converted into abstain-to-static labels rather than discarded?

Q5. Are warehouse no-solution contexts best treated as abstain/static/additive fallback cases, or do they require longer probe budgets / separate solver settings?

Q6. Is there enough stable, high-margin, nonstatic evidence to train a tiny offline diagnostic G6 model?

Q7. If offline G6 is trained, does it beat static fallback on observed dev contexts and beat random/shuffled controls without using forbidden features?
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
- use final full-run outcomes as per-update labels
- train or integrate a runtime C++ learned policy in this round
- hide 250 ms probe instability
- hide warehouse no-solution contexts
- use audit-only cost features in runtime/performance-safe model variants
```

Allowed:

```text
- observed-ID counterfactual label analysis and additional observed-ID probes
- budget-aware label-confidence modeling
- reclassifying 250 ms as stress-only if evidence supports it
- abstention/static-fallback target construction
- tiny offline diagnostic G6 training only if stable-label gates pass
- random-feature and shuffled-label controls
- design of later runtime preflight only if offline G6 passes
```

---

## 4. Split policy

Observed IDs remain available for diagnostic label analysis only:

```text
1..25      observed support/training
26..45     observed G1/G2 development
46..65     observed G2 final
66..105    observed G3 diagnostics
106..115   possible observed sentinel; audit before reuse
126..165   observed G4/G5/G5.1/G5.2/G5.3/G5.4/G5.5/G5.6
```

Reserved IDs:

```text
166..205:
  must remain untouched.
  do not use for labels, model training, hyperparameter selection, debugging, command dry-runs, or peeking.
```

Recommended G5.7 split:

```text
observed_train/dev only:
  use existing G5.6 contexts first
  optionally add more observed contexts <=165 if needed for budget confidence

no fresh holdout:
  G5.7 is not a fresh validation result.
```

---

## 5. Required work

### P0. Documentation and decision hygiene

Add this plan to repo root:

```text
czr004_repair5g57_budget_aware_label_confidence_offline_g6_plan.md
```

Update:

```text
docs/codex-worklog.md
```

Write:

```text
outputs/reports/phase5p5_repair5g56_final_interpretation.md
outputs/reports/phase5p5_repair5g57_protocol_overview.md
```

Required interpretation:

```text
G5.6 passed label completion and feature allowlist.
G5.6 failed training permission due to budget instability.
The instability should be analyzed by budget tier, not treated as a method failure.
Goal-aware dual-channel LTM remains valid.
G6 training remains blocked until budget-aware label-confidence gates pass.
```

---

### P1. Budget-tier stability analysis

Implement:

```text
scripts/analyze_repair5g57_budget_tier_stability.py
```

Inputs:

```text
outputs/tables/phase5p5_repair5g56_probe_budget_rank_stability.csv
outputs/tables/phase5p5_repair5g56_counterfactual_update_labels.csv
outputs/tables/phase5p5_repair5g56_oracle_by_context.csv
```

Analyze separately:

```text
stress budget:
  250 ms

mid budget:
  500 ms

primary training budget:
  1000 ms

sentinel budget:
  2000 ms
```

Compute:

```text
oracle agreement 1000 vs 2000
oracle agreement 500 vs 1000/2000
static-vs-oracle sign agreement 1000 vs 2000
candidate rank top1/top2/top3 agreement
per-context no-solution pattern by budget
candidate feasibility by budget
margin stability by budget
```

Outputs:

```text
outputs/reports/phase5p5_repair5g57_budget_tier_stability.md
outputs/reports/phase5p5_repair5g57_budget_tier_stability_summary.json
outputs/tables/phase5p5_repair5g57_budget_tier_stability_by_context.csv
outputs/tables/phase5p5_repair5g57_budget_tier_stability_by_map_agent.csv
```

Gate:

```text
budget_tier_stability_analyzed = true
primary_1000_2000_stable_contexts_count reported
stress_250_disagreement_rate reported
no_solution_by_budget_reported = true
```

---

### P2. Confidence-weighted label construction

Implement:

```text
scripts/create_repair5g57_confidence_weighted_labels.py
scripts/analyze_repair5g57_confidence_weighted_labels.py
```

Construct label classes:

```text
stable_high_confidence_nonstatic:
  1000/2000 agree on nonstatic oracle
  oracle beats static by margin >= margin_threshold
  candidate feasible at primary budget

stable_static:
  1000/2000 agree static is best or nonstatic margin too small

abstain_to_static:
  unstable oracle identity but static is feasible and non-harmful

no_solution_abstain:
  no candidate reliably solves under primary/sentinel budget

budget_sensitive:
  1000 and 2000 disagree or feasibility changes

exclude_from_training:
  corrupted / missing / forbidden / unclassifiable
```

Suggested initial thresholds:

```text
margin_thresholds = {0.0025, 0.005, 0.010}
primary budgets = 1000 and 2000 ms
250 ms = stress-only by default
500 ms = optional agreement bonus, not hard gate
```

Outputs:

```text
outputs/tables/phase5p5_repair5g57_confidence_weighted_labels.csv
outputs/reports/phase5p5_repair5g57_confidence_weighted_label_summary.json
outputs/reports/phase5p5_repair5g57_confidence_weighted_label_report.md
```

Gates:

```text
confidence_labels_created = true
training_eligible_contexts_count reported
stable_high_confidence_nonstatic_count reported
stable_static_count reported
abstain_to_static_count reported
no_solution_abstain_count reported
budget_sensitive_count reported
```

Training permission threshold:

```text
training_eligible_contexts >= 30
stable_high_confidence_nonstatic_count >= 10
stable_static_or_abstain_count >= 10
```

If these fail, do not train. Recommend additional observed-ID probes or revised candidate/probe budget.

---

### P3. Warehouse / no-solution policy refinement

Implement:

```text
scripts/analyze_repair5g57_warehouse_no_solution_policy.py
```

Inputs:

```text
outputs/reports/phase5p5_repair5g56_warehouse_probe_failure_summary.json
outputs/tables/phase5p5_repair5g56_warehouse_probe_failure_cases.csv
outputs/tables/phase5p5_repair5g56_probe_budget_rank_stability.csv
```

Determine whether warehouse contexts should become:

```text
no_solution_abstain
longer_budget_needed
separate_warehouse_specialist_later
candidate_space_gap
valid_flat_static_default
```

Outputs:

```text
outputs/reports/phase5p5_repair5g57_warehouse_no_solution_policy.md
outputs/reports/phase5p5_repair5g57_warehouse_no_solution_policy_summary.json
outputs/tables/phase5p5_repair5g57_warehouse_context_policy.csv
```

Gate:

```text
warehouse_policy_classified = true
warehouse_contexts_not_silently_dropped = true
```

---

### P4. G6 offline feature matrix variants

Implement:

```text
scripts/create_repair5g57_g6_offline_feature_matrices.py
scripts/analyze_repair5g57_g6_feature_matrix_quality.py
```

Build two feature variants:

```text
perf_safe_only:
  use only phase5p5_repair5g56_perf_feature_allowlist_summary.json perf_safe_features

audit_plus_perf:
  diagnostic only; may include audit-only cost features, never for runtime claim
```

Forbidden features remain:

```text
future outcome
probe result
oracle score
candidate label
traffic_after
actions
priorities
restart
h-values
candidate deletion
```

Outputs:

```text
outputs/tables/phase5p5_repair5g57_g6_features_perf_safe.csv
outputs/tables/phase5p5_repair5g57_g6_features_audit_plus_perf.csv
outputs/reports/phase5p5_repair5g57_g6_feature_matrix_summary.json
```

Gates:

```text
perf_safe_feature_matrix_passed = true
audit_plus_perf_marked_diagnostic_only = true
forbidden_feature_count = 0
```

---

### P5. Offline G6 training only if P1-P4 gates pass

If and only if confidence-weighted labels pass training thresholds, implement:

```text
scripts/train_repair5g57_offline_safe_mixture.py
scripts/eval_repair5g57_offline_safe_mixture.py
```

Allowed models:

```text
calibrated multinomial logistic regression
small MLP <= 64 hidden units
static-fallback abstention model
```

Forbidden:

```text
GNN/Transformer
runtime C++ integration
fresh IDs
continuous arbitrary parameter output
```

Baselines:

```text
static flow-shield
map-agent selector
always additive
majority expert
random features
shuffled labels
oracle upper bound
```

Evaluation metrics:

```text
mean selected-vs-static delta on observed dev
mean selected-vs-additive delta
oracle regret
harmful-vs-static rate
abstention rate
nonstatic selection rate
beats random/shuffled controls
calibration / confidence bins
```

Outputs:

```text
artifacts/models/laur_ltm/repair5g57_offline_safe_mixture/
outputs/reports/phase5p5_repair5g57_offline_safe_mixture_report.md
outputs/reports/phase5p5_repair5g57_offline_safe_mixture_summary.json
outputs/tables/phase5p5_repair5g57_offline_safe_mixture_eval.csv
```

Training gate:

```text
offline_g6_mean_delta_vs_static < 0
harmful_vs_static_rate <= conservative threshold
beats_random_features = true
beats_shuffled_labels = true
static_fallback_available = true
observed_dev_only = true
```

If training thresholds fail, decision must be `offline_g6_safe_mixture_failed_continue_label_confidence_or_candidate_space`.

---

### P6. Final decision

Write:

```text
outputs/reports/phase5p5_repair5g57_decision.md
outputs/reports/phase5p5_repair5g57_decision_summary.json
```

Decision options:

```text
budget_tier_analysis_failed
confidence_labels_insufficient_continue_probe_design
warehouse_no_solution_policy_blocks_training
perf_feature_matrix_failed
offline_g6_not_run_training_gate_failed
offline_g6_safe_mixture_failed_continue_label_confidence_or_candidate_space
offline_g6_safe_mixture_passed_continue_runtime_preflight_design
candidate_space_gap_expand_flow_shield_lattice
probe_budget_protocol_needs_revision
stop_for_protocol_or_semantic_bug
```

Required final fields:

```text
context_count
label_rows
primary_1000_2000_stable_contexts
training_eligible_contexts
stable_high_confidence_nonstatic_count
stable_static_or_abstain_count
warehouse_policy
offline_training_run
offline_g6_passed
ids_166_205_untouched
phase5p5_allowed=false
phase6_allowed=false
aaai_ready=false
runtime_claim_allowed=false
```

---

## 6. Validation

Required validation:

```text
python -m py_compile all new/modified Python scripts
if C++ changed, run scripts/build_phase1a_batch.ps1
pytest focused G5.7 tests if available; otherwise manual fallback harness
reserved-ID guard rejects 166
JSON summaries parse
CSV row-count sanity checks pass
git diff --check
```

Commit and push only G5.7-related tracked files/reports. Leave unrelated dirty/untracked files untouched.

Suggested commit message:

```text
repair5g: add budget-aware label confidence and offline g6 gate
```

---

## 7. Success criteria

A good G5.7 outcome is **not necessarily training a model**.

Good outcomes include:

```text
A. confidence_labels_insufficient_continue_probe_design
   if 1000/2000 labels remain unstable or too sparse;

B. candidate_space_gap_expand_flow_shield_lattice
   if stable labels exist but candidate experts are too coarse;

C. offline_g6_safe_mixture_passed_continue_runtime_preflight_design
   only if stable labels are enough and controls pass.
```

Bad outcome:

```text
forcing G6 training on 4 stable contexts
or treating 250 ms stress instability as proof that learning direction failed
or using fresh IDs before a frozen runtime design exists
```
