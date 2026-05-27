# Phase4F Repair2: Advanced Update-Rule Network Plan

**File name:** `phase4f_repair2_advanced_update_rule_network_plan.md`  
**Target branch:** `phase4-laur-ltm`  
**Primary goal:** keep the LAU/LAUR-LTM direction, but replace the checkpoint-level MLP with a stronger neural architecture that predicts **which LTM update rule / update parameter family should be used**.  
**Do not change direction. Do not lower the Phase4F performance gate. Do not enter Phase5 learned runtime yet.**

---

## 0. Current evidence and decision

### 0.1 Current repository state to assume

Use the GitHub branch:

```text
https://github.com/czr5454112-glitch/czr004/tree/phase4-laur-ltm
```

Current Phase4B–4F chain is already implemented:

```text
Phase4B: parameterized UpdateLTM API
Phase4C: iteration checkpoints + raw trace export
Phase4D: update-rule probe labels
Phase4E: LAU update dataset builder
Phase4F: LAU-MLP-v1 training/eval full run
Phase4F repair1: larger data + soft-label/safety repair
```

Do not revert any of the above.

### 0.2 Repair1 result summary

`full_repair1` was operationally successful but did **not** pass Phase4F performance gate.

Observed repair1 validation metrics:

```text
validation rule top1       = 0.3072   < 0.35  fail
validation rule top3       = 0.6427   < 0.70  fail
harmful recall             = 0.9538   >= 0.80 pass
harmful precision          = 0.4015   >= 0.30 pass
predicted-rule mean delta  = 0.0110   > 0.0  pass
validation non-neutral     = 359      >= 50   pass
```

Repair1 therefore fixed much of the safety problem, but exact rule selection is still not strong enough.

### 0.3 Current model problem

The current model is `LAU-MLP-v1`.

Its effective learning problem is:

```text
aggregate checkpoint features -> one best update rule
```

This is likely too weak for LAUR because choosing an LTM update rule depends on:

```text
W_t: current traffic-map state
H_t: current iteration trace events
local bottlenecks / corridors / blocked regions
which candidate update rule is being evaluated
rule-family structure: additive / commit / block / wait / decay
near-ties between rules in short-budget probes
```

A single aggregate MLP loses most of this structure.

### 0.4 Repair2 decision

Repair2 must **not** continue by only tuning the same MLP.

Repair2 must implement advanced models whose output is still LAUR-compatible:

```text
input:
  checkpoint context + traffic-map tokens + trace/event tokens + candidate update-rule tokens

output:
  score for each candidate update rule
  harmful probability for each candidate update rule
  optional expected delta_ratio for each rule

selected update:
  safety-gated argmax over candidate update-rule scores
```

This is inspired by graph-attention guidance work such as LaGAT, but it must remain LAUR:

```text
Do not predict agent actions.
Do not replace PIBT.
Do not change LaCAM*/PIBT legality.
Do not change high-level LaCAM* search.
Do not implement learned restart in this repair.
Only predict traffic-map update rule / update parameters.
```

---

## 1. Non-negotiable constraints

### 1.1 Direction constraints

Repair2 must stay on this path:

```text
LaCAM* + LTM
  -> learned adaptive LTM update rule
  -> update-rule prediction from checkpoint/trace/traffic context
```

Do **not** switch to:

```text
agent-level neural MAPF policy
LaGAT clone
end-to-end learned planner
learned PIBT replacement
learned collision resolver
generic GNN MAPF solver
pure edge-weight regression
Phase5 runtime integration
```

### 1.2 Gate constraints

Do not lower the gate.

Repair2 still must target:

```text
validation top1 >= 0.35
validation top3 >= 0.70
harmful recall >= 0.80
harmful precision >= 0.30
predicted-rule mean delta > 0.0
validation non-neutral checkpoints >= 50
```

Add diagnostic metrics, but do not use diagnostics to weaken the main gate.

### 1.3 Safety constraints

The learned model must remain fallback-safe:

```text
if harmful_prob(rule) is high:
    do not select that rule

if model confidence is low:
    select additive_ltm

if data/schema is missing:
    select additive_ltm

if candidate rule is absent from exported rule table:
    select additive_ltm
```

### 1.4 Runtime boundary

Repair2 is still **offline Phase4F**.

Do not integrate the learned model into C++ solver runtime yet.

Allowed:

```text
dataset features
advanced PyTorch models
training/evaluation scripts
offline reports
model checkpoint/export for later inspection
```

Not allowed in this stage:

```text
cpp/ntm learned runtime
changing solve_with_ltm behavior
calling neural model inside LaCAM*
Phase5 closed-loop learned runtime
```

---

## 2. Repair2 high-level strategy

Repair2 should be implemented in this order:

```text
R2-A. Clean executable rule target
R2-B. Build token/rule-aware dataset
R2-C. Implement LAU-EdgeTraceTransformer-v2 as the primary advanced model
R2-D. Implement LAU-SetTransformer-v2 as a lighter fallback advanced model
R2-E. Optional: implement topology-biased attention, not full PyG
R2-F. Train/evaluate locally on existing repair1 artifacts
R2-G. Run full_repair2 only after local evidence beats repair1
R2-H. Write report and decide whether Phase4F gate is passed
```

The priority is not "make a bigger MLP."  
The priority is to change the architecture and objective to:

```text
Q(checkpoint, update_rule)
```

instead of:

```text
checkpoint -> hard best-rule class
```

---

## 3. R2-A: Clean executable update-rule target

### 3.1 Why this is mandatory

Current labels/rule vocabulary still include both:

```text
additive_ltm
neutral_additive
```

But both correspond to the same executable additive fallback behavior:

```text
alpha_commit = 1.0
alpha_block  = 1.0
alpha_wait   = 1.0
rho_decay    = 1.0
force_additive = true
```

This creates a label/action mismatch.

Repair2 must separate:

```text
executable update rule
```

from:

```text
neutral / fallback semantic flag
```

### 3.2 Required target representation

Each training sample must keep both original and cleaned targets:

```json
{
  "best_rule_original": "neutral_additive",
  "best_rule_executable": "additive_ltm",
  "is_neutral_label": true,
  "is_non_neutral_label": false,
  "harmful_update": false
}
```

Executable rule vocabulary:

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

`neutral_additive` is not an executable rule class.

It may remain as:

```text
neutral_flag
fallback_reason
original_label_for_audit
```

### 3.3 Required metrics after cleanup

Evaluation must report both:

```text
raw_original_top1/top3
executable_top1/top3
family_top1/top3
```

But the main gate should be evaluated on the cleaned executable rule vocabulary.

Do not count a model as passing just because a diagnostic improved; it still must satisfy the Phase4F thresholds.

### 3.4 Files to update

Expected files:

```text
src/czr004_teacher/update_sequences.py
src/czr004_teacher/features_laur.py
src/eval/eval_laur_offline.py
src/train/train_laur_ltm.py
tests/test_phase4_laur_schema.py
```

Add tests:

```text
test_neutral_additive_maps_to_additive_executable()
test_original_label_is_preserved_for_audit()
test_executable_rule_vocab_has_no_neutral_duplicate()
test_eval_reports_raw_and_executable_metrics()
```

---

## 4. R2-B: Build token/rule-aware dataset

### 4.1 Why the current dataset is insufficient

The current `aggregate_checkpoint_v1` dataset produces one numeric feature vector per checkpoint.

That is acceptable for MLP smoke, but not enough for a stronger network.

Repair2 needs structured inputs:

```text
global checkpoint token
traffic edge tokens from W_t
trace/event tokens from H_t
candidate update-rule tokens
probe outcome vector for supervision
```

### 4.2 New schema

Add a schema version:

```text
phase4_laur_update_dataset_v2
```

Keep v1 compatibility, but training advanced models should use v2.

Each v2 row should contain:

```json
{
  "schema_version": "phase4_laur_update_dataset_v2",
  "run_id": "...",
  "checkpoint_id": "...",
  "split": "train",
  "map_name": "...",
  "agents": 100,
  "iteration": 2,

  "global_features": [...],

  "edge_tokens": [
    {
      "edge_id": "...",
      "from_id": 123,
      "to_id": 124,
      "direction": 1,
      "raw_before": 3.0,
      "weight_before": 6.0,
      "raw_after_additive": 4.0,
      "blocked_count": 2,
      "committed_count": 1,
      "wait_spillover_count": 0,
      "local_degree": 3,
      "is_topk_raw": true,
      "is_topk_delta": true
    }
  ],

  "trace_tokens": [
    {
      "bucket_id": 0,
      "kind": "blocked",
      "edge_id": "...",
      "count": 4,
      "is_wait": false,
      "at_goal_count": 0,
      "event_index_min": 0,
      "event_index_max": 25
    }
  ],

  "rule_tokens": [
    {
      "rule_id": "block_heavy",
      "rule_family": "block",
      "alpha_commit": 1.0,
      "alpha_block": 1.5,
      "alpha_wait": 1.0,
      "rho_decay": 1.0,
      "force_additive": false
    }
  ],

  "rule_delta_vector": {
    "additive_ltm": 0.0,
    "commit_heavy": 0.003,
    "block_heavy": 0.011,
    "block_light": -0.002,
    "wait_light": 0.006,
    "wait_heavy": -0.004,
    "decay_095": 0.001,
    "decay_090": 0.002
  },

  "rule_harmful_vector": {
    "additive_ltm": false,
    "commit_heavy": false,
    "block_heavy": false,
    "block_light": true,
    "wait_light": false,
    "wait_heavy": true,
    "decay_095": false,
    "decay_090": false
  },

  "best_rule_executable": "block_heavy",
  "best_rule_original": "block_heavy",
  "soft_rule_target": [...]
}
```

### 4.3 Token sources

Use existing Phase4C–4F artifacts.

Preferred source order:

```text
1. checkpoints JSONL
2. traffic snapshots / top-k traffic maps
3. probe JSONL
4. update_labels dataset
5. raw trace zst, if available locally/server-side
```

If raw trace zst is unavailable locally, do not block the first implementation.  
Fall back to:

```text
edge tokens from traffic snapshots
trace summary tokens from checkpoint aggregate counts
probe vectors from probe JSONL
```

Then add raw trace tokenization as a later enhancement.

### 4.4 Token budget

Default token limits:

```text
max_edge_tokens = 128
max_trace_tokens = 256
max_rule_tokens = 8
```

For smoke:

```text
max_edge_tokens = 32
max_trace_tokens = 64
```

For memory control:

```text
truncate by edge importance:
  high blocked_count
  high raw_before
  high topk_raw_delta
  high wait_spillover_count
  high local bottleneck proxy
```

### 4.5 Files to create

```text
src/czr004_teacher/token_features_laur.py
src/czr004_teacher/token_dataset_laur.py
tests/test_phase4_laur_token_dataset.py
```

### 4.6 Token dataset tests

Add tests:

```text
test_token_dataset_preserves_checkpoint_count()
test_token_dataset_has_rule_delta_vector_for_each_rule()
test_token_dataset_no_map_name_in_model_features()
test_token_dataset_no_split_in_model_features()
test_token_dataset_handles_missing_raw_trace()
test_token_dataset_padding_mask_shapes()
test_token_dataset_neutral_additive_cleaned()
```

---

## 5. R2-C: Primary model — LAU-EdgeTraceTransformer-v2

### 5.1 Model purpose

This is the main Repair2 architecture.

It predicts:

```text
Q(checkpoint, rule)
P_harmful(checkpoint, rule)
```

for each candidate update rule.

It does **not** predict agent action.  
It does **not** replace PIBT.  
It does **not** predict final LTM edge weights.

### 5.2 Architecture overview

```text
global_features
    -> global token encoder

edge_tokens
    -> edge token encoder
    -> type embedding + numeric projection + optional direction embedding

trace_tokens
    -> trace token encoder
    -> event kind embedding + count/numeric projection

rule_tokens
    -> rule token encoder
    -> rule family embedding + update-param numeric projection

context tokens = [global token, edge tokens, trace tokens]

Transformer encoder over context tokens

Rule-conditioned cross-attention:
    query = rule tokens
    key/value = context tokens

Rule-token self-attention:
    lets candidate rules compare against each other

Heads:
    q_delta_head(rule_token) -> expected delta_ratio score
    harmful_head(rule_token) -> harmful probability
    optional family_head(rule_token) -> family auxiliary logits
```

### 5.3 Pseudocode

```python
class LAUEdgeTraceTransformerV2(nn.Module):
    def __init__(self, d_model=128, n_heads=4, n_layers=2):
        self.global_encoder = NumericEncoder(...)
        self.edge_encoder = EdgeTokenEncoder(...)
        self.trace_encoder = TraceTokenEncoder(...)
        self.rule_encoder = RuleTokenEncoder(...)

        self.context_encoder = nn.TransformerEncoder(...)
        self.rule_cross_attn = nn.MultiheadAttention(...)
        self.rule_self_attn = nn.TransformerEncoder(...)

        self.q_head = nn.Linear(d_model, 1)
        self.harmful_head = nn.Linear(d_model, 1)
        self.family_head = nn.Linear(d_model, num_families)

    def forward(batch):
        g = encode_global(batch.global_features)
        e = encode_edges(batch.edge_tokens)
        t = encode_trace(batch.trace_tokens)
        r = encode_rules(batch.rule_tokens)

        context = concat([g, e, t])
        context = context_encoder(context, key_padding_mask=context_mask)

        r2 = cross_attention(query=r, key=context, value=context)
        r2 = rule_self_attention(r2)

        q_delta = q_head(r2).squeeze(-1)
        harmful_logit = harmful_head(r2).squeeze(-1)

        return {
          "rule_score": q_delta,
          "harmful_logit": harmful_logit,
          "family_logits": family_head(r2)
        }
```

### 5.4 Why this model is appropriate

This is the closest LAUR-compatible way to borrow the idea behind graph-attention guidance:

```text
LaGAT-style idea:
  attention helps reason over interacting agents/local graph structure

LAUR adaptation:
  attention reasons over traffic edges, trace events, and update rules

Output remains:
  which LTM update rule to use
```

This keeps the project within LTM + learning-enhanced traffic map.

### 5.5 Files to create

```text
src/models/laur_rule_attention.py
src/train/train_laur_rule_attention.py
src/train/losses_laur_rule_attention.py
src/eval/eval_laur_rule_attention.py
configs/phase4/laur_ltm_full_repair2_attention.yaml
tests/test_laur_rule_attention_model.py
```

### 5.6 Do not remove old MLP files

Keep old MLP code for baseline comparison:

```text
src/models/laur_ltm.py
src/train/train_laur_ltm.py
src/eval/eval_laur_offline.py
```

But Repair2 should not use MLP-v1 as the main model.

---

## 6. R2-D: Backup advanced model — LAU-SetTransformer-v2

### 6.1 Motivation

If EdgeTraceTransformer is too heavy or raw trace tokens are hard to build, implement a lighter non-MLP advanced model:

```text
LAU-SetTransformer-v2
```

It uses attention over sets of traffic-edge tokens and rule tokens, without explicit raw trace sequence.

This is still not a plain MLP.

### 6.2 Inputs

```text
global token
top-K traffic edge tokens
top-K additive delta edge tokens
rule tokens
```

No raw trace tokens required.

### 6.3 Architecture

```text
edge token encoder
Set Transformer / Transformer encoder over edge tokens
pooling by multihead attention
rule-conditioned cross-attention
q_delta_head per rule
harmful_head per rule
```

### 6.4 When to use

Use this if:

```text
raw trace zst is unavailable
trace tokenization is too slow
EdgeTraceTransformer overfits
GPU memory is too high
```

### 6.5 Required comparison

Repair2 report must compare:

```text
MLP-v1 repair1 baseline
LAU-SetTransformer-v2
LAU-EdgeTraceTransformer-v2
```

If EdgeTraceTransformer fails but SetTransformer passes the gate, SetTransformer can become the Repair2 main model.

---

## 7. R2-E: Optional topology-biased attention

### 7.1 Motivation

Plain attention sees edge tokens as a set.  
Traffic map edges live on a graph.

Instead of adding PyG as a hard dependency, implement topology bias inside attention:

```text
bias(i, j) =
  +b_shared_vertex if edge_i and edge_j share a vertex
  +b_reverse_edge if edge_i is reverse of edge_j
  +b_same_direction_corridor if directions align locally
  +b_nearby if endpoint distance <= 2
```

This gives a GAT-like inductive bias while staying pure PyTorch.

### 7.2 Optional model name

```text
LAU-TopoEdgeAttention-v2
```

### 7.3 Do not make PyG mandatory

Allowed:

```text
pure PyTorch attention bias
networkx preprocessing
top-k sparse adjacency masks
```

Avoid making PyTorch Geometric a Phase4F hard dependency.

---

## 8. Loss functions

### 8.1 Required objective change

Do not train the new model as only a hard classifier.

Use probe outcomes directly.

The model predicts:

```text
score[rule] = predicted expected delta_ratio
harmful_logit[rule] = harmful probability
```

### 8.2 Loss components

Use:

```text
L =
  lambda_listwise * listwise_kl_loss(score, soft_rule_target)
+ lambda_pairwise * pairwise_margin_ranking_loss(score, rule_delta_vector)
+ lambda_delta    * smooth_l1(score, rule_delta_vector)
+ lambda_safe     * per_rule_harmful_bce(harmful_logit, rule_harmful_vector)
+ lambda_family   * family_auxiliary_loss
+ lambda_additive * additive_fallback_regularization
```

### 8.3 Listwise KL

Create soft targets from probe deltas:

```python
soft_rule_target = softmax(rule_delta_vector / temperature)
```

Default:

```text
temperature = 0.005 or 0.01
```

### 8.4 Pairwise margin ranking

For each pair `(i, j)`:

```text
if delta_i - delta_j >= margin:
    score_i should be greater than score_j
```

Default:

```text
pairwise_margin_delta = 0.0025
```

This avoids forcing the model to rank near-tied rules.

### 8.5 Per-rule harmful safety

The safety head should be per rule, not only per checkpoint:

```text
P_harmful(checkpoint, rule)
```

At inference/eval:

```python
allowed_rules = [r for r in rules if harmful_prob[r] < harmful_threshold]
if no allowed_rules:
    choose additive_ltm
else:
    choose argmax score among allowed rules
```

### 8.6 Family auxiliary loss

Map rules to families:

```text
additive_ltm -> additive
commit_heavy -> commit
block_heavy/block_light -> block
wait_heavy/wait_light -> wait
decay_095/decay_090 -> decay
```

Train:

```text
family of best executable rule
```

This gives the model an easier intermediate structure.

Do not replace rule-level gate with family-level gate; family metrics are diagnostic/auxiliary.

---

## 9. Evaluation metrics

### 9.1 Required metrics

Report at least:

```text
rule_top1_accuracy
rule_top3_accuracy
executable_rule_top1_accuracy
executable_rule_top3_accuracy
family_top1_accuracy
family_top3_accuracy
harmful_update_recall
harmful_update_precision
harmful_update_f1
safety_auroc
predicted_rule_validation_mean_delta_ratio
safety_gated_predicted_mean_delta_ratio
oracle_top1_delta
oracle_top3_delta
additive_baseline_delta
per_map_metrics
per_rule_confusion
```

### 9.2 Required comparisons

Compare against:

```text
repair1 LAU-MLP-v1
repair2 SetTransformer-v2
repair2 EdgeTraceTransformer-v2
repair2 TopoEdgeAttention-v2, if implemented
```

### 9.3 Gate

Phase4F gate still requires:

```text
validation rule top1 >= 0.35
validation rule top3 >= 0.70
harmful recall >= 0.80
harmful precision >= 0.30
predicted-rule mean delta > 0.0
validation non-neutral checkpoints >= 50
```

Do not advance to Phase5 if this gate fails.

### 9.4 Repair2 improvement target

Even before gate, the report must show whether Repair2 improves over repair1:

```text
repair1 top1 = 0.3072
repair1 top3 = 0.6427
repair1 harmful recall = 0.9538
repair1 predicted mean delta = 0.0110
```

Repair2 should aim to exceed repair1 on:

```text
top1
top3
predicted mean delta
```

while keeping:

```text
harmful recall >= 0.80
harmful precision >= 0.30
```

---

## 10. Config design

Create:

```text
configs/phase4/laur_ltm_full_repair2_attention.yaml
```

Suggested content:

```yaml
mode: phase4-full-repair2-attention

data:
  base_artifact_mode: full_repair1
  checkpoint_jsonl: artifacts/teacher/laur/full_repair1/checkpoints/phase4_laur_checkpoints_full_repair1.jsonl
  probe_jsonl: artifacts/teacher/laur/full_repair1/probes/phase4_laur_probe_full_repair1.jsonl
  update_dataset_jsonl: artifacts/teacher/laur/full_repair1/update_labels/phase4_laur_update_dataset_full_repair1.jsonl
  raw_trace_zst: artifacts/teacher/laur/full_repair1/traces/phase4_laur_trace_full_repair1.jsonl.zst
  raw_trace_required: false
  output_token_dataset_jsonl: artifacts/teacher/laur/full_repair2/update_labels/phase4_laur_update_dataset_full_repair2_tokens.jsonl

target_cleanup:
  collapse_neutral_additive: true
  executable_rule_vocab:
    - additive_ltm
    - commit_heavy
    - block_heavy
    - block_light
    - wait_light
    - wait_heavy
    - decay_095
    - decay_090

tokens:
  max_edge_tokens: 128
  max_trace_tokens: 256
  max_rule_tokens: 8
  edge_token_source:
    - traffic_snapshots
    - checkpoint_topk
    - raw_trace_if_available
  trace_token_source:
    - raw_trace_if_available
    - checkpoint_counts_fallback

model:
  name: LAU-EdgeTraceTransformer-v2
  d_model: 128
  n_heads: 4
  n_context_layers: 2
  n_rule_layers: 1
  dropout: 0.10
  use_topology_bias: false
  use_family_head: true
  use_per_rule_safety: true

loss:
  listwise_kl_weight: 1.0
  pairwise_ranking_weight: 1.0
  delta_regression_weight: 0.25
  safety_bce_weight: 2.0
  family_aux_weight: 0.3
  additive_regularization_weight: 0.05
  soft_target_temperature: 0.005
  pairwise_delta_margin: 0.0025

train:
  batch_size: 64
  epochs: 250
  lr: 0.0008
  weight_decay: 0.0005
  early_stopping_metric: validation_rule_top3_accuracy
  patience: 40
  seed: 1

eval:
  harmful_threshold_grid: [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]
  default_harmful_threshold: 0.10
  report_per_map: true
  report_confusion: true
  report_executable_metrics: true
  report_family_metrics: true
```

For local smoke, create:

```text
configs/phase4/laur_ltm_repair2_attention_smoke.yaml
```

with smaller token limits and fewer epochs.

---

## 11. Suggested command chain

### 11.1 Start-of-work commands

Codex must begin with:

```bash
git status --short
git branch --show-current
```

Do not touch untracked `1.txt`.

Append to:

```text
docs/codex-worklog.md
```

before coding.

### 11.2 Build token dataset

```bash
python -m src.czr004_teacher.token_dataset_laur \
  --config configs/phase4/laur_ltm_full_repair2_attention.yaml \
  --output artifacts/teacher/laur/full_repair2/update_labels/phase4_laur_update_dataset_full_repair2_tokens.jsonl \
  --summary outputs/reports/phase4f_repair2_token_dataset_summary.json
```

### 11.3 Run tests

```bash
pytest -q tests/test_phase4_laur_schema.py tests/test_phase4_laur_token_dataset.py tests/test_laur_rule_attention_model.py
```

### 11.4 Train SetTransformer smoke

```bash
python -m src.train.train_laur_rule_attention \
  --config configs/phase4/laur_ltm_repair2_attention_smoke.yaml \
  --model-name LAU-SetTransformer-v2 \
  --dataset artifacts/teacher/laur/full_repair2/update_labels/phase4_laur_update_dataset_full_repair2_tokens.jsonl \
  --output-dir artifacts/models/laur_ltm/full_repair2_set_transformer_smoke \
  --report outputs/reports/phase4f_repair2_set_transformer_smoke_train.md
```

### 11.5 Evaluate SetTransformer smoke

```bash
python -m src.eval.eval_laur_rule_attention \
  --config configs/phase4/laur_ltm_repair2_attention_smoke.yaml \
  --dataset artifacts/teacher/laur/full_repair2/update_labels/phase4_laur_update_dataset_full_repair2_tokens.jsonl \
  --model artifacts/models/laur_ltm/full_repair2_set_transformer_smoke/model.pt \
  --report outputs/reports/phase4f_repair2_set_transformer_smoke_eval.md \
  --summary-json outputs/reports/phase4f_repair2_set_transformer_smoke_eval_summary.json
```

### 11.6 Train EdgeTraceTransformer full repair2 offline

Only run after smoke passes.

```bash
python -m src.train.train_laur_rule_attention \
  --config configs/phase4/laur_ltm_full_repair2_attention.yaml \
  --model-name LAU-EdgeTraceTransformer-v2 \
  --dataset artifacts/teacher/laur/full_repair2/update_labels/phase4_laur_update_dataset_full_repair2_tokens.jsonl \
  --output-dir artifacts/models/laur_ltm/full_repair2_edge_trace_transformer \
  --report outputs/reports/phase4f_repair2_edge_trace_transformer_train.md
```

### 11.7 Evaluate EdgeTraceTransformer

```bash
python -m src.eval.eval_laur_rule_attention \
  --config configs/phase4/laur_ltm_full_repair2_attention.yaml \
  --dataset artifacts/teacher/laur/full_repair2/update_labels/phase4_laur_update_dataset_full_repair2_tokens.jsonl \
  --model artifacts/models/laur_ltm/full_repair2_edge_trace_transformer/model.pt \
  --report outputs/reports/phase4f_repair2_edge_trace_transformer_eval.md \
  --summary-json outputs/reports/phase4f_repair2_edge_trace_transformer_eval_summary.json
```

### 11.8 Final Repair2 report

Write:

```text
outputs/reports/phase4f_repair2_advanced_update_rule_network_report.md
```

It must include:

```text
commit
branch
dirty status
artifact paths
dataset count
token stats
model parameter count
train/eval command
repair1 comparison
gate table
per-map metrics
confusion matrix
decision: pass/fail Phase4F
```

---

## 12. Implementation details for the advanced model

### 12.1 Batch format

Batch tensors:

```text
global_features:      [B, G]
edge_tokens:          [B, E, Fe]
edge_mask:            [B, E]     true for valid tokens
trace_tokens:         [B, T, Ft]
trace_mask:           [B, T]
rule_tokens:          [B, R, Fr]
rule_mask:            [B, R]

rule_delta_targets:   [B, R]
rule_harmful_targets: [B, R]
soft_rule_targets:    [B, R]
best_rule_index:      [B]
best_family_index:    [B]
```

### 12.2 Rule selection at eval time

```python
score = model.rule_score
harmful_prob = sigmoid(model.harmful_logit)

allowed = harmful_prob < threshold
if not any(allowed):
    selected = additive_ltm
else:
    selected = argmax(score over allowed rules)
```

For top-k metrics:

```text
top-k should rank rules by safety-gated score
```

Also report ungated top-k for diagnostics.

### 12.3 Additive fallback handling

`additive_ltm` must always be present.

If `additive_ltm` is missing from a row:

```text
schema error
```

If a model predicts unknown rule:

```text
fallback additive_ltm
record warning in eval summary
```

### 12.4 Exports

For Phase4F offline:

```text
model.pt
model_config.json
feature_stats.json
rule_vocab.json
token_schema.json
train_summary.json
```

Do not force JSON-only MLP export for attention models.

If later Phase5 requires runtime, decide separately between:

```text
TorchScript
ONNX
Python service wrapper
C++ lightweight attention implementation
```

Do not solve Phase5 runtime export in Repair2.

---

## 13. What not to do

Do not:

```text
lower top1/top3 gate
enter Phase5 runtime after safety passes only
replace update-rule prediction with agent action prediction
add learned restart
change C++ LTM update behavior
delete old MLP baseline
commit large raw trace files
make PyG a hard dependency
claim LAUR improves LTM before closed-loop Phase5/6
```

Do not call a result successful if it only improves:

```text
training accuracy
edge-weight MAE
family accuracy
executable diagnostic accuracy
```

The main Phase4F gate must be satisfied.

---

## 14. Decision tree after Repair2

### Case A: EdgeTraceTransformer passes gate

If:

```text
top1 >= 0.35
top3 >= 0.70
harmful recall >= 0.80
harmful precision >= 0.30
predicted mean delta > 0
```

then write:

```text
Phase4F advanced model gate passed.
Phase5 runtime can be planned next, but not implemented in the same commit.
```

### Case B: SetTransformer passes but EdgeTraceTransformer fails

Use SetTransformer as the current Phase4F model.  
Document that raw trace tokens were not necessary or were noisy.

### Case C: Both improve over repair1 but do not pass

Remain in Phase4F.

Next likely action:

```text
improve probe labels
increase map-family balance
try topology-biased attention
try sequence-of-checkpoints model
```

Do not proceed to Phase5.

### Case D: Advanced models do not improve over repair1

Document negative result:

```text
Advanced architecture did not solve rule selection.
Failure likely comes from label/probe ambiguity rather than model capacity.
```

Then consider:

```text
longer probe budget
better update-rule set
continuous update parameters
more stable label target
```

Still do not proceed to Phase5.

---

## 15. Why this is still LAUR-LTM

This Repair2 plan keeps the scientific claim narrow:

```text
Learn how to update the Lightweight Traffic Map from LaCAM*/PIBT trace history.
```

The advanced network is only a better model for:

```text
P(update rule | traffic map state, PIBT trace, solver context)
```

It does not alter:

```text
candidate action set
vertex conflict logic
edge swap conflict logic
priority inheritance
LaCAM* high-level search
LTM fallback behavior
```

The final paper story remains:

```text
LAUR-LTM learns adaptive traffic-map update dynamics.
```

not:

```text
We replaced LaCAM*/PIBT with a neural MAPF policy.
```

---

## 16. Minimum acceptance for the Codex implementation commit

A single Repair2 implementation commit should include at least:

```text
docs/codex-worklog.md update

src/czr004_teacher/token_features_laur.py
src/czr004_teacher/token_dataset_laur.py

src/models/laur_rule_attention.py
src/train/train_laur_rule_attention.py
src/train/losses_laur_rule_attention.py
src/eval/eval_laur_rule_attention.py

configs/phase4/laur_ltm_repair2_attention_smoke.yaml
configs/phase4/laur_ltm_full_repair2_attention.yaml

tests/test_phase4_laur_token_dataset.py
tests/test_laur_rule_attention_model.py

outputs/reports/phase4f_repair2_advanced_update_rule_network_report.md
```

The report must state whether the gate passed or failed.

---

## 17. Suggested commit messages

Implementation commit:

```text
model: add LAUR rule-conditioned attention network
```

Dataset/token commit:

```text
data: add LAUR token dataset for update-rule attention
```

Experiment evidence commit:

```text
results: add Phase4F repair2 attention evidence
```
