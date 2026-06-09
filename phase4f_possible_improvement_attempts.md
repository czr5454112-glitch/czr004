# Phase4F Possible Improvement Attempts for LAU-LTM

Date: 2026-05-26  
Target branch: `phase4-laur-ltm`  
Latest remote evidence mentioned by user: `380dbe6 results: add Phase4 LAUR full evidence`  
Do not change direction. Do not lower standards. Do not enter Phase5 learned runtime until Phase4F performance gates pass.

---

## 0. Purpose

This document is a Codex-executable repair plan for the current Phase4F LAU/LAUR-LTM result.

The project direction remains:

```text
LaCAM* + LTM
  -> learned adaptive LTM update rule
  -> LAU-LTM / LAUR-LTM
```

Do **not** switch to CBR, do **not** switch to pure edge-weight regression, do **not** introduce unrelated MAPF solvers, and do **not** reduce the performance gates merely to declare success.

The goal is still:

```text
learned update must become strong enough to justify Phase5 solver integration
and ultimately beat ordinary additive LTM in closed-loop solver metrics.
```

Current conclusion from the full Phase4F run:

```text
Operational pipeline: pass
Performance gate: fail
Phase5 learned runtime: blocked
Next step: Phase4F repair and rerun
```

---

## 1. Current GitHub / code-state facts to verify before work

Codex must begin by verifying the current repository state.

```bash
git status --short
git branch --show-current
git rev-parse --short HEAD
git log --oneline -5
```

Expected branch:

```text
phase4-laur-ltm
```

Known local caveat from user:

```text
Untracked 1.txt may exist. Do not touch it.
```

Important current artifacts and reports:

```text
outputs/reports/phase4_laur_ltm_full_result_analysis.md
outputs/reports/phase4_laur_ltm_full_batch_report.md
outputs/reports/phase4_laur_ltm_full_batch_summary.json
outputs/reports/phase4_laur_ltm_offline_eval_full_summary.json
outputs/reports/phase4_laur_ltm_train_full.md
configs/phase4/laur_ltm_full.yaml
src/models/laur_ltm.py
src/train/train_laur_ltm.py
src/train/losses_laur.py
src/eval/eval_laur_offline.py
src/czr004_teacher/features_laur.py
src/czr004_teacher/update_sequences.py
```

Current full-run evidence:

```text
run_count: 480
checkpoints: 1897
probe_rows: 15360
dataset_rows: 1897
non_neutral_checkpoints: 1484
validation_non_neutral_checkpoints: 349
raw_trace_zstd_size: about 810 MB
raw_trace_sha256: c2a8deadfa8c7628fd8411b91bc369b3c1d69aa171184f278c1f1171ffd0ad47
```

Current performance failure:

```text
validation rule top1: 0.1943        threshold: 0.35   fail
validation rule top3: 0.4716        threshold: 0.70   fail
validation harmful recall: 0.5525   threshold: 0.80   fail
validation harmful precision: 0.5952 threshold: 0.30  pass
validation predicted mean delta: 0.0029 threshold: >0 pass
```

Train/validation gap:

```text
train top1: 0.7470
train top3: 0.9514
train harmful recall: 0.7454

validation top1: 0.1943
validation top3: 0.4716
validation harmful recall: 0.5525
```

Current validation maps:

```text
empty-48-48
maze-32-32-4
```

Current training maps:

```text
empty-32-32
random-32-32-20
random-64-64-20
room-64-64-8
warehouse-10-20-10-2-1
warehouse-10-20-10-2-2
```

This means the current validation is hard: `maze-32-32-4` is map-family OOD, and `empty-48-48` is size extrapolation relative to `empty-32-32`.

---

## 2. Hard constraints

Codex must obey these constraints.

### 2.1 Do not lower the Phase4F performance gates

Keep the current gates unless the user explicitly changes them:

```text
validation non-neutral checkpoints >= 50
validation rule top1 >= 0.35
validation rule top3 >= 0.70
validation harmful recall >= 0.80
validation harmful precision >= 0.30
validation predicted-rule mean delta ratio > 0
```

You may add additional diagnostics and additional stricter sub-gates.  
Do **not** reduce these thresholds to pass.

### 2.2 Do not enter Phase5 learned runtime

Until repaired Phase4F passes:

```text
Do not implement cpp/ntm learned runtime.
Do not run learned-update Phase5 solver integration.
Do not claim LAU-LTM improves LTM.
```

### 2.3 Do not change research direction

Allowed:

```text
learned update rule
rule scoring
safety-gated additive fallback
margin-aware update-rule labels
probe-label repair
feature repair
targeted LAU data expansion
```

Not allowed:

```text
switching to CBR
pure edge-weight regression as the main story
unrelated MAPF solvers
learned restart before learned update is stable
removing legal PIBT actions
changing LaCAM* high-level semantics
```

### 2.4 Preserve fallback semantics

Every repair attempt must preserve:

```text
learning off -> ordinary additive LTM
force-additive -> current Phase4B behavior
no learned runtime until gate passes
```

---

## 3. Main diagnosis

The failure is not an engineering-pipeline failure. The full chain has run:

```text
record -> probe -> dataset -> train -> eval
```

The likely causes are:

1. **Hard best-rule classification is too brittle.**  
   A checkpoint is assigned exactly one best rule, even when several rules may have near-equal probe deltas.

2. **`neutral_additive` duplicates `additive_ltm` as an executable action.**  
   Both map to the same additive fallback parameters, but the classifier is asked to distinguish them.

3. **Safety score has signal but poor recall at threshold 0.5.**  
   Validation safety AUROC is around 0.709, so calibration/thresholding and class weighting should be tried before changing direction.

4. **Validation is map-family hard.**  
   Train has no maze-family map; validation includes `maze-32-32-4`. This is useful as OOD stress, but it explains the sharp drop.

5. **Current model predicts checkpoint -> class.**  
   It does not explicitly learn `Q(checkpoint, update_rule)`, even though Phase4D generated 15,360 probe rows that contain per-rule outcomes.

6. **Some solver-context features are still smoke-style proxies.**  
   Features such as best-ratio-before, improved-last-iteration, returned-solutions-count-so-far should be audited and replaced with true running solver context if they are currently approximations.

---

## 4. Recommended priority order

Do these in order. Do not skip diagnostics.

```text
P0: Diagnostics and evidence report
P1: Additive/neutral target cleanup
P2: Safety calibration and class-weighted safety training
P3: Margin-aware labels and soft/ranking losses
P4: Rule-aware scorer model using probe rows
P5: Feature and checkpoint-context repair
P6: Split/data repair without lowering the standard
P7: Probe-label quality improvement
P8: Model capacity and regularization sweep
```

The highest-probability improvement path is:

```text
P0 -> P1 -> P2 -> P3 -> P4
```

If P4 does not pass, then do:

```text
P5 -> P6 -> P7 -> rerun P4
```

---

# P0. Diagnostics and evidence report

## Goal

Before changing training, produce a stronger failure diagnosis from the existing full artifacts.

Do not rerun full record/probe yet.

## New files

```text
src/eval/diagnose_laur_phase4f.py
outputs/reports/phase4f_laur_failure_diagnostics.md
outputs/tables/phase4f_laur_label_margin_histogram.csv
outputs/tables/phase4f_laur_per_map_confusion.csv
outputs/tables/phase4f_laur_safety_threshold_sweep.csv
outputs/tables/phase4f_laur_feature_drift.csv
```

## Diagnostics to compute

### A. Label margin diagnostics

For each checkpoint, reconstruct all candidate rule probe outcomes.

Compute:

```text
best_rule
second_best_rule
best_delta_ratio
second_best_delta_ratio
best_minus_second_margin
best_minus_additive_margin
number_of_rules_within_margin_0.001
number_of_rules_within_margin_0.0025
number_of_rules_within_margin_0.005
number_of_rules_within_margin_0.01
```

Report by:

```text
split
map
agent_count
iteration
best_rule
```

Purpose:

```text
If many labels have tiny best-vs-second margins, hard CE is noisy.
```

### B. Confusion matrix by map and agent count

Use the existing model predictions.

Report:

```text
true_rule -> predicted_rule
true_rule -> predicted_rule by map
true_rule -> predicted_rule by agent_count
true_rule -> predicted_rule by iteration
```

Pay special attention to:

```text
neutral_additive <-> block_heavy
block_heavy <-> neutral_additive
wait_light -> neutral_additive
wait_heavy -> block_heavy
commit_heavy -> block_heavy
```

### C. Safety threshold sweep

Evaluate thresholds:

```text
0.05, 0.10, 0.15, ..., 0.95
```

For each threshold:

```text
harmful recall
harmful precision
harmful F1
additive fallback rate
mean predicted delta after safety gating
per-map harmful recall
per-map mean predicted delta
```

Do not lower the final gate. This is calibration evidence only.

### D. Feature drift diagnostics

For each feature in `aggregate_checkpoint_v1`:

```text
train mean/std
validation mean/std
empty-48-48 mean/std
maze-32-32-4 mean/std
standardized mean difference
KS-like quantile differences if easy
```

Report the top 15 drifted features.

Expected high-risk features:

```text
density
map_width
map_height
obstacle_ratio
blocked_per_committed
wait_per_committed
topk_blocked_edge_concentration
entropy_edge_usage
local_degree_mean_topk
weight_entropy
saturated_edge_count
```

### E. Rule family accuracy

Collapse rules into families for diagnosis only:

```text
additive family: additive_ltm, neutral_additive
commit family: commit_heavy
block family: block_heavy, block_light
wait family: wait_light, wait_heavy
decay family: decay_095, decay_090
```

Report family top1/top3.  
Do not use this to pass the gate. It only tells us whether errors are within a plausible family.

## P0 gate

P0 passes if:

```text
diagnostics script runs
all tables written
diagnostics report explains the top 3 failure causes
no model/training changes were made
no raw trace committed
```

---

# P1. Additive/neutral target cleanup

## Rationale

Current rule vocab contains both:

```text
additive_ltm
neutral_additive
```

But both are executable additive fallback actions. In `src/models/laur_ltm.py`, both have:

```text
alpha_commit = 1.0
alpha_block = 1.0
alpha_wait = 1.0
rho_decay = 1.0
force_additive = True
```

This creates an artificial 9-class problem even though runtime only needs one additive action.

## Goal

Remove `neutral_additive` from the executable rule classification target.

Keep neutral as a semantic flag:

```text
target.neutral = true/false
```

But executable rule should be:

```text
additive_ltm
```

## New / modified files

```text
src/czr004_teacher/update_sequences.py
src/train/train_laur_ltm.py
src/train/losses_laur.py
src/eval/eval_laur_offline.py
src/models/laur_ltm.py
tests/test_phase4_laur_schema.py
outputs/reports/phase4f_laur_additive_neutral_cleanup_report.md
```

## Implementation details

### Dataset builder

Add config option:

```yaml
target_repair:
  collapse_neutral_additive: true
```

When building target:

```python
if rule_class == "neutral_additive":
    rule_class = "additive_ltm"
    neutral = True
```

The output rule vocab must exclude `neutral_additive`:

```text
additive_ltm
commit_heavy
block_heavy
block_light
wait_light
wait_heavy
decay_095
decay_090
```

Keep these target fields:

```text
target.neutral
target.best_rule_original
target.best_rule_executable
target.best_minus_second_margin
target.best_minus_additive_margin
```

### Model export

`DEFAULT_RULE_PARAMS` may keep `neutral_additive` for backward-compatible loading of old artifacts, but new exported `laur_mlp_v1_rules.json` should not contain `neutral_additive`.

### Loss

Simplify fallback regularization:

```text
safe fallback rule = additive_ltm only
neutral rows receive stronger regularization toward additive_ltm
```

Do not require a separate `neutral_index`.

### Evaluation

Rename metric:

```text
neutral_additive_rate -> additive_fallback_rate
```

Still report:

```text
neutral_label_rate
```

## Tests

Add or update tests:

```text
test_neutral_additive_collapses_to_additive_ltm
test_rule_vocab_excludes_neutral_additive_after_cleanup
test_neutral_flag_preserved
test_legacy_neutral_additive_rows_still_load
```

## P1 gate

Run on existing full dataset without regenerating probes.

Pass if:

```text
dataset rebuild passes schema validation
rule_vocab_count becomes 8
neutral flag count preserved
train/eval scripts run
validation top1/top3/harmful recall are reported
```

Do not expect this alone to solve all performance issues. It removes a known target defect.

---

# P2. Safety calibration and class-weighted safety training

## Rationale

Validation safety AUROC has signal, but harmful recall at threshold 0.5 is below gate. Before changing LAUR direction, calibrate the safety head and increase recall.

## Goal

Improve:

```text
validation harmful recall >= 0.80
validation harmful precision >= 0.30
```

while preserving:

```text
validation predicted-rule mean delta ratio > 0
```

## New / modified files

```text
src/train/losses_laur.py
src/train/train_laur_ltm.py
src/eval/eval_laur_offline.py
src/eval/diagnose_laur_phase4f.py
configs/phase4/laur_ltm_full_repair.yaml
outputs/reports/phase4f_laur_safety_calibration_report.md
outputs/tables/phase4f_laur_safety_threshold_sweep.csv
```

## Implementation details

### Loss options

Add config:

```yaml
training:
  safety:
    pos_weight: auto
    focal_gamma: 0.0
    threshold_selection: calibration_split
    threshold_grid: [0.05, 0.10, 0.15, ..., 0.95]
```

If `pos_weight: auto`:

```python
pos_weight = negative_count / positive_count
```

Add to BCE:

```python
binary_cross_entropy_with_logits(..., pos_weight=pos_weight)
```

Optional focal loss only if BCE + pos_weight is insufficient.

### Threshold selection

Do not hardcode 0.5.

Select safety threshold on training/calibration rows:

```text
maximize predicted safe delta subject to:
  harmful recall >= 0.80
  harmful precision >= 0.30
```

Then report validation metrics using that threshold.

If no threshold satisfies both:

```text
select the threshold with highest recall while precision >= 0.30
and mark gate failed
```

### Safety-gated rule selection

For offline evaluation only:

```python
if harmful_probability >= selected_threshold:
    predicted_rule = "additive_ltm"
else:
    predicted_rule = rule_head_argmax
```

Report both ungated and gated results:

```text
ungated_top1
ungated_top3
gated_top1
gated_top3
gated_harmful_recall
gated_harmful_precision
gated_predicted_delta
additive_fallback_rate
```

## P2 gate

Pass if:

```text
threshold sweep table written
selected threshold documented
validation harmful recall improves
precision remains >= 0.30
predicted mean delta remains > 0
```

The main Phase4F gate is not considered passed unless top1/top3 gates also pass.

---

# P3. Margin-aware labels and soft/ranking losses

## Rationale

The current hard target:

```text
one checkpoint -> one best_update_rule_class
```

is too brittle when several rules have nearly equal probe deltas. LAU should learn solver-facing update preference, not noisy argmax labels.

## Goal

Use probe outcome margins to train with soft targets and ranking losses while keeping the final strict metrics.

## New / modified files

```text
src/czr004_teacher/update_sequences.py
src/train/losses_laur.py
src/train/train_laur_ltm.py
src/eval/eval_laur_offline.py
tests/test_phase4_laur_schema.py
outputs/reports/phase4f_laur_margin_aware_training_report.md
```

## Dataset changes

Add fields to each checkpoint-level dataset row:

```json
{
  "target": {
    "rule_class": "...",
    "rule_vocab": [...],
    "neutral": false,
    "harmful_update": false,
    "delta_ratio_best": 0.0,

    "rule_delta_vector": [ ... ],
    "rule_harmful_vector": [ ... ],
    "rule_valid_vector": [ ... ],

    "best_minus_second_margin": 0.0,
    "best_minus_additive_margin": 0.0,
    "ambiguous_label": true,
    "soft_rule_target": [ ... ]
  }
}
```

### Soft target construction

For each rule:

```text
safe_score(rule) =
  delta_ratio(rule)
  - harmful_penalty * is_harmful(rule)
```

Then:

```text
soft_rule_target = softmax(safe_score / temperature)
```

Recommended first settings:

```yaml
target_repair:
  soft_target_temperature: 0.01
  harmful_penalty: 0.02
  ambiguous_margin: 0.005
  pairwise_margin: 0.005
```

Do not remove ambiguous rows from validation.  
You may report unambiguous subset metrics, but the main gate must remain on all validation rows.

## Loss changes

Replace or augment hard CE with:

```text
KLDivLoss(log_softmax(rule_logits), soft_rule_target)
pairwise ranking loss between rules with delta gap >= pairwise_margin
safety BCE with pos_weight
delta expected-value regression
additive fallback regularization
```

Recommended total loss:

```text
L =
  λ_soft_ce * soft_rule_KL
+ λ_pairwise * pairwise_rule_ranking
+ λ_safety * weighted_safety_BCE
+ λ_delta * expected_delta_regression
+ λ_reg * additive_deviation_regularization
```

Do not remove hard top1/top3 evaluation. Training can be soft; the gate remains strict.

## Evaluation changes

Report:

```text
hard top1
hard top3
top1 within margin
top3 within margin
pairwise ranking accuracy
expected selected delta
safety-gated selected delta
```

Main gate remains:

```text
hard validation top1 >= 0.35
hard validation top3 >= 0.70
harmful recall >= 0.80
precision >= 0.30
predicted delta > 0
```

## P3 gate

Pass if:

```text
soft/ranking model trains
validation top3 improves over current 0.4716
harmful recall does not regress
predicted mean delta remains positive
```

If P3 does not reach gate, move to P4.

---

# P4. Rule-aware scorer model

## Rationale

This is the most important modeling change.

The current classifier uses:

```text
checkpoint features -> rule class
```

But Phase4D generated richer data:

```text
checkpoint x candidate update rule -> probe outcome
```

LAU should learn:

```text
Q(checkpoint, update_rule) = expected solver improvement
```

rather than directly classifying the checkpoint.

This uses all 15,360 probe rows instead of compressing them into 1,897 hard labels.

## Goal

Train a rule-aware scoring model that predicts, for each candidate update rule:

```text
expected delta ratio
harmful probability
```

Then select:

```text
best safe rule = argmax(expected_delta - safety_penalty * harmful_prob)
fallback to additive_ltm if unsafe or low confidence
```

This remains LAU-LTM. It still learns the LTM update rule. It does not change solver direction.

## New files

```text
src/czr004_teacher/rule_scoring_dataset.py
src/models/laur_rule_scorer.py
src/train/train_laur_rule_scorer.py
src/train/losses_laur_rule_scorer.py
src/eval/eval_laur_rule_scorer_offline.py
tests/test_phase4f_rule_scorer.py
configs/phase4/laur_ltm_full_rule_scorer.yaml
outputs/reports/phase4f_laur_rule_scorer_report.md
```

## Dataset schema

One training row per:

```text
(checkpoint_id, rule_id)
```

Input features:

```text
checkpoint_feature_vector
rule_feature_vector
interaction_features
```

Rule features:

```text
alpha_commit
alpha_block
alpha_wait
rho_decay
saturation_scale
contraflow_penalty
is_additive
is_commit_rule
is_block_rule
is_wait_rule
is_decay_rule
```

Interaction features:

```text
committed_count * alpha_commit
blocked_count * alpha_block
wait_event_count * alpha_wait
blocked_per_committed * alpha_block
wait_per_committed * alpha_wait
max_raw_before * rho_decay
topk_raw_delta_mean under this rule if available
topk_raw_delta_max under this rule if available
new_nonzero_edges_count under this rule if available
```

Targets:

```text
delta_ratio_vs_additive
is_harmful_update
rank_within_checkpoint
is_best_rule
is_within_top3
```

Group key:

```text
run_id + checkpoint_id
```

## Model

Recommended first model:

```text
LAU-RuleScorer-v1
```

Architecture:

```text
checkpoint_encoder: Linear(36 -> 96) + ReLU
rule_encoder: Linear(rule_dim -> 32) + ReLU
joint_encoder: Linear(96 + 32 + interaction_dim -> 96) + ReLU
delta_head: Linear(96 -> 1)
safety_head: Linear(96 -> 1)
```

Do not start with a large Transformer or GNN. The immediate problem is objective alignment, not capacity.

## Loss

For each checkpoint group:

```text
L =
  λ_delta * SmoothL1(pred_delta, true_delta)
+ λ_safety * weighted_BCE(pred_harmful, true_harmful)
+ λ_pairwise * pairwise ranking loss over rules
+ λ_topk * listwise softmax / NDCG-like loss
+ λ_additive * fallback regularization
```

Pairwise ranking:

```python
for rules i,j in same checkpoint:
    if true_delta_i - true_delta_j >= margin:
        loss += softplus(-(score_i - score_j))
```

Scoring function for ranking:

```text
score(rule) = pred_delta - safety_penalty * sigmoid(harmful_logit)
```

## Rule selection policy

Offline selection:

```python
safe_rules = rules where harmful_prob < safety_threshold
if no safe non-additive rule:
    select additive_ltm
else:
    select argmax(pred_delta - safety_penalty * harmful_prob)
```

Always include additive_ltm.

## Evaluation

Convert selected rule per checkpoint back to the existing Phase4F metrics:

```text
selected rule top1
selected rule top3
harmful recall
harmful precision
predicted selected-rule mean delta
additive fallback rate
per-map breakdown
per-agent breakdown
per-iteration breakdown
```

Also report scorer-specific metrics:

```text
delta MAE
delta Spearman within checkpoint
pairwise ranking accuracy
oracle top3 delta
selected vs additive delta
```

## P4 gate

Same strict Phase4F gate:

```text
validation top1 >= 0.35
validation top3 >= 0.70
harmful recall >= 0.80
harmful precision >= 0.30
predicted mean delta > 0
```

Additional scorer gate:

```text
validation pairwise ranking accuracy > 0.55
validation selected-vs-additive delta > 0
```

This is likely the best route if hard checkpoint classification remains poor.

---

# P5. Feature and checkpoint-context repair

## Rationale

Current aggregate checkpoint features are useful, but some solver-context features may still be approximations rather than true running solver state. LAU needs the model to understand where the solver is in the anytime process.

## Goal

Replace proxy solver-context fields with true running fields and add topology/bottleneck features that improve map-family generalization.

## Files likely to change

```text
cpp/ltm/ltm.hpp
cpp/ltm/ltm.cpp
cpp/tools/phase4_laur_record.cpp
src/czr004_teacher/features_laur.py
src/czr004_teacher/update_sequences.py
tests/test_phase4_laur_schema.py
outputs/reports/phase4f_laur_feature_repair_report.md
```

## Add true running solver context

Add or verify these checkpoint fields:

```text
has_incumbent_before_update
best_sum_of_loss_before_update
best_ratio_before_update
sum_of_loss_this_iteration
ratio_this_iteration
improved_this_iteration
improved_last_iteration
returned_solutions_count_so_far
time_to_first_solution_ms
expanded_nodes_cumulative
high_level_expansions_cumulative
low_level_pibt_calls_cumulative
```

Current feature names include:

```text
has_solution_before
best_ratio_before
improved_last_iteration
returned_solutions_count_so_far
```

Audit whether these are true fields or smoke proxies. If proxy, repair them.

## Add topology features

From map parser / free-cell graph:

```text
degree_1_cell_fraction
degree_2_cell_fraction
degree_3_cell_fraction
degree_4_cell_fraction
corridor_cell_fraction
intersection_cell_fraction
dead_end_fraction
obstacle_boundary_fraction
estimated_bottleneck_fraction
connected_component_count
```

Local top-K traffic topology features:

```text
topk_edge_mean_from_degree
topk_edge_mean_to_degree
topk_edge_degree2_fraction
topk_edge_corridor_fraction
topk_edge_intersection_fraction
```

Keep `map_name` and `split` out of model features.

## P5 gate

Pass if:

```text
schema validation passes
feature drift report updated
train/eval scripts still run
validation top1/top3/harmful recall improve or feature repair is documented as neutral
```

If the feature repair requires re-recording full data, do it only after P0-P4 show that labels/objective are no longer the main bottleneck.

---

# P6. Split and data repair without lowering standards

## Rationale

Current validation is heavily OOD. This is valuable, but a single OOD validation split is not ideal for developing a stable learned update policy.

The standard should not be lowered. Instead, create clearer split categories.

## Goal

Add split categories:

```text
train
validation_id
validation_ood
test_holdout
```

Do not remove OOD evaluation. Do not make the gate easier. Add better diagnostics.

## Config changes

Create:

```text
configs/phase4/laur_ltm_full_repair.yaml
```

Recommended split structure:

```yaml
maps:
  # train: cover every major map family when possible
  - map_name: empty-32-32
    split: train
  - map_name: random-32-32-20
    split: train
  - map_name: random-64-64-20
    split: train
  - map_name: room-64-64-8
    split: train
  - map_name: warehouse-10-20-10-2-1
    split: train
  - map_name: warehouse-10-20-10-2-2
    split: train

  # add a maze-like train map if available in external/lacam2/scripts/map/
  # do not use the exact final OOD maze map for training if it is reserved as test
  - map_name: maze-train-candidate
    split: train

  # ID validation: same families as train, different map or held-out instances/seeds
  - map_name: validation-id-candidate
    split: validation_id

  # OOD validation / stress
  - map_name: empty-48-48
    split: validation_ood
  - map_name: maze-32-32-4
    split: validation_ood
```

Codex should inspect available map files before deciding exact names.

## Important rule

Do not pass Phase4F by ignoring OOD.  
Report both:

```text
validation_id metrics
validation_ood metrics
```

A repaired model should satisfy:

```text
validation_id passes strict gate
validation_ood predicted delta is not negative
validation_ood harmful recall is not catastrophic
```

For Phase5 learned runtime readiness, prefer a model that also passes the original validation maps, but use the split report to diagnose whether failure is pure OOD.

## Data expansion priorities

If adding data, prioritize:

```text
1. Add maze-like train family or additional maze holdout split.
2. Add empty-size variation so empty-48-48 is not the only size extrapolation.
3. Balance agent counts 50/100/200/400.
4. Balance iterations 0/1/2/3.
5. Add instances only after map-family coverage is fixed.
```

## P6 gate

Pass if:

```text
new split audit passes
no leakage between train / validation_id / validation_ood / test_holdout
validation report includes all split categories
strict Phase4F metrics are reported for each category
```

---

# P7. Probe-label quality improvement

## Rationale

If label margins are small or noisy, the one-second probe may not give stable best-rule labels.

## Goal

Improve label reliability without changing LAUR direction.

## Changes to consider

In config:

```yaml
probe:
  short_budget_sec: 2.0   # try 2 first, then 3 if needed
  min_delta_ratio_for_label: 0.005
  harmful_delta_ratio_threshold: -0.02
  repeated_probe_seeds: 3
  label_margin_for_confidence: 0.005
```

Do not immediately rerun a massive full batch. First run a pilot:

```text
2 maps
2 agent counts
5 instances
max_iterations 4
all current rules
short_budget 1 vs 2 vs 3 comparison
```

## Add label confidence

For each checkpoint:

```text
label_confidence = best_minus_second_margin
probe_stability = agreement rate across repeated probe seeds
```

Use these in training:

```text
higher confidence -> higher loss weight
low confidence -> soft target / lower pairwise weight
```

Do not drop low-confidence validation rows from the main gate. You may report a confidence-stratified breakdown.

## Optional rule-set expansion

Only after P1-P4 are working, consider adding:

```text
saturation_low
saturation_high
decay_080
block_very_heavy
commit_light
```

But do not expand the rule set before fixing label/objective issues. More rules make hard classification harder.

## P7 gate

Pass if:

```text
probe label stability improves
best-vs-second margin improves
validation top3 or selected-delta improves after retraining
```

---

# P8. Model capacity and regularization sweep

## Rationale

The current one-hidden-layer MLP can fit training but generalizes poorly. Capacity alone is not the first fix, but after target repair it may help.

## Allowed model sweeps

Do not make a huge model. Keep Phase4F lightweight.

Try:

```text
hidden_dim: 64, 96, 128, 192
num_layers: 1, 2
dropout: 0.0, 0.1, 0.2
weight_decay: 0.0002, 0.001, 0.003
learning_rate: 0.001, 0.003, 0.006
early_stopping_patience: 30
```

For safety:

```text
safety_pos_weight: auto, 2.0, 4.0
safety_threshold: selected by calibration
```

## Add early stopping

Stop on a validation objective that reflects the strict gates:

```text
score =
  + top3
  + 0.5 * top1
  + harmful_recall
  + 0.25 * harmful_precision
  + 0.5 * indicator(predicted_delta > 0)
  - 0.1 * additive_fallback_rate_if_too_high
```

Do not optimize only training loss.

## P8 gate

Pass if:

```text
best config is selected by validation, not train
all metrics reported
strict Phase4F gate passes or remains blocked
```

---

## 5. Suggested execution schedule

### Round 1: no big data rerun

```text
P0 diagnostics
P1 collapse neutral/additive target
P2 safety calibration
retrain/eval on existing full dataset
```

Expected output:

```text
outputs/reports/phase4f_laur_repair_round1_report.md
```

If strict gate passes, stop and ask user before Phase5.

### Round 2: objective repair

```text
P3 margin-aware soft/ranking labels
retrain/eval on existing full dataset
```

Expected output:

```text
outputs/reports/phase4f_laur_repair_round2_margin_report.md
```

### Round 3: rule-aware scorer

```text
P4 rule-aware scorer dataset/model/train/eval
```

Expected output:

```text
outputs/reports/phase4f_laur_rule_scorer_report.md
```

If this passes strict Phase4F gate, it becomes the preferred Phase5 candidate.

### Round 4: data/feature repair

Only if Rounds 1-3 fail:

```text
P5 feature repair
P6 split/data repair
P7 probe-label improvement
rerun smaller pilot first
then rerun full if pilot improves
```

---

## 6. Required reports after each attempt

Every attempt must write a Markdown report.

Minimum report template:

```markdown
# phase4f_laur_<attempt_name>_report

## Question
What failure mode does this attempt test?

## Code State
- branch:
- commit:
- dirty files:

## Inputs
- dataset:
- probe jsonl:
- model artifact:
- config:

## Changes
- files changed:
- target changes:
- loss changes:
- eval changes:

## Results
- train top1/top3:
- validation top1/top3:
- harmful recall:
- harmful precision:
- predicted mean delta:
- additive fallback rate:
- per-map breakdown:
- per-agent breakdown:
- per-iteration breakdown:

## Interpretation
- pass/fail:
- what improved:
- what regressed:
- whether Phase5 is still blocked:

## Repro Command
```

---

## 7. Required tests

Add tests before or with each code change.

Suggested tests:

```text
test_neutral_additive_collapses_to_additive_ltm
test_rule_vocab_is_dynamic_and_no_duplicate_additive
test_soft_rule_target_sums_to_one
test_rule_delta_vector_aligns_with_rule_vocab
test_pairwise_groups_are_checkpoint_local
test_safety_threshold_sweep_selects_valid_threshold
test_rule_scorer_dataset_has_one_row_per_checkpoint_rule
test_rule_scorer_additive_rule_always_present
test_no_map_name_or_split_in_model_features
test_legacy_phase4e_dataset_still_loads_or_fails_with_clear_message
```

Run:

```bash
python -m pytest tests/test_phase4_laur_schema.py tests/test_phase4f_rule_scorer.py -q
```

Also rerun existing Phase4F smoke after changes.

---

## 8. When to use the server

Do not use the server for P0-P4 unless local artifacts are missing.

Use local existing full artifacts for:

```text
diagnostics
target cleanup
retraining on existing dataset
rule-scorer dataset from existing probes
offline eval
```

Use server only for:

```text
new full record/probe generation
short_budget_sec comparison at scale
expanded split/data rerun
large repeated-probe jobs
```

Do not commit raw trace files to normal GitHub.

---

## 9. Stop conditions

### Stop and report success

If any repaired Phase4F attempt passes:

```text
validation top1 >= 0.35
validation top3 >= 0.70
harmful recall >= 0.80
harmful precision >= 0.30
predicted mean delta > 0
```

Then:

```text
write a pass report
do not start Phase5 automatically
ask user whether to proceed to Phase5 learned runtime
```

### Stop and report blocked

If P1-P4 fail and diagnostics show:

```text
labels are near-tie/noisy
validation OOD remains the main blocker
rule scorer selected-delta is not positive
```

Then do not keep blindly tuning. Move to P5-P7 with a pilot data rerun.

---

## 10. Final recommendation

The most promising path is:

```text
1. Fix duplicate additive target.
2. Calibrate safety to recover harmful recall.
3. Replace hard best-rule CE with margin-aware soft/ranking loss.
4. If still weak, switch from checkpoint classifier to rule-aware scorer.
```

The strongest LAUR-consistent modeling formulation is:

```text
learn Q(checkpoint, update_rule)
rather than
classify checkpoint -> best update rule
```

This uses the Phase4D probe rows more fully, remains within learned LTM update, and is the most likely route to a model that can eventually beat ordinary additive LTM in closed-loop Phase5/Phase6 experiments.
