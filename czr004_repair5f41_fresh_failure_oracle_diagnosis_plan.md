# czr004 Repair5F.4.1 Plan: Fresh-Holdout Failure Decomposition and Full-Lattice Oracle Diagnosis

**Branch:** `phase4f5p5-stable-attention-lau`
**Start after:** `ca4dfb6 repair5f: validate static updateparams on fresh holdout`
**Status:** proposed diagnostic follow-up after F4-A larger-validation failure
**Promotion status:** `phase5p5_allowed=false`, `phase6_allowed=false`
**Main project objective:** use learning-enhanced `UpdateLTM` to replace LTM's coarse additive update and beat `LaCAM*+plain additive LTM` under closed-loop solver metrics, without changing LaCAM*/PIBT semantics.

---

## 0. Why this follow-up exists

Repair5F.4-A was a high-quality negative result.

It completed the fresh-ID larger validation with clean engineering controls:

```text
expected_rows = 1800
raw_rows_after_dedupe = 1800
missing_rows = 0
schema_errors = 0

force_additive_parity_exact = true
exact_additive_candidate_parity_exact = true
laur_disable_parity_exact = true
laur_force_additive_direct_parity_exact = true

support_validation_overlap_count = 0
f2f3_holdout_validation_overlap_count = 0
phase5p5_allowed = false
phase6_allowed = false
```

But the locked support-trained static rule did not generalize:

```text
repair5f_static_c100_b100_w075_d090:
  rows = 120
  better / equal / worse = 25 / 68 / 27
  mean_delta_ratio_vs_ltm = +0.0000451908770666587
  bootstrap_95ci_mean_delta_ratio_vs_ltm =
    [-0.0025432106323166875, 0.002837331297599984]

Failed gates:
  main_static_better_gt_worse = false
  main_static_mean_delta_ratio_vs_ltm_lt_0 = false
  main_static_bootstrap_ci_upper_le_0 = false
  main_static_ratio_worse_than_ltm_groups_le_1 = false
  main_static_beats_deterministic_random_candidate_diagnostic = false
```

Therefore, do **not** proceed to F4-B time-budget stress validation. The current static rule is not a reliable candidate.

The next step is not retuning from F4 and not promotion. The next step is a diagnostic autopsy:

```text
Repair5F.4.1:
  Explain why the locked static rule failed on fresh IDs 26..45.
  Determine whether the bounded UpdateParams lattice still contains robust
  fresh-ID headroom.
  Decide whether Repair5 should pivot to a properly trained context/group-adaptive
  UpdateParams selector with a new untouched final holdout, or whether bounded
  UpdateParams should be stopped.
```

---

## 1. Interpretation to preserve

### 1.1 What remains positive

Repair5F.3.1 was not invalidated by F4. It remains true that:

```text
- runtime artifact wiring works
- additive parity controls can be exact
- F2/F3 small final holdout showed a weak positive signal
- the intervention remains inside UpdateLTM
- no LaCAM*/PIBT semantics were changed
```

### 1.2 What F4 falsified

F4-A falsified the specific claim:

```text
A globally fixed support-trained c100_b100_w075_d090 rule is robustly better
than additive LTM on fresh IDs 26..45.
```

Do not describe `c100_b100_w075_d090` as a validated replacement after F4-A.

### 1.3 What F4 suggests but does not prove

Component ablations suggest that the problem may be `rho_decay=0.90` or a global static rule rather than the entire bounded UpdateParams idea:

```text
repair5f_static_c100_b100_w075_d100:
  25 / 72 / 23
  mean_delta_ratio_vs_ltm = -0.0008398811590833434

repair5f_static_c100_b100_w100_d090:
  23 / 74 / 23
  mean_delta_ratio_vs_ltm = -0.0003064312557916717

repair5f_static_c100_b100_w075_d095:
  22 / 76 / 22
  mean_delta_ratio_vs_ltm = -0.0008186365335416705
```

These are **diagnostic observations only**. Do not retune from F4 and claim success. If they motivate a new method, that method must be trained/tuned on allowed support/validation data and evaluated on a new untouched final holdout.

### 1.4 The current branch point

The key scientific question is now:

```text
Is the failure because:
  A. bounded UpdateParams no longer has enough fresh-ID headroom,
  B. the selected static c100_b100_w075_d090 rule overfit IDs 21..25,
  C. a different static rule is more robust but was not selected by support-only F2,
  D. benefits are strongly map/agent/context-dependent and require an adaptive selector,
  E. most observed gains are solver/time-budget noise and should not be pursued?
```

Repair5F.4.1 must answer this before more runtime promotion work.

---

## 2. Non-negotiable constraints

Do not:

```text
- modify external/lacam2/lacam2/**
- change PIBT, LaCAM*, candidate generation, pruning, conflict semantics,
  OPEN/EXPLORED, incumbent pruning, rewrite, or restart semantics
- introduce action prediction
- introduce learned restart
- introduce richer traffic-map representation
- claim Phase5.5 or Phase6
- claim context-adaptive selection before a selector wins against static/random/shuffled controls
- retune c100_b100_w075_d090 from F4 and call it validated
- use F4 outcomes as final evidence for any newly selected rule
```

Allowed:

```text
- diagnostic analysis of F4 failure
- full bounded-lattice diagnostic on F4 IDs 26..45
- oracle/headroom analysis
- group/subgroup analysis
- support-vs-F4 rank correlation analysis
- planning a new training/validation/final split with untouched IDs 46..65 or later
```

---

## 3. Required work

## P0. Documentation

Add this file to the repository root:

```text
czr004_repair5f41_fresh_failure_oracle_diagnosis_plan.md
```

Update:

```text
docs/codex-worklog.md
```

Write:

```text
outputs/reports/phase5p5_repair5f4_final_interpretation.md
```

The interpretation must state:

```text
- F4-A was a clean diagnostic failure, not an engineering failure.
- Coverage, freshness, and additive parity controls passed.
- The locked c100_b100_w075_d090 rule did not generalize.
- Do not promote, do not retune from F4, and do not claim Phase5.5/Phase6.
- The correct next step is failure decomposition and full-lattice oracle diagnosis.
```

---

## P1. F4 static-failure autopsy

Implement:

```text
scripts/analyze_repair5f4_static_failure.py
```

Inputs:

```text
outputs/reports/phase5p5_repair5f4_static_updateparams_validation_summary.json
outputs/reports/phase5p5_repair5f4_static_updateparams_validation_report.md
outputs/tables/phase5p5_repair5f4_static_updateparams_validation_paired.csv
outputs/tables/phase5p5_repair5f4_static_updateparams_validation_by_map_agent.csv
outputs/tables/phase5p5_repair5f4_static_updateparams_validation_component_ablation.csv
outputs/reports/phase5p5_repair5f4_static_updateparams_validation_freshness_audit_summary.json
```

Outputs:

```text
outputs/reports/phase5p5_repair5f4_static_failure_autopsy.md
outputs/reports/phase5p5_repair5f4_static_failure_autopsy_summary.json
outputs/tables/phase5p5_repair5f4_static_failure_cases.csv
outputs/tables/phase5p5_repair5f4_static_failure_by_group.csv
outputs/tables/phase5p5_repair5f4_component_dominance.csv
```

Required analysis:

```text
- worst groups and best groups for c100_b100_w075_d090
- per-map-agent mean delta, better/equal/worse, and success regression
- whether failures concentrate in maze-100, random-50, or other groups
- whether warehouse is mostly no-op / no-effect
- component dominance:
    c100_b100_w075_d100  # wait 0.75 only
    c100_b100_w100_d090  # decay 0.90 only
    c100_b100_w100_d095  # decay 0.95 only
    c100_b100_w075_d095  # wait 0.75 + decay 0.95
    c100_b100_w075_d090  # F2/F3 locked rule
- pairwise per-case wins/losses among component ablations
- bootstrap CI and sign probability for each component
- deterministic random diagnostic comparison
- E5 real and E5 shuffled diagnostic comparison
```

Do not create a new candidate or runtime artifact in P1.

---

## P2. Full bounded-lattice diagnostic on F4 fresh IDs

Run the full 47-candidate bounded UpdateParams lattice over the same F4 fresh IDs:

```text
maps:
  random-32-32-20
  maze-32-32-4
  warehouse-10-20-10-2-1

agents:
  50
  100

instance_ids:
  26..45

time_limit_sec:
  3.0

ltm_max_iterations:
  4
```

This is diagnostic-only and may use chunk/resume.

Use or extend existing candidate-probe tooling. Do not change C++ solver semantics.

Write:

```text
outputs/logs/phase5p5_repair5f4_full_lattice_probe/
  phase5p5_repair5f4_full_lattice_probe.jsonl
  phase5p5_repair5f4_full_lattice_probe_commands.jsonl
  phase5p5_repair5f4_full_lattice_probe_laur_updates.jsonl

outputs/tables/
  phase5p5_repair5f4_full_lattice_utility_long.csv
  phase5p5_repair5f4_full_lattice_utility_wide.csv

outputs/reports/
  phase5p5_repair5f4_full_lattice_probe_report.md
  phase5p5_repair5f4_full_lattice_probe_summary.json
  phase5p5_repair5f4_full_lattice_probe_audit.md
```

Required controls:

```text
force_additive_parity_exact = true
exact_additive_candidate_parity_exact = true
laur_disable_parity_exact = true
support_validation_overlap_count = 0
f2f3_holdout_validation_overlap_count = 0
phase5p5_allowed = false
phase6_allowed = false
```

---

## P3. Full-lattice oracle and robustness analysis

Implement:

```text
scripts/analyze_repair5f4_full_lattice_oracle.py
```

Inputs:

```text
outputs/tables/phase5p5_repair5f4_full_lattice_utility_long.csv
outputs/tables/phase5p5_repair5f4_full_lattice_utility_wide.csv
outputs/tables/phase5p5_repair5f4_static_updateparams_validation_paired.csv
outputs/tables/phase5p5_repair5f4_static_updateparams_validation_by_map_agent.csv
outputs/reports/phase5p5_repair5f_selector_threshold_sweep_summary.json
outputs/reports/phase5p5_repair5f_selector_simulation_summary.json
```

Outputs:

```text
outputs/reports/phase5p5_repair5f4_full_lattice_oracle_report.md
outputs/reports/phase5p5_repair5f4_full_lattice_oracle_summary.json
outputs/tables/phase5p5_repair5f4_full_lattice_oracle_by_case.csv
outputs/tables/phase5p5_repair5f4_full_lattice_static_candidate_ranking.csv
outputs/tables/phase5p5_repair5f4_full_lattice_group_best_candidates.csv
outputs/tables/phase5p5_repair5f4_support_vs_f4_rank_correlation.csv
```

Required analysis:

```text
1. F4 full-lattice oracle:
   - better / equal / worse
   - mean_delta_ratio_vs_ltm
   - ratio_worse_than_ltm_groups
   - success_worse_than_ltm_groups
   - selected candidate distribution

2. Best single static candidate on F4:
   - diagnostic only
   - must not be claimed as selected method
   - compare with c100_b100_w075_d090 and component ablations

3. Robust static selection:
   - leave-one-map-agent-group-out static candidate selection
   - maximin group mean delta
   - min worst-group harm
   - better>worse robustness

4. Group-adaptive oracle:
   - choose one candidate per map-agent group using only that group's F4 outcomes
   - diagnostic only
   - estimate headroom for group-adaptive selector

5. Support-vs-F4 transfer:
   - support mean candidate ranking vs F4 mean candidate ranking
   - Spearman/Pearson rank correlation where possible
   - whether F2 support overranked c100_b100_w075_d090
   - whether the support objective was too narrow or too optimistic

6. Failure classification:
   - no headroom
   - static overfit
   - group heterogeneity
   - noisy/time-budget-sensitive effects
   - selector/objective mismatch
```

---

## P4. Decision report

Write:

```text
outputs/reports/phase5p5_repair5f4_failure_oracle_diagnosis_decision.md
```

Decision logic:

### Case A: F4 full-lattice oracle is weak

If:

```text
oracle mean_delta_ratio_vs_ltm >= 0
or oracle better <= worse
or oracle ratio_worse_than_ltm_groups > 1
or oracle success_worse_than_ltm_groups > 0
```

then:

```text
Stop Repair5F bounded UpdateParams branch as currently defined.
Do not proceed to adaptive selector.
Recommend returning to richer UpdateLTM evidence features or broader event representation,
still without changing solver semantics.
```

### Case B: F4 oracle is strong, but no static candidate is robust

If oracle is strong but the best static candidate and leave-one-group robust static selection are weak, then:

```text
Recommend Repair5G:
  support/validation-trained group/context-adaptive bounded UpdateParams selector
  evaluated only on untouched final IDs 46..65 or later.
```

### Case C: a static candidate looks robust on F4

If a different static candidate appears robust on F4, then:

```text
Treat it as diagnostic only.
Plan a new support+validation training protocol and untouched final validation.
Do not claim F4-tuned success.
```

### Case D: support-vs-F4 rank transfer is poor

If support rankings do not transfer to F4, then:

```text
Diagnose selector objective and support representativeness before more runtime export.
```

---

## 4. Validation

Run:

```text
python -m py_compile scripts/analyze_repair5f4_static_failure.py scripts/analyze_repair5f4_full_lattice_oracle.py
python -m pytest tests/test_repair5f_updateparams.py -q
```

If pytest is unavailable, record that and run the manual fallback harness over all Repair5F tests.

If C++ changed, run:

```text
powershell -ExecutionPolicy Bypass -File scripts/build_phase1a_batch.ps1
```

Always run:

```text
git diff --check
```

Commit and push only Repair5F.4.1-related files and records. Leave unrelated dirty/untracked files untouched.

Commit message:

```text
repair5f: diagnose fresh validation failure
```

---

## 5. Codex prompt

```text
Continue czr004 on branch phase4f5p5-stable-attention-lau after commit ca4dfb6 repair5f: validate static updateparams on fresh holdout.

Goal:
  Implement Repair5F.4.1: fresh-holdout failure decomposition and full-lattice oracle diagnosis. F4-A failed the performance gates for the locked support-trained static rule, so do not run F4-B time-budget validation and do not retune/promote from F4 outcomes.

Main project objective:
  Use learning-enhanced UpdateLTM to replace the coarse additive update in the LTM paper and eventually beat LaCAM*+plain additive LTM under closed-loop solver metrics, without changing LaCAM*/PIBT semantics.

Read first:
  deep-research-report.md
  phase4_6_laur_ltm_codex_execution_plan.md
  czr004_repair5f_bounded_updateparams_decision_plan.md
  czr004_repair5f1_safety_parity_closure_plan.md
  czr004_repair5f2_updateparam_selector_plan.md
  czr004_repair5f3_runtime_export_static_ablation_plan.md
  czr004_repair5f31_runtime_parity_closure_plan.md
  czr004_repair5f4_static_updateparams_larger_validation_plan.md
  czr004_repair5f41_fresh_failure_oracle_diagnosis_plan.md
  outputs/reports/phase5p5_repair5f4_static_updateparams_validation_decision.md
  outputs/reports/phase5p5_repair5f4_static_updateparams_validation_report.md
  outputs/reports/phase5p5_repair5f4_static_updateparams_validation_summary.json
  outputs/reports/phase5p5_repair5f4_static_updateparams_validation_audit.md
  outputs/reports/phase5p5_repair5f4_static_updateparams_validation_freshness_audit.md
  outputs/tables/phase5p5_repair5f4_static_updateparams_validation_by_map_agent.csv
  outputs/tables/phase5p5_repair5f4_static_updateparams_validation_component_ablation.csv

Preserve this interpretation:
  - F4-A was a clean diagnostic failure, not an engineering failure.
  - Freshness/leakage and additive parity controls passed.
  - The locked rule c100_b100_w075_d090 did not generalize:
      25 / 68 / 27
      mean_delta_ratio_vs_ltm = +0.0000451908770666587
      bootstrap 95% CI crosses zero
  - The locked rule failed to beat deterministic random diagnostic.
  - Do not promote. Do not claim Phase5.5 or Phase6.
  - Do not retune from F4 and claim success.
  - The next question is whether the bounded UpdateParams lattice still has robust fresh-ID headroom.

Do not:
  - modify external/lacam2/lacam2/**
  - change PIBT, LaCAM*, candidate generation, pruning, conflict semantics, OPEN/EXPLORED, incumbent pruning, rewrite, or restart semantics
  - introduce action prediction
  - introduce learned restart
  - introduce richer traffic-map representation
  - claim context-adaptive selection
  - claim Phase5.5 or Phase6
  - export a new promoted runtime artifact
  - use F4 outcomes as final evidence for a newly selected rule

Tasks:
  1. Add czr004_repair5f41_fresh_failure_oracle_diagnosis_plan.md to the repository root and update docs/codex-worklog.md.

  2. Write outputs/reports/phase5p5_repair5f4_final_interpretation.md.

  3. Implement scripts/analyze_repair5f4_static_failure.py.
     Write:
       outputs/reports/phase5p5_repair5f4_static_failure_autopsy.md
       outputs/reports/phase5p5_repair5f4_static_failure_autopsy_summary.json
       outputs/tables/phase5p5_repair5f4_static_failure_cases.csv
       outputs/tables/phase5p5_repair5f4_static_failure_by_group.csv
       outputs/tables/phase5p5_repair5f4_component_dominance.csv

  4. Run full bounded-lattice diagnostic over F4 fresh IDs 26..45:
       maps = random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
       agents = 50, 100
       instance_ids = 26..45
       time_limit_sec = 3.0
       ltm_max_iterations = 4
       candidates = full Repair5F 47-candidate lattice
     Use chunk/resume if needed.

     Write:
       outputs/logs/phase5p5_repair5f4_full_lattice_probe/phase5p5_repair5f4_full_lattice_probe.jsonl
       outputs/logs/phase5p5_repair5f4_full_lattice_probe/phase5p5_repair5f4_full_lattice_probe_commands.jsonl
       outputs/logs/phase5p5_repair5f4_full_lattice_probe/phase5p5_repair5f4_full_lattice_probe_laur_updates.jsonl
       outputs/tables/phase5p5_repair5f4_full_lattice_utility_long.csv
       outputs/tables/phase5p5_repair5f4_full_lattice_utility_wide.csv
       outputs/reports/phase5p5_repair5f4_full_lattice_probe_report.md
       outputs/reports/phase5p5_repair5f4_full_lattice_probe_summary.json
       outputs/reports/phase5p5_repair5f4_full_lattice_probe_audit.md

  5. Implement scripts/analyze_repair5f4_full_lattice_oracle.py.
     Write:
       outputs/reports/phase5p5_repair5f4_full_lattice_oracle_report.md
       outputs/reports/phase5p5_repair5f4_full_lattice_oracle_summary.json
       outputs/tables/phase5p5_repair5f4_full_lattice_oracle_by_case.csv
       outputs/tables/phase5p5_repair5f4_full_lattice_static_candidate_ranking.csv
       outputs/tables/phase5p5_repair5f4_full_lattice_group_best_candidates.csv
       outputs/tables/phase5p5_repair5f4_support_vs_f4_rank_correlation.csv

  6. Write outputs/reports/phase5p5_repair5f4_failure_oracle_diagnosis_decision.md.
     Decide:
       - stop bounded UpdateParams branch,
       - or plan Repair5G adaptive/group selector with untouched IDs 46..65,
       - or plan a new static candidate protocol with untouched final validation.
     Do not promote anything from F4.

Validation:
  - py_compile all new/modified Python scripts
  - python -m pytest tests/test_repair5f_updateparams.py -q
  - if pytest unavailable, run manual fallback harness and record it
  - if C++ changed, run scripts/build_phase1a_batch.ps1
  - git diff --check
  - commit and push only Repair5F.4.1-related files and records
  - leave unrelated dirty/untracked files untouched

Commit message:
  repair5f: diagnose fresh validation failure
```
