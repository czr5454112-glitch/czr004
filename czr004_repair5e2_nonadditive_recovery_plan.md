# czr004 Repair5E.2 Plan: Recover Positive Non-Additive UpdateLTM Choices Without Leaving the Simple LAUR Idea

**Branch:** `phase4f5p5-stable-attention-lau`  
**Latest pushed commit:** `b16f87bfdc6ee5e9458f7912536678adc690c678`  
**Latest commit message:** `repair5e caseb ood guard`  
**Current objective:** keep the project on the same simple idea: learn an `UpdateLTM` policy that can exceed plain additive LTM, without predicting agent actions and without changing PIBT/LaCAM*/candidate/pruning/gate semantics.

This plan does **not** switch to action prediction, learned restart, solver replacement, richer agent policy, or continuous update-parameter control. It stays inside LAUR / learned `UpdateLTM` and the existing preset-rule space unless diagnostics prove that this space is exhausted.

---

## 0. Current State After `b16f87b`

Repair5E.1 implemented an OOD/defer guard around the existing Repair5D composite distilled bridge.

Latest preflight result:

```text
repair5e_caseb_ood_guard_distilled:
  better/equal/worse vs LaCAM*+LTM = 0 / 18 / 0
  mean delta ratio vs LTM = 0.0
  ratio_worse_than_ltm_groups = 0
  success_worse_than_ltm_groups = 0
  zero_nonadditive_groups = 6

repair5d_composite_diagnostic_distilled:
  better/equal/worse = 1 / 12 / 5
  mean delta ratio vs LTM = +0.0025935989466666395
  ratio_worse_than_ltm_groups = 2

oracle_teacher_forced_best_safe_update_static_proxy:
  better/equal/worse = 8 / 9 / 1
  mean delta ratio vs LTM = -0.010131897741666685
```

Interpretation:

```text
OOD guard successfully removed Repair5D-distill regressions.
But it did so by deferring to additive_ltm everywhere in the evaluated groups.
So it is a safe fallback baseline, not a Repair5 breakthrough.
```

The latest decision table remains:

```text
case = B
oracle_positive = true
repair5d_positive = false
phase5p5_allowed = false
phase6_allowed = false
recommended_action = improve_composite_or_reranker_do_not_jump_to_delta_updateparams
```

This means Repair5 is still alive, but the next step must recover **positive non-additive choices** while keeping the OOD/defer guard as a safety rail.

---

## 1. What This Result Proved

### 1.1 Safety / non-regression improved

The OOD guard is useful because it turned the previous Repair5D distilled closed-loop result from:

```text
1 / 12 / 5, mean +0.00259
```

into:

```text
0 / 18 / 0, mean 0.0
```

So the guard can protect the runtime from bad learned updates.

### 1.2 It did not yet exceed simple additive LTM

The guarded method equals LTM, not beats it.

The important red flag is:

```text
zero_nonadditive_groups = 6
non-additive update rate = 0.0 in every group
```

That means the method is currently too conservative: it has become an additive-LTM parity mode.

### 1.3 Oracle headroom still exists

The oracle/static proxy remains positive:

```text
8 / 9 / 1, mean delta = -0.01013
```

Therefore the project should not jump away from LAUR. The next bottleneck is learning/selecting the good non-additive preset updates, not changing solver semantics.

---

## 2. Keep the Simple Idea: Exceed Plain Additive LTM

The project goal remains simple:

```text
LaCAM*+LTM uses simple additive LTM updates.
Repair5 should learn when a small preset UpdateLTM variant is better than simple additive.
```

Allowed:

```text
learned UpdateLTM selector
8 preset rules plus additive/defer fallback
safety mask
OOD/defer guard
rule ranking / utility rerank inside the selector
closed-loop diagnostic logging
```

Not allowed:

```text
agent action prediction
PIBT replacement
LaCAM* replacement
candidate-generation or pruning changes
learned restart
lowering final gates
Phase5.5/Phase6 claim from diagnostic preflight
bounded ΔUpdateParams implementation in this step
richer LTM representation as the main branch in this step
```

---

## 3. Main Diagnosis

The current failure mode is not “no signal.” It is:

```text
Repair5D distilled selector collapsed into bad / unbalanced runtime decisions,
then OOD guard safely deferred those decisions back to additive LTM.
```

The previous Case-B analysis showed:

```text
Repair5D closed-loop rule distribution:
  {'commit_heavy': 43, 'wait_light': 2}

oracle/static closed-loop distribution:
  {'block_heavy': 7, 'block_light': 12, 'commit_heavy': 1,
   'decay_090': 5, 'wait_heavy': 4, 'wait_light': 16}

Repair5D closed-loop commit_heavy share:
  0.9555555555555556
```

So the next step should not merely make the guard stricter. It should recover the oracle-like diversity of safe non-additive choices while keeping the guard.

---

## 4. Repair5E.2 Objective

Call the next phase:

```text
Repair5E.2: Guarded Non-Additive Recovery
```

Primary question:

```text
Can we recover a small amount of positive, safe non-additive UpdateLTM behavior
from the current 8 preset rules, while preserving the no-regression behavior of
the OOD guard?
```

Success is not Phase5.5. Success is a stronger diagnostic candidate than Repair5E.1.

Target criteria:

```text
success_worse_than_ltm_groups = 0
ratio_worse_than_ltm_groups <= 1
mean_delta_ratio_vs_ltm < 0.0
better > worse
zero_nonadditive_groups < 6
force-additive parity remains equal to LTM
phase5p5_allowed = false
phase6_allowed = false
```

A minimal positive result such as:

```text
better/equal/worse = 2 / 16 / 0
mean delta ratio < 0
```

would be more valuable than another parity-only guard.

---

## 5. Required P0 Work

## P0-A. Add full runtime feature logging before changing the selector

The Case-B OOD report warns that current OOD values are proxy diagnostics because the update log did not include full runtime feature vectors.

Add to every LAUR update log row:

```text
runtime_feature_names
runtime_feature_values
feature_max_abs_z
feature_mean_abs_z
feature_outside_3sigma_count
feature_outside_5sigma_count
ood_guard_triggered
ood_z_threshold
selected_rule_before_guard
selected_rule_after_guard
selected_rule_source
```

Do not change solver behavior for this subtask. This is instrumentation only.

Create/update:

```text
cpp/ntm/laur_ltm_runtime.cpp
cpp/ntm/laur_ltm_runtime.hpp
cpp/tools/phase1a_batch.cpp
scripts/run_phase5p5_laur_diagnostic_preflight_exec.py
```

Add tests to ensure fields exist in emitted update logs.

---

## P0-B. Re-run a short instrumentation-only preflight

Use the same small scope or a reduced smoke subset first.

Purpose:

```text
Replace proxy OOD evidence with true runtime feature OOD evidence.
Confirm whether OOD guard is firing because all runtime features are genuinely OOD
or because one poorly scaled feature dominates.
```

Write:

```text
outputs/reports/phase5p5_repair5e2_runtime_feature_ood_report.md
outputs/reports/phase5p5_repair5e2_runtime_feature_ood_summary.json
outputs/tables/phase5p5_repair5e2_runtime_feature_ood_rows.csv
```

Required analysis:

```text
per-feature max |z|
per-feature mean |z|
which feature triggers guard most often
whether entropy_edge_usage dominates all OOD decisions
OOD trigger rate by map/agents/iteration
rule selected before guard vs after guard
```

If one feature dominates due to schema/scale mismatch, fix normalization or feature mapping before training a new selector.

---

## P0-C. Implement one guarded non-additive recovery candidate

Implement exactly one targeted candidate, not a large search.

Preferred candidate:

```text
repair5e2_guarded_oracle_aligned_selector
```

Design:

```text
Use the existing Repair5D distilled runtime as base.
Keep OOD guard.
Add a conservative non-additive allowlist / rerank layer based on closed-loop oracle/static support rows.
Only allow non-additive choices when:
  - runtime feature vector is in-distribution enough,
  - predicted rule is not commit_heavy collapse by default,
  - the chosen rule is supported by oracle/static evidence for similar map/agent/update context,
  - additive/defer remains fallback.
```

This candidate may be implemented either as:

```text
Option 1: a small single-network selector with rule score + safety/guard metadata, still outputting the same 8 preset rules;
Option 2: a deterministic diagnostic reranker over the existing 8 rules using oracle/static support and true OOD metrics.
```

Do not implement bounded ΔUpdateParams yet.
Do not add richer LTM representation yet.
Do not change solver semantics.

Create:

```text
scripts/create_repair5e2_guarded_selector_runtime.py
artifacts/models/laur_ltm/repair5e2_guarded_oracle_aligned_selector/
outputs/reports/phase5p5_repair5e2_guarded_selector_report.md
outputs/reports/phase5p5_repair5e2_guarded_selector_summary.json
```

The report must explicitly state:

```text
diagnostic-only = true
phase5p5_allowed = false
phase6_allowed = false
solver_semantic_changes = false
output_space = existing_8_rules_plus_additive_defer
```

---

## P0-D. Rerun the same Case-B preflight

Scope:

```text
maps:
  random-32-32-20
  maze-32-32-4
  warehouse-10-20-10-2-1

agents:
  50
  100

instances_per_setting:
  3

time_limit_sec:
  3.0

ltm_max_iterations:
  4
```

Methods:

```text
lacam_star
lacam_star_ltm
always_additive_defer
repair3_safe_runtime
repair5d_composite_diagnostic_distilled
repair5e_caseb_ood_guard_distilled
repair5e2_guarded_oracle_aligned_selector
repair5e2_guarded_oracle_aligned_selector_force_additive_parity
oracle_teacher_forced_best_safe_update_static_proxy
```

Write:

```text
outputs/reports/phase5p5_repair5e2_preflight_report.md
outputs/reports/phase5p5_repair5e2_preflight_summary.json
outputs/tables/phase5p5_repair5e2_preflight_summary.csv
outputs/tables/phase5p5_repair5e2_preflight_paired.csv
outputs/logs/phase5p5_repair5e2_preflight/*.jsonl
```

---

## 6. Decision Table After Repair5E.2

### Case A: Guarded selector beats LTM and oracle remains positive

Proceed to:

```text
multi-seed component validation
true single-network neural composite selector
formal Phase5.5 runtime export design
```

Still do not claim Phase5.5 until larger closed-loop validation passes.

### Case B: Guarded selector equals LTM but has zero non-additive choices

Interpretation:

```text
Safety is solved, but learned improvement is still blocked.
```

Next:

```text
train a true neural composite selector with ranking + safety + utility heads
or add a closed-loop-labeled reranker.
```

### Case C: Guarded selector uses non-additive choices but still loses

Interpretation:

```text
Rule selection is still misaligned with closed-loop metrics.
```

Next:

```text
stop using offline top1 labels as primary target
use closed-loop oracle/static rows as the target for reranking
```

### Case D: Oracle/static proxy remains positive but no learned 8-rule selector can recover it

Only then open the reserved design discussion:

```text
Repair5F bounded ΔUpdateParams
richer LTM representation
```

Do not implement those in Repair5E.2.

---

## 7. Codex Prompt

```text
Continue czr004 on branch phase4f5p5-stable-attention-lau after commit b16f87bfdc6ee5e9458f7912536678adc690c678.

Goal:
  Repair5E.2 guarded non-additive recovery.
  Stay on the simple LAUR idea: learned UpdateLTM should exceed plain additive LTM.
  Do not predict agent actions, replace PIBT/LaCAM*, change candidate generation/pruning/conflict semantics, add learned restart, lower gates, or claim Phase5.5/Phase6.
  Do not implement bounded ΔUpdateParams in this step.
  Do not make richer LTM representation the main branch in this step.

Current evidence:
  - Repair5E.1 OOD guard result:
      repair5e_caseb_ood_guard_distilled better/equal/worse = 0/18/0
      mean delta ratio vs LTM = 0.0
      ratio_worse_than_ltm_groups = 0
      success_worse_than_ltm_groups = 0
      zero_nonadditive_groups = 6
  - Old Repair5D distilled result:
      better/equal/worse = 1/12/5
      mean delta ratio vs LTM = +0.0025935989466666395
      ratio_worse_than_ltm_groups = 2
  - Oracle/static proxy remains positive:
      better/equal/worse = 8/9/1
      mean delta ratio vs LTM = -0.010131897741666685
  - Current decision table is still Case B:
      oracle_positive = true
      repair5d_positive = false
      phase5p5_allowed = false
      phase6_allowed = false
      recommended_action = improve_composite_or_reranker_do_not_jump_to_delta_updateparams
  - Case-B analysis found Repair5D closed-loop commit_heavy collapse:
      Repair5D closed-loop distribution = {'commit_heavy': 43, 'wait_light': 2}
      oracle/static distribution = {'block_heavy': 7, 'block_light': 12, 'commit_heavy': 1, 'decay_090': 5, 'wait_heavy': 4, 'wait_light': 16}
      commit_heavy share = 0.9555555555555556
  - The OOD analysis was proxy-based because the update log did not include full runtime feature vectors.

Tasks:
  1. Add full runtime feature logging to every LAUR update log row:
       runtime_feature_names
       runtime_feature_values
       feature_max_abs_z
       feature_mean_abs_z
       feature_outside_3sigma_count
       feature_outside_5sigma_count
       ood_guard_triggered
       ood_z_threshold
       selected_rule_before_guard
       selected_rule_after_guard
       selected_rule_source
     This task is instrumentation only; do not change solver behavior.

  2. Re-run a small instrumentation preflight and write:
       outputs/reports/phase5p5_repair5e2_runtime_feature_ood_report.md
       outputs/reports/phase5p5_repair5e2_runtime_feature_ood_summary.json
       outputs/tables/phase5p5_repair5e2_runtime_feature_ood_rows.csv
     Required analysis:
       per-feature max |z|
       per-feature mean |z|
       OOD trigger rate by map/agents/iteration
       which feature triggers guard most often
       selected rule before guard vs after guard
       whether entropy_edge_usage or any one feature dominates due to scale/schema mismatch

  3. Implement exactly one guarded non-additive recovery candidate:
       repair5e2_guarded_oracle_aligned_selector
     It must stay in existing 8 preset UpdateLTM rules plus additive/defer fallback.
     It must keep the OOD/defer guard.
     It must prevent commit_heavy collapse.
     It should recover non-additive choices only when true runtime OOD metrics and closed-loop oracle/static evidence support them.
     Acceptable implementation:
       either a small single-network selector still outputting the same 8 rules,
       or a deterministic diagnostic reranker over existing 8 rules using oracle/static support rows and true OOD metrics.
     Do not implement bounded ΔUpdateParams.

  4. Rerun the same Case-B preflight:
       maps: random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
       agents: 50, 100
       instances_per_setting: 3
       time_limit_sec: 3.0
       ltm_max_iterations: 4
     Required methods:
       lacam_star
       lacam_star_ltm
       always_additive_defer
       repair3_safe_runtime
       repair5d_composite_diagnostic_distilled
       repair5e_caseb_ood_guard_distilled
       repair5e2_guarded_oracle_aligned_selector
       repair5e2_guarded_oracle_aligned_selector_force_additive_parity
       oracle_teacher_forced_best_safe_update_static_proxy

  5. Write:
       outputs/reports/phase5p5_repair5e2_preflight_report.md
       outputs/reports/phase5p5_repair5e2_preflight_summary.json
       outputs/tables/phase5p5_repair5e2_preflight_summary.csv
       outputs/tables/phase5p5_repair5e2_preflight_paired.csv
       outputs/logs/phase5p5_repair5e2_preflight/*.jsonl

Diagnostic pass criteria:
  - success_worse_than_ltm_groups = 0
  - ratio_worse_than_ltm_groups <= 1
  - mean_delta_ratio_vs_ltm < 0.0
  - better > worse
  - zero_nonadditive_groups < 6
  - force-additive parity remains equal to LTM
  - phase5p5_allowed = false
  - phase6_allowed = false

Verification:
  - Build C++ batch target.
  - Run: python -m pytest tests/test_repair5e_composite_preflight.py
  - Run: python -m pytest

Do not claim Phase5.5 or Phase6.
```

---

## 8. Final Position

Repair5E.1 made the candidate safe but too conservative.

The next step is not to abandon the simple idea. The next step is:

```text
Recover a small number of safe, oracle-supported non-additive UpdateLTM choices
under the OOD guard, and show they beat plain additive LTM in closed-loop preflight.
```

Only if this fails after true runtime-feature diagnostics should we formally open:

```text
richer LTM representation
bounded ΔUpdateParams
```

Those are reserved Repair5F directions, not the next Repair5E.2 move.
