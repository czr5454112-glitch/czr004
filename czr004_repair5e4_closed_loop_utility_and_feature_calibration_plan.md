# czr004 Repair5E.4 Plan: Closed-Loop Utility Labels + Runtime Feature Calibration

**Branch:** `phase4f5p5-stable-attention-lau`  
**Start after commit:** `48b5c6da438376f99c207a1deebc0d3dd0efdc1a`  
**Latest known commit message:** `Implement Repair5E.3 validation and split selector`  
**Main project objective:** use learned / data-driven `UpdateLTM` to replace the rough additive LTM update in the LTM paper and exceed `LaCAM*+LTM`, without changing solver semantics.

This phase stays on the main Repair5 line. It does **not** switch to action prediction, PIBT replacement, LaCAM* replacement, candidate-generation changes, learned restart, lower gates, richer LTM representation as the main branch, or bounded delta `UpdateParams`.

---

## 0. State After Repair5E.3

Repair5E.3 was a useful negative result.

### 0.1 Frozen E2 did not generalize

Held-out frozen E2 validation:

```text
repair5e2_guarded_oracle_aligned_selector:
  better / equal / worse = 7 / 40 / 13
  mean_delta_ratio_vs_ltm = +0.0024377673388333372
  ratio_worse_than_ltm_groups = 3
  success_worse_than_ltm_groups = 0
  zero_nonadditive_groups = 3

repair5e2_guarded_oracle_aligned_selector_force_additive_parity:
  better / equal / worse = 0 / 60 / 0
  mean_delta_ratio_vs_ltm = 0.0
```

Interpretation:

```text
E2 same-scope oracle-support recovery was overfit / too context-specific.
The positive 6/12/0 result from E2 was real inside its scope, but not robust enough for held-out promotion.
```

### 0.2 E3 split selector was safe but collapsed to additive parity

Final E3 preflight:

```text
repair5e3_split_guarded_selector:
  better / equal / worse = 0 / 60 / 0
  mean_delta_ratio_vs_ltm = 0.0
  zero_nonadditive_groups = 6

repair5e3_split_guarded_selector_force_additive_parity:
  better / equal / worse = 0 / 60 / 0
  mean_delta_ratio_vs_ltm = 0.0
```

Interpretation:

```text
E3 preserved safety, but it did not learn or recover useful non-additive updates.
It is equivalent to additive LTM under the guard.
```

### 0.3 Oracle/static proxy still has strong positive headroom

Final E3 preflight oracle/static proxy:

```text
oracle_teacher_forced_best_safe_update_static_proxy:
  better / equal / worse = 30 / 27 / 3
  mean_delta_ratio_vs_ltm = -0.013133598120000001
```

Interpretation:

```text
Repair5 is not dead.
The existing preset UpdateLTM rule space still contains positive choices.
The failure is in selecting / learning / calibrating those choices, not in the LAUR UpdateLTM idea itself.
```

### 0.4 Leakage audit is good, but it confirms the weakness

Leakage audit:

```text
leakage_detected = False
support/eval instance overlap count = 0
support generated after eval logs = False
exact map/agent recovery table used = True
```

The last line matters. E2/E3 recovery was still essentially an exact map/agent-context support table, not a learned utility model.

### 0.5 Major new diagnosis: OOD feature stats are still not trustworthy

E3 split selector manifest says train OOD stats were derived from train-support update logs, but the generated stats show these runtime features with fallback-like `mean=0, std=1`:

```text
committed_count
blocked_count
wait_event_count
goal_wait_ignored_count
blocked_per_committed
wait_per_committed
blocked_per_agent
committed_per_agent
nonzero_edges_before
max_raw_before
entropy_edge_usage
weight_entropy
```

Then the runtime OOD report shows extreme z-scores:

```text
committed_count max |z| = 126300.0
committed_count mean |z| = 8750.335570469799
goal_wait_ignored_count max |z| = 117237.0
nonzero_edges_before max |z| = 6162.0
```

and all learned choices are guarded away:

```text
commit_heavy -> additive_ltm by ood_guard: 146
wait_light -> additive_ltm by ood_guard: 3
```

Interpretation:

```text
The train-support logs used for E3 were not feature-schema-compatible with current runtime logs.
The OOD guard is doing its safety job, but it is also masking the selector because its statistics are miscalibrated.
```

This makes E3 a valid negative result for E2/E3, but not a proof that the 8-rule LAUR space is exhausted.

---

## 1. Repair5E.4 Objective

Call the next phase:

```text
Repair5E.4: Closed-Loop Utility Labels + Runtime Feature Calibration
```

Primary question:

```text
Can a selector trained from same-schema closed-loop rule-utility evidence recover the oracle/static headroom under a calibrated guard, while keeping additive fallback safety?
```

This phase should not merely add another exact recovery table. The next candidate must be trained or reranked from a **wide closed-loop utility table** and must use runtime-feature stats generated from the same instrumentation schema as the eval runtime.

---

## 2. What Not To Do Next

Do **not** jump to Repair5F yet.

Reserved for later, not this step:

```text
bounded delta UpdateParams
richer LTM representation
new solver semantics
agent action prediction
learned restart
candidate/pruning/gate changes
```

Reason:

```text
Oracle/static proxy is still positive on held-out E3.
E3 did not test a properly calibrated closed-loop utility selector; it tested a sparse exact support table plus mismatched OOD stats.
```

---

## 3. Required P0 Work

## P0-A. Fix provenance reporting first

Reports generated during E3 still recorded `git commit: c609bb8` and dirty state even though E3 was later committed as `48b5c6d`. E4 reports must record the actual current head at run time.

Add / fix:

```text
git_head_sha
git_branch
git_status_short
tracked_dirty_files_count
untracked_files_count
runtime_manifest_sha256
script_sha256 for report-generation scripts
runtime_artifact_dir
train_support_log_paths
eval_log_paths
forbidden_eval_support_paths
```

Required behavior:

```text
If tracked dirty files are present, report them explicitly.
If untracked files are present, count them but do not fail unless they are consumed as inputs.
Never claim clean provenance unless tracked worktree is clean.
```

Write:

```text
outputs/reports/phase5p5_repair5e4_provenance_audit_report.md
outputs/reports/phase5p5_repair5e4_provenance_audit_summary.json
```

---

## P0-B. Regenerate train-support logs with current full runtime feature schema

Do not reuse old `phase5p5_repair5e_caseb_preflight` logs for feature stats. They predate the current full runtime feature logging and produced fallback-like 0/1 stats for key runtime counters.

Create a fresh E4 train-support run:

```text
outputs/logs/phase5p5_repair5e4_train_support/
outputs/reports/phase5p5_repair5e4_train_support_report.md
outputs/reports/phase5p5_repair5e4_train_support_summary.json
```

Suggested train scope:

```text
maps:
  random-32-32-20
  maze-32-32-4
  warehouse-10-20-10-2-1
agents:
  50
  100
train_instance_ids:
  1..20
ltm_max_iterations:
  4
time_limit_sec:
  3.0
```

If runtime is too slow, use a smaller smoke first, but final E4 should have at least 10 train instances per map/agent group.

Required methods for support generation:

```text
lacam_star_ltm
always_additive_defer
oracle_probe_static_block_heavy
oracle_probe_static_block_light
oracle_probe_static_commit_heavy
oracle_probe_static_decay_090
oracle_probe_static_decay_095
oracle_probe_static_wait_heavy
oracle_probe_static_wait_light
```

The train support logs must include, for every LAUR update row:

```text
runtime_feature_names
runtime_feature_values
selected_rule_before_guard
selected_rule_after_guard
selected_rule_source
feature_max_abs_z
feature_mean_abs_z
feature_outside_3sigma_count
feature_outside_5sigma_count
ood_guard_triggered
```

---

## P0-C. Build a wide closed-loop rule-utility table

Create:

```text
scripts/create_repair5e4_closed_loop_utility_table.py
```

Inputs:

```text
outputs/logs/phase5p5_repair5e4_train_support/*.jsonl
outputs/logs/phase5p5_repair5e4_train_support/*_laur_updates.jsonl
```

Output:

```text
outputs/tables/phase5p5_repair5e4_closed_loop_rule_utility_train.csv
outputs/reports/phase5p5_repair5e4_closed_loop_rule_utility_report.md
outputs/reports/phase5p5_repair5e4_closed_loop_rule_utility_summary.json
```

The table should join candidate-rule outcomes by:

```text
map
agents
instance_id
iteration
update_index if available
feature vector hash / command context hash if available
```

For each context, include utility columns for every candidate rule:

```text
additive_ltm
block_heavy
block_light
commit_heavy
decay_090
decay_095
wait_heavy
wait_light
```

For each rule, compute at least:

```text
success_delta_vs_ltm
ratio_delta_vs_ltm
expanded_delta_vs_ltm
pibt_delta_vs_ltm
ttfs_delta_vs_ltm
non_additive_flag
safe_nonregression_flag
positive_utility_flag
```

Recommended label rule:

```text
A non-additive rule is positive only if:
  success_delta_vs_ltm >= 0
  ratio_delta_vs_ltm < -epsilon_ratio
  ratio is not worse on the group-level aggregation
  harmful rule cap does not trigger
  the rule has support across multiple instances or enough nearest-neighbor support
Otherwise label additive_ltm/defer.
```

Use a small epsilon initially:

```text
epsilon_ratio = 0.0005 or 0.001
```

Also produce label diagnostics:

```text
positive non-additive contexts per map/agent
rule distribution among positive labels
commit_heavy positive share
support per rule
support per instance
oracle label entropy
cases where oracle positive but every fixed rule is group-neutral
```

---

## P0-D. Fix runtime-feature/OOD calibration

Create:

```text
scripts/create_repair5e4_runtime_feature_stats_from_train_support.py
scripts/audit_repair5e4_runtime_feature_stats.py
```

Outputs:

```text
artifacts/models/laur_ltm/repair5e4_closed_loop_utility_selector/ood_feature_stats_train.csv
outputs/reports/phase5p5_repair5e4_runtime_feature_stats_report.md
outputs/reports/phase5p5_repair5e4_runtime_feature_stats_summary.json
```

Required checks:

```text
No important runtime counter may silently default to mean=0,std=1 unless it is genuinely constant in train logs.
Flag these as invalid if they default without evidence:
  committed_count
  blocked_count
  wait_event_count
  goal_wait_ignored_count
  blocked_per_committed
  wait_per_committed
  blocked_per_agent
  committed_per_agent
  nonzero_edges_before
  max_raw_before
  entropy_edge_usage
  weight_entropy
```

Use robust stats in addition to mean/std:

```text
median
mad
p01
p05
p95
p99
min
max
rows_non_missing
rows_nonzero
```

Guard logic should become calibrated, not simply looser:

```text
- Missing required feature => defer/additive.
- Invalid feature stats => fail artifact creation; do not run as learned selector.
- Out-of-distribution only if multiple calibrated features are outside robust thresholds, or if a feature exceeds an extreme percentile bound.
- Record trigger feature and trigger reason.
```

Add an explicit report section comparing E3 and E4 OOD:

```text
E3 committed_count max |z|
E4 committed_count max |z|
E3 top trigger concentration
E4 top trigger concentration
before_guard -> after_guard transition counts
```

Pass condition for this subtask:

```text
feature_stats_valid = true
top_ood_trigger_share < 0.8, or report explains why the top trigger is physically valid
no feature with max_abs_z > 1000 unless explicitly justified
learned choices are not all blocked by OOD guard in train smoke
```

---

## P0-E. Implement one E4 selector candidate

Candidate name:

```text
repair5e4_closed_loop_utility_selector
```

Runtime artifact:

```text
artifacts/models/laur_ltm/repair5e4_closed_loop_utility_selector/
```

Create script:

```text
scripts/create_repair5e4_closed_loop_utility_selector_runtime.py
```

Allowed implementation options:

```text
Option 1: deterministic feature-space reranker / nearest-neighbor utility selector.
Option 2: small neural selector with rule-utility and safety heads, still exported through current LAUR runtime constraints.
```

Both options must obey:

```text
Output space = existing 8 preset UpdateLTM rules plus additive/defer fallback.
No bounded delta UpdateParams.
No richer LTM representation.
No solver semantic changes.
No eval logs while creating the runtime artifact.
Additive/defer fallback remains available.
commit_heavy is capped or excluded unless train utility evidence is strong and replicated.
```

Minimum selector behavior:

```text
1. Compute runtime features.
2. Apply calibrated feature/OOD audit.
3. Score candidate rules by closed-loop utility evidence.
4. Select non-additive only if predicted margin over additive exceeds threshold.
5. Otherwise select additive_ltm.
6. Log selected_rule_before_guard, selected_rule_after_guard, selected_rule_source, predicted_margin, nearest_support_count, and guard reason.
```

Recommended conservative thresholds:

```text
min_support_neighbors = 5
min_positive_instances = 2
min_predicted_margin_ratio = 0.001
max_commit_heavy_share = 0.2 in any group unless oracle utility proves otherwise
```

Write:

```text
outputs/reports/phase5p5_repair5e4_selector_artifact_report.md
outputs/reports/phase5p5_repair5e4_selector_artifact_summary.json
```

The manifest must include:

```text
diagnostic_only = true
phase5p5_allowed = false
phase6_allowed = false
solver_semantic_changes = false
output_space = existing_8_rules_plus_additive_defer
train_instance_ids
eval_instance_ids_forbidden
train_support_paths
eval_log_paths = []
closed_loop_utility_table_sha256
feature_stats_sha256
source_runtime_hashes
```

---

## P0-F. Run ablations before final validation

Run a controlled ablation set:

```text
repair5e4_calibrated_guard_only_on_e3_split
repair5e4_closed_loop_utility_selector
repair5e4_closed_loop_utility_selector_force_additive_parity
repair5e4_closed_loop_utility_selector_recovery_disabled_parity
repair5e4_closed_loop_utility_selector_no_ood_guard_diagnostic
repair5e4_closed_loop_utility_selector_shuffled_labels_diagnostic
```

Purpose:

```text
- calibrated_guard_only_on_e3_split checks whether E3 failed mainly due to OOD calibration.
- force_additive / recovery_disabled verify parity.
- no_ood_guard is diagnostic only; it must not be promoted.
- shuffled_labels ensures the learned/reranked utility labels carry real signal.
```

Write:

```text
outputs/reports/phase5p5_repair5e4_ablation_report.md
outputs/reports/phase5p5_repair5e4_ablation_summary.json
outputs/tables/phase5p5_repair5e4_ablation_paired.csv
```

---

## P0-G. Final E4 held-out preflight

Use held-out eval instances not used in train support generation.

Suggested eval scope:

```text
maps:
  random-32-32-20
  maze-32-32-4
  warehouse-10-20-10-2-1
agents:
  50
  100
eval_instance_ids:
  21..40 if train used 1..20
  otherwise pick a disjoint range and record it
instances_per_setting:
  at least 10, preferably 20 if runtime allows
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
repair5d_composite_diagnostic_distilled
repair5e_caseb_ood_guard_distilled
repair5e3_split_guarded_selector
repair5e4_closed_loop_utility_selector
repair5e4_closed_loop_utility_selector_force_additive_parity
oracle_teacher_forced_best_safe_update_static_proxy
```

Write:

```text
outputs/reports/phase5p5_repair5e4_preflight_report.md
outputs/reports/phase5p5_repair5e4_preflight_summary.json
outputs/tables/phase5p5_repair5e4_preflight_summary.csv
outputs/tables/phase5p5_repair5e4_preflight_paired.csv
outputs/logs/phase5p5_repair5e4_preflight/*.jsonl
```

---

## 4. E4 Diagnostic Success Criteria

E4 succeeds diagnostically if:

```text
success_worse_than_ltm_groups = 0
ratio_worse_than_ltm_groups <= 1
mean_delta_ratio_vs_ltm < 0.0
better > worse
zero_nonadditive_groups < total_groups
force-additive parity remains exact LTM parity
recovery-disabled parity remains exact LTM parity
no support/eval leakage detected
feature_stats_valid = true
learned choices are not all OOD-blocked
phase5p5_allowed = false
phase6_allowed = false
```

A strong E4 result would look like:

```text
repair5e4_closed_loop_utility_selector:
  better / equal / worse >= 10 / ? / <= 5 on 60+ rows
  mean_delta_ratio_vs_ltm < -0.003
  ratio_worse_than_ltm_groups <= 1
```

A minimal useful E4 result would be:

```text
better > worse
mean_delta_ratio_vs_ltm < 0.0
success_worse_than_ltm_groups = 0
non_additive_update_rate > 0 in at least 2 groups
```

---

## 5. Decision Table After E4

### Case A: E4 selector positive under clean held-out eval

Proceed to:

```text
larger multi-map / multi-agent validation
multi-seed stability
formal Phase5.5 runtime-export design
```

Still do not claim Phase5.5 until larger validation passes.

### Case B: E4 still additive parity because guard blocks all learned choices

Interpretation:

```text
Feature/OOD calibration or selector confidence is still too conservative.
```

Next:

```text
separate OOD schema guard from selector uncertainty
train calibrated abstention head
increase train-support coverage
```

### Case C: E4 uses non-additive choices but loses

Interpretation:

```text
Closed-loop label definition or feature representation is still misaligned.
```

Next:

```text
inspect per-rule utility margins
remove unstable rules
train utility-rank objective instead of top1 labels
```

### Case D: Oracle/static proxy remains positive but E4 cannot learn it even with valid stats and wide utility labels

Only then open Repair5F discussion:

```text
bounded delta UpdateParams
richer LTM representation
```

Even then, keep the main project constraint: learned `UpdateLTM`, not solver replacement.

---

## 6. Codex Prompt

```text
Continue czr004 on branch phase4f5p5-stable-attention-lau after commit 48b5c6da438376f99c207a1deebc0d3dd0efdc1a.

Goal:
  Implement Repair5E.4: closed-loop utility labels plus runtime feature/OOD calibration for LAUR UpdateLTM.

Main objective:
  Replace plain additive LTM updates with a learned/data-driven UpdateLTM selector that exceeds LaCAM*+LTM.
  Stay on the Repair5 LAUR/UpdateLTM main line.
  Do not predict agent actions, replace PIBT/LaCAM*, change candidate generation/pruning/conflict semantics, add learned restart, lower gates, implement bounded delta UpdateParams, or introduce richer LTM representation as the main branch.
  Do not claim Phase5.5 or Phase6.

Current evidence after Repair5E.3:
  - Frozen E2 held-out failed:
      repair5e2_guarded_oracle_aligned_selector = 7 better / 40 equal / 13 worse
      mean_delta_ratio_vs_ltm = +0.0024377673388333372
      ratio_worse_than_ltm_groups = 3
      success_worse_than_ltm_groups = 0
      zero_nonadditive_groups = 3
  - E2 force-additive parity was exact:
      0 / 60 / 0, mean 0.0
  - Final E3 split selector collapsed to additive parity:
      repair5e3_split_guarded_selector = 0 / 60 / 0, mean 0.0
      zero_nonadditive_groups = 6
  - Oracle/static proxy remains strongly positive:
      30 better / 27 equal / 3 worse
      mean_delta_ratio_vs_ltm = -0.013133598120000001
  - Leakage audit found no support/eval leakage, but exact map/agent recovery table was still used.
  - E3 train-derived OOD stats are invalid/mismatched for important runtime counters:
      committed_count, blocked_count, wait_event_count, goal_wait_ignored_count,
      blocked_per_committed, wait_per_committed, blocked_per_agent,
      committed_per_agent, nonzero_edges_before, max_raw_before,
      entropy_edge_usage, weight_entropy all had fallback-like mean=0,std=1 in the stats CSV.
    Runtime OOD then showed huge z-scores and guarded all learned choices:
      committed_count max |z| = 126300.0
      goal_wait_ignored_count max |z| = 117237.0
      commit_heavy -> additive_ltm by ood_guard = 146
      wait_light -> additive_ltm by ood_guard = 3

Tasks:
  1. Fix provenance reporting for E4 outputs.
     Reports must record actual git_head_sha, git_branch, git_status_short, tracked dirty count, untracked count, runtime manifest hashes, script hashes, train support paths, eval paths, and forbidden eval support paths.
     Write:
       outputs/reports/phase5p5_repair5e4_provenance_audit_report.md
       outputs/reports/phase5p5_repair5e4_provenance_audit_summary.json

  2. Regenerate train-support logs with the current full runtime feature schema.
     Do not reuse old phase5p5_repair5e_caseb_preflight logs for feature stats.
     Suggested train scope:
       maps: random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
       agents: 50, 100
       train_instance_ids: 1..20 if feasible, at least 1..10 for final if runtime constrained
       time_limit_sec: 3.0
       ltm_max_iterations: 4
     Include oracle probe support methods for all existing preset rules:
       oracle_probe_static_block_heavy
       oracle_probe_static_block_light
       oracle_probe_static_commit_heavy
       oracle_probe_static_decay_090
       oracle_probe_static_decay_095
       oracle_probe_static_wait_heavy
       oracle_probe_static_wait_light
     Write:
       outputs/logs/phase5p5_repair5e4_train_support/*.jsonl
       outputs/reports/phase5p5_repair5e4_train_support_report.md
       outputs/reports/phase5p5_repair5e4_train_support_summary.json

  3. Create a wide closed-loop rule-utility table.
     Implement:
       scripts/create_repair5e4_closed_loop_utility_table.py
     Output:
       outputs/tables/phase5p5_repair5e4_closed_loop_rule_utility_train.csv
       outputs/reports/phase5p5_repair5e4_closed_loop_rule_utility_report.md
       outputs/reports/phase5p5_repair5e4_closed_loop_rule_utility_summary.json
     Join candidate-rule outcomes by map, agents, instance_id, iteration, update index or feature/context hash.
     Compute per-rule utility vs LTM/additive for success, ratio, expanded, PIBT, and TTFS.
     Label a non-additive rule positive only if it is safe and has closed-loop utility margin over additive.

  4. Fix runtime-feature/OOD stats.
     Implement:
       scripts/create_repair5e4_runtime_feature_stats_from_train_support.py
       scripts/audit_repair5e4_runtime_feature_stats.py
     Important runtime counters must not silently default to mean=0,std=1 unless genuinely constant.
     Add robust stats: median, MAD, p01, p05, p95, p99, min, max, rows_non_missing, rows_nonzero.
     Artifact creation must fail if feature stats are invalid.
     Write:
       outputs/reports/phase5p5_repair5e4_runtime_feature_stats_report.md
       outputs/reports/phase5p5_repair5e4_runtime_feature_stats_summary.json

  5. Implement one E4 selector candidate:
       repair5e4_closed_loop_utility_selector
     Runtime dir:
       artifacts/models/laur_ltm/repair5e4_closed_loop_utility_selector/
     Implement:
       scripts/create_repair5e4_closed_loop_utility_selector_runtime.py
     Allowed implementation:
       deterministic feature-space reranker / nearest-neighbor utility selector, or small neural utility/safety selector.
     Requirements:
       output space remains existing 8 preset UpdateLTM rules plus additive/defer fallback;
       keep calibrated OOD/defer guard;
       no bounded delta UpdateParams;
       no richer LTM representation;
       no solver semantic changes;
       no eval logs used to create runtime artifact;
       commit_heavy excluded or capped unless utility evidence is strong and replicated;
       log predicted margin, support count, selected_rule_before_guard, selected_rule_after_guard, selected_rule_source, and guard reason.
     Write:
       outputs/reports/phase5p5_repair5e4_selector_artifact_report.md
       outputs/reports/phase5p5_repair5e4_selector_artifact_summary.json

  6. Run E4 ablations:
       repair5e4_calibrated_guard_only_on_e3_split
       repair5e4_closed_loop_utility_selector
       repair5e4_closed_loop_utility_selector_force_additive_parity
       repair5e4_closed_loop_utility_selector_recovery_disabled_parity
       repair5e4_closed_loop_utility_selector_no_ood_guard_diagnostic
       repair5e4_closed_loop_utility_selector_shuffled_labels_diagnostic
     Write:
       outputs/reports/phase5p5_repair5e4_ablation_report.md
       outputs/reports/phase5p5_repair5e4_ablation_summary.json
       outputs/tables/phase5p5_repair5e4_ablation_paired.csv

  7. Run final E4 held-out preflight.
     Suggested eval scope:
       maps: random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
       agents: 50, 100
       eval_instance_ids: 21..40 if train used 1..20; otherwise choose a disjoint range and record it
       instances_per_setting: at least 10
       time_limit_sec: 3.0
       ltm_max_iterations: 4
     Methods:
       lacam_star
       lacam_star_ltm
       always_additive_defer
       repair5d_composite_diagnostic_distilled
       repair5e_caseb_ood_guard_distilled
       repair5e3_split_guarded_selector
       repair5e4_closed_loop_utility_selector
       repair5e4_closed_loop_utility_selector_force_additive_parity
       oracle_teacher_forced_best_safe_update_static_proxy
     Write:
       outputs/reports/phase5p5_repair5e4_preflight_report.md
       outputs/reports/phase5p5_repair5e4_preflight_summary.json
       outputs/tables/phase5p5_repair5e4_preflight_summary.csv
       outputs/tables/phase5p5_repair5e4_preflight_paired.csv
       outputs/logs/phase5p5_repair5e4_preflight/*.jsonl

Diagnostic pass criteria:
  - success_worse_than_ltm_groups = 0
  - ratio_worse_than_ltm_groups <= 1
  - mean_delta_ratio_vs_ltm < 0.0
  - better > worse
  - zero_nonadditive_groups < total_groups
  - force-additive parity remains exact LTM parity
  - recovery-disabled parity remains exact LTM parity
  - no support/eval leakage detected
  - feature_stats_valid = true
  - learned choices are not all OOD-blocked
  - phase5p5_allowed = false
  - phase6_allowed = false

Verification:
  - scripts/build_phase1a_batch.ps1
  - python -m pytest tests/test_repair5e_composite_preflight.py
  - python -m pytest

Commit only Repair5E.4 scoped changes. Leave unrelated dirty/untracked work untouched.
```

---

## 7. Final Position

Repair5E.3 did **not** pass promotion, but it did not kill Repair5.

The correct next move is not to abandon LAUR or jump to bounded delta updates. The correct next move is:

```text
Regenerate same-schema train support,
learn/rerank from closed-loop rule utility,
fix OOD calibration,
and validate on held-out instances.
```

Only if Repair5E.4 fails under valid feature stats and a real wide utility table should the project open Repair5F.

---

## 8. Execution Closure: Repair5E.4

Completed on 2026-06-01 on branch `phase4f5p5-stable-attention-lau`, starting from `48b5c6da438376f99c207a1deebc0d3dd0efdc1a`.

Implemented and generated:

```text
scripts/create_repair5e4_closed_loop_utility_table.py
scripts/create_repair5e4_runtime_feature_stats_from_train_support.py
scripts/audit_repair5e4_runtime_feature_stats.py
scripts/create_repair5e4_closed_loop_utility_selector_runtime.py
scripts/audit_repair5e4_provenance.py
artifacts/models/laur_ltm/repair5e4_closed_loop_utility_selector/
outputs/reports/phase5p5_repair5e4_*
outputs/tables/phase5p5_repair5e4_*
outputs/logs/phase5p5_repair5e4_train_support/
outputs/logs/phase5p5_repair5e4_preflight/
```

Train support used disjoint instance IDs `1..10` for each map/agent group. Final held-out preflight used instance IDs `11..20` because this local checkout only had scenarios through `25`; this still preserves train/eval disjointness and 10 held-out instances per map/agent group.

Key measured outputs:

```text
closed_loop_utility_train:
  contexts = 210
  positive_nonadditive_contexts = 24
  positive groups = random-32-32-20:50 and random-32-32-20:100

runtime_feature_stats:
  feature_stats_valid = true
  pass_condition = true
  E3 committed_count max |z| = 126300.0
  E4 committed_count max |z| = 8.191661429636884 on final preflight updates
  learned_choices_all_blocked_by_ood = false

final_preflight repair5e4_closed_loop_utility_selector:
  better / equal / worse = 3 / 53 / 4
  mean_delta_ratio_vs_ltm = -0.0008248539980000043
  ratio_worse_than_ltm_groups = 1
  success_worse_than_ltm_groups = 0
  zero_nonadditive_groups = 4

final_preflight repair5e4_closed_loop_utility_selector_force_additive_parity:
  better / equal / worse = 0 / 60 / 0
  mean_delta_ratio_vs_ltm = 0.0

oracle_teacher_forced_best_safe_update_static_proxy:
  better / equal / worse = 29 / 28 / 3
  mean_delta_ratio_vs_ltm = -0.014011226436383337

leakage/provenance:
  leakage_detected = false
  support_eval_instance_overlap_count = 0
  support_generated_after_eval_logs = false
  diagnostic_only = true
  phase5p5_allowed = false
  phase6_allowed = false
```

Decision:

```text
Repair5E.4 completed as a valid negative / weak-signal result.
It fixed the OOD feature calibration problem and recovered non-additive selector activity,
but it did not satisfy diagnostic success because better <= worse on held-out validation.
Do not promote to Phase5.5 or Phase6.
Next work should inspect utility-label margins, remove unstable rules or maps from the candidate,
and consider a utility-rank or calibrated abstention objective before opening Repair5F.
```
