# Repair5G.5.66 — Valid-Only Tail-Causal Direct Actor, Three-Tier LTM Baselines, and Blind Solver Closure

Project: `czr004`
Repository: `czr5454112-glitch/czr004`
Required branch: `server-code`
Source-of-truth start commit: `68f70e0510363f8b80b416c505eb231b0b512c18`
Primary supported deployment baseline: `g556_c063174`
Paper-faithful floor: `LaCAM* + additive LTM`
Intermediate ablation baseline: frozen hand/static-flow shield
Round: `Repair5G.5.66`

---

# 0. Executive mandate

G5.66 continues the current scientific mainline:

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
theta is fixed for the complete solver run
        ↓
ordinary trace-driven C/F traffic maps continue updating online
```

The project goal remains:

```text
replace the coarse hand-designed additive LTM update configuration
with an instance-conditioned learned continuous parameter predictor.
```

G5.66 does not change LaCAM*/PIBT/search semantics.

G5.66 does not introduce:

```text
agent action imitation
DAgger
PIBT action prediction
learned restart selection
learned priority ordering
runtime checkpoint switching
candidate-ID classification
codebook selection
nearest-neighbor theta retrieval
map-ID lookup
deployment-time critic selection
runtime-varying theta
```

The deployment contract remains:

```text
one actor forward
-> one continuous theta
-> no codebook
-> no candidate enumeration
-> no deployed critic
-> no runtime theta change
```

The actor may become more sophisticated, but it may never fall below the permanent F6 representation floor:

```text
physical graph topology
+ actual paired starts/goals
+ paired OD tokens
+ directed C0 congestion prior
+ directed F0 goal-progress prior
+ solver budget
+ LTM iteration budget
```

Scalar summaries are supplemental inputs and controls only.

---

# 1. Three-tier scientific target

G5.66 replaces the previous two-level interpretation with a three-tier hierarchy.

## Tier A — paper-faithful additive LTM

Question:

```text
Does the learned goal-aware continuous-theta actor outperform the
coarse additive update used by paper-faithful LaCAM*+LTM?
```

Canonical role:

```text
paper_additive_ltm
```

Current replay aliases may include:

```text
additive_ltm
repair5g59_additive_fallback
repair5g59_additive_fallback / paper_faithful_additive_ltm
```

The exact actual method and additive fingerprint must be recorded.

This tier is the direct answer to the main research objective.

## Tier B — frozen static-flow shield

Question:

```text
Does the learned instance-conditioned actor outperform a manually designed,
frozen dual-channel/static-flow guidance rule?
```

Canonical report ID:

```text
static_flow_shield_hand
```

Repository alias:

```text
repair5g2_best_frozen_static_candidate
```

Frozen underlying method expected from the project history:

```text
repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75
```

Codex must verify the alias-to-underlying mapping and actual
`updateparams_fingerprint`; it must not assume the alias is correct.

This tier is the key paper ablation separating:

```text
coarse additive LTM
vs
hand-designed static flow
vs
learned instance-conditioned dual-channel theta
```

## Tier C — optimized fixed-global g556

Question:

```text
Can the learned instance-conditioned actor safely outperform the expensive,
globally optimized fixed UpdateParams vector g556_c063174?
```

Canonical ID:

```text
g556_c063174
```

This remains the deployment/promotion baseline unless superseded.

## Three-tier interpretation

```text
Tier A pass:
  learned enhancement succeeds against paper LTM.

Tier B pass:
  learned instance conditioning beats a strong hand/static-flow ablation.

Tier C pass:
  learned instance conditioning beats the optimized fixed global baseline.

Tier A/B pass but Tier C fail:
  valid research success;
  keep g556 as deployment baseline;
  report the remaining gap honestly.

All tiers fail after clean blind replay:
  current run-static continuous-theta formulation is not supported.
```

No stronger baseline may erase a valid weaker-tier result.

---

# 2. Correct interpretation of G5.65

## 2.1 G5.65 was complete

G5.65 completed:

```text
canonical repaired-loss parity
matched g556 initialization
strong 1/4/8/16/32 memorization
1,000-context current-bank scaling
4 physical-map folds
3 seeds
100 epochs
fresh exact nontrain solver replay
5,000-context expansion
expanded exact solver replay
fixed-alpha response materialization
```

The final no-promotion decision is valid.

## 2.2 G5.65 did not show a null actor

The strongest expanded rich actor, E1, approximately achieved:

```text
1,000 nontrain contexts
better than g556: 391
worse than g556: 207
mean quality delta vs g556: -0.323
median quality delta vs g556: -0.0125
success gains vs g556: 10
success regressions vs g556: 5
exact materialization: 1.0
```

E0 also showed more gains than regressions and negative mean/median quality delta.

Therefore:

```text
the learned residual direction carries solver value;
the current actor is not safe enough for Tier C promotion.
```

## 2.3 Retrospective Tier-A signal

The G5.65 pair tables already include additive-LTM outcomes.

A retrospective rich-only analysis supplied after the run indicates approximately:

```text
fresh panel vs additive LTM:
  mean relative improvement: 14.45%
  median relative improvement: 13.72%
  contexts above 6% improvement: 90.7%
  contexts above 10% improvement: 70.4%

expanded panel vs additive LTM:
  mean relative improvement: 18.70%
  median relative improvement: 14.62%
  contexts above 6% improvement: 90.6%
  contexts above 10% improvement: 74.1%
```

This is substantial evidence that the original learning-enhanced-LTM idea is
not dead.

However, it remains retrospective development evidence because:

```text
valid-only loading was not fail-closed;
the static-flow baseline was not explicitly replayed;
multiple checkpoints were inspected;
the panel is no longer blind;
raw regressions require repeatability adjudication.
```

G5.66 must reproduce Tier A prospectively.

## 2.4 Tier B was not tested cleanly

The G5.65 fresh/expanded replay explicitly materialized:

```text
additive LTM
g556
actor checkpoints
```

It did not explicitly execute the frozen `static_flow_shield` baseline on every
same context.

`quality_delta_vs_additive` cannot be relabeled as a static-flow comparison.

G5.66 must add a real static-flow row to every development and blind context.

## 2.5 Current-bank scaling was real but small

For E1, matched-control repaired validation risk changed roughly:

```text
N=128: 0.011866
N=all: 0.011739
```

All four folds and three seeds improved.

This proves learnability, but does not explain the rare solver boundary.

## 2.6 Correct G5.65 scientific conclusion

```text
Graph/OD/C0/F0 representations contain learnable instance-conditioned theta
signal.  Direct continuous actors improve solver quality on many fresh
instances and appear strongly better than additive LTM.  The current label,
validity, risk, and trust pipeline does not reliably suppress rare success
regressions relative to g556.
```

---

# 3. Why the idea is still worth G5.66

Continuation is justified because:

```text
memorization succeeds;
matched offline scaling succeeds;
fresh quality medians are negative;
leading rich actors have better > worse;
leading rich actors have success gains > regressions;
materialization and identity are exact;
retrospective additive-LTM improvements are large;
the failure is concentrated in a rare tail.
```

G5.66 is also a decision round.

If the following repairs do not control the supported g556 tail:

```text
valid-only reconstruction
repeatability-based labels
field-group causal response
training-time distributional risk
continuous group-wise trust
new blind physical maps
```

then the current formulation:

```text
instance -> one run-static 15D UpdateParams theta
```

should be considered exhausted in its present form.

That would not invalidate all neural LTM update models, but it would be a strong
negative result for this specific deployment formulation.

---

# 4. P0 source-of-truth repairs

## 4.1 Valid-only primary loading was not enforced

The main G5.65 loader defaulted to:

```text
phase5p5_repair5g560_labelv51_training_rows.csv
```

The historical audit found:

```text
2,000 scenarios
1,203 valid
797 invalid
515 duplicate-start cases
298 duplicate-goal cases
288 unreachable-pair cases
```

A valid-only table existed but was not the mandatory primary path.

### Required fix

Create data scopes:

```text
VALID_PRIMARY_TRAIN
VALID_PRIMARY_VALIDATION
VALID_CALIBRATION
VALID_BLIND
INVALID_QUARANTINE
ALL_ROWS_DIAGNOSTIC_ONLY
```

All primary scripts must reject all-row input unless an explicit diagnostic flag
is provided.

## 4.2 The 5,000-context top-up was not fully audited

The top-up records:

```text
5,000 instance UIDs
40 physical maps
16 families
minimum path-found rate 0.75
```

A path-found rate below 1.0 is incompatible with the full-agent F6 contract.

### Required fix

Audit every actual scenario file.

Require:

```text
unique starts
unique goals
all starts/goals traversable
all pairs reachable
all agent mass represented
traffic path_found_rate = 1.0
scenario/map hashes match
```

Regenerate invalid assignments component-aware.

Minimum target:

```text
5,000 independently valid contexts
```

Preferred:

```text
6,000 valid contexts
```

## 4.3 The calibrated margin was not applied to labels

G5.65 calculated a recommended quality margin near:

```text
0.043
```

but actor dataset construction still used a default zero margin.

### Required fix

Create:

```text
Label-v5.3-valid-replicated-tail
```

The applied margin and its source must be part of:

```text
dataset hash
loss configuration
checkpoint manifest
replay report
```

## 4.4 The margin was not a repeatability estimate

The G5.65 margin used heterogeneous deltas across contexts and candidates.

That estimates task variation, not same-pair noise.

### Required fix

Estimate measurement variation from repeated scientific pairs:

```text
same map
same starts/goals
same theta
same budget
same LTM iterations
controlled planner RNG conditions
```

## 4.5 Expanded validation used an index split

The expanded script used approximately:

```text
every fifth example for validation
```

instead of physical-map grouping.

### Required fix

Use one frozen physical-map split manifest.

No index-based split is allowed in a scientific result.

## 4.6 G5.65 heldout evidence is consumed

Validation and heldout results were inspected during G5.65 development.

They remain useful development labels but are not a future blind claim.

### Required fix

Generate new blind maps and scenarios absent from every G5.59–G5.65 artifact.

## 4.7 Replay merge omitted the most relevant rows

The merge consumed G5.62 cycle3 rows only.

It did not ingest development-eligible rows from:

```text
G5.65 fresh replay
G5.65 expanded replay
G5.65 alpha response
```

### Required fix

Merge all development rows with exact identity.

Never merge new blind rows.

## 4.8 Alpha calibration did not train a trust head

G5.65 executed a fixed alpha grid but recorded:

```text
alpha_trust_head_trained = false
fresh_fixed_panel_reran_after_alpha = false
```

### Required fix

Train an instance-conditioned continuous trust head and replay it.

## 4.9 Offline risk remained a theta-geometry proxy

The repaired risk did not directly predict:

```text
success regression probability
quality quantiles
q90/q95 tail
CVaR
runtime/search effort
```

### Required fix

Train a cross-fitted distributional outcome ensemble for training only.

## 4.10 G5.65 quality gate was noise-unaware

The per-variant strict gate required:

```text
success regressions = 0
worse quality count = 0
success gains > 0
```

Any positive delta, even one inside the subsequently calibrated tie margin,
blocked support.

### Required fix

Keep success safety strict, but use noise-aware quality gates:

```text
raw worse
supported worse outside margin
q90/q95
CVaR
paired bootstrap CI
```

## 4.11 Aggregate metrics can obscure the best actor

G5.65 evaluated many checkpoints together.

Aggregate CVaR across controls and checkpoints is not the metric for one
pre-registered E1 checkpoint.

### Required fix

All scientific gates are per checkpoint.

## 4.12 Parallel wall-clock replay may create measurement tails

Fresh replay used multiple workers under wall-clock budgets.

CPU contention, order effects, and timing jitter may affect solution-found and
ratio outcomes.

A nearly no-op actor checkpoint even showed a success regression in one panel,
which requires investigation.

### Required fix

Run a controlled replay audit:

```text
max_workers = 1
CPU affinity/pinning where available
randomized blocked method order
same-pair repeats
record machine load
compare with parallel execution
```

Separate:

```text
theta-causal tail
from
measurement/runtime tail.
```

## 4.13 Static-flow baseline was absent

The current replay helper built additive and g556 rows only.

### Required fix

Every panel must include:

```text
additive LTM
frozen static-flow shield
g556
actor
```

## 4.14 Representation gaps remain

Current graph nodes are largely topology-only.

Traffic code computes wait-pressure summaries, but full spatial node features do
not yet include:

```text
start mass
goal mass
start-goal imbalance
vertex expected occupancy
vertex convergence/wait pressure
```

### Required fix

Add and ablate these features.

---

# 5. Baseline truth registry

Create:

```text
src/gcst/three_tier_baselines.py
```

It must define:

```text
TIER_A_ADDITIVE
TIER_B_STATIC_FLOW
TIER_C_G556
```

## 5.1 Tier A

```text
canonical_report_id:
  paper_additive_ltm

accepted solver aliases:
  additive_ltm
  repair5g59_additive_fallback

required fingerprint:
  force_additive = 1
  enable_dual_channel = 0
```

## 5.2 Tier B

```text
canonical_report_id:
  static_flow_shield_hand

registry alias:
  repair5g2_best_frozen_static_candidate

expected underlying solver method:
  repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75
```

Codex must resolve the actual frozen spec and store:

```text
alias
underlying method
full UpdateParams fingerprint
source artifact SHA
```

If the alias points elsewhere, the actual mapping is authoritative and the
difference must be reported.

## 5.3 Tier C

```text
canonical_report_id:
  g556_c063174

required:
  canonical theta schema
  exact fingerprint
  force_additive = 0
  dual channel enabled
```

## 5.4 Baseline contract tests

```text
test_tierA_additive_fingerprint
test_tierB_alias_resolves_to_frozen_underlying
test_tierB_fingerprint_is_constant
test_tierC_g556_fingerprint
test_all_three_baselines_execute_same_context
test_baseline_identity_is_not_inferred_from_label
```

---

# 6. Three-tier pair schema

Every actor pair row must contain:

```text
actor_success
additive_success
static_flow_success
g556_success

actor_ratio
additive_ratio
static_flow_ratio
g556_ratio

delta_vs_additive
delta_vs_static_flow
delta_vs_g556

relative_improvement_vs_additive
relative_improvement_vs_static_flow
relative_improvement_vs_g556

success_gain_vs_additive
success_regression_vs_additive
success_gain_vs_static_flow
success_regression_vs_static_flow
success_gain_vs_g556
success_regression_vs_g556
```

Relative improvement:

```text
(baseline ratio - actor ratio) / baseline ratio
```

Lower sum-of-loss ratio remains better.

Quality is compared only when both relevant methods succeed.

---

# 7. Tier-specific claim gates

## 7.1 Raw and supported outcomes

Always report both:

```text
raw success regressions
supported success regressions after replicate adjudication
raw quality worse
supported quality worse outside calibrated margin
```

Never hide raw outcomes.

## 7.2 Tier A minimal pass

On new blind maps:

```text
exact materialization = 1.0
zero supported success regressions vs additive
success rate noninferior vs additive
median relative improvement >= 6%
bootstrap lower bound of median/paired effect > 0
better > worse outside calibrated margin
```

## 7.3 Tier A strong pass

```text
Tier A minimal pass
median relative improvement >= 10%
majority of map families improve
no supported catastrophic tail
```

This is the main learned-LTM paper claim.

## 7.4 Tier B minimal pass

```text
exact static-flow materialization
zero supported success regressions vs static flow
success rate noninferior
paired quality CI favors actor
median relative improvement >= 3%
```

## 7.5 Tier B strong pass

```text
Tier B minimal pass
median relative improvement >= 6%
majority of map families improve
```

## 7.6 Tier C research-signal pass

This is not deployment promotion.

```text
success gains > regressions
negative median quality delta
better > worse outside noise margin
no concentration of regressions in one invalid/measurement stratum
```

## 7.7 Tier C deployment pass

```text
exact materialization = 1.0
zero supported success regressions vs g556
raw regressions all adjudicated and reported
mean and median quality delta < 0
paired bootstrap CI upper <= 0
q95 harmful quality delta <= calibrated margin
CVaR below pre-registered limit
better > worse outside margin
no hidden checkpoint selection on blind
```

Only this gate can supersede g556 as deployment baseline.

---

# 8. Research hypotheses

## H1 — validity contamination

Invalid assignments distorted priors and labels.

Prediction:

```text
valid-only training improves offline-to-solver alignment.
```

## H2 — direction good, amplitude unsafe

E1 residual direction is useful, but magnitude is unsafe in rare contexts.

Prediction:

```text
continuous instance-conditioned trust preserves gains and removes regressions.
```

## H3 — field-group tail

Only some UpdateParams groups cause failures.

Prediction:

```text
group-wise alpha outperforms one global alpha.
```

## H4 — geometric proxy gap

Theta-space distance does not model the solver boundary.

Prediction:

```text
distributional success/quality supervision improves transfer.
```

## H5 — no-op calibration

The actor must learn where to remain at g556.

Prediction:

```text
explicit no-op/trust supervision reduces false deviations.
```

## H6 — safe low-dimensional residual manifold

Safe useful residuals lie in a low-dimensional subspace.

Prediction:

```text
safe-subspace actor preserves Tier A/B gain with lower Tier-C tail.
```

## H7 — measurement-tail hypothesis

Some raw regressions are caused by wall-clock contention or unstable solver
conditions.

Prediction:

```text
controlled repeats reduce unsupported raw regression count.
```

---

# 9. Mandatory execution order

```text
Phase 0: G5.65 truth audit
Phase 1: valid-only context reconstruction
Phase 2: frozen train/validation/calibration/blind maps
Phase 3: replay determinism and replicate calibration
Phase 4: explicit three-tier baseline replay
Phase 5: per-variant tail attribution
Phase 6: field-group causal response acquisition
Phase 7: Label-v5.3 dataset
Phase 8: distributional outcome ensemble
Phase 9: direct actors with group trust / safe subspace
Phase 10: valid-only scaling
Phase 11: development exact three-tier replay
Phase 12: tail-focused acquisition and retraining
Phase 13: frozen blind three-tier replay
Phase 14: paper ablations and final decision
```

No scientific scope downgrade is allowed.

Allowed lossless acceleration:

```text
tensor caching
graph/OD/C0/F0 caching
vectorized segment attention
BF16/TF32 with parity tests
checkpoint/resume
B1/B2 fast paths
staged screening followed by full confirmation
```

Forbidden:

```text
reducing required folds
reducing required seeds
dropping E1/E2
dropping static-flow replay
replacing blind replay with old rows
shortening training below convergence
calling missing evidence a negative conclusion
```

The user accepts long-running 5090 experiments.

---

# 10. Phase 0 — G5.65 truth audit

Write:

```text
outputs/reports/phase5p5_repair5g566_g565_truth_audit.md
outputs/reports/phase5p5_repair5g566_g565_truth_audit_summary.json
```

Required fields:

```text
g565_complete = true
g565_tierA_retrospective_signal = strong
g565_tierB_explicit_replay = false
g565_tierC_deployment_supported = false
g565_valid_only_enforced = false
g565_applied_quality_margin = 0
g565_reported_margin > 0
g565_expanded_split_physical_map_grouped = false
g565_alpha_trust_head_trained = false
g565_merge_includes_fresh_expanded_alpha = false
g565_blind_panel_still_available = false
```

---

# 11. Phase 1 — valid-only reconstruction

## 11.1 Actual-file audit

For every context:

```text
map exists
scenario exists
hashes match
requested and encoded agent count match
starts unique
goals unique
starts traversable
goals traversable
each pair reachable
all agent mass preserved
traffic path_found_rate = 1
```

## 11.2 Regeneration

Use connected-component-aware sampling.

Do not use modulo cell reuse.

If a region lacks capacity:

```text
expand the region
resample a component
resample the assignment
or regenerate the context
```

## 11.3 Context targets

Minimum:

```text
5,000 valid contexts
40 map hashes
16 families
6 agent tiers
4 budgets
recorded OD regimes
```

Preferred:

```text
6,000 valid contexts
```

## 11.4 Artifacts

```text
phase5p5_repair5g566_valid_context_manifest.csv
phase5p5_repair5g566_invalid_quarantine.csv
phase5p5_repair5g566_scenario_validity.csv
phase5p5_repair5g566_validity_summary.json
phase5p5_repair5g566_validity.md
```

---

# 12. Phase 2 — frozen split and blind bank

## 12.1 Roles

```text
TRAIN
VALIDATION
CALIBRATION
BLIND
```

Split by physical map hash.

Recommended:

```text
60% train
15% validation
10% calibration
15% blind
```

## 12.2 Blind novelty

Blind maps/scenarios must be absent from:

```text
all G5.59–G5.65 actor training
all G5.65 fresh/expanded/alpha panels
all checkpoint selection
all margin calibration
```

Generate new maps if necessary.

## 12.3 Blind lock

Before blind replay, hash:

```text
blind manifest
scenario archive
baseline registry
candidate checkpoint manifest
decision rules
```

No changes after the first blind result is observed.

---

# 13. Phase 3 — deterministic/replicate calibration

## 13.1 Controlled replay

Compare:

```text
max_workers=1
max_workers=normal parallel setting
```

Use:

```text
CPU affinity where available
randomized blocked order
machine load records
same scientific pair
```

## 13.2 Replicate methods

For calibration contexts execute:

```text
additive LTM
static-flow shield
g556
raw E1
one verified positive theta
one boundary harmful theta
```

Use at least 3 permitted planner RNG seeds/repeats.

## 13.3 Outputs

```text
success probability
success-regression posterior
quality median
quality MAD
q10/q50/q90/q95
runtime variance
same-pair repeatability
worker-contention effect
```

## 13.4 Label confidence

Examples:

```text
SUPPORTED_REGRESSION:
  repeated regression or posterior above threshold

UNCERTAIN_BOUNDARY:
  unstable regression

SUPPORTED_GAIN:
  repeatable gain

QUALITY_TIE:
  within stratum-specific margin
```

---

# 14. Phase 4 — explicit three-tier replay smoke

Before model training, verify every baseline on at least:

```text
128 valid contexts
```

Each context must produce:

```text
additive row
static-flow row
g556 row
```

Check:

```text
method identity
fingerprint
scenario hash
evaluation UID
success
ratio
runtime
expanded nodes
PIBT calls
```

No Tier B claim may use an inferred static value.

---

# 15. Phase 5 — per-variant tail attribution

Primary diagnosis models:

```text
expanded E1 seed565
expanded E0 seed565
expanded E2 seed565
best matched scalar
g556
```

For every tail/gain context report:

```text
map family
map hash
OD regime
agents
density
budget
path overlap
head-on pressure
wait pressure
baseline states
actor residual norm
each theta field
each field-group residual
runtime delta
node expansion delta
PIBT-call delta
measurement repeatability
```

Cluster:

```text
instance features
residual direction
field groups
solver symptoms
```

Determine whether failures are:

```text
map concentrated
budget concentrated
density concentrated
field concentrated
out-of-support
measurement unstable
```

---

# 16. Phase 6 — field-group causal response

## 16.1 Field groups

```text
G1 congestion commit/block:
  alpha_cong_commit_progress
  alpha_cong_commit_nonprogress
  alpha_cong_block

G2 congestion wait:
  alpha_cong_wait_progress
  alpha_cong_wait_nonprogress

G3 goal flow:
  alpha_flow_commit_progress
  alpha_flow_wait_progress

G4 decay:
  rho_cong_decay
  rho_flow_decay

G5 channel weights:
  lambda_cong
  lambda_flow

G6 shield/bounds:
  flow_shield_beta
  max_flow_shield
  min_edge_cost
  max_edge_cost
```

## 16.2 Response design

For raw residual `delta_g(x)`:

```text
theta = g556 + concat_g(alpha_g * delta_g)
```

Collect:

```text
global alpha
one-group-only
leave-one-group-out
identified group-pair interactions
```

## 16.3 Scale

Use at least:

```text
1,500 valid development contexts
50,000 new exact actor candidate rows
```

Preferred:

```text
80,000–120,000 rows
```

Replicate safety boundaries.

---

# 17. Phase 7 — Label-v5.3

## 17.1 Context object

Store:

```text
absolute candidate outcome
outcomes vs additive
outcomes vs static flow
outcomes vs g556
quality distribution
success distribution
replicate confidence
candidate support
field-group response
```

## 17.2 Merge sources

Eligible development rows:

```text
valid historical rows
G5.61/G5.62 valid development rows
G5.65 validation rows
G5.65 expanded development rows with valid lineage
G5.65 alpha development rows
G5.66 replicate rows
G5.66 group-response rows
```

Forbidden:

```text
invalid scenarios
ambiguous identity
new blind outcomes
```

## 17.3 Sampling

Sample:

```text
context
-> outcome stratum
-> theta
```

Balance:

```text
safe improvement
supported regression
quality tail
safe no-op
uncertain boundary
```

## 17.4 Artifacts

```text
phase5p5_repair5g566_labelv53_summary.json
phase5p5_repair5g566_labelv53_contexts.csv
phase5p5_repair5g566_labelv53_candidates.csv
phase5p5_repair5g566_labelv53_replicates.csv
```

---

# 18. Phase 8 — distributional outcome ensemble

## 18.1 Inputs

```text
graph topology
paired OD
C0/F0
budget
theta embedding
```

## 18.2 Outputs

```text
P(success regression vs additive)
P(success regression vs static flow)
P(success regression vs g556)
P(success gain)
quality delta q10/q50/q90/q95 for all three tiers
harmful CVaR
runtime/search-effort quantiles
epistemic uncertainty
```

## 18.3 Cross-fitting

Use physical-map cross-fitting.

An actor training context may only use predictions from a critic ensemble that
did not train on that physical map.

## 18.4 Conservative estimates

Use:

```text
upper confidence bound for regression risk
upper confidence bound for harmful quality
lower confidence bound for gain
```

Penalize unsupported theta regions.

## 18.5 Deployment

The critic is training-only.

Actor-only export must not include it.

---

# 19. Phase 9 — direct actor variants

All variants remain direct one-forward continuous actors.

## A0 — geometric E1 control

Valid-only E1 trained with repaired geometric set loss.

## A1 — E1 distributional-tail actor

```text
E1 encoder
+ 15D residual direction
+ global continuous trust
+ distributional risk training
```

## A2 — field-group trust actor

```text
E1 encoder
+ 15D residual direction
+ six continuous group trust values
```

Deployment:

```text
theta = g556 + group_trust(x) * residual(x)
```

No discrete fallback.

## A3 — safe residual subspace actor

Build a residual basis from verified safe improvements:

```text
theta = g556 + B z(x)
```

Screen dimensions:

```text
K = 4, 6, 8
```

Add group trust.

## A4 — enhanced spatial E1

Add:

```text
node start mass
node goal mass
node imbalance
vertex occupancy
wait pressure
OD-to-node/edge cross attention
```

## A5 — optional soft mixture of continuous experts

Allowed only if needed:

```text
soft continuous mixture
-> one residual
-> one theta
```

No expert/candidate ID is selected at deployment.

---

# 20. Tail-aware actor loss

Primary loss:

```text
L =
  L_safe_mode
  + lambda_reg * UCB_success_regression
  + lambda_q * predicted_quality_q90
  + lambda_cvar * predicted_harmful_CVaR
  + lambda_noop * no-op calibration
  + lambda_support * OOD support penalty
  + lambda_group * group trust regularization
  + lambda_tierA * additive gain loss
  + lambda_tierB * static-flow gain loss
  + lambda_tierC * g556 risk/quality loss
```

Success regression has lexicographic priority over quality gain for Tier C.

For Tier A/B, preserve large relative improvement while controlling supported
regressions.

---

# 21. Representation improvements

## 21.1 Node features

Add:

```text
start endpoint mass
goal endpoint mass
start-goal imbalance
expected path occupancy
vertex convergence
wait-pressure prior
local demand entropy
```

## 21.2 Edge features

Keep separate:

```text
topology
C0 conflict/congestion
F0 goal-progress
opposing flow
head-on pressure
bottleneck demand
```

## 21.3 OD interaction

Compare:

```text
pooled OD only
OD-to-node attention
OD-to-edge gating
start/goal node injection
```

## 21.4 Interventions

Report normalized effect size for:

```text
pair shuffle
C0 zero
F0 zero
start mass zero
goal mass zero
wait pressure zero
budget change
```

---

# 22. Training protocol

## 22.1 Splits

Physical-map grouped:

```text
4–5 development folds
3 actor seeds
3 critic ensemble seeds per fold
```

## 22.2 Training scale

Use all valid TRAIN contexts.

Minimum:

```text
100 epochs
min 30 epochs
early stopping patience >= 10
```

Continue if validation tail metrics improve.

## 22.3 Checkpoint selection

Do not select by total geometric loss alone.

Pre-register a Pareto rule:

```text
1. minimum supported regression surrogate
2. harmful q95/CVaR
3. Tier-C quality
4. Tier-B quality
5. Tier-A quality
```

## 22.4 Candidate count

Before development replay, pre-register at most:

```text
3 primary rich checkpoints
1 scalar control
```

Avoid aggregate checkpoint fishing.

---

# 23. Phase 10 — valid-only scaling

Sizes:

```text
512
1,000
2,000
all-valid
```

Methods:

```text
B0 g556
B1 global residual
B2 scalar residual
A0
A1
A2
A3
A4
```

Report:

```text
geometric risk
regression UCB
quality q50/q90/q95
CVaR
no-op deviation
Tier-A/B/C predicted metrics
field-group trust
```

A valid scaling claim requires fold/seed consistency and solver validation.

---

# 24. Phase 11 — development exact three-tier replay

## 24.1 Contexts

At least:

```text
1,500 valid validation/calibration contexts
```

## 24.2 Methods

Every context:

```text
LaCAM* no-LTM diagnostic
Tier A additive LTM
Tier B static-flow shield
Tier C g556
B2 scalar control
up to three pre-registered rich actors
```

## 24.3 Resource control

Run:

```text
controlled single-worker replicate shard
normal-throughput main shard
```

## 24.4 Decision

Select at most two actors for blind replay using predeclared development rules.

---

# 25. Phase 12 — second tail-focused acquisition

If development actors still have supported Tier-C regressions:

```text
collect group-response rows around those contexts
replicate boundary cases
train distributional critic v2
train actor v2
rerun a separate validation panel
```

Do not use blind contexts.

Minimum additional rows when triggered:

```text
25,000 exact development rows
```

---

# 26. Phase 13 — blind three-tier replay

## 26.1 Freeze

Before execution freeze:

```text
one primary actor
one backup conservative actor
baseline registry
blind contexts
gate thresholds
checkpoint hashes
```

## 26.2 Scale

At least:

```text
1,000 valid blind contexts
12+ unseen physical-map hashes
multiple families/densities/budgets/agent tiers
```

## 26.3 Methods

```text
LaCAM* no-LTM diagnostic
additive LTM
static-flow shield
g556
primary actor
backup actor
```

## 26.4 No post-hoc changes

After results:

```text
no retraining
no threshold tuning
no checkpoint replacement
```

---

# 27. Paper ablation matrix

Required rows:

```text
LaCAM* no LTM
LaCAM* + additive LTM
LaCAM* + static-flow shield
LaCAM* + g556
LaCAM* + learned actor
```

Representation ablations:

```text
scalar-only control
no graph
no paired OD
unpaired starts/goals
no C0
no F0
no wait-pressure
no OD-to-graph cross-attention
```

Safety/output ablations:

```text
global trust
field-group trust
no distributional critic
geometric loss only
full 15D residual
safe subspace
```

Training ablations:

```text
all-row vs valid-only diagnostic
zero-margin vs calibrated margin diagnostic
single-run vs replicate-confidence labels
```

Invalid/all-row diagnostics may never support the main claim.

---

# 28. Metrics

For every tier and method:

```text
success rate
success gains
raw regressions
supported regressions
both-success
both-fail
sum-of-loss ratio
absolute delta
relative improvement
mean
median
trimmed mean
bootstrap CI
better/worse/ties outside margin
q90/q95
CVaR
runtime
expanded nodes
PIBT calls
```

Stratify by:

```text
map family
physical map
agent count
density
budget
OD regime
baseline success state
```

---

# 29. Required tests

## Data validity

```text
test_primary_loader_rejects_all_rows
test_unique_starts
test_unique_goals
test_all_pairs_reachable
test_path_found_rate_one
test_invalid_context_quarantined
test_topup_actual_files_audited
```

## Split

```text
test_physical_map_splits_disjoint
test_blind_absent_from_training
test_blind_manifest_frozen
test_index_split_forbidden
```

## Three-tier baselines

```text
test_additive_actual_fingerprint
test_static_alias_resolution
test_static_underlying_fingerprint
test_g556_fingerprint
test_all_baselines_on_same_context
test_three_tier_pair_columns
```

## Labels

```text
test_margin_applied_to_labelv53
test_replicate_confidence
test_uncertain_not_harmful
test_supported_regression_rule
test_blind_rows_not_merged
```

## Outcome ensemble

```text
test_crossfit_no_map_leakage
test_quantile_monotonicity
test_risk_ucb_increases_with_uncertainty
test_critic_not_in_actor_export
```

## Actor

```text
test_f6_information_floor
test_group_trust_shape
test_one_forward_one_theta
test_theta_fixed_for_run
test_safe_subspace_bounds
test_actor_export_no_codebook
test_actor_export_no_critic
```

## Replay

```text
test_single_worker_repeatability
test_parallel_contention_reported
test_exact_materialization_all_methods
test_per_variant_gates
test_noise_margin_used_in_quality_gate
```

---

# 30. Required artifacts

## Truth/validity

```text
phase5p5_repair5g566_g565_truth_audit.md
phase5p5_repair5g566_validity_summary.json
phase5p5_repair5g566_valid_context_manifest.csv
phase5p5_repair5g566_invalid_quarantine.csv
phase5p5_repair5g566_split_manifest.csv
```

## Baselines

```text
phase5p5_repair5g566_three_tier_baseline_registry.json
phase5p5_repair5g566_baseline_materialization_summary.json
```

## Calibration

```text
phase5p5_repair5g566_replicate_calibration_summary.json
phase5p5_repair5g566_worker_contention_audit.json
phase5p5_repair5g566_labelv53_summary.json
```

## Tail/response

```text
phase5p5_repair5g566_g565_tail_attribution.md
phase5p5_repair5g566_tail_contexts.csv
phase5p5_repair5g566_field_group_response_summary.json
phase5p5_repair5g566_field_group_response_pairs.csv
```

## Models

```text
phase5p5_repair5g566_distributional_critic_summary.json
phase5p5_repair5g566_actor_training_summary.json
phase5p5_repair5g566_actor_scaling_summary.json
phase5p5_repair5g566_actor_manifest.json
```

## Solver

```text
phase5p5_repair5g566_dev_three_tier_summary.json
phase5p5_repair5g566_dev_three_tier_pairs.csv
phase5p5_repair5g566_blind_three_tier_summary.json
phase5p5_repair5g566_blind_three_tier_pairs.csv
```

## Final

```text
phase5p5_repair5g566_tierA_decision.json
phase5p5_repair5g566_tierB_decision.json
phase5p5_repair5g566_tierC_decision.json
phase5p5_repair5g566_decision.md
phase5p5_repair5g566_decision_summary.json
phase5p5_repair5g566_failure_attribution.md
phase5p5_repair5g566_artifact_manifest.json
phase5p5_repair5g566_checksums.sha256
```

---

# 31. No premature completion

G5.66 is not complete after:

```text
writing wrappers
adding tests
building a manifest
training one critic
training one actor
rerunning old G5.65 rows
replaying additive and g556 without static flow
running invalid/all-row contexts
using fixed alpha without training group trust
copying an old heldout panel
reporting aggregate all-checkpoint CVaR
```

Minimum substantive completion:

```text
1. valid-only actual-file audit and repair
2. new frozen split/blind bank
3. exact three-tier baseline registry
4. repeatability/contention calibration
5. Label-v5.3 with applied margin
6. per-variant tail attribution
7. >=50k new group/tail exact development rows
8. distributional cross-fitted outcome ensemble
9. direct group-trust and safe-subspace actors
10. valid-only multi-seed scaling
11. development three-tier exact replay
12. second tail acquisition if needed
13. new blind three-tier replay
14. separate Tier A/B/C decisions
```

If a stage fails, execute its diagnostic/repair branch rather than ending the
round immediately.

---

# 32. Decision vocabulary

```text
g566_valid_only_dataset_ready
g566_validity_repair_failed
g566_three_tier_baselines_materialized
g566_static_flow_mapping_failed
g566_measurement_tail_detected
g566_theta_causal_tail_confirmed
g566_labelv53_ready
g566_distributional_critic_calibrated
g566_distributional_critic_not_calibrated
g566_group_trust_learned
g566_safe_subspace_supported
g566_valid_scaling_supported
g566_valid_scaling_flat
g566_dev_tierA_pass
g566_dev_tierB_pass
g566_dev_tierC_signal
g566_dev_tierC_tail_blocked
g566_blind_tierA_pass
g566_blind_tierA_strong_pass
g566_blind_tierB_pass
g566_blind_tierB_strong_pass
g566_blind_tierC_research_signal
g566_blind_tierC_deployment_pass
g566_blind_tierC_tail_blocked
g566_learned_ltm_success_keep_g556_deployment
g566_learned_ltm_and_static_flow_success
g566_full_three_tier_success
g566_run_static_theta_formulation_exhausted
```

---

# 33. Final interpretation matrix

## Case 1

```text
Tier A pass
Tier B fail
Tier C fail
```

Conclusion:

```text
learning successfully replaces coarse additive LTM,
but does not yet beat hand static-flow guidance.
```

## Case 2

```text
Tier A pass
Tier B pass
Tier C fail
```

Conclusion:

```text
strong learning-enhanced LTM result;
learned instance conditioning beats additive and hand static flow;
g556 remains deployment baseline.
```

## Case 3

```text
Tier A/B/C pass
```

Conclusion:

```text
full success;
learned actor supersedes fixed global baseline.
```

## Case 4

```text
Tier A fails on clean blind valid-only data
```

Conclusion:

```text
the current run-static continuous-theta formulation is not supported.
```

---

# 34. Literature-informed guidance

G5.66 may use these principles without changing the task:

```text
LTM:
  keep LaCAM* and dynamic trace-updated traffic maps intact.

GGO:
  real simulator outcomes and update-model optimization are valid supervision;
  simulator performance is the final judge.

LaGAT:
  graph-native attention can help classical MAPF search, but imperfect neural
  guidance needs explicit safety handling.

Conservative offline optimization:
  penalize unsupported theta regions and optimize upper risk bounds.

Set-valued learning:
  preserve multiple safe theta modes rather than averaging them.
```

The project does not adopt LaGAT action imitation or DAgger.

---

# 35. Final questions

G5.66 must answer:

```text
1. On fully valid, unseen contexts, does the learned actor strongly outperform
   paper-faithful additive LTM?

2. Does it outperform the frozen hand/static-flow shield?

3. Can field-group continuous trust and distributional tail supervision remove
   supported regressions relative to g556?

4. Are the remaining raw regressions theta-causal or measurement/runtime noise?

5. Does a low-dimensional safe residual manifold improve Tier-C safety?

6. Does the three-tier result support a clean paper story:
   additive -> static flow -> optimized global -> learned instance-conditioned?
```

---

# 36. Codex completion record (2026-06-22)

Execution:

```text
Remote instance: ackcs-00gjh6i6 RTX5090
tmux session: g566
exit code: 0
final decision: g566_blind_complete
```

Pipeline integrity:

```text
valid contexts: 6000
blind contexts: 1031 available, 1000 replayed
smoke replay: 128 contexts, 512/512 rows
repeatability replay: 48 contexts, 192/192 rows
field-group response: 1500 contexts, 54500/54500 rows, 50000 actor rows
Label-v5.3: 1021 contexts, 50048 candidates, 50018 safe candidates
distributional critic: calibrated, 50048 OOF prediction rows
actor training: C0/A0/A1/A2/A3/A4 x seeds 566/567/568, 18 checkpoints
development replay: 1500 contexts, 12000/12000 rows
blind replay: 1000 contexts, 6000/6000 rows
```

Blind materialization checks:

```text
exact materialization rate: 1.0
candidate recognition rate: 1.0
scenario hash match rate: 1.0
identity retention rate: 1.0
```

Blind outcome:

```text
Tier A pass: false
Tier B pass: false
Tier C research signal: false
Tier C deployment pass: false
```

Why the result did not pass:

```text
Tier A median relative improvement vs additive: 13.22%
Tier A success regressions vs additive: 12

Tier B median relative improvement vs static-flow: 4.69%
Tier B success regressions vs static-flow: 30

Tier C success gains vs g556: 21
Tier C success regressions vs g556: 23
Tier C q95 harmful delta vs g556: 0.263 > 0.05 margin
```

Interpretation:

```text
The learned run-static continuous theta has a real central-tendency signal,
especially versus additive LTM and moderately versus static-flow. However, the
blind tail is not safe: a small number of cases regress from solved to unsolved
relative to weaker baselines, and the g556 tail gate is not close to deployment
safe. G5.66 is therefore a clean negative promotion result, not a failed run.
The next scientific step should target zero success regressions and harmful-tail
control rather than chasing only better median quality.
```
