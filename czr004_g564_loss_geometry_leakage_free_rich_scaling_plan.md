# Repair5G.5.64 — Loss-Geometry Truth, Leakage-Free Rich-Attention Scaling, and Real Feasibility Closure

Project: `czr004`  
Repository: `czr5454112-glitch/czr004`  
Required branch: `server-code`  
Source-of-truth start commit: `1c3670232e6dc2c9bb34a2289a65d46945b7617d`  
Primary supported baseline: `g556_c063174`  
Paper-faithful floor: `LaCAM* + additive LTM`  
Round: `Repair5G.5.64`

---

## 0. Non-negotiable scientific mainline

The project goal remains:

```text
one MAPF instance
  = physical graph topology
  + actual paired starts/goals
  + paired OD tokens
  + directed C0 congestion/conflict prior
  + directed F0 goal-progress prior
  + solver budget
  + LTM iteration budget
        ↓
goal-aware attention-based neural actor
        ↓
one bounded continuous dual-channel UpdateParams theta
        ↓
theta remains fixed for the complete solver run
        ↓
ordinary trace-driven C/F traffic maps continue updating online
```

The project is trying to replace the coarse hand-designed additive LTM update configuration with an instance-conditioned learned continuous parameter predictor and ultimately outperform:

```text
1. paper-faithful LaCAM* + additive LTM;
2. the strong fixed global baseline g556_c063174.
```

The main method is not:

```text
an agent action policy
a PIBT priority policy
a restart policy
a checkpoint-time policy
a codebook selector
a candidate-ID classifier
a nearest-neighbor theta retriever
a runtime critic selector
a scalar-only MLP
```

G5.64 must preserve the final deployment contract:

```text
one actor forward pass
-> one continuous theta
-> no codebook
-> no critic
-> no candidate enumeration
-> no runtime theta switching
```

---

# Part I — Correct interpretation of G5.63

## 1. What G5.63 successfully fixed

G5.63 made meaningful engineering progress:

```text
Label-v5.2 set-valued adapter exists
all original Label-v5.1 candidate rows are retained
positive safe modes are no longer arithmetically averaged
censored rows are not automatically treated as harmful
grouped physical-map splits are disjoint
nested context subsets are materialized
run-scoped provenance is implemented
1,000 contexts / 65,000 candidate rows are represented
the diagnostic per-context optimizer reduced loss by about 36%
```

These are real improvements and should be preserved.

## 2. Why the current tiny-overfit failure is not yet a model failure

The committed tiny-overfit test does not train the goal-aware graph actor.

It creates one independently trainable theta vector per context:

```python
logits = Parameter[num_contexts, theta_dim]
theta = lo + sigmoid(logits) * (hi - lo)
```

Therefore it is testing:

```text
Can the current mathematical loss attain a sufficiently low value?
```

It is not testing:

```text
Can the graph/OD/C0/F0 neural architecture learn the mapping?
```

The current failure label:

```text
g563_tiny_overfit_failed_repair_model_or_loss
```

must be split into:

```text
loss geometry / parameterization failure
actual neural memorization failure
```

Those are different scientific outcomes.

## 3. Why the current scaling “pass” is not valid evidence for the main idea

The G5.63 scaling model is a scalar MLP whose input includes:

```text
positive_rows
safe_rows
harmful_rows
censored_rows
```

These fields are computed from solver outcome labels.

They are unavailable at inference.

This is direct target leakage.

The scaling model also does not consume:

```text
graph topology
paired OD
C0
F0
```

Therefore:

```text
64 -> 128 -> 256 validation improvement
```

does not yet establish that the production goal-aware graph actor scales with data.

G5.64 must formally reclassify the current scaling result as:

```text
diagnostic_only_invalid_for_primary_feasibility_due_to_label_leakage
```

The scalar curve may be retained as a debugging artifact, but it cannot satisfy a feasibility gate.

## 4. Why the tiny loss floor may be artificial

Several implementation choices can create an irreducible or artificial floor.

### 4.1 Normalized softmin weights create a nonzero entropy floor

Current positive loss:

```text
L = -tau log sum_j normalized_weight_j * exp(-distance_j / tau)
```

Even when theta exactly equals a positive mode, the loss is generally not zero if the positive weight of that mode is less than one.

Therefore an absolute loss target or “50% reduction” target is not meaningful without computing the per-context oracle floor.

### 4.2 Default AdamW applies unintended weight decay

The tiny optimizer uses:

```python
AdamW([logits], lr=...)
```

without setting `weight_decay=0`.

For free per-context logits this regularizes logits toward zero, which means:

```text
theta -> midpoint of all solver bounds
```

That is not g556 and is not a scientifically intended prior.

### 4.3 Sigmoid bounded parameterization cannot exactly reach bounds

Many observed positive theta rows lie on solver bounds.

A sigmoid parameterization requires infinite logits to exactly reach a bound.

Combined with weight decay, this can prevent exact fitting.

### 4.4 Fixed harmful margin can be geometrically impossible

The current harmful repulsion uses a fixed normalized L1 margin of `0.12`.

If a verified positive theta is closer than that to a harmful theta, then:

```text
positive attraction
and
harmful repulsion
```

cannot both reach zero.

This can reflect:

```text
solver discontinuity
label noise
single-run outcome instability
near-duplicate theta with conflicting outcomes
an overlarge geometric margin
```

It does not automatically reflect optimizer or actor failure.

### 4.5 Mean harmful loss can hide the nearest dangerous candidate

A mean over all harmful candidates can dilute one nearby harmful point among many distant harmful points.

For safety, the closest or top-k harmful distances matter more than the average.

## 5. Current label-state distribution is difficult

The current 1,000-context Label-v5.2 dataset contains approximately:

```text
MIXED_FRONTIER: 604
CENSORED_UNKNOWN: 368
POSITIVE_SUPPORTED: 12
HARMFUL_SUPPORTED: 16
```

and uses:

```text
quality_margin = 0.0
```

Thus almost every finite nonzero delta is treated as clearly positive or harmful.

This is too aggressive until solver noise, integer cost resolution, and replicate behavior have been audited.

---

# Part II — G5.64 priority order

## 6. Mandatory order

G5.64 must proceed in this exact order:

```text
A. truth-correct G5.63 conclusions;
B. remove all input leakage;
C. compute the true loss-geometry lower bound;
D. repair the tiny parameter-oracle test;
E. run actual rich-network memorization tests;
F. calibrate label noise / conflicting neighborhoods;
G. run leakage-free scaling with rich attention actors;
H. merge existing exact replay labels and retrain;
I. run a fixed exact solver feasibility panel;
J. expand independent contexts only if the preceding evidence supports it.
```

Do not start a large new data sweep before A–G are complete.

## 7. Required iterative behavior

Codex must not stop after the first failed overfit attempt.

If an overfit test fails, it must:

```text
1. compute the oracle floor and conflict geometry;
2. run the specified optimizer / loss ablation matrix;
3. implement at least one justified repair;
4. rerun the test;
5. attribute any remaining floor quantitatively.
```

A JSON summary saying “gate failed” is not substantive completion.

---

# Part III — P0 code-truth repairs

## 8. Reclassify G5.63 decisions

Add a truth audit that records:

```text
g563_tiny_test_object = per_context_free_theta_not_graph_actor
g563_scaling_model = scalar_label_leaking_control
g563_primary_graph_scaling_test_executed = false
g563_loss_floor_computed = false
g563_true_retraining_cycle_executed = false
```

Update the global history without deleting the original artifacts.

The new interpretation should be:

```text
G5.63 repaired data semantics,
but did not yet produce a valid primary-model scaling result.
```

## 9. Strict inference-feature allowlist

Create two separate schemas:

```text
INFERENCE_FEATURE_SCHEMA
LABEL_ANALYSIS_SCHEMA
```

Only the first may enter any actor or deployable encoder.

### 9.1 Allowed pre-solver information

```text
physical graph topology
node structural features
directed edge structural features
actual paired starts/goals
paired OD tokens
C0 tensor
F0 tensor
agent count
density derived from the instance
solver budget
LTM iteration budget
other deterministic pre-solver instance descriptors
```

### 9.2 Forbidden actor inputs

```text
positive_rows
safe_rows
harmful_rows
censored_rows
label_state
quality_delta
success_gain
success_regression
candidate rank
oracle theta
candidate ID
map ID as a lookup token
solver outcome counts
post-run trace statistics
```

### 9.3 Mandatory tests

```text
test_actor_feature_schema_contains_no_label_fields
test_scaling_control_contains_no_outcome_counts
test_rich_actor_forward_requires_graph_od_c0_f0
test_export_feature_schema_is_pre_solver_only
test_forbidden_feature_ast_audit
```

## 10. Split truth

Maintain four roles:

```text
train
validation
heldout
blind solver panel
```

Rules:

```text
validation selects checkpoints and hyperparameters;
heldout is evaluated only after freeze;
blind solver panel is not used for offline tuning;
physical map hashes are disjoint.
```

Add a split-use ledger listing every script that reads each split.

## 11. Run provenance

Every run must record:

```text
run_uid
source commit
dataset SHA
candidate manifest SHA
split manifest SHA
feature schema SHA
loss configuration SHA
model configuration SHA
optimizer configuration SHA
parent checkpoint SHA
output checkpoint SHA
progress JSONL
server hostname
CUDA device
start/end timestamp
```

Progress logs from different runs must never be concatenated into a single unscoped file.

---

# Part IV — Loss-geometry truth audit

## 12. Per-context geometry table

For every context, compute:

```text
positive count
harmful-regression count
harmful-quality count
safe-nonimproving count
censored count
minimum positive-positive distance
minimum positive-harmful distance
median positive-harmful distance
minimum positive-g556 distance
nearest harmful distance to g556
positive mode count after clustering
duplicate theta count
near-duplicate conflicting-label count
current softmin entropy floor
best observed-positive total loss
best observed-safe total loss
best observed-candidate total loss
continuous multi-start oracle loss
```

Output:

```text
outputs/tables/phase5p5_repair5g564_loss_geometry_by_context.csv
outputs/reports/phase5p5_repair5g564_loss_geometry_summary.json
outputs/reports/phase5p5_repair5g564_loss_geometry.md
```

## 13. Conflict definitions

A context is `GEOMETRICALLY_COMPATIBLE` only when at least one positive mode has adequate separation from verified harmful modes under the proposed margin.

Otherwise classify:

```text
NEAR_CONFLICT
EXACT_THETA_CONFLICT
BOUNDARY_CONFLICT
SUCCESS_DISCONTINUITY
INSUFFICIENT_SUPPORT
```

Do not force geometrically incompatible contexts into the same overfit gate.

## 14. Replicate/confidence audit

Locate:

```text
near-duplicate theta pairs with opposite labels
very small positive/negative quality deltas
success-boundary candidates
large ratio outliers
```

Run a compact paired replicate panel on a stratified diagnostic subset.

The data object remains:

```text
(instance, theta) -> solver outcome
```

This is not DAgger.

Estimate:

```text
quality tie margin
success label stability
quality delta variance
candidate repeatability
```

Use the resulting margin in the repaired label adapter.

If replicates are unavailable for a context, retain uncertainty rather than inventing certainty.

---

# Part V — Loss repair matrix

## 15. Positive set losses

Implement and compare at least three options.

### P0 — current normalized-weight softmin

Retain only as a diagnostic baseline.

### P1 — floor-corrected softmin

Compute the per-context oracle floor and optimize excess loss:

```text
L_excess = L_softmin(theta) - L_softmin_oracle_floor(context)
```

The reported minimum is approximately zero by construction.

### P2 — quality-aware hard winner-take-all

For each forward pass:

```text
j* = argmin_j [distance(theta_hat, theta_j) + beta * utility_regret_j]
L = distance(theta_hat, theta_j*) + beta * utility_regret_j*
```

Only the selected mode receives gradient.

This is a training loss, not deployment-time candidate selection.

### P3 — clustered medoid WTA

Cluster verified positive candidates in normalized theta space.

Use one medoid per mode.

Train against the best compatible medoid.

This reduces duplicate candidate bias.

## 16. Harmful losses

Compare:

### H0 — current mean hinge

Diagnostic only.

### H1 — nearest-harmful hinge

```text
max(0, margin - min_distance_to_harmful)
```

### H2 — top-k/CVaR harmful hinge

Penalize the most dangerous nearest harmful subset.

### H3 — adaptive-margin harmful loss

Set context margin using observed positive-harmful geometry:

```text
margin_x <= fraction * positive_harmful_separation
```

Do not demand an impossible fixed margin.

### H4 — critic risk penalty

Use a cross-fitted training-only critic to estimate risk at generated theta.

Do not export the critic.

## 17. Censored and unsupported contexts

Censored contexts must not contribute a fake target.

Allowed terms:

```text
weak support distance
small residual prior
uncertainty-aware trust penalty
representation consistency
```

Report their loss separately so the large censored fraction cannot make total validation loss look artificially good.

## 18. Loss normalization

All headline metrics must include:

```text
raw total loss
oracle floor
excess over oracle floor
nearest-positive distance
harmful violation rate
success-regression surrogate loss
censored-only loss
```

The primary offline feasibility metric is:

```text
normalized excess set risk
```

not raw softmin value.

---

# Part VI — Correct tiny-overfit ladder

## 19. Stage T0 — one-context positive-only parameter oracle

Use a directly projected theta parameter.

No sigmoid saturation.

No weight decay.

No harmful term.

Initialize from:

```text
g556
best observed positive
random interior
```

Require convergence near a verified positive mode.

## 20. Stage T1 — one-context mixed parameter oracle

Use only geometrically compatible mixed contexts.

Compare:

```text
best observed candidate
multi-start projected Adam
LBFGS
CMA-ES diagnostic if needed
```

The pass criterion is excess over the computed oracle floor, not percentage reduction from initialization.

## 21. Stage T2 — 8/16/32-context independent parameter oracle

Each context retains a free theta.

Report:

```text
per-context oracle loss
achieved loss
excess loss
contexts at bound
harmful violations
positive-mode capture
```

## 22. Stage T3 — actual neural actor memorization

Train the real actor using actual graph/OD/C0/F0 inputs.

Dataset sizes:

```text
1
4
8
16
32 contexts
```

Models:

```text
E0 repaired dual-stream actor
E1 lightweight edge-aware attention actor
E2 OD-to-graph cross-attention actor
```

Use:

```text
no dropout
weight_decay = 0 for the initial overfit proof
hidden dimensions 64 and 96
sufficient epochs
best checkpoint by fixed train-set excess risk
```

Pass requires the network—not a per-context embedding—to approach the parameter-oracle solution.

## 23. Stage T4 — memorization controls

Run:

```text
scalar-only actor
global learned theta
rich actor with OD shuffled
rich actor with C0/F0 zeroed
```

The rich actor should fit context-dependent targets better than global/scalar controls.

## 24. Required tiny-overfit outputs

```text
phase5p5_repair5g564_parameter_oracle_summary.json
phase5p5_repair5g564_neural_memorization_summary.json
phase5p5_repair5g564_loss_repair_matrix.csv
phase5p5_repair5g564_context_conflict_matrix.csv
```

---

# Part VII — Leakage-free scaling study

## 25. The scaling question

The valid question is:

```text
Does a graph/OD/C0/F0 actor achieve lower heldout excess set risk
as the number of independent training contexts increases?
```

It is not:

```text
Does a scalar MLP supplied with label-count features improve?
```

## 26. Models

Run matched scaling curves for:

```text
G0: one global learned theta
S0: scalar pre-solver control, no label fields
E0: repaired dual-stream rich actor
E1: lightweight edge-aware attention actor
E2: OD-to-graph cross-attention actor
```

The primary method candidates are E0/E1/E2.

G0/S0 are controls only.

## 27. Input truth for S0

Allowed scalar features may include only deterministic pre-solver values such as:

```text
agent count
budget
LTM iterations
free-cell count
agent density
path length summaries
OD directional summaries
precomputed C0/F0 aggregate summaries
```

Forbidden:

```text
positive/harmful/censored/safe counts
outcome labels
candidate statistics derived from outcomes
```

## 28. Nested context sizes

Use the current bank:

```text
64
128
256
512
all available train contexts
```

If later expansion is justified:

```text
1,000
2,000
4,000
8,000
```

The unit remains independent context.

## 29. Physical-map folds

Use grouped physical-map cross-validation for development.

Recommended:

```text
4 or 5 folds
3 seeds
fixed fold manifests
```

Retain a separate blind solver panel.

## 30. Equalized optimization

Run both:

```text
fixed epochs / context presentations
fixed wall-clock or optimizer-token diagnostic
```

Primary statistical curve:

```text
same maximum epochs
same early-stopping rule
same validation frequency
same architecture
same optimizer schedule
```

Recommended minimum:

```text
30 epochs
patience >= 10 validation checkpoints
```

If loss is still improving, continue rather than stopping at an arbitrary 100 steps.

## 31. Validation logging

At every checkpoint:

```text
positive excess loss
nearest-positive distance
harmful violation rate
censored support loss
total excess risk
theta variance
distance to global theta
intervention effect sizes
```

Report median and uncertainty across folds/seeds.

## 32. Valid scaling gate

A primary-model scaling pass requires all of:

```text
no forbidden inputs
rich actor actually trained
fixed validation map folds
last-size median excess risk < first-size median excess risk
negative slope with uncertainty reported
improvement exceeds seed/fold noise
rich actor beats global theta
rich actor beats scalar control on a majority of folds
```

A tiny `first > last` numerical difference alone is insufficient.

---

# Part VIII — Lightweight attention architecture

## 33. Current network-size interpretation

The current hidden-32 rich network is small.

The likely bottleneck is not parameter count.

Audit:

```text
Python per-destination softmax loop
three full graph encoders
dense global node attention
repeated graph construction
small batches
CPU/GPU imbalance
```

## 34. E1 lightweight actor

Implement a production-eligible lightweight attention actor:

```text
shared sparse edge-aware topology backbone
+ channel-specific C0/F0 adapters or gates
+ paired-OD Set Transformer
+ OD-to-graph cross-attention
+ attention pooling
+ field-group continuous theta head
```

Constraints:

```text
preserve the F6 information floor
one forward -> one theta
no critic/codebook at inference
0.2M–1.5M parameters preferred
```

## 35. Vectorized attention

Replace the Python destination-node loop with tested segment softmax or scatter operations.

Required equivalence tests:

```text
vectorized attention matches reference implementation
node permutation invariance
batch composition invariance
gradient equivalence on a small graph
```

## 36. Profiling

For E0/E1/E2 report:

```text
parameter count
peak VRAM
examples/sec
nodes/sec
edges/sec
data preparation time
forward time
backward time
GPU utilization
```

Do not select architecture by speed alone.

---

# Part IX — Merge the 18,200 exact replay rows

## 37. Actual merge

Convert G5.62 exact replay rows into Label-v5.2.x candidate rows with:

```text
evaluation UID
instance UID
physical map hash
scenario hash
theta fingerprint
candidate success
g556 success
quality delta
materialization truth
source checkpoint
source cycle
```

Deduplicate by full scientific identity.

## 38. Distinguish theta coverage from context coverage

The 18,200 rows likely add substantial theta coverage on existing contexts.

They do not automatically add 18,200 independent instances.

Report separately:

```text
new candidate rows
new unique theta
expanded existing contexts
new unique contexts
new positive modes
new harmful modes
new censored rows
```

## 39. True retraining cycle

Required proof:

```text
dataset_v1 SHA != dataset_v0 SHA
actor_v1 SHA != actor_v0 SHA
actor_v1 manifest lists merged replay rows
fixed validation manifest unchanged
blind panel unchanged
```

Retrain E0/E1/E2 with the repaired loss.

Compare actor_v0 vs actor_v1 on the same fixed offline and solver panels.

---

# Part X — Fixed exact solver feasibility panel

## 40. Preconditions

Do not launch until:

```text
input leakage audit passes
parameter-oracle test is understood
actual neural memorization passes
at least one rich scaling curve is valid
materialization remains exact
```

## 41. Methods

```text
paper-faithful additive LTM
g556_c063174
global learned theta
scalar pre-solver control
E0
E1
E2
```

## 42. Panels

Keep separate:

```text
validation maps
heldout maps
blind/new maps
```

Do not aggregate train replay into the generalization headline.

## 43. Metrics

```text
success regressions
success gains
both-success
both-fail
mean quality delta
median quality delta
trimmed mean
bootstrap CI
better/worse/ties
q90/q95 harmful tail
CVaR
runtime
expanded nodes
PIBT calls
per-family
per-density
per-budget
per-agent count
```

## 44. Research feasibility gate

The idea is supported for scale-up when:

```text
actual rich neural memorization succeeds;
leakage-free rich validation loss decreases with context count;
rich actors outperform scalar/global controls offline;
fixed solver replay trends improve with data/retraining;
success-regression tail is controlled;
oracle opportunity remains after noise calibration.
```

This is a research-continuation gate, not automatic runtime promotion.

## 45. Promotion gate

Keep the existing strict promotion requirements.

At minimum:

```text
zero supported success regressions
non-worse quality
confidence interval acceptable
exact materialization
physical-map-heldout evidence
actor-only deterministic export
```

---

# Part XI — Conditional independent-context expansion

## 46. Expansion is conditional

Do not expand merely because G5.63’s leaked scalar curve was labeled positive.

Expand only if the corrected E0/E1/E2 curve shows real improvement.

## 47. First expansion target

```text
2,000–3,000 independent valid contexts
at least 32 physical-map hashes
balanced morphology, density, budget, and OD regimes
```

Then rerun the same fixed scaling protocol.

## 48. Second expansion target

Only if the slope remains favorable:

```text
4,000–8,000 independent contexts
24–48 well-designed theta outcomes per context
selective replicates near safety/quality boundaries
```

## 49. Acquisition is not DAgger

Allowed contextual black-box acquisition:

```text
small residual neighborhoods around g556
verified positive-mode neighborhoods
positive/harmful boundary neighborhoods
underrepresented map morphologies
critic uncertainty
rich-vs-scalar disagreement
```

Forbidden:

```text
expert action labeling
learner trajectory imitation
PIBT action targets
```

---

# Part XII — Mandatory tests

## 50. Leakage tests

```text
test_scaling_features_exclude_positive_rows
test_scaling_features_exclude_harmful_rows
test_scaling_features_exclude_label_state
test_actor_inputs_are_pre_solver_only
test_export_schema_excludes_outcome_features
```

## 51. Loss tests

```text
test_softmin_oracle_floor_is_computed
test_floor_corrected_loss_zero_at_oracle
test_wta_loss_zero_at_selected_positive
test_nearest_harmful_not_diluted_by_far_harmful
test_adaptive_margin_is_geometrically_feasible
test_conflicting_near_duplicate_is_flagged
test_censored_is_not_negative
```

## 52. Optimizer tests

```text
test_parameter_oracle_uses_no_weight_decay
test_parameter_oracle_initializes_at_g556_or_requested_mode
test_projected_parameter_can_reach_solver_bounds
test_sigmoid_saturation_is_not_used_for_oracle_gate
```

## 53. Neural overfit tests

```text
test_rich_actor_memorizes_one_context
test_rich_actor_memorizes_four_contexts
test_graph_od_c0_f0_branches_receive_gradient
test_scalar_control_is_not_primary
test_od_shuffle_changes_prediction
test_c0_and_f0_interventions_have_effect
```

## 54. Scaling tests

```text
test_nested_subsets_are_identical_prefixes
test_validation_manifest_identical_across_sizes
test_physical_map_hashes_disjoint
test_scaling_uses_rich_actor
test_scaling_slope_uses_multiple_seeds
test_scaling_gate_rejects_label_leakage
```

## 55. Cycle tests

```text
test_replay_merge_changes_dataset_hash
test_retraining_changes_checkpoint_hash
test_retrained_manifest_lists_new_rows
test_fixed_panel_hash_unchanged
```

---

# Part XIII — Required artifacts

## 56. Truth and geometry

```text
outputs/reports/phase5p5_repair5g564_g563_truth_audit.md
outputs/reports/phase5p5_repair5g564_loss_geometry.md
outputs/reports/phase5p5_repair5g564_loss_geometry_summary.json
outputs/tables/phase5p5_repair5g564_loss_geometry_by_context.csv
outputs/tables/phase5p5_repair5g564_conflicting_theta_pairs.csv
```

## 57. Overfit

```text
outputs/reports/phase5p5_repair5g564_parameter_oracle_summary.json
outputs/reports/phase5p5_repair5g564_neural_memorization_summary.json
outputs/tables/phase5p5_repair5g564_loss_repair_matrix.csv
outputs/tables/phase5p5_repair5g564_overfit_by_context.csv
```

## 58. Scaling

```text
outputs/reports/phase5p5_repair5g564_rich_scaling_summary.json
outputs/tables/phase5p5_repair5g564_rich_scaling_results.csv
outputs/tables/phase5p5_repair5g564_rich_vs_scalar_by_fold.csv
outputs/reports/phase5p5_repair5g564_scaling_curve_fit.json
```

## 59. Merge and replay

```text
outputs/reports/phase5p5_repair5g564_replay_merge_summary.json
outputs/reports/phase5p5_repair5g564_true_cycle_summary.json
outputs/reports/phase5p5_repair5g564_fixed_solver_panel_summary.json
outputs/tables/phase5p5_repair5g564_fixed_solver_panel_pairs.csv
```

## 60. Final decision

```text
outputs/reports/phase5p5_repair5g564_decision.md
outputs/reports/phase5p5_repair5g564_decision_summary.json
outputs/reports/phase5p5_repair5g564_failure_attribution.md
```

---

# Part XIV — Completion policy

## 61. G5.64 is not complete after

```text
adding new classes
adding unit tests
rerunning the old tiny test
running only a per-context embedding
running only a scalar curve
creating an unexecuted lightweight actor
writing a failure summary after the first failed run
```

## 62. Minimum substantive completion

```text
1. truth-correct G5.63 scaling and tiny interpretations;
2. remove target leakage;
3. compute per-context oracle floors and conflict geometry;
4. execute the optimizer/loss repair matrix;
5. execute actual graph-actor memorization;
6. execute leakage-free rich scaling over nested context counts;
7. train at least E0 and E1 across multiple seeds;
8. merge existing exact replay rows into a new dataset;
9. retrain a genuinely new checkpoint;
10. run the fixed exact solver panel or document a rigorously justified gate block;
11. write final feasibility attribution.
```

If a stage fails, continue through its required diagnostic/repair branch rather than immediately declaring the whole round complete.

---

# Part XV — Decision vocabulary

```text
g564_g563_scaling_invalid_target_leakage
g564_g563_tiny_gate_invalid_loss_floor
g564_loss_geometry_audited
g564_labelv521_geometry_calibrated
g564_parameter_oracle_passed
g564_parameter_oracle_blocked_by_conflicting_labels
g564_neural_memorization_passed
g564_neural_memorization_failed_architecture_or_batching
g564_rich_scaling_positive
g564_rich_scaling_flat
g564_rich_actor_beats_scalar_control
g564_scalar_control_matches_rich_actor
g564_true_retraining_cycle_completed
g564_fixed_solver_panel_improves_with_data
g564_offline_scaling_solver_transfer_blocked
g564_feasibility_supported_expand_contexts
g564_feasibility_inconclusive_repair_labels
g564_feasibility_not_supported_keep_g556
```

---

# Part XVI — Literature-informed but mainline-preserving guidance

Recent learning-enhanced MAPF work supports several engineering principles that are relevant without changing this project’s task:

```text
LaGAT:
  lightweight graph attention can guide classical search when imperfect
  neural information is explicitly controlled.

GGO:
  real simulator outcomes and learned update models are meaningful supervision,
  but the simulator remains the final judge.

Graph-Transformer MAPF guidance:
  graph-native learned heuristics can generalize while preserving the classical
  planner as the execution backbone.

Multiple-hypothesis prediction:
  ambiguous supervision should preserve modes rather than average them.

Conservative objective modeling:
  a learned surrogate used for optimization should be pessimistic outside
  observed support.
```

These ideas may inform:

```text
attention efficiency
set-valued loss
critic conservatism
pretraining and fine-tuning
```

They must not introduce:

```text
agent action imitation
runtime neural control
selector deployment
solver semantic replacement
```

---

# Final question G5.64 must answer

```text
After removing label leakage and correcting the mathematical loss floor,
can the actual graph/paired-OD/C0/F0 attention actor memorize real set-valued
theta supervision and show a statistically credible improvement as the number
of independent MAPF contexts increases?
```

Only after this question is answered should the project commit to a large-scale context-generation campaign.

---

# Execution closure - 2026-06-20

G5.64 was executed on the RTX5090 instance `ackcs-00gjh6i6` inside tmux session
`g564_5090`.  The remote log was pulled back to:

```text
outputs/reports/phase5p5_repair5g564_5090_tmux.log
```

Executed gates:

```text
G5.63 truth audit:
  decision = g564_g563_scaling_invalid_target_leakage

Loss geometry:
  decision = g564_loss_geometry_audited
  contexts = 1000
  positive_contexts = 616
  conflicting_theta_pairs = 0

Projected parameter oracle:
  decision = g564_parameter_oracle_passed
  device = cuda
  contexts = 256
  median_best_total_repaired_loss = 0.0

Graph actor memorization:
  decision = g564_neural_memorization_passed
  device = cuda
  eligible_contexts = 51

Leakage-free rich scaling:
  decision = g564_rich_scaling_positive
  device = cuda
  sizes = 16, 32, 34
  seeds = 564, 565
  result_rows = 12
  rich_vs_scalar = g564_rich_actor_beats_scalar_control
  rich_beats_scalar_pair_win_rate = 1.0

True replay cycle:
  decision = g564_true_retraining_cycle_completed
  replay_merge_changes_dataset_hash = true
  retraining_changes_checkpoint_hash = true

Fixed solver panel:
  decision = g564_offline_scaling_solver_transfer_blocked
  new_g564_solver_panel_ran = false
```

Final decision:

```text
g564_offline_scaling_solver_transfer_blocked
```

Interpretation:

```text
The corrected G5.64 offline evidence chain is substantially healthier than
G5.63: leakage is removed, the loss floor is audited, the projected oracle
passes, the actual graph/OD/C0/F0 actor memorizes small real label sets, and
the leakage-free rich actor beats the scalar control across all paired folds.

The round still cannot open runtime, Phase-6, or AAAI claims because no fresh
G5.64 fixed exact solver panel was launched after selecting the leakage-free
actor.  The appropriate next gate is a fixed-panel solver transfer run using
the selected G5.64 actor checkpoint or export path.
```
