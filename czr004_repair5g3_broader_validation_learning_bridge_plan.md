# czr004 Repair5G.3 Plan: Broader Validation, Representation/Selector Disentanglement, and Learning-Bridge for Goal-Aware Dual-Channel LTM

**Branch:** `phase4f5p5-stable-attention-lau`
**Start after commit:** `004168f repair5g: validate flow-shield selector on fresh holdout`
**Status:** proposed next diagnostic research wave after Repair5G.2 fresh-final pass
**Promotion status:** `phase5p5_allowed=false`, `phase6_allowed=false`
**Main project objective:** use learning-enhanced `UpdateLTM` to replace the coarse additive update in the LTM paper and eventually beat `LaCAM*+plain additive LTM` under closed-loop solver metrics, without changing LaCAM*/PIBT semantics.

---

## 0. Executive interpretation

Repair5G.2 is a strong positive result.

It is the first czr004 result that shows a goal-aware dual-channel `UpdateLTM` design surviving a non-leaky frozen protocol and a fresh holdout split.

Preserve the core facts:

```text
G2 decision:
  continue_repair5g3_broader_validation

Fresh final:
  maps = random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
  agents = 50, 100
  instance_ids = 46..65
  rows = 2520 / 2520
  missing_rows = 0
  schema_errors = 0
  solver_crash_count = 0

Frozen selected method:
  repair5g2_frozen_static_or_selector
  better / equal / worse = 62 / 44 / 14
  mean_delta_ratio_vs_ltm = -0.020112979571774988
  bootstrap_probability_mean_delta_lt_0 = 1.0
  ratio_worse_than_ltm_groups = 0
  success_worse_than_ltm_groups = 0

Strict controls:
  additive parity exact = true
  always-additive-defer parity exact = true
  laur-disable parity exact = true
  laur-force-additive-direct parity exact = true
  dual-additive parity exact = true
  dual C-equiv additive parity exact = true
  all costs finite = true
  cost bounds respected = true

Boundary:
  phase5p5_allowed=false
  phase6_allowed=false
```

This is **good** because it validates the *representation hypothesis*:

```text
G0 global flow bonus failed.
G1/G2 flow-shielded goal-aware dual-channel UpdateLTM works on fresh IDs.
The benefit is much larger than scalar C-equivalent bounded UpdateParams.
```

But this is **not yet enough** for Phase5.5, Phase6, or a paper claim because:

```text
1. Scope is still narrow:
   3 maps, 2 agent counts, one time budget, one LTM iteration budget, 20 final IDs.

2. The selector itself is not clearly better than the strongest static flow-shield rule:
   repair5g2_best_frozen_static_candidate:
     64 / 43 / 13
     mean = -0.020043939351749987

   repair5g2_frozen_static_or_selector:
     62 / 44 / 14
     mean = -0.020112979571774988

   Interpretation:
     the family is strong;
     the map-agent selector may mostly be a safe fallback mechanism, not yet a learned adaptive policy.

3. Synthetic flow-shield diagnostics are also very strong:
   repair5g2_shuffled_flow_shield_diagnostic:
     63 / 43 / 14
     mean = -0.019850973894158318

   repair5g2_shuffled_goal_progress_diagnostic:
     60 / 44 / 16
     mean = -0.01761917499324165

   Interpretation:
     the current evidence strongly supports flow-shield representation;
     it does not yet prove that selector intelligence is the main source of gain.

4. Warehouse is mostly no-op / fallback:
   warehouse-10-20-10-2-1, 50 agents:
     static flow-shield had 0 / 19 / 1 and positive mean delta;
     the frozen selector fell back to a C-equivalent/additive-safe choice and got 0 / 20 / 0.

   warehouse-10-20-10-2-1, 100 agents:
     almost everything is exact no-op.

   Interpretation:
     current gains are driven mainly by random and maze;
     G3 must test whether flow-shield helps broader map/agent regimes.

5. Time-budget sensitivity was already observed in G1/G2 audits:
   true semantic mismatches were zero, but strict parity mismatches were classified as time-budget sensitivity.
   G3 must include repeat/run-order/time-budget stress before any stronger claim.
```

Therefore the correct next decision is:

```text
Continue Repair5G.3 broader validation.

Do not promote Phase5.5.
Do not claim Phase6.
Do not call this a learned policy yet.
Do not collapse the story into "selector won".

The defensible current story is:
  goal-aware flow-shielded dual-channel UpdateLTM has fresh-holdout closed-loop benefit
  under the tested split, and deserves broader validation plus a learning-bridge.
```

---

## 1. Scientific hypotheses for G3

G3 must separate four hypotheses that G2 currently entangles.

### H1. Flow-shield representation is genuinely useful

```text
C-channel = congestion / blockage / wait-risk evidence
F-channel = successful goal-progress / corridor evidence

flow_shield:
  F does not make an edge globally cheap.
  F only reduces C over-penalty on current-agent goal-progress edges.
```

Expected evidence:

```text
flow-shield static candidates keep beating:
  additive LTM
  scalar C-equivalent baselines
  global-F / agent-progress-F diagnostics
  random/shuffled controls
across new IDs, time budgets, and map-agent regimes.
```

### H2. The G2 selector is mostly a safe fallback selector

The current selector may be valuable because it avoids warehouse harm and chooses slightly different flow-shield parameters by map-agent group. But it has not clearly beaten the best static flow-shield rule.

G3 must report:

```text
frozen selector vs selected static
frozen selector vs best static from G2
frozen selector vs shuffled flow-shield diagnostic
frozen selector regret to oracle on new IDs
static flow-shield regret to oracle on new IDs
```

If static wins or ties selector, the decision should be:

```text
flow_shield_representation_valid_selector_unclear
```

not:

```text
adaptive selector validated
```

### H3. The next real project advance is a learnable UpdateLTM policy, not another hand-tuned map-agent table

The final project target is learning-enhanced `UpdateLTM`, not a hand-coded map-agent lookup.

G3 should therefore build a bridge toward:

```text
trace/context -> choose bounded UpdateParams / flow-shield parameters
```

This is still legal because it chooses `UpdateLTM` parameters and traffic-map cost projection. It must not output actions, priorities, restarts, candidate deletions, or learned search semantics.

### H4. The observed gain must survive timing and protocol noise

G1/G2 strict parity discrepancies were classified as time-budget sensitivity, not semantic mismatch. That is acceptable for diagnostics, but G3 must measure:

```text
repeat stability
run-order sensitivity
1s / 3s / 5s time-budget sensitivity
2 / 4 / 8 LTM-iteration sensitivity
```

---

## 2. Data split policy

Observed after G2:

```text
IDs 1..25:
  support / selector training data

IDs 26..45:
  G1/F4 development validation data

IDs 46..65:
  G2 fresh final data, now observed
```

G3 must not reuse IDs 46..65 as untouched final evidence.

Recommended new split:

```text
G3 frozen broader validation:
  IDs 66..105
  no G3 tuning before evaluating these IDs
  use the G2 frozen selector and G2 frozen static candidate unchanged

G3 learning-bridge heldout:
  IDs 106..125
  use only if a contextual / learned selector is trained after broader validation
  freeze learned selector before looking at IDs 106..125

Optional map-expansion diagnostic:
  if adding new maps, generated instance IDs can start at 1 because those map/scenario tuples are new,
  but the report must label them "new-map diagnostic", not comparable to old-map final IDs.
```

If scenario files are missing, use the existing deterministic scenario generator policy and record:

```text
script_version
base_seed
seed function
requested IDs
generated count
paths
SHA256 / manifest if possible
```

---

## 3. Non-negotiable constraints

Do not:

```text
- modify external/lacam2/lacam2/**
- change PIBT legality, priority inheritance, backtracking, vertex conflict, or swap conflict semantics
- change LaCAM* candidate generation
- change child pruning, OPEN/EXPLORED, rewrite, incumbent pruning, or restart semantics
- introduce action prediction
- introduce learned restart
- output learned h_i(v)
- output learned edge action logits
- output learned priority overrides
- delete legal candidates
- call any result Phase5.5 or Phase6
- use IDs 66..105 for tuning before the frozen G2 methods are evaluated
- use IDs 106..125 for learned-selector tuning if they are reserved for learning-bridge final
```

Allowed:

```text
- project-owned scripts and reports
- project-owned cpp/ltm/** and cpp/tools/phase1a_batch.cpp only if strictly needed
- bounded dual-channel traffic-map state and costs
- frozen static flow-shield candidate
- frozen map-agent selector
- offline contextual selector diagnostics
- runtime selector only if it selects bounded UpdateLTM parameters using pre-update context features
- exact additive / disable / force-additive fallback
```

Must preserve:

```text
phase5p5_allowed=false
phase6_allowed=false
diagnostic_only=true
strict additive parity controls
strict force-additive controls
dual C-equivalence controls
finite bounded costs
raw log manifest / row-count audit
```

---

## 4. G3 required work

## P0. Documentation and interpretation

Add this plan to repo root:

```text
czr004_repair5g3_broader_validation_learning_bridge_plan.md
```

Update:

```text
docs/codex-worklog.md
```

Write:

```text
outputs/reports/phase5p5_repair5g2_final_interpretation.md
outputs/reports/phase5p5_repair5g3_protocol_overview.md
```

`phase5p5_repair5g2_final_interpretation.md` must say:

```text
- G2 is a strong positive fresh-holdout result for flow-shielded goal-aware dual-channel UpdateLTM.
- The strongest current evidence is representation-level, not selector-intelligence-level.
- The frozen selector passed fresh IDs 46..65, but the best static flow-shield and shuffled flow-shield diagnostics are close.
- C-equivalent/scalar congestion baselines are much weaker.
- Warehouse mostly needs no-op/fallback; random and maze drive the gains.
- IDs 46..65 are now observed and cannot be reused as untouched final evidence.
- phase5p5_allowed=false and phase6_allowed=false remain closed.
```

## P1. G2 artifact integrity and reproducibility preservation

Implement:

```text
scripts/analyze_repair5g2_artifact_integrity.py
```

Inputs:

```text
outputs/reports/phase5p5_repair5g2_decision.md
outputs/reports/phase5p5_repair5g2_protocol_overview.md
outputs/reports/phase5p5_repair5g2_frozen_selector_spec.json
outputs/reports/phase5p5_repair5g2_selector_sweep_summary.json
outputs/reports/phase5p5_repair5g2_fresh_final_eval_summary.json
outputs/tables/phase5p5_repair5g2_fresh_final_eval_summary.csv
outputs/tables/phase5p5_repair5g2_fresh_final_eval_by_map_agent.csv
outputs/tables/phase5p5_repair5g2_fresh_final_eval_paired.csv
outputs/logs/phase5p5_repair5g2_support_probe/*.jsonl
outputs/logs/phase5p5_repair5g2_fresh_final_eval/*.jsonl
```

Large JSONL logs may remain ignored/uncommitted, but write a committed manifest with:

```text
path
exists
row_count
file_size_bytes
sha256
method counts
map-agent counts
parse errors
duplicate keys
missing expected keys
```

Outputs:

```text
outputs/reports/phase5p5_repair5g2_artifact_integrity.md
outputs/reports/phase5p5_repair5g2_artifact_integrity_summary.json
outputs/tables/phase5p5_repair5g2_raw_log_manifest.csv
```

Required checks:

```text
- final tables and summary agree exactly
- raw logs, if present locally, agree with committed summaries
- final IDs were 46..65
- final_ids_used_for_tuning=false
- frozen selector timestamp/spec existed before final eval summary timestamp
- script-runtime commit and artifact commit are both recorded
- no true semantic parity mismatch
```

If raw logs are absent because they were not committed, do not fail. Record `raw_logs_available=false` and require committed tables/summaries to be internally consistent.

## P2. G2 result autopsy: representation vs selector vs diagnostics

Implement:

```text
scripts/analyze_repair5g2_result_autopsy.py
```

Inputs:

```text
outputs/reports/phase5p5_repair5g2_frozen_selector_spec.json
outputs/reports/phase5p5_repair5g2_fresh_final_eval_summary.json
outputs/tables/phase5p5_repair5g2_fresh_final_eval_paired.csv
outputs/tables/phase5p5_repair5g2_fresh_final_eval_by_map_agent.csv
outputs/tables/phase5p5_repair5g2_fresh_final_eval_summary.csv
```

Outputs:

```text
outputs/reports/phase5p5_repair5g2_result_autopsy.md
outputs/reports/phase5p5_repair5g2_result_autopsy_summary.json
outputs/tables/phase5p5_repair5g2_selector_vs_static_cases.csv
outputs/tables/phase5p5_repair5g2_representation_dominance_by_group.csv
outputs/tables/phase5p5_repair5g2_final_oracle_regret.csv
outputs/tables/phase5p5_repair5g2_worst_cases.csv
```

Required analysis:

```text
1. Frozen selector vs selected static:
   repair5g2_frozen_static_or_selector
   repair5g2_best_frozen_static_candidate
   repair5g2_g1_top_diagnostic_candidate

2. Flow-shield representation vs C-equivalent/scalar baselines:
   selected flow-shield methods
   repair5g2_c_equiv_best_frozen_baseline
   repair5f_static_c100_b100_w075_d090
   repair5f4_best_static_c125_b125_w075_d095_diagnostic_only

3. Diagnostics:
   repair5g2_random_candidate_diagnostic
   repair5g2_shuffled_goal_progress_diagnostic
   repair5g2_shuffled_flow_shield_diagnostic

4. Per-map-agent decomposition:
   random-50
   random-100
   maze-50
   maze-100
   warehouse-50
   warehouse-100

5. Case-level dominance:
   selector wins over static
   static wins over selector
   both win over additive
   both lose to additive
   selector avoids warehouse harm

6. Final candidate oracle over evaluated G2 final methods:
   oracle better/equal/worse vs LTM
   selector regret to oracle
   selected static regret to oracle
   shuffled-flow regret to oracle

7. Risk:
   cases where flow-shield hurts but C-equiv/additive is safe
   cases where selector chose fallback and avoided harm
   cases where selector fallback caused missed gain
```

The report must explicitly answer:

```text
Is G2 mainly a representation win, selector win, or both?
```

## P3. Determinism, repeat, and method-order stress

Implement:

```text
scripts/run_repair5g3_determinism_repeat.py
```

Run before broad validation:

```text
maps = random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
agents = 50, 100
instance_ids = 66..75
time_limit_sec = 3.0
ltm_max_iterations = 4
repeats = 3
method_order = deterministic shuffled per repeat
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
repair5g2_frozen_static_or_selector
repair5g2_best_frozen_static_candidate
repair5g2_c_equiv_best_frozen_baseline
repair5g2_shuffled_flow_shield_diagnostic
repair5g2_random_candidate_diagnostic
```

Outputs:

```text
outputs/logs/phase5p5_repair5g3_determinism_repeat/phase5p5_repair5g3_determinism_repeat.jsonl
outputs/logs/phase5p5_repair5g3_determinism_repeat/phase5p5_repair5g3_determinism_repeat_commands.jsonl
outputs/tables/phase5p5_repair5g3_determinism_repeat_paired.csv
outputs/tables/phase5p5_repair5g3_determinism_repeat_by_repeat.csv
outputs/reports/phase5p5_repair5g3_determinism_repeat_report.md
outputs/reports/phase5p5_repair5g3_determinism_repeat_summary.json
```

Required gates before broad validation:

```text
strict control parity exact for all non-timeout-equivalent controls
true_semantic_parity_mismatch_count = 0
solver_crash_count = 0
schema_errors = 0
selected_mean_delta_sign_stable = true
selected_repeat_mean_delta_ratio_vs_ltm < 0 in at least 2 / 3 repeats
selected_success_worse_than_ltm_groups = 0
```

If these fail, do not run G3 broad validation. Write decision:

```text
stop_for_determinism_or_time_budget_autopsy
```

## P4. G3 broader frozen validation on new IDs 66..105

Implement or extend:

```text
scripts/run_repair5g3_broader_validation.py
```

Run:

```text
maps = random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
agents = 50, 100
instance_ids = 66..105
time_limit_sec = 3.0
ltm_max_iterations = 4
chunk_resume = true
```

Methods:

```text
Core controls:
  lacam_star_ltm
  always_additive_defer
  repair5f_candidate_additive_ltm
  laur_disable
  laur_force_additive_direct
  repair5g_dual_additive_parity
  repair5g_dual_c_equiv_additive

C/scalar baselines:
  repair5f_static_c100_b100_w075_d090
  repair5f4_best_static_c125_b125_w075_d095_diagnostic_only
  repair5g2_c_equiv_best_frozen_baseline
  repair5g_dual_c_equiv_c100_b100_w075_d095
  repair5g_dual_c_equiv_c100_b100_w075_d100

Frozen G2:
  repair5g2_frozen_static_or_selector
  repair5g2_best_frozen_static_candidate
  repair5g2_g1_top_diagnostic_candidate

Flow-shield nearby candidates:
  repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75
  repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75
  repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p5
  repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p75
  repair5g1_shield_c100_b100_w075_d095_beta0p35_max0p75

Diagnostics:
  repair5g3_random_flow_shield_diagnostic_seed0
  repair5g3_random_flow_shield_diagnostic_seed1
  repair5g3_random_flow_shield_diagnostic_seed2
  repair5g3_shuffled_flow_shield_diagnostic_seed0
  repair5g3_shuffled_flow_shield_diagnostic_seed1
  repair5g3_shuffled_goal_progress_diagnostic_seed0
```

Write:

```text
outputs/logs/phase5p5_repair5g3_broader_validation/phase5p5_repair5g3_broader_validation.jsonl
outputs/logs/phase5p5_repair5g3_broader_validation/phase5p5_repair5g3_broader_validation_commands.jsonl
outputs/logs/phase5p5_repair5g3_broader_validation/phase5p5_repair5g3_broader_validation_ltm_updates.jsonl
outputs/tables/phase5p5_repair5g3_broader_validation_paired.csv
outputs/tables/phase5p5_repair5g3_broader_validation_summary.csv
outputs/tables/phase5p5_repair5g3_broader_validation_by_map_agent.csv
outputs/tables/phase5p5_repair5g3_broader_validation_oracle_regret.csv
outputs/reports/phase5p5_repair5g3_broader_validation_report.md
outputs/reports/phase5p5_repair5g3_broader_validation_summary.json
outputs/reports/phase5p5_repair5g3_broader_validation_audit.md
```

G3 broader validation gates:

```text
protocol:
  expected_rows_full = true
  missing_rows = 0
  schema_errors = 0
  solver_crash_count = 0
  additive_parity_exact = true
  laur_disable_parity_exact = true
  laur_force_additive_direct_parity_exact = true
  dual_additive_parity_exact = true
  dual_c_equiv_additive_parity_exact = true
  all_costs_finite = true
  cost_bounds_respected = true
  no IDs <=65 used as G3 fresh validation

selected method:
  selected_better_gt_worse = true
  selected_mean_delta_ratio_vs_ltm < -0.008
  selected_bootstrap_probability_mean_delta_lt_0 >= 0.99
  selected_ratio_worse_than_ltm_groups <= 1
  selected_success_worse_than_ltm_groups = 0

representation:
  best_flow_shield_mean_delta_ratio_vs_ltm < -0.010
  best_c_equiv_mean_delta_ratio_vs_ltm is at least 0.006 worse than best_flow_shield
  best_scalar_repair5f_mean_delta_ratio_vs_ltm is at least 0.006 worse than best_flow_shield
  flow_shield_family_beats_random_median = true
  flow_shield_family_beats_shuffled_goal_progress_median = true

selector vs static:
  classify, do not force pass:
    selector_beats_static
    static_beats_selector
    tied_within_0p001
```

Decision after P4:

```text
If selected and static both pass, but selector does not beat static:
  continue_flow_shield_static_or_learning_bridge
  interpretation = representation validated, selector unclear

If selected passes and beats static/diagnostics:
  continue_contextual_selector_learning

If flow-shield fails broad validation:
  stop_or_return_to_representation_design

If protocol fails:
  stop_for_protocol_autopsy
```

## P5. Time-budget and LTM-iteration stress

Only run if P4 protocol gates pass.

Implement:

```text
scripts/run_repair5g3_time_iteration_stress.py
```

Run:

```text
maps = random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
agents = 50, 100
instance_ids = 66..85
time_limit_sec in {1.0, 3.0, 5.0}
ltm_max_iterations in {2, 4, 8}
```

Methods:

```text
lacam_star_ltm
always_additive_defer
laur_disable
laur_force_additive_direct
repair5g_dual_additive_parity
repair5g_dual_c_equiv_additive
repair5g2_frozen_static_or_selector
repair5g2_best_frozen_static_candidate
repair5g2_c_equiv_best_frozen_baseline
repair5g3_shuffled_flow_shield_diagnostic_seed0
```

Outputs:

```text
outputs/tables/phase5p5_repair5g3_time_iteration_stress_paired.csv
outputs/tables/phase5p5_repair5g3_time_iteration_stress_summary.csv
outputs/tables/phase5p5_repair5g3_time_iteration_stress_by_budget.csv
outputs/tables/phase5p5_repair5g3_time_iteration_stress_by_iteration.csv
outputs/reports/phase5p5_repair5g3_time_iteration_stress_report.md
outputs/reports/phase5p5_repair5g3_time_iteration_stress_summary.json
```

Stress interpretation:

```text
- 1s may be noisy; do not fail the direction solely on 1s.
- 3s should reproduce sign and approximate magnitude.
- 5s should not reverse sign.
- 8 iterations should not introduce broad harm.
- If gains vanish at 5s, investigate whether flow-shield only accelerates early solutions rather than improves final quality.
```

## P6. Optional map/agent expansion diagnostic

Only run if P4 passes and time remains.

Implement:

```text
scripts/run_repair5g3_map_expansion_probe.py
```

First audit available maps under:

```text
external/lacam2/scripts/map/
```

Do not assume missing maps exist. Candidate extra maps may include, only if present:

```text
random-64-64-20
maze-32-32-2
maze-64-64-2
room-64-64-16
warehouse-20-40-10-2-1
```

If none are available, write a skip report.

For available maps:

```text
agents = feasible subset from {50, 100, 150, 200}
instance_ids = 1..20 for new-map diagnostic
time_limit_sec = 3.0
ltm_max_iterations = 4
```

Methods:

```text
lacam_star_ltm
always_additive_defer
laur_disable
laur_force_additive_direct
repair5g2_frozen_static_or_selector
repair5g2_best_frozen_static_candidate
repair5g2_c_equiv_best_frozen_baseline
best 2 flow-shield static candidates
random/shuffled diagnostics
```

Outputs:

```text
outputs/reports/phase5p5_repair5g3_map_expansion_probe_report.md
outputs/reports/phase5p5_repair5g3_map_expansion_probe_summary.json
outputs/tables/phase5p5_repair5g3_map_expansion_probe_summary.csv
outputs/tables/phase5p5_repair5g3_map_expansion_probe_by_map_agent.csv
```

This is diagnostic only. Do not let new-map results tune the G2 frozen selector.

## P7. Learning bridge: contextual flow-shield UpdateLTM selector

This is the most important scientific bridge after G2.

If P4 passes, implement the first **learning-enhanced UpdateLTM** bridge. It must remain inside UpdateLTM parameter selection and traffic-map cost projection.

Implement:

```text
scripts/create_repair5g3_learning_bridge_dataset.py
scripts/tune_repair5g3_contextual_flow_shield_selector.py
```

Dataset sources:

```text
Allowed for training/development:
  G2 support IDs 1..25
  G1 dev IDs 26..45
  G2 final IDs 46..65  # now observed after G2; allowed for later training but not for G2 claims
  G3 broader validation IDs 66..85 if P4 uses 66..105 and you reserve 86..105 for learning validation

Reserved for learning-bridge fresh evaluation:
  Prefer IDs 106..125
  If already touched for other G3 tasks, use next clean range 126..145
```

Feature policy:

Allowed features must be available before choosing the update rule for an iteration:

```text
map structural features:
  map_width, map_height, obstacle_ratio, free_cells

instance features:
  agents, density

iteration/runtime context:
  ltm_iterations
  returned_solutions_count_so_far
  has_incumbent_before
  best_ratio_before
  improved_last_iteration

trace/update summary:
  committed_count
  blocked_count
  wait_event_count
  progress_committed_count
  nonprogress_committed_count
  blocked_per_committed
  wait_per_committed
  blocked_per_agent
  committed_per_agent
  progress_ratio
  c_update_count
  f_update_count
  c_nonzero_edges
  f_nonzero_edges
  c_flow_update_ratio
  cost_min
  cost_max
  cost_span
  cost_bounds_respected
```

Forbidden features:

```text
instance_id
seed
scen filename
case key
held-out candidate outcomes
oracle label from the same held-out fold
final solver outcome after the chosen update
map-agent group lookup as the only decision rule
```

Selectors to test:

```text
static top flow-shield
G2 map-agent static selector
risk-capped static selector
decision stump selector
small pure-Python decision tree selector
linear score selector implemented without heavy dependencies
margin selector with additive/C-equiv fallback
flow-shield-family-only selector
shuffled-label diagnostic selector
random-feature diagnostic selector
```

If runtime integration is feasible, export:

```text
outputs/reports/phase5p5_repair5g3_contextual_selector_spec.json
outputs/reports/phase5p5_repair5g3_contextual_selector_report.md
```

If runtime integration is not feasible, write an implementation-gap report and do not fake a runtime result.

Learning bridge dev gates before any fresh learned-selector evaluation:

```text
learned_selector_uses_no_forbidden_features = true
learned_selector_mean_delta_ratio_vs_ltm < -0.008 on cross-validation
learned_selector_bootstrap_probability_mean_delta_lt_0 >= 0.99
learned_selector_success_worse_than_ltm_groups = 0
learned_selector_beats_static_or_matches_within_0p001 = true
learned_selector_beats_shuffled_label_diagnostic = true
learned_selector_beats_random_feature_diagnostic = true
learned_selector_not_map_agent_lookup_only = true
```

If gates pass, run learned-selector fresh evaluation:

```text
maps = random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
agents = 50, 100
instance_ids = 106..125 or next untouched range
time_limit_sec = 3.0
ltm_max_iterations = 4
methods:
  lacam_star_ltm
  controls/parity
  G2 frozen static
  G2 frozen map-agent selector
  learned contextual selector
  C-equiv fallback
  shuffled/random learned diagnostics
```

Outputs:

```text
outputs/reports/phase5p5_repair5g3_contextual_selector_fresh_eval_report.md
outputs/reports/phase5p5_repair5g3_contextual_selector_fresh_eval_summary.json
outputs/tables/phase5p5_repair5g3_contextual_selector_fresh_eval_paired.csv
outputs/tables/phase5p5_repair5g3_contextual_selector_fresh_eval_by_map_agent.csv
```

Important:

```text
Even if the learned selector passes, do not claim Phase5.5 or Phase6.
The correct next step would be Repair5G.4 formal promotion-candidate validation.
```

## P8. Final G3 decision report

Write:

```text
outputs/reports/phase5p5_repair5g3_decision.md
outputs/reports/phase5p5_repair5g3_decision_summary.json
```

Decision options:

```text
continue_repair5g4_formal_promotion_candidate_validation
continue_flow_shield_static_candidate_validation
continue_contextual_learning_bridge
flow_shield_representation_valid_selector_unclear
stop_for_determinism_or_time_budget_autopsy
stop_or_return_to_representation_design
protocol_failed
```

The decision must explicitly answer:

```text
1. Does flow-shield survive broader new-ID validation?
2. Is static flow-shield enough?
3. Does map-agent selector add value over static?
4. Is there evidence that a learned contextual selector is worth building/running?
5. Is the effect stable across time budgets and LTM iteration budgets?
6. Which IDs are now observed and which remain reserved?
7. What exact next split should G4 use?
```

---

## 5. Validation requirements

Run:

```text
python -m py_compile \
  scripts/analyze_repair5g2_artifact_integrity.py \
  scripts/analyze_repair5g2_result_autopsy.py \
  scripts/run_repair5g3_determinism_repeat.py \
  scripts/run_repair5g3_broader_validation.py \
  scripts/run_repair5g3_time_iteration_stress.py \
  scripts/run_repair5g3_map_expansion_probe.py \
  scripts/create_repair5g3_learning_bridge_dataset.py \
  scripts/tune_repair5g3_contextual_flow_shield_selector.py
```

Run pytest if available. If pytest is unavailable, run the existing manual fallback harness and record every test function executed.

If any C++ changed, run:

```text
scripts/build_phase1a_batch.ps1
```

Always run:

```text
git diff --check
```

Commit only G3-related tracked files and reports. Leave unrelated dirty/untracked files untouched. Large raw JSONL logs may remain ignored, but their manifest/hash summaries should be committed.

Commit message:

```text
repair5g: broaden flow-shield validation and prepare learned selector
```

---

# Codex prompt

Continue czr004 on branch `phase4f5p5-stable-attention-lau` after commit `004168f repair5g: validate flow-shield selector on fresh holdout`.

Goal:
Implement Repair5G.3: broader validation, representation/selector disentanglement, and a learning-bridge for goal-aware dual-channel LTM. This remains diagnostic-only. Do not claim Phase5.5 or Phase6.

Main project objective:
Use learning-enhanced `UpdateLTM` to replace the coarse additive update in the LTM paper and eventually beat `LaCAM*+plain additive LTM` under closed-loop solver metrics, without changing LaCAM*/PIBT semantics.

Read first:
```text
deep-research-report.md
phase4_6_laur_ltm_codex_execution_plan.md
czr004_repair5f41_fresh_failure_oracle_diagnosis_plan.md
czr004_repair5g0_goal_aware_dual_channel_ltm_plan.md
czr004_repair5g1_agent_aware_dual_channel_ltm_overnight_plan.md
czr004_repair5g2_flow_shield_selector_fresh_validation_plan.md
outputs/reports/phase5p5_repair5g0_final_interpretation.md
outputs/reports/phase5p5_repair5g1_design_delta.md
outputs/reports/phase5p5_repair5g1_final_interpretation.md
outputs/reports/phase5p5_repair5g1_parity_determinism_audit.md
outputs/reports/phase5p5_repair5g1_parity_determinism_audit_summary.json
outputs/reports/phase5p5_repair5g2_protocol_overview.md
outputs/reports/phase5p5_repair5g2_selector_sweep_report.md
outputs/reports/phase5p5_repair5g2_selector_sweep_summary.json
outputs/reports/phase5p5_repair5g2_frozen_selector_spec.json
outputs/reports/phase5p5_repair5g2_fresh_final_eval_report.md
outputs/reports/phase5p5_repair5g2_fresh_final_eval_summary.json
outputs/reports/phase5p5_repair5g2_decision.md
outputs/tables/phase5p5_repair5g2_fresh_final_eval_summary.csv
outputs/tables/phase5p5_repair5g2_fresh_final_eval_by_map_agent.csv
```

Preserve this interpretation:
```text
- Repair5G.2 is a strong positive fresh-holdout result for flow-shielded goal-aware dual-channel UpdateLTM.
- The strongest current evidence is representation-level: flow-shield is much stronger than scalar/C-equivalent bounded UpdateParams.
- The frozen map-agent selector passed fresh IDs 46..65:
    62 / 44 / 14
    mean_delta_ratio_vs_ltm = -0.020112979571774988
    bootstrap probability mean < 0 = 1.0
    ratio_worse_than_ltm_groups = 0
    success_worse_than_ltm_groups = 0
- Strict final controls passed exactly:
    additive, always-additive-defer, laur-disable, force-additive direct, dual-additive, dual C-equiv additive.
- The best static flow-shield candidate and shuffled flow-shield diagnostic are very close to the frozen selector on final IDs.
- Therefore G2 validates the flow-shield representation more strongly than selector intelligence.
- Warehouse is mostly no-op/fallback; random and maze drive the gains.
- IDs 1..65 are now observed. Do not reuse IDs 46..65 as untouched final evidence.
- phase5p5_allowed=false and phase6_allowed=false remain mandatory.
```

Do not:
```text
- modify external/lacam2/lacam2/**
- change PIBT legality, priority inheritance, backtracking, vertex conflict, or swap conflict semantics
- change LaCAM* candidate generation, child pruning, OPEN/EXPLORED, rewrite, incumbent pruning, or restart semantics
- introduce action prediction
- introduce learned restart
- output learned h_i(v), action logits, priority overrides, or candidate deletion
- claim Phase5.5 or Phase6
- tune on IDs 66..105 before evaluating frozen G2 methods there
- use reserved learned-selector holdout IDs for training
```

Tasks:

1. Add `czr004_repair5g3_broader_validation_learning_bridge_plan.md` to repo root and update `docs/codex-worklog.md`.

2. Write:
```text
outputs/reports/phase5p5_repair5g2_final_interpretation.md
outputs/reports/phase5p5_repair5g3_protocol_overview.md
```

3. Implement `scripts/analyze_repair5g2_artifact_integrity.py`.

Write:
```text
outputs/reports/phase5p5_repair5g2_artifact_integrity.md
outputs/reports/phase5p5_repair5g2_artifact_integrity_summary.json
outputs/tables/phase5p5_repair5g2_raw_log_manifest.csv
```

The manifest should hash raw JSONL logs if present locally; if ignored raw logs are absent, record that explicitly and rely on committed tables/summaries.

4. Implement `scripts/analyze_repair5g2_result_autopsy.py`.

Write:
```text
outputs/reports/phase5p5_repair5g2_result_autopsy.md
outputs/reports/phase5p5_repair5g2_result_autopsy_summary.json
outputs/tables/phase5p5_repair5g2_selector_vs_static_cases.csv
outputs/tables/phase5p5_repair5g2_representation_dominance_by_group.csv
outputs/tables/phase5p5_repair5g2_final_oracle_regret.csv
outputs/tables/phase5p5_repair5g2_worst_cases.csv
```

The report must explicitly decide whether G2 was mainly a representation win, selector win, or both.

5. Implement `scripts/run_repair5g3_determinism_repeat.py`.

Run:
```text
maps = random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
agents = 50, 100
instance_ids = 66..75
time_limit_sec = 3.0
ltm_max_iterations = 4
repeats = 3
method_order = deterministic shuffled per repeat
```

If repeat/determinism gates fail, stop before broader validation and write a decision.

6. If P3 passes, implement and run `scripts/run_repair5g3_broader_validation.py`.

Run:
```text
maps = random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
agents = 50, 100
instance_ids = 66..105
time_limit_sec = 3.0
ltm_max_iterations = 4
```

Methods must include:
```text
lacam_star_ltm
always_additive_defer
repair5f_candidate_additive_ltm
laur_disable
laur_force_additive_direct
repair5g_dual_additive_parity
repair5g_dual_c_equiv_additive
repair5f_static_c100_b100_w075_d090
repair5f4_best_static_c125_b125_w075_d095_diagnostic_only
repair5g2_c_equiv_best_frozen_baseline
repair5g_dual_c_equiv_c100_b100_w075_d095
repair5g_dual_c_equiv_c100_b100_w075_d100
repair5g2_frozen_static_or_selector
repair5g2_best_frozen_static_candidate
repair5g2_g1_top_diagnostic_candidate
repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75
repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75
repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p5
repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p75
repair5g1_shield_c100_b100_w075_d095_beta0p35_max0p75
repair5g3_random_flow_shield_diagnostic_seed0
repair5g3_random_flow_shield_diagnostic_seed1
repair5g3_random_flow_shield_diagnostic_seed2
repair5g3_shuffled_flow_shield_diagnostic_seed0
repair5g3_shuffled_flow_shield_diagnostic_seed1
repair5g3_shuffled_goal_progress_diagnostic_seed0
```

Write:
```text
outputs/logs/phase5p5_repair5g3_broader_validation/phase5p5_repair5g3_broader_validation.jsonl
outputs/logs/phase5p5_repair5g3_broader_validation/phase5p5_repair5g3_broader_validation_commands.jsonl
outputs/logs/phase5p5_repair5g3_broader_validation/phase5p5_repair5g3_broader_validation_ltm_updates.jsonl
outputs/tables/phase5p5_repair5g3_broader_validation_paired.csv
outputs/tables/phase5p5_repair5g3_broader_validation_summary.csv
outputs/tables/phase5p5_repair5g3_broader_validation_by_map_agent.csv
outputs/tables/phase5p5_repair5g3_broader_validation_oracle_regret.csv
outputs/reports/phase5p5_repair5g3_broader_validation_report.md
outputs/reports/phase5p5_repair5g3_broader_validation_summary.json
outputs/reports/phase5p5_repair5g3_broader_validation_audit.md
```

7. If P4 passes protocol gates, run time/iteration stress via `scripts/run_repair5g3_time_iteration_stress.py`.

Run:
```text
instance_ids = 66..85
time_limit_sec in {1.0, 3.0, 5.0}
ltm_max_iterations in {2, 4, 8}
```

8. If P4 passes and time remains, run optional map/agent expansion with an availability audit. Do not assume extra maps exist; skip cleanly if unavailable.

9. If P4 passes, build the learning bridge:
```text
scripts/create_repair5g3_learning_bridge_dataset.py
scripts/tune_repair5g3_contextual_flow_shield_selector.py
```

This must stay inside UpdateLTM parameter selection. It must not output actions, restarts, priorities, h-values, or child deletions.

If a learned contextual selector passes development gates, freeze it before evaluating any reserved learned-selector holdout IDs such as 106..125 or the next clean range.

10. Write final G3 decision:
```text
outputs/reports/phase5p5_repair5g3_decision.md
outputs/reports/phase5p5_repair5g3_decision_summary.json
```

Decision options:
```text
continue_repair5g4_formal_promotion_candidate_validation
continue_flow_shield_static_candidate_validation
continue_contextual_learning_bridge
flow_shield_representation_valid_selector_unclear
stop_for_determinism_or_time_budget_autopsy
stop_or_return_to_representation_design
protocol_failed
```

Validation:
```text
py_compile all new/modified Python scripts
pytest if available; otherwise manual fallback harness over all relevant test functions
if C++ changed, run scripts/build_phase1a_batch.ps1
git diff --check
commit and push only G3-related tracked files and records
leave unrelated dirty/untracked files untouched
```

Commit message:
```text
repair5g: broaden flow-shield validation and prepare learned selector
```
