# Repair5G.5.65 — Unified Repaired-Loss Rich Actor, Matched-Control Scaling, Fresh Solver Transfer, and Context Expansion

Project: `czr004`
Repository: `czr5454112-glitch/czr004`
Required branch: `server-code`
Source-of-truth start commit: `92758c071e256f79aacc96cd403168f003aa1e6f`
Primary supported baseline: `g556_c063174`
Paper-faithful floor: `LaCAM* + additive LTM`
Round: `Repair5G.5.65`

---

# 0. Executive mandate

G5.65 keeps the scientific direction unchanged:

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
theta is fixed for the entire solver run
        ↓
ordinary trace-driven C/F traffic maps continue updating online
```

The research target remains:

```text
replace the coarse hand-designed additive LTM update configuration
with an instance-conditioned learned continuous theta predictor,
and outperform paper-faithful LaCAM*+LTM;
the stronger target is also to outperform the optimized fixed global
baseline g556_c063174.
```

The final method must not become:

```text
a selector over candidate IDs
a nearest-neighbor theta retriever
a map-ID lookup
an agent action policy
a PIBT priority policy
a learned restart policy
a runtime checkpoint policy
a critic-dependent deployment method
a scalar-only production model
```

The final inference contract remains:

```text
one actor forward
-> one continuous theta
-> no codebook
-> no critic
-> no candidate enumeration
-> no runtime theta switching
```

G5.65 is a combined:

```text
bug repair
+ strict feasibility proof
+ fresh solver transfer
+ conditional independent-context expansion
```

round.

---

# 1. Source-of-truth interpretation of G5.64

## 1.1 What G5.64 genuinely proved

G5.64 established useful facts:

```text
G5.63 scalar scaling contained target leakage and was correctly reclassified
the Label-v5.2 set representation remains usable
a floor-corrected/adaptive parameter-oracle objective can be optimized
real graph/OD/C0/F0 branches receive gradients
real rich actor predictions react to OD/C0/F0 interventions
a replay-row merge changes the dataset hash
a retraining command can produce a different checkpoint hash
no fresh solver panel was falsely claimed
```

This is good engineering evidence.

## 1.2 Why G5.64 does not yet prove rich-actor scaling

The committed rich-scaling run used:

```text
contexts loaded: 62
train contexts available: 34
fixed validation contexts: 8
actual train sizes: 16, 32, 34
seeds: 564, 565
steps: 30
one physical-map split
one rich architecture
```

The rich median validation loss changed only approximately:

```text
N=16: 0.109687
N=32: 0.109236
N=34: 0.109199
```

This is roughly a 0.45% first-to-last reduction.

It is a weak directional probe, not statistically credible scaling evidence.

## 1.3 Rich-vs-scalar comparison was anchor-confounded

The rich actor uses a residual parameterization around g556:

```text
theta = g556 + trust * scale * tanh(delta)
```

The scalar control uses:

```text
theta = lo + sigmoid(raw) * (hi - lo)
```

and therefore begins near the midpoint of the full solver bounds.

Their initial validation losses were approximately:

```text
rich:   0.109
scalar: 0.204
```

The reported 100% paired rich-vs-scalar wins therefore largely compare:

```text
g556-anchored initialization
against
full-bounds midpoint initialization
```

rather than graph representation against scalar representation.

All controls in G5.65 must use a matched output parameterization and matched initialization.

## 1.4 The oracle and rich actor optimize different losses

The parameter oracle uses:

```text
floor-corrected positive loss
nearest-harmful repulsion
adaptive harmful margin
g556 anchoring for unsupported contexts
```

The rich actor training still imports and uses the older:

```text
set_valued_actor_loss
```

with:

```text
raw normalized softmin
mean harmful hinge
fixed harmful margin
```

Therefore:

```text
parameter-oracle pass
```

and:

```text
rich memorization/scaling pass
```

do not currently refer to the same mathematical objective.

This is the highest-priority G5.65 bug.

## 1.5 Parameter-oracle pass is partly trivial

The G5.64 parameter oracle reports:

```text
256 contexts
132 contexts improved
median initial repaired loss ~= 0.000325
median best repaired loss = 0
```

Many contexts already have zero repaired loss at g556.

A median over all contexts therefore cannot prove learnability on opportunity contexts.

G5.65 must separate:

```text
TRIVIAL_G556_OPTIMAL
NONTRIVIAL_OPPORTUNITY
MIXED_SAFETY_BOUNDARY
UNSUPPORTED_CENSORED
HARMFUL_ONLY
```

The central feasibility question is performance on `NONTRIVIAL_OPPORTUNITY` and `MIXED_SAFETY_BOUNDARY`.

## 1.6 Neural memorization gate was too weak

The G5.64 neural memorization test trained only:

```text
1 context
4 contexts
80 steps
one model
one seed
```

The gate passed whenever final loss was merely lower than initial loss.

Observed results were approximately:

```text
1 context: 0.13793 -> 0.12547
4 contexts: 0.13915 -> 0.10321
```

This proves gradients and some fitting signal.

It does not prove that the neural actor approaches the per-context oracle or memorizes 8/16/32 distinct context-conditioned modes.

## 1.7 The “true cycle” was a scalar smoke

The G5.64 true-cycle artifact trained:

```text
scalar control
32 examples
12 steps
no fixed heldout comparison
```

It proves pipeline plumbing only.

It does not prove that a rich graph actor improves after ingesting replay outcomes.

## 1.8 No fresh solver transfer was executed

The G5.64 fixed solver table is a copied subset of an older G5.62 panel.

The artifact explicitly records:

```text
new_g564_solver_panel_ran = false
```

Therefore the next scientific gate is a fresh exact-materialized solver panel.

---

# 2. G5.65 priority order

The mandatory order is:

```text
A. truth-correct G5.64 weak gates;
B. unify oracle and actor losses;
C. build matched controls and common g556 initialization;
D. audit and repair C0/F0 representation semantics;
E. run strong actual neural memorization;
F. run statistically credible current-bank rich scaling;
G. merge all usable exact replay labels and retrain rich actors;
H. run fresh fixed solver transfer;
I. repair trust/tail risk if transfer fails;
J. expand independent contexts if trend is credible;
K. retrain and rerun the same fixed panels.
```

Do not start a massive data sweep before A–F.

Do not stop after A–F without executing a fresh solver panel unless a hard materialization or data-integrity blocker is demonstrated.

---

# 3. P0 truth audit and governance repair

## 3.1 Required G5.64 reinterpretation

Write a source-of-truth audit with fields:

```text
g564_parameter_oracle_loss = repaired floor-corrected objective
g564_rich_actor_loss = old G5.63 objective
g564_oracle_actor_loss_parity = false
g564_neural_memorization_context_sizes = [1,4]
g564_neural_memorization_strong_gate = false
g564_rich_scaling_train_contexts = 34
g564_rich_scaling_validation_contexts = 8
g564_rich_scaling_seeds = 2
g564_rich_scaling_folds = 1
g564_rich_scaling_steps = 30
g564_rich_vs_scalar_output_parameterization_matched = false
g564_rich_scaling_statistically_supported = false
g564_true_cycle_model = scalar
g564_true_cycle_rich_actor = false
g564_new_solver_panel_ran = false
```

The historical G5.64 result should be preserved but reworded as:

```text
promising underpowered offline probe;
not yet a strict rich-actor feasibility pass.
```

## 3.2 Decision gates must inspect evidence, not decision strings

Do not write:

```python
gate = summary["decision"] == "pass_string"
```

without checking quantitative fields.

Each gate must directly validate:

```text
context counts
seed counts
fold counts
training epochs
loss-config hash
matched initialization
checkpoint existence
checkpoint hash uniqueness
validation manifest hash
exact solver row counts
materialization rates
success regressions
quality metrics
```

## 3.3 Minimum unit-test additions

```text
test_g564_rich_scaling_reclassified_underpowered
test_g564_scalar_control_anchor_mismatch_detected
test_g564_oracle_actor_loss_mismatch_detected
test_g564_true_cycle_scalar_not_rich
test_g564_fixed_panel_is_not_new_solver_evidence
```

---

# 4. One canonical repaired differentiable loss

## 4.1 Single source of truth

Create:

```text
src/gcst/repaired_set_risk.py
```

It must implement both:

```text
NumPy evaluation
PyTorch differentiable evaluation
```

from one shared configuration schema.

All of these must use the same configuration:

```text
parameter oracle
neural memorization
scalar/global controls
rich actor training
scaling evaluation
checkpoint selection
replay-label retraining
offline reports
```

## 4.2 Required loss configuration

The canonical risk must support:

```text
positive loss:
  floor-corrected softmin
  hard WTA
  clustered-medoid WTA

harmful loss:
  nearest-harmful hinge
  top-k/CVaR hinge
  adaptive-margin hinge

unsupported/censored loss:
  weak support term
  weak continuous shrinkage prior
  no fake harmful label

safe-nonimproving loss:
  support preservation
  calibrated g556 shrinkage

optional critic term:
  cross-fitted training-only conservative risk
```

## 4.3 Default primary loss for G5.65

Recommended primary:

```text
positive:
  clustered-medoid WTA or floor-corrected softmin

harmful:
  nearest/top-k adaptive-margin hinge

censored:
  weak support + trust regularization

total:
  context-balanced mean
```

Do not average candidate rows globally.

## 4.4 Strict parity tests

```text
test_numpy_torch_repaired_loss_parity
test_parameter_oracle_and_actor_share_loss_config_sha
test_scaling_and_memorization_share_loss_config_sha
test_checkpoint_records_loss_config_sha
test_floor_corrected_loss_is_zero_at_oracle_mode
test_nearest_harmful_not_diluted_by_distant_harmful
test_adaptive_margin_is_feasible
test_censored_context_has_no_harmful_gradient
```

## 4.5 Real loss ablation matrix

The file called `loss_repair_matrix.csv` must actually contain configurations.

At minimum compare:

```text
P1 + H1
P1 + H2
P2 + H1
P2 + H2
P3 + H1
P3 + H2
```

where:

```text
P1 = floor-corrected softmin
P2 = hard WTA
P3 = clustered-medoid WTA
H1 = nearest adaptive harmful
H2 = top-k/CVaR adaptive harmful
```

Run on a fixed set of nontrivial contexts.

Report:

```text
oracle excess
mode capture
harmful violation
optimization stability
runtime
```

---

# 5. Opportunity-aware label and metric contract

## 5.1 Context categories

For each context compute:

```text
L_g556
L_oracle
oracle_gap = L_g556 - L_oracle
positive mode count
harmful boundary distance
candidate coverage
censoring rate
```

Assign:

```text
TRIVIAL_G556_OPTIMAL:
  oracle_gap <= epsilon

NONTRIVIAL_OPPORTUNITY:
  oracle_gap > epsilon and positive support exists

MIXED_SAFETY_BOUNDARY:
  positive support exists and harmful theta is nearby

UNSUPPORTED_CENSORED:
  insufficient comparable support

HARMFUL_ONLY:
  verified harmful but no verified positive
```

## 5.2 Primary normalized regret

For opportunity contexts:

```text
normalized_oracle_regret =
  (L_actor - L_oracle)
  / max(L_g556 - L_oracle, epsilon)
```

Interpretation:

```text
1.0 = no better than g556
0.0 = reaches oracle
<0 = better than observed oracle under current surrogate
```

Report raw loss too.

## 5.3 No-op preservation

For trivial/unsupported contexts report:

```text
distance_to_g556
predicted trust
harmful violation
false-deviation rate
```

The actor must learn:

```text
change theta where opportunity is supported;
remain near g556 where evidence is weak.
```

This remains one continuous theta output.

## 5.4 Noise margin calibration

G5.63/G5.64 used `quality_margin=0`.

G5.65 must estimate a nonzero tie/noise margin from fresh paired diagnostic rows or robust discrete-cost resolution.

Run a compact panel on:

```text
g556
one verified positive
one near-boundary harmful
one actor output
```

across multiple solver RNG seeds when supported, while holding map and scenario fixed.

Report:

```text
success stability
quality delta variance
median absolute deviation
recommended positive margin
recommended harmful margin
```

Do not call this DAgger.

It remains black-box evaluation of `(instance, theta)`.

---

# 6. Matched controls

## 6.1 Common output parameterization

All controls and rich actors must use:

```text
raw_delta = head(embedding)
trust = sigmoid(trust_head(embedding))
theta = clamp(
    g556 + trust * field_scale * tanh(raw_delta)
)
```

Initialize final delta heads to zero.

At step zero:

```text
all models output exactly g556
```

or the same numerically documented epsilon-neighborhood.

## 6.2 Required controls

```text
B0: always g556
B1: one learned global residual theta
B2: scalar pre-solver residual actor
E0: repaired current dual-stream actor
E1: lightweight shared-backbone edge-attention actor
E2: OD-to-node/edge cross-attention actor
E3: optional learned safe-residual subspace actor
```

B1/B2 are controls only.

## 6.3 Fairness tests

```text
test_all_models_start_at_g556
test_all_models_use_same_theta_bounds
test_all_models_use_same_residual_scale
test_scalar_and_rich_heads_are_parameterization_matched
test_initial_validation_risk_is_equal_within_tolerance
```

A rich-vs-scalar claim is invalid if their step-zero outputs differ.

---

# 7. C0/F0 and instance-representation audit

## 7.1 Separate semantic provenance

For every instance record separate hashes and statistics for:

```text
topology tensor
C0 tensor
F0 tensor
node start mass
node goal mass
vertex path occupancy / wait pressure
paired OD tensor
```

Required:

```text
C0 and F0 are not aliases
C0 and F0 intervention changes are separately measurable
C0/F0 hashes are instance-dependent
OD pairing changes F0
opposing flow changes C0
```

## 7.2 Current representation gap

The current graph node features are mostly topology.

G5.65 should add or ablate:

```text
start endpoint mass per node
goal endpoint mass per node
start-goal imbalance
vertex expected path occupancy
vertex convergence / wait-pressure prior
local bottleneck demand
```

F0 remains directed goal-progress flow.

C0 should represent congestion/conflict pressure, not merely duplicate F0.

## 7.3 Node-level OD interaction

Current pooled graph-to-OD attention may lose spatial correspondence.

Explore:

```text
OD token -> start node injection
OD token -> goal node injection
OD-to-node cross-attention
OD-conditioned edge gating
```

The final actor still outputs one theta.

## 7.4 Causal audits

Report effect sizes normalized by natural theta variation:

```text
paired-goal shuffle effect
C0 zero-out effect
F0 zero-out effect
start/goal endpoint removal effect
budget change effect
node permutation invariance
batch composition invariance
```

A merely nonzero `>1e-7` threshold is not sufficient.

---

# 8. Strong actual neural memorization

## 8.1 Required context sizes

Run:

```text
1
4
8
16
32
```

for each primary rich architecture.

## 8.2 Architectures

At minimum:

```text
E0 current repaired dual-stream
E1 lightweight shared-backbone edge attention
```

Also run E2 on at least:

```text
8
16
32
```

## 8.3 Training

Use:

```text
same repaired risk as parameter oracle
weight_decay=0 for memorization proof
no dropout
hidden dimensions 64 and 96 screen
enough epochs to reach plateau
best checkpoint by full train excess risk
three seeds for 16/32 contexts
```

Do not use a fixed 80-step gate.

## 8.4 Oracle-gap metric

For every context report:

```text
g556 risk
parameter-oracle risk
neural risk
normalized oracle regret
nearest positive-mode distance
harmful violation
trust
```

## 8.5 Memorization gate

A strong pass requires:

```text
median normalized oracle regret substantially below 1
rich actor beats global residual control
rich actor beats matched scalar control
opportunity mode-capture rate is high
harmful violation does not rise
results hold at 16 and 32 contexts
```

Do not pass merely because final loss is lower than initial loss.

## 8.6 Required artifacts

```text
phase5p5_repair5g565_neural_memorization_summary.json
phase5p5_repair5g565_neural_memorization_by_context.csv
phase5p5_repair5g565_oracle_gap_closure.csv
phase5p5_repair5g565_branch_gradient_audit.csv
```

---

# 9. Efficient lightweight attention actor E1

## 9.1 Architecture

Implement:

```text
one shared sparse topology backbone
+ C0 channel adapter
+ F0 channel adapter
+ edge-conditioned GATv2-style local layers
+ paired-OD Set Transformer
+ OD-to-graph cross-attention
+ attention pooling
+ continuous field-group residual/trust head
```

Preferred parameter range:

```text
0.2M–1.5M
```

It may be more complex if evidence supports it, but may not fall below the F6 information floor.

## 9.2 Avoid triple redundant encoding where possible

Compare:

```text
triple independent encoders
shared backbone + channel adapters
shared backbone + FiLM/gating
```

## 9.3 Vectorize attention

Replace the Python destination-node loop with:

```text
segment softmax
scatter_reduce
PyG scatter when available and stable
```

Required parity tests:

```text
forward equivalence
gradient equivalence
node permutation invariance
batch invariance
```

## 9.4 Profiling

Report:

```text
parameter count
peak VRAM
GPU utilization
CPU utilization
examples/sec
nodes/sec
edges/sec
data loading time
forward time
backward time
```

The current model is small; efficiency work is to support more contexts and epochs, not to justify a scalar fallback.

---

# 10. Statistically credible current-bank scaling

## 10.1 Current bank first

Use the complete available training bank, not a 34-context subset.

Retain censored contexts with the correct weak loss.

## 10.2 Development design

### Screening stage

```text
one fixed physical-map fold
sizes: 64,128,256,512,all-train
seeds: 3
methods: B0,B1,B2,E0,E1,E2
```

### Confirmatory stage

Select the two best rich architectures without examining heldout/blind solver outcomes.

Run:

```text
at least 4 grouped physical-map folds
at least 3 seeds
sizes: 128,256,512,all-train
```

## 10.3 Training budget

Use epoch-based training:

```text
minimum 30 epochs
maximum >=100 epochs if validation still improves
validation every epoch
early stopping patience >=10 epochs
save best checkpoint
```

Record:

```text
epochs
context presentations
best epoch
full train risk
full validation risk
wall time
```

## 10.4 Scaling metrics

Report separately:

```text
all-context repaired risk
opportunity-context normalized regret
mixed-boundary harmful violation
trivial-context false deviation
censored-context trust
positive mode capture
theta variance
```

## 10.5 Scaling statistics

For each architecture:

```text
median by size
fold variance
seed variance
paired bootstrap slope
first-to-last effect
CI of effect
fraction of folds improved
```

## 10.6 Valid scaling gate

A valid rich-scaling pass requires:

```text
matched initialization
same loss config
same folds
same validation manifests
at least 3 seeds
at least 4 physical-map folds
last-size opportunity regret < first-size regret
effect exceeds seed/fold noise
majority of folds improve
rich beats global and scalar matched controls
harmful violation does not worsen
```

A 0.45% change on 8 validation contexts cannot pass this gate.

---

# 11. Merge all usable exact replay evidence

## 11.1 Sources

Audit and merge exact materialized rows from:

```text
G5.61 development/fine-tune panels
G5.62 cycle1
G5.62 cycle2
G5.62 cycle3
G5.62 alpha/teacher panels if genuinely executed
any later exact actor rows
```

## 11.2 Scientific identity

Deduplicate using:

```text
evaluation UID
physical map hash
scenario hash
solver seed
budget
LTM iterations
full theta fingerprint
source checkpoint
```

## 11.3 Report coverage

Separate:

```text
new candidate rows
new unique theta
expanded existing contexts
new independent contexts
new positive modes
new harmful modes
new censored modes
```

Do not call candidate-row growth context growth.

## 11.4 True rich retraining cycle

Train:

```text
E0/E1 before merge
E0/E1 after merge
```

with:

```text
same split
same initialization
same seeds
same training schedule
same fixed validation panel
```

Required proof:

```text
dataset SHA changes
rich checkpoint SHA changes
training provenance lists merged rows
validation manifest unchanged
post-merge validation opportunity regret reported
```

A scalar 12-step smoke cannot satisfy this gate.

---

# 12. Fresh exact solver transfer panel

## 12.1 Preconditions

Run after:

```text
canonical loss parity passes
matched controls pass
strong memorization passes
current-bank rich scaling is complete
materialization contract remains 1.0
```

## 12.2 Freeze models

Freeze selected checkpoints:

```text
B1 global residual
B2 matched scalar residual
best E0
best E1
best E2
```

Also freeze at least two data-size checkpoints for the top rich actor:

```text
smaller-data checkpoint
all-current-data checkpoint
```

This directly tests whether more training data improves solver behavior.

## 12.3 Panel composition

Use at least:

```text
400–800 independent heldout/new contexts
multiple physical-map families
multiple densities
multiple budgets
multiple agent counts
```

No train-map leakage in the heldout headline.

## 12.4 Methods per context

```text
paper-faithful additive LTM
g556_c063174
B1
B2
E0
E1
E2
```

Use exact paired conditions.

## 12.5 Required truth gates

```text
candidate_recognized = 1
fingerprint exact = 1
force_additive = false for learned dual-channel methods
dual-channel enabled = true
scenario hash = 1
identity complete = 1
theta fixed for run = true
```

## 12.6 Metrics

Against additive and against g556 separately:

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
```

## 12.7 Tiered scientific conclusions

### Tier A — learning enhancement over paper LTM

Supported only if a rich actor:

```text
beats additive LTM
has no supported success regression
shows stable multi-map evidence
```

### Tier B — superiority over optimized fixed baseline

Supported only if it also beats:

```text
g556_c063174
```

Failure of Tier B must not erase a genuine Tier A result.

g556 remains the supported deployment baseline unless the strict promotion gate passes.

---

# 13. Continuous trust/alpha calibration branch

## 13.1 When to run

If the rich actor shows:

```text
better median quality
but nonzero success regressions
or harmful tail
```

run an alpha-response experiment.

## 13.2 Data collection

For the same raw actor residual `delta(x)`, execute:

```text
theta(alpha) = g556 + alpha * delta(x)
alpha in {0, 0.125, 0.25, 0.5, 0.75, 1.0}
```

on a stratified development panel.

This is training-time continuous response mapping.

It is not a codebook selector.

## 13.3 Train trust head

Use real alpha-response outcomes to supervise:

```text
alpha_hat(x)
```

The final actor outputs:

```text
theta_hat(x) = g556 + alpha_hat(x) * delta_hat(x)
```

in one forward pass.

No runtime critic or candidate enumeration is allowed.

## 13.4 Alpha gate

Report:

```text
safe alpha frontier
quality-vs-alpha curve
success-vs-alpha curve
predicted alpha calibration
raw actor vs trust-calibrated actor
```

Then rerun the fresh fixed solver panel.

---

# 14. Mandatory new diagnostic solver data

Even before large expansion, generate a compact new exact dataset for:

```text
quality/noise margin calibration
alpha response
fresh fixed transfer
```

Recommended minimum substantive evidence:

```text
at least 5,000 new exact-materialized candidate rows
```

across independent contexts.

These rows must not be reused as blind evidence after they affect model selection.

---

# 15. Conditional independent-context expansion

## 15.1 Expansion trigger

Proceed only if at least one of these holds:

```text
valid rich scaling effect is positive;
fresh solver transfer improves with larger-data checkpoint;
trust calibration repairs tail risk while preserving quality signal.
```

## 15.2 First context expansion

Increase to:

```text
3,000 total independent valid contexts
at least 32 physical-map hashes
at least 10 map/morphology families
balanced density, budget, agent count, and OD regimes
```

Prioritize independent context diversity over theta Cartesian products.

## 15.3 Theta outcomes per new context

Recommended 20–32 candidate thetas:

```text
g556 baseline
paper additive baseline
small trust-region residual samples
top rich actor output
alpha-scaled actor residuals
local positive-mode perturbations
boundary/hard-negative perturbations
low-discrepancy safe-bounds samples
```

These are training experiments.

The deployed actor remains direct and continuous.

## 15.4 Target solver-row scale

First expansion target:

```text
roughly 50,000–90,000 new candidate solver rows
```

with exact identity and materialization.

## 15.5 Second expansion

Only if the 3,000-context curve remains favorable:

```text
5,000–8,000 independent contexts
```

and rerun the same fixed scaling and solver panels.

## 15.6 No DAgger

Forbidden:

```text
expert actions
learner trajectory imitation
PIBT action labels
state-action aggregation
```

Allowed:

```text
(instance, theta) -> real solver outcome
```

---

# 16. Literature-informed scale interpretation

G5.65 may use the following principles without changing the task:

```text
LaGAT:
  lightweight edge-aware graph attention, multi-layer message passing,
  and substantial pretraining/fine-tuning can make learning-guided search
  competitive; however, its action-imitation/data-aggregation pipeline
  is not adopted here.

GGO:
  optimizing an update model through real simulator outcomes is a valid
  guidance-learning paradigm; simulator performance remains the judge.

Graph Transformer MAPF guidance:
  graph-native learned components can improve classical planning while
  preserving the classical planner as the execution backbone.

Conservative offline optimization:
  actor/critic optimization must avoid unsupported theta regions.
```

Current G5.64 scale:

```text
34 train contexts
8 validation contexts
30 optimizer steps
```

must not be treated as comparable to mature learning-enhanced MAPF training.

---

# 17. Required implementation modules

Recommended:

```text
src/gcst/
  repaired_set_risk.py
  opportunity_labels.py
  matched_theta_heads.py
  c0_f0_representation.py
  shared_edge_attention_actor.py
  alpha_trust_head.py
  rich_scaling_protocol.py
  exact_replay_dataset.py
```

Scripts:

```text
scripts/
  audit_repair5g565_g564_truth.py
  calibrate_repair5g565_label_margin.py
  run_repair5g565_loss_ablation.py
  run_repair5g565_neural_memorization.py
  run_repair5g565_current_bank_scaling.py
  merge_repair5g565_exact_replays.py
  train_repair5g565_rich_cycle.py
  run_repair5g565_fresh_solver_panel.py
  run_repair5g565_alpha_response.py
  generate_repair5g565_context_expansion.py
  run_repair5g565_expanded_training.py
  write_repair5g565_decision.py
```

---

# 18. Required tests

## 18.1 Objective truth

```text
test_oracle_and_actor_use_same_repaired_loss
test_numpy_torch_loss_parity
test_loss_config_hash_is_recorded
test_floor_corrected_loss_at_mode
test_nearest_harmful_loss
test_topk_harmful_loss
test_adaptive_margin_feasible
test_censored_has_no_harmful_gradient
```

## 18.2 Control fairness

```text
test_global_scalar_rich_start_at_g556
test_output_head_parameterizations_match
test_residual_scales_match
test_theta_bounds_match
test_step_zero_risk_matches
```

## 18.3 Representation

```text
test_c0_f0_are_not_aliases
test_c0_f0_hashes_are_separate
test_node_start_goal_mass_is_used
test_od_pairing_changes_prediction
test_c0_intervention_changes_prediction
test_f0_intervention_changes_prediction
test_node_permutation_invariance
test_batch_invariance
```

## 18.4 Memorization/scaling

```text
test_memorization_runs_1_4_8_16_32
test_memorization_compares_oracle_gap
test_scaling_uses_full_train_bank
test_scaling_has_three_seeds
test_scaling_has_multiple_map_folds
test_scaling_gate_checks_uncertainty
test_scalar_control_has_no_label_features
```

## 18.5 Replay/cycle

```text
test_replay_merge_scientific_identity
test_rich_checkpoint_changes_after_merge
test_merged_rows_recorded_in_provenance
test_validation_manifest_unchanged
test_fresh_solver_panel_is_new_execution
test_materialization_exact
```

## 18.6 Anti-degeneration

```text
test_primary_model_not_scalar_only
test_actor_export_excludes_codebook
test_actor_export_excludes_critic
test_actor_one_forward_one_theta
test_theta_fixed_for_run
```

---

# 19. Required artifacts

## 19.1 Truth and loss

```text
outputs/reports/phase5p5_repair5g565_g564_truth_audit.md
outputs/reports/phase5p5_repair5g565_loss_config.json
outputs/tables/phase5p5_repair5g565_loss_ablation_matrix.csv
outputs/tables/phase5p5_repair5g565_opportunity_contexts.csv
outputs/reports/phase5p5_repair5g565_label_margin_summary.json
```

## 19.2 Memorization

```text
outputs/reports/phase5p5_repair5g565_neural_memorization_summary.json
outputs/tables/phase5p5_repair5g565_neural_memorization_by_context.csv
outputs/tables/phase5p5_repair5g565_oracle_gap_closure.csv
```

## 19.3 Scaling

```text
outputs/reports/phase5p5_repair5g565_current_bank_scaling_summary.json
outputs/tables/phase5p5_repair5g565_scaling_by_fold_seed_size.csv
outputs/tables/phase5p5_repair5g565_matched_control_comparison.csv
outputs/reports/phase5p5_repair5g565_scaling_statistics.json
```

## 19.4 Replay/cycle

```text
outputs/reports/phase5p5_repair5g565_exact_replay_merge_summary.json
outputs/reports/phase5p5_repair5g565_rich_retraining_cycle_summary.json
outputs/reports/phase5p5_repair5g565_fresh_solver_panel_summary.json
outputs/tables/phase5p5_repair5g565_fresh_solver_panel_pairs.csv
```

## 19.5 Alpha and expansion

```text
outputs/reports/phase5p5_repair5g565_alpha_response_summary.json
outputs/tables/phase5p5_repair5g565_alpha_response_pairs.csv
outputs/reports/phase5p5_repair5g565_context_expansion_summary.json
outputs/tables/phase5p5_repair5g565_context_expansion_manifest.csv
```

## 19.6 Final

```text
outputs/reports/phase5p5_repair5g565_decision.md
outputs/reports/phase5p5_repair5g565_decision_summary.json
outputs/reports/phase5p5_repair5g565_failure_attribution.md
outputs/reports/phase5p5_repair5g565_artifact_manifest.json
outputs/tables/phase5p5_repair5g565_checksums.sha256
```

---

# 20. Server execution policy

Run substantive experiments under tmux on the RTX5090.

Required phases:

```text
Phase 0: truth audit and tests
Phase 1: canonical repaired-loss parity
Phase 2: label/noise calibration
Phase 3: matched-control memorization
Phase 4: current-bank scaling
Phase 5: exact replay merge + rich retraining
Phase 6: fresh solver transfer
Phase 7: alpha repair if needed
Phase 8: conditional independent-context expansion
Phase 9: expanded retraining + same fixed panels
```

Every phase must write progress with:

```text
run UID
commit
dataset hash
model hash
loss hash
split hash
server/GPU
timestamps
```

---

# 21. No premature completion

G5.65 is not complete after:

```text
writing wrappers
adding unit tests
running one seed
running one split
training on fewer than the requested context sizes
replaying old solver rows
training only a scalar control
changing a checkpoint hash without evaluating it
showing only nonzero gradients
showing only a negative median
copying an old fixed panel
```

Minimum substantive completion:

```text
1. G5.64 truth audit;
2. canonical repaired loss used by oracle and rich actor;
3. matched g556-anchored controls;
4. strong 1/4/8/16/32 neural memorization;
5. multi-seed multi-fold current-bank scaling;
6. at least E0 and E1 trained and saved;
7. rich retraining after exact replay merge;
8. fresh exact solver panel;
9. alpha-response repair branch if tail risk blocks transfer;
10. at least 5,000 new exact diagnostic rows;
11. conditional independent-context expansion if gates support it;
12. final evidence-based decision.
```

If the first attempt fails, execute the specified repair branch and rerun before concluding.

---

# 22. Decision vocabulary

```text
g565_g564_rich_scaling_underpowered_anchor_confounded
g565_g564_true_cycle_scalar_only
g565_repaired_loss_parity_passed
g565_repaired_loss_parity_failed
g565_label_margin_calibrated
g565_matched_controls_ready
g565_neural_memorization_strong_pass
g565_neural_memorization_failed
g565_current_bank_rich_scaling_supported
g565_current_bank_rich_scaling_flat
g565_rich_actor_beats_matched_controls
g565_rich_actor_not_better_than_controls
g565_exact_replay_merge_completed
g565_rich_retraining_improved
g565_rich_retraining_no_gain
g565_fresh_solver_transfer_positive
g565_fresh_solver_transfer_tail_blocked
g565_alpha_calibration_repaired_tail
g565_alpha_calibration_no_gain
g565_expand_to_3000_contexts
g565_expanded_context_training_completed
g565_tierA_beats_paper_ltm
g565_tierB_beats_g556
g565_keep_g556_continue_research
g565_direction_not_supported
```

---

# 23. Final scientific questions

G5.65 must answer:

```text
1. When oracle and neural actor optimize exactly the same repaired set risk,
   can the graph/OD/C0/F0 actor close a substantial fraction of the
   g556-to-oracle gap?

2. Under matched g556-anchored output parameterizations, does the rich actor
   beat global and scalar controls?

3. Does rich-actor performance improve across independent context counts,
   physical-map folds, and seeds?

4. Does that improvement transfer to fresh exact solver replay?

5. If raw actor residuals have quality signal but unsafe tails, can a continuous
   instance-conditioned trust head repair them without selector deployment?

6. After adding independent contexts, does both offline regret and solver
   performance improve further?
```

Only these answers should determine whether the project scales to the next data regime.
