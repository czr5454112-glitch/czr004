# czr004 Repair5G.1 Overnight Plan: Agent-Aware Dual-Channel LTM After G0 No-Headroom

**Branch:** `phase4f5p5-stable-attention-lau`
**Start after commit:** `85636b4 repair5g: probe goal-aware dual-channel ltm`
**Status:** proposed overnight diagnostic task
**Promotion status:** `phase5p5_allowed=false`, `phase6_allowed=false`
**Primary project objective:** use learning-enhanced `UpdateLTM` to replace the coarse additive update from the LTM paper and eventually beat `LaCAM*+plain additive LTM` under closed-loop solver metrics, without changing LaCAM*/PIBT legality, conflict, search, or restart semantics.

---

## 0. Executive decision

Repair5G.0/G1 produced a clean negative result for the **first simple global dual-channel candidate family**:

```text
Decision: dual_channel_no_headroom
phase5p5_allowed=false
phase6_allowed=false
```

That result is important, but it should not be treated as a final rejection of goal-aware dual-channel LTM. It rejected a narrow implementation family:

```text
cost(e) = clip(1 + lambda_cong*C_norm(e) - lambda_flow*F_norm(e))
```

where the flow/corridor bonus `F` is global and edge-level, so a flow edge discovered by one agent becomes cheap for every agent. It also did not preserve scalar Repair5F C-channel semantics for committed goal-progress events.

Repair5G.1 must therefore do a stronger diagnostic:

```text
1. Close C-channel scalar-equivalence/parity.
2. Replace global F discount with agent-aware or flow-shielded projection.
3. Use a much broader chunkable candidate lattice than G0.
4. Stop quickly if C-equivalence or additive parity breaks.
5. Remain diagnostic-only: no Phase5.5, no Phase6, no learned action policy.
```

---

## 1. Evidence and interpretation

### 1.1 Repair5F.4.1 remains important

Repair5F.4.1 showed that scalar bounded UpdateParams still has strong oracle headroom on F4 fresh IDs 26..45:

```text
F4 full-lattice oracle:
  67 / 53 / 0
  mean_delta_ratio_vs_ltm = -0.017388555948699997
  ratio_worse_than_ltm_groups = 0
  success_worse_than_ltm_groups = 0

best F4 observed static candidate:
  c125_b125_w075_d095
  35 / 64 / 21
  mean_delta_ratio_vs_ltm = -0.0028050352278249997

support-vs-F4 transfer:
  Spearman = 0.18987049028677153
  locked support rank = 1
  locked F4 rank = 27
```

Interpretation:

```text
The congestion channel is not useless.
The old static support selector picked the wrong global rule.
Repair5G should reuse Repair5F diagnostics as C-channel baselines and controls.
```

### 1.2 Repair5G.0/G1 says naive global F was harmful

G0/G1 development probe on IDs 26..45 reported:

```text
dual_channel_oracle_static_proxy:
  29 / 55 / 36
  mean_delta_ratio_vs_ltm = +0.001879629688233328

best G0 dual candidate:
  repair5g_dual_c_only_best_f4_observed
  17 / 61 / 42
  mean_delta_ratio_vs_ltm = +0.007440336798399994

flow-only candidates:
  0 / 70 / 50
  mean_delta_ratio_vs_ltm = +0.022428777828941655
```

Interpretation:

```text
A global flow bonus is very likely dangerous.
It can make globally popular flow edges cheap for agents for whom they are not goal-progress edges.
```

### 1.3 Why G0 does not fully test Level-2 dual-channel LTM

Two design gaps matter.

#### Gap A: C-only dual candidates were not scalar-equivalent

In scalar Repair5F, all committed moves update the congestion/raw-count channel with `alpha_commit`, regardless of whether the move is goal-progress or not.

In G0 dual-channel code, a committed goal-progress event updates only the flow channel:

```text
if committed and progress > 0:
    F[e] += alpha_flow_commit_progress * progress
else:
    C[e] += alpha_cong_commit_nonprogress
```

Therefore a dual C-only candidate with `alpha_flow_commit_progress=0` can silently ignore committed goal-progress edges instead of behaving like scalar C-only LTM. This likely explains why the G0 C-only candidates performed much worse than the scalar F4 static diagnostic.

Repair5G.1 must add a congestion update for committed goal-progress events:

```text
alpha_cong_commit_progress
```

and verify exact scalar-equivalence.

#### Gap B: F-channel cost was global, not agent-aware

G0 cost was global edge-level:

```text
cost(e) = clip(1 + lambda_cong*C(e) - lambda_flow*F(e))
```

A real goal-aware corridor channel should be projected through the current agent's goal:

```text
cost_i(e) = clip(1 + lambda_cong*C(e) - lambda_flow*F(e)*progress_i(e))
```

or used to shield congestion only when it agrees with the current agent's goal-progress:

```text
cost_i(e) = 1 + lambda_cong*C(e)*(1 - shield(F(e), progress_i(e)))
```

The second form may be safer because it prevents the flow channel from making edges cheaper than base cost; it only prevents over-penalizing useful goal corridors.

---

## 2. Non-negotiable boundaries

Do not:

```text
- modify external/lacam2/lacam2/**
- change PIBT legality, priority inheritance, backtracking, vertex conflict, or swap conflict semantics
- change LaCAM* candidate generation, pruning, OPEN/EXPLORED/rewrite, incumbent pruning, or restart semantics
- introduce action prediction
- introduce learned restart
- directly output learned h_i(v), learned edge action logits, learned priorities, or learned child deletion
- call this Phase5.5 or Phase6
- promote any candidate selected using IDs 26..45
- use IDs 46..65 as final evidence if they are touched during development
```

Allowed:

```text
- project-owned C++ changes under cpp/ltm/** and cpp/tools/phase1a_batch.cpp
- bounded dual-channel traffic-map state
- changing only traversal costs used by WeightedDistanceTable
- exact additive / disable / force-additive fallback
- development diagnostics on IDs 26..45
- optional development-validation on IDs 46..55, marked diagnostic-only
```

---

## 3. Repair5G.1 core questions

### Q1. Can dual-channel C-only exactly reproduce scalar Repair5F?

Required exact or near-exact method pairs:

```text
repair5f_candidate_additive_ltm
  == repair5g_dual_c_equiv_additive

repair5f_static_c100_b100_w075_d090
  == repair5g_dual_c_equiv_c100_b100_w075_d090

repair5f4_best_static_c125_b125_w075_d095_diagnostic_only
  == repair5g_dual_c_equiv_c125_b125_w075_d095
```

If this fails, stop and fix implementation. Do not run large probes.

### Q2. Does agent-aware F avoid G0's global-flow harm?

Test:

```text
goal_projection_mode=agent_progress
lambda_flow in {0.01, 0.025, 0.05, 0.10, 0.20}
min_edge_cost in {0.50, 0.75, 1.00}
```

### Q3. Is flow-shield safer than subtractive flow bonus?

Test:

```text
goal_projection_mode=flow_shield
beta in {0.05, 0.10, 0.20, 0.35}
max_shield in {0.25, 0.50, 0.75}
min_edge_cost >= 1.0 preferred
```

A good result would be:

```text
flow_shield candidates do not create the broad harm seen in G0 flow-only/global-F candidates,
and at least some candidates improve mean delta or group robustness over C-only.
```

### Q4. Does dual-channel headroom exceed scalar C-only headroom?

Compare:

```text
F4 scalar full-lattice oracle
F4 scalar best static candidate
G1 scalar-equivalent C-only candidates
G1 agent-progress F candidates
G1 flow-shield candidates
G1 oracle
G1 random/shuffled diagnostics
```

---

## 4. Required tasks

## P0. Documentation and interpretation

Add/update:

```text
czr004_repair5g1_agent_aware_dual_channel_ltm_overnight_plan.md
docs/codex-worklog.md
outputs/reports/phase5p5_repair5g0_final_interpretation.md
outputs/reports/phase5p5_repair5g1_design_delta.md
```

`phase5p5_repair5g0_final_interpretation.md` must state:

```text
- G0 was a clean negative for a small global-F candidate family.
- G0 build/parity/cost gates passed.
- G0 does not reject dual-channel LTM in general.
- Likely problems: C-only scalar mismatch and agent-agnostic global F bonus.
- phase5p5_allowed=false and phase6_allowed=false remain mandatory.
```

## P1. Analyze G0 semantic gap

Implement:

```text
scripts/analyze_repair5g0_c_channel_semantic_gap.py
```

Inputs:

```text
outputs/reports/phase5p5_repair5g_dual_channel_dev_probe_summary.json
outputs/tables/phase5p5_repair5g_dual_channel_dev_summary.csv
outputs/tables/phase5p5_repair5g_dual_channel_dev_by_map_agent.csv
outputs/tables/phase5p5_repair5f4_full_lattice_static_candidate_ranking.csv
cpp/ltm/ltm.cpp
cpp/ltm/ltm.hpp
```

Outputs:

```text
outputs/reports/phase5p5_repair5g0_c_channel_semantic_gap.md
outputs/reports/phase5p5_repair5g0_c_channel_semantic_gap_summary.json
```

It must answer:

```text
- Do committed progress events update only F in G0?
- Do dual C-only candidates with alpha_flow=0 ignore committed progress events?
- Does that explain the mismatch between scalar c125_b125_w075_d095 and dual c_only_best_f4_observed?
- Is G0 therefore a test of a reduced C semantics, not the scalar F4 C-channel?
```

## P2. Implement C-channel scalar equivalence

Modify project-owned C++ only.

Add fields or equivalent behavior:

```text
alpha_cong_commit_progress
alpha_cong_commit_nonprogress
alpha_flow_commit_progress
```

Committed progress event should support updating both channels:

```text
if committed and progress > 0:
    C[e] += alpha_cong_commit_progress
    F[e] += alpha_flow_commit_progress * progress_scale
elif committed:
    C[e] += alpha_cong_commit_nonprogress
```

For scalar-equivalent C-only candidates:

```text
alpha_cong_commit_progress = alpha_commit
alpha_cong_commit_nonprogress = alpha_commit
alpha_cong_block = alpha_block
alpha_cong_wait_progress = alpha_wait_spillover
alpha_cong_wait_nonprogress = alpha_wait_spillover
rho_cong_decay = rho_decay
lambda_flow = 0
```

Add runtime methods:

```text
repair5g_dual_c_equiv_additive
repair5g_dual_c_equiv_c100_b100_w075_d090
repair5g_dual_c_equiv_c125_b125_w075_d095
repair5g_dual_c_equiv_c100_b125_w075_d100
```

Required exact gates on smoke:

```text
dual_c_equiv_additive_parity_exact=true
dual_c_equiv_locked_matches_scalar=true
dual_c_equiv_best_f4_static_matches_scalar=true
```

## P3. Add optional agent-aware traversal cost

Implement optional `goal_projection_mode`:

```text
none             # legacy G0 global edge-level formula
agent_progress   # subtract F only when edge progresses current agent to its goal
flow_shield      # F reduces C penalty only on current-agent progress edges
```

Cost formulas:

```text
none:
  cost(e) = clip(1 + lambda_C*C(e) - lambda_F*F(e), min_cost, max_cost)

agent_progress:
  progress_i(e) = max(0, dist_i(from) - dist_i(to))
  cost_i(e) = clip(1 + lambda_C*C(e) - lambda_F*F(e)*progress_i(e), min_cost, max_cost)

flow_shield:
  progress_i(e) = max(0, dist_i(from) - dist_i(to))
  shield = clamp(beta * F(e) * progress_i(e), 0, max_shield)
  cost_i(e) = clip(1 + lambda_C*C(e)*(1 - shield), min_cost, max_cost)
```

Implementation guidance:

```text
- WeightedDistanceTable may be extended in project-owned code to call an agent-aware cost function.
- Use unweighted distance-to-goal or a cached base DistTable for progress_i.
- Do not let any learned or dual-channel module output actions, priorities, or legality decisions.
- All costs must be finite and bounded.
```

## P4. Expanded candidate lattice

Implement:

```text
scripts/create_repair5g1_agent_aware_dual_channel_candidates.py
```

Write:

```text
outputs/tables/phase5p5_repair5g1_agent_aware_dual_channel_candidate_lattice.csv
outputs/reports/phase5p5_repair5g1_agent_aware_dual_channel_candidate_lattice_report.md
outputs/reports/phase5p5_repair5g1_agent_aware_dual_channel_candidate_lattice_summary.json
```

Candidate families:

```text
A. Controls / parity
  additive LTM
  laur_disable
  laur_force_additive_direct
  dual additive parity

B. Scalar-equivalent C-only candidates
  additive
  c100_b100_w075_d090
  c125_b125_w075_d095
  c100_b125_w075_d100
  c100_b100_w075_d095
  c100_b100_w100_d090
  c100_b100_w075_d100

C. Global-F small-lambda controls
  lambda_flow in {0.01, 0.025, 0.05, 0.10}
  This checks whether G0 failed mainly because 0.25/0.50 was too strong.

D. Agent-progress F candidates
  C base in {additive, c125_b125_w075_d095, c100_b125_w075_d100, c100_b100_w075_d095}
  lambda_flow in {0.01, 0.025, 0.05, 0.10, 0.20}
  min_cost in {0.50, 0.75, 1.00}
  flow source = committed_progress only

E. Flow-shield candidates
  C base in {c125_b125_w075_d095, c100_b125_w075_d100, c100_b100_w075_d095}
  beta in {0.05, 0.10, 0.20, 0.35}
  max_shield in {0.25, 0.50, 0.75}
  min_cost >= 1.0 preferred

F. Wait-gated candidates
  goal-progress wait exits receive reduced C penalty
  non-progress wait exits receive normal or stronger C penalty
  no direct wait-flow bonus by default

G. Diagnostics
  deterministic random candidate
  shuffled flow/progress diagnostic
```

Target size:

```text
60 <= candidate_count <= 140
```

If the lattice is too large, support chunk/resume and run in blocks.

## P5. Smoke and equivalence closure

Implement or extend:

```text
scripts/run_repair5g1_agent_aware_dual_channel_probe.py
```

Smoke scope:

```text
maps = random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
agents = 50, 100
instance_ids = 26, 27
ltm_max_iterations = 4
time_limit_sec = 3.0
```

Outputs:

```text
outputs/logs/phase5p5_repair5g1_smoke/phase5p5_repair5g1_smoke.jsonl
outputs/logs/phase5p5_repair5g1_smoke/phase5p5_repair5g1_smoke_commands.jsonl
outputs/logs/phase5p5_repair5g1_smoke/phase5p5_repair5g1_smoke_ltm_updates.jsonl
outputs/reports/phase5p5_repair5g1_smoke_report.md
outputs/reports/phase5p5_repair5g1_smoke_summary.json
```

Smoke gates:

```text
build_passed=true
schema_errors=0
missing_rows=0
no_solver_crashes=true
all_costs_finite=true
cost_bounds_respected=true
additive_parity_exact=true
laur_disable_parity_exact=true
laur_force_additive_direct_parity_exact=true
dual_additive_parity_exact=true
dual_c_equiv_additive_parity_exact=true
dual_c_equiv_locked_matches_scalar=true
dual_c_equiv_best_f4_static_matches_scalar=true
phase5p5_allowed=false
phase6_allowed=false
```

If any C-equivalence gate fails, stop and write a failed decision report.

## P6. Overnight development probe

If smoke passes, run development probe on IDs 26..45.

Scope:

```text
maps = random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
agents = 50, 100
instance_ids = 26..45
ltm_max_iterations = 4
time_limit_sec = 3.0
candidate_count ~= 60-140
```

Write:

```text
outputs/logs/phase5p5_repair5g1_dev_probe/phase5p5_repair5g1_dev_probe.jsonl
outputs/logs/phase5p5_repair5g1_dev_probe/phase5p5_repair5g1_dev_probe_commands.jsonl
outputs/logs/phase5p5_repair5g1_dev_probe/phase5p5_repair5g1_dev_probe_ltm_updates.jsonl
outputs/tables/phase5p5_repair5g1_dev_utility_long.csv
outputs/tables/phase5p5_repair5g1_dev_utility_wide.csv
outputs/tables/phase5p5_repair5g1_dev_candidate_ranking.csv
outputs/tables/phase5p5_repair5g1_dev_by_map_agent.csv
outputs/tables/phase5p5_repair5g1_dev_component_ablation.csv
outputs/reports/phase5p5_repair5g1_dev_probe_report.md
outputs/reports/phase5p5_repair5g1_dev_probe_summary.json
```

Use chunk/resume support. Record expected rows, command rows, missing rows, duplicates, and schema errors.

## P7. Optional development-validation if time remains

If P6 finishes and at least one G1 family shows positive diagnostic headroom, optionally run a smaller development-validation.

Scope:

```text
maps = same 3
agents = 50, 100
instance_ids = 46..55
methods = controls + top 10-20 G1 candidates
```

Important:

```text
If IDs 46..55 are used here, they are no longer untouched final holdout.
Reserve IDs 56..75 or later for final validation.
Do not claim promotion from this optional run.
```

Outputs:

```text
outputs/logs/phase5p5_repair5g1_dev_validation/
outputs/tables/phase5p5_repair5g1_dev_validation_*.csv
outputs/reports/phase5p5_repair5g1_dev_validation_*.md/json
```

## P8. Analysis

Implement:

```text
scripts/analyze_repair5g1_agent_aware_dual_channel_oracle.py
```

Compute:

```text
- candidate ranking
- oracle static proxy
- C-only vs global-F vs agent-progress-F vs flow-shield vs wait-gated components
- bootstrap 95% CI
- probability mean_delta < 0
- better/equal/worse
- ratio_worse_than_ltm_groups
- success_worse_than_ltm_groups
- group best candidates
- worst group for each top candidate
- comparison against Repair5F F4 oracle/static results
- random/shuffled diagnostic comparison
- cost audit: min/max cost, clipping rate, flow/C raw and normalized summaries
- update audit: committed progress events, committed non-progress events, blocked events, wait progress/non-progress edges
```

Outputs:

```text
outputs/reports/phase5p5_repair5g1_agent_aware_dual_channel_oracle_report.md
outputs/reports/phase5p5_repair5g1_agent_aware_dual_channel_oracle_summary.json
outputs/reports/phase5p5_repair5g1_agent_aware_dual_channel_decision.md
```

## P9. Decision rules

Possible decisions:

```text
1. stop_repair5g_dual_channel
   Use if C-equivalence closes but agent-aware/flow-shield candidates still have no headroom.

2. continue_repair5g_with_agent_aware_selector
   Use if G1 oracle and at least one non-leaky candidate family beats C-only diagnostics.

3. continue_repair5f_static_protocol_instead
   Use if C-equivalent scalar candidates dominate and F-channel remains harmful.

4. fix_implementation_before_science
   Use if C-equivalence/parity/cost gates fail.
```

Do not export a promoted runtime model in G1. Do not use IDs 46..55 or 56..75 for final if they are touched.

---

## 5. Validation requirements

Run and record:

```text
python -m py_compile <all new/modified Python scripts>
python -m pytest tests/test_repair5f_updateparams.py tests/test_repair5g_dual_channel_ltm.py -q
# If pytest unavailable, record it and run manual fallback harness over all relevant tests.

powershell -ExecutionPolicy Bypass -File scripts/build_phase1a_batch.ps1
# Required if C++ changed.

git diff --check
```

Commit and push only Repair5G.1-related files and records. Leave unrelated dirty/untracked files untouched.

Commit message:

```text
repair5g: close c-channel parity and probe agent-aware dual ltm
```

---

## 6. Codex prompt

```text
Continue czr004 on branch phase4f5p5-stable-attention-lau after commit 85636b4 repair5g: probe goal-aware dual-channel ltm.

Goal:
  Implement Repair5G.1: close dual-channel C-only scalar-equivalence, add agent-aware / flow-shielded goal-corridor projection, run smoke, then run an expanded chunkable development oracle probe if smoke passes. This is diagnostic-only.

Main project objective:
  Use learning-enhanced UpdateLTM to replace the coarse additive update in the LTM paper and eventually beat LaCAM*+plain additive LTM under closed-loop solver metrics, without changing LaCAM*/PIBT semantics.

Read first:
  deep-research-report.md
  phase4_6_laur_ltm_codex_execution_plan.md
  czr004_repair5f41_fresh_failure_oracle_diagnosis_plan.md
  czr004_repair5g0_goal_aware_dual_channel_ltm_plan.md
  czr004_repair5g1_agent_aware_dual_channel_ltm_overnight_plan.md
  outputs/reports/phase5p5_repair5f4_failure_oracle_diagnosis_decision.md
  outputs/reports/phase5p5_repair5f4_full_lattice_oracle_report.md
  outputs/reports/phase5p5_repair5g_dual_channel_decision.md
  outputs/reports/phase5p5_repair5g_dual_channel_oracle_report.md
  outputs/reports/phase5p5_repair5g_dual_channel_dev_probe_report.md
  outputs/reports/phase5p5_repair5g0_design_memo.md

Preserve this interpretation:
  - G0/G1 was a clean negative for a small global-F candidate family.
  - G0/G1 does not reject stronger dual-channel LTM because it did not test C-only scalar equivalence or agent-aware F projection.
  - F4.1 showed scalar bounded UpdateParams still has strong oracle headroom.
  - phase5p5_allowed=false and phase6_allowed=false remain mandatory.

Do not:
  - modify external/lacam2/lacam2/**
  - change PIBT legality, LaCAM* candidate generation, conflict handling, OPEN/EXPLORED/rewrite, incumbent pruning, or restart semantics
  - introduce action prediction
  - introduce learned restart
  - output learned h_i(v), action logits, priority overrides, or child deletion
  - promote any F4/G0 observed candidate
  - claim Phase5.5 or Phase6

Tasks:
  1. Add czr004_repair5g1_agent_aware_dual_channel_ltm_overnight_plan.md to repository root and update docs/codex-worklog.md.

  2. Write outputs/reports/phase5p5_repair5g0_final_interpretation.md and outputs/reports/phase5p5_repair5g1_design_delta.md.

  3. Implement scripts/analyze_repair5g0_c_channel_semantic_gap.py and write the semantic-gap reports.

  4. Fix dual C-channel scalar equivalence in project-owned C++:
       add alpha_cong_commit_progress or equivalent;
       committed progress can update both C and F;
       scalar-equivalent C-only candidates must match scalar Repair5F candidates.

  5. Add optional goal_projection_mode:
       none
       agent_progress
       flow_shield
     Use agent goal progress only to project cost; do not output actions or heuristics directly.

  6. Implement scripts/create_repair5g1_agent_aware_dual_channel_candidates.py with 60-140 diagnostic candidates.

  7. Run smoke on IDs 26,27. Stop if parity/C-equivalence/cost gates fail.

  8. If smoke passes, run chunkable development probe on IDs 26..45.

  9. If time remains and G1 has positive headroom, optionally run a diagnostic development-validation on IDs 46..55 and reserve later IDs for final.

  10. Implement analysis and decision reports. Do not export a promoted runtime artifact.

Validation:
  - py_compile all new/modified Python scripts
  - pytest if available; otherwise manual fallback harness
  - C++ build because C++ is expected to change
  - git diff --check
  - commit and push only Repair5G.1-related files and records
  - leave unrelated dirty/untracked files untouched

Commit message:
  repair5g: close c-channel parity and probe agent-aware dual ltm
```
