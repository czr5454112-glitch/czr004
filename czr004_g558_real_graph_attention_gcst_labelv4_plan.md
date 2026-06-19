# Repair5G.5.58 Plan — Real Graph-Attention GCST, Label-v4 Repair, Local Learnability Proof, and Server-Scale Active Replay

Project: `czr004`
Repository: `czr5454112-glitch/czr004`
Required branch: `server-code`
Start commit: `097f495b34296b684cc575b91043757dcb92ef72`
Primary baseline: `g556_c063174`
Round name: `Repair5G.5.58 real neural graph-conditioned static-theta repair`

---

## 0. Executive decision

G5.58 continues the graph-conditioned static-theta direction.

The target method remains:

```text
(map graph, starts, goals, agent distribution, pre-run traffic priors, run budget)
    -> neural network
    -> one bounded dual-channel UpdateParams theta
    -> theta is fixed for the entire solver run
```

Do not return to a universal fixed theta as the main scientific method, and do not jump to a checkpoint-conditioned or runtime-dynamic policy.

However, G5.57 must not be interpreted as a clean negative result for a Graph Transformer. The G5.57 pipeline completed substantial solver data generation, but its committed implementation did not train the planned neural TTGT model.

The correct interpretation is:

```text
G5.57 engineering pipeline: completed
G5.57 label matrix: large and potentially valuable
G5.57 deterministic aggregate lookup/scorer: negative
real graph-attention GCST neural model: not yet tested
```

G5.58 must first close this implementation gap, prove that a real neural model can learn on a small trustworthy subset, and only then use the two RTX 4090 GPUs and run additional expensive solver replay.

---

## 1. Source-of-truth audit of G5.57

Before writing new model code, inspect commit:

```text
097f495b34296b684cc575b91043757dcb92ef72
```

Required files:

```text
czr004_g557_graph_conditioned_static_theta_aaai_plan.md
scripts/repair5g557_common.py
scripts/train_eval_repair5g557_ttgt_outcome_model.py
scripts/train_eval_repair5g557_gcst_generator.py
outputs/reports/phase5p5_repair5g557_decision_summary.json
outputs/reports/phase5p5_repair5g557_label_matrix_summary.json
outputs/reports/phase5p5_repair5g557_label_v3_dataset_summary.json
outputs/reports/phase5p5_repair5g557_ttgt_outcome_eval_summary.json
outputs/reports/phase5p5_repair5g557_gcst_generator_eval_summary.json
outputs/tables/phase5p5_repair5g557_control_metrics.csv
outputs/tables/phase5p5_repair5g557_label_matrix_by_topology.csv
outputs/tables/phase5p5_repair5g557_map_topology_manifest.csv
outputs/tables/phase5p5_repair5g557_graph_feature_manifest.csv
artifacts/models/laur_ltm/repair5g557_ttgt_outcome_manifest.json
```

The audit must explicitly verify the following findings.

### 1.1 No real TTGT neural training occurred

G5.57 reports:

```text
epochs_requested = 120
gpus_requested = 2
training_backend = deterministic_aggregate_scorer
```

The implementation of `main_train_eval_ttgt_outcome_model` builds aggregate score tables and evaluates lookup-based candidate selection. It does not instantiate a `torch.nn.Module`, run backpropagation, step an optimizer, or save learned graph-attention weights.

Therefore:

```text
g557_real_neural_model_trained = false
g557_graph_attention_executed = false
g557_optimizer_steps = 0
g557_gpu_training_claim_valid = false
```

Do not call the G5.57 scorer TTGT in G5.58 reports. Rename it:

```text
G5.57 deterministic aggregate lookup control
```

### 1.2 The G5.57 all-fallback result was partly induced by scorer/gate design

The scorer falls back if:

```text
predicted_regression_rate > 0.002
or support < 32
or score <= 0
```

Its utility assigns:

```text
success regression = -10
success gain = +5
otherwise utility = -quality_delta
```

Most quality deltas are orders of magnitude smaller than the regression penalty. Aggregate candidate regression rates are nonzero, so score collapse and fallback are expected.

The result:

```text
fallback_to_g556_rate = 1.0
```

is valid for that conservative lookup rule, but it is not evidence that a learned graph model cannot identify context-specific safe candidates.

### 1.3 Graph and traffic features were mostly manifests or proxies

Audit whether each declared graph cache file actually contains node and edge tensors.

G5.57 code currently records feature names and a proxy bottleneck score, but does not construct the planned graph tensors.

The pre-run traffic features currently use `stable_unit(...)` pseudo-random deterministic proxies. They are not computed from actual start-goal paths, edge overlap, directionality, or graph flow.

Required conclusions:

```text
g557_actual_node_tensor_count
g557_actual_edge_tensor_count
g557_actual_start_goal_assignment_count
g557_actual_od_flow_computation_used
g557_synthetic_hash_proxy_feature_count
```

### 1.4 “60 topology variants” did not mean 60 distinct physical graphs

The G5.57 context builder assigns extra `qd_*` topology IDs while reusing existing map files. These aliases do not add physical graph diversity.

Count topology using:

```text
physical_map_sha256
adjacency_sha256
free_cell_bitmap_sha256
```

not `topology_id`.

Report:

```text
declared_topology_ids
unique_physical_map_hashes
duplicate_topology_alias_count
heldout_physical_map_hashes
train_test_physical_hash_overlap
```

No map file or adjacency hash may occur in more than one split.

### 1.5 Effective theta coverage was 512, not 20,000 per experiment

G5.57 generated a registry of 20,000 candidates, but the actual run sliced:

```python
candidates[:args.candidates_per_context]
```

with:

```text
candidates_per_context = 512
```

Thus the effective evaluated candidate set was 512 theta vectors.

Report both:

```text
registry_unique_theta_count
effective_label_matrix_unique_theta_count
per_context_theta_count
candidate_family_coverage
theta_parameter_space_coverage
```

### 1.6 Pair metadata appears partially disconnected from the context bank

The committed `label_matrix_by_topology.csv` has blank topology IDs. This indicates a context-key/context-ID join failure or metadata loss.

Before model training, require:

```text
context_uid_nonempty_rate = 1
topology_id_nonempty_rate = 1
physical_map_hash_nonempty_rate = 1
start_goal_assignment_hash_nonempty_rate = 1
graph_tensor_join_rate = 1
traffic_tensor_join_rate = 1
```

### 1.7 Controls were not all genuine implementations

In G5.57, several declared controls map back to `tabular_only`. Negative controls are recorded as status rows rather than trained models.

However, the committed `agent_density_lookup` diagnostic is an important positive signal:

```text
heldout contexts = 1,519
nonfallback contexts = 328
success regressions = 0
success gains = 9
quality delta = -0.00118034841494
CI upper = -0.000503980783512
```

This suggests that context-conditioned static theta has exploitable signal even before a real graph model is trained. Treat `agent_density_lookup` as:

```text
strong control
possible teacher/prior
fallback hierarchy component for diagnostics
```

The real GCST model must beat it on heldout physical maps and must show that graph, goal, and traffic information adds value beyond density.

G5.58 must implement each control independently and prove it ran.

Write:

```text
outputs/reports/phase5p5_repair5g558_g557_truth_audit.md
outputs/reports/phase5p5_repair5g558_g557_truth_audit_summary.json
outputs/tables/phase5p5_repair5g558_implementation_gap_audit.csv
outputs/tables/phase5p5_repair5g558_effective_data_scale_audit.csv
outputs/tables/phase5p5_repair5g558_context_join_audit.csv
outputs/tables/phase5p5_repair5g558_physical_map_hash_audit.csv
```

Stop full-scale training if the audit does not complete.

---

## 2. Scientific interpretation of the G5.57 data

The G5.57 solver data still contains encouraging evidence:

```text
same-context pair rows: 6,144,000
contexts in label matrix: 12,000
safe-improving contexts: 6,152
no-safe-improvement contexts: 5,848
effective theta candidates: 512
```

Approximately half of the contexts contain at least one materialized safe-improving candidate in the evaluated slate.

This means the core opportunity hypothesis remains plausible:

```text
The best dual-channel UpdateParams depends on the MAPF instance.
```

But row count must not be confused with independent graph-learning sample size.

For the instance encoder:

```text
effective independent examples ~= unique contexts
```

not:

```text
contexts × theta candidates
```

The 6.144M pair rows are useful for learning a candidate-conditioned critic, but only 12,000 unique contexts supervise graph/instance generalization.

G5.58 must report all data scales separately:

```text
pair rows
unique physical maps
unique adjacency hashes
unique start-goal assignments
unique solver contexts
unique theta vectors
candidate rows per context
effective context weights
```

---

## 3. G5.58 candidate object

A G5.58 candidate is:

```text
one graph-conditioned bounded static theta predicted before a solver run
```

Allowed input:

```text
physical map graph
actual start vertices
actual goal vertices
agent count and spatial density
actual start-goal assignment
OD/path-flow priors computed from the instance
actual graph topology features
run budget and LTM iteration budget
optional fixed baseline warm-up probe in a separate diagnostic track
```

Output:

```text
theta_alpha_cong_commit_progress
theta_alpha_cong_commit_nonprogress
theta_alpha_cong_block
theta_alpha_cong_wait_progress
theta_alpha_cong_wait_nonprogress
theta_alpha_flow_commit_progress
theta_alpha_flow_wait_progress
theta_rho_cong_decay
theta_rho_flow_decay
theta_lambda_cong
theta_lambda_flow
theta_flow_shield_beta
theta_max_flow_shield
theta_min_edge_cost
theta_max_edge_cost
theta_goal_projection_mode
```

The output theta is fixed for the full solver run.

Forbidden:

```text
changing theta at checkpoints
using main-run trace before predicting theta
future solver outcomes as input
candidate IDs as model features
map IDs as the primary feature
per-instance offline oracle lookup at evaluation time
agent actions, priorities, restart nodes, h-values, or candidate deletion
changes to external/lacam2/lacam2
```

---

## 4. Literature and code audit

G5.58 must inspect papers and official code, recording exact commits and licenses where code exists.

### 4.1 Guidance Graph Optimization — IJCAI 2024

Paper:

```text
Guidance Graph Optimization for Lifelong Multi-Agent Path Finding
arXiv:2402.01446
```

Official code:

```text
https://github.com/lunjohnzhang/ggo_public
```

Required lessons:

```text
guidance is solver-facing and must be evaluated by simulation
CMA-ES is a strong non-neural black-box control
PIU uses traffic information to update guidance
training and evaluation cover multiple map structures and large agent counts
```

Do not vendor the code. Audit architecture, configuration, simulation count, map split, and optimization procedure.

### 4.2 LaGAT — graph attention integrated with LaCAM

Paper:

```text
Graph Attention-Guided Search for Dense Multi-Agent Pathfinding
arXiv:2510.17382
```

Official code cited by the paper:

```text
https://github.com/proroklab/lagat
```

Required lessons:

```text
real graph-attention layers with edge features
pretrain then fine-tune
21K generic instances plus 1K target-map instances in the paper
200-epoch pretraining and multi-hour fine-tuning
hybrid search retains non-learning safeguards
model imperfections require explicit handling
```

G5.58 does not imitate actions and does not modify PIBT. It adopts the training rigor, edge-aware attention, map generalization analysis, and shielded hybrid methodology.

### 4.3 CS-PIBT lesson

Paper:

```text
Work Smarter Not Harder: Simple Imitation Learning with CS-PIBT...
arXiv:2409.14491
```

Required lesson:

```text
700K high-quality examples alone did not guarantee a good learned MAPF policy
architecture-task alignment and a strong shield matter more than raw row count
```

For czr004, the shield remains `g556_c063174` plus real solver replay.

### 4.4 MAPF-GPT and large training sets

Paper:

```text
MAPF-GPT: Imitation Learning for Multi-Agent Pathfinding at Scale
arXiv:2409.00134
```

Use only as a scale and training-protocol reference. Do not copy the action-policy formulation.

### 4.5 Graph Transformer references

Audit:

```text
GraphGPS — local message passing + global attention
Exphormer — sparse/global graph attention
Accelerating Multi-Agent Planning Using Graph Transformers with Bounded Suboptimality — arXiv:2301.08451
```

Select the lightest architecture that can process real grid graphs on 2×4090.

### 4.6 MAPF map diversity

Audit:

```text
A Quality Diversity Method to Automatically Generate MAPF Benchmark Maps
arXiv:2409.06888
```

Generated maps must be actual new obstacle/free-cell layouts, not aliases for existing maps.

Write:

```text
outputs/reports/phase5p5_repair5g558_literature_code_audit.md
outputs/tables/phase5p5_repair5g558_literature_design_matrix.csv
outputs/tables/phase5p5_repair5g558_external_repo_commit_audit.csv
```

---

## 5. Local-first versus server-first decision

G5.58 must be local-first for implementation truth and learnability.

Do not immediately launch another multi-million-row server experiment.

Reason:

```text
G5.57 already has enough pair rows to test whether a real model implementation can learn.
The primary blocker is not raw solver row count.
The primary blockers are model non-implementation, metadata loss, proxy features, and all-fallback gate design.
```

Use the server only after the following local gates pass:

```text
real torch model instantiated
nonzero gradient/backpropagation verified
tiny subset overfit succeeds
graph/goal/traffic input sensitivity succeeds
validation beats real tabular controls
nonfallback coverage is nonzero
```

If the local machine cannot run the model efficiently, use the server for a bounded `g558_smoke` job only:

```text
one GPU
<= 5,000 contexts
<= 128 candidates per context
no new solver generation
no Stage1/Stage2/blind
```

Only after the smoke passes may Codex launch the full 2×4090 training job.

---

## 6. Label-v4 design

G5.57 Label-v3 selected one oracle theta per context and exposed top-k IDs. This is inadequate as the sole generator target because the safe optimum is multimodal: many distant theta vectors can be similarly good.

G5.58 uses Label-v4.

### 6.1 Immutable context identity

Create:

```text
context_uid = SHA256(
  physical_map_sha256,
  start_positions_sha256,
  goal_positions_sha256,
  agent_count,
  solver_seed,
  nominal_budget_ms,
  short_budget_ms,
  base_time_limit_sec,
  ltm_max_iterations
)
```

This key must survive scenario generation, solver execution, pair construction, graph joins, and model splits.

### 6.2 Pair-level labels

For every `(context_uid, theta)`:

```text
selected_success
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
```

### 6.3 Context-level safe set

For every context:

```text
safe_theta_ids
safe_improving_theta_ids
Pareto_theta_ids
top_k_safe_theta_ids
fallback_required
best_observed_quality_delta
safe_frontier_size
theta_cluster_representatives
```

### 6.4 Soft listwise target

Define a soft target over safe candidates:

```text
p*(theta | context) ∝ exp(-quality_delta / temperature)
```

Unsafe candidates receive zero target probability for the safe-distribution head.

Do not train the generator with plain MSE to one oracle theta.

### 6.5 Multimodal target clusters

Cluster safe-improving theta by normalized parameter distance. Store 4–16 representatives per context.

Train a K-proposal generator with best-of-K or set-matching loss.

### 6.6 Context-balanced weighting

Each context contributes equal total weight:

```text
row_weight = 1 / candidate_rows_for_context
```

Otherwise a context with 512 candidates dominates a context with 64 candidates.

Also balance:

```text
physical map
map family
agent-density bin
start-goal regime
budget
success-regression hard negatives
```

### 6.7 Split policy

Split first by physical map hash:

```text
train physical maps
validation physical maps
heldout physical maps
family-heldout diagnostic maps
```

Then split start-goal assignments inside train maps.

Hard constraints:

```text
no physical map hash overlap
no start-goal assignment hash overlap
no scenario hash overlap
candidate IDs not used as features
no outcome leakage
```

### 6.8 Salvage existing G5.57 rows

Existing rows may be reused only after:

```text
context_uid recovered
topology/map metadata recovered
actual start and goal positions recovered
physical graph hash attached
graph tensor attached
traffic prior recomputed from actual instance
```

Rows that cannot be repaired remain solver-outcome diagnostics, not graph-model training examples.

Write:

```text
outputs/reports/phase5p5_repair5g558_label_v4_repair.md
outputs/reports/phase5p5_repair5g558_label_v4_summary.json
outputs/tables/phase5p5_repair5g558_label_v4_join_audit.csv
outputs/tables/phase5p5_repair5g558_label_v4_split_audit.csv
outputs/tables/phase5p5_repair5g558_context_effective_sample_audit.csv
```

---

## 7. Real map, agent, goal, and traffic representation

### 7.1 Physical map graph

For each real map:

```text
node = traversable cell
directed edge = legal move
```

Node features:

```text
normalized x/y
degree
dead-end flag
corridor flag
room/intersection flag
door/choke candidate
local obstacle density at multiple radii
connected-component size
distance to nearest obstacle
approximate betweenness
articulation/near-cut score
Laplacian or random-walk positional encoding
start count/density
goal count/density
```

Edge features:

```text
orientation
edge length
corridor-axis alignment
approximate edge betweenness
shortest-path OD flow
opposing-direction OD flow
flow imbalance
head-on-conflict pressure
local C-prior
local F-prior
```

### 7.2 Actual start-goal distribution

Do not encode only entropy proxies.

Store actual:

```text
start vertex list
goal vertex list
paired start-goal assignments
shortest-path distance per agent
start and goal spatial histograms
source/sink imbalance
OD cluster assignments
```

### 7.3 Pre-run traffic prior

Compute from the actual instance.

Primary Mode P:

```text
sampled shortest paths or k-shortest paths
directed edge-use counts
opposing-flow counts
path-overlap concentration
bottleneck demand
expected head-on conflict pressure
goal-progress directionality
```

Derive initial traffic tensors:

```text
C0(e) = congestion/conflict-pressure prior
F0(e) = directed goal-progress flow prior
```

These are model inputs only. The real LTM C/F map still evolves from solver traces during the main run.

No stable-hash pseudo-random values are allowed as scientific features.

### 7.4 Optional Mode W

Only after Mode P works:

```text
run g556_c063174 for a fixed tiny probe
extract actual C/F snapshot
restart main solver from scratch
predict static theta
```

Report probe overhead separately. Mode W is not the primary G5.58 claim.

---

## 8. Actual neural architecture

Recommended method:

```text
SafeGCST-v2:
Graph-Attention Multi-Proposal Static-Theta Network
```

It consists of three learned components.

### 8.1 Instance encoder

Recommended default:

```text
GraphGPS-lite
  4–6 local GINE or GATv2 layers
  edge features enabled
  2–4 sparse/global attention blocks
  hidden dimension 192–256
  8 attention heads
  dropout 0.1
  residual connections and layer norm
```

For large maps, use graph coarsening or patch/landmark tokens:

```text
corridor segments
rooms/intersections
spatial patches
top-flow edges
global map token
```

Do not apply dense all-pairs attention over tens of thousands of free cells.

### 8.2 Agent-goal and traffic encoder

Use one of:

```text
Set Transformer over sampled agent OD tokens
cross-attention from OD tokens to graph nodes
flow tensor channels embedded directly on graph edges
```

The representation must contain actual paired start-goal information, not just agent count.

### 8.3 Multi-proposal theta generator

Output:

```text
K = 8 or 16 bounded theta proposals
one fallback-to-g556 logit
one proposal confidence per theta
```

Each proposal is a residual around `g556_c063174`:

```text
theta_k = clamp(theta_g556 + scale * tanh(delta_k))
```

Use field-specific residual scales.

The categorical goal projection mode is produced by logits.

### 8.4 Candidate-conditioned critic

Input:

```text
instance embedding + theta tokens
```

Outputs:

```text
p_success_regression
p_success_gain
expected_quality_delta
quality q10/q50/q90
uncertainty
materialization feasibility
```

The critic scores generated proposals and observed codebook candidates.

### 8.5 Static inference rule

Before the solver run:

```text
generate K theta proposals
score each proposal
apply calibrated risk threshold
choose best predicted safe proposal
if none pass, use g556_c063174
freeze chosen theta for entire run
```

This is still graph-conditioned static theta, not a dynamic policy.

---

## 9. Losses

Critic loss:

```text
asymmetric/focal BCE for success regression
BCE for success gain
Huber or Gaussian NLL for quality delta
pinball loss for quality quantiles
pairwise/listwise ranking loss within each context
Brier/calibration penalty
hard-negative margin loss
```

Generator loss:

```text
best-of-K distance to safe theta-cluster representatives
soft listwise distillation from safe utility distribution
critic-guided expected utility loss
diversity regularization between proposals
fallback classification loss
field-bound penalty
```

Robustness:

```text
GroupDRO across physical maps/topology families
context-balanced sampling
hard-negative replay buffer
candidate-family balancing
```

Do not use direct single-oracle theta MSE as the primary objective.

---

## 10. Mandatory implementation-truth gates

A model cannot be reported as trained unless all pass:

```text
torch.nn.Module exists
trainable_parameter_count >= 500,000
optimizer_step_count >= required minimum
nonzero gradient norm recorded
checkpoint contains state_dict and optimizer state
checkpoint size > 1 MB
training loss curve contains >= 100 logged points
validation metrics change over training
actual CUDA device used when requested
GPU utilization sampled during training
model outputs change under meaningful input perturbations
```

Write:

```text
outputs/reports/phase5p5_repair5g558_neural_implementation_truth.md
outputs/reports/phase5p5_repair5g558_neural_implementation_truth_summary.json
outputs/tables/phase5p5_repair5g558_training_step_audit.csv
outputs/tables/phase5p5_repair5g558_gpu_utilization_audit.csv
```

A deterministic lookup or aggregate scorer is a control and must never satisfy this gate.

---

## 11. Local learnability proof

This stage is mandatory before full server training.

### 11.1 Synthetic unit tests

Construct tiny graphs where the desired response is known:

```text
single corridor with opposing flow
two-route graph with one bottleneck
two rooms with one door
warehouse aisle with directional imbalance
open grid with uniform flow
```

The model should change relevant theta fields in the expected direction.

These are sanity tests, not scientific evidence.

### 11.2 Tiny overfit test

Dataset:

```text
128–256 real contexts
64 candidates per context
```

Required:

```text
critic train ranking accuracy > 0.95
critic train top-5 safe recall > 0.95
generator best-of-K safe-set hit rate > 0.90
fallback classification train accuracy > 0.95
loss visibly decreases
```

Failure means implementation or label mismatch. Stop before server scale.

### 11.3 Real local proof split

Use repaired existing rows:

```text
2,000–5,000 train contexts
500–1,000 validation contexts
500–1,000 physical-map-heldout contexts
64–128 candidates per context
```

Required development evidence:

```text
nonfallback coverage between 5% and 80%
safe opportunity recall better than agent-density lookup
safe utility better than tabular MLP and GBDT
coverage-risk curve reported
graph+goal+traffic beats graph-only and tabular-only
shuffled-label and random-feature controls fail
```

Do not require zero regressions to pass the local research gate.

Write:

```text
outputs/reports/phase5p5_repair5g558_local_learnability.md
outputs/reports/phase5p5_repair5g558_local_learnability_summary.json
outputs/tables/phase5p5_repair5g558_local_model_metrics.csv
outputs/tables/phase5p5_repair5g558_local_coverage_risk.csv
```

Possible decision:

```text
g558_local_learnability_passed_continue_server
g558_local_learnability_failed_stop_and_repair
```

---

## 12. Effective data-scale target

Raw rows are secondary. Prioritize unique physical maps and independent MAPF instances.

### 12.1 Minimum server-scale target

```text
unique physical map hashes >= 80
preferred >= 150

unique MAPF context_uids >= 50,000
preferred >= 100,000

actual start-goal assignments >= 50,000
preferred >= 100,000

map families >= 7
start-goal regimes >= 8
agent-density bins >= 8
budget/horizon settings >= 12

global theta codebook >= 8,000
preferred >= 20,000

new candidates evaluated per new context:
  initial top-up 64
  active hard-negative top-up 16–32

total pair rows:
  minimum 5,000,000 usable repaired/new
  preferred 8,000,000–12,000,000
```

### 12.2 Map structures

Use actual physical layouts:

```text
empty/open
random obstacles at multiple obstacle rates
mazes with multiple corridor widths
rooms with multiple room/door sizes
warehouse aisle variants
bottleneck/tunnel/tree/loop structures
game/irregular maps
actual generated QD/adversarial maps
```

A new topology counts only when the adjacency hash is new.

### 12.3 Agent scale

Use density-normalized curricula and absolute anchors:

```text
16, 24, 32
50, 75, 100
150, 200, 300, 400
600, 800, 1000
1500, 2000, 3000 where map capacity permits
```

Do not claim all scales for maps that cannot physically hold the agents.

### 12.4 Actual start-goal regimes

Implement actual generators:

```text
uniform random
opposite-side cross-flow
same-room local flow
room-to-room through doors
warehouse aisle-to-aisle
many-to-one goal cluster
clustered starts to dispersed goals
central choke-point crossing
low-conflict easy
high-conflict adversarial
```

Verify each generated scenario with measurable statistics, not a regime string alone.

---

## 13. Active label acquisition

Do not blindly generate another Cartesian product.

Begin with repaired G5.57 data, then add labels where they are informative.

Acquisition priorities:

```text
model/control disagreement
high uncertainty
predicted low-risk high-utility proposals
hard-negative neighborhoods
underrepresented physical maps
heldout-like topology embeddings
rare density/budget combinations
proposal regions near the safe/unsafe boundary
```

For each active round:

```text
Round 0: existing repaired data
Round 1: 20,000 new contexts × 64 theta ~= 1.28M candidate rows
Round 2: 10,000 hard contexts × 32 theta ~= 0.32M rows
Round 3: only if validation continues improving
```

Run baseline `g556_c063174` once per context and reuse the paired baseline result for candidate comparisons.

Maintain exact solver-row accounting.

---

## 14. Full two-GPU training

Only after local learnability passes.

Use:

```text
torchrun --standalone --nproc_per_node=2
mixed precision
DistributedDataParallel
gradient clipping
AdamW
cosine decay with warmup
checkpoint/resume
```

Training schedule should be step-based:

```text
minimum optimizer steps before early stop: 20,000
target critic steps: 80,000–200,000
target generator steps: 50,000–150,000
joint fine-tuning: 20,000–50,000
```

Run at least:

```text
3 seeds for the final architecture
3 seeds for strongest tabular control
1 seed for expensive ablations
```

Record:

```text
wall time
GPU utilization
GPU memory
examples/sec
optimizer steps
learning curves
best checkpoint selection rule
```

Do not equate requested epochs with completed learning.

---

## 15. Controls and ablations

Real controls:

```text
always g556_c063174
agent-density lookup
map-family lookup
map-ID lookup diagnostic
linear/ridge
GBDT
TabM/MLP
Set Transformer without graph edges
GATv2 only
GraphGPS-lite
CMA-ES/CEM instance-conditioned search diagnostic
```

Ablations:

```text
no actual starts/goals
unpaired start/goal histograms only
no traffic prior
no graph topology
no edge features
no global attention
no local message passing
single theta proposal instead of K proposals
single-oracle MSE instead of safe-set/listwise target
no hard-negative mining
no fallback head
```

Negative controls:

```text
shuffled labels
random graph features
permuted start-goal pairing
permuted map adjacency
candidate ID feature diagnostic
```

The main method should fail when graph/goal/traffic information is destroyed.

---

## 16. Offline evaluation

Report separately:

```text
critic quality
generator proposal quality
policy coverage
policy risk
fallback behavior
```

Required metrics:

```text
success-regression PR-AUC
safe-candidate top-k recall
safe-improvement opportunity recall
quality ranking Spearman/NDCG
best-of-K oracle regret
calibration ECE/Brier
coverage-risk curve
nonfallback coverage
per-map/per-family worst-group metrics
```

### 16.1 Research gate for diagnostic Stage1

Stage1 may open when:

```text
real neural implementation truth gate passed
local learnability passed
main model beats tabular and lookup controls
nonfallback coverage >= 5%
coverage-risk curve has a useful operating point
predicted selected quality is negative on heldout data
false-safe rate is calibrated and bounded
materialization checks pass
```

Zero offline regressions are not required to open a diagnostic Stage1.

### 16.2 Strict promotion gate

Promotion remains strict and is evaluated by fresh solver replay:

```text
zero success regressions vs g556_c063174
non-worse success rate
negative mean quality delta
CI upper <= 0
better_count > worse_count
fingerprint = 1
recognized = true
cost finite = true
theta in bounds = true
```

Separate the research gate from the final promotion gate.

---

## 17. Solver replay ladder

### Stage1 diagnostic replay

Minimum:

```text
150,000 fresh paired solver rows
preferred 300,000
fresh contexts
multiple calibrated coverage thresholds
g556 baseline
GCST policy
agent-density control
tabular control
```

If the strict policy is all fallback, still run a bounded diagnostic subset for:

```text
top-confidence nonfallback proposal
medium-confidence proposal
best codebook proposal
```

This is diagnostic only and cannot promote.

### Stage2 heldout physical-map replay

Minimum:

```text
600,000 fresh rows
physical maps absent from training
actual new start-goal assignments
```

### Blind replay

Minimum:

```text
720,000 fresh rows
no tuning after blind plan freeze
new physical maps or withheld map hashes
new scenario seeds
```

All claim flags remain closed unless a later governance decision explicitly changes them.

---

## 18. Required code structure

Do not put the entire round into another monolithic `repair5g558_common.py`.

Create modular code:

```text
src/gcst/
  __init__.py
  graph_data.py
  map_hash.py
  scenario_features.py
  traffic_prior.py
  label_v4.py
  graph_encoder.py
  od_encoder.py
  theta_generator.py
  theta_critic.py
  losses.py
  calibration.py
  inference.py
  metrics.py

scripts/
  audit_repair5g558_g557_truth.py
  repair_repair5g558_label_v4.py
  build_repair5g558_real_graph_cache.py
  build_repair5g558_real_traffic_prior.py
  train_repair5g558_critic.py
  train_repair5g558_generator.py
  eval_repair5g558_local_learnability.py
  plan_repair5g558_active_topup.py
  run_repair5g558_active_topup.py
  train_repair5g558_full_ddp.py
  freeze_repair5g558_static_theta_policy.py
  run_repair5g558_stage1.py
  run_repair5g558_stage2.py
  run_repair5g558_blind.py
  write_repair5g558_decision.py
```

Wrappers may be short, but actual model/data logic must live in auditable modules.

---

## 19. Tests

Required tests:

```text
test_context_uid_stability
test_physical_map_split_no_leakage
test_start_goal_pair_preserved
test_graph_tensor_matches_map
test_traffic_prior_uses_actual_paths
test_no_stable_hash_scientific_features
test_theta_bounds
test_generator_fixed_for_full_run
test_tiny_overfit
test_gradient_nonzero
test_checkpoint_roundtrip
test_graph_permutation_sensitivity
test_shuffled_label_control_fails
test_fallback_to_g556
test_reserved_ids_166_205_rejected
```

---

## 20. Server storage

Use:

```text
/root/shared-nvme/czr004_g558
/root/shared-nvme/czr004_g558_remote_artifacts
/root/shared-nvme/tmp
```

Large graph tensors, pair rows, checkpoints, and solver logs remain outside git.

Commit:

```text
compact summaries
small previews
hash manifests
model architecture/config
training curves
leaderboards
exact commands
```

Do not commit raw files above 50 MB.

---

## 21. Decision labels

```text
g558_g557_truth_audit_confirms_no_real_neural_training
g558_label_v4_join_repair_failed
g558_real_graph_features_not_materialized
g558_tiny_overfit_failed_stop
g558_local_learnability_failed_stop
g558_local_learnability_passed_continue_server
g558_full_training_no_advantage_over_controls
g558_gcst_offline_signal_found_continue_stage1
g558_stage1_failed_keep_g556
g558_stage2_failed_keep_g556
g558_blind_failed_keep_g556
g558_graph_conditioned_static_theta_blind_passed_keep_claims_closed
```

---

## 22. Forbidden shortcuts

Do not:

```text
call a lookup table a Graph Transformer
record requested epochs as completed training
record requested GPUs as evidence of GPU training
use stable hashes as traffic features
reuse one map file under multiple topology IDs and count them as new maps
use blank topology IDs in training
use candidate ID as a model feature
train only a direct MSE oracle-theta regressor
stop the whole round merely because the strict offline policy is all fallback
open Stage2/blind from offline metrics alone
modify external/lacam2/lacam2
use reserved IDs 166..205
```

---

## 23. Main scientific question

G5.58 must answer:

```text
When implemented as a real edge-aware graph-attention neural network,
trained on correctly joined physical-map, start-goal, and traffic-flow data,
can GCST predict one bounded dual-channel LTM theta per MAPF instance
that improves over g556_c063174 while remaining fixed for the entire run?
```

A clean negative is valuable only after:

```text
actual model training
actual graph tensors
actual start-goal flow features
proper physical-map holdout
non-degenerate controls
local learnability proof
fresh solver replay
```

Until then, G5.57 is not a negative result for the neural GCST hypothesis.
