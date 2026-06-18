# Repair5G.5.57 Plan — AAAI-Scale Graph-Conditioned StaticTheta for Goal-Aware Dual-Channel LTM

Project: `czr004`
Branch: `codex/g531-slice-pilot`
Start point: after G5.56 commit `d090d7b8115be8d61ca1f6cd47cdf7edaeda8628` (`repair5g: finish g556 fixed staticflow blind run`)
Round name: `Repair5G.5.57 graph-conditioned static-theta learning for goal-aware dual-channel LTM`

---

## 0. Executive decision

G5.57 should move beyond “one fixed global theta for every situation” while still staying much safer than dynamic learned UpdateLTM.

The new candidate object is:

```text
one static UpdateParams theta vector predicted once before a solver run
```

The theta is allowed to depend on:

```text
map graph topology
agent count and density
start distribution
goal distribution
start-goal flow priors
budget / horizon / ltm iteration budget
pre-run traffic priors
optional fixed-cost warm-up probe traffic map
```

The theta is not allowed to depend on:

```text
checkpoint index during the main run
runtime trace during the main run
candidate outcome labels
future solver result
per-iteration policy decisions
abstention decisions during the main run
```

Therefore the method is not a dynamic learned UpdateLTM policy. It is a **graph-conditioned static theta predictor**:

```text
(map graph, starts, goals, flow/traffic prior, run budget)
  -> bounded dual-channel UpdateParams theta
  -> fixed for the entire solver run
```

Recommended method name:

```text
GCST-LTM: Graph-Conditioned Static-Theta Lightweight Traffic Map
```

Recommended primary neural architecture name:

```text
TTGT: Topology-and-Traffic Graph Transformer
```

G5.57 should run two tracks:

```text
Track A: fixed-global continuation
  still search one universal theta against g556_c063174

Track B: graph-conditioned static theta
  predict one theta per map/instance/budget context
```

Track B is the main scientific target.

---

## 1. Why this route is stronger than G5.56

G5.56 made real progress, but its story is still narrow:

```text
offline Transformer/retrieval-assisted search found a better global constant theta.
```

G5.57 should tell a stronger learning-enhanced MAPF story:

```text
Different map topologies and traffic distributions require different LTM update dynamics.
A graph neural model reads map topology, start-goal flow pressure, and traffic priors,
then predicts bounded dual-channel UpdateParams before search begins.
LaCAM*/PIBT semantics stay unchanged.
The predicted theta is fixed for the whole solver run.
```

This is safer than dynamic runtime policy because it avoids per-checkpoint action logs, but it is much more learned than a single universal coefficient vector.

---

## 2. Literature anchors to audit before coding

G5.57 must include a real literature/code audit. Do not just cite names.

Required anchors:

### 2.1 Guidance graph / learned guidance in MAPF

1. **Guidance Graph Optimization for Lifelong MAPF**
   Paper: https://arxiv.org/abs/2402.01446
   Code from paper: https://github.com/lunjohnzhang/ggo_public
   Relevant lessons:
   - guidance can be represented as weighted directed edges;
   - guidance should be optimized through solver-facing simulation;
   - the update model can generate guidance for large maps and many agents;
   - this validates our “traffic/guidance generation through learning + replay” story.

2. **Online Guidance Graph Optimization for Lifelong MAPF**
   Paper: https://arxiv.org/abs/2411.16506
   Relevant lessons:
   - adaptive guidance from real-time traffic patterns is powerful;
   - dynamic guidance is harder and should be a later stage;
   - G5.57 deliberately uses pre-run/static theta to stay safer.

3. **Mixed Guidance Graph Optimization** if relevant and available
   Paper: https://arxiv.org/abs/2602.23468
   Relevant lesson:
   - edge directions and weights both matter for traffic guidance;
   - G5.57 should not change edge directions, but can include directionality/flow-orientation features.

### 2.2 Learning-based MAPF with graph / attention information

1. **LaGAT: Graph Attention-Guided Search for Dense MAPF**
   Paper: https://arxiv.org/abs/2510.17382
   Relevant lessons:
   - learned graph-attention guidance can help search when integrated carefully;
   - pretrain/fine-tune and deadlock/failure handling matter;
   - it is especially relevant because it integrates learned guidance into LaCAM.

2. **CS-PIBT / collision shield lesson**
   Paper: https://arxiv.org/abs/2409.14491
   Relevant lessons:
   - large supervised MAPF data alone is not enough;
   - strong shields / strong baselines matter;
   - in czr004, the shield is paired replay against g556_c063174 plus additive diagnostics.

3. **Learning-based MAPF survey**
   Paper: https://arxiv.org/abs/2505.19219
   Relevant lessons:
   - learning-based MAPF often evaluates smaller instances than classical MAPF;
   - G5.57 should deliberately scale maps, agent counts, seeds, and topology diversity.

### 2.3 Graph Transformer / scalable graph representation

1. **GraphGPS**
   Paper: https://arxiv.org/abs/2205.12454
   Relevant lessons:
   - combine local message passing with global attention;
   - use positional/structural encodings;
   - useful for grid/free-cell graphs.

2. **Exphormer**
   Paper/code: https://arxiv.org/abs/2303.06147 / https://github.com/hamed1375/Exphormer
   Relevant lessons:
   - sparse graph transformer with virtual global nodes and expander-style connections;
   - useful for scaling beyond tiny graphs.

3. Optional newer sparse graph transformer diagnostics if easy:
   - HopFormer / sparse n-hop attention;
   - SFi-Former / sparse flow-induced attention.

### 2.4 Benchmark diversity

1. **Quality Diversity MAPF benchmark-map generation**
   Paper: https://arxiv.org/abs/2409.06888
   Relevant lessons:
   - fixed hand-designed maps can bias MAPF evaluation;
   - generated/adversarial topology panels can expose failure modes;
   - G5.57 should include generated topology diagnostics, not only the original LTM map set.

Write:

```text
outputs/reports/phase5p5_repair5g557_literature_code_audit.md
outputs/reports/phase5p5_repair5g557_literature_code_audit_summary.json
outputs/tables/phase5p5_repair5g557_literature_method_matrix.csv
outputs/tables/phase5p5_repair5g557_available_external_code.csv
```

The audit must say which ideas are adopted, which are only inspirations, and which are not compatible with czr004 guardrails.

---

## 3. Current baseline and claim policy

Primary baseline for all promotion:

```text
g556_c063174
```

Previous fixed baselines for diagnostics:

```text
g554_c00051
old hand static_flow_shield / repair5g59_static_flow_shield
additive_ltm
```

G5.57 must not call itself:

```text
dynamic learned UpdateLTM policy
checkpoint policy
runtime trace policy
learned SafeGate
Phase5.5 ready
Phase6 ready
AAAI ready
```

Allowed narrow claim if blind passes:

```text
A graph-conditioned static-theta predictor proposes bounded dual-channel UpdateParams
once before a solver run, and the predicted static theta improves over g556_c063174
under paired solver replay while preserving LaCAM*/PIBT semantics.
```

All global claim flags stay closed unless a separate later governance round opens them:

```json
{
  "phase5p5_allowed": false,
  "phase6_allowed": false,
  "runtime_claim_allowed": false,
  "learned_runtime_policy_validated": false,
  "aaai_ready": false
}
```

---

## 4. Candidate object: graph-conditioned static theta

For each evaluation context, the model emits:

```text
theta_pred(context)
```

where `context` includes map graph and initial instance information.

Theta is fixed for the entire solver run:

```text
before main solver starts:
  compute theta_pred

main solver run:
  use theta_pred for every LTM update
  no switching
  no checkpoint-dependent changes
  no runtime trace-dependent changes
```

This makes the method halfway between:

```text
fixed global theta          # safest, weakest learning story

graph-conditioned theta     # G5.57 target

dynamic learned policy      # stronger story, harder safety
```

G5.57 target is the middle one.

---

## 5. Two legal traffic-map input modes

The user specifically wants traffic-map information included because traffic map is the central object. Use two legal modes.

### 5.1 Mode P — Pre-run traffic priors, no solver probe

This mode uses only information available before any solver call:

```text
map graph
starts
goals
agent count
budget/horizon
shortest-path flow prior
k-shortest-path or randomized-shortest-path flow prior if feasible
node/edge betweenness and bottleneck proxies
predicted start-goal OD pressure
```

It is the cleanest method and should be the primary paper-friendly version.

### 5.2 Mode W — Warm-up probe traffic, fixed after probe

This mode runs a fixed, deterministic, small-budget probe using baseline settings, then predicts theta once:

```text
run fixed warm-up probe with additive_ltm or g556_c063174 for a small bounded budget
export initial C/F traffic snapshot and trace aggregates
model predicts theta
restart main solver from scratch using theta fixed for the whole run
```

This is still not dynamic policy, but it has extra overhead and must be evaluated separately.

Warm-up constraints:

```text
probe budget must be fixed before experiments
probe method must not be tuned on blind
probe overhead must be reported
main solver must restart cleanly from scratch
probe trace cannot be from candidate theta
probe trace cannot include future labels
```

Recommended default:

```text
primary method = Mode P
secondary method = Mode W diagnostic
```

If Mode W wins, report both with and without overhead.

---

## 6. Label-v3: graph-conditioned static-theta labels

G5.57 should not train from final full-run hindsight alone without same-context counterfactual candidates.

Create **Label-v3**:

```text
same context + many candidate theta values + paired solver outcomes vs g556_c063174
```

Each training context has a slate:

```text
context_id
map_id / map_family / topology_id
agent_count
start-goal seed
budget/horizon
candidate_theta_1 outcome
candidate_theta_2 outcome
...
candidate_theta_K outcome
g556_c063174 baseline outcome
additive_ltm diagnostic outcome
old hand staticflow diagnostic outcome
```

Each candidate-context row must include:

```text
selected_success
baseline_success
success_regression_vs_g556_c063174
success_gain_vs_g556_c063174
both_success
quality_delta_vs_g556_c063174
quality_delta_vs_additive
candidate_recognized
fingerprint_match
cost_finite
theta_in_bounds
```

Do not use missing fields silently. Explicitly audit success field mapping as in G5.55.

### 6.1 Row-level labels

For model scoring and auxiliary outcome prediction:

```text
row_label_regression_risk = success_regression_vs_g556_c063174
row_label_success_gain    = success_gain_vs_g556_c063174
row_label_quality_delta   = quality_delta_vs_g556_c063174
row_label_additive_risk   = success_regression_vs_additive
row_label_materialized    = fingerprint_match & candidate_recognized & cost_finite & theta_in_bounds
```

### 6.2 Context-level oracle labels

For each context, derive a safe candidate set:

```text
safe(theta, context) =
  success_regression_vs_g556_c063174 == 0
  and candidate_recognized == true
  and fingerprint_match == 1
  and cost_finite == true
  and theta_in_bounds == true
```

Then compute:

```text
utility(theta, context) =
  - quality_delta_vs_g556_c063174
  + success_gain_bonus
  - regression_penalty
  - materialization_penalty
```

Recommended constants for labels only:

```text
success_gain_bonus = 0.05
regression_penalty = 10.0
materialization_penalty = 10.0
```

Context target forms:

```text
oracle_theta_id:
  best safe candidate by utility

oracle_topk_theta_ids:
  top 5 safe candidates by utility

soft_safe_utility_distribution:
  softmax over safe candidates with temperature 0.01 or tuned on val

oracle_theta_barycenter:
  weighted average of top safe theta vectors, after clipping to bounds

no_safe_improvement:
  true if no safe candidate improves quality over g556_c063174
```

If no safe candidate exists:

```text
label = ABSTAIN_TO_G556_C063174
```

This is not runtime abstention. It is the static-theta generator choosing to output the baseline theta.

### 6.3 Group-level labels to reduce noise

Per-context labels are noisy. Also construct group labels over:

```text
same map_id + agent_count + budget/horizon
same topology cluster + density bucket + flow-pressure bucket
same map_family + agent_count + budget/horizon
```

For each group, compute:

```text
group_safe_frontier
group_oracle_theta
group_oracle_topk
group_mean_quality_delta
group_regression_rate
group_support_count
```

Use group labels for pretraining and context labels for fine-tuning.

### 6.4 Forbidden label leakage

Forbidden model inputs:

```text
candidate outcome
baseline outcome
quality delta
success regression/gain
oracle theta label
post-hoc rank
candidate id as memorization feature
blind seed id
future replay labels
trace from candidate theta before theta is chosen
```

Allowed metadata:

```text
map graph features
start/goal distribution
agent count
budget/horizon
pre-run flow prior
fixed warm-up probe traffic in Mode W only
source split / source round for balancing, not as primary predictive feature
```

---

## 7. Dataset scale target

G5.56 was useful but not enough. G5.57 must be deliberately larger and more topologically diverse.

### 7.1 Minimum scale

```text
unique map/topology variants >= 60
unique heldout map/topology variants >= 15
unique context-horizons >= 20,000
unique base instances >= 10,000
primary row-level examples vs g556_c063174 >= 3,000,000
total usable row-level examples >= 5,000,000
unique theta candidates evaluated >= 20,000
unique candidate-context rows with same-context slates >= 3,000,000
```

### 7.2 Preferred scale

```text
unique map/topology variants >= 100
unique heldout map/topology variants >= 25
unique context-horizons >= 40,000
unique base instances >= 20,000
primary row-level examples vs g556_c063174 >= 6,000,000
total usable row-level examples >= 10,000,000
unique theta candidates evaluated >= 50,000
same-context candidate rows >= 6,000,000
```

### 7.3 Stop condition

Do not mark G5.57 as complete if the minimum scale is not met. Instead write:

```text
g557_dataset_underpowered_continue_topup
```

with exact missing counts and resume commands.

---

## 8. Map and instance coverage

The context bank must cover topology, not just map names.

### 8.1 Required topology families

Use all available project maps first. Then generate additional maps if necessary.

Required families:

```text
empty/open grids
random obstacle grids
maze/corridor maps
room maps
warehouse maps
narrow door / bottleneck maps
game / irregular maps if available
QD/generated topology diagnostics
adversarial corridor/room/warehouse variants
```

### 8.2 Agent counts

Use a scale ladder, adjusted by map free cells:

```text
small:   25, 50, 75, 100
medium:  150, 200, 300, 400
large:   600, 800, 1000
stress:  1500, 2000, 3000 where feasible
```

Do not force infeasible large counts onto small maps. Report free-cell ratio and density.

### 8.3 Start-goal distributions

For every map/topology, generate multiple start-goal regimes:

```text
uniform random
opposite-side / cross-flow
same-room local flow
room-to-room door bottleneck
warehouse aisle-to-aisle
many-to-one / goal-clustered
start-clustered / goal-dispersed
flow through central choke point
low-conflict easy distribution
high-conflict adversarial distribution
```

### 8.4 Budgets / horizons

Use multiple budgets and LTM iteration settings:

```text
base_time_limit_sec in {0.5, 1.0, 2.0}
nominal_budget_ms in {500, 1000, 2000, 5000}
short_budget_ms in {250, 500, 1000, 2000}
ltm_max_iterations in {2, 4, 8}
```

Do not mix all combinations blindly if solver cost explodes. Use stratified sampling with manifest counts.

---

## 9. Feature design: make the traffic-map story central

The model must not just get tabular `map_family` and `agents`. It must receive topology, traffic, and dual-channel information.

### 9.1 Graph node features

For each free cell / graph vertex:

```text
x_norm, y_norm
degree
is_dead_end
is_corridor_cell
is_room_interior
is_door_candidate
is_articulation_or_near_cut
biconnected_component_id_hash_or_embedding
local_obstacle_density_radius_1/2/4
corridor_width_proxy
distance_to_nearest_obstacle
static_betweenness_approx
shortest_path_distance_to_start_density_center
shortest_path_distance_to_goal_density_center
start_density
goal_density
start_goal_overlap_density
pre_run_node_flow_prior
pre_run_wait_pressure_proxy
optional_probe_c_channel_node_aggregate
optional_probe_f_channel_node_aggregate
```

### 9.2 Directed edge features

For each directed move edge:

```text
from_node_features
to_node_features
orientation one-hot
is_reverse_of_high_flow_edge
undirected_edge_betweenness_approx
shortest_path_flow_prior_on_directed_edge
opposing_flow_prior
flow_imbalance
edge_cut_or_bridge_proxy
corridor_axis_alignment
start_to_goal_progress_prior
potential_head_on_conflict_prior
optional_probe_c_raw
optional_probe_c_normalized
optional_probe_f_raw
optional_probe_f_normalized
optional_probe_blocked_count
optional_probe_committed_progress_count
optional_probe_wait_spillover_count
```

### 9.3 Agent / goal distribution features

Global and pooled features:

```text
agent_count
free_cells
density = agents/free_cells
start_entropy
goal_entropy
start_cluster_count
goal_cluster_count
mean_start_goal_shortest_path
std_start_goal_shortest_path
p90_start_goal_shortest_path
mean_pairwise_start_distance
mean_pairwise_goal_distance
start_goal_flow_concentration_top1/top5/top10_percent
fraction_paths_through_top_bottleneck_nodes
opposite_direction_flow_ratio
expected_edge_conflict_proxy
expected_vertex_conflict_proxy
```

### 9.4 Traffic-map features

Traffic map is the scientific center. Use two versions.

Pre-run traffic prior:

```text
C_prior(e): expected congestion from shortest-path / k-shortest-path flow
F_prior(e): expected goal-progress flow from starts to goals
shield_opportunity_prior(e): F_prior(e) * bottleneck/congestion context
```

Warm-up probe traffic, Mode W only:

```text
C_probe(e): congestion channel after fixed probe
F_probe(e): flow channel after fixed probe
blocked_probe(e)
wait_probe(e)
progress_probe(e)
rank_margin_probe(e)
cost_audit_probe
```

### 9.5 Theta features for scoring model

For candidate-scoring head:

```text
theta numeric fields
theta mode one-hot
distance from g556_c063174
distance from g554_c00051
distance from old hand staticflow
active field deltas
bounds-normalized theta
```

Do not use candidate ID as a normal feature. Candidate ID can be used only in a memorization ablation.

---

## 10. Model architecture

Main architecture:

```text
TTGT-GCST: Topology-and-Traffic Graph Transformer for Graph-Conditioned Static Theta
```

### 10.1 Encoders

```text
Graph encoder:
  GraphGPS/Exphormer-inspired sparse graph transformer
  local message passing over grid edges
  sparse/global attention via global map tokens and bottleneck tokens
  positional/structural encodings

Flow/traffic encoder:
  directed edge tokens for C_prior/F_prior and optional C_probe/F_probe
  cross-attention between traffic tokens and graph topology tokens

Agent-goal distribution encoder:
  start/goal density maps
  OD-flow summary tokens
  agent-count/density/budget tokens

Theta candidate encoder:
  theta scalar tokenization
  interaction attention over theta fields
```

### 10.2 Heads

Use two coupled heads.

#### Outcome scoring head

Input:

```text
context embedding + theta embedding
```

Output:

```text
p_success_regression_vs_g556_c063174
p_success_gain_vs_g556_c063174
expected_quality_delta_vs_g556_c063174
quality_delta_q10/q50/q90
materialization risk
uncertainty
```

This is used for ranking candidate theta values and generating hard negatives.

#### Static theta generator head

Input:

```text
context embedding only
```

Output:

```text
prototype distribution over theta codebook
bounded residual around selected prototype
fallback-to-g556 probability
predicted static theta vector
```

The generator should not output arbitrary unbounded theta. Use:

```text
codebook + bounded residual + clamp + fingerprint check
```

Recommended codebook:

```text
all known promoted/elites from G5.54-G5.56
stage1/stage2 safe candidates
C/F ablation candidates
trust-region samples around g556_c063174
learned prototypes from safe-frontier clustering
```

Residual bound default:

```text
max_abs_residual_per_field <= 0.15 * field_range
or tighter around g556 for first run
```

---

## 11. Training objectives

Use multi-task training. Do not rely on one hard oracle class.

### 11.1 Outcome-scoring losses

```text
weighted BCE for success regression risk
weighted BCE for success gain
Huber loss for quality delta
quantile pinball loss for q10/q50/q90
pairwise ranking loss within same context slate
Brier / calibration loss
false-safe hard-negative penalty
```

### 11.2 Generator losses

```text
KL / cross-entropy to soft safe-utility distribution
listwise ranking loss against candidate slate
residual regression to oracle_theta_barycenter
fallback loss for no_safe_improvement contexts
safety penalty if generated theta is predicted unsafe
smoothness regularization over similar topology contexts
```

### 11.3 Robustness losses

```text
group-DRO over map families
group-DRO over topology clusters
density-bucket reweighting
hard-negative oversampling
heldout-map calibration penalty
shuffled-label negative-control audit
```

---

## 12. Train / validation / test splits

Splits must prevent map and topology leakage.

Use four splits:

```text
train:
  seen maps, seen topology families, non-heldout seeds

validation:
  seen maps, heldout seed blocks, heldout candidate families

heldout-map-test:
  maps not used for training, same broad topology families

heldout-topology-test:
  topology families or generated maps not used for training

blind-execution:
  generated after model freeze; no labels visible before plan generation
```

At least 20% of map/topology variants must be held out.

Do not put the same generated map variant into both train and blind.

---

## 13. Required controls and ablations

A graph-conditioned predictor is only credible if it beats simpler lookup and tabular alternatives.

Required controls:

```text
C0 global baseline: g556_c063174
C1 previous fixed baseline: g554_c00051
C2 old hand staticflow
C3 additive_ltm
C4 map-family lookup static theta
C5 map-id lookup static theta, diagnostic only, cannot support generalization claim
C6 agent-count/density lookup theta
C7 tabular-only context model, no graph
C8 graph-only model, no start/goal distribution
C9 start-goal distribution model, no traffic prior
C10 graph + start/goal, no traffic prior
C11 graph + traffic prior, no start/goal labels
C12 warm-up probe model with overhead accounting
C13 shuffled-label graph model
C14 random-feature model
C15 GBDT / TabM controls on global/context summary features
C16 CMA-ES / CEM per-family optimizer diagnostic
```

A successful G5.57 graph-conditioned claim must beat:

```text
g556_c063174
map-family lookup
tabular-only summary model
shuffled/random controls
```

on heldout maps/topologies, not only on seen maps.

---

## 14. Gate policy: strict baseline plus optional noninferiority exploration

Keep two separate ledgers.

### 14.1 Strict safe promotion gate

This is the main baseline ladder gate:

```text
success_regression_count_vs_g556_c063174 = 0
success_rate_delta_vs_g556_c063174 >= 0
quality_delta_mean_vs_g556_c063174 <= -0.001
bootstrap_ci_upper <= 0
better_count > worse_count
fingerprint = 1
recognized = true
cost_finite = true
theta_in_bounds = true
```

Only strict candidates can replace the primary baseline.

### 14.2 Controlled-regression research ledger

Optionally report Pareto/noninferiority candidates separately:

```text
global success regression rate <= 0.05% or 0.1%
per topology-family regression rate <= 0.2%
noninferiority CI on success rate passes
quality improvement is materially larger than strict candidate
all regression cases audited
no regressions on critical stress panels
```

These candidates cannot become the safe baseline in G5.57. They are only research diagnostics.

---

## 15. Required scripts

Create the following scripts. Do not compress all logic into one giant common file only. Use common utilities, but each stage must have inspectable stage-specific code.

```text
czr004_g557_graph_conditioned_static_theta_aaai_plan.md

scripts/repair5g557_common.py
scripts/verify_repair5g557_g556_artifacts.py
scripts/create_repair5g557_literature_code_audit.py
scripts/create_repair5g557_context_bank.py
scripts/create_repair5g557_graph_feature_cache.py
scripts/create_repair5g557_traffic_prior_features.py
scripts/create_repair5g557_probe_traffic_plan.py
scripts/run_repair5g557_probe_traffic.py
scripts/analyze_repair5g557_probe_traffic.py
scripts/create_repair5g557_theta_candidate_slate.py
scripts/create_repair5g557_label_matrix_plan.py
scripts/run_repair5g557_theta_label_matrix.py
scripts/analyze_repair5g557_label_matrix.py
scripts/create_repair5g557_label_v3_dataset.py
scripts/train_eval_repair5g557_ttgt_outcome_model.py
scripts/train_eval_repair5g557_gcst_generator.py
scripts/train_eval_repair5g557_controls.py
scripts/analyze_repair5g557_model_ablation.py
scripts/generate_repair5g557_static_theta_policy.py
scripts/create_repair5g557_stage1_execution_plan.py
scripts/run_repair5g557_stage1_execution.py
scripts/analyze_repair5g557_stage1_execution.py
scripts/create_repair5g557_stage2_heldout_map_plan.py
scripts/run_repair5g557_stage2_heldout_map.py
scripts/analyze_repair5g557_stage2_heldout_map.py
scripts/create_repair5g557_blind_plan.py
scripts/run_repair5g557_blind.py
scripts/analyze_repair5g557_blind.py
scripts/write_repair5g557_decision.py
```

---

## 16. Stage A — Verify G5.56 baseline

Inputs:

```text
outputs/reports/phase5p5_repair5g556_decision_summary.json
outputs/reports/phase5p5_repair5g556_blind_summary.json
outputs/tables/phase5p5_repair5g556_final_candidate_theta.csv
```

Required checks:

```text
g556 decision = g556_transformer_fixed_global_candidate_blind_passed_keep_claims_closed
promoted_fixed_candidate_id = g556_c063174
blind_solver_rows = 360000
success_regression_count_vs_g554_c00051 = 0
quality_delta_vs_g554_c00051 = -0.0032705119799
fingerprint = 1
recognized = true
cost_finite = true
all claim flags closed
external_lacam2_clean = true
```

Write:

```text
outputs/reports/phase5p5_repair5g557_g556_verification.md
outputs/reports/phase5p5_repair5g557_g556_verification_summary.json
outputs/tables/phase5p5_repair5g557_g556_theta.csv
outputs/tables/phase5p5_repair5g557_claim_flag_audit.csv
```

Stop if baseline cannot be verified.

---

## 17. Stage B — Context bank and topology expansion

Create a context bank with explicit topology metadata.

Write:

```text
outputs/reports/phase5p5_repair5g557_context_bank.md
outputs/reports/phase5p5_repair5g557_context_bank_summary.json
outputs/tables/phase5p5_repair5g557_context_manifest.csv
outputs/tables/phase5p5_repair5g557_map_topology_manifest.csv
outputs/tables/phase5p5_repair5g557_start_goal_distribution_manifest.csv
outputs/tables/phase5p5_repair5g557_split_manifest.csv
```

Required counts:

```text
map/topology variants >= 60
context-horizons >= 20000
base instances >= 10000
heldout map/topology variants >= 15
start-goal distribution regimes >= 8
```

If maps are insufficient, generate topology variants under `outputs/tmp/phase5p5_repair5g557_generated_maps/` and commit only manifests/checksums.

---

## 18. Stage C — Graph feature cache

Compute graph, agent, goal, and traffic-prior features before replay.

Raw large feature stores:

```text
/root/shared-nvme/czr004_g557_remote_artifacts/features/node_features.parquet
/root/shared-nvme/czr004_g557_remote_artifacts/features/edge_features.parquet
/root/shared-nvme/czr004_g557_remote_artifacts/features/context_features.parquet
/root/shared-nvme/czr004_g557_remote_artifacts/features/traffic_prior_features.parquet
```

Committed summaries:

```text
outputs/reports/phase5p5_repair5g557_graph_feature_cache.md
outputs/reports/phase5p5_repair5g557_graph_feature_cache_summary.json
outputs/tables/phase5p5_repair5g557_graph_feature_manifest.csv
outputs/tables/phase5p5_repair5g557_feature_leakage_audit.csv
outputs/tables/phase5p5_repair5g557_feature_preview.csv
```

Feature leakage audit must state:

```text
no outcome fields
no candidate label fields
no blind labels
no candidate theta success fields
probe traffic separated from pre-run features
```

---

## 19. Stage D — Optional warm-up probe traffic

Run only if resources allow. This is Mode W.

Probe method options:

```text
g556_c063174 short deterministic probe
additive_ltm short deterministic probe
```

Recommended:

```text
probe_time_limit_sec <= 0.25 or <= 10% of main budget
probe_ltm_iterations <= 1 or 2
```

Write:

```text
outputs/reports/phase5p5_repair5g557_probe_traffic.md
outputs/reports/phase5p5_repair5g557_probe_traffic_summary.json
outputs/tables/phase5p5_repair5g557_probe_traffic_manifest.csv
outputs/tables/phase5p5_repair5g557_probe_overhead_audit.csv
```

The main result should still include Mode P without probe.

---

## 20. Stage E — Theta candidate slate for labels

Build a candidate slate broad enough to produce useful oracle labels.

Sources:

```text
g556_c063174 and neighborhood
g554_c00051 and neighborhood
old hand staticflow
additive and C-only diagnostics
G5.54/G5.55/G5.56 elite candidates
trust-region samples around g556_c063174
structured sweeps over C/F/shield/decay parameters
flow-shield beta/max-flow variants
wait-progress variants
map-topology-inspired heuristic candidates
CMA-ES/CEM candidates from small context subsets
random negative controls
```

Minimum:

```text
unique theta candidates in slate >= 20000
per-context candidate slate size >= 256
preferred per-context slate size >= 512
```

Write:

```text
outputs/reports/phase5p5_repair5g557_theta_candidate_slate.md
outputs/reports/phase5p5_repair5g557_theta_candidate_slate_summary.json
outputs/tables/phase5p5_repair5g557_theta_candidate_registry_preview.csv
outputs/tables/phase5p5_repair5g557_theta_family_breakdown.csv
```

---

## 21. Stage F — Label matrix replay

This is the expensive core stage. It creates Label-v3.

Minimum row plan:

```text
contexts_for_dense_label_matrix >= 8000
candidate_thetas_per_context >= 256
primary candidate-context rows >= 2,048,000
baseline g556 rows for all contexts
additive diagnostic rows for all contexts
old hand staticflow diagnostic rows for all contexts
```

Preferred row plan:

```text
contexts_for_dense_label_matrix >= 12000
candidate_thetas_per_context >= 512
primary candidate-context rows >= 6,144,000
```

Use balanced sampling over topology, agent density, and start-goal regimes.

Write:

```text
outputs/reports/phase5p5_repair5g557_label_matrix.md
outputs/reports/phase5p5_repair5g557_label_matrix_summary.json
outputs/tables/phase5p5_repair5g557_label_matrix_leaderboard.csv
outputs/tables/phase5p5_repair5g557_label_matrix_by_topology.csv
outputs/tables/phase5p5_repair5g557_label_matrix_failure_cases.csv
outputs/tables/phase5p5_repair5g557_success_field_mapping_audit.csv
```

Do not proceed to generator training unless:

```text
same-context candidate rows >= 3,000,000
contexts with at least one safe improving theta >= 1,000
feature leakage = false
success field audit = passed
```

If not met:

```text
g557_label_matrix_underpowered_continue_topup
```

---

## 22. Stage G — Label-v3 dataset construction

Build model-ready datasets:

```text
/root/shared-nvme/czr004_g557_remote_artifacts/datasets/label_v3_row_rows.parquet
/root/shared-nvme/czr004_g557_remote_artifacts/datasets/label_v3_context_oracle.parquet
/root/shared-nvme/czr004_g557_remote_artifacts/datasets/label_v3_group_oracle.parquet
/root/shared-nvme/czr004_g557_remote_artifacts/datasets/graph_cache_index.parquet
```

Committed outputs:

```text
outputs/reports/phase5p5_repair5g557_label_v3_dataset.md
outputs/reports/phase5p5_repair5g557_label_v3_dataset_summary.json
outputs/tables/phase5p5_repair5g557_label_v3_split_summary.csv
outputs/tables/phase5p5_repair5g557_label_v3_context_oracle_preview.csv
outputs/tables/phase5p5_repair5g557_label_v3_group_oracle_preview.csv
outputs/tables/phase5p5_repair5g557_label_v3_leakage_audit.csv
```

Report:

```text
safe-improvement context count
no-safe-improvement context count
oracle theta entropy
topology-family label coverage
agent-density label coverage
heldout-map label coverage
```

---

## 23. Stage H — Train TTGT outcome model

Train the context+theta outcome model.

Command target:

```bash
python scripts/train_eval_repair5g557_ttgt_outcome_model.py \
  --device cuda --gpus 2 --epochs 120 --batch-size auto \
  --mixed-precision --hard-negative-oversampling --group-dro
```

Minimum:

```text
epochs >= 80 unless early stopping after clear plateau
train rows >= 3,000,000
gpus visible >= 2, or write reason for single-GPU fallback
```

Write:

```text
outputs/reports/phase5p5_repair5g557_ttgt_outcome_eval.md
outputs/reports/phase5p5_repair5g557_ttgt_outcome_eval_summary.json
outputs/tables/phase5p5_repair5g557_ttgt_outcome_metrics.csv
outputs/tables/phase5p5_repair5g557_ttgt_outcome_calibration.csv
outputs/tables/phase5p5_repair5g557_ttgt_outcome_by_topology.csv
outputs/tables/phase5p5_repair5g557_ttgt_false_safe_cases.csv
artifacts/models/laur_ltm/repair5g557_ttgt_outcome_manifest.json
```

Outcome model audit:

```text
false_safe_hard_negative_count reported
quality ranking correlation reported
heldout-map degradation reported
heldout-topology degradation reported
negative controls fail
```

Failure of this audit does not automatically block solver replay, but it blocks learned-SafeGate claims.

---

## 24. Stage I — Train GCST static theta generator

Train generator using context-only inputs.

Command target:

```bash
python scripts/train_eval_repair5g557_gcst_generator.py \
  --device cuda --gpus 2 --epochs 150 --batch-size auto \
  --mode pre_run --codebook-residual --group-dro
```

Train both:

```text
GCST-P: pre-run graph/start-goal/traffic-prior only
GCST-W: warm-up probe traffic, if probe data exists
```

Write:

```text
outputs/reports/phase5p5_repair5g557_gcst_generator_eval.md
outputs/reports/phase5p5_repair5g557_gcst_generator_eval_summary.json
outputs/tables/phase5p5_repair5g557_gcst_generator_metrics.csv
outputs/tables/phase5p5_repair5g557_gcst_generator_by_topology.csv
outputs/tables/phase5p5_repair5g557_gcst_generator_oracle_gap.csv
outputs/tables/phase5p5_repair5g557_gcst_generated_theta_preview.csv
artifacts/models/laur_ltm/repair5g557_gcst_generator_manifest.json
```

Offline generator audit:

```text
safe-improvement recall
unsafe-selection rate
oracle regret
fallback-to-g556 rate
heldout-map performance
heldout-topology performance
comparison to tabular-only control
comparison to map-family lookup
```

---

## 25. Stage J — Controls and ablations

Run controls listed in Section 13.

Write:

```text
outputs/reports/phase5p5_repair5g557_controls_and_ablations.md
outputs/reports/phase5p5_repair5g557_controls_and_ablations_summary.json
outputs/tables/phase5p5_repair5g557_control_metrics.csv
outputs/tables/phase5p5_repair5g557_ablation_metrics.csv
outputs/tables/phase5p5_repair5g557_negative_control_metrics.csv
```

If GCST does not beat simple map-family or tabular controls offline, still allow solver preflight, but label the result as exploratory.

---

## 26. Stage K — Freeze graph-conditioned static theta policy

Generate a policy-as-executed table before any fresh solver replay.

This table is critical.

For each context:

```text
context_id
map_id
map_family
topology_id
agent_count
budget/horizon
model_version
input_mode P or W
predicted_theta fields
theta_hash
fallback_to_g556 flag
materialization_precheck
```

Write:

```text
outputs/reports/phase5p5_repair5g557_static_theta_policy_freeze.md
outputs/reports/phase5p5_repair5g557_static_theta_policy_freeze_summary.json
outputs/tables/phase5p5_repair5g557_policy_as_executed_preview.csv
outputs/tables/phase5p5_repair5g557_policy_theta_distribution.csv
outputs/tables/phase5p5_repair5g557_policy_materialization_audit.csv
```

After this file is generated:

```text
no tuning
no threshold changes
no candidate edits
no extra filtering
```

unless a new plan and new blind split are created.

---

## 27. Stage L — Stage1 execution preflight

Run frozen graph-conditioned static theta on fresh contexts.

Minimum:

```text
Stage1 solver rows >= 600,000
preferred >= 1,000,000
contexts >= 10,000
include g556_c063174 baseline for every context
include additive diagnostic subset
include old hand staticflow diagnostic subset
include tabular-only control subset
include map-family lookup control subset
```

Stage1 gate for Stage2:

```text
success_regression_count_vs_g556_c063174 <= 5
success_rate_delta_vs_g556_c063174 >= 0
quality_delta_mean_vs_g556_c063174 <= -0.001
regression cases audited
materialization pass
```

Do not promote from Stage1.

Write:

```text
outputs/reports/phase5p5_repair5g557_stage1_execution.md
outputs/reports/phase5p5_repair5g557_stage1_execution_summary.json
outputs/tables/phase5p5_repair5g557_stage1_by_topology.csv
outputs/tables/phase5p5_repair5g557_stage1_by_agent_density.csv
outputs/tables/phase5p5_repair5g557_stage1_failure_cases.csv
outputs/tables/phase5p5_repair5g557_stage1_vs_controls.csv
```

---

## 28. Stage M — Stage2 heldout-map and heldout-topology validation

Stage2 must focus on generalization, not seen-map performance.

Minimum:

```text
Stage2 solver rows >= 600,000
preferred >= 1,200,000
heldout map/topology variants >= 15
heldout contexts >= 8,000
```

Stage2 strict pass:

```text
success_regression_count_vs_g556_c063174 = 0
success_rate_delta_vs_g556_c063174 >= 0
quality_delta_mean_vs_g556_c063174 <= -0.001
bootstrap_ci_upper <= 0
better_count > worse_count
no topology-family catastrophic regression
materialization/fingerprint pass
```

Write:

```text
outputs/reports/phase5p5_repair5g557_stage2_heldout_map.md
outputs/reports/phase5p5_repair5g557_stage2_heldout_map_summary.json
outputs/tables/phase5p5_repair5g557_stage2_by_topology.csv
outputs/tables/phase5p5_repair5g557_stage2_by_map.csv
outputs/tables/phase5p5_repair5g557_stage2_vs_controls.csv
outputs/tables/phase5p5_repair5g557_stage2_failure_cases.csv
```

If strict pass fails but controlled-regression ledger looks promising, report it separately and do not promote.

---

## 29. Stage N — Blind replay

Only run if Stage2 strict pass is clean.

Blind plan must be generated after model freeze and Stage2 decision.

Minimum:

```text
blind solver rows >= 720,000
preferred >= 1,200,000
blind contexts >= 12,000
blind map/topology variants >= 20
fresh seeds
no tuning after blind plan
```

Blind strict pass:

```text
success_regression_count_vs_g556_c063174 = 0
success_rate_delta_vs_g556_c063174 >= 0
quality_delta_mean_vs_g556_c063174 <= -0.001
bootstrap_ci_upper <= 0
better_count > worse_count
fingerprint = 1
recognized = true
cost_finite = true
theta_in_bounds = true
beats tabular-only and map-family controls on heldout topology aggregate
```

Write:

```text
outputs/reports/phase5p5_repair5g557_blind.md
outputs/reports/phase5p5_repair5g557_blind_summary.json
outputs/tables/phase5p5_repair5g557_blind_by_topology.csv
outputs/tables/phase5p5_repair5g557_blind_by_map.csv
outputs/tables/phase5p5_repair5g557_blind_vs_controls.csv
outputs/tables/phase5p5_repair5g557_blind_failure_cases.csv
outputs/tables/phase5p5_repair5g557_final_policy_theta_sample.csv
```

---

## 30. Stage O — Decision

Write:

```text
outputs/reports/phase5p5_repair5g557_decision.md
outputs/reports/phase5p5_repair5g557_decision_summary.json
outputs/tables/phase5p5_repair5g557_claim_ledger.csv
outputs/tables/phase5p5_repair5g557_large_artifact_manifest.csv
outputs/tables/phase5p5_repair5g557_final_method_comparison.csv
```

Decision labels:

```text
g557_g556_baseline_not_verified_stop
g557_context_bank_underpowered_continue
g557_label_matrix_underpowered_continue_topup
g557_gcst_offline_not_better_than_controls_exploratory_only
g557_stage1_regressed_stop
g557_stage2_heldout_failed_keep_g556
g557_blind_failed_keep_g556
g557_gcst_strict_blind_passed_keep_claims_closed
g557_controlled_regression_candidate_only_not_promoted
```

Final summary keys:

```json
{
  "decision": "...",
  "primary_baseline": "g556_c063174",
  "method": "GCST-LTM",
  "model_family": "TTGT",
  "candidate_object": "one graph-conditioned static theta predicted before solver run",
  "dynamic_policy": false,
  "checkpoint_policy": false,
  "traffic_input_mode": "P or W",
  "context_horizons": 0,
  "primary_row_level_examples_vs_g556": 0,
  "total_row_level_examples": 0,
  "stage1_solver_rows": 0,
  "stage2_solver_rows": 0,
  "blind_solver_rows": 0,
  "strict_blind_passed": false,
  "success_regressions_vs_g556": 0,
  "quality_delta_vs_g556": "",
  "beats_map_family_lookup": false,
  "beats_tabular_only_control": false,
  "phase5p5_allowed": false,
  "phase6_allowed": false,
  "runtime_claim_allowed": false,
  "learned_runtime_policy_validated": false,
  "aaai_ready": false
}
```

---

## 31. Remote storage and compute

Use shared NVMe:

```bash
export REMOTE_ARTIFACT_ROOT=/root/shared-nvme/czr004_g557_remote_artifacts
export TMPDIR=/root/shared-nvme/tmp
mkdir -p "$REMOTE_ARTIFACT_ROOT" "$TMPDIR"
```

Large files go under:

```text
/root/shared-nvme/czr004_g557_remote_artifacts/features/
/root/shared-nvme/czr004_g557_remote_artifacts/datasets/
/root/shared-nvme/czr004_g557_remote_artifacts/solver_results/
/root/shared-nvme/czr004_g557_remote_artifacts/model_checkpoints/
/root/shared-nvme/czr004_g557_remote_artifacts/tmp/
```

Do not commit raw CSV/parquet/checkpoints larger than 50MB.

Use 2x4090 for model training:

```text
mixed precision
DDP if stable
single-GPU fallback only with written reason
gradient accumulation
checkpoint every epoch
resume-safe training
```

---

## 32. Recommended server command sequence

```bash
export REMOTE_ARTIFACT_ROOT=/root/shared-nvme/czr004_g557_remote_artifacts
export TMPDIR=/root/shared-nvme/tmp
mkdir -p "$REMOTE_ARTIFACT_ROOT" "$TMPDIR"

git status --short --branch
python -m py_compile scripts/repair5g557_common.py

python scripts/verify_repair5g557_g556_artifacts.py
python scripts/create_repair5g557_literature_code_audit.py
python scripts/create_repair5g557_context_bank.py --min-contexts 20000 --min-topologies 60
python scripts/create_repair5g557_graph_feature_cache.py
python scripts/create_repair5g557_traffic_prior_features.py

# Optional but recommended secondary track.
python scripts/create_repair5g557_probe_traffic_plan.py
python scripts/run_repair5g557_probe_traffic.py --max-workers 24
python scripts/analyze_repair5g557_probe_traffic.py

python scripts/create_repair5g557_theta_candidate_slate.py --min-candidates 20000
python scripts/create_repair5g557_label_matrix_plan.py --contexts 12000 --candidates-per-context 512
python scripts/run_repair5g557_theta_label_matrix.py --max-workers 24
python scripts/analyze_repair5g557_label_matrix.py
python scripts/create_repair5g557_label_v3_dataset.py

python scripts/train_eval_repair5g557_ttgt_outcome_model.py --device cuda --gpus 2 --epochs 120 --mixed-precision
python scripts/train_eval_repair5g557_gcst_generator.py --device cuda --gpus 2 --epochs 150 --mode pre_run --codebook-residual
python scripts/train_eval_repair5g557_controls.py
python scripts/analyze_repair5g557_model_ablation.py

python scripts/generate_repair5g557_static_theta_policy.py --freeze
python scripts/create_repair5g557_stage1_execution_plan.py
python scripts/run_repair5g557_stage1_execution.py --max-workers 24
python scripts/analyze_repair5g557_stage1_execution.py

python scripts/create_repair5g557_stage2_heldout_map_plan.py
python scripts/run_repair5g557_stage2_heldout_map.py --max-workers 24
python scripts/analyze_repair5g557_stage2_heldout_map.py

python scripts/create_repair5g557_blind_plan.py
python scripts/run_repair5g557_blind.py --max-workers 24
python scripts/analyze_repair5g557_blind.py
python scripts/write_repair5g557_decision.py
```

---

## 33. Required validation before push

```bash
python -m py_compile \
  scripts/repair5g557_common.py \
  scripts/verify_repair5g557_g556_artifacts.py \
  scripts/create_repair5g557_literature_code_audit.py \
  scripts/create_repair5g557_context_bank.py \
  scripts/create_repair5g557_graph_feature_cache.py \
  scripts/create_repair5g557_traffic_prior_features.py \
  scripts/create_repair5g557_theta_candidate_slate.py \
  scripts/create_repair5g557_label_matrix_plan.py \
  scripts/run_repair5g557_theta_label_matrix.py \
  scripts/analyze_repair5g557_label_matrix.py \
  scripts/create_repair5g557_label_v3_dataset.py \
  scripts/train_eval_repair5g557_ttgt_outcome_model.py \
  scripts/train_eval_repair5g557_gcst_generator.py \
  scripts/train_eval_repair5g557_controls.py \
  scripts/generate_repair5g557_static_theta_policy.py \
  scripts/analyze_repair5g557_model_ablation.py \
  scripts/write_repair5g557_decision.py

python - <<'PY'
import json, glob
for p in glob.glob('outputs/reports/phase5p5_repair5g557_*summary.json'):
    with open(p, 'r', encoding='utf-8') as f:
        json.load(f)
print('json summaries parse')
PY

git diff --check
git status --short -- external/lacam2/lacam2
```

Also run a secret scan over newly staged text files before push.

---

## 34. Interpretation guide

### If strict blind passes

Claim only:

```text
Graph-conditioned static theta prediction improves over g556_c063174 under paired replay.
The model predicts bounded dual-channel UpdateParams once before each solver run.
LaCAM*/PIBT semantics are unchanged.
```

Do not claim:

```text
dynamic learned UpdateLTM policy
checkpoint-level policy
AAAI-ready final method
```

### If only controlled-regression candidate passes

Report it as:

```text
Pareto/noninferiority diagnostic, not safe baseline promotion.
```

### If GCST fails but fixed-global Track A improves

Promote only the fixed-global baseline if strict blind passes, and document that graph-conditioned static prediction failed to generalize.

### If all fail

This is still valuable:

```text
g556_c063174 may be near the safe fixed/static frontier;
future gains may require dynamic learned UpdateLTM with checkpoint-level labels.
```

---

## 35. Short Codex prompt

Continue `czr004` after G5.56 commit `d090d7b8115be8d61ca1f6cd47cdf7edaeda8628` on branch `codex/g531-slice-pilot`. Implement G5.57: AAAI-scale Graph-Conditioned StaticTheta for goal-aware dual-channel LTM.

Primary baseline is `g556_c063174`, not `g554_c00051` and not old hand staticflow. The main method is `GCST-LTM`: a graph-conditioned static-theta predictor. It reads map graph topology, agent count/density, start/goal distributions, start-goal flow priors, budget/horizon, and traffic-map priors, then predicts one bounded dual-channel `UpdateParams` theta before the solver run. The theta remains fixed for the entire solver run. It must not depend on checkpoint, runtime trace during the main run, future outcomes, or per-iteration policy decisions.

Main model family: `TTGT`, a Topology-and-Traffic Graph Transformer inspired by GraphGPS/Exphormer and learning-guided MAPF work. It should encode map/free-cell graph topology, node/edge bottleneck features, start/goal density, OD flow, pre-run C/F traffic priors, and optional fixed warm-up probe traffic. Use codebook + bounded residual output, not unconstrained theta generation.

Build Label-v3: same-context candidate-theta slates with paired solver outcomes versus `g556_c063174`. Labels must include row-level success regression/gain and quality delta, plus context-level safe-oracle theta distributions and group-level safe-frontier labels. Do not use outcome fields as features. If no safe improving theta exists for a context, label fallback to `g556_c063174`.

Dataset minimum: at least 60 map/topology variants, 20,000 context-horizons, 10,000 base instances, 3M primary row-level examples versus `g556_c063174`, 5M total usable rows, 20k unique theta candidates, and at least 3M same-context candidate rows. Preferred scale is larger. If insufficient, write `g557_dataset_underpowered_continue_topup` with exact resume commands, not a completed success.

Required topology coverage: open grids, random, maze/corridor, room, warehouse, bottleneck/door, irregular/game maps if available, and generated/QD/adversarial topology diagnostics. Required start-goal regimes: uniform, opposite-side, room-to-room, bottleneck, warehouse aisle, clustered goals, clustered starts, central choke, easy/low-conflict and adversarial/high-conflict.

Run controls: global `g556_c063174`, `g554_c00051`, old hand staticflow, additive, map-family lookup theta, map-id lookup diagnostic, agent-density lookup, tabular-only model, graph-only/no-goal, no-traffic, graph+goal no-traffic, warm-up probe, shuffled-label, random-feature, GBDT/TabM, and CEM/CMA-ES diagnostics. GCST must beat map-family lookup and tabular-only controls on heldout maps/topologies before a learned-method interpretation.

Promotion requires real paired solver replay, not offline predictions. Stage1 minimum 600k solver rows, Stage2 heldout-map/topology minimum 600k rows, blind minimum 720k rows. Strict safe promotion requires zero success regressions vs `g556_c063174`, non-worse success rate, negative quality delta with CI upper <= 0, better_count>worse_count, fingerprint=1, recognized=true, finite cost, and theta bounds. Optional controlled-regression candidates may be reported separately but cannot replace the safe baseline.

Do not edit `external/lacam2/lacam2/**`. Do not change LaCAM*/PIBT/search semantics. Do not use reserved IDs 166..205. Store large data/checkpoints/results under `/root/shared-nvme/czr004_g557_remote_artifacts` and `/root/shared-nvme/tmp`. Commit only compact summaries, manifests, small previews, and code. Keep Phase5.5, Phase6, runtime, learned-runtime, and AAAI claims closed.

<!-- G5.57_FINAL_RESULT_BEGIN -->
## 2026-06-19 - G5.57 final result: graph-conditioned static theta

Final decision: `g557_gcst_offline_not_better_than_controls_exploratory_only`. GCST-LTM is not promoted as a new baseline; keep g556_c063174 as the active promotion baseline.

Baseline/SafeGate: the declared promotion baseline is `g556_c063174`. Offline prediction, candidate ranking, learned-SafeGate scores, and proxy labels do not promote GCST. Promotion requires real paired solver replay against `g556_c063174` with the strict zero-success-regression gate.

Scale and replay evidence:

- context horizons: `20,000`
- primary row-level examples vs g556: `6,144,000`
- total usable row-level examples: `6,180,000`
- same-context candidate rows: `6,144,000`
- Stage1 / Stage2 / blind solver rows: `0` / `0` / `0`
- success regressions vs g556: `0`
- quality delta vs g556: `n/a`; CI upper `n/a`
- better/worse quality pairs vs g556: `0` / `0`

Closed-claim policy remains unchanged: `phase5p5_allowed=false`, `phase6_allowed=false`, `runtime_claim_allowed=false`, `learned_runtime_policy_validated=false`, and `aaai_ready=false`.

Local final-artifact audit status: `true` with `0` failed checks.
<!-- G5.57_FINAL_RESULT_END -->
