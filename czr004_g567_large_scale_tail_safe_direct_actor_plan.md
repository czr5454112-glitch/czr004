# Repair5G.5.67 — Large-Scale Tail-Safe Goal-Aware Direct-Theta Actor

**副标题：真实大规模数据、3000-agent curriculum、时间边界审计与 48h+ RTX5090 训练总纲**

- Project: `czr004`
- Repository: `czr5454112-glitch/czr004`
- Source branch: `server-code`
- Source commit: `43c9bd2a11316a073fea5c2908fe70e9ebba6418`
- Previous round: `Repair5G.5.66`
- New round: `Repair5G.5.67`
- Primary research target: learned actor > paper-faithful additive LTM
- Co-primary research target: learned actor > frozen hand-designed static-flow shield
- Stretch/internal target: learned actor > globally tuned `g556_c063174`
- Deployment contract: one instance-conditioned neural forward pass produces one bounded continuous `UpdateParams theta`, fixed for the complete solver run
- Maximum planned agent tier: **3000 agents**
- Minimum intended GPU-active training campaign: **48 hours**
- Preferred total GPU-active campaign: **60–72 hours**, excluding solver-label generation and idle time

---

# 0. Executive mandate

The project objective is unchanged:

```text
replace the coarse additive UpdateLTM rule from the LTM paper
with a learned, instance-conditioned, bounded continuous UpdateParams predictor,
while keeping LaCAM*/PIBT/search semantics unchanged.
```

The method must remain:

```text
physical map graph
+ actual paired starts/goals
+ OD-flow representation
+ C0 congestion/conflict prior
+ F0 goal-progress prior
+ agent count/density
+ solver budget
+ LTM iteration budget
        ↓
goal-aware graph/set/attention neural actor
        ↓
one bounded continuous 15D dual-channel theta
        ↓
ordinary trace-driven C/F traffic map updates
        ↓
ordinary LaCAM*/PIBT search
```

This round explicitly preserves the user’s preferred research route:

```text
train a neural network to predict the UpdateLTM parameters directly.
```

It must not become:

```text
candidate-ID classification
nearest-neighbor theta retrieval
finite codebook selection
runtime selector over hand-written rules
agent-action prediction
PIBT priority prediction
learned restart selection
candidate deletion
learned collision handling
runtime-varying theta
deployment-time critic arbitration
```

A training-only critic, teacher, safe-set model, uncertainty model, or surrogate is allowed. The exported actor must remain critic-free and emit exactly one continuous theta.

---

# 1. Correct scientific interpretation of G5.66

## 1.1 G5.66 was a clean completed experiment

The GitHub branch `server-code` points to:

```text
43c9bd2a Complete G5.66 three-tier actor experiment
```

The committed run reports:

```text
valid context bank: 6000
blind contexts available: 1031
blind contexts replayed: 1000
blind executed rows: 6000
actor rows: 2000
exact materialization: 1.0
candidate recognition: 1.0
scenario hash match: 1.0
identity retention: 1.0
```

The run is therefore not invalid or incomplete.

## 1.2 The central quality signal is strong

Aggregating the two frozen blind actor checkpoints, G5.66 reported:

| Baseline | Median relative improvement | Better outside margin | Success gains | Success regressions |
|---|---:|---:|---:|---:|
| additive LTM | 13.22% | 1650 / 2000 | 254 / 2000 | 12 / 2000 |
| frozen static-flow | 4.69% | 1009 / 2000 | 50 / 2000 | 30 / 2000 |
| g556 | 0.65% | 186 / 2000 | 21 / 2000 | 23 / 2000 |

Additional tail-quality values were:

```text
q95 harmful delta vs additive    = 0.000
q95 harmful delta vs static-flow = 0.0074
q95 harmful delta vs g556        = 0.2628
applied quality margin           = 0.05
```

Interpretation:

```text
vs additive:
  large and convincing central benefit;
  success gains greatly exceed raw regressions;
  both-success harmful-quality tail is very small.

vs static-flow:
  moderate but meaningful central benefit;
  raw success boundary remains the main blocker;
  both-success harmful-quality q95 remains below the applied margin.

vs g556:
  only a small central benefit;
  gains do not exceed regressions;
  harmful tail is genuinely too large.
```

## 1.3 G5.66 is good research evidence but not a deployment pass

The correct verdict is:

```text
good:
  the neural direct-theta route has learned real solver value;
  the effect against additive LTM is large;
  the effect against the hand static-flow rule is nontrivial;
  the run is materially cleaner than earlier rounds.

bad:
  the current actor is not tail-safe enough for deployment;
  the g556 comparison is not yet positive;
  raw success regressions remain.

inconclusive:
  the existing timing/repeatability protocol does not yet prove that every
  raw success regression is a stable theta-caused failure.
```

This is not a reason to abandon direct neural parameter prediction.

It is a reason to:

```text
1. repair the supervision and repeatability protocol;
2. adjudicate the raw timeout regressions;
3. enlarge the number and diversity of independent contexts;
4. stop averaging incompatible safe theta modes;
5. train a substantially stronger actor for a genuinely large compute budget.
```

---

# 2. Revised claim hierarchy

The three baselines remain useful, but they do not carry equal scientific meaning.

## Primary Claim A — learned UpdateLTM beats paper-faithful additive LTM

This is the direct project objective.

A successful Claim A supports:

```text
learning-enhanced UpdateLTM replaces the coarse additive update from LTM
and improves closed-loop LaCAM* solver performance.
```

## Co-primary Claim B — learned UpdateLTM beats frozen static-flow

The static-flow shield is a real hand-designed contribution and a strong ablation.

A successful Claim B supports:

```text
the neural actor improves beyond both the original additive update
and a carefully designed non-learned dual-channel flow-shield rule.
```

This is already a substantial learning contribution.

## Stretch Claim C — learned UpdateLTM beats g556

`g556_c063174` remains valuable research. It represents an expensive globally tuned fixed parameter vector.

However, its role is:

```text
strong fixed-global tuning baseline
and deployment reference,
not the definition of whether the learning idea has scientific value.
```

A/B success with C failure means:

```text
the learning paper result can still be strong;
g556 remains the deployment baseline;
instance conditioning has not yet surpassed the best global tuning.
```

The final paper should present:

```text
additive LTM
→ hand static-flow
→ globally tuned fixed g556
→ learned instance-conditioned direct theta
```

but the main headline should be A/B, not “all value disappears unless g556 is beaten.”

---

# 3. High-priority audit findings in the G5.66 implementation

These findings must be addressed before expensive data acquisition.

## 3.1 The Label-v5.3 safe predicate omitted additive success regressions

Current logic in `create_labelv53_from_pairs` effectively uses:

```python
safe =
    not success_regression_vs_g556
    and not success_regression_vs_static_flow
```

It omits:

```text
success_regression_vs_additive
```

Consequences:

```text
a candidate that turns an additive success into actor failure
can still be marked development-safe
if it does not simultaneously regress against static-flow or g556.
```

Required fix:

```text
safe_A = no supported regression vs additive
safe_B = no supported regression vs static-flow
safe_C = no supported regression vs g556

primary_safe = safe_A and safe_B
stretch_safe = primary_safe and safe_C
```

No combined safe label may silently omit Tier A.

## 3.2 The positive predicate is “better than any baseline”

Current logic allows:

```text
positive = safe and any(delta_A, delta_B, delta_C < -margin)
```

This can label a candidate positive because it beats additive while being materially worse in quality against static-flow or g556.

Required replacement:

```text
positive_A
positive_B
positive_C
joint_positive_AB
joint_positive_ABC
```

Primary actor training must prioritize:

```text
hard constraint: stable safety vs A and B
objective 1: improve additive
objective 2: improve static-flow
secondary objective: improve g556 where supported
```

## 3.3 “Repeatability” did not perform repeated same-pair executions

The G5.66 repeatability phase used 48 contexts with one execution of each method. It did not assign multiple replicate IDs to the same:

```text
map + assignment + theta + budget + LTM iterations
```

The summary nevertheless recorded:

```text
same_pair_repeats = 48
worker_contention_compared = true
```

The second field is hard-coded rather than demonstrated by a paired single-worker versus multi-worker experiment.

Required fix:

```text
repeat_count >= 10 for every audited boundary context
repeat_count >= 5 for a broad calibration panel
replicate_id mandatory
randomized balanced method order
single process
one solver worker
fixed CPU affinity
OMP_NUM_THREADS=1
MKL_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
no simultaneous GPU training
```

A single execution is not a repeat.

## 3.4 Main solver replays used `max_workers=8`

G5.66 used one worker for the nominal repeatability panel but up to eight workers for:

```text
field-group response
development replay
blind replay
```

For short budgets from 0.5 to 8 seconds, concurrent processes may create wall-clock boundary flips.

Required fix:

```text
broad data collection may use parallel workers,
but all success-regression adjudication must be single-process and CPU-pinned.
```

Raw parallel-run failures and supported single-worker failures must be reported separately.

## 3.5 Actor training had only 624 training contexts

Although the valid bank contained 6000 contexts and Label-v5.3 contained 1021 contexts, the actual actor matrix reports:

```text
train examples      = 624
validation examples = 397
```

The exact actor training stage took approximately:

```text
5466.8 seconds ≈ 1.52 hours
```

This is far below the intended scale for a graph/OD attention model.

The 50,048 candidate rows are not 50,048 independent MAPF contexts. They are multiple theta outcomes attached to 1021 contexts.

## 3.6 The actor target averaged many safe/positive thetas

Current target construction computes a weighted arithmetic mean of candidate theta vectors.

This is unsafe when the valid theta set is multimodal:

```text
safe mode 1 + safe mode 2
        arithmetic average
may fall into an unsupported or harmful region.
```

Required fix:

```text
set-valued target loss
or conservative medoid target
or differentiable safe-critic actor optimization
```

Do not reduce a multimodal safe set to a single coordinate-wise average.

## 3.7 Checkpoint selection optimized theta-label L1, not solver tail

The actor was early-stopped and ranked primarily by:

```text
validation_labelv53_normalized_l1
validation_noop_deviation
```

This does not directly optimize:

```text
success regression probability
Tier-A/B solver quality
q95 harmful delta
CVaR
time-to-first-solution
search effort
```

Required fix:

```text
offline loss may screen checkpoints,
but development solver replay must select the primary actor
using a pre-registered lexicographic A/B safety and utility criterion.
```

## 3.8 The critic’s “calibrated” gate was too weak

The critic was declared calibrated if:

```text
prediction coverage was complete
and physical-map leakage was zero.
```

Its reported values included:

```text
binary Brier mean = 0.0269
delta OOF MAE     = 0.3633
effort-log MAE    = 1.1908
```

For rare regressions, Brier score must be compared to a prevalence-only baseline. Coverage is not calibration.

Required metrics:

```text
AUROC
AUPRC
Brier skill score vs prevalence baseline
ECE / adaptive ECE
calibration slope/intercept
reliability diagram
recall of supported regressions at fixed 1% and 5% false-positive rates
quantile coverage for q50/q90/q95
per-map-family and per-agent-tier calibration
```

## 3.9 The scaling summary was a placeholder matrix

`write_scaling_summary` wrote labels such as:

```text
512
1000
2000
all-valid
```

but did not actually retrain and replay each data scale.

Required fix:

```text
real nested-context scaling runs
with identical model/seed/steps and exact solver replay.
```

## 3.10 Blind reporting pooled two checkpoints

The blind summary contained 2000 actor pairs for 1000 contexts because it evaluated two actor checkpoints.

That is useful replication, but it is not a single primary paper model.

Required fix:

```text
pre-register exactly one primary actor checkpoint before blind access;
report secondary seeds/checkpoints separately;
never describe checkpoint-context rows as independent instances.
```

## 3.11 Current agent range stopped at 80

The G5.66 valid bank used:

```text
8, 12, 16, 24, 32, 48, 64, 80 agents
```

This does not test large-scale generalization.

G5.67 must extend the context and model pipeline to 3000 agents.

## 3.12 Remote provenance was incomplete

The remote run directory was not a full Git checkout, causing provenance log loss.

Required fix:

```text
run from a complete clean Git worktree
at a recorded commit;
do not upload only a partial source subset.
```

---

# 4. Ranked failure hypotheses

G5.67 must distinguish these hypotheses rather than assuming only “not enough data.”

## H1 — wall-clock boundary and worker contention

Evidence:

```text
short 0.5–8s budgets
eight-worker replay
no true same-pair repeats
success regressions are rare
both-success q95 harm vs additive/static-flow is small
```

Prediction:

```text
many raw regressions disappear or become unstable under pinned repeated runs,
or recover at a small symmetric budget increase.
```

## H2 — incorrect safety/positive labels

Evidence:

```text
additive regression omitted from safe predicate
any-tier improvement can make a candidate positive
```

Prediction:

```text
rebuilding labels with explicit A/B safety reduces regressions
even without substantially more data.
```

## H3 — insufficient independent context diversity

Evidence:

```text
624 actor train contexts
35 physical maps in critic training
agents only 8–80
```

Prediction:

```text
real nested scaling from 1k to 36k unique labeled contexts
steadily improves map-family transfer and supported regression rate.
```

## H4 — multimodal safe theta averaging

Evidence:

```text
many candidates per context
one arithmetic-mean theta target
```

Prediction:

```text
safe-set nearest loss or conservative medoid targets
improve tail safety while preserving median gains.
```

## H5 — representation bottleneck at high agent count

Evidence:

```text
current OD cross-attention was designed and tested only at <=80 agents
```

Prediction:

```text
chunked Set Transformer / Perceiver latent OD encoding
outperforms naive full-token attention and scalar pooling at 1000–3000 agents.
```

## H6 — true theta-causal tail

Prediction:

```text
actor remains stably worse under 10+ pinned repeats,
fails to recover at 2–3x budget,
and uses substantially worse search effort.
```

If H6 dominates after all repairs, the round should shrink the residual trust or change the training objective, not hide the failure by changing the timeout definition.

---

# 5. Literature-informed design principles

G5.67 should borrow principles, not tasks, from recent learning-based MAPF work.

## 5.1 Guidance Graph Optimization — IJCAI 2024

Relevant lessons:

```text
simulator outcomes are valid supervision for guidance/update models;
edge/update guidance can scale to large maps and up to 3000 agents;
random, warehouse, room, maze, empty, random-64, and den312d
form a useful map diversity anchor;
strong hand-designed traffic-flow baselines remain necessary.
```

G5.67 remains one-shot/anytime LaCAM*+LTM rather than lifelong PIBT, so metrics and solver semantics must not be copied blindly.

## 5.2 SILLM — ICRA 2025

Relevant lessons:

```text
large-scale learning requires systematic data collection;
training at hundreds of agents can transfer to much larger evaluation scales;
pretraining/bootstrapping and repeated data-collection iterations matter;
structured warehouse, city, and random maps should all be represented;
modern GPU training must be paired with scalable CPU simulation.
```

SILLM predicts actions, whereas G5.67 predicts one UpdateLTM theta. The project must not import its action-policy semantics.

## 5.3 CACTUS — AAMAS 2024

Relevant lessons:

```text
curriculum should increase difficulty only after supported competence;
map size, obstacle density, goal distance, and agent count should vary;
fixed test instances and repeated runs are important;
structured mazes/rooms expose failures hidden by random maps.
```

G5.67 should use a curriculum over:

```text
agent count
agent density
OD path length
bottleneck pressure
opposing-flow pressure
map size
map structure
solver budget
```

## 5.4 LaGAT — recent hybrid-search work

Relevant lessons:

```text
graph attention can improve classical search;
pretrain-then-fine-tune is useful;
imperfect neural guidance needs explicit deadlock/tail handling.
```

G5.67 does not copy action guidance. It uses graph attention only to infer bounded UpdateLTM parameters.

## 5.5 MovingAI MAPF benchmarks

Relevant lessons:

```text
use recognized canonical maps and fixed random/even scenario sets;
split by physical map, not by row;
include short and long OD demands;
evaluate one agent-count ladder rather than one hand-picked density.
```

---

# 6. P0 — Mandatory code and protocol repair before expensive runs

Codex must create a fresh worktree from `server-code@43c9bd2a`.

Do not use or alter unrelated dirty files in the user’s current working tree.

Recommended setup:

```powershell
git fetch origin
git worktree add C:\PROGRAMING\czr004-g567 -b repair5g567-large-scale-tail-safe origin/server-code
cd C:\PROGRAMING\czr004-g567
git rev-parse HEAD
git status --short
```

Required initial state:

```text
HEAD = 43c9bd2a11316a073fea5c2908fe70e9ebba6418
clean worktree
submodules recorded
full repository available remotely
```

## P0.1 Label semantics tests

Add tests proving:

```text
an additive regression can never be primary_safe;
a static-flow regression can never be primary_safe;
a g556-only regression may remain AB-safe but not ABC-safe;
better-vs-additive alone cannot create joint_positive_AB;
quality harm vs B/C is not hidden by improvement vs A;
single-run boundary rows are marked uncertain, not stable-safe.
```

## P0.2 True replicate schema

Every repeated row must contain:

```text
replicate_id
replicate_group_id
execution_order_index
cpu_affinity
worker_count
OMP/MKL/OpenBLAS thread counts
host load snapshot
solver internal time limit
process hard timeout
method start/end timestamps
```

## P0.3 Time semantics audit

Document the difference between:

```text
solver internal budget
process wall-clock timeout
actor inference time
process startup overhead
queueing/CPU contention
```

Primary comparison:

```text
same solver-internal budget for every method.
```

Process hard timeout may include a symmetric overhead allowance, for example:

```text
hard_timeout = max(nominal_budget + 0.25s, nominal_budget * 1.10)
```

but this overhead allowance must apply equally to actor and all baselines and must not increase the solver’s internal budget.

## P0.4 Critic calibration tests

Fail closed unless:

```text
Brier skill > 0 against prevalence baseline
AUPRC materially exceeds event prevalence
q90/q95 empirical coverage is calibrated
regression recall at fixed FPR is reported
no physical-map or scenario leakage
```

## P0.5 Real scaling implementation

Replace the placeholder scaling writer with actual:

```text
nested context manifests
training runs
checkpoint hashes
development solver replays
per-scale statistics
```

## P0.6 3000-agent memory and correctness smoke

Before data generation:

```text
8, 64, 256, 1000, 2000, 3000 agent synthetic smokes
OD-token count exactly equals agent count
no agent mass dropped
path_found_rate = 1.0
no duplicate starts/goals
finite C0/F0 features
bounded memory
deterministic batching
same theta for identical input
```

## P0.7 Artifact integrity

Require:

```text
manifest written only after final files are complete
all hashes rechecked
large CSVs compressed deterministically
raw local path recorded
Git LFS or .gz policy explicit
remote run is a full Git checkout
```

No large training or solver run may start until all P0 tests pass.

---

# 7. P1 — G5.66 success-regression adjudication

The old G5.66 blind set is now development evidence. Use it for autopsy, never again as fresh blind evidence.

## P1.1 Extract every tail case

Create separate tables for:

```text
12 raw regressions vs additive
30 raw regressions vs static-flow
23 raw regressions vs g556
all quality-worse rows outside margin
all success gains
```

Deduplicate by:

```text
evaluation_uid
actor checkpoint
baseline tier
```

Report concentration by:

```text
actor A1/A2
map family
physical map
agent count
agent density
budget
LTM iterations
OD regime
theta field group
```

## P1.2 Pinned nominal-budget repeats

For every unique raw regression:

```text
repeat each actor-baseline pair 10 times minimum
preferred 20 times
single process
single solver worker
fixed CPU affinity
balanced AB/BA order
no simultaneous training or data generation
```

Also repeat a matched sample of:

```text
success gains
both-success improvements
neutral cases
```

This prevents auditing only failures.

## P1.3 Symmetric budget-recovery curves

For all suspect contexts run actor and baseline at:

```text
1.00x
1.10x
1.25x
1.50x
2.00x
3.00x
```

The primary scientific result remains 1.00x.

The curves answer:

```text
is the actor stably wrong,
slightly late,
or merely affected by timing noise?
```

## P1.4 Equal-search-work diagnostics

Run matched limits for:

```text
expanded nodes
high-level expansions
low-level PIBT calls
```

A method that fails under equal wall-clock but succeeds under equal work has an overhead problem. A method that uses more search effort and still fails has a guidance problem.

## P1.5 Tail classification

Each raw regression receives exactly one primary classification:

```text
protocol_identity_error
measurement_or_contention_noise
unstable_boundary
stable_late_recovery
stable_theta_causal_regression
unresolved
```

Suggested supported regression rule:

```text
baseline success frequency >= 0.8
actor success frequency <= 0.2
paired difference supported by a one-sided 95% interval
identity/fingerprint checks all pass
```

Do not promote the method by simply reclassifying failures without evidence.

---

# 8. P2 — Large-scale valid context bank

## 8.1 Scale targets

Create two banks.

### Unlabeled representation bank

Used for self-supervised encoder pretraining:

```text
minimum:   100,000 unique valid contexts
preferred: 150,000–200,000 unique valid contexts
```

### Exact solver-labeled bank

Used for candidate response, critic, and actor learning:

```text
minimum:   24,000 unique labeled contexts
preferred: 36,000–48,000 unique labeled contexts
```

The unit is a unique MAPF context, not a candidate row.

### Exact solver-row target

```text
minimum:   1,000,000 candidate/context solver rows
preferred: 1,500,000–2,000,000 rows
```

Use multi-fidelity acquisition to control cost.

## 8.2 Physical map target

```text
minimum unique physical maps: 256
preferred: 384+
minimum map families: 16
preferred: 24+
```

Derived variants sharing the same parent/base map must remain in one split.

## 8.3 Map families

### Canonical MovingAI families

Include actual files, not only synthetic approximations:

```text
empty:
  8x8, 16x16, 32x32, 48x48, plus larger generated 64/96/128

random:
  32x32 and 64x64 at 10% and 20% obstacles
  generated 96/128/192/256 at 10/20/30%

maze:
  32x32 and 128x128
  corridor widths 1, 2, 4, 8, 10

room:
  32x32 and 64x64
  room sizes 4, 8, 16
  generated 96/128 room variants

warehouse:
  warehouse-10-20-10-2-1
  warehouse-10-20-10-2-2
  warehouse-20-40-10-2-1
  warehouse-20-40-10-2-2

game/city:
  den312d
  den520d
  Berlin_1_256
  Boston_0_256
  Paris_1_256
  lak303d
  ost003d
  brc202d
  ht_chantry
  ht_mansion_n
  lt_gallowstemplar_n
  w_woundedcoast
```

### GGO anchor families

Reproduce compatible one-shot contexts on:

```text
random-32-32-20
warehouse-33x36 style
room-64-64-8
maze-32-32-4
empty-48-48
random-64-64-20
den312d
```

Agent-count anchors should include:

```text
400, 1000, 1200, 1500, and 3000 where map capacity permits.
```

### Large LRR/SILLM-style families

When licensing and local data allow, include:

```text
sortation
large warehouse
Paris
Berlin
random 10%
random 20%
```

### Synthetic topology stress families

Retain and expand:

```text
connector
tunnel
single/double choke
loop
tree
string
corners
cross
lanes
plaza
islands
chambers
spiral
multi-room doors
one-way-like aisle geometry
adversarial opposing corridors
```

Synthetic maps may not dominate the final blind panel.

## 8.4 Agent curriculum

Use both exact canonical counts and density-conditioned counts.

Canonical agent counts:

```text
8, 16, 32, 50, 64,
100, 128, 200, 256,
400, 512, 768,
1000, 1200, 1500,
2000, 2500, 3000
```

Recommended context distribution:

| Tier | Agent range | Share of valid bank | Purpose |
|---|---:|---:|---|
| T0 | 8–64 | 12% | parity, small-map transfer, low-density controls |
| T1 | 100–256 | 23% | canonical LTM regime |
| T2 | 400–768 | 25% | dense/scalable MAPF |
| T3 | 1000–1500 | 25% | GGO/SILLM-inspired large scale |
| T4 | 2000–3000 | 15% | extreme stress and extrapolation |

T4 requirements:

```text
at least 5000 valid bank contexts
at least 1000 exact-labeled training contexts
at least 200 calibration contexts
at least 300 blind contexts
```

Do not place 3000 agents on maps that cannot support meaningful free-space density.

## 8.5 Density curriculum

Agent count alone is insufficient.

Stratify:

```text
low density:      5–15%
moderate density: 15–30%
high density:     30–50%
extreme density:  50–70% diagnostic subset
```

Record:

```text
agents / free cells
agents / biconnected-core cells
agents / effective reachable component
OD flow through top-1%, top-5%, top-10% bottleneck edges
```

## 8.6 Start-goal regimes

Include:

```text
uniform random
MovingAI random scenarios
MovingAI even-distance scenarios
short-range local goals
long-range cross-map goals
opposite-side cross flow
adversarial opposing flow
central choke
room-to-room doors
warehouse aisle-to-aisle
clustered starts → dispersed goals
dispersed starts → clustered goals
many-to-many bottleneck
perimeter → center
center → perimeter
cyclic flow
high-overlap shortest-path corridors
low-overlap control
```

## 8.7 Solver budget curriculum

Use:

```text
0.5s, 0.75s, 1s, 1.5s, 2s, 3s, 5s, 8s,
plus 12s and 20s for large-agent contexts where necessary.
```

Budget distribution must be conditional on agent tier and map size. Do not interpret a 3000-agent failure at 0.5s as equivalent to an 80-agent failure at 0.5s.

## 8.8 Split policy

Freeze before any labels:

```text
TRAIN
VALIDATION
CALIBRATION
DEVELOPMENT-HELDOUT
BLIND
FAMILY-OOD-BLIND
INVALID-QUARANTINE
```

Suggested minimum exact-labeled counts:

```text
TRAIN:              24,000
VALIDATION:          4,000
CALIBRATION:         3,000
DEVELOPMENT-HELDOUT: 4,000
BLIND:               5,000
```

Rules:

```text
split by parent physical-map identity
no map-derived variants across splits
no scenario seed reuse
no assignment hash reuse
no blind candidate outcomes before checkpoint freeze
family-OOD blind contains entire unseen families or canonical map roots
```

## 8.9 Validity rules

Every context must satisfy:

```text
map file exists and hash matches
scenario exists and hash matches
unique starts
unique goals
all starts/goals traversable
all paired OD demands reachable
path_found_rate = 1.0
OD token count = agent count
C0/F0 edge mass finite
no dropped agents at 3000
assignment hash exact
no train/blind parent-map overlap
```

---

# 9. P3 — Candidate acquisition and exact solver labels

## 9.1 Candidate proposal mixture

For each exact-labeled context, draw candidates from:

```text
20% local perturbations around additive-compatible region
25% local perturbations around frozen static-flow
25% local perturbations around g556
10% Sobol / Latin-hypercube global bounded exploration
10% field-group causal interventions
10% actor/critic uncertainty-driven proposals
```

After the first actor exists, use active acquisition:

```text
uncertain high-benefit contexts
predicted success-boundary contexts
high-agent/high-density contexts
underrepresented map families
known G5.66 regression analogues
```

## 9.2 Multi-fidelity exact evaluation

Stage F0:

```text
short probe on broad candidate set
```

Stage F1:

```text
nominal full budget on top, uncertain, and harmful candidates
```

Stage F2:

```text
replicated pinned evaluation near success boundaries
```

Stage F3:

```text
budget-recovery and equal-work curves for supported tail cases
```

Never train a final safety label from only F0.

## 9.3 Replication allocation

Broad noise panel:

```text
>=2000 context/candidate pairs
5 repeats each
```

Boundary panel:

```text
all success gains/regressions
10–20 repeats each
```

Large-agent panel:

```text
representative 1000/1500/2000/2500/3000-agent pairs
>=5 repeats
```

## 9.4 Label-v5.4 schema

Required labels:

```text
stable_success_probability_actor
stable_success_probability_additive
stable_success_probability_static
stable_success_probability_g556

supported_regression_A
supported_regression_B
supported_regression_C

supported_gain_A
supported_gain_B
supported_gain_C

delta_A_q10/q50/q90/q95
delta_B_q10/q50/q90/q95
delta_C_q10/q50/q90/q95

time_to_recovery_multiplier
equal_work_delta
runtime_delta
expanded_node_delta
PIBT_call_delta

safe_A
safe_B
safe_C
primary_safe_AB
stretch_safe_ABC

positive_A
positive_B
positive_C
joint_positive_AB
joint_positive_ABC

measurement_confidence
replicate_count
```

## 9.5 Do not average the safe set

For context `i`, preserve:

```text
S_i^AB = set of supported-safe candidates vs additive and static-flow
S_i^ABC = subset also safe vs g556
```

Actor supervision options, in priority order:

### Option 1 — nearest-safe-set loss

```text
L_set(theta_hat, S_i) = min(theta in S_i) distance(theta_hat, theta)
```

### Option 2 — conservative medoid

Select the candidate that minimizes within-safe-set distance while maximizing lexicographic A/B utility.

### Option 3 — frozen differentiable critic

Backpropagate through a well-calibrated training-only critic:

```text
minimize predicted regression UCB and q95 harm
maximize predicted A/B gain LCB
```

The final actor still emits one theta.

Arithmetic averaging may be kept only as an ablation.

---

# 10. P4 — Model architecture exploration

## 10.1 Permanent input floor

Every rich actor must consume:

```text
physical graph topology
C0 directed edge prior
F0 directed edge prior
paired OD information
agent count and density
budget and LTM iterations
map dimensions and free-space statistics
```

## 10.2 Required controls

```text
B0: fixed g556
B1: learned global theta independent of instance
C0: scalar-only context actor
A2: current G5.66 OD graph cross-attention actor
```

## 10.3 New primary architecture candidates

### A5 — hierarchical OD Perceiver actor

Purpose:

```text
handle 8–3000 OD pairs without O(N²) token attention.
```

Design:

```text
chunked OD token embedding
64–128 learned latent tokens
cross-attention from latent tokens to OD chunks
latent self-attention
map/C0/F0 summaries cross-attend to OD latents
15D bounded theta head
```

### A6 — multi-scale topology/C0/F0 actor

Design:

```text
shared local graph trunk
separate topology/C0/F0 adapters
bottleneck-node tokens
corridor/room/aisle region pooling
global graph transformer
OD Perceiver fusion
field-group residual and trust heads
```

### A7 — OD-flow hypergraph ablation

Design:

```text
construct training-time or input-time flow groups from overlapping OD corridors
hyperedges represent groups sharing bottleneck regions
hypergraph attention summarizes group pressure
final output remains one theta
```

A7 is an ablation, not permission to predict actions.

## 10.4 Output parameterization

Compare:

```text
R1: full 15D bounded residual around g556
R2: full 15D bounded residual around static-flow
R3: learned 6-group residual + within-group offsets
R4: low-rank learned residual basis from safe candidates
```

Each deployed model emits one deterministic 15D theta.

## 10.5 Trust design

Trust is not a selector.

Allowed:

```text
six continuous trust values internally scale six theta field groups
before producing the final one theta.
```

Required trust supervision:

```text
field-group causal response
tail risk
safe-set support
epistemic uncertainty
```

## 10.6 Model size

Target primary model:

```text
20–60 million trainable parameters
hidden dimension 256–384
6–10 graph/latent layers
8 attention heads where feasible
BF16 training
gradient accumulation
```

Do not enlarge the network without verifying 3000-agent memory and throughput.

---

# 11. P5 — 48h+ RTX5090 training campaign

The scientific requirement is not to “sleep for 48 hours.” The GPU must perform useful training, validation, or hard-negative mining.

## 11.1 Minimum campaign

```text
GPU-active wall time >= 48 hours
preferred total       = 60–72 hours
```

Exclude:

```text
solver-label generation
CPU-only preprocessing
idle tmux time
failed startup time
waiting for files
```

Record GPU utilization and active training time.

## 11.2 Stage schedule

### Stage T0 — architecture and pipeline screen: 6–10h

Train A2/A5/A6/A7 on a fixed subset.

Goal:

```text
eliminate broken or memory-unsafe models;
select at most two serious architectures.
```

No blind access.

### Stage T1 — self-supervised representation pretraining: 10–14h

Tasks:

```text
masked C0/F0 edge reconstruction
OD-flow histogram prediction
agent density prediction
bottleneck load prediction
shortest-path length distribution
same-map/different-assignment contrast
same-assignment/perturbed-budget consistency
```

Use the 100k–200k unlabeled bank.

### Stage T2 — safe-set supervised actor training: 16–22h

Loss components:

```text
nearest-safe-set theta loss
A/B lexicographic utility
anchor regularization
field-group causal consistency
map-family-balanced weighting
agent-tier-balanced weighting
```

### Stage T3 — risk-aware actor optimization: 10–14h

Use a frozen, cross-fitted, calibrated neural critic.

Loss:

```text
success regression UCB vs A/B
q95/CVaR harm vs A/B
gain LCB vs A/B
secondary g556 utility
unsupported-region penalty
```

### Stage T4 — hard-tail fine-tuning: 8–12h

Mine:

```text
G5.66 tail analogues
short-budget boundary contexts
high-density bottlenecks
1000–3000-agent failures
family-OOD errors
```

Use oversampling without erasing common-case quality.

### Stage T5 — multi-seed confirmation: 8–12h

Fine-tune or retrain three final seeds from the frozen representation checkpoint.

Only development evidence may choose the primary seed.

## 11.3 Optimizer and logging requirements

Use:

```text
AdamW
BF16
gradient clipping
cosine or plateau-aware learning rate
EMA checkpoint optional
deterministic seeds
gradient accumulation
mixed-size batching by graph/agent token budget
```

Log every 15 minutes or every fixed step interval:

```text
optimizer step
unique contexts consumed
agent-tier histogram
map-family histogram
loss components
safe-set coverage
critic risk estimates
validation A/B/C metrics
GPU utilization
GPU memory
examples/sec
OD tokens/sec
```

Checkpoint at least every:

```text
1 hour
or 5000 optimizer steps
```

## 11.4 Early stopping rule

Do not terminate the campaign merely because theta L1 plateaus.

If one stage plateaus:

```text
move remaining compute to hard-negative mining,
risk-aware fine-tuning,
or a pre-registered alternate objective.
```

Do not continue uselessly on an overfit objective.

---

# 12. P6 — Real data scaling study

Train the same architecture and seed on nested labeled-context subsets:

```text
1k
4k
12k
24k
36k
all available
```

Hold constant:

```text
optimizer steps or total context exposures
model size
validation split
candidate acquisition source
loss weights
```

For each scale, report:

```text
offline safe-set loss
critic-estimated risk
development exact solver A/B/C
supported regressions
median relative improvement
q95 harm
map-family transfer
agent-tier transfer
```

The scaling conclusion must distinguish:

```text
more candidate rows on the same contexts
versus
more independent contexts.
```

---

# 13. P7 — Development evaluation and primary actor freeze

## 13.1 Development panel

Minimum:

```text
4000 unique contexts
>=80 physical maps
all agent tiers
all budgets
all major map families
```

## 13.2 Checkpoint selection

Use a pre-registered lexicographic rule:

```text
1. minimize supported regression rate vs additive
2. minimize supported regression rate vs static-flow
3. enforce Tier-A/B success non-inferiority
4. minimize A/B q95 harmful delta
5. maximize median improvement vs additive
6. maximize median improvement vs static-flow
7. use g556 only as secondary tie-breaker
```

Freeze:

```text
one primary checkpoint
two secondary seed checkpoints
exact hashes
model config
dataset hash
loss config
decision rule
```

No blind access before freeze.

---

# 14. P8 — Blind evaluation

## 14.1 Blind scope

Minimum:

```text
5000 unique contexts
>=40 unseen parent physical maps
>=300 contexts in the 2000–3000-agent tier
separate family-OOD panel
```

Run:

```text
paper-faithful additive LTM
frozen static-flow
g556
one primary actor
```

Secondary actor seeds are reported separately and must not be pooled into the primary instance count.

## 14.2 Primary equal-budget result

Every method receives the same solver-internal budget.

Report:

```text
success rate
sum-of-loss ratio
median and mean relative improvement
trimmed mean
quality-time AUC
TTFS
expanded nodes
high-level expansions
PIBT calls
actor inference overhead
```

## 14.3 Grace-time diagnostics

Run symmetric recovery curves for all raw success disagreements.

Do not use grace time to rewrite the equal-budget result.

Report:

```text
fraction recovered by 1.10x
fraction recovered by 1.25x
fraction recovered by 1.50x
fraction recovered by 2.00x
fraction still failed at 3.00x
```

---

# 15. Statistical gates

All primary statistics use:

```text
one primary actor
unique evaluation_uid
cluster bootstrap by parent physical map
95% confidence intervals
family and agent-tier stratification
```

## 15.1 Claim A research pass

Suggested criteria:

```text
success-rate difference vs additive:
  one-sided 95% lower bound > -0.25 percentage points

median relative improvement:
  point estimate >= 10%
  cluster-bootstrap lower bound >= 8%

supported regression rate:
  upper 95% bound <= 0.5%

map-family consistency:
  majority of families improve
  no major family shows a large supported success collapse
```

## 15.2 Claim B research pass

Suggested criteria:

```text
success-rate difference vs static-flow:
  one-sided 95% lower bound > -0.5 percentage points

median relative improvement:
  point estimate >= 3%
  cluster-bootstrap lower bound > 1%

q95 harmful quality delta:
  <= calibrated measurement margin

supported regression rate:
  upper 95% bound <= 1%
```

## 15.3 Strong A/B pass

```text
A median >= 12%
B median >= 5%
positive mean and trimmed-mean evidence
stable across agent tiers up to 3000
family-OOD result remains positive
```

## 15.4 Claim C research signal

Secondary criterion:

```text
median delta vs g556 < 0
success gains > supported regressions
cluster-bootstrap evidence supports nonzero benefit
q95 harm substantially below G5.66
```

## 15.5 Deployment pass

Deployment remains stricter than research:

```text
zero or near-zero supported regressions under repeated pinned adjudication
no severe family/agent-tier collapse
bounded inference overhead
all identity/fingerprint/provenance checks pass
```

Do not use a deployment gate to erase a valid A/B research result.

---

# 16. Required ablations

## Data

```text
candidate-row scaling with fixed contexts
independent-context scaling
remove large-agent data
remove canonical benchmark maps
remove structured maps
remove family-OOD training
```

## Labels/objective

```text
old arithmetic-mean target
conservative medoid target
nearest-safe-set target
critic-optimized target
without A/B lexicographic safety
without replicate confidence
```

## Representation

```text
scalar-only
without topology
without C0
without F0
without OD pairs
OD mean pooling
OD Perceiver
multi-scale graph
hypergraph flow grouping
```

## Parameterization

```text
g556 anchor
static-flow anchor
full 15D residual
six-group residual
learned low-rank safe basis
without trust
with continuous group trust
```

## Controls

```text
random labels
shuffled labels within map family
shuffled OD pairs
shuffled C0/F0 channels
random features
same parameter-count MLP
fixed global learned theta
```

## Timing

```text
1 worker vs 8 workers
CPU pinned vs unpinned
equal wall-clock
equal node budget
symmetric grace curves
```

---

# 17. Required artifacts

## Governance

```text
czr004_g567_large_scale_tail_safe_direct_actor_plan.md
docs/codex-worklog.md
outputs/reports/phase5p5_repair5g567_bug_log.md
outputs/reports/phase5p5_repair5g567_protocol_overview.md
```

## P0 audits

```text
phase5p5_repair5g567_source_state.json
phase5p5_repair5g567_label_semantics_audit.json
phase5p5_repair5g567_repeatability_protocol_audit.json
phase5p5_repair5g567_time_budget_semantics.md
phase5p5_repair5g567_3000_agent_memory_smoke.json
```

## G5.66 tail

```text
phase5p5_repair5g567_g566_tail_cases.csv
phase5p5_repair5g567_g566_tail_repeats.csv
phase5p5_repair5g567_g566_budget_recovery.csv
phase5p5_repair5g567_g566_tail_classification.csv
phase5p5_repair5g567_g566_tail_autopsy.md
```

## Dataset

```text
phase5p5_repair5g567_parent_map_manifest.csv
phase5p5_repair5g567_context_manifest.csv.gz
phase5p5_repair5g567_split_manifest.csv
phase5p5_repair5g567_validity_audit.csv.gz
phase5p5_repair5g567_agent_tier_summary.json
phase5p5_repair5g567_map_family_summary.json
phase5p5_repair5g567_blind_freeze_manifest.json
```

## Labels

```text
phase5p5_repair5g567_candidate_registry.csv.gz
phase5p5_repair5g567_solver_results.csv.gz
phase5p5_repair5g567_replicates.csv.gz
phase5p5_repair5g567_labelv54_contexts.csv.gz
phase5p5_repair5g567_labelv54_candidates.csv.gz
phase5p5_repair5g567_labelv54_safe_sets.jsonl.zst
phase5p5_repair5g567_labelv54_summary.json
```

## Models

```text
phase5p5_repair5g567_pretraining_summary.json
phase5p5_repair5g567_architecture_screen.csv
phase5p5_repair5g567_training_matrix.csv
phase5p5_repair5g567_training_times.json
phase5p5_repair5g567_gpu_utilization.csv
phase5p5_repair5g567_critic_calibration.json
phase5p5_repair5g567_scaling_summary.json
phase5p5_repair5g567_primary_actor_manifest.json
```

## Solver evaluation

```text
phase5p5_repair5g567_development_pairs.csv.gz
phase5p5_repair5g567_development_summary.json
phase5p5_repair5g567_blind_pairs.csv.gz
phase5p5_repair5g567_blind_summary.json
phase5p5_repair5g567_family_ood_summary.json
phase5p5_repair5g567_grace_curve_summary.json
phase5p5_repair5g567_equal_work_summary.json
```

## Final

```text
phase5p5_repair5g567_claimA_decision.json
phase5p5_repair5g567_claimB_decision.json
phase5p5_repair5g567_claimC_decision.json
phase5p5_repair5g567_final_decision.md
phase5p5_repair5g567_final_decision_summary.json
phase5p5_repair5g567_artifact_manifest.json
phase5p5_repair5g567_checksums.sha256
```

---

# 18. No premature completion

G5.67 is not complete after:

```text
writing a plan
adding wrappers
passing py_compile
generating 100k unlabeled contexts
running one 3000-agent smoke
training for a few hours
reusing G5.66 labels
training on candidate rows without more independent contexts
running only additive/g556 and omitting static-flow
reporting pooled checkpoints
declaring a critic calibrated from coverage alone
giving actor-only extra time and calling that a pass
```

Minimum substantive completion:

```text
1. all P0 bugs fixed and tested
2. true same-pair repeatability protocol
3. G5.66 tail adjudicated
4. >=100k valid unique context bank
5. >=24k unique exact-labeled contexts
6. >=1M exact solver rows
7. map/agent curriculum through 3000 agents
8. safe-set Label-v5.4
9. calibrated cross-fitted training-only critic
10. real nested data scaling
11. >=48 GPU-active training hours
12. one primary actor frozen before blind
13. exact additive/static/g556 blind replay
14. symmetric grace and equal-work diagnostics
15. separate Claim A/B/C decisions
16. full artifact hashes and clean Git provenance
```

If a stage fails, Codex must execute its diagnostic and repair branch rather than ending the round immediately.

---

# 19. Decision vocabulary

```text
g567_source_state_clean
g567_p0_bug_repair_complete
g567_repeatability_protocol_valid
g567_g566_raw_regressions_mostly_timing_noise
g567_g566_supported_theta_tail_confirmed
g567_large_context_bank_ready
g567_3000_agent_contract_valid
g567_labelv54_safe_sets_ready
g567_critic_calibrated
g567_critic_not_calibrated
g567_independent_context_scaling_positive
g567_independent_context_scaling_flat
g567_primary_actor_frozen
g567_claimA_pass
g567_claimA_strong_pass
g567_claimB_pass
g567_claimB_strong_pass
g567_claimC_signal
g567_claimC_fail_keep_g556_deployment
g567_full_success
g567_direct_theta_data_limited_continue
g567_direct_theta_objective_limited_repair
g567_direct_theta_true_tail_blocked
```

---

# 20. Final interpretation matrix

## A passes, B fails, C fails

```text
The learned actor successfully replaces coarse additive LTM,
but has not yet surpassed the hand-designed static-flow shield.
```

## A and B pass, C fails

```text
Core learning-enhanced LTM result succeeds.
The actor beats both paper-faithful additive LTM and the user's
hand-designed static-flow contribution.
g556 remains the fixed-global deployment baseline.
```

## A, B, and C pass

```text
The learned instance-conditioned direct-theta actor supersedes
the original additive rule, the hand static-flow rule,
and the optimized global fixed parameter vector.
```

## A/B central benefit remains but supported regressions persist

```text
Publishable research signal may remain under statistical non-inferiority,
but deployment must stay closed.
Continue tail-safe training or introduce an explicitly disclosed fallback
in a later engineering round.
```

## A fails after repaired labels, true repeats, large data, and fresh blind maps

```text
The current run-static direct 15D theta formulation is not supported
as a reliable replacement for additive LTM.
```

---

# 21. Reference anchors

Primary sources to inspect before implementation:

1. Guidance Graph Optimization for Lifelong Multi-Agent Path Finding, IJCAI 2024  
   Paper: https://arxiv.org/abs/2402.01446  
   Code: https://github.com/lunjohnzhang/ggo_public

2. Deploying Ten Thousand Robots: Scalable Imitation Learning for Lifelong Multi-Agent Path Finding, ICRA 2025  
   Paper: https://arxiv.org/abs/2410.21415  
   Code: https://github.com/DiligentPanda/Scalable-Imitation-Learning-for-LMAPF

3. Confidence-Based Curriculum Learning for Multi-Agent Path Finding, AAMAS 2024  
   Paper: https://arxiv.org/abs/2401.05860  
   Code: https://github.com/thomyphan/rl4mapf

4. Graph Attention-Guided Search for Dense Multi-Agent Pathfinding  
   Paper: https://arxiv.org/abs/2510.17382

5. MovingAI MAPF Benchmarks  
   https://movingai.com/benchmarks/mapf.html

---

# 22. Execution addendum, 2026-06-22

GPT Pro decision state:

```text
g567_stage2_true_a5_and_gate3a_approved
g567_gate3b_blocked_pending_pipeline_repairs
g567_full_campaign_locked
```

Accepted as complete before this addendum:

```text
Stage 0 source/timeout closure
Stage 1 public benchmark ingestion
remote HEAD a2489c91f34bf16d7460f6591672821ba1dbce08 evidence accepted
```

Allowed next execution:

```text
Train one diagnostic-only true A5 checkpoint on 64-256 non-blind contexts.
Run true Gate-3A on >=32 contexts and tiers 32/256/1000/3000.
Gate-3A must prove:
  A5 inference -> continuous theta -> registry -> C++ UpdateLTM -> solver
  public-parent and synthetic contexts both present
  no blind access
  no hard-timeout rows
  exact materialization, candidate recognition, identity retention, and scenario hash rates all 1.0
```

Still forbidden:

```text
server_start_repair5g567_full.sh
100k+ context generation
1M+ solver acquisition
48h+ training campaign
final blind construction/access
astar_v1 as the primary traffic-prior backend
```

Stage-2/Gate-3A repair notes now implemented or fail-closed:

```text
1. response_theta_front_loaded_context_coverage
   Fixed with coverage-first acquisition: every context receives one exact actor candidate before exploratory alpha/group candidates.

2. a5_attention_heads_checkpoint_load_mismatch
   Fixed by saving both heads and attention_heads and loading either alias.

3. true A5 checkpoint audit too weak
   Fixed: Gate-3A now requires artifact_type, variant_id=A5, actor_state_dict,
   labelv54_training=true, diagnostic_only=true, CUDA BF16 training,
   training_context_uids, dataset hash, source commit, OD Perceiver, and graph_global_layers=0.

4. critic_development_split_mismatch
   Corrected in the full main path to fit critic candidates from LABEL_TRAIN,
   with CALIBRATION reserved for calibration evidence.

5. blind_feature_preload_before_primary_freeze
   Fixed: before primary actor freeze, only blind map/scenario/assignment hash manifest is summarized.
   BLIND graph/C0/F0 materialization is delayed until after one primary actor is selected.

6. public_ratio_and_official_scenario_gate_too_weak
   Full validity now fails closed unless LABEL_TRAIN public/canonical >=50%,
   development/blind public/canonical >=70%, parent physical-map hashes >=256,
   and the official MovingAI/MAPF-LNS2 scenario-prefix consumer is ready.
```

Gate-3B remains blocked until all GPT Pro repairs are complete and true Gate-3A passes.

Remote Stage-2A first-attempt findings:

```text
The first remote Stage-2A attempt correctly reached real replay/Label-v5.4/training,
but it did not pass:
  replay process_hard_timeout_rows = 92
  A5 training then hit RTX5090 CUDA OOM on huge diagnostic public maps
  Label-v5.4 candidate rows omitted split metadata, making LABEL_TRAIN unique count report 0

Follow-up repair:
  Stage-2A now blocks before labels/training unless replay is fully materialized with zero hard timeouts.
  Label-v5.4 candidate rows preserve split/map/agent metadata.
  Stage-2A diagnostic training has explicit graph-size bounds and reports them.

This first failed attempt is evidence for an active large-graph training/memory risk.
It is not a Gate-3A pass and it does not unlock Gate-3B or full execution.
```

Uniform-budget correction after operator review:

```text
Operator correction:
  Do not shrink diagnostic training evidence to tiny tiers such as 8/12/16/24.
  Do not use tier-dependent short internal budgets for small/medium maps.
  Use 30.0s solver_internal_time_limit_sec and 60.0s process_hard_timeout_sec
  for every staged primary solver row across all agent counts and all maps.

Implemented contract:
  budget_profile_for_agent_tier now returns 30000 ms / 30.0s / 12 LTM iterations
  with role uniform_30s_all_agent_tiers_primary_exact for every tier and purpose.
  The solver budget audit fails closed on any planned row not using 30.0s/60.0s.
  The valid-context bank summary treats the budget target as uniform 30000 ms,
  not as legacy multi-budget coverage.
  Response-theta generation treats every 30s primary context as selected exact
  evidence and does not expand a full exploratory 30s lattice for smaller tiers.

Status:
  This correction supersedes the invalid 8/12/16/24 diagnostic attempt.
```

Remote Stage-2A uniform-30s first rerun finding:

```text
Observed failure:
  Stage-2A used 64 contexts with tiers 32/64/128/256 and every row recorded
  solver_internal_time_limit_sec=30.0 / process_hard_timeout_sec=60.0.
  The replay still failed closed with process_hard_timeout_rows=24.

Root cause:
  The Python plan had one row per candidate, but the G5.49 probe runner grouped
  additive, static-flow, g556, and actor candidates for the same context into one
  C++ process. The outer process hard timeout was therefore 60s for four planned
  rows combined, not 60s per row.

Repair:
  G5.67 replay now enables row-process isolation. Each planned solver row is
  launched as its own subprocess, so the 60s hard timeout is scoped to the row
  required by the budget contract.

Status:
  The failed rerun is not Gate-3A evidence and does not unlock Gate-3B.
```

Remote Stage-2A row-isolated r5 finding:

```text
Observed after row-process isolation:
  Remote P0 passed at commit 65c807b7: 52 passed.
  Stage-2A r5 used the same 64 contexts and tiers 32/64/128/256.
  The probe status confirmed candidate_count=1, so the earlier context-batched
  hard-timeout-scope bug was fixed for this run.

Remaining failure:
  The run streamed 248/256 result rows and observed 8 true row-level hard
  timeouts at process_elapsed_sec ~= 60.8-61.3s.
  Timeout contexts:
    g567-tunnel-24x24-a-v0, 64 agents, additive
    g567-cross-32x32-a-v3, 256 agents, additive/static/g556
    g567-connector-48x48-a-v3, 256 agents, additive/static/g556/A5 actor

Infrastructure anomaly:
  The tmux session ended without an rc file and without a final Stage-2A summary.
  No active Python or phase1a_batch process remained when checked.

Decision:
  Stop. This is not a Stage-2A pass.
  Do not launch Gate-3A, Gate-3B, or any full campaign until the true row-level
  hard timeouts and no-rc/no-summary runner termination are repaired and rerun.
```

Post-r5 GPT Pro diagnosis and direct-exact repair:

```text
Important reinterpretation:
  The r5 60.8-61.3s timeout pattern is not valid evidence that direct additive,
  direct static-flow, direct g556, or direct A5 rows cannot terminate in a 30s
  solver budget. The row-isolated replay still used the old static-flow outer
  solver with a counterfactual candidate callback. Therefore a reported
  "additive timeout" was a static-flow primary execution plus an additive
  counterfactual probe, not a direct additive primary run.

Repair implemented locally:
  run_replay_phase now uses direct_exact_solver_row for exact G5.67 replay.
  Each planned row launches exactly one solver subprocess with:
    --method = materialized_method for that row
    solver_internal_time_limit_sec = 30.0
    process_hard_timeout_sec = 60.0
    registry passed only for generated-theta materialization
    counterfactual probe callback disabled

  The old counterfactual-probe path remains diagnostic-only:
    requested budget is capped to <=5000 ms
    C++ clips effective probe budget to parent deadline remaining time minus guard
    skipped probes record probe_skipped_parent_deadline=true
    probe rows never count as exact Label-v5.4 solver rows

  C++ solve_with_ltm now checks the parent deadline immediately after
  one_shot.solve. If expired, it preserves incumbent/basic stats, skips
  UpdateLTM/callback, and returns normally. phase1a_batch perf mode also skips
  full traffic cost_audit after post-solve deadline expiry and records phase
  timing fields.

  A Stage-2A tmux runner wrapper now writes rc and an atomic final summary on
  normal exit, fail-closed exit, exception, and SIGTERM; it records stale-marker
  evidence if a previous run died without final summary. SIGKILL cannot execute
  a trap, so recovery is represented by the stale marker.

Local verification:
  python -m py_compile passed for the modified Python scripts.
  pytest over tests/test_repair5g567*.py: 53 passed, 1 skipped.
  Windows C++ build_phase1a_batch.ps1 succeeded.
  Local direct additive smoke on empty-8-8 wrote updateparams_fingerprint,
  counterfactual_probe_ms=0, and phase timings.

Remote status:
  Not yet rerun after this repair in this document state.
  Gate-3A, Gate-3B, full 100k/1M/48h, and final blind remain locked.

Next allowed remote step:
  Build on the RTX5090 server, run targeted reproducer on:
    tunnel-24x24 a64
    cross-32x32 a256
    connector-48x48 a256
  Compare:
    A. historical old 30s outer + 30s probe path
    B. direct exact 30s, no probe
    C. parent-clipped 3s diagnostic probe
  Then rerun Stage-2A only. It must complete 256/256 rows, zero hard-timeout
  rows, rc and final summary present, true A5 checkpoint produced, before
  Gate-3A can run.

Tail handling:
  Do not delete tunnel/cross/connector. Reclassify extreme map-agent-density
  combinations as an extreme-tail audit panel, exclude them from diagnostic
  training until direct exact is stable, then reintroduce through curriculum.
```

Critical manual-approval barrier:

```text
This plan does not authorize Gate-3B or the full G5.67 campaign, even if all
technical gates later pass.

Required stopping points:

STOP 1:
  After timeout/nested-deadline repair and the targeted tunnel/cross/connector
  reproducer, stop and report all evidence.

STOP 2:
  After Stage-2A reaches 256/256 completed rows, zero hard timeouts, valid rc,
  valid final summary, and a true diagnostic A5 checkpoint, stop and report.
  Do not automatically launch Gate-3A unless it was explicitly included in the
  current approved bounded task.

STOP 3:
  After true A5 Gate-3A passes, stop all tmux sessions and solver/GPU processes,
  sync artifacts to GitHub, and report the exact commit and evidence. Do not
  launch Gate-3B automatically.

STOP 4:
  Gate-3B may run only after a new explicit user/GPT-Pro approval. After Gate-3B
  completes, stop again and report exact HEAD, context and solver-row counts,
  timeout/crash rates, public-map and official-scenario proportions,
  Label-v5.4 distribution, critic calibration, A/B/C development results,
  GPU-active hours, and full-campaign storage estimate.

Absolute full-campaign lock:
  Under no circumstances may Codex launch server_start_repair5g567_full.sh,
  100k+ context generation, 1M+ solver acquisition, 48h+ training, final blind
  feature materialization, or final blind solver replay unless a new user
  message is received after GPT Pro reviews Gate-3B evidence.

  Passing Stage-2A, Gate-3A, or Gate-3B does not grant full-campaign permission.
  Approval cannot be inferred from an earlier plan, previous prompt, automated
  gates passing, available GPU time, available disk, or an existing tmux session.

  The exact full approval must contain:
    APPROVE_G567_FULL_<EXACT_COMMIT_SHA>

  Without that exact fresh approval token, the required decision is:
    g567_full_campaign_waiting_for_manual_gptpro_review

  Codex must not set, guess, or generate G567_FULL_MANUAL_APPROVAL. That
  environment variable can only be provided explicitly by the user after
  Gate-3B evidence is reviewed.

  server_start_repair5g567_full.sh now enforces this in code by comparing:
    G567_FULL_MANUAL_APPROVAL == APPROVE_G567_FULL_$(git rev-parse HEAD)

Fixed execution order:
  timeout repair -> targeted reproducer -> stop/report -> Stage-2A ->
  stop/report -> true Gate-3A only after explicit bounded approval ->
  stop/report -> user/GPT-Pro review -> Gate-3B only after new approval ->
  stop/report -> final full review -> user-provided APPROVE_G567_FULL_<SHA> ->
  full campaign may start.
```
