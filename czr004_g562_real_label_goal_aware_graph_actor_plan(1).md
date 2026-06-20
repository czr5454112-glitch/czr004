# Repair5G.5.62 Plan — Real-Label Goal-Aware Dual-Channel Graph-Attention Actor, Tail-Risk Repair, and Solver-Evaluated Amortized UpdateParams Optimization

Project: `czr004`
Repository: `czr5454112-glitch/czr004`
Required branch: `server-code`
Source-of-truth start commit at plan creation: `7f9f57e454277162222b596e6dffe9f159ddbd78`
Primary fixed baseline: `g556_c063174`
Paper-faithful floor: `LaCAM* + additive LTM`
Round: `Repair5G.5.62 real-label goal-aware graph actor and tail-risk optimization`
Revision: `v2 — literature/source audit, non-DAgger clarification, censored-label repair, and safe-subspace exploration`

---

## 0. Executive decision

G5.62 keeps the current research direction.

The primary method remains:

```text
one MAPF instance
  = physical map graph
  + actual paired starts/goals
  + paired OD demand
  + directed C0 congestion prior
  + directed F0 goal-progress prior
  + solver budget
  + LTM iteration budget
        ↓
attention-based goal-aware graph/traffic neural network
        ↓
one bounded continuous dual-channel UpdateParams theta
        ↓
theta remains fixed for the complete solver run
        ↓
the ordinary trace-driven C/F traffic maps continue to update online
```

The project is **not** changing to:

```text
agent action imitation
checkpoint-dependent theta
runtime theta switching
restart-node prediction
candidate-ID selection
codebook retrieval
map-ID lookup
scalar-only production actor
```

### 0.1 Mainline lock and explicit non-DAgger clarification

G5.62 is **not** DAgger and must not be implemented as DAgger under another name.

The project does not learn an agent action policy. It does not query an expert for actions on states visited by a learner, mix expert and learner actions, imitate PIBT/LaCAM decisions, or aggregate state-action trajectories.

The only learned production mapping remains:

```text
rich pre-run MAPF instance representation -> one continuous run-static theta
```

The only expensive data-generation object is:

```text
(instance identity, continuous theta, unchanged solver conditions)
    -> real solver outcome
```

Sequential data collection in this plan means **targeted solver-outcome experimental design for a contextual black-box response surface**. It may acquire additional `(instance, theta, outcome)` labels near positive frontiers, unsafe boundaries, or uncertain regions. It may not acquire agent action labels or change the solver's decision semantics.

This distinction must be written into the project-level research contract. Any future implementation that introduces an action decoder, expert action query, learner-state action aggregation, learned priority ordering, or learned restart control is outside G5.62.

G5.61 is an important engineering advance, but it is not yet the clean scientific experiment required by the project goal.

G5.61 established:

```text
canonical solver-facing theta bounds
exact generated-theta materialization
component-aware valid scenario generation
a real graph-attention + paired-OD forward path
real solver replay for graph actors
multi-seed CUDA execution
hard-negative replay and fine-tuning infrastructure
```

G5.61 did not establish:

```text
that a rich graph actor trained from real solver-derived Label-v5.1 safe sets
can outperform additive LTM or g556_c063174
```

The central G5.62 diagnosis is:

```text
The representation path is now present,
but the main graph actor was initially trained on analytic synthetic theta targets,
not on the recovered real solver safe/improving theta sets.

The expanded 2,600-scenario bank was not the main supervised actor dataset.
The primary multi-seed run used 128 generated samples per seed and 500 steps.
The F7 "critic" path was not yet a calibrated graph-conditioned solver-outcome critic.
The later hard-negative fine-tune mostly pulled bad outputs toward g556,
which repaired regressions but did not teach context-specific positive improvement.
```

Therefore G5.62 must connect all three components at once:

```text
rich attention representation
+ real solver safe/improving supervision
+ exact-materialized targeted solver-outcome design
```

The round must not stop after one model, one training seed, one 100-context replay, one hard-negative pass, or one summary file.

Minimum substantive G5.62 completion requires:

```text
1. permanently record the representation floor in the project-level outlines;
2. build a real Label-v5.1 graph/OD/C0/F0 tensor dataset;
3. train multiple non-scalar attention actors on real solver labels;
4. train a real conservative graph-conditioned outcome critic for training only;
5. execute at least two train → exact replay → acquire labels → retrain cycles;
6. compare every serious actor against both additive LTM and g556_c063174;
7. produce a final causal and solver-level failure attribution if no actor passes.
```

---

## 1. Project-level representation floor: permanent research contract

### 1.1 This is a minimum information floor, not an architecture ceiling

Before implementing G5.62 experiments, Codex must update all of the following:

```text
deep-research-report.md
phase4_6_laur_ltm_codex_execution_plan.md
docs/goal_aware_dual_channel_ltm_research_contract.md   # create if absent
```

Insert a clearly delimited block in both project-level outlines:

```text
<!-- GOAL_AWARE_DUAL_CHANNEL_LTM_REPRESENTATION_FLOOR_BEGIN -->
...
<!-- GOAL_AWARE_DUAL_CHANNEL_LTM_REPRESENTATION_FLOOR_END -->
```

The block must state the following semantics.

### 1.2 Minimum production-main-model input contract

The minimum production main model must consume, in its actual forward pass:

```text
physical graph topology
+ actual paired starts/goals
+ paired OD tokens
+ directed C0 congestion prior
+ directed F0 goal-progress prior
+ solver budget
+ LTM iteration budget
```

The minimum output remains:

```text
one continuous bounded theta per MAPF instance
```

The theta remains fixed throughout that solver run.

### 1.3 More complex models are explicitly allowed

The representation floor does **not** freeze the architecture at the current F6 implementation.

Allowed and encouraged extensions include:

```text
more expressive GATv2-style local attention
GraphGPS-style local/global graph Transformer layers
sparse global attention
hierarchical full-grid + corridor/junction graphs
OD-to-node or OD-to-edge cross-attention
agent-grid bipartite attention
separate C-channel and F-channel graph streams
multi-resolution raster/graph fusion
structural or positional encodings
hypernetwork or field-group theta heads
mixture-of-experts encoders
probabilistic training heads with deterministic one-theta deployment
uncertainty distillation into a continuous trust/shrinkage head
self-supervised graph/traffic pretraining
```

The model may be simpler than these examples if evidence supports it, but it may not go below the minimum information floor for the primary method.

### 1.4 Scalar information is supplemental, not sufficient

Scalar features such as:

```text
agent_count
density
map size
budget
path_found_rate
flow mass
map-family indicators
```

may be used as:

```text
an auxiliary branch
a normalization signal
a budget/context token
a control model
an ablation
```

They may not replace graph topology, paired OD, C0, and F0 in the primary production actor.

A scalar-only MLP is a valid control named explicitly as such. It is not the main `goal_aware_dual_channel_ltm` model.

### 1.5 Forbidden architectural regressions

The primary method is invalid if any of the following is true:

```text
main actor consumes only scalar/tabular summaries
graph tensors are built but not used by forward
graph branch receives zero gradients throughout training
OD tokens are unpaired start/goal histograms only
paired OD is loaded but masked out in the selected production model
C0/F0 are stored only in manifests or summaries
C0/F0 are replaced by hash proxies
C0 and F0 are declared but map to the same duplicated tensor without audit
map ID, candidate ID, theta ID, or solver RNG seed is used as a predictive shortcut
rich model is trained only on analytic synthetic theta targets
scalar control is renamed to imply it is the graph-attention main model
```

### 1.6 Representation evidence required for every future round

Every future round claiming a goal-aware graph actor must record:

```text
actual node tensor count and dimensions
actual directed edge tensor count and dimensions
actual paired OD token count
actual C0 tensor nonzero rate
actual F0 tensor nonzero rate
C0/F0 provenance
forward-hook evidence for each branch
nonzero gradient norm for graph encoder
nonzero gradient norm for OD encoder
nonzero gradient norm for C/F traffic modules
batch-composition invariance
node-order permutation invariance
agent-order permutation invariance
solver-seed invariance
paired-goal shuffle intervention
C0 intervention
F0 intervention
graph-topology intervention
scalar-only ablation
```

### 1.7 Contract tests

Add tests that fail if the primary actor drops below the floor:

```text
test_project_outline_contains_representation_floor_markers
test_primary_actor_forward_requires_graph_batch
test_primary_actor_forward_requires_paired_od
test_primary_actor_consumes_c0
test_primary_actor_consumes_f0
test_primary_actor_uses_budget_and_ltm_iteration
test_primary_actor_graph_gradient_nonzero
test_primary_actor_od_gradient_nonzero
test_primary_actor_traffic_gradient_nonzero
test_primary_actor_is_not_scalar_only
test_scalar_model_is_control_only
test_richer_than_f6_architecture_is_allowed
test_actor_export_contains_no_codebook_or_critic
```

The project-level contract update must be committed before model promotion claims are evaluated.

---

## 1A. Literature-grounded refinements without changing the project direction

Before implementation, Codex must inspect the papers and official code below and record exact paper/repository versions in a compact literature audit. The purpose is to improve the current parameter-prediction route, not to import a different MAPF policy formulation.

### 1A.1 AAAI 2024 — Traffic Flow Optimisation for Lifelong Multi-Agent Path Finding

Paper:

```text
https://arxiv.org/abs/2308.11234
```

Direct lessons for czr004:

```text
vertex convergence congestion and edge contraflow are different phenomena;
the paper reports that a structured/two-part treatment is more effective than a crude additive sum;
traffic-aware guidance must remain a soft heuristic and preserve solver feasibility;
wait/block pressure matters, not only move-edge flow.
```

Required G5.62 consequence:

```text
C0 must include explicit vertex/queue/wait-pressure features as well as edge contraflow;
F0 must remain a separate directed goal-progress representation;
C/F fusion should be gated or interaction-aware rather than merely concatenated and linearly averaged;
wait-related theta fields must be predicted from explicit wait/convergence evidence.
```

### 1A.2 IJCAI 2024 — Guidance Graph Optimization

Paper and official implementation:

```text
https://arxiv.org/abs/2402.01446
https://github.com/lunjohnzhang/ggo_public
```

Direct lessons:

```text
the simulator is the final objective;
CMA-ES is a serious black-box control;
a lower-dimensional parameterized update model can transfer better than direct high-dimensional guidance optimization;
wait actions can be represented in guidance;
reloadable logs, exact configs, and resumable experiments are first-class evidence.
```

Required G5.62 consequence:

```text
retain exact solver replay as final truth;
add a small bounded CMA-ES/CEM teacher/control on a selected subset only when positive-frontier support is sparse;
consider a low-dimensional continuous safe-residual subspace actor;
never deploy the optimizer—the final method remains one attention-network forward pass.
```

### 1A.3 ICRA 2023 — Graph Transformers with bounded-suboptimal MAPF search

Paper:

```text
https://arxiv.org/abs/2301.08451
```

Direct lessons:

```text
a graph Transformer can guide MAPF while the classical solver retains its guarantees;
size/agent-count generalization must be tested explicitly;
learned guidance should alter heuristic preference, not feasibility semantics.
```

Required G5.62 consequence:

```text
keep LaCAM*/PIBT semantics unchanged;
add graph-size, density, and agent-count curriculum/evaluation;
report extrapolation from smaller/easier train contexts to larger/denser heldout contexts.
```

### 1A.4 AAAI 2026 — LaGAT

Paper and official implementation:

```text
https://arxiv.org/abs/2510.17382
https://github.com/proroklab/lagat
```

Direct lessons:

```text
pretrain then fine-tune is more credible than a tiny one-stage fit;
edge attributes and graph attention are operational, not decorative;
imperfect learned guidance requires an explicit safeguard;
target-map adaptation and unseen-map generalization are different claims.
```

Required G5.62 consequence:

```text
use representation pretraining followed by real solver-label fine-tuning;
use a continuous learned trust/shrinkage head as the safeguard;
separate strict inductive heldout-map evaluation from any target-map adaptation diagnostic;
do not copy LaGAT's action-policy target.
```

### 1A.5 QD-generated MAPF maps as a diagnostic, not a direction switch

Reference:

```text
https://arxiv.org/abs/2409.06888
```

Use morphology descriptors or targeted generated maps only to expose failure regions and improve heldout coverage. Do not spend the main round rebuilding a QD/NCA map generator unless the current 56-map bank is proven to miss a specific morphology needed for the actor-vs-g556 question.

### 1A.6 Explicit exclusions from the literature review

Do not adopt:

```text
agent-action imitation or reinforcement learning;
DAgger or learner-state expert action aggregation;
learned priority ordering;
learned restart selection;
strict edge-direction deletion or any mechanism that removes legal moves;
a runtime-varying theta policy;
a deployed CMA-ES/CEM optimizer;
a selector over stored theta IDs.
```

The literature review may improve representation, training, safeguards, experimental design, and controls only.

Required artifacts:

```text
outputs/reports/phase5p5_repair5g562_literature_method_audit.md
outputs/tables/phase5p5_repair5g562_literature_design_decisions.csv
outputs/tables/phase5p5_repair5g562_official_repo_commit_manifest.csv
```

---

## 2. Source-of-truth interpretation of G5.61

G5.62 must begin with a code-and-artifact audit at the exact start commit.

### 2.1 Positive G5.61 conclusions

Record and preserve:

```text
G5.60 replay contamination was correctly identified.
The G5.61 canonical theta schema repaired solver-facing bounds.
The materialization contract passed 85/85 vectors.
Candidate recognition, exact fingerprint, dual-channel enablement,
force_additive=false, scenario hash, and identity retention all reached 1.0.
The valid scenario bank reached 2,600 valid instances.
The bank reports 56 physical map hashes, 12 map families,
8 start-goal regimes, 6 density bins, and 8 budget profiles.
A real GoalAwareDualChannelActor now accepts graph_batch, OD tokens,
OD mask, and scalar context.
Exact-materialized architecture replay and development replay were executed.
```

Do not undo these repairs.

### 2.2 Current solver evidence

Record separately:

```text
Architecture replay:
  F6 mean quality delta vs g556 ≈ +0.01898 on 100 pairs
  F7 mean quality delta vs g556 ≈ +0.01928 on 100 pairs
  zero success regressions in that small panel

Larger development replay:
  F6 mean delta ≈ +0.02450, 3 success regressions / 400
  F7 mean delta ≈ +0.03758, 4 success regressions / 400

Hard-negative fine-tune panel:
  F6FT mean delta ≈ +0.01508, 0 regressions, better/worse 194/188
  F7FT mean delta ≈ +0.01006, 0 regressions, better/worse 203/188
```

Interpretation:

```text
The first graph actors are not promotable.
However, F6FT/F7FT are not featureless failures:
they eliminated success regressions and produced slightly more better than worse pairs.
The remaining blocker is dominated by quality-loss magnitude and upper-tail harm,
not merely by the count of losing contexts.
```

### 2.3 Main training-truth problem

Audit and explicitly record that the initial graph actor training path:

```text
calls build_samples(...)
constructs a small generated sample bank
computes target theta with context_target_theta(...)
optimizes normalized L1 to that analytic target
```

This is an implementation/representation smoke, not real Label-v5.1 actor learning.

Analytic targets may remain for unit tests only.

They must not be used as the primary G5.62 actor target, early-stopping target, architecture ranking target, or promotion evidence.

### 2.4 Scenario-bank disconnection

Audit whether the 2,600 valid scenario bank is actually consumed by:

```text
self-supervised pretraining
real-label actor training
critic training
targeted solver-outcome design
heldout replay
```

Do not count scenario-bank generation as model data use unless the model loader records the exact scenario IDs consumed.

### 2.5 Current critic truth

Audit the current F7 implementation.

The previous F7 flag must not be described as a real calibrated critic if it only adds an anchor/trust penalty or writes placeholder calibration metrics.

A G5.62 real critic requires:

```text
instance-rich representation + theta input
real success-regression targets
real success-gain targets
real finite quality targets
optimizer steps
heldout physical-map metrics
calibration
checkpoint
actor-gradient usage during training only
```

### 2.6 Current hard-negative fine-tune limitation

The G5.61 hard-negative target blends harmful actor output back toward g556.

That mechanism is useful for safety repair, but it cannot by itself teach the actor where the positive context-specific frontier lies.

G5.62 must learn from both:

```text
hard negatives
and
verified positive safe-improving theta/outcomes
```

### 2.7 Required G5.61 truth-audit artifacts

Write:

```text
outputs/reports/phase5p5_repair5g562_g561_training_truth_audit.md
outputs/reports/phase5p5_repair5g562_g561_training_truth_audit_summary.json
outputs/tables/phase5p5_repair5g562_g561_target_provenance_audit.csv
outputs/tables/phase5p5_repair5g562_g561_scenario_bank_usage_audit.csv
outputs/tables/phase5p5_repair5g562_g561_critic_truth_audit.csv
outputs/tables/phase5p5_repair5g562_g561_replay_evidence_matrix.csv
```

---

## 3. Scientific formulation: contextual black-box optimization

Treat the problem explicitly as a contextual, solver-evaluated continuous optimization problem.

For one instance `x`:

```text
x = graph + paired OD + C0 + F0 + budget
```

The actor predicts:

```text
theta_hat = f_phi(x)
```

The solver produces:

```text
y = SolverOutcome(x, theta_hat)
```

where `y` contains at minimum:

```text
success/failure
success gain/regression vs baseline
sum-of-loss ratio
quality delta vs g556
quality delta vs additive LTM
runtime
expanded nodes
low-level PIBT calls
trace/update diagnostics
```

The actor is an amortized optimizer:

```text
expensive per-instance theta search
    -> distilled into one forward pass
```

The solver is non-differentiable, so G5.62 may use:

```text
real safe-set supervision
real advantage-weighted regression
training-only graph-conditioned critic
conservative lower-confidence utility
targeted solver-outcome experimental design
```

Final deployment remains:

```text
one actor forward
one continuous theta
no codebook
no critic
no candidate enumeration
```

---

## 4. Real Label-v5.1 graph/traffic dataset

### 4.1 Build a real instance tensor store

Implement a dataset keyed by `g560_evaluation_uid` / its G5.62 successor.

Recommended module:

```text
src/gcst/real_label_graph_dataset.py
```

For every retained valid Label-v5.1 instance, materialize or cache:

```text
physical map hash
scenario hash
actual ordered start-goal pairs
full graph node tensor
full directed edge index
structural edge tensor
C0 edge tensor
F0 edge tensor
OD token tensor
budget token
LTM iteration token
all observed theta rows
all real solver outcomes
safe/improving/Pareto sets
replicate metadata
```

### 4.2 Required node features

At minimum include:

```text
normalized x/y
degree
corridor / junction / dead-end indicators
local obstacle density
border distance
structural/positional encoding
start count or start mass at node
goal count or goal mass at node
start-goal imbalance
local OD demand summary
local bottleneck/cut proxy
connected-component ID where relevant
```

The node start/goal fields must be built from the actual paired scenario, not generated again from a seed.

### 4.3 Required directed edge features

Separate structural, C-channel, and F-channel features.

Structural edge features:

```text
direction dx/dy
edge length
corridor alignment
clearance
local degree context
edge betweenness/cut proxy
relative positional encoding
```

C0 congestion prior must have an explicit provenance and dedicated channels, for example:

```text
predicted edge-use pressure
opposing demand
head-on pressure
local conflict exposure
bottleneck occupancy pressure
bidirectional contention
```

F0 goal-progress prior must be represented separately, for example:

```text
directed progress flow toward paired goals
reverse/nonprogress demand
goal attraction directionality
remaining-distance reduction signal
flow alignment with destination demand
```

Do not satisfy this contract by renaming a single tensor twice.

Write an audit that measures:

```text
C0/F0 correlation
exact equality rate
nonzero rates
mass conservation
sign/direction consistency
intervention response
```

High correlation may be legitimate; exact duplication without justification is not.

### 4.3A Explicit vertex convergence and wait-pressure evidence

The actor predicts several wait/nonprogress update coefficients. Those fields cannot be considered informed if the input contains only path-flow edge counts.

For each node and its adjacent directed edges, build pre-run features such as:

```text
inbound OD demand mass
outbound OD demand mass
vertex convergence count/pressure
normalized n(n-1)/2 conflict-pressure proxy
predicted queue or wait pressure
terminal-goal occupancy pressure
narrow-corridor queue exposure
blocked/nonprogress exposure proxy
start-at-goal and goal-cluster indicators
```

Propagate node pressure to directed edges with explicit provenance rather than hiding it inside one scalar summary.

Required audit:

```text
wait-pressure nonzero rate
wait-pressure mass by scenario
correlation with actual blocked/wait trace counts on labeled rows
ablation effect on wait-related theta fields
ablation effect on solver quality tails
```

The exact analytic proxy may be improved, but it must be derived from the real map and paired starts/goals and must remain separate from F0 goal-progress flow.

### 4.4 Paired OD tokens

Each agent/OD token should include at least:

```text
start coordinates
goal coordinates
relative displacement
shortest-path distance
normalized path length
start/goal local topology descriptors
budget/agent-scale context where useful
```

The pair identity must remain intact.

The following intervention must be possible:

```text
same start set + same goal set + shuffled pairing
```

### 4.5 Scalar branch

Scalar features remain useful but supplemental:

```text
agent count
density
budget
LTM iterations
free-cell count
path-found rate
flow totals
map dimensions
```

The production actor may fuse them as a budget/context token.

### 4.6 Dataset splits

Split by physical map hash first.

Required splits:

```text
train physical hashes
validation physical hashes
heldout physical hashes
family-heldout diagnostic
new scenario-bank replay panel
blind hashes reserved for later
```

No physical map hash may occur in more than one primary split.

The same scenario hash and paired start-goal assignment may not cross splits.

### 4.7 Real-label targets

For each instance, construct from real solver outcomes:

```text
safe set
safe-improving set
Pareto set
high-confidence positive set
unsafe/regression set
quality-worse set
both-fail/noncomparable set
```

Do not treat every non-regression candidate as equally useful.

Recommended positive target requirements:

```text
no success regression
candidate recognized
exact fingerprint
bounds valid
scenario/identity exact
and one of:
  success gain
  finite quality delta < -margin
  bootstrap-supported improvement
```

Recommended hard-negative definitions:

```text
success regression
large positive quality delta
unstable replicate behavior
actor/critic false-safe prediction
full-budget reversal of short-budget gain
large tail loss within a generally good stratum
```

### 4.7A Candidate-slate censoring and three-state supervision

The observed theta slate is finite. Therefore:

```text
no observed safe improvement != proof that no safe improvement exists
unobserved theta != unsafe theta
missing replicate confirmation != negative label
```

Classify supervision into three states:

```text
verified positive:
  exact, safe, and materially improving real solver evidence

verified harmful:
  success regression or materially worse/tail-harmful real solver evidence

unknown/censored:
  unobserved regions, noncomparable outcomes, insufficient support, or a slate with no discovered positive
```

Rules:

```text
unknown rows are masked from positive-vs-negative classification losses;
unknown contexts may receive a weak g556 trust prior, not a hard no-op target;
strong anchoring to g556 requires actor-line/local-response evidence that alpha=0 is optimal or that nearby residuals are harmful;
acquisition priority should increase for high-opportunity but heavily censored contexts;
report positive-discovery coverage separately from true fallback/no-op evidence.
```

A positive-unlabeled or censoring-aware implementation is allowed, but it must be auditable and must not silently relabel unknowns as negatives.

Required outputs:

```text
outputs/tables/phase5p5_repair5g562_label_censoring_audit.csv
outputs/reports/phase5p5_repair5g562_positive_discovery_coverage.json
```

### 4.8 Real label weighting

Each instance contributes equal total mass.

Within an instance, weight observed theta by:

```text
safety confidence
quality advantage
replicate confidence
full-budget confirmation
local support density
map-family balancing
```

Rows from the same instance are not independent graph samples.

### 4.9 Dataset truth gates

Require:

```text
identity join = 1.0
scenario hash join = 1.0
physical map hash join = 1.0
graph tensor join = 1.0
OD tensor join = 1.0
C0 tensor join = 1.0
F0 tensor join = 1.0
theta join = 1.0
valid scenario rate for retained training groups = 1.0
train/validation/heldout physical hash overlap = 0
analytic synthetic target rate in primary dataset = 0
```

### 4.10 Storage

Large tensors and rows should be stored outside ordinary Git when necessary.

Use:

```text
partitioned Parquet / Arrow for row metadata
NPZ/PT shards for graph and OD tensors
artifact registry
SHA256 checksums
row counts and byte sizes
producer command
source commit
```

Do not silently omit large files. Record durable remote paths and transfer manifests.

---

## 5. Recompute real opportunity before training

### 5.1 Valid-only oracle audit

Recompute oracle opportunity using only:

```text
valid scenarios
exact identities
exact materialization
real solver outcomes
comparable budgets
```

Report separately against:

```text
g556_c063174
paper-faithful additive LTM
```

Metrics:

```text
fraction with any safe improvement
fraction with replicated safe improvement
mean oracle gain
median oracle gain
90th percentile opportunity
per-family opportunity
per-density opportunity
per-budget opportunity
short-to-full-budget transfer
```

### 5.2 Actor-line shrinkage oracle

For current F6FT/F7FT outputs, evaluate a continuous interpolation family:

```text
theta(alpha) = g556 + alpha * (theta_actor - g556)
```

Use an acquisition grid such as:

```text
alpha ∈ {0.0, 0.125, 0.25, 0.5, 0.75, 1.0}
```

This is an offline/solver data-acquisition device, not deployment selection.

For each context report:

```text
best safe alpha
quality curve vs alpha
monotonicity/non-monotonicity
failure boundary
whether alpha=0 is optimal
whether alpha in (0,1) beats both endpoints
```

This directly supervises the actor's continuous trust/shrinkage head.

### 5.3 Field-group response audit

Group theta fields into at least:

```text
C update amplitudes
F update amplitudes
C/F decay
C/F mixing lambdas
flow shield
edge-cost clamp
goal projection mode
```

On a balanced subset, perturb one group at a time around:

```text
g556
F6FT
F7FT
known safe-improving observed theta
```

Measure which groups cause:

```text
large positive tails
success regressions
stable improvements
map-family-specific effects
```

### 5.4 Opportunity decision branches

If valid-only oracle opportunity is strong:

```text
continue representation/training repair
```

If codebook/observed safe opportunity is strong but actor-line opportunity is weak:

```text
actor target/mode learning is the blocker
```

If actor-line interpolation contains safe gains:

```text
prioritize supervised trust/shrinkage learning
```

If no safe gain exists even in observed candidate space:

```text
candidate/update-parameter space is the blocker
```

Do not blame graph learning for absent solver opportunity.

---

## 6. Architecture search: F6 is the floor, not the endpoint

G5.62 must keep a scalar control but explore several rich production candidates.

### 6.1 C0 — scalar MLP control

```text
scalar summaries -> one theta
```

Purpose:

```text
measure whether graph/OD/C0/F0 adds value
```

This model cannot be the primary production method.

### 6.2 A0 — current F6-Lite reproduction

Reproduce the current G5.61 F6 implementation exactly enough to establish a comparable baseline.

```text
GraphGPSLite pooled graph
+ pooled OD Set Transformer
+ scalar branch
+ concat fusion
+ one theta
```

Purpose:

```text
separate new-data/training gains from architecture gains
```

### 6.3 A1 — Dual-Stream Edge-Aware GraphGPS/GATv2 actor

Recommended first serious architecture:

```text
shared topology encoder
C-channel edge-attention stream
F-channel edge-attention stream
cross-channel gated fusion
paired-OD encoder
budget token
field-group theta heads
```

Suggested scale tiers:

```text
small:  hidden 96–128, 3–4 local layers, 1–2 global layers
medium: hidden 192, 4–6 local layers, 2–3 global layers
large diagnostic: hidden 256, 6 local layers, sparse/global attention
```

Use dynamic/query-dependent attention such as GATv2 or an equivalent edge-aware implementation.

### 6.4 A2 — OD-to-Graph cross-attention actor

The current F6 pools graph and OD independently before fusion, which weakens spatial alignment.

A2 must permit direct interaction:

```text
OD tokens query graph node/edge tokens
or
graph bottleneck tokens query OD demand tokens
```

Possible implementation:

```text
paired OD Set Transformer
  -> OD queries
full graph/corridor tokens
  -> keys/values
cross-attention
  -> demand-conditioned graph embedding
```

Alternative:

```text
scatter start/goal and OD-path demand into nodes/edges
then run graph attention
```

### 6.5 A3 — Hierarchical full-grid + corridor/junction actor

Use two graph scales:

```text
full physical grid graph
corridor/junction coarse graph
```

Required invariants:

```text
all traversable cells represented
connectivity preserved
coarse-to-fine assignment complete
start/goal/flow mass conserved
```

Fuse local fine-grid congestion with global corridor demand.

### 6.6 A4 — Field-group hypernetwork actor

Use a rich instance encoder and separate parameter heads:

```text
C amplitude head
F amplitude head
decay head
mixing head
shield head
clamp head
goal-mode head
continuous trust/shrinkage head
```

This remains one direct continuous actor.

It may improve inductive bias because the 15 fields have different semantics and safety scales.

### 6.6A A4S — Safe-residual subspace actor

G5.61/G5.62 operate in a 15-dimensional theta space with limited independent real instances. A full unconstrained head may spend samples learning unsafe or inactive directions.

Build a continuous low-rank residual basis only from training-map, verified safe/improving residuals around g556:

```text
R = {normalize(theta_safe - theta_g556)}
B = robust PCA/SVD or a learned orthogonal basis over R
z(x) = rich attention encoder output in d dimensions
alpha_group(x) = continuous semantic-group trust

theta(x) = project[g556 + group_scale(alpha_group) * B z(x)]
```

Compare at least:

```text
d = 3
d = 5
d = 8
full 15D head
```

Requirements:

```text
basis is fitted only on training physical hashes;
no nearest-neighbor lookup or candidate retrieval occurs at inference;
B is a continuous parameterization, not a codebook;
semantic field groups and solver bounds are preserved;
residual support distance and tail harm are reported.
```

This variant is strongly encouraged if the full head retains positive CVaR or if field-group sensitivity shows a low-dimensional safe region.

### 6.7 A5 — Pessimistic distributional actor with deterministic deployment

Optional advanced variant:

```text
encoder predicts per-field location + scale or a small learned mode family
training models multimodal safe regions
inference emits one deterministic mode/mean
```

No codebook or historical candidate enumeration is allowed.

A fixed deterministic latent or highest learned mixture mode is acceptable if the exported actor still performs one forward pass and returns one theta.

### 6.8 A6 — Distilled ensemble actor

Train multiple rich actors/critics for epistemic analysis, then distill:

```text
ensemble consensus and pessimistic trust
    -> one standalone production actor
```

The deployed artifact must not load the ensemble.

### 6.9 Architecture minimums

Train at least:

```text
C0 scalar control
A0 F6-Lite reproduction
A1 dual-stream graph actor
A2 OD-to-graph cross-attention actor
A4 field-group/trust actor
```

A3/A5/A6 are encouraged if resources allow or if earlier variants expose the corresponding bottleneck.

At least two rich non-scalar variants must receive full real-label training and exact-materialized replay.

The top two rich variants must receive at least three training seeds before a final G5.62 conclusion.

### 6.10 Performance engineering

The current edge attention uses Python-side node loops and per-graph global-attention loops.

Audit and improve GPU utilization with:

```text
vectorized segmented softmax/scatter
packed graph batches
masked padded sparse/global tokens where appropriate
bf16 mixed precision
gradient accumulation
checkpoint/resume
torch.compile only if stable
profiling of data-loader vs compute time
```

Report:

```text
GPU utilization distribution
VRAM peak
nodes/sec
edges/sec
OD tokens/sec
optimizer steps/sec
loader wait fraction
```

Model complexity is allowed to increase, but unused complexity is not evidence.

---

## 7. Self-supervised and supervised training sequence

### 7.1 Phase P — representation pretraining

Use the 2,600 valid scenario bank and any additional valid unlabeled contexts.

Tasks may include:

```text
masked node-feature reconstruction
masked C0 reconstruction
masked F0 reconstruction
C0/F0 summary prediction
shortest-path distance histogram
bottleneck-demand quantiles
actual-pair vs shuffled-pair contrastive classification
graph augmentation consistency
map morphology prediction without map-ID leakage
```

Pretraining must not use analytic theta as its main task.

Recommended execution floor:

```text
at least 10,000 optimizer steps for serious rich variants
checkpoint every 1,000–2,000 steps
validation by heldout physical maps
```

### 7.1A Inductive and target-adaptation tracks must be separated

The primary generalization claim is inductive.

For the primary track:

```text
heldout and blind physical-map hashes may not appear in representation pretraining,
real-label training, critic training, normalization fitting, basis fitting, or hyperparameter selection.
```

An optional LaGAT-style target-map adaptation diagnostic is permitted only on a separately designated adaptation split and must be labeled:

```text
transductive/target-adapted diagnostic
not unseen-map generalization
not blind evidence
```

Report both tracks separately. Do not use unlabeled heldout topology during pretraining and then describe the result as fully unseen-map generalization.

### 7.2 Phase S1 — real safe-set actor supervision

For each instance with real positive set `S+`:

```text
L_positive_set = softmin over real safe-improving modes
```

Weights should increase with:

```text
success gain
negative quality delta
replicate confidence
full-budget confirmation
margin from unsafe boundary
```

For instances with no verified positive:

```text
learn conservative continuous shrinkage toward g556
```

But distinguish:

```text
no observed positive
from
proved no opportunity
```

Do not over-anchor merely because the 64-candidate slate missed the optimum.

### 7.2A Confidence and difficulty curriculum

Use a staged real-label curriculum rather than mixing all labels from step 1:

```text
Stage 1:
  replicated/high-margin safe positives
  clear success regressions and large harmful deltas

Stage 2:
  broader safe sets and moderate-margin rankings
  map/agent-count/density balancing

Stage 3:
  ambiguous boundaries, short/full-budget reversals, and tail-risk hard cases
```

Also stratify by graph size and agent count so the model first learns stable topology/OD relations and then handles dense/high-conflict contexts. Final validation must still use the full heldout distribution.

The curriculum changes training order and weights only. It does not change the deployed mapping or solver.

### 7.3 Advantage-weighted safe behavior regression

Treat observed theta rows as continuous actions in a contextual bandit.

Define safe advantage relative to g556/additive:

```text
A(x, theta) = risk-adjusted utility(theta) - baseline utility
```

Use clipped advantage weights such as:

```text
w = safety_confidence * exp(clipped_advantage / temperature)
```

Combine with mode-seeking set loss so distant modes are not averaged into a harmful midpoint.

### 7.4 Unsafe repulsion

For real unsafe/harmful theta:

```text
push actor output away from local unsafe neighborhoods
```

Use field-normalized distances and noise-aware margins.

Do not repel all worse-but-safe points equally; focus on meaningful harmful margins and regressions.

### 7.5 Tail-risk objective

The G5.61 fine-tuned actors often produced more better than worse pairs but retained positive mean loss.

Train explicitly for tail risk:

```text
mean quality delta
+ upper quantile quality delta
+ CVaR of positive quality loss
+ success-regression penalty
+ worst-family penalty
```

Recommended outputs/losses:

```text
quality median
quality q75/q90
regression probability
uncertainty
```

The production actor still outputs only theta; auxiliary heads may be removed or distilled at export.

### 7.6 Supervised continuous trust/shrinkage

Use actor-line alpha replay to supervise:

```text
alpha_hat(x) ∈ [0,1]
```

Then:

```text
theta_final = g556 + alpha_hat(x) * residual_actor(x)
```

Field-group alpha is allowed:

```text
alpha_C
alpha_F
alpha_decay
alpha_shield
alpha_clamp
```

This is continuous parameter generation, not fallback selection.

### 7.7 Consistency and causal losses

Use weak but meaningful regularization:

```text
same instance augmentation -> stable theta
agent-order permutation -> identical theta
node-order permutation -> identical theta
solver seed change -> identical theta
paired-goal shuffle -> output may change
C0/F0 perturbation -> relevant fields may change
```

Do not force invariance to changes that alter the actual traffic demand.

### 7.7A Geometric symmetry and scale generalization

Because theta contains global update coefficients rather than map-direction-specific actions, valid map isometries should preserve the predicted theta when all directional inputs are transformed consistently.

Add training/evaluation transformations where valid:

```text
90/180/270-degree rotations
horizontal/vertical reflection
consistent transformation of graph edges, starts/goals, OD displacement, C0, and F0
```

Require:

```text
transformed instance -> same theta within a declared numerical/learned tolerance
```

Do not apply an augmentation that changes map semantics or start-goal pairing.

Also evaluate extrapolation across:

```text
agent count
density
graph size
budget
```

with explicit in-range and out-of-range panels.

### 7.8 Training scale

G5.61's 128 samples and 500 steps are smoke-scale.

For G5.62 serious variants, target:

```text
representation pretraining: 10k–30k steps
real safe-set actor training: minimum 15k, target 30k–60k steps
critic training: minimum 20k, target 40k–100k steps
joint conservative refinement: 5k–20k steps
```

Early stopping may occur only after the relevant minimum floor and after validation has been evaluated on heldout physical maps.

Record all losses separately.

---

## 8. Real graph-conditioned outcome critic, training only

### 8.1 Critic input

The critic must consume:

```text
same rich instance representation as the actor
+ candidate continuous theta
```

It must not be a scalar-only critic for the primary rich actor.

### 8.2 Critic targets

Train on real solver outcomes:

```text
success regression
success gain
finite quality delta vs g556
finite quality delta vs additive LTM
quality quantiles
runtime/search-effort delta
materialization validity as a separate engineering head if useful
```

### 8.3 Grouped batches

Each batch should contain:

```text
multiple independent instances
× multiple theta rows per instance
```

Required losses:

```text
class-balanced or focal regression-risk loss
gain loss
quality Huber/Gaussian-NLL
quantile pinball losses
within-instance pairwise ranking
within-instance listwise safe-utility loss
calibration loss
hard-negative margin loss
```

### 8.4 Cross-fitting

Use physical-map cross-fitting:

```text
critic fold k trains without map fold k
actor supervision on fold k uses an out-of-fold critic
```

This reduces actor exploitation of critic memorization.

### 8.5 Conservative objective

Use an ensemble or equivalent uncertainty mechanism.

Actor training should optimize a pessimistic quantity such as:

```text
quality_upper_confidence_bound
+ regression_risk_upper_confidence_bound
- conservative_gain_lower_bound
+ support-distance penalty
```

The actor must not be rewarded for unsupported theta that merely fools one critic.

### 8.6 Critic metrics

Report on heldout physical maps:

```text
regression PR-AUC
regression recall at fixed precision
Brier score
ECE
quality MAE/RMSE
quality Spearman
NDCG / ranking accuracy
q90 coverage
safe top-k recall
false-safe rate vs coverage
critic disagreement
```

Placeholder values are forbidden.

### 8.7 Deployment boundary

The critic may be used for:

```text
training gradients
targeted solver-outcome design
uncertainty analysis
failure attribution
```

The final exported actor must not require the critic.

---

## 9. Sequential solver-outcome experimental design: learn from positives and negatives (not DAgger)

G5.62 must execute at least two acquisition/training cycles.

### 9.0 Unit of acquisition and forbidden interpretation

Every acquired datum is:

```text
(instance_uid, evaluation_uid, continuous theta, solver budget, exact materialization, solver outcome)
```

It is not:

```text
(agent observation, expert action)
(learner-visited state, oracle action)
a trajectory-level behavior-cloning sample
```

Do not call this DAgger in code, reports, or commits. Prefer:

```text
targeted solver-outcome design
sequential black-box experimental design
response-surface acquisition
positive-frontier acquisition
```

The solver remains unchanged and supplies only outcome labels.

### 9.1 Cycle 0 — existing real labels

Train from all valid recovered Label-v5.1 data.

Do not first regenerate the entire historical dataset.

### 9.2 Cycle 1 — actor-line and tail-risk panel

Select a balanced set of at least 400 valid contexts across:

```text
physical map hash
map family
density
budget
start-goal regime
current actor tail-risk score
```

For at least two rich actors, replay:

```text
g556
additive LTM
actor alpha grid
```

Suggested alpha grid:

```text
0.0, 0.125, 0.25, 0.5, 0.75, 1.0
```

This cycle should create direct labels for continuous shrinkage and tail boundaries.

### 9.3 Cycle 2 — positive-frontier and local response acquisition

For contexts with observed or newly discovered gain, evaluate a compact local set around:

```text
best safe observed theta
best actor-line theta
current actor output
```

Use field-group perturbations and trust-region sampling.

Include:

```text
positive local neighbors
unsafe boundary neighbors
C-only changes
F-only changes
mixing/decay changes
shield/clamp changes
```

The purpose is not to deploy a selector. It is to generate supervision for a continuous actor.

### 9.3A Optional GGO-inspired bounded optimizer teacher/control

If either of the following is true:

```text
verified positive coverage is sparse after Cycle 1;
actor-line interpolation rarely finds a negative quality delta;
observed-codebook oracle remains much stronger than the actor;
```

run a bounded trust-region CMA-ES or CEM diagnostic on a selected set of 32–64 training/development contexts.

Recommended search:

```text
center around g556, the best verified safe theta, and/or current rich actor output;
operate in the semantic field groups or A4S low-dimensional residual basis;
32–96 exact solver evaluations per context;
use no heldout/blind contexts for optimizer tuning;
retain all successes, failures, and replicate lineage.
```

The optimizer is:

```text
a teacher/control and positive-frontier data generator only
```

It is not:

```text
the deployed method
a selector
a runtime optimizer
permission to replace the attention actor
```

Report optimizer oracle gain, evaluation cost, transferability, and how well the actor distills its positive regions.

### 9.4 Cycle 3 — scenario-bank expansion labels

Use the expanded valid scenario bank to label previously unlabeled contexts.

Prioritize:

```text
underrepresented physical hashes
underrepresented families
OD patterns unlike old Label-v5.1
high graph-vs-scalar disagreement
high actor ensemble disagreement
high critic uncertainty
predicted safe high utility
known failure morphologies
```

### 9.5 Minimum acquisition scale

Unless a hard materialization/data-integrity blocker occurs, G5.62 must collect at least:

```text
12,000 new exact-materialized candidate solver rows
across at least 800 unique valid contexts
and at least two acquisition cycles
```

Preferred if development signal improves:

```text
25,000–50,000 new candidate rows
```

The round must not declare completion after a 100-context smoke panel.

### 9.6 Replicates and fidelity

For promotion-relevant candidates:

```text
use fresh paired solver seeds
confirm at target budget
retain short/medium/full budget lineage
```

Short-budget gains alone are development labels.

---

## 10. Replay ladder

### 10.1 R0 — schema/materialization recheck

After any theta-schema or replay change, run at least 64 diverse vectors and require:

```text
candidate_recognized = 1
exact fingerprint = 1
force_additive = false
dual channel enabled = true
scenario hash = 1
identity retention = 1
```

### 10.2 R1 — controlled architecture panel

Use the same exact contexts and solver conditions for:

```text
additive LTM
g556
C0 scalar control
A0 F6-Lite
A1 dual-stream graph actor
A2 cross-attention actor
A4 field-group/trust actor
```

Minimum:

```text
200 balanced contexts
fresh evaluation seeds
exact materialization
```

Purpose:

```text
rank architectures under identical evidence
```

### 10.3 R2 — heldout physical-map development replay

Select top two rich variants from real-label offline + R1 evidence.

Minimum:

```text
600 heldout/new valid contexts
at least two fresh solver seed blocks
additive LTM + g556 + top rich actors
```

Report all map/family/budget strata.

### 10.4 R3 — post-acquisition retrain replay

After at least two acquisition cycles, freeze the retrained actors and replay:

```text
minimum 1,000 valid contexts
new physical-map hashes where possible
three training seeds for top architecture
fresh evaluation seeds
```

### 10.5 Stage1 trigger

Only plan the existing large Stage1 floor if at least one rich actor shows:

```text
zero or research-gate-acceptable success regressions
negative mean quality delta vs g556
CI direction promising or upper bound near/below zero
better > worse
clear improvement over scalar control
negative delta vs additive LTM
exact materialization
no catastrophic family
```

Do not spend 200k+ rows merely because training finished.

---

## 11. Evaluation metrics

### 11.1 Primary solver metrics

Against both g556 and additive LTM:

```text
success regressions
success gains
success rate
mean/median quality delta
paired bootstrap CI
better/worse/ties
sum-of-loss ratio
TTFS where available
quality-time AUC
expanded nodes
low-level PIBT calls
runtime overhead
```

### 11.2 Tail metrics

Required because G5.61 showed a harmful upper tail:

```text
q75/q90/q95 positive quality loss
CVaR@90 of quality loss
worst 10% mean
largest loss
fraction delta > 0.01 / 0.05 / 0.10
per-family q90
per-budget q90
```

### 11.3 Actor metrics

```text
nearest real safe-improving set distance
safe-set hit under local solver replay
continuous alpha calibration
per-field output variance
fraction exactly g556
fraction near g556
unique theta count
support distance
map/OD/C0/F0 conditional variation
```

### 11.4 Representation-value metrics

Compare:

```text
scalar control
F6-Lite
dual-stream graph
cross-attention graph
hierarchical graph if implemented
```

The rich model must be evaluated on identical heldout maps and replay contexts.

### 11.5 Statistical units

Report:

```text
row level
instance level
physical-map level
map-family level
seed-block level
```

Do not treat multiple theta rows from one instance as independent map examples.

---

## 12. Causal representation audits

The current threshold `difference > 1e-6` is too weak for a substantive causal claim.

### 12.1 Noise floor

Measure repeated-inference numerical noise and batch-composition variance.

Intervention effects must exceed a predeclared multiple of this noise floor.

### 12.2 Paired OD audit

Compare:

```text
same exact instance
same starts and goals but shuffled pairing
```

Report:

```text
theta change
field-group changes
attention change
predicted critic change
solver replay change on a subset
```

### 12.3 C0 and F0 audits

Run separately:

```text
zero C0 only
zero F0 only
shuffle C0 across edges
reverse F0 directions
scale C0/F0
```

Do not only zero all traffic channels together.

### 12.4 Topology audit

Use topology-preserving and topology-changing perturbations:

```text
node-order permutation -> invariant
edge-order permutation -> invariant
single obstacle/corridor perturbation -> may change theta
same scalar summaries, different topology -> should be distinguishable
```

### 12.5 Scalar-shortcut audit

Construct matched context pairs with similar scalar summaries but different:

```text
topology
paired OD
C0/F0
```

The rich actor should produce meaningfully different embeddings/theta where solver opportunity differs.

### 12.6 Gradient/branch utilization

Record per step/epoch:

```text
graph encoder gradient norm
OD encoder gradient norm
C stream gradient norm
F stream gradient norm
fusion gradient norm
theta head gradient norm
trust head gradient norm
```

A branch that remains effectively unused must be diagnosed.

---

## 13. Loss and optimizer ablations

At minimum compare:

```text
analytic-target L1 smoke only                 # control, not primary
real safe-set softmin
advantage-weighted real theta regression
safe-set + unsafe repulsion
safe-set + tail/CVaR loss
safe-set + supervised alpha/trust
safe-set + conservative cross-fit critic
full combined objective
```

Also compare:

```text
single global anchor penalty
context-conditioned trust
field-group trust
support-distance penalty
critic ensemble pessimism
no critic
```

Do not perform an unstructured hyperparameter sweep without interpreting the failure mode.

Use staged searches with clear hypotheses.

---

## 14. Interpretation of likely outcomes

### 14.1 Safe but mean quality remains positive

Likely causes:

```text
harmful quality tail
excess residual magnitude
wrong field-group residuals
positive labels too sparse
budget mismatch
```

Actions:

```text
alpha line labels
field-group trust
CVaR loss
positive local acquisition
full-budget confirmation
```

### 14.2 Rich actor does not beat scalar control

Investigate:

```text
scenario bank not used
C0/F0 duplication or noise
independent pooling loses spatial alignment
model too small
attention branch unused
physical-map diversity insufficient
```

Actions:

```text
OD-to-graph cross-attention
node-level start/goal mass
separate C/F streams
larger hidden size/layers
self-supervised pairing tasks
matched-scalar topology tests
```

### 14.3 Offline metrics improve but replay does not

Investigate:

```text
real labels at wrong budget
safe-set interpolation gap
critic extrapolation
short-budget/full-budget reversal
candidate slate support mismatch
```

### 14.4 Success regressions return

Actions:

```text
risk ensemble
upper-confidence risk penalty
smaller learned trust
replicated hard negatives
map-family worst-group weighting
```

### 14.5 Critic-guided actor exploits the critic

Actions:

```text
cross-fitting
conservative objective model penalty
support distance
ensemble disagreement
actor-line solver checks
```

### 14.6 Valid real oracle gap is weak

Do not abandon the parameter-prediction route immediately.

First test a richer but still continuous UpdateParams parameterization:

```text
additional saturation coefficients
separate progress/nonprogress decay
field-group nonlinear scaling
continuous channel-mixing parameters
```

Any theta-v2 expansion must remain:

```text
predicted once per instance
bounded
run-static
solver-semantics preserving
```

It may not become an action policy.

---

## 15. Required code structure

Recommended additions/refactors:

```text
src/gcst/
  real_label_graph_dataset.py
  representation_contract.py
  dual_stream_graph_actor.py
  od_graph_cross_attention.py
  hierarchical_graph_actor.py
  field_group_theta_head.py
  safe_residual_subspace.py
  graph_outcome_critic.py
  conservative_actor_losses.py
  tail_risk_losses.py
  advantage_weighted_safe_set.py
  censoring_aware_labels.py
  solver_outcome_design.py
  replay_truth.py
```

Scripts:

```text
scripts/audit_repair5g562_g561_truth.py
scripts/write_repair5g562_project_contract.py
scripts/build_repair5g562_real_graph_dataset.py
scripts/analyze_repair5g562_valid_oracle.py
scripts/pretrain_repair5g562_representation.py
scripts/train_repair5g562_graph_critic.py
scripts/train_repair5g562_real_label_actors.py
scripts/run_repair5g562_alpha_response_panel.py
scripts/run_repair5g562_positive_frontier_acquisition.py
scripts/run_repair5g562_optimizer_teacher.py
scripts/run_repair5g562_architecture_panel.py
scripts/run_repair5g562_cycle2_replay.py
scripts/run_repair5g562_cycle3_replay.py
scripts/export_repair5g562_actor.py
scripts/write_repair5g562_decision.py
scripts/monitor_repair5g562_server.py
```

Existing modules may be extended instead of duplicated when that produces a cleaner design.

Do not create dozens of five-line wrappers that call the same evaluator.

---

## 16. Required artifacts

### 16.1 Governance and truth

```text
outputs/reports/phase5p5_repair5g562_project_contract_update.md
outputs/reports/phase5p5_repair5g562_literature_method_audit.md
outputs/tables/phase5p5_repair5g562_literature_design_decisions.csv
outputs/tables/phase5p5_repair5g562_official_repo_commit_manifest.csv
outputs/reports/phase5p5_repair5g562_g561_training_truth_audit.md
outputs/reports/phase5p5_repair5g562_g561_training_truth_audit_summary.json
outputs/tables/phase5p5_repair5g562_g561_target_provenance_audit.csv
```

### 16.2 Dataset

```text
outputs/reports/phase5p5_repair5g562_real_graph_dataset_summary.json
outputs/tables/phase5p5_repair5g562_real_graph_dataset_manifest.csv
outputs/tables/phase5p5_repair5g562_split_manifest.csv
outputs/tables/phase5p5_repair5g562_c0_f0_provenance_audit.csv
outputs/tables/phase5p5_repair5g562_safe_set_statistics.csv
outputs/tables/phase5p5_repair5g562_label_censoring_audit.csv
outputs/reports/phase5p5_repair5g562_positive_discovery_coverage.json
outputs/tables/phase5p5_repair5g562_pretraining_split_audit.csv
outputs/tables/phase5p5_repair5g562_valid_oracle_opportunity.csv
```

### 16.3 Training

```text
outputs/reports/phase5p5_repair5g562_pretraining_summary.json
outputs/reports/phase5p5_repair5g562_actor_training_summary.json
outputs/reports/phase5p5_repair5g562_critic_training_summary.json
outputs/reports/phase5p5_repair5g562_training_progress.jsonl
outputs/tables/phase5p5_repair5g562_architecture_matrix.csv
outputs/tables/phase5p5_repair5g562_loss_ablation_matrix.csv
outputs/tables/phase5p5_repair5g562_critic_calibration.csv
outputs/tables/phase5p5_repair5g562_branch_gradient_audit.csv
```

### 16.4 Acquisition and replay

```text
outputs/reports/phase5p5_repair5g562_alpha_response_summary.json
outputs/tables/phase5p5_repair5g562_alpha_response_pairs.csv
outputs/reports/phase5p5_repair5g562_optimizer_teacher_summary.json
outputs/tables/phase5p5_repair5g562_optimizer_teacher_pairs.csv
outputs/reports/phase5p5_repair5g562_cycle1_summary.json
outputs/reports/phase5p5_repair5g562_cycle2_summary.json
outputs/reports/phase5p5_repair5g562_cycle3_summary.json
outputs/tables/phase5p5_repair5g562_replay_by_method.csv
outputs/tables/phase5p5_repair5g562_replay_by_map_family.csv
outputs/tables/phase5p5_repair5g562_tail_risk_metrics.csv
outputs/tables/phase5p5_repair5g562_failure_cases.csv
```

### 16.5 Final

```text
outputs/reports/phase5p5_repair5g562_failure_attribution.md
outputs/reports/phase5p5_repair5g562_decision.md
outputs/reports/phase5p5_repair5g562_decision_summary.json
outputs/reports/phase5p5_repair5g562_artifact_manifest.json
outputs/tables/phase5p5_repair5g562_checksums.sha256
```

---

## 17. Required tests

```text
test_project_outline_representation_floor_present
test_research_contract_explicitly_forbids_dagger_and_action_labels
test_representation_floor_is_minimum_not_ceiling
test_scalar_only_actor_cannot_be_primary
test_real_dataset_uses_actual_scenario_pairs
test_real_dataset_uses_no_analytic_theta_targets
test_physical_hash_split_disjoint
test_graph_tensor_join_complete
test_od_tensor_join_complete
test_c0_tensor_join_complete
test_f0_tensor_join_complete
test_c0_and_f0_not_silently_duplicated
test_wait_pressure_is_real_instance_derived
test_wait_pressure_affects_wait_parameter_branch
test_graph_encoder_gradient_nonzero
test_od_encoder_gradient_nonzero
test_c_stream_gradient_nonzero
test_f_stream_gradient_nonzero
test_agent_order_invariance
test_node_order_invariance
test_solver_seed_invariance
test_pairing_shuffle_exceeds_noise_floor
test_c0_intervention_exceeds_noise_floor
test_f0_intervention_exceeds_noise_floor
test_scalar_matched_topology_pair_changes_embedding
test_safe_set_loss_uses_real_solver_rows
test_unknown_censored_rows_are_not_negative_labels
test_no_observed_positive_is_not_hard_g556_target
test_advantage_weights_prefer_real_safe_improvement
test_unsafe_repulsion_uses_real_harmful_rows
test_quality_loss_masks_noncomparable_rows
test_crossfit_critic_has_no_map_overlap
test_primary_pretraining_excludes_heldout_and_blind_hashes
test_rotation_reflection_transform_preserves_theta_contract
test_safe_subspace_actor_uses_no_candidate_retrieval
test_actor_export_excludes_critic
test_actor_export_excludes_codebook
test_actor_inference_one_forward_one_theta
test_theta_fixed_for_run
test_materialization_contract_full_schema
test_replay_pairs_retain_identity
test_additive_and_g556_baselines_present
test_tail_metrics_are_computed_from_pairs
test_checkpoint_resume
test_large_artifacts_registered_and_checksummed
```

---

## 18. Server execution protocol

Use the current RTX5090 server route and existing monitoring pattern.

Requirements:

```text
all serious training runs under tmux
all long solver replay under tmux
no credentials committed to Git
password/key passed through environment or secure operator input
source commit recorded
remote workdir recorded
GPU model/VRAM recorded
progress JSONL written during training
checkpoint/resume supported
monitor/pull script preserves newer local artifacts
```

At each major cycle, push code and compact evidence artifacts.

Do not call the scientific round complete merely because the remote process launched or a checkpoint exists.

---

## 19. Layered gates

### 19.1 Representation-floor gate

Requires:

```text
project outlines updated
rich actor consumes all minimum F6 information
no scalar-only primary model
all branch gradients nonzero
causal interventions exceed noise floor
```

### 19.2 Real-label gate

Requires:

```text
primary actor analytic-target rate = 0
real safe-set dataset built
real physical-map-heldout validation
positive and negative supervision both used
```

### 19.3 Engineering replay gate

Requires:

```text
materialization exact = 1
identity complete = 1
scenario valid = 1
additive and g556 controls present
```

### 19.4 Development signal gate

At least one rich actor should satisfy on heldout/new contexts:

```text
better than scalar control
negative delta vs additive LTM
no catastrophic family
success-regression rate at a usable research point
quality delta vs g556 materially improved over G5.61
positive-tail/CVaR reduced
```

A small remaining mean loss vs g556 may justify one additional acquisition cycle if the trend, tail, and additive comparison are strongly favorable.

### 19.5 Promotion-candidate gate

Strict:

```text
success regressions vs g556 = 0
success non-worse
mean quality delta vs g556 < 0
CI upper <= 0
better > worse
negative delta vs additive LTM
materialization/identity exact
no severe worst-family regression
three training seeds
fresh solver replay
```

### 19.6 Claim policy

Keep closed until strict evidence:

```text
phase5p5_allowed = false
phase6_allowed = false
runtime_claim_allowed = false
learned_runtime_policy_validated = false
aaai_ready = false
```

---

## 20. Minimum completion requirement

Codex may not declare G5.62 complete after any of the following alone:

```text
editing the project outline
writing a plan
building a dataset manifest
training a scalar MLP
running analytic-target smoke
training one rich model for a few hundred steps
producing offline L1 metrics
passing materialization only
running one 100-context replay
performing hard-negative shrinkage only
writing skip/failure summaries
```

Minimum substantive completion is:

```text
1. project-level minimum representation floor and non-DAgger mainline contract committed;
2. literature/source audit completed with explicit adopted and rejected lessons;
3. real Label-v5.1 graph/OD/C0/F0 dataset implemented and audited,
   including wait pressure, censoring state, and inductive split provenance;
4. valid-only real oracle and actor-line opportunity computed;
5. at least four serious rich/control architectures trained,
   including at least two rich attention actors and a full-head vs safe-subspace comparison;
6. top two rich actors trained with at least three seeds;
7. real graph-conditioned critic trained and calibrated for training-only use;
8. verified positive, verified harmful, and censored/unknown supervision are handled separately;
9. at least two targeted solver-outcome design/retraining cycles executed;
10. at least 12,000 new exact-materialized candidate rows collected
    across at least 800 valid contexts unless a hard truth blocker is proven;
11. exact-materialized replay against both additive LTM and g556;
12. tail-risk, scale-generalization, causal representation, and split-leakage analysis completed;
13. final decision and failure attribution written from real solver evidence.
```

If a hard blocker prevents a required stage, Codex must:

```text
prove the blocker with code/artifacts
complete all unaffected branches
write a resumable command
preserve partial data
not relabel the blocker as scientific model failure
```

---

## 21. Decision labels

Use precise labels such as:

```text
g562_project_representation_floor_recorded
g562_non_dagger_mainline_contract_recorded
g562_literature_method_audit_completed
g562_g561_synthetic_target_training_confirmed
g562_real_graph_dataset_ready
g562_censoring_aware_labels_ready
g562_real_label_join_failed
g562_valid_oracle_gap_present
g562_valid_oracle_gap_absent
g562_representation_pretraining_completed
g562_real_graph_critic_calibrated
g562_real_safe_set_actor_training_completed
g562_alpha_response_acquisition_completed
g562_positive_frontier_acquisition_completed
g562_optimizer_teacher_diagnostic_completed
g562_cycle1_replay_completed
g562_cycle2_replay_completed
g562_cycle3_replay_completed
g562_rich_actor_beats_additive_not_g556_continue
g562_rich_actor_no_supported_gain_continue_representation_or_label_repair
g562_direct_graph_actor_promotion_candidate_keep_claims_closed
g562_materialization_or_identity_blocker_not_model_failure
```

---

## 22. Main question

G5.62 must answer:

```text
When the production actor consumes at least physical topology, actual paired
starts/goals, paired OD tokens, separate directed C0/F0 priors, solver budget,
and LTM iteration budget—and is trained on real solver-derived safe/improving
theta sets rather than analytic targets—can one attention-based neural forward
pass generate a continuous run-static dual-channel UpdateParams theta that
outperforms paper-faithful additive LTM and the stronger g556_c063174 baseline?
```

Do not answer this question from:

```text
analytic theta fitting
nonzero gradients alone
causal sensitivity alone
requested epochs
checkpoint existence
selector performance
critic performance
loss decrease
```

Answer it only from exact-materialized, identity-safe, heldout/new-map real solver replay.
