# czr004 Repair5G.0/G1 Plan: Goal-Aware Dual-Channel LTM Exploration

**Branch:** `phase4f5p5-stable-attention-lau`
**Start after commit:** `d6667af repair5f: diagnose fresh validation failure`
**Status:** proposed overnight diagnostic exploration
**Promotion status:** `phase5p5_allowed=false`, `phase6_allowed=false`
**Primary project goal:** use learning-enhanced `UpdateLTM` to replace the coarse additive LTM update from the LTM paper and beat `LaCAM*+plain additive LTM` under closed-loop solver metrics, without changing LaCAM*/PIBT semantics.

---

## 0. Why this plan exists

Repair5F.4-A showed that the locked support-trained static rule

```text
c100_b100_w075_d090
alpha_commit         = 1.00
alpha_block          = 1.00
alpha_wait_spillover = 0.75
rho_decay            = 0.90
```

does **not** generalize on fresh IDs 26..45.

Repair5F.4.1 then showed that the bounded UpdateParams lattice still has substantial oracle headroom:

```text
F4 full-lattice oracle:
  better / equal / worse = 67 / 53 / 0
  mean_delta_ratio_vs_ltm = -0.017388555948699997
  ratio_worse_than_ltm_groups = 0
  success_worse_than_ltm_groups = 0

Best F4 observed static candidate:
  c125_b125_w075_d095
  better / equal / worse = 35 / 64 / 21
  mean_delta_ratio_vs_ltm = -0.0028050352278249997
  ratio_worse_than_ltm_groups = 0
  bootstrap CI below 0 on F4 diagnostic split

Support-vs-F4 rank transfer:
  Spearman = 0.18987049028677153
  locked support rank = 1
  locked F4 rank = 27
```

Interpretation:

```text
Repair5F did not fail because bounded UpdateParams have no headroom.
Repair5F failed because the support-trained selector/static protocol overranked a fragile rule.
The current scalar congestion-only UpdateParams space may still be useful,
but it is probably too narrow as the final story.
```

This plan starts a new diagnostic branch:

```text
Repair5G: Goal-Aware Dual-Channel LTM
```

The goal is to test whether LTM should store **two kinds of traffic evidence**:

```text
C[e] = congestion / blockage / wait-risk penalty
F[e] = successful flow / goal-corridor guidance evidence
```

instead of only one negative congestion channel.

---

## 1. High-level research decision

Do **not** directly jump to LaGAT-style learned heuristic or action prediction.

Do **not** modify LaCAM*/PIBT semantics.

Do **not** promote or retune any F4-observed candidate as a final method.

Instead, run an oracle-first representation test:

```text
Question:
  Does a goal-aware dual-channel traffic map have stronger closed-loop
  headroom than congestion-only LTM / Repair5F scalar UpdateParams?

Allowed intervention:
  update the LTM traffic-map state and the edge costs consumed by
  WeightedDistanceTable.

Forbidden intervention:
  directly predict actions, priorities, restart nodes, legal child pruning,
  conflict outcomes, or LaCAM*/PIBT search decisions.
```

This keeps the project story as:

```text
learning-enhanced UpdateLTM
```

not:

```text
learned LaCAM heuristic
learned MAPF action policy
```

---

## 2. Core method concept

### 2.1 Current LTM: one negative channel

Current LTM treats all trace evidence mostly as congestion:

```text
committed edge -> increase traffic penalty
blocked edge   -> increase traffic penalty
wait spillover -> increase traffic penalty
```

Traversal cost is essentially:

```text
cost(e) = 1 + normalized_congestion(e)
```

This only says:

```text
Where should future search avoid?
```

It does not separately say:

```text
Which edges are useful goal-directed flow/corridor evidence?
```

### 2.2 Repair5G: dual-channel LTM

Add a positive, bounded guidance channel:

```text
C_t(e): congestion penalty channel
F_t(e): flow/corridor guidance channel
```

For the first implementation, keep the cost global and edge-level to minimize semantic risk:

```text
cost(e) = clip(
    1.0
    + lambda_cong * C_norm(e)
    - lambda_flow * F_norm(e),
    min_edge_cost,
    max_edge_cost
)
```

This is the G0 version.

It is goal-aware because `F_t(e)` is updated only from agent-goal progress evidence, even if the final cost is still edge-global.

A later G1/G2 version may test agent-projected guidance:

```text
cost_i(e) = clip(
    1.0
    + lambda_cong * C_norm(e)
    - lambda_flow * F_norm(e) * progress_i(e),
    min_edge_cost,
    max_edge_cost
)
```

But do not implement agent-specific cost projection unless the global dual-channel smoke passes and the code change is safely scoped.

---

## 3. Trace semantics for dual-channel updates

For a trace event with agent `i`, edge `u -> v`, and goal `g_i`, define unweighted progress:

```text
base_dist_i(x) = unweighted shortest-path distance from x to goal_i
progress_i(u, v) = max(0, base_dist_i(u) - base_dist_i(v))
regress_i(u, v)  = max(0, base_dist_i(v) - base_dist_i(u))
```

On unit-grid graphs, progress is usually `0` or `1`, but keep it numeric and bounded.

### 3.1 Committed move

A committed move can mean either congestion or successful flow.

Recommended first semantics:

```text
if from != to and progress_i(from, to) > 0:
    F[from, to] += alpha_flow_commit_progress * progress_i(from, to)
else if from != to:
    C[from, to] += alpha_cong_commit_nonprogress
```

Rationale:

```text
A successful goal-progress move is evidence that this edge/corridor can carry useful flow.
A non-progress or regressive move may still be traffic evidence, but should not receive flow bonus.
```

### 3.2 Blocked move

A blocked move is mostly congestion evidence:

```text
if from != to:
    C[from, to] += alpha_cong_block
```

Optional later variant:

```text
if blocked edge was goal-progress:
    C[from, to] += alpha_cong_block_progress
```

because a blocked goal-progress edge is likely a bottleneck on a useful corridor.

### 3.3 Wait event

Current LTM spills wait penalty to all outgoing edges.

Dual-channel first semantics:

```text
if at goal:
    ignore
else:
    for each neighbor v of from:
        if progress_i(from, v) > 0:
            # Do not punish goal-progress exits as strongly.
            C[from, v] += alpha_cong_wait_progress
            F[from, v] += alpha_flow_wait_progress
        else:
            C[from, v] += alpha_cong_wait_nonprogress
```

Start conservative:

```text
alpha_cong_wait_progress    <= alpha_cong_wait_nonprogress
alpha_flow_wait_progress    small or zero
```

This makes wait spillover goal-aware instead of blindly polluting every outgoing edge.

---

## 4. Candidate family for first overnight probe

Keep the first candidate family small and deterministic. The goal is representation headroom, not final tuning.

Suggested candidates:

```text
dcltm_additive_parity
  enable_dual_channel = false
  exact additive LTM parity control

dcltm_c_only_locked_f4
  C channel behaves like c100_b100_w075_d090
  F disabled

dcltm_c_only_best_f4_observed
  C channel behaves like c125_b125_w075_d095
  diagnostic only; do not promote

dcltm_flow_only_025
  C disabled or additive-neutral
  F from committed goal-progress edges
  lambda_flow = 0.25

dcltm_flow_only_050
  same, lambda_flow = 0.50

dcltm_block_wait_cong_flow025
  blocked/wait update C
  committed goal-progress updates F
  lambda_flow = 0.25

dcltm_block_wait_cong_flow050
  same, lambda_flow = 0.50

dcltm_goal_gated_wait_025
  blocked updates C
  wait non-progress exits update C strongly
  wait progress exits update C weakly
  committed progress updates F
  lambda_flow = 0.25

dcltm_goal_gated_wait_050
  same, lambda_flow = 0.50

dcltm_balanced_decay
  C decay = 0.95
  F decay = 0.95
  blocked/wait update C
  committed progress update F
  lambda_flow = 0.25
```

Candidate parameters must be bounded and recorded in a CSV/JSON artifact.

Do not add more candidates until smoke passes.

---

## 5. Engineering boundaries

Allowed files / components:

```text
cpp/ltm/ltm.hpp
cpp/ltm/ltm.cpp
cpp/tools/phase1a_batch.cpp
scripts/create_repair5g_dual_channel_candidates.py
scripts/run_repair5g_dual_channel_probe.py
scripts/analyze_repair5g_dual_channel_oracle.py
tests/test_repair5g_dual_channel_ltm.py
outputs/reports/*
outputs/tables/*
outputs/logs/*
```

Forbidden:

```text
external/lacam2/lacam2/**
PIBT legality semantics
LaCAM* OPEN/EXPLORED/rewrite semantics
candidate generation semantics
vertex/swap conflict semantics
incumbent pruning semantics
learned restart
action prediction
learned priority override
direct learned h_i(v) or action logits
```

Any change to WeightedDistanceTable must only change edge costs derived from LTM state, not legality or search semantics.

---

## 6. Implementation plan

### P0. Documentation and carry-forward

Create:

```text
czr004_repair5g0_goal_aware_dual_channel_ltm_plan.md
outputs/reports/phase5p5_repair5g0_design_memo.md
outputs/reports/phase5p5_repair5f_to_repair5g_transition_interpretation.md
```

The transition interpretation must state:

```text
- F4.1 showed strong bounded UpdateParams oracle headroom.
- F4.1 also showed support-to-F4 transfer was poor.
- The locked static rule failed fresh validation.
- F4 observed best static candidates are diagnostic-only.
- Repair5G is a new representation diagnostic, not a promotion.
- phase5p5_allowed=false and phase6_allowed=false remain mandatory.
```

### P1. Dual-channel candidate artifact

Implement:

```text
scripts/create_repair5g_dual_channel_candidates.py
```

Write:

```text
outputs/tables/phase5p5_repair5g_dual_channel_candidate_lattice.csv
outputs/reports/phase5p5_repair5g_dual_channel_candidate_lattice_report.md
outputs/reports/phase5p5_repair5g_dual_channel_candidate_lattice_summary.json
```

Each candidate row must include:

```text
candidate_id
enable_dual_channel
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
notes
diagnostic_only
phase5p5_allowed=false
phase6_allowed=false
```

### P2. C++ dual-channel LTM smoke implementation

Implement the minimal global dual-channel traffic-map state.

Suggested C++ approach:

```text
DirectedTrafficMap:
  existing raw_counts_ can remain congestion raw counts for legacy path.
  add flow_raw_counts_ and normalized_flow_weights_ only when dual-channel enabled.

UpdateParams:
  either extend UpdateParams with Repair5G fields,
  or introduce a nested DualChannelParams inside UpdateParams.
```

Required behavior:

```text
enable_dual_channel=false:
  exact current LTM behavior.

enable_dual_channel=true:
  update C and F according to candidate params.
  compute normalized C and normalized F.
  traversal_cost = clip(1 + lambda_cong*C_norm - lambda_flow*F_norm,
                        min_edge_cost,
                        max_edge_cost)
```

Goal-progress update requires access to the instance / goals during update. If this is too invasive, implement a scoped overload:

```text
DirectedTrafficMap::update_from_trace(events, params, const Instance* instance)
```

and keep the existing overload unchanged for exact parity.

### P3. Runtime wiring

Extend `phase1a_batch` only as needed to run diagnostic methods such as:

```text
repair5g_dual_additive_parity
repair5g_dual_c_only_locked_f4
repair5g_dual_c_only_best_f4_observed
repair5g_dual_flow_only_025
repair5g_dual_flow_only_050
repair5g_dual_block_wait_cong_flow025
repair5g_dual_block_wait_cong_flow050
repair5g_dual_goal_gated_wait_025
repair5g_dual_goal_gated_wait_050
repair5g_dual_balanced_decay
```

All methods must log:

```text
candidate_id
dual_channel_enabled
lambda_cong
lambda_flow
C/F decay
C/F selected update counts
flow channel nonzero edge count
congestion channel nonzero edge count
laur_update_mode or repair5g_update_mode
```

### P4. Tiny smoke evaluation

Before the full overnight probe, run a tiny smoke:

```text
maps:
  random-32-32-20
  maze-32-32-4
  warehouse-10-20-10-2-1

agents:
  50, 100

instance_ids:
  26, 27

time_limit_sec:
  3.0

ltm_max_iterations:
  4
```

Methods:

```text
lacam_star_ltm
repair5g_dual_additive_parity
repair5g_dual_flow_only_025
repair5g_dual_block_wait_cong_flow025
repair5g_dual_goal_gated_wait_025
```

Write:

```text
outputs/logs/phase5p5_repair5g_dual_channel_smoke/phase5p5_repair5g_dual_channel_smoke.jsonl
outputs/reports/phase5p5_repair5g_dual_channel_smoke_report.md
outputs/reports/phase5p5_repair5g_dual_channel_smoke_summary.json
```

Smoke gates:

```text
build_passed=true
schema_errors=0
missing_rows=0
dual_additive_parity_exact=true
all dual costs finite
all dual costs >= min_edge_cost
no solver crashes
```

If smoke fails, stop and write autopsy. Do not run the larger probe.

### P5. Development oracle probe on F4 diagnostic IDs

If P4 passes, run development oracle on F4 diagnostic IDs 26..45.

Important:

```text
IDs 26..45 are already observed by F4. They are development/diagnostic only.
Do not use these results for a final claim.
Reserve IDs 46..65 or later for untouched final validation.
```

Scope:

```text
maps:
  random-32-32-20
  maze-32-32-4
  warehouse-10-20-10-2-1

agents:
  50, 100

instance_ids:
  26..45

time_limit_sec:
  3.0

ltm_max_iterations:
  4
```

Methods:

```text
lacam_star_ltm
always_additive_defer
repair5f_candidate_additive_ltm
laur_disable
laur_force_additive_direct

repair5f_static_c100_b100_w075_d090
repair5f4_best_static_c125_b125_w075_d095_diagnostic_only

all Repair5G dual-channel candidates from P1
repair5g_random_dual_candidate_diagnostic
repair5g_shuffled_goal_progress_diagnostic, if cheap
```

Write:

```text
outputs/logs/phase5p5_repair5g_dual_channel_dev_probe/phase5p5_repair5g_dual_channel_dev_probe.jsonl
outputs/logs/phase5p5_repair5g_dual_channel_dev_probe/phase5p5_repair5g_dual_channel_dev_probe_commands.jsonl
outputs/logs/phase5p5_repair5g_dual_channel_dev_probe/phase5p5_repair5g_dual_channel_dev_probe_ltm_updates.jsonl

outputs/tables/phase5p5_repair5g_dual_channel_dev_utility_long.csv
outputs/tables/phase5p5_repair5g_dual_channel_dev_utility_wide.csv
outputs/tables/phase5p5_repair5g_dual_channel_dev_summary.csv
outputs/tables/phase5p5_repair5g_dual_channel_dev_by_map_agent.csv
outputs/tables/phase5p5_repair5g_dual_channel_dev_component_ablation.csv

outputs/reports/phase5p5_repair5g_dual_channel_dev_probe_report.md
outputs/reports/phase5p5_repair5g_dual_channel_dev_probe_summary.json
outputs/reports/phase5p5_repair5g_dual_channel_dev_probe_audit.md
```

### P6. Oracle and decision analysis

Implement:

```text
scripts/analyze_repair5g_dual_channel_oracle.py
```

Compute:

```text
dual candidate ranking
dual-channel oracle
C-only vs F-only vs C+F component comparison
by map/agent group breakdown
candidate selected distribution under oracle
bootstrap CI for mean delta
success regressions
random/shuffled diagnostic comparison
comparison to Repair5F full-lattice oracle
```

Write:

```text
outputs/reports/phase5p5_repair5g_dual_channel_oracle_report.md
outputs/reports/phase5p5_repair5g_dual_channel_oracle_summary.json
outputs/tables/phase5p5_repair5g_dual_channel_candidate_ranking.csv
outputs/tables/phase5p5_repair5g_dual_channel_oracle_by_case.csv
outputs/tables/phase5p5_repair5g_dual_channel_group_best_candidates.csv
```

Decision report:

```text
outputs/reports/phase5p5_repair5g_dual_channel_decision.md
```

Possible decisions:

```text
A. dual_channel_has_strong_headroom:
   Plan G1 support/validation selector and reserve IDs 46..65 for final.

B. dual_channel_no_headroom:
   Stop dual-channel LTM and return to Repair5F static-selector protocol or richer features.

C. implementation_not_trusted:
   Fix parity / cost-bound / update-log issues before more experiments.

D. mixed:
   Design narrower goal-gated wait / committed-flow candidate family.
```

---

## 7. Mandatory gates

For smoke:

```text
dual_additive_parity_exact=true
laur_disable_parity_exact=true
force_additive_parity_exact=true
schema_errors=0
missing_rows=0
no solver crashes
cost_bounds_respected=true
phase5p5_allowed=false
phase6_allowed=false
```

For development oracle:

```text
full_expected_rows=true
missing_rows=0
schema_errors=0
support_dev_overlap_count=0 for any final-reserved split
dual_additive_parity_exact=true
laur_disable_parity_exact=true
force_additive_parity_exact=true
cost_bounds_respected=true
dual_channel_oracle_better_gt_worse=true
dual_channel_oracle_mean_delta_ratio_vs_ltm < 0
dual_channel_oracle_success_worse_than_ltm_groups = 0
phase5p5_allowed=false
phase6_allowed=false
```

Do **not** require dual-channel static candidate to pass final promotion gates in G0. This is representation exploration.

---

## 8. What would count as a good overnight result?

Strong positive diagnostic:

```text
dual-channel oracle mean_delta_ratio_vs_ltm <= -0.01
dual-channel oracle better >> worse
C+F candidates outperform C-only and F-only
additive parity exact
cost bounds clean
no success-regression groups
```

Moderate positive diagnostic:

```text
some C+F candidate has mean < 0 and better > worse
but CI crosses 0 or group failures remain
```

Negative diagnostic:

```text
dual-channel candidates do not beat Repair5F static or random diagnostics
dual-channel oracle weak
C+F adds no value over C-only
```

Implementation blocker:

```text
parity fails
cost bounds fail
runtime crashes
trace update logs inconsistent
```

---

## 9. Validation requirements

Run:

```text
python -m py_compile scripts/create_repair5g_dual_channel_candidates.py scripts/run_repair5g_dual_channel_probe.py scripts/analyze_repair5g_dual_channel_oracle.py
python -m pytest tests/test_repair5f_updateparams.py tests/test_repair5g_dual_channel_ltm.py -q
```

If pytest is unavailable, record it and run a manual fallback harness.

If C++ changed, run:

```text
powershell -ExecutionPolicy Bypass -File scripts/build_phase1a_batch.ps1
```

Always run:

```text
git diff --check
```

Commit and push only Repair5G.0/G1-related files and records. Leave unrelated dirty/untracked files untouched.

Commit message:

```text
repair5g: probe goal-aware dual-channel ltm
```

---

## 10. Codex prompt

```text
Continue czr004 on branch phase4f5p5-stable-attention-lau after commit d6667af repair5f: diagnose fresh validation failure.

Goal:
  Implement Repair5G.0/G1: goal-aware dual-channel LTM design, minimal runtime support, smoke test, and development oracle probe. This is diagnostic-only. Do not claim Phase5.5, Phase6, or context-adaptive learned heuristic.

Main project objective:
  Use learning-enhanced UpdateLTM to replace the coarse additive update in the LTM paper and eventually beat LaCAM*+plain additive LTM under closed-loop solver metrics, without changing LaCAM*/PIBT semantics.

Read first:
  deep-research-report.md
  phase4_6_laur_ltm_codex_execution_plan.md
  czr004_repair5f_bounded_updateparams_decision_plan.md
  czr004_repair5f4_static_updateparams_larger_validation_plan.md
  czr004_repair5f41_fresh_failure_oracle_diagnosis_plan.md
  czr004_repair5g0_goal_aware_dual_channel_ltm_plan.md
  outputs/reports/phase5p5_repair5f4_failure_oracle_diagnosis_decision.md
  outputs/reports/phase5p5_repair5f4_full_lattice_oracle_report.md
  outputs/reports/phase5p5_repair5f4_full_lattice_oracle_summary.json
  outputs/reports/phase5p5_repair5f4_final_interpretation.md

Preserve this interpretation:
  - F4-A was a clean static-rule failure.
  - F4.1 showed strong bounded-lattice oracle headroom:
      67 / 53 / 0
      mean_delta_ratio_vs_ltm = -0.017388555948699997
      ratio_worse_than_ltm_groups = 0
  - Best F4 observed static candidate c125_b125_w075_d095 is diagnostic-only and cannot be promoted from F4.
  - Support-to-F4 transfer was poor:
      Spearman = 0.18987049028677153
      locked support rank = 1
      locked F4 rank = 27
  - Repair5G is a representation diagnostic: LTM should test whether it needs both congestion penalty and goal/corridor guidance channels.
  - phase5p5_allowed=false and phase6_allowed=false remain mandatory.

Do not:
  - modify external/lacam2/lacam2/**
  - change PIBT legality, LaCAM* candidate generation, conflict handling, OPEN/EXPLORED/rewrite, incumbent pruning, or restart semantics
  - introduce action prediction
  - introduce learned restart
  - directly output learned h_i(v), learned edge action logits, learned priorities, or learned candidate deletion
  - promote any F4-observed candidate
  - use IDs 46..65 final holdout for tuning
  - claim Phase5.5 or Phase6

Core design:
  Add a diagnostic dual-channel LTM:
    C[e] = congestion/blockage/wait penalty evidence
    F[e] = successful goal-progress flow/corridor evidence

  First implementation may use global edge cost:
    cost(e) = clip(1 + lambda_cong*C_norm(e) - lambda_flow*F_norm(e),
                   min_edge_cost,
                   max_edge_cost)

  Keep exact additive parity when dual-channel is disabled.

Tasks:
  1. Add czr004_repair5g0_goal_aware_dual_channel_ltm_plan.md to repository root and update docs/codex-worklog.md.

  2. Write:
       outputs/reports/phase5p5_repair5g0_design_memo.md
       outputs/reports/phase5p5_repair5f_to_repair5g_transition_interpretation.md

  3. Implement:
       scripts/create_repair5g_dual_channel_candidates.py
       outputs/tables/phase5p5_repair5g_dual_channel_candidate_lattice.csv
       outputs/reports/phase5p5_repair5g_dual_channel_candidate_lattice_report.md
       outputs/reports/phase5p5_repair5g_dual_channel_candidate_lattice_summary.json

  4. Implement minimal project-owned C++ support for dual-channel LTM:
       - exact legacy behavior when enable_dual_channel=false
       - C and F raw/normalized channels when enable_dual_channel=true
       - goal-progress-based F updates using agent goals
       - bounded costs
       - no external/lacam2/lacam2 changes

  5. Extend phase1a_batch/runtime wiring only enough to run diagnostic Repair5G methods:
       repair5g_dual_additive_parity
       repair5g_dual_c_only_locked_f4
       repair5g_dual_c_only_best_f4_observed
       repair5g_dual_flow_only_025
       repair5g_dual_flow_only_050
       repair5g_dual_block_wait_cong_flow025
       repair5g_dual_block_wait_cong_flow050
       repair5g_dual_goal_gated_wait_025
       repair5g_dual_goal_gated_wait_050
       repair5g_dual_balanced_decay

  6. Run tiny smoke first:
       maps = random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
       agents = 50, 100
       instance_ids = 26, 27
       time_limit_sec = 3.0
       ltm_max_iterations = 4
     Stop if smoke parity/cost/build gates fail.

  7. If smoke passes, run development oracle probe on IDs 26..45:
       maps = random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
       agents = 50, 100
       instance_ids = 26..45
       time_limit_sec = 3.0
       ltm_max_iterations = 4
     Treat IDs 26..45 as diagnostic/development only. Reserve IDs 46..65 or later for untouched final.

  8. Write all outputs under:
       outputs/logs/phase5p5_repair5g_dual_channel_smoke/
       outputs/logs/phase5p5_repair5g_dual_channel_dev_probe/
       outputs/tables/phase5p5_repair5g_dual_channel_*.csv
       outputs/reports/phase5p5_repair5g_dual_channel_*.md/json

  9. Implement:
       scripts/run_repair5g_dual_channel_probe.py
       scripts/analyze_repair5g_dual_channel_oracle.py
     Compute candidate rankings, oracle, component comparison C-only vs F-only vs C+F, group breakdown, bootstrap CI, success regression risk, and random/shuffled diagnostics if cheap.

  10. Write:
       outputs/reports/phase5p5_repair5g_dual_channel_decision.md
     Decide whether dual-channel LTM has enough diagnostic headroom to justify a later G1 support/validation selector with untouched final IDs.

Validation:
  - py_compile all new/modified Python scripts
  - run pytest if available; otherwise manual fallback harness
  - if C++ changed, run scripts/build_phase1a_batch.ps1
  - git diff --check
  - commit and push only Repair5G-related files and records
  - leave unrelated dirty/untracked files untouched

Commit message:
  repair5g: probe goal-aware dual-channel ltm
```
