# czr004 Repair5G.5.5 Plan: Scale Same-Context Counterfactual Labels and Prepare G6 Safe Mixture/Residual UpdateLTM

**Branch:** `phase4f5p5-stable-attention-lau`
**Start after commit:** `2754692 repair5g: collect semantic replay counterfactual update labels`
**Status:** proposed next diagnostic/research wave after G5.4 produced true same-context counterfactual UpdateLTM labels
**Promotion status:** `phase5p5_allowed=false`, `phase6_allowed=false`
**AAAI status:** `aaai_ready=false`
**Main project objective:** use learning-enhanced `UpdateLTM` to replace the coarse additive update in the LTM paper and eventually beat `LaCAM*+plain additive LTM` under closed-loop solver metrics, without changing LaCAM*/PIBT semantics.

---

## 0. Executive interpretation

G5.4 is the first genuinely positive learning-infrastructure result after the G5 runtime selector failure.

It proves that the project can now create true same-context counterfactual labels:

```text
same instance
same pre-update traffic_before
same trace_events
same candidate set
candidate UpdateParams A -> short-probe outcome A
candidate UpdateParams B -> short-probe outcome B
candidate UpdateParams C -> short-probe outcome C
```

Key G5.4 facts to preserve:

```text
Decision:
  counterfactual_labels_available_adaptive_gap_found

checkpoint_export_passed:
  true

checkpoint_replayability_passed:
  true

counterfactual_labels_available:
  true

oracle_gap_over_static_measured:
  true

G6 design allowed:
  true

G6 training allowed:
  false

IDs 166..205:
  untouched

phase5p5_allowed:
  false

phase6_allowed:
  false

aaai_ready:
  false
```

G5.4 also confirms the earlier G5.3 interpretation:

```text
UpdateLTM transform equivalence passed.
The C/F dual-channel traffic-map transform is not corrupted.
The remaining 3s minimal-hook issue is warehouse/100 deadline sensitivity, not a semantic UpdateLTM bug.
```

This is a major forward step toward the grand-plan route:

```text
goal-aware dual-channel LTM
+
learned bounded UpdateLTM dynamics
```

But it is not yet enough to train or claim a learned method. The current label set is only a smoke proof:

```text
contexts = 2
label rows = 14
candidate count = 7
map/agent coverage = random-32-32-20, 50 agents only
oracle beats static contexts = 1 / 2
mean oracle gap over static = -0.01075268817199998
```

Therefore G5.5 must scale labels and measure whether the adaptive oracle gap survives across maps, agents, seeds, iterations, and probe budgets. Do not train G6 until label coverage and quality gates pass.

---

## 1. Correct scientific interpretation

Do not interpret G5.4 as:

```text
We already have a learned runtime UpdateLTM method.
```

Correct interpretation:

```text
We now have the first working causal-label infrastructure for learning UpdateLTM.
```

Do not interpret the tiny adaptive gap as paper-grade evidence.

Correct interpretation:

```text
The adaptive gap exists in at least one same-context probe.
Now we must test whether it is broad enough to justify G6 safe mixture/residual learning.
```

Do not interpret G5.3/G5.4 as evidence against goal-aware dual-channel LTM.

Correct interpretation:

```text
Static/map-agent flow-shield remains a strong baseline.
Transform equivalence passed.
Replayability passed.
The open question is whether a learned policy can choose or perturb safe dual-channel UpdateParams better than static flow-shield across contexts.
```

---

## 2. G5.5 research questions

G5.5 must answer these questions before G6 training:

```text
Q1. Does oracle best safe UpdateParams beat fixed static flow-shield often enough to justify learning?

Q2. Which contexts need adaptation?
    map family
    agent count
    LTM iteration
    trace density
    blocked/committed/wait ratios
    C/F traffic state

Q3. Which candidate families win?
    static flow-shield
    map-agent flow-shield
    alternative flow-shield beta/max/rho
    C-equiv fallback
    additive fallback

Q4. Is the oracle gap stable under short-probe budget changes?
    250 ms
    500 ms
    1000 ms
    optional 2000 ms sentinel

Q5. Are labels learnable from allowed runtime features?
    no action features
    no restart features
    no future final-run outcome leakage
    no forbidden solver-state fields

Q6. Is the first G6 method better framed as:
    safe expert mixture
    abstention selector
    bounded residual over flow-shield parameters
    or candidate-space expansion before learning?
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
- train G6 before scaled counterfactual label gates pass
- treat static flow-shield as a learned-method contribution
- use final full-run outcomes as per-update labels
- hide the fact that G5.4 labels currently cover only two contexts
```

Allowed:

```text
- observed-ID semantic replay and checkpoint/probe label collection
- observed-ID stratified label scaling over IDs <=165
- budget sensitivity diagnostics for probe labels
- oracle gap analysis
- feature availability / leakage audits
- G6 safe-mixture/residual design reports
- optional tiny offline diagnostic classifier only if label scaling gates pass, marked not runtime and not Phase5.5
```

---

## 4. Split policy

Observed IDs:

```text
1..25      support/training
26..45     G1/G2 development
46..65     G2 fresh final, now observed
66..105    G3 broader/protocol diagnostics, now observed
106..115   possible G3.1 diagnostic sentinel; audit before reuse
126..165   G4/G5/G5.1/G5.2/G5.3/G5.4 observed diagnostics
146..155   G5.2/G5.3/G5.4 latest observed smoke
156..165   allowed observed extension
```

Reserved:

```text
166..205
  remain untouched for later learned-runtime fresh validation.
  Do not use for G5.5 label scaling, G6 training, hyperparameter selection, or diagnostic peeking.
```

G5.5 label scaling may use:

```text
Primary observed extension:
  IDs 146..165

Optional broader observed pool after audit:
  IDs 126..165
  optionally <=165 if compute is needed for train/dev splits
```

No result from G5.5 is a fresh validation result.

---

## 5. Required work

### P0. Documentation and decision hygiene

Add this plan to repo root:

```text
czr004_repair5g55_scaled_counterfactual_g6_design_plan.md
```

Update:

```text
docs/codex-worklog.md
```

Write:

```text
outputs/reports/phase5p5_repair5g54_final_interpretation.md
outputs/reports/phase5p5_repair5g55_protocol_overview.md
```

Required interpretation:

```text
G5.4 succeeded as label-infrastructure proof.
G5.4 did not train G6.
G5.4 did not make a learned-runtime performance claim.
G5.4 labels are too small for training.
G5.5 must scale labels and measure oracle gap.
Goal-aware dual-channel LTM is not corrupted.
IDs 166..205 remain untouched.
phase5p5_allowed=false, phase6_allowed=false, aaai_ready=false.
```

### P1. Label-scaling runner

Implement:

```text
scripts/run_repair5g55_scaled_counterfactual_labels.py
scripts/analyze_repair5g55_scaled_counterfactual_labels.py
```

Inputs should include:

```text
maps = random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
agents = 50,100
instance_ids = 146..165 by default
ltm_max_iterations = 4
primary short_budget_ms = 1000
optional budgets = 250,500,1000,2000
max_contexts_per_group configurable
candidate set configurable
```

Output:

```text
outputs/logs/phase5p5_repair5g55_scaled_counterfactual_labels/...
outputs/tables/phase5p5_repair5g55_counterfactual_update_labels.csv
outputs/tables/phase5p5_repair5g55_counterfactual_contexts.csv
outputs/reports/phase5p5_repair5g55_counterfactual_label_quality.md
outputs/reports/phase5p5_repair5g55_counterfactual_label_quality_summary.json
```

Required gates:

```text
observed_ids_only = true
ids_166_205_untouched = true
context_count >= 60 minimum smoke; target >= 120 if compute allows
label_rows = context_count * candidate_count
candidate_coverage_complete = true
same_context_labels_exist_for_all_candidates = true
feature_leakage_audit_passes = true
runtime_feature_availability_audit_passes = true
no_final_full_run_label_leakage = true
map_agent_coverage_complete = true
nonzero_trace_context_fraction > 0
checkpoint_replayability_still_passes = true
```

If compute is tight, run a stratified smoke first and write the exact missing coverage.

### P2. Candidate-set expansion audit

Implement:

```text
scripts/create_repair5g55_candidate_set.py
scripts/analyze_repair5g55_candidate_set.py
```

Start candidate set:

```text
additive_ltm
repair5g2_best_frozen_static_candidate
repair5g2_frozen_static_or_selector
repair5g2_c_equiv_best_frozen_baseline
repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75
repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p5
repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75
```

Add a small bounded local lattice around validated flow-shield only if runtime registry supports it:

```text
rho_decay in {0.90, 0.95, 1.00}
flow_shield_beta in {0.20, 0.35, 0.50}
max_flow_shield in {0.50, 0.75}
alpha_commit/block/wait around validated values only
```

Do not explode the candidate space. The goal is to estimate adaptive gap, not brute-force tune a benchmark.

### P3. Oracle gap and adaptivity analysis

Implement:

```text
scripts/analyze_repair5g55_oracle_gap.py
```

Outputs:

```text
outputs/reports/phase5p5_repair5g55_oracle_gap.md
outputs/reports/phase5p5_repair5g55_oracle_gap_summary.json
outputs/tables/phase5p5_repair5g55_oracle_by_context.csv
outputs/tables/phase5p5_repair5g55_oracle_gap_by_map_agent_iteration.csv
outputs/tables/phase5p5_repair5g55_candidate_win_rates.csv
outputs/tables/phase5p5_repair5g55_static_failure_contexts.csv
```

Required metrics:

```text
mean oracle gap over static
median oracle gap over static
oracle_beats_static_fraction
oracle_beats_additive_fraction
static_dominates_all_contexts
candidate win rates
candidate regret distribution
by map/agent/iteration
by trace density
by blocked-per-committed
by wait-event ratio
by traffic C/F state
```

Decision rule:

```text
If static dominates all or almost all contexts:
  do not train G6; expand candidate space or accept static flow-shield as baseline.

If oracle beats static on a meaningful fraction of contexts and features explain it:
  continue G6 safe mixture design.

If oracle beats static but contexts are rare/noisy:
  continue label collection and budget-stability checks.
```

### P4. Probe-budget stability

Implement:

```text
scripts/run_repair5g55_probe_budget_stability.py
scripts/analyze_repair5g55_probe_budget_stability.py
```

Budgets:

```text
250 ms
500 ms
1000 ms
optional 2000 ms sentinel
```

Required outputs:

```text
outputs/reports/phase5p5_repair5g55_probe_budget_stability.md
outputs/reports/phase5p5_repair5g55_probe_budget_stability_summary.json
outputs/tables/phase5p5_repair5g55_probe_budget_rank_stability.csv
```

Gate:

```text
candidate rank stability measured
oracle candidate stability measured
static-vs-oracle sign stability measured
unstable labels separated from training-eligible labels
```

### P5. Feature audit and G6 feature table

Implement:

```text
scripts/create_repair5g55_g6_feature_table.py
scripts/analyze_repair5g55_feature_leakage_and_availability.py
```

Allowed feature families:

```text
map size / density / agent count
iteration index
has incumbent before
best ratio before only if available before update
returned_solutions_count_so_far before update
trace counts from current pre-update trace
committed / blocked / wait counts
progress / non-progress counts
traffic_before C/F summary
cost bounds flags only if cheap/perf-safe
```

Forbidden:

```text
actions
future solution outcome
probe outcome features
oracle label fields
restart nodes
priority overrides
h-values
candidate deletion information
post-update traffic_after unless explicitly marked label-only
```

Outputs:

```text
outputs/tables/phase5p5_repair5g55_g6_feature_table.csv
outputs/reports/phase5p5_repair5g55_feature_audit.md
outputs/reports/phase5p5_repair5g55_feature_audit_summary.json
```

### P6. G6 safe mixture / residual design, no training unless explicitly gated

Write:

```text
outputs/reports/phase5p5_repair5g55_g6_safe_mixture_policy_design.md
outputs/reports/phase5p5_repair5g55_g6_safe_mixture_policy_spec.json
```

The first G6 method should be:

```text
Safe learned mixture over validated UpdateLTM experts
+
static flow-shield fallback
+
abstention / confidence threshold
+
optional bounded residual only after mixture gap is validated
```

Do not train by default. If and only if P1-P5 pass and label coverage is sufficient, Codex may write a separate G6 training plan:

```text
czr004_repair5g6_safe_mixture_training_plan.md
```

but should not train in G5.5 unless explicitly authorized.

### P7. Final G5.5 decision

Write:

```text
outputs/reports/phase5p5_repair5g55_decision.md
outputs/reports/phase5p5_repair5g55_decision_summary.json
```

Decision options:

```text
scaled_labels_failed
scaled_labels_passed_static_dominates
scaled_labels_passed_adaptive_gap_weak
scaled_labels_passed_adaptive_gap_strong_continue_g6_design
candidate_space_too_small_expand_before_g6
probe_budget_instability_blocks_training
feature_leakage_blocks_training
continue_g6_safe_mixture_training_plan
stop_for_protocol_or_semantic_bug
```

Mandatory final status fields:

```json
{
  "phase5p5_allowed": false,
  "phase6_allowed": false,
  "aaai_ready": false,
  "ids_166_205_untouched": true,
  "g6_training_allowed": false,
  "learned_runtime_fresh_holdout": "blocked_not_run"
}
```

---

## 6. Validation

Run:

```text
python -m py_compile all new/modified Python scripts
scripts/build_phase1a_batch.ps1 if C++ changed
pytest focused tests if available
manual fallback harness if pytest unavailable
reserved-ID guard must reject 166
git diff --check
JSON summary validation
```

Commit message:

```text
repair5g: scale counterfactual labels and prepare g6 design
```

---

## 7. Codex prompt

```text
Continue czr004 on branch phase4f5p5-stable-attention-lau after commit 2754692 repair5g: collect semantic replay counterfactual update labels.

Goal:
Implement Repair5G.5.5: scale true same-context counterfactual UpdateLTM labels across observed maps/agents/IDs, measure whether an adaptive goal-aware dual-channel UpdateLTM oracle beats static flow-shield broadly enough to justify G6, audit feature leakage/runtime availability, and write the G6 safe mixture/residual design. Do not run IDs 166..205. Do not claim Phase5.5/Phase6/AAAI-ready. Do not train G6 unless explicitly authorized after this round.

Main project objective:
Use learning-enhanced UpdateLTM to replace the coarse additive update in the LTM paper and eventually beat LaCAM*+plain additive LTM under closed-loop solver metrics, without changing LaCAM*/PIBT semantics.

Read first:
  deep-research-report.md
  phase4_6_laur_ltm_codex_execution_plan.md
  docs/aaai_quality_requirements.md
  czr004_repair5g54_semantic_replay_counterfactual_labels_plan.md
  outputs/reports/phase5p5_repair5g54_decision.md
  outputs/reports/phase5p5_repair5g54_decision_summary.json
  outputs/reports/phase5p5_repair5g54_checkpoint_replayability_summary.json
  outputs/reports/phase5p5_repair5g54_counterfactual_label_summary.json
  outputs/reports/phase5p5_repair5g54_counterfactual_oracle_gap_summary.json
  outputs/reports/phase5p5_repair5g54_g6_safe_mixture_readiness_summary.json

Preserve this interpretation:
  - G5.4 decision = counterfactual_labels_available_adaptive_gap_found.
  - Checkpoint export and replayability passed.
  - True same-context counterfactual labels are now available.
  - Oracle gap over static was measured and adaptive gap was found.
  - Current labels are only a tiny smoke: 2 contexts, 14 label rows, random-32-32-20 / 50 agents only.
  - G6 design is allowed, but G6 training remains blocked until scaled label coverage and quality pass.
  - Goal-aware dual-channel LTM is not corrupted.
  - Fixed static/map-agent flow-shield remains a strong baseline.
  - 3s minimal-hook issue remains classified as warehouse/100 time-budget sensitivity, not UpdateLTM transform corruption.
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
  - use final full-run outcomes as per-update labels
  - train G6 in this round unless every scaled-label/feature/probe-stability gate passes and the report explicitly marks the result diagnostic-only

Tasks:
  1. Add czr004_repair5g55_scaled_counterfactual_g6_design_plan.md to repo root and update docs/codex-worklog.md.
  2. Write outputs/reports/phase5p5_repair5g54_final_interpretation.md and outputs/reports/phase5p5_repair5g55_protocol_overview.md.
  3. Implement and run scripts/run_repair5g55_scaled_counterfactual_labels.py and scripts/analyze_repair5g55_scaled_counterfactual_labels.py.
  4. Use observed IDs only: primary IDs 146..165; optional broader observed pool <=165 only after audit. Reserved-ID guard must reject 166.
  5. Cover maps random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1 and agents 50,100.
  6. Produce scaled label CSVs/reports with candidate coverage, context coverage, same-context checks, replayability checks, and leakage audits.
  7. Implement candidate-set audit and a small bounded flow-shield local lattice only if supported by registry.
  8. Implement oracle-gap analysis by map/agent/iteration/trace/traffic features.
  9. Implement probe-budget stability for 250/500/1000ms plus optional 2000ms sentinel.
  10. Create a G6 feature table using allowed pre-update runtime features only.
  11. Write G6 safe mixture/residual design and policy spec, but do not claim runtime performance.
  12. Write outputs/reports/phase5p5_repair5g55_decision.md and outputs/reports/phase5p5_repair5g55_decision_summary.json.

Decision options:
  scaled_labels_failed
  scaled_labels_passed_static_dominates
  scaled_labels_passed_adaptive_gap_weak
  scaled_labels_passed_adaptive_gap_strong_continue_g6_design
  candidate_space_too_small_expand_before_g6
  probe_budget_instability_blocks_training
  feature_leakage_blocks_training
  continue_g6_safe_mixture_training_plan
  stop_for_protocol_or_semantic_bug

Validation:
  python -m py_compile all new/modified Python scripts
  if C++ changed, run scripts/build_phase1a_batch.ps1
  pytest focused G5.5 tests if available; otherwise manual fallback harness
  reserved-ID guard rejects 166
  JSON summaries validate
  git diff --check
  commit and push only G5.5-related tracked files and reports
  leave unrelated dirty/untracked files untouched

Commit message:
  repair5g: scale counterfactual labels and prepare g6 design
```
