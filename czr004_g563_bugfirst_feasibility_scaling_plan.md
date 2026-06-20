# Repair5G.5.63 Plan — Bug-First Feasibility Proof, Set-Valued Real Labels, Data-Scaling Curves, and Efficient Goal-Aware Attention Actors

Project: `czr004`
Repository: `czr5454112-glitch/czr004`
Required branch: `server-code`
Source-of-truth start commit: `ea4cc94bb8ac3d8c0e72c40ccb3070d1fbf3fe3f`
Primary supported baseline: `g556_c063174`
Paper-faithful floor: `LaCAM* + additive LTM`
Round: `Repair5G.5.63 bug-first feasibility and scaling proof`

---

## 0. Executive decision

G5.63 keeps the current scientific mainline unchanged:

```text
one MAPF instance
  = physical graph topology
  + actual paired starts/goals
  + paired OD demand
  + directed C0 congestion/conflict prior
  + directed F0 goal-progress prior
  + solver budget
  + LTM iteration budget
        ↓
attention-based goal-aware dual-channel neural actor
        ↓
one bounded continuous UpdateParams theta
        ↓
theta is fixed for the complete solver run
        ↓
ordinary trace-driven C/F traffic maps continue to update online
```

The objective remains:

```text
replace the coarse hand-written additive LTM update configuration
with an instance-conditioned learned continuous parameter predictor,
and ultimately outperform paper-faithful LTM and the strong fixed g556 baseline.
```

G5.63 is not a direction change. It is a truth-repair and feasibility-proof round.

### 0.1 Priority order

The mandatory order is:

```text
1. repair code, label-adapter, split, logging, and cycle semantics;
2. prove the actor can learn the intended set-valued real-label problem;
3. measure whether validation loss improves as independent context count grows;
4. measure whether exact heldout solver replay improves with training data;
5. only then expand solver data and model capacity.
```

Do not reverse this order.

A larger server run must not conceal a broken target, mixed split, stale log, fake retraining cycle, or invalid learning curve.

### 0.2 Explicit non-DAgger contract

G5.63 is not DAgger.

Forbidden:

```text
expert action queries on learner-visited states
state-action imitation datasets
agent action decoders
learned PIBT priority actions
learned restart actions
learner/expert action mixing
trajectory-level behavior cloning
```

Allowed data object:

```text
(instance identity, continuous theta, unchanged solver conditions)
    -> real solver outcome
```

Sequential acquisition is contextual black-box experimental design over `theta`, not action imitation.

### 0.3 F6 representation floor remains permanent

The production main model may become more sophisticated, but it may not fall below:

```text
physical graph topology
+ actual paired starts/goals
+ paired OD tokens
+ directed C0 prior
+ directed F0 prior
+ solver budget
+ LTM iteration budget
```

Scalar summaries are supplemental only.

A scalar-only MLP remains a named control and can never be promoted as the primary `goal_aware_dual_channel_ltm` method.

---

# Part I — Source-of-truth interpretation of G5.62

## 1. What G5.62 genuinely established

G5.62 established all of the following:

```text
canonical solver-facing theta schema
real graph, OD, C0/F0 forward paths
real Label-v5.1 identity and scenario joins
real solver-derived positive/harmful/censored labels
exact materialization at server scale
three rich actor variants across three seeds
a training-only graph-conditioned outcome critic
18,200 exact-materialized actor candidate replay rows
real negative medians and better-than-worse signal in several replay panels
strict refusal to promote after success regressions / wide confidence intervals
```

These are meaningful advances.

G5.62 must not be summarized as a null result.

## 2. Why G5.62 is not a conclusive negative test

The principal actor training configuration was:

```text
real contexts available in graph dataset: 1,000
contexts containing at least one observed safe improvement: 616
actor train examples: 394
actor validation examples: 222
hidden dimension: 32
steps per actor: 100
batch size: 8
effective context presentations per actor: 800
approximate passes over 394 train contexts: ~2.0 epochs
```

Therefore G5.62 was a feasibility smoke, not a saturated training experiment.

It cannot answer whether a properly trained graph actor with thousands of independent contexts can beat g556.

## 3. Current replay signal

The strongest G5.62 cycle-3 row has approximately:

```text
method: A1 seed 562
pairs: 1,000
better / worse: 340 / 263
median quality delta vs g556: negative
mean quality delta vs g556: negative
success gains / regressions: 6 / 6
CI upper: positive
```

This is not promotable, but it is not random-looking failure either.

It suggests:

```text
context-conditioned theta signal exists,
but safety and tail calibration are unresolved.
```

The central question is now whether cleaner labels and more independent contexts produce a consistent learning curve.

---

# Part II — Mandatory G5.62 bug and evidence audit

## 4. P0 bug: safe-set averaging destroys multimodal semantics

Current code constructs:

```python
target = np.average(all_positive_safe_theta, weights=quality_weights)
```

This is invalid as the primary set-valued actor target.

Two distant safe modes can have an unsafe or poor arithmetic average.

Required repair:

```text
retain the complete positive safe set;
cluster or preserve separate modes;
train the one-output actor with a soft-min / energy objective to a safe mode;
never silently average distant theta modes.
```

Mandatory test:

```text
test_multimodal_safe_set_is_not_averaged
```

The test must construct separated safe modes and prove that the loss rewards approaching either mode rather than their midpoint.

## 5. P0 bug: positive-only actor dataset

Current actor loading drops every context without an observed positive target.

Consequences:

```text
the actor never learns verified harmful regions;
the actor never learns when evidence supports shrinking toward g556;
censored contexts disappear;
candidate coverage uncertainty is ignored;
the trust head receives no explicit supervision for unsupported instances.
```

Required repair:

Each context must remain in the actor dataset with a label state:

```text
POSITIVE_SUPPORTED
SAFE_NONIMPROVING_SUPPORTED
HARMFUL_SUPPORTED
CENSORED_UNKNOWN
MIXED_FRONTIER
```

The loss applied to each state differs.

Censored does not mean harmful.

No-positive-observed does not automatically mean g556 is the unique target.

## 6. P0 bug: G5.62 cycles were replay expansion, not learning cycles

The cycle-2 and cycle-3 wrappers only invoke replay with more contexts.

They do not:

```text
merge new outcomes into a versioned dataset;
rebuild safe/harmful/censored sets;
retrain an actor;
save a new checkpoint;
prove the checkpoint hash changed;
evaluate the new checkpoint on an untouched panel.
```

Therefore G5.62 did not execute:

```text
train -> replay -> ingest -> retrain
```

It executed:

```text
train once -> replay on 200 contexts
           -> replay the same checkpoints on 800 contexts
           -> replay the same checkpoints on 1,000 contexts
```

Mandatory G5.63 repairs:

```text
cycle N dataset manifest
cycle N checkpoint manifest
parent checkpoint hash
new-label row count
new independent context count
training source rows
checkpoint hash change
fixed evaluation panel
```

Mandatory tests:

```text
test_cycle2_dataset_contains_cycle1_new_rows
test_cycle2_checkpoint_differs_from_cycle1_checkpoint
test_cycle3_checkpoint_differs_from_cycle2_checkpoint
test_cycle_manifest_records_parent_and_training_rows
```

## 7. P0 bug: current logs do not form a valid learning curve

Current logged `loss` values are random minibatch losses from different batches.

They are not directly comparable across checkpoints.

The run does not record:

```text
full-train loss on a fixed evaluation subset
full-validation set loss at repeated checkpoints
loss terms separately
best checkpoint by validation
step-zero validation
epoch count
context presentations
```

Therefore statements such as “loss decreased with more data” are not currently supported.

Required logging:

```text
run_uid
dataset_version
dataset_sha256
split_manifest_sha256
model_config_sha256
checkpoint_step
epoch_float
context_presentations
fixed_train_eval_loss
fixed_validation_loss
positive_set_loss
harmful_margin_loss
risk_loss
trust_loss
censored_support_loss
theta variance
gradient norms
wall time
GPU utilization
```

Every progress file must be run-scoped, not globally appended without provenance.

## 8. P0 bug: stale / mixed progress provenance

The committed progress stream contains a critic start with 65,000 rows, while the final critic summary reports 16,000 rows.

This may reflect multiple runs appended to one file.

Required repair:

```text
one progress file per run UID
one final manifest linking the chosen run
no summary may infer scale from an unscoped mixed log
```

Mandatory test:

```text
test_summary_run_uid_matches_progress_run_uid
test_progress_dataset_count_matches_summary
test_stale_progress_rows_are_not_collected
```

## 9. P0 bug: heldout is merged with validation

Current actor evaluation uses:

```text
validation + heldout
```

as one model-selection set.

This destroys an untouched heldout claim.

Required split semantics:

```text
train:
  optimizer updates only

validation:
  checkpoint selection, hyperparameter choice, early stopping

heldout:
  exactly one post-freeze offline evaluation

blind solver panel:
  exact replay only after actor freeze
```

No physical map hash may overlap.

Current 24-map Label-v5.1 bank has too few heldout hashes for a strong single split. Use grouped physical-map cross-validation for feasibility, while reserving a separate blind subset for final replay.

## 10. P0 bug: replay panels mix train and non-train contexts

The replay wrappers use `preferred_split=any` and take the first sorted contexts.

This is valid for a development stress test, but not for a generalization claim.

Required outputs must distinguish:

```text
train-context replay
validation-map replay
heldout-map replay
new-map blind replay
```

Do not aggregate them into one headline.

## 11. P0 bug: sorted-UID truncation

`max_contexts` truncates a sorted UID list before stratified sampling.

This can distort:

```text
map family
physical map hashes
density
budget
agent count
positive/harmful/censored prevalence
```

Required repair:

Use deterministic, stratified, nested sampling with a manifest.

All scaling subsets must be nested:

```text
D64 ⊂ D128 ⊂ D256 ⊂ D512 ⊂ D1024 ...
```

## 12. P1 issue: oracle and replay means are outlier-sensitive

The current oracle includes a minimum quality delta near `-94`.

Some cycle means are much more negative than their medians.

Required audit:

```text
raw ratio values
finite denominator checks
winsorized diagnostics
median
trimmed mean
q05/q25/q50/q75/q90/q95/q99
CVaR of harmful tail
per-context cap diagnostics
```

Do not replace the official metric, but report robust statistics alongside it.

## 13. P1 issue: low output variance

Several rich actors have very small heldout theta variance.

This may indicate:

```text
near-global-theta collapse
weak instance conditioning
overly strong averaging target
insufficient training signal
```

Required audit:

```text
per-field variance
between-map variance
within-map assignment variance
paired-goal shuffle effect
C0-only intervention effect
F0-only intervention effect
budget intervention effect
nearest-global-theta distance
```

Passing a nonzero sensitivity threshold alone is insufficient; report effect size relative to natural output variation.

## 14. P1 issue: loss matrix misnames the actual objective

The committed loss matrix calls the actor objective:

```text
real_positive_safe_set_weighted_l1
```

But implementation first averages the positive set and then applies point L1.

After repair, artifact names must match executable semantics.

---

# Part III — Label-v5.2 set-valued training contract

## 15. Label-v5.2 is an adapter repair, not a new solver label source

Label-v5.1 identity and real solver outcomes remain valuable.

G5.63 should create a versioned actor/critic training adapter:

```text
Label-v5.2-set
```

It must preserve every original real row and add set/censoring semantics.

## 16. Per-context label object

For each evaluation context `x`, construct:

```text
S_pos(x):
  verified safe-improving theta rows

S_safe(x):
  verified safe but not necessarily improving theta rows

U_reg(x):
  success-regression theta rows

U_quality(x):
  both-success but materially worse theta rows

C_unknown(x):
  non-comparable / censored rows

B(x):
  g556 baseline outcome

coverage(x):
  candidate-space coverage descriptors

noise(x):
  available replicate / local-margin estimates
```

## 17. Never average the safe set

The actor emits one theta:

```text
theta_hat(x)
```

Use mode-seeking set loss:

```text
d_j = normalized distance(theta_hat, theta_j)

L_positive =
  -tau * log sum_j w_j exp(-d_j / tau)
```

Alternative allowed formulations:

```text
mixture energy
cluster-medoid softmin
contrastive safe-mode loss
nearest verified Pareto mode
```

Forbidden:

```text
arithmetic mean of distant safe theta modes
single arbitrary candidate ID classification
```

## 18. Harmful repulsion

For verified harmful candidates:

```text
L_harm =
  mean max(0, margin - distance(theta_hat, harmful_theta))
```

Weight success regressions more strongly than mild quality losses.

Do not use only a pull-to-g556 repair.

## 19. Censored contexts

For `C_unknown`:

```text
do not label as harmful;
do not hard-target g556;
do not invent a positive theta.
```

Allowed supervision:

```text
small trust-region regularization
critic uncertainty penalty
support-distance penalty
consistency loss
```

A context becomes `VERIFIED_NO_POSITIVE` only if candidate coverage and replicated evidence meet an explicit threshold.

## 20. Baseline shrinkage

The actor may learn continuous shrinkage:

```text
theta_hat = g556 + trust(x) * delta(x)
```

But `trust(x)` must be learned from real support/risk evidence.

It must not be a disguised discrete selector.

## 21. Quality margins and noise

A tiny negative delta close to solver noise should not define a strong positive mode.

Estimate a development margin from:

```text
replicated g556 rows
replicated theta rows on a stratified subset
same-context reruns
```

Label:

```text
clear improvement
tie / noise band
clear degradation
success gain
success regression
censored
```

## 22. Required Label-v5.2 tests

```text
test_identity_rows_are_losslessly_preserved
test_positive_set_is_not_averaged
test_censored_is_not_negative
test_success_regression_is_harmful
test_quality_loss_masks_noncomparable
test_noise_band_creates_tie
test_no_positive_observed_is_not_automatically_verified_noop
test_context_total_weight_is_balanced
test_candidate_rows_do_not_count_as_independent_contexts
```

---

# Part IV — First prove basic learnability

## 23. Tiny-overfit contract

Before any large training job, run exact overfit tests.

### 23.1 Single-context positive-mode overfit

Select contexts with:

```text
at least 4 clear positive safe theta
at least 4 harmful theta
nontrivial separated modes
valid graph / OD / C0 / F0
```

Require:

```text
positive-set distance decreases strongly
harmful margin violations decrease
actor output reaches one verified safe mode
no midpoint averaging
```

### 23.2 Multi-context overfit

Use:

```text
8, 16, 32 contexts
```

Require the rich actor to fit context-dependent modes substantially better than:

```text
one global learned theta
scalar-only MLP
always g556
```

### 23.3 Intervention overfit

Create pairs with:

```text
same map, changed paired goals
same starts/goals sets, shuffled pairing
same topology, changed C0/F0 demand
same demand, changed budget
```

Require distinguishable theta predictions.

If tiny overfit fails, do not collect more data. Repair architecture, batching, loss, or targets first.

---

# Part V — Controlled loss-vs-data scaling experiment

## 24. What “loss decreases with more data” must mean

It does not mean:

```text
random minibatch loss at step 100 < random minibatch loss at step 1
```

It means:

```text
on one fixed, untouched physical-map validation suite,
the same model/training protocol achieves lower full validation loss
as the number of independent training contexts increases.
```

## 25. Nested dataset sizes

On the repaired current bank, start with:

```text
64
128
256
512
all available train contexts
```

After expanding the bank:

```text
1,000
2,000
4,000
8,000 independent train contexts
```

The unit is an independent MAPF context, not candidate rows.

## 26. Split protocol

Use grouped physical-map folds.

Recommended feasibility protocol:

```text
5-fold group cross-validation over physical_map_sha256
3 training seeds per fold for the two main architectures
1 scalar control seed per fold initially
```

For expensive solver replay, reserve one fixed map-heldout panel not touched by model or hyperparameter selection.

## 27. Equalized optimization

Do not compare data sizes with a fixed 100-step budget.

Use either:

```text
fixed epochs / context presentations
```

or both:

```text
A. fixed epochs to measure statistical scaling
B. fixed optimizer tokens to measure compute scaling
```

Recommended first pass:

```text
minimum 30 epochs
maximum 150 epochs
validation every epoch
early stop patience >= 15 epochs
save best validation checkpoint
```

Record exact context presentations.

## 28. Loss components

For every epoch:

```text
train positive-set loss
validation positive-set loss
train harmful-margin loss
validation harmful-margin loss
risk/quality loss
censored support penalty
trust magnitude
theta output variance
global-theta regret
scalar-control regret
```

## 29. Scaling-curve analysis

Fit diagnostics such as:

```text
L(N) = A * N^(-b) + C
```

Report:

```text
slope b
bootstrap CI of b
loss at each N
seed variance
fold variance
rich-vs-scalar gap
rich-vs-global-theta gap
```

Do not force a power-law claim if the data do not support it.

## 30. Feasibility gates

### Gate F0 — code truth

All P0 bugs repaired and tests pass.

### Gate F1 — overfit truth

Rich actor can overfit real set-valued contexts without midpoint averaging.

### Gate F2 — representation value

At matched data and compute:

```text
rich actor validation loss < scalar control validation loss
```

on a majority of physical-map folds.

### Gate F3 — data scaling

Across at least three increasing context sizes:

```text
median validation set loss decreases
or
heldout safe-frontier regret decreases
```

with a positive scaling slope.

### Gate F4 — fixed replay trend

On the same frozen replay suite, checkpoints trained on larger datasets show:

```text
non-increasing success regressions
improving median quality delta
improving better/worse balance
shrinking harmful q90/q95 tail
```

### Gate F5 — research continuation

If F1–F4 pass, expand data.

If F1 fails, repair implementation.

If F1 passes but F2 fails, rich representation is not yet adding value.

If F2 passes but F3 is flat, label noise or candidate coverage is the likely bottleneck.

If offline F3 passes but replay F4 fails, solver-transfer/tail calibration is the bottleneck.

---

# Part VI — Use the existing 18,200 exact replay rows correctly

## 31. Merge, do not merely report

The 18,200 exact rows must be converted into a versioned additional label source.

Required:

```text
replay row -> exact context identity
replay row -> exact generated theta
replay row -> g556 paired outcome
replay row -> Label-v5.2 state
```

Report:

```text
new unique contexts
new positive contexts
new harmful contexts
new censored contexts
new theta coverage
overlap with original candidate slate
```

## 32. True cycle semantics

A valid cycle is:

```text
dataset_v0
  -> train actor_v0
  -> freeze actor_v0
  -> exact solver replay
  -> label new rows
  -> build dataset_v1
  -> train actor_v1
  -> freeze actor_v1
  -> evaluate on unchanged heldout panel
```

Mandatory proof:

```text
dataset_v1 hash != dataset_v0 hash
actor_v1 checkpoint hash != actor_v0 checkpoint hash
new replay rows are listed in actor_v1 training provenance
heldout panel hash is unchanged
```

## 33. Do not use all new rows indiscriminately

Balance by context.

One context with many theta evaluations must not dominate the graph encoder.

Use:

```text
context-balanced batches
positive/harmful/censored stratification
multiple theta rows per sampled context
```

---

# Part VII — Efficient attention architecture on one RTX5090

## 34. Current model is not too large

The current hidden-32 dual-stream actor is roughly a `0.1M`-parameter model.

The main resource problem is not parameter count.

Likely inefficiencies include:

```text
Python loop over every destination node in edge softmax
three separate GraphGPS encoders
dense per-graph global attention over every grid node
rebuilding graph/traffic tensors repeatedly
small batch sizes
CPU-bound data preparation
```

Do not make the network smaller solely because training took about two hours.

## 35. Architecture comparison after bug repair

Train three matched actors:

### E0 — repaired current A1

```text
three streams:
topology / C0 / F0
pooled fusion
hidden 64 or 96
```

### E1 — lightweight edge-aware attention actor

Inspired by the efficiency principles of graph-attention MAPF work, but retaining our theta target:

```text
one shared sparse topology backbone
edge-conditioned GATv2-style local attention
learned channel embeddings for C0 and F0
3–4 local sparse layers
attention pooling to graph tokens
paired-OD Set Transformer
OD-to-graph cross-attention
field-group continuous theta head
```

Target size:

```text
0.2M–1.5M parameters
```

No action decoder.

### E2 — cross-attention actor

```text
current A2 concept
with repaired labels, larger hidden dimension, and efficient tensorization
```

Optional only after F1/F2:

### E3 — hierarchical graph actor

```text
full-grid local encoder
corridor/junction graph tokens
OD-to-corridor cross-attention
C/F channel fusion
```

## 36. Efficiency engineering

Required profiling:

```text
parameter count
VRAM peak
GPU utilization
CPU utilization
examples/sec
nodes/sec
edges/sec
data-loading time
forward time
backward time
```

Required engineering options:

```text
vectorized segment softmax
torch.scatter_reduce / PyG scatter when stable
cached graph tensors
cached traffic tensors
bucketing by graph size
gradient accumulation
bf16
torch.compile only if validated
sparse or token-level global attention
```

A faster lightweight attention model is useful only if it preserves the F6 information floor.

---

# Part VIII — Data sufficiency strategy

## 37. Current effective data is small

The actor’s effective sample size is the number of independent contexts, not the number of theta rows.

Current primary supervision:

```text
394 positive train contexts
```

is insufficient to draw a saturation conclusion.

## 38. Expansion order

Do not jump directly to millions of rows.

### Expansion A

After F0–F3 on existing data:

```text
at least 2,000 independent valid train contexts
at least 24 train physical-map hashes
at least 8 validation hashes
at least 8 heldout/blind hashes
```

### Expansion B

If scaling remains positive:

```text
4,000–8,000 independent train contexts
24–48 theta outcomes per context
balanced across map morphology, density, budget, and demand
```

The target is independent context diversity first.

## 39. Contextual theta acquisition, not DAgger

Acquire real outcomes from:

```text
small residuals around g556
verified positive-frontier neighborhoods
harmful boundary neighborhoods
underrepresented morphologies
high uncertainty in the theta response surface
disagreement between rich actor and scalar/global controls
```

Do not collect agent actions.

## 40. Replicate allocation

Use solver replicates selectively for:

```text
near-zero quality differences
success boundaries
high-impact claimed gains
promotion candidates
```

Replicate information should define noise margins and confidence, not merely increase row count.

---

# Part IX — Fixed solver feasibility panels

## 41. Panel P0 — current-data feasibility

Use one fixed validation-map suite.

Compare checkpoints trained with:

```text
N=64,128,256,512,all-current
```

Methods:

```text
g556
paper-faithful additive LTM
global learned theta
scalar actor
E0 rich actor
E1 lightweight attention actor
E2 cross-attention actor
```

## 42. Panel P1 — post-merge feasibility

After merging 18,200 exact rows and retraining:

```text
actor_v0 vs actor_v1
same contexts
same seeds
same budgets
same baseline
```

## 43. Panel P2 — expanded-data heldout

Only after positive scaling:

```text
new physical maps
new start-goal assignments
frozen actor
no threshold tuning
```

## 44. Required metrics

```text
success regressions
success gains
both-success count
both-fail count
mean quality delta
median quality delta
trimmed mean
bootstrap CI
better / worse / ties
q90 / q95 harmful tail
CVaR
expanded nodes
PIBT calls
runtime
per-map family
per-density
per-budget
per-agent count
```

## 45. Idea-feasibility interpretation

Evidence supporting the idea:

```text
real oracle opportunity exists;
rich actor overfits real set labels;
rich actor beats scalar/global controls offline;
validation loss improves with independent context count;
fixed-panel replay improves with data size;
success-regression tail shrinks with conservative training.
```

Evidence against the current formulation:

```text
after bug repair, overfit fails;
rich representation never beats scalar/global controls;
validation loss is flat across a substantial data range;
fixed replay does not improve with data despite offline improvement;
oracle opportunity disappears after noise/replicate correction.
```

Do not declare the entire research idea impossible from a 394-context, two-epoch smoke.

---

# Part X — Required implementation structure

## 46. Recommended new modules

```text
src/gcst/
  label_v52_set.py
  set_valued_actor_losses.py
  scaling_dataset.py
  light_edge_attention_actor.py
  run_provenance.py
  replay_label_merge.py
```

## 47. Recommended scripts

```text
scripts/
  audit_repair5g563_g562_code_truth.py
  build_repair5g563_labelv52_set_dataset.py
  run_repair5g563_tiny_overfit.py
  run_repair5g563_scaling_study.py
  merge_repair5g563_exact_replay_labels.py
  train_repair5g563_attention_actors.py
  run_repair5g563_fixed_feasibility_panel.py
  profile_repair5g563_attention_models.py
  write_repair5g563_decision.py
```

## 48. Required tests

```text
test_multimodal_safe_set_is_not_averaged
test_positive_only_filter_removed
test_censored_context_retained
test_censored_is_not_harmful
test_verified_noop_requires_coverage
test_train_validation_heldout_hashes_disjoint
test_heldout_not_used_for_checkpoint_selection
test_replay_panel_excludes_train_hashes
test_nested_scaling_subsets
test_fixed_validation_examples_identical_across_scales
test_epoch_loss_uses_fixed_examples
test_run_uid_provenance
test_progress_count_matches_summary
test_cycle2_ingests_cycle1_rows
test_cycle2_checkpoint_hash_changes
test_context_balanced_sampling
test_rich_actor_requires_graph_od_c0_f0
test_scalar_actor_is_control_only
test_exact_materialization_contract_stays_at_1
test_actor_export_excludes_critic_and_codebook
```

---

# Part XI — Server execution policy

## 49. Phase ordering on RTX5090

Run under tmux.

### Phase 0 — bug audit and unit tests

No large solver job.

### Phase 1 — Label-v5.2 build

No large solver job.

### Phase 2 — tiny overfit

Stop and repair if it fails.

### Phase 3 — current-data scaling curves

Run nested context sizes and three seeds.

### Phase 4 — fixed feasibility panel

Only selected checkpoints.

### Phase 5 — merge existing 18,200 replay rows

Retrain and rerun the same panel.

### Phase 6 — conditional data expansion

Only if the scaling slope and replay trend justify it.

## 50. No premature completion

G5.63 is not complete after:

```text
writing wrappers
adding tests only
creating a dataset manifest
training one model
showing nonzero gradients
showing one negative median
replaying the same checkpoint on more contexts
```

Minimum substantive completion:

```text
all P0 bugs repaired;
Label-v5.2 set semantics implemented;
tiny overfit evidence;
nested loss-vs-context scaling curves;
rich-vs-scalar comparison;
true replay-label merge and retraining;
fixed-panel exact solver comparison;
final feasibility attribution.
```

---

# Part XII — Decision labels

```text
g563_g562_target_averaging_bug_confirmed
g563_g562_cycle_not_retraining_confirmed
g563_g562_loss_curve_not_identifiable
g563_labelv52_set_dataset_ready
g563_tiny_overfit_failed_repair_model_or_loss
g563_tiny_overfit_passed
g563_validation_loss_scales_with_context_count
g563_validation_loss_flat_label_or_representation_blocker
g563_rich_actor_beats_scalar_control
g563_rich_actor_not_better_than_scalar_control
g563_true_cycle_retraining_completed
g563_fixed_replay_improves_with_data
g563_offline_scales_but_solver_transfer_fails
g563_feasibility_supported_continue_scaleup
g563_feasibility_not_supported_keep_g556
```

---

# Final question

G5.63 must answer, with auditable evidence:

```text
After repairing set-valued targets, censored-label semantics, data splits,
run provenance, and true retraining cycles, does a goal-aware graph-attention
actor become more accurate and safer as the number of independent real
MAPF contexts increases?
```

Only after this question is answered should the project decide how much more solver data or model capacity to purchase.

---

# Execution closure - 2026-06-20

## Implemented G5.63 repair layer

New code:

```text
src/gcst/label_v52_set.py
src/gcst/set_valued_actor_losses.py
src/gcst/scaling_dataset.py
src/gcst/run_provenance.py
src/gcst/replay_label_merge.py
src/gcst/light_edge_attention_actor.py
```

New scripts:

```text
scripts/build_repair5g563_labelv52_set_dataset.py
scripts/run_repair5g563_tiny_overfit.py
scripts/run_repair5g563_scaling_study.py
scripts/write_repair5g563_decision.py
```

New tests:

```text
tests/test_repair5g563_labelv52_set.py
```

The implemented adapter preserves original real Label-v5.1 rows, creates
Label-v5.2 set states, keeps censored rows as unknown rather than negative,
keeps candidate rows separate from independent context count, prevents
safe-set averaging, creates grouped physical-map splits, creates nested
scaling subsets, and writes run-scoped progress files.

## RTX5090 execution

Server:

```text
instance: ackcs-00gjh6i6
host: ssh.bj8.bz1.paratera.com:2233
gpu: NVIDIA GeForce RTX 5090, 32607 MiB
tmux sessions: g563_5090, g563_tiny_long
context dir: /root/shared-nvme/czr004_g559_remote_artifacts/contexts
```

Commands were run under tmux.  The first tmux attempt used the default
`outputs/external/...` context path and correctly failed with zero local
scenario files.  The successful run used the shared-nvme context path above.

Primary artifacts pulled back:

```text
outputs/reports/phase5p5_repair5g563_decision_summary.json
outputs/reports/phase5p5_repair5g563_labelv52_set_dataset_summary.json
outputs/reports/phase5p5_repair5g563_tiny_overfit_summary.json
outputs/reports/phase5p5_repair5g563_scaling_study_summary.json
outputs/tables/phase5p5_repair5g563_labelv52_context_manifest.csv
outputs/tables/phase5p5_repair5g563_labelv52_candidate_manifest.csv
outputs/tables/phase5p5_repair5g563_scaling_study_results.csv
```

## Evidence summary

Code-truth and Label-v5.2 dataset gate:

```text
decision: g563_labelv52_set_dataset_ready
contexts: 1000
candidate rows: 65000
positive contexts: 616
harmful contexts: 620
censored contexts: 380
mixed-frontier contexts: 604
dataset sha256: b93f715c4e766d92b7da1db9165fe6edfb6ae0fad6af840fcc5796b71df8ca05
grouped split hashes disjoint: true
nested scaling subsets: true
```

Tiny-overfit gate:

```text
decision: g563_tiny_overfit_failed_repair_model_or_loss
device: cuda
contexts: 32
steps: 2000
initial loss: 0.1267247200012207
final loss: 0.08067557215690613
minimum loss: 0.08063578605651855
loss reduction fraction: 0.3633793615316017
positive set is not averaged: true
```

Interpretation: the mode-seeking objective itself passes the midpoint
diagnostic, but the 32-context real set-valued overfit plateaus well above the
strict F1 gate.  The blocker is therefore not stale logging or safe-set
averaging; it is likely conflicting Label-v5.2 support geometry, harmful-margin
weighting, target coverage, or the current simple overfit parameterization.

Nested scaling gate:

```text
decision: g563_validation_loss_scales_with_context_count
device: cuda
train contexts available: 643
fixed validation contexts: 213
fixed validation manifest sha256: ab6ea31284197d361252d8419056ece31275ad0d85f7eeec9c9e4c024fdee37a
rows: 12
sizes: 64, 128, 256, 512
median best validation loss:
  64:  0.028361642733216286
  128: 0.027901289984583855
  256: 0.02779296226799488
  512: 0.02782842330634594
```

Interpretation: validation loss improves from 64 to 256 independent contexts
and remains better than 64 at 512, but the 512 median slightly regresses from
256.  This is positive but not sufficient to override the failed tiny-overfit
gate.

## Final G5.63 decision

```text
decision: g563_tiny_overfit_failed_repair_model_or_loss
code truth gate: true
tiny overfit gate: false
scaling gate: true
claims opened: none
```

Do not expand solver data or promote a learned actor yet.  The next round
should debug F1 first: audit positive/harmful distances inside mixed-frontier
contexts, relax or calibrate harmful margins from replicate/noise estimates,
separate impossible conflicting contexts from clean overfit contexts, and then
rerun 8/16/32-context rich-actor overfit before any fixed solver replay claim.
