# Repair5G.5.59 Plan — Real-Solver Label-v5, Hierarchical Dual-Traffic Graph Transformer, and Instance-Conditioned Static UpdateLTM

Project: `czr004`
Repository: `czr5454112-glitch/czr004`
Required branch: `server-code`
Start commit: `6b0c5e807239b68f1c9c86018db3424c25739525`
Primary fixed baseline: `g556_c063174`
Round name: `Repair5G.5.59 real-solver graph-conditioned static-theta learning`

---

## 0. Executive decision

G5.59 continues the current scientific direction:

```text
MAPF instance
  = physical map
  + actual paired starts/goals
  + all-agent spatial distribution
  + goal-aware flow / traffic priors
  + solver budget
        ↓
real neural graph/traffic encoder
        ↓
one bounded dual-channel UpdateParams theta
        ↓
theta stays fixed for the entire solver run
        ↓
the ordinary trace-driven C/F traffic map continues to evolve
```

This is still:

```text
instance-conditioned
run-static
trace-updated
```

It is not:

```text
one universal theta for every instance
checkpoint-conditioned theta
runtime dynamic policy
action policy
priority policy
restart policy
```

G5.58 is an important engineering success but not yet a scientific test of the final GCST hypothesis.

G5.58 proved:

```text
real PyTorch graph-attention code exists
CUDA training executes
gradients and checkpoints are real
the old G5.57 "TTGT" was not a neural model
```

G5.58 did not prove:

```text
a neural model can learn real solver-derived context→theta behavior
```

because the RTX5090 server did not contain the G5.57 raw pair rows. The Label-v4 training set therefore used 192 contexts, 64 candidates per context, and synthetic analytic labels rather than paired solver outcomes.

G5.59 must repair the scientific evidence chain rather than merely increase epochs.

---

## 1. Source-of-truth interpretation of G5.58

Before new experiments, write a code-and-artifact audit from commit:

```text
6b0c5e807239b68f1c9c86018db3424c25739525
```

Required source files:

```text
src/gcst/graph_data.py
src/gcst/graph_encoder.py
src/gcst/scenario_features.py
src/gcst/traffic_prior.py
src/gcst/od_encoder.py
src/gcst/theta_critic.py
src/gcst/theta_generator.py
src/gcst/losses.py
src/gcst/metrics.py
src/gcst/inference.py
src/gcst/label_v4.py
scripts/repair5g558_pipeline.py
outputs/reports/phase5p5_repair5g558_*summary.json
outputs/tables/phase5p5_repair5g558_*.csv
```

### 1.1 Positive conclusions

Record:

```text
real_neural_implementation = true
trainable_parameters = 5,957,541
optimizer_steps = 300
cuda_used = true
graph_attention_executed = true
checkpoint_contains_state_dict = true
checkpoint_contains_optimizer_state = true
nonzero_gradient = true
input_sensitivity = true
loss decreased strongly
```

Do not discard this implementation work.

### 1.2 Scientific blocker

Record:

```text
raw_solver_pair_rows_available = false
training_label_source = synthetic analytic learnability labels
training_contexts = 192
candidate_rows = 12,288
actual_solver_stage1_rows = 0
actual_solver_stage2_rows = 0
actual_solver_blind_rows = 0
```

The negative result is therefore:

```text
the smoke implementation did not satisfy its synthetic tiny-overfit ranking gate
```

not:

```text
graph-conditioned static theta failed on real MAPF solver labels
```

### 1.3 The 0.8207 ranking result is not explained only by insufficient training

Audit and fix all of the following.

#### A. No explicit ranking loss

The critic training objective uses:

```text
success-regression BCE
success-gain BCE
SmoothL1 quality regression
materialization BCE
```

but does not directly optimize pairwise or listwise ranking.

A ranking threshold of 0.95 cannot be treated as a fair training gate unless the objective contains a ranking term.

#### B. Generator target remains a single synthetic theta

The generator uses best-of-K L1 distance to one analytic `context_target_theta`.

This is not the intended Label-v4 safe-set / multimodal target.

#### C. Several passing metrics are proxy identities

Audit:

```text
fallback classification accuracy
success-gain accuracy proxy
generator safe-set hit-rate proxy
coverage-risk table
```

No metric may compare labels to themselves or convert "loss decreased" into a fixed hit rate.

#### D. Evaluation uses a narrow ordered slice

The critic evaluation currently uses the first 512 pair rows. Replace this with:

```text
stratified complete-context evaluation
all candidate rows for each selected context
multiple maps and physical hashes
fixed train/validation/test context lists
```

### 1.4 Graph representation bugs

#### A. Connectivity-destroying node subsampling

The smoke job uses:

```text
max_nodes = 96
```

and `build_graph` keeps every N-th traversable cell. It then retains only grid edges whose two endpoints both survived.

This destroys corridor and room connectivity.

G5.58 materialized:

```text
5,760 nodes
1,008 directed edges
60 declared topologies
```

which is only about:

```text
96 nodes / topology
16.8 directed edges / topology
```

This is not a faithful grid graph.

#### B. Cross-instance global-attention leakage

The current graph encoder does:

```python
pooled = scatter_mean(...)
tokens = pooled.unsqueeze(0)
TransformerEncoderLayer(batch_first=True)
```

This treats the graphs in a minibatch as tokens in one sequence. Therefore the embedding for one instance depends on the other instances in the same minibatch.

Required invariant:

```text
prediction(instance A alone)
==
prediction(instance A in any batch composition/order)
```

#### C. Incomplete agent representation

The smoke job uses:

```text
max_agents = 64
```

even when contexts declare hundreds or thousands of agents.

The model therefore ignores most agent assignments.

#### D. Incorrect density denominator

Density must be:

```text
agent_count / physical_free_cell_count
```

not:

```text
agent_count / sampled_node_count
```

#### E. Traffic prior degeneracy

The shortest-path flow is computed on the sparsified/disconnected graph. Many committed traffic rows have:

```text
edge_use_total = 0
opposing_flow_total = 0
bottleneck_demand = 0
```

A path computation call is not sufficient evidence that the traffic signal is meaningful.

Write:

```text
outputs/reports/phase5p5_repair5g559_g558_failure_autopsy.md
outputs/reports/phase5p5_repair5g559_g558_failure_autopsy_summary.json
outputs/tables/phase5p5_repair5g559_loss_metric_mismatch_audit.csv
outputs/tables/phase5p5_repair5g559_graph_connectivity_audit.csv
outputs/tables/phase5p5_repair5g559_batch_invariance_audit.csv
outputs/tables/phase5p5_repair5g559_traffic_nonzero_audit.csv
outputs/tables/phase5p5_repair5g559_agent_mass_audit.csv
```

---

## 2. Scientific hypothesis

Primary hypothesis:

```text
The best bounded dual-channel UpdateLTM coefficients depend systematically on
physical topology, paired start-goal demand, agent density, directional flow,
and bottleneck pressure.
```

Operational hypothesis:

```text
A graph/traffic neural model can predict one static theta per MAPF instance
that outperforms the universal g556_c063174 baseline on supported contexts,
while safely falling back on unsupported contexts.
```

The key scientific story is:

```text
LTM uses a hand-written additive update rule.
czr004 retains LaCAM*/PIBT semantics but learns how strongly different event
types should update the congestion and goal-progress flow channels.
The prediction is made once from the instance and is fixed during the run.
The traffic map itself remains dynamic and trace-driven.
```

---

## 3. Literature and code anchors

G5.59 must inspect the official repositories and paper implementations, not only abstracts.

### 3.1 Guidance Graph Optimization — IJCAI 2024

Official code:

```text
https://github.com/lunjohnzhang/ggo_public
```

Lessons to adopt:

```text
solver-facing simulation remains final truth
CMA-ES is a serious non-neural optimizer/control
different maps and agent scales use explicit configurations
guidance transfer must be evaluated, not assumed
experiments need reloadable logs and exact manifests
```

Do not vendor or modify GGO code.

### 3.2 LaGAT — AAAI 2026

Official code:

```text
https://github.com/proroklab/lagat
```

Lessons to adopt:

```text
real edge-aware graph attention
pretrain then fine-tune
hybrid learned/search design
explicit safeguards for imperfect neural guidance
large, heterogeneous evaluation commands
```

Do not learn MAPF actions. Adopt only representation/training rigor.

### 3.3 MAPF-GPT — AAAI 2025

Official code:

```text
https://github.com/CognitiveAISystems/MAPF-GPT
```

Lessons:

```text
large training pipelines use explicit train/validation datasets
large row counts are stored as streaming datasets
DDP and reproducible configs are first-class
validation maps are separated from training maps
```

Do not imitate its action target. The relevance is data engineering and training scale.

### 3.4 CS-PIBT / ML-MAPF-with-Search — ICRA 2025 line

Official code:

```text
https://github.com/Rishi-V/ML-MAPF-with-Search
```

Lessons:

```text
large supervised datasets alone do not guarantee success
a strong shield/baseline is mandatory
the learned model should focus on information the search baseline lacks
```

For czr004:

```text
shield/fallback = g556_c063174
```

### 3.5 GraphGPS / Exphormer

Lessons:

```text
combine local real-edge aggregation with global attention
keep graph-local and graph-global operations inside each graph
use sparse/global mechanisms for large maps
use structural/positional encodings
```

### 3.6 QD-MAPPER

Lessons:

```text
fixed human-designed maps may hide failure modes
generated maps must be physically distinct layouts
performance should be stratified by map morphology
```

Write:

```text
outputs/reports/phase5p5_repair5g559_literature_code_audit.md
outputs/tables/phase5p5_repair5g559_literature_method_matrix.csv
outputs/tables/phase5p5_repair5g559_official_repo_commit_manifest.csv
```

---

## 4. New method: DualTraffic-HGT-GCST

Recommended method name:

```text
DualTraffic-HGT-GCST
```

Expanded:

```text
Hierarchical Goal-Aware Dual-Traffic Graph Transformer
for Graph-Conditioned Static Theta
```

Input:

```text
physical map topology
actual paired starts/goals
all-agent distribution
C0 congestion/conflict prior
F0 directed goal-progress prior
budget and LTM iteration setting
```

Output:

```text
one bounded dual-channel UpdateParams theta
```

The chosen theta is frozen for the complete solver run.

---

## 5. Representation repair

### 5.1 Preserve full physical topology

Do not stride-sample grid cells.

Use one of two correct representations.

#### Preferred: corridor-junction supergraph

Compress:

```text
degree-2 corridor chains -> superedges
junctions / doors / room entrances -> supernodes
open-room regions -> spatial patch nodes
dead ends -> explicit terminal nodes
```

Store on every superedge:

```text
corridor length
minimum width
mean obstacle proximity
directed OD flow
opposing flow
flow imbalance
head-on pressure
C0
F0
```

Required:

```text
all original traversable cells assigned to a supernode/superedge
connectivity preserved
shortest-path distortion reported
component count unchanged
```

#### Secondary control: raster/patch encoder

Channels:

```text
obstacle mask
start density
goal density
C0
F0
opposing flow
path-overlap concentration
distance-to-obstacle
bottleneck score
```

Use a small U-Net/CNN or patch transformer.

The primary model may fuse the corridor graph and raster tokens.

### 5.2 Correct global attention

Global attention must be per graph.

Allowed:

```text
padded token sequence per graph + attention mask
PyG-style to_dense_batch
per-graph landmark tokens
per-graph virtual global node
```

Forbidden:

```text
attention across independent graphs in the same minibatch
```

Mandatory tests:

```text
batch composition invariance
batch order invariance
single-instance vs batched inference equivalence
```

### 5.3 Represent all agents

The network must preserve all-agent mass even when the OD token encoder samples agents.

Use all of:

```text
full start-density field
full goal-density field
full C0/F0 flow fields
requested agent count
physical density
OD distance histogram
direction histogram
source/sink imbalance
```

Optional OD tokens:

```text
stratified reservoir sample of 128–512 agents
weighted by rare route / bottleneck usage
```

Record:

```text
requested_agent_count
encoded_OD_token_count
represented_agent_mass
represented_flow_mass
```

Required:

```text
represented_agent_mass = requested_agent_count
```

### 5.4 Compute traffic on the full graph

For each actual start-goal pair:

```text
compute a valid shortest path on the full physical graph
accumulate directed edge demand
accumulate opposing demand
derive C0 and F0
then aggregate to the corridor supergraph
```

For large agent counts:

```text
cache reverse shortest-path trees per unique goal
or group/sparsify goals
or use bounded multi-source shortest paths
```

Required traffic gates:

```text
path_found_rate >= 0.999
nonzero_flow_context_rate reported
edge_use_total approximately equals summed path lengths
flow mass preserved after graph coarsening
```

---

## 6. Instance identity and scenario integrity

Create two immutable identifiers.

```text
instance_uid = hash(
  physical_map_sha256,
  paired_start_goal_assignment_sha256,
  agent_count,
  planning_budget,
  ltm_iteration_budget
)
```

```text
evaluation_uid = hash(
  instance_uid,
  solver_rng_seed
)
```

The neural network may receive:

```text
instance features
budget
```

It must not receive:

```text
solver RNG seed
candidate ID
posthoc outcome
```

Labels may aggregate multiple `evaluation_uid` replicates under the same `instance_uid`.

Actual scenario files must be archived or hash-addressable.

No synthetic start/goal reconstruction may be used for solver labels.

---

## 7. Label-v5: real solver preference and safe-set labels

G5.59 must generate Label-v5 from real paired solver runs.

### 7.1 Pair record

For each:

```text
(instance_uid, evaluation_uid, theta_id)
```

record:

```text
candidate_success
baseline_success
success_regression
success_gain
both_success
both_fail
quality_delta_vs_g556
candidate_recognized
fingerprint_match
cost_finite
theta_in_bounds
runtime
search-effort metrics
```

### 7.2 Replicate aggregation

For each `(instance_uid, theta_id)`:

```text
replicate_count
success_regression_count
success_gain_count
quality_delta_mean
quality_delta_CI
worst_replicate_delta
```

Development-safe:

```text
regression_rate below calibrated research threshold
```

Promotion-safe:

```text
zero regression in all required fresh replicates
```

### 7.3 Safe sets and preferences

For each instance:

```text
safe theta set
safe-improving theta set
Pareto theta set
top-k safe theta set
fallback-required label
```

Construct pairwise preferences only when:

```text
quality difference exceeds a noise/margin threshold
or bootstrap confidence supports the order
```

Ties remain ties.

### 7.4 Soft listwise target

For safe candidates:

```text
target probability ∝ exp(-normalized_quality_delta / temperature)
```

Unsafe candidates have zero probability in the safe-utility distribution.

### 7.5 Context-balanced weighting

Each `instance_uid` contributes equal total weight.

Do not let 128 candidate rows for one instance count as 128 independent graph samples.

---

## 8. Candidate slate and active optimization

Do not reuse the same first 64 theta candidates for every context.

### 8.1 Global codebook

Construct 2,048–8,192 candidates using:

```text
Sobol / Latin hypercube residuals around g556
G5.54–G5.56 promoted/near-miss candidates
field-group perturbations
C/F-channel ablation candidates
goal-mode diagnostics
CMA-ES/CEM global elites
```

### 8.2 Per-instance initial slate

For each pilot instance select 64–96 candidates:

```text
16 nearest trust-region candidates
16 space-filling candidates
16 topology/flow-informed candidates
8 known strong global candidates
8 hard-negative candidates
optional 8 control candidates
```

Rotate candidates so codebook coverage is broad.

### 8.3 Multi-fidelity replay

For each instance:

```text
Level 0:
  baseline + 64–96 theta at short budget

Level 1:
  top 12–16 safe/uncertain theta at medium budget

Level 2:
  top 3–5 theta + baseline at target budget

Level 3:
  replicate-confirmation seeds for selected labels
```

Measure short-to-full budget rank transfer.

Short-budget labels cannot become promotion evidence without full-budget confirmation.

### 8.4 Contextual optimization teacher

For a subset of training instances run:

```text
CEM or CMA-ES around g556
```

Use it to enrich the safe theta frontier.

This is a teacher/control, not the deployed method.

---

## 9. Two-stage proof strategy

Direct continuous generation is not the first gate.

### Track A — neural critic + codebook selection

Train:

```text
instance + candidate theta -> safety / utility
```

At inference:

```text
score the global codebook
select the best calibrated-safe theta
or fall back to g556
```

This proves whether the instance representation contains useful theta-selection signal.

### Track B — continuous multi-proposal generator

Only after Track A beats controls.

Train:

```text
instance -> K continuous residual theta proposals
```

Then score proposals with the frozen/finetuned critic.

Final paper method may be Track B, but Track A is the necessary learnability bridge.

---

## 10. Loss repair

### 10.1 Critic loss

Use:

```text
asymmetric focal BCE for success regression
BCE for success gain
Huber or Gaussian NLL for quality delta
quantile pinball loss
pairwise ranking loss inside each instance
listwise KL / ListNet loss to safe-utility distribution
calibration penalty
hard-negative margin loss
```

Batch structure must include:

```text
multiple theta candidates from the same instance
```

Random independent row batches are insufficient for listwise learning.

### 10.2 Generator loss

Use:

```text
best-of-K distance to safe theta-cluster representatives
set matching / Chamfer loss
critic-guided expected safe utility
per-instance proposal diversity
fallback classification
field-bound penalty
```

Do not compute diversity across proposals belonging to different instances.

Do not use one-oracle-theta MSE as the main loss.

---

## 11. Correct metric implementation

No proxy metrics.

### 11.1 Critic metrics

Compute from model predictions:

```text
success-regression PR-AUC
success-regression recall at fixed precision
Brier score
ECE
quality Spearman
quality NDCG
pairwise ranking accuracy
top-k safe recall
top-k safe-improving recall
oracle regret
```

### 11.2 Generator metrics

Compute actual:

```text
best-of-K safe-set hit rate
best-of-K safe-improving hit rate
minimum theta distance to safe frontier
critic-predicted and actual codebook regret
proposal diversity per instance
fallback accuracy from predicted fallback logits
```

### 11.3 Coverage-risk

Generate from actual model confidence/risk scores:

```text
coverage
success-regression rate
quality delta
better/worse count
```

No hard-coded table rows.

### 11.4 Evaluation units

Report:

```text
pair-row metrics
instance-level metrics
physical-map-level metrics
map-family worst-group metrics
density-bin metrics
budget metrics
```

---

## 12. Synthetic contract tests

Synthetic labels are allowed only as implementation tests.

### 12.1 Analytic label contract

Because the synthetic label is generated by a known function, require:

```text
ranking accuracy >= 0.98
quality R² >= 0.98
safe classification >= 0.99
fallback accuracy >= 0.99
best-of-K safe-set hit >= 0.98
```

If this fails, fix code before real labels.

### 12.2 Graph tests

Required:

```text
full graph connectivity preserved
coarsened graph connectivity preserved
batch composition invariance
node-order permutation invariance
map perturbation changes embedding
start-goal permutation preserves aggregate prediction
start-goal pairing permutation changes prediction when flows change
all-agent mass conservation
traffic flow conservation
```

### 12.3 Metric tests

Construct hand-made predictions and prove:

```text
ranking metric is correct
safe recall is not trivially 1
fallback metric uses predictions
coverage-risk uses model outputs
generator hit rate uses generated theta
```

---

## 13. Pilot real-solver Label-v5 experiment

Run this first on the server.

### 13.1 Pilot physical maps

Minimum:

```text
24 distinct physical map hashes
6 map families
```

Use:

```text
empty/open
random
maze
room
warehouse
irregular/bottleneck
```

### 13.2 Pilot instances

Minimum:

```text
2,000 unique instance_uids
```

Balanced across:

```text
map
density
start-goal flow pattern
budget
```

### 13.3 Pilot rows

Target:

```text
2,000 instances × 64 candidate theta
= 128,000 short-budget candidate rows

plus g556 baseline rows
plus medium/full fidelity confirmation
```

Preferred total:

```text
180,000–300,000 fresh solver rows
```

### 13.4 Pilot gate

Continue only if at least one learned route satisfies:

```text
beats agent-density lookup
beats GBDT
beats tabular MLP
nonfallback coverage >= 5%
heldout-map quality delta < 0
calibrated false-safe rate has a usable operating point
graph+goal+traffic ablation is better than graph-only/no-traffic
```

The pilot gate does not require zero solver regressions.

---

## 14. Full AAAI-scale Label-v5 dataset

Only after pilot success.

Minimum:

```text
unique physical map hashes >= 80
unique instance_uids >= 30,000
preferred unique instance_uids >= 60,000

map families >= 7
start-goal regimes >= 8
density bins >= 8
budget/horizon profiles >= 12

real pair rows >= 1,500,000
preferred 3,000,000–6,000,000
```

A pair row is not an independent instance. Always report both.

### 14.1 Actual generated maps

Generate physically distinct maps with:

```text
connectivity constraint
free-cell ratio bounds
corridor-width controls
room/door morphology
bottleneck count
warehouse aisle parameters
```

Hash every layout.

Do not count aliases as new maps.

### 14.2 Split

Use:

```text
train maps
validation physical-map hashes
heldout physical-map hashes
family-heldout diagnostics
blind maps
```

No physical hash overlap.

---

## 15. Self-supervised pretraining

Before solver-label fine-tuning, pretrain the instance encoder on unlabeled instance data.

Tasks:

```text
masked node-feature reconstruction
masked edge-flow reconstruction
predict C0/F0 summary
predict shortest-path distance histogram
contrast actual start-goal pairing against shuffled pairing
predict bottleneck-demand quantiles
graph augmentation consistency
```

Minimum:

```text
50,000 unlabeled instance contexts
```

Preferred:

```text
100,000+
```

This gives graph/traffic attention a meaningful initialization before expensive Label-v5 training.

---

## 16. Model architecture

### 16.1 Hierarchical graph encoder

Recommended:

```text
corridor-junction GraphGPS / GATv2
4–6 local edge-aware layers
2–4 per-graph sparse/global attention layers
hidden size 192–256
8 heads
```

### 16.2 Raster/flow branch

Recommended control or fusion branch:

```text
small U-Net / ResNet over:
obstacle, starts, goals, C0, F0, opposing flow, bottleneck channels
```

### 16.3 OD encoder

Use:

```text
Set Transformer with inducing points
or stratified OD tokens + all-agent summary fields
```

### 16.4 Fusion

Use cross-attention between:

```text
graph structural tokens
flow/raster tokens
OD tokens
budget token
```

### 16.5 Parameter head

Output:

```text
K = 8–16 residual theta proposals
fallback logit
proposal confidence
goal-mode logits
```

---

## 17. Training protocol on RTX5090

Assume one RTX5090 with approximately 32 GB VRAM unless runtime audit says otherwise.

Use:

```text
bf16 mixed precision
gradient accumulation
gradient checkpointing
torch.compile if stable
streaming Parquet/Arrow dataset
checkpoint/resume
```

### 17.1 Critic

```text
minimum optimizer steps = 30,000
target = 80,000–200,000
3 random seeds for final model
```

### 17.2 Generator

```text
minimum optimizer steps = 20,000
target = 50,000–120,000
```

### 17.3 Joint fine-tuning

```text
10,000–30,000 steps
```

Early stopping is disabled before minimum steps.

Record:

```text
GPU utilization distribution
VRAM usage
steps/sec
examples/sec
loss terms separately
train/validation curves
checkpoint hashes
```

---

## 18. Real controls

Implement independently:

```text
always g556_c063174
agent-density lookup
map-family lookup
GBDT on scalar summaries
TabM/MLP
Set Transformer without graph adjacency
raster CNN
GATv2 without global attention
hierarchical GraphGPS
CMA-ES/CEM teacher/control
```

The G5.58 agent-density result is a strong control, not a nuisance.

The main model must show that:

```text
graph + paired goals + traffic
adds value beyond density
```

---

## 19. Ablations

Required:

```text
remove traffic prior
remove goal pairing but retain start/goal histograms
remove graph topology
remove edge features
remove F channel
remove C channel
remove global attention
remove local message passing
single proposal
single-oracle regression
no self-supervised pretraining
no hard-negative mining
no fallback
```

Important causal ablation:

```text
shuffle the start-goal pairing while preserving the same start set and goal set
```

If performance does not change, the model is not using goal-aware flow information.

---

## 20. Active learning loop

After each training round, acquire new labels from:

```text
high model uncertainty
critic-generator disagreement
graph-vs-tabular disagreement
predicted safe high-utility proposals
hard-negative boundary regions
underrepresented map morphologies
heldout-like embeddings
```

Round structure:

```text
Round 0: pilot Label-v5
Round 1: 10,000–20,000 new instances × 32–64 candidates
Round 2: hard-negative top-up
Round 3: only if validation continues improving
```

Every round must update:

```text
dataset manifest
physical-map split manifest
label provenance
model checkpoint
coverage-risk curve
```

---

## 21. Layered gates

### 21.1 Implementation gate

Requires all synthetic contract tests and representation tests.

### 21.2 Real learnability gate

Requires:

```text
real solver labels
heldout physical maps
main model beats density/GBDT/MLP
nonfallback coverage >= 5%
negative mean quality delta
useful coverage-risk point
```

Small observed regression is allowed at this research gate.

### 21.3 Diagnostic Stage1 gate

Requires:

```text
policy frozen
materialization pass
risk calibration
fresh contexts
```

No paper or runtime claim.

### 21.4 Promotion gate

Remains strict:

```text
success regressions vs g556 = 0
success rate non-worse
quality delta < 0
CI upper <= 0
better > worse
fingerprint = 1
recognized = true
cost finite = true
theta bounded = true
```

---

## 22. Solver validation ladder

### Stage1

```text
minimum 200,000 fresh paired rows
preferred 400,000
```

Test multiple policy thresholds:

```text
high coverage
medium coverage
strict low-risk coverage
```

### Stage2

```text
minimum 600,000 fresh rows
heldout physical maps
```

### Blind

```text
minimum 720,000 fresh rows
new physical-map hashes
no tuning after freeze
```

---

## 23. Artifact durability

The G5.57 raw labels were unavailable on the RTX5090 server. This must not recur.

Store:

```text
/root/shared-nvme/czr004_g559_remote_artifacts/
```

Use partitioned Parquet:

```text
contexts/
candidates/
pair_rows/
replicate_aggregates/
graph_tensors/
traffic_tensors/
checkpoints/
solver_logs/
```

Maintain:

```text
artifact_registry.json
schema version
absolute/relative URI
SHA256
row count
physical size
producer command
source commit
```

At round completion, create:

```text
compact bundle
raw-data transfer manifest
resume script
checksum verification script
```

Do not delete raw pair rows until at least two verified copies exist.

---

## 24. Required code structure

Extend `src/gcst` rather than replacing it with one monolith.

Recommended additions:

```text
src/gcst/
  graph_coarsening.py
  raster_encoder.py
  hierarchical_encoder.py
  listwise_losses.py
  label_v5.py
  multi_fidelity.py
  active_acquisition.py
  artifact_registry.py

scripts/
  audit_repair5g559_g558_failure.py
  build_repair5g559_corridor_graphs.py
  generate_repair5g559_real_instances.py
  run_repair5g559_labelv5_pilot.py
  analyze_repair5g559_labelv5_pilot.py
  pretrain_repair5g559_instance_encoder.py
  train_repair5g559_codebook_critic.py
  train_repair5g559_continuous_generator.py
  eval_repair5g559_real_learnability.py
  plan_repair5g559_active_round.py
  run_repair5g559_active_round.py
  freeze_repair5g559_policy.py
  run_repair5g559_stage1.py
  run_repair5g559_stage2.py
  run_repair5g559_blind.py
  write_repair5g559_decision.py
```

---

## 25. Required tests

```text
test_graph_connectivity_preserved
test_corridor_graph_shortest_path_distortion
test_batch_composition_invariance
test_batch_order_invariance
test_node_permutation_invariance
test_agent_mass_conservation
test_flow_mass_conservation
test_actual_scenario_pairing
test_solver_seed_excluded_from_features
test_context_balanced_weighting
test_listwise_loss_orders_candidates
test_pairwise_loss_handles_ties
test_safe_recall_metric_nontrivial
test_fallback_metric_uses_prediction
test_coverage_risk_uses_predictions
test_generator_hit_rate_uses_generated_theta
test_checkpoint_resume
test_theta_fixed_for_run
test_reserved_ids_166_205_rejected
```

---

## 26. Mandatory failure branches

### If synthetic ranking still fails

Stop and fix:

```text
graph batch leakage
ranking loss
metric implementation
candidate normalization
```

### If synthetic passes but real critic fails

Investigate:

```text
solver-label noise
short/full-budget transfer
candidate slate quality
feature insufficiency
```

### If critic codebook selection works but generator fails

Do not abandon GCST.

Use:

```text
critic-selected codebook policy as teacher
more safe-set generator training
conditional flow/diffusion diagnostic in 15D theta space
```

### If density lookup remains stronger

Analyze whether:

```text
graph features are too compressed
traffic priors are noisy
candidate optimum mostly depends on density
```

This is a meaningful scientific result and should guide a simpler model.

### If no oracle opportunity remains

Compute real per-instance oracle gap. If the real candidate slate rarely beats g556, the blocker is candidate space, not the neural model.

---

## 27. Claim policy

Keep closed:

```text
phase5p5_allowed = false
phase6_allowed = false
runtime_claim_allowed = false
learned_runtime_policy_validated = false
aaai_ready = false
```

Even a successful Stage1 is not a runtime or AAAI claim.

A blind pass may promote:

```text
graph-conditioned run-static theta predictor
```

but does not validate a dynamic UpdateLTM policy.

---

## 28. Decision labels

```text
g559_g558_representation_bug_confirmed
g559_synthetic_contract_failed
g559_real_labelv5_pilot_underpowered
g559_no_real_oracle_gap_keep_g556
g559_codebook_critic_learnability_passed
g559_continuous_generator_learnability_passed
g559_real_learnability_failed_continue_feature_or_label_repair
g559_stage1_failed_keep_g556
g559_stage2_failed_keep_g556
g559_blind_failed_keep_g556
g559_dualtraffic_hgt_gcst_blind_passed_keep_claims_closed
```

---

## 29. Main question

G5.59 must answer:

```text
After correcting graph topology, all-agent flow representation, ranking objectives,
metrics, and real solver labels, can a hierarchical goal-aware dual-traffic graph
transformer predict one static dual-channel UpdateLTM theta per MAPF instance that
outperforms g556_c063174?
```

Do not answer this question from synthetic labels, requested epochs, or loss decrease.

Only real heldout-map solver evidence can answer it.
