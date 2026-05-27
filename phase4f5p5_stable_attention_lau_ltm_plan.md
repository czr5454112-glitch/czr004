# Phase4F/Phase5.5 Stable-Target Attention Plan for LAU-LTM

**Document purpose:** Codex-executable plan for replacing the current MLP-only learned update model with a stronger, LaGAT-inspired but LAUR-compatible neural architecture.

**Target project:** `czr004`  
**Target branch:** `phase4-laur-ltm`  
**Recommended working branch:** `phase4f5p5-stable-attention-lau` branched from the latest `origin/phase4-laur-ltm`  
**Current upstream state assumed:** Phase5C closed-loop smoke has completed on `phase4-laur-ltm`, but the learned MLP runtime has not shown solver-level benefit over ordinary LTM.

---

## 0. Core decision

We are **not changing direction**.

The method remains:

```text
LaCAM* + LTM
  -> learned adaptive LTM update rule
  -> LAU-LTM / LAUR-LTM
```

The learning target remains:

```text
predict the LTM update rule / update parameters
```

The learning target must **not** become:

```text
predict agent actions
replace PIBT
replace LaCAM*
fit final LTM edge weights
learn a restart policy before learned update is stable
```

The new model should borrow the useful idea from LaGAT-style graph attention: use attention to represent dense multi-agent interaction and traffic structure. However, unlike LaGAT, the model here must output **traffic-map update-rule decisions**, not one-step agent policies.

The correct slogan for this repair route is:

```text
LaGAT-inspired attention for LAUR update-rule selection,
not LaGAT-style agent policy replacement.
```

---

## 1. Why this plan exists

### 1.1 What has already worked

The repository has already completed the following LAUR/LAU chain:

```text
Phase4B: parameterized UpdateLTM API
Phase4C: iteration-level checkpoints + raw trace export
Phase4D: short-budget update-rule probes
Phase4E: update-rule training dataset builder
Phase4F: MLP training/eval pipeline
Repair1: larger data + better safety calibration
Repair2: initial advanced attention attempt, but before stable target
Repair3: stable target formulation, MLP passes local offline gate
Phase5A/B: runtime skeleton + force-additive parity
Phase5C: closed-loop runtime smoke / ablation / TTFS logging
```

### 1.2 What has not worked yet

Phase5C shows that the learned MLP runtime can be exercised in the solver and preserve success on a small smoke set, but it does **not** yet beat ordinary LTM in ratio or expanded-node checks.

The strongest current offline candidate is still a **stable-target MLP**. This is useful as a safe engineering baseline, but it is unlikely to be the final scientific model.

### 1.3 Why the earlier advanced model result should not be treated as final

The previous Repair2 attention attempt failed the Phase4F gate, but it was run before fully adopting the Repair3 stable-target framing as the central target formulation. The later Repair3 evidence showed that many update-rule probe labels are near-tied; therefore, the earlier advanced models were probably learning an unstable target.

This plan therefore says:

```text
Do not reuse the old Repair2 attention result as the final verdict.
Redo advanced models using Repair3 stable targets.
```

---

## 2. Hard constraints

Codex must obey these constraints.

### 2.1 No direction change

Allowed:

```text
learned update rule
stable target / tie-aware labels
rule-conditioned attention
Set Transformer
EdgeTrace Transformer
Perceiver-style token bottleneck
attention over traffic-map edges and trace events
safety-gated fallback to additive LTM
```

Not allowed:

```text
agent action prediction as the main method
MAGAT / LaGAT agent policy replacement
learned restart before learned update is stable
pure edge-weight regression as the main story
new unrelated MAPF solver baseline
changing PIBT candidate domain
changing conflict semantics
removing legal moves
```

### 2.2 No lowering gates

Keep the current Phase4F offline gates:

```text
validation top1 >= 0.35
validation top3 >= 0.70
harmful recall >= 0.80
harmful precision >= 0.30
mean selected delta > 0.0
validation non-neutral checkpoints >= 50
```

For advanced models, add stricter promotion gates in Section 10.

### 2.3 No Phase5 advanced runtime until offline gate passes

Do **not** integrate the advanced model into C++ runtime until the advanced model passes offline gate using the stable-target formulation.

### 2.4 Preserve existing Phase5C MLP runtime as a baseline

Do not delete or break the current MLP runtime path. It is the engineering baseline for parity/fallback and closed-loop comparison.

The new advanced route should be additive:

```text
MLP runtime path remains available.
Advanced model path is added as Phase5.5.
```

### 2.5 Large files policy

Do not commit large raw trace files. If raw trace `.zst` is needed, use local/server paths and write sha256 + local archive manifest. Commit only:

```text
configs
scripts
code
small summaries
reports
metrics CSV/JSON summaries
model artifacts only if small enough
```

---

## 3. Current facts Codex must verify before coding

Start every session with:

```powershell
git status --short
git branch --show-current
git rev-parse --short HEAD
git log --oneline -8
```

Expected branch:

```text
phase4-laur-ltm
```

Known local caveat from user:

```text
untracked 1.txt may exist; do not touch it.
```

Codex must inspect these files before starting:

```text
phase4_6_laur_ltm_codex_execution_plan.md
outputs/reports/phase4f_repair3_stable_target_report.md
outputs/reports/phase5c_laur_closed_loop_smoke_report.md
outputs/reports/phase5c_laur_metrics_replay.md
src/models/laur_ltm.py
src/models/laur_rule_attention.py
src/czr004_teacher/token_dataset_laur.py
src/czr004_teacher/token_features_laur.py
src/train/train_laur_rule_attention.py
src/eval/eval_laur_rule_attention.py
cpp/ntm/laur_ltm_runtime.cpp
cpp/tools/phase1a_batch.cpp
```

The first worklog entry for this route must be appended before code:

```markdown
## YYYY-MM-DD HH:MM - Start Phase4F/5.5 stable-target attention LAU

- Request: Redo advanced LAU update-rule model using Repair3 stable target formulation, then integrate only if offline gate passes.
- Branch:
- Base commit:
- Files planned:
- Key constraints: predict update rules only; do not predict agent actions; do not modify PIBT or LaCAM* semantics; do not lower gates; do not break MLP runtime baseline.
- Follow-up:
```

---

## 4. Naming

Use the following names consistently.

### 4.1 Offline model family

```text
LAU-StableAttention-v1
```

This is the umbrella name for stable-target advanced models.

### 4.2 Primary model

```text
LAU-SetRuleTransformer-v1
```

A lightweight Set Transformer / rule-conditioned attention model over:

```text
global checkpoint token
top-K traffic edge tokens
candidate update-rule tokens
```

This is the primary model because it is much easier to export to C++ than a full raw-trace transformer.

### 4.3 Secondary model

```text
LAU-EdgeTraceTransformer-v3
```

A richer model over:

```text
global checkpoint token
top-K traffic edge tokens
compressed trace/event tokens
candidate update-rule tokens
```

This model can be used for offline evidence and may enter Phase5.5 only if its runtime export is tractable.

### 4.4 Optional model

```text
LAU-TopoBiasAttention-v1
```

A topology-biased attention variant that adds sparse attention biases between edge tokens:

```text
shared endpoint
reverse edge
same corridor direction
nearby endpoint distance <= 2
```

No PyTorch Geometric dependency should be introduced as a hard requirement.

---

## 5. Phase4F.4-A: Stable-target audit and dataset compatibility

### Goal

Ensure the advanced model uses Repair3 stable targets, not the old hard best-rule target.

### Files to inspect and likely modify

```text
src/czr004_teacher/update_sequences.py
src/czr004_teacher/token_dataset_laur.py
src/czr004_teacher/token_features_laur.py
tests/test_phase4_laur_schema.py
configs/phase4/laur_ltm_full_repair3_stable_attention.yaml
outputs/reports/phase4f_repair4_stable_attention_dataset_report.md
```

### Required dataset behavior

The dataset must expose both original probe labels and stable labels:

```json
{
  "target": {
    "rule_class_original": "...",
    "rule_class_stable": "...",
    "rule_class_executable": "...",
    "is_neutral_label": false,
    "best_minus_second_margin": 0.0,
    "best_minus_additive_margin": 0.0,
    "rule_delta_vector": [...],
    "rule_harmful_vector": [...],
    "soft_rule_target_stable": [...],
    "soft_rule_target_probe": [...]
  }
}
```

Use `rule_class_stable` as the main target. Keep `rule_class_original` only for audit.

### Executable rule vocabulary

For runtime decisions, use executable rules:

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

`neutral_additive` is allowed as a **semantic stable target** during audit, but it must map to executable `additive_ltm` for rule execution.

### Tests

Add or update tests:

```text
test_stable_target_fields_present
test_original_and_stable_targets_preserved
test_neutral_additive_executes_as_additive_ltm
test_executable_rule_vocab_has_8_rules
test_soft_targets_sum_to_one
test_rule_delta_vector_order_matches_rule_vocab
```

### Gate

Pass if:

```text
schema validation passes
rule vocab is stable and ordered
stable target rows match Repair3 report counts if rebuilt from same artifacts
no raw trace committed
```

---

## 6. Phase4F.4-B: Token dataset v3

### Goal

Build a richer token dataset that gives the model enough structure to learn traffic update rules.

The previous MLP used aggregate checkpoint features. That loses spatial and trace structure. The new model must see tokenized traffic state.

### New / modified files

```text
src/czr004_teacher/stable_attention_dataset_laur.py
src/czr004_teacher/stable_attention_tokens_laur.py
src/czr004_teacher/topology_features_laur.py
tests/test_phase4f_stable_attention_dataset.py
configs/phase4/laur_ltm_full_repair4_stable_attention.yaml
outputs/reports/phase4f_repair4_stable_attention_dataset_report.md
```

### Sample structure

Each sample corresponds to one checkpoint.

```text
sample = checkpoint t
input = W_t + H_t + topology + solver context + candidate update rules
output = stable target + per-rule probe outcome vectors
```

### Global token

One global token per checkpoint:

```text
agents
density
map_width
map_height
obstacle_ratio
iteration
has_incumbent_before_update
best_ratio_before_update
ratio_this_iteration
improved_this_iteration
returned_solutions_count_so_far
time_to_first_solution_ms_or_minus1
committed_count
blocked_count
wait_event_count
goal_wait_ignored_count
blocked_per_committed
wait_per_committed
traffic_before_nonzero_edges
traffic_before_max_raw
traffic_before_entropy
traffic_after_additive_estimated_entropy
```

Keep `map_name`, `split`, absolute file path, and run-specific IDs out of model features.

### Edge tokens

Use top-K directed edge tokens. Recommended default:

```yaml
tokenization:
  max_edge_tokens: 64
  edge_selection:
    - top raw_count before update
    - top blocked_count on edge
    - top committed_count on edge
    - top additive_delta_abs
    - top wait_spillover_count
```

Each edge token contains:

```text
from_id, to_id hashed or omitted from numeric model features
from_x_norm, from_y_norm, to_x_norm, to_y_norm
direction_onehot or direction_embedding
from_degree, to_degree
is_reverse_of_top_edge
raw_before
normalized_before
committed_count_on_edge
blocked_count_on_edge
wait_spillover_count_on_edge
blocked_minus_committed
blocked_per_committed_edge
additive_delta_raw
would_decay_095_delta
would_decay_090_delta
local_corridor_score
local_intersection_score
local_obstacle_boundary_score
```

### Trace/event tokens

Two levels are allowed.

#### Level 1: compressed trace tokens

Use this first because it is stable and cheap:

```text
one token per edge-event aggregate in checkpoint H_t
```

Fields:

```text
edge index within top-K or -1
kind: committed / blocked
is_wait
at_goal
count
first_event_index_bucket
last_event_index_bucket
agent_count_unique_on_edge
```

#### Level 2: raw event sequence tokens

Use only if local evidence shows Level 1 is insufficient.

Recommended constraints:

```yaml
tokenization:
  max_trace_tokens: 128
  trace_event_selection:
    - blocked events first
    - wait events second
    - committed events on top-K edges third
    - deterministic order by event_index
```

Do not load multi-GB raw trace into memory at once. Stream `.jsonl.zst` if used.

### Rule tokens

There is one token for each executable rule.

Rule-token numeric fields:

```text
alpha_commit
alpha_block
alpha_wait
rho_decay
saturation_scale
contraflow_penalty
is_additive
is_commit_rule
is_block_rule
is_wait_rule
is_decay_rule
rule_family_id embedding
```

### Topology bias inputs

Optional but recommended for later:

```text
edge_i shares endpoint with edge_j
edge_i is reverse of edge_j
edge_i and edge_j lie in same direction locally
endpoint graph distance <= 2
```

These can become attention bias masks.

### Dataset output files

```text
artifacts/teacher/laur/full_repair4_stable_attention/update_labels/phase4_laur_stable_attention_dataset.jsonl
outputs/reports/phase4f_repair4_stable_attention_dataset_summary.json
outputs/tables/phase4f_repair4_stable_attention_dataset_summary.csv
```

Do not commit the full dataset if it is large. Commit summaries and small fixtures only.

### Gate

Pass if:

```text
dataset builder runs on existing Repair3 artifacts
dataset schema validation errors = 0
rule vocab count = 8 executable rules
all token masks have correct shapes
no NaN / inf features
top-K token truncation rates are reported
split leakage errors = 0
small fixture tests pass
```

---

## 7. Phase4F.4-C: Model architecture

### 7.1 Primary: LAU-SetRuleTransformer-v1

Use this as the first serious advanced model.

Reason:

```text
It is stronger than MLP, uses attention over traffic edge sets and rules,
but remains small enough for future C++ JSON runtime export.
```

Architecture:

```python
class LAUSetRuleTransformerV1(nn.Module):
    def __init__(self, d_model=64, n_heads=2, n_layers=2):
        self.global_encoder = NumericEncoder(global_dim, d_model)
        self.edge_encoder = EdgeTokenEncoder(edge_dim, d_model)
        self.rule_encoder = RuleTokenEncoder(rule_dim, d_model)

        self.edge_set_encoder = TransformerEncoder(d_model, n_heads, n_layers)
        self.rule_cross_attention = MultiheadAttention(d_model, n_heads)
        self.rule_self_attention = TransformerEncoder(d_model, n_heads, 1)

        self.q_delta_head = Linear(d_model, 1)          # [B, R]
        self.harmful_head = Linear(d_model, 1)          # [B, R]
        self.family_head = Linear(d_model, num_families) # optional
        self.confidence_head = Linear(d_model, 1)       # optional

    def forward(batch):
        g = encode_global(batch.global_features)        # [B, 1, D]
        e = encode_edges(batch.edge_tokens)             # [B, E, D]
        e = edge_set_encoder(concat([g, e]), mask)
        r = encode_rules(batch.rule_tokens)             # [B, R, D]
        r = cross_attn(query=r, key=e, value=e)
        r = rule_self_attention(r)
        return {
            "q_delta": q_delta_head(r).squeeze(-1),
            "harmful_logit": harmful_head(r).squeeze(-1),
            "family_logits": family_head(r),
            "confidence_logit": confidence_head(r).squeeze(-1),
        }
```

### 7.2 Secondary: LAU-EdgeTraceTransformer-v3

Use this only after SetRuleTransformer is working.

Architecture difference:

```text
context tokens = global token + edge tokens + compressed trace tokens
rule tokens cross-attend to all context tokens
```

Recommended defaults:

```yaml
model:
  d_model: 96
  n_heads: 4
  context_layers: 2
  rule_layers: 1
  max_edge_tokens: 64
  max_trace_tokens: 128
```

### 7.3 Optional: LAU-TopoBiasAttention-v1

Add attention bias between edge tokens:

```text
+b_shared_vertex
+b_reverse_edge
+b_nearby_endpoint
+b_same_direction_corridor
```

Do not make PyG a dependency. Use pure PyTorch attention masks / additive attention bias.

### New files

```text
src/models/laur_stable_attention.py
src/train/losses_laur_stable_attention.py
src/train/train_laur_stable_attention.py
src/eval/eval_laur_stable_attention.py
tests/test_phase4f_stable_attention_model.py
tests/test_phase4f_stable_attention_eval.py
```

---

## 8. Phase4F.4-D: Losses and selection policy

### Main prediction target

The model predicts per rule:

```text
q_delta[rule] = predicted delta_ratio_vs_additive
harmful_prob[rule] = probability this rule is harmful
```

It does **not** directly predict agent actions.

### Score for rule selection

Use:

```python
score(rule) = q_delta[rule] - safety_penalty * harmful_prob[rule]
```

Safety-gated selection:

```python
safe_rules = rules where harmful_prob < safety_threshold
if no safe non-additive rule:
    selected = additive_ltm
elif max(score) - score(additive_ltm) < confidence_margin:
    selected = additive_ltm
else:
    selected = argmax(score over safe_rules)
```

Recommended first values:

```yaml
eval:
  safety_threshold: 0.10
  safety_penalty: 0.02
  confidence_margin: 0.002
```

### Loss function

Total loss:

```text
L =
  lambda_listwise * listwise_KL(q_delta, soft_rule_target_stable)
+ lambda_pairwise * pairwise_margin_ranking(q_delta, rule_delta_vector)
+ lambda_delta * SmoothL1(q_delta, rule_delta_vector)
+ lambda_safe * per_rule_harmful_BCE(harmful_logit, rule_harmful_vector)
+ lambda_family * family_auxiliary_loss
+ lambda_conf * confidence_or_fallback_loss
+ lambda_additive * additive_fallback_regularization
```

Recommended first config:

```yaml
loss:
  lambda_listwise: 1.0
  lambda_pairwise: 0.5
  lambda_delta: 0.5
  lambda_safe: 2.0
  lambda_family: 0.1
  lambda_conf: 0.1
  lambda_additive: 0.1
  pairwise_margin: 0.005
  soft_target_temperature: 0.010
  harmful_pos_weight: auto
```

### Stable target handling

Use Repair3 stable targets as the main classification/eval target:

```text
rule_class_stable -> main top1/top3 target
rule_delta_vector -> listwise/pairwise/delta target
rule_harmful_vector -> per-rule safety target
```

Do not train against the old arbitrary hard argmax target as the only target.

---

## 9. Phase4F.4-E: Offline evaluation

### Evaluation files

```text
src/eval/eval_laur_stable_attention.py
outputs/reports/phase4f_repair4_stable_attention_report.md
outputs/reports/phase4f_repair4_stable_attention_summary.json
outputs/tables/phase4f_repair4_stable_attention_per_map.csv
outputs/tables/phase4f_repair4_stable_attention_confusion.csv
outputs/tables/phase4f_repair4_stable_attention_threshold_sweep.csv
```

### Metrics

Report all current Phase4F metrics:

```text
validation top1
validation top3
harmful recall
harmful precision
mean selected delta
validation non-neutral checkpoints
```

Add advanced-model diagnostics:

```text
executable top1 / top3
stable-target top1 / top3
original-target top1 / top3
pairwise ranking accuracy within checkpoint
Spearman correlation between q_delta and probe delta within checkpoint
selected-vs-additive delta
fallback rate
unsafe fallback rate
low-confidence fallback rate
per-map top1/top3/delta
per-agent-count top1/top3/delta
per-iteration top1/top3/delta
```

### Baselines to compare

Always compare against:

```text
Repair3 stable-target MLP seed-61
Repair3 stable-target MLP extra seeds 103 and 107
Repair1 MLP
Repair2 SetTransformer / EdgeTraceTransformer previous best
additive_ltm always
oracle best safe rule
```

### Offline promotion gate

The advanced model can be promoted to Phase5.5 only if it passes the original Phase4F gate and at least one advanced promotion condition.

Original gate:

```text
validation top1 >= 0.35
validation top3 >= 0.70
harmful recall >= 0.80
harmful precision >= 0.30
mean selected delta > 0.0
validation non-neutral checkpoints >= 50
```

Advanced promotion conditions:

```text
Condition A: mean selected delta is positive for at least 2 of 3 training seeds.
Condition B: average selected delta across seeds is positive.
Condition C: top3 is not worse than Repair3 MLP seed-61 by more than 0.02.
Condition D: harmful recall remains >= 0.80 for every reported seed.
Condition E: per-map selected delta is not catastrophically negative on either validation map.
```

Recommended seed set:

```text
61, 103, 107
```

If the advanced model fails this gate, do not integrate it into Phase5.5 runtime.

---

## 10. Phase4F.4-F: Training protocol

### Local smoke first

Run a small smoke before full training:

```powershell
python -m pytest tests/test_phase4f_stable_attention_dataset.py tests/test_phase4f_stable_attention_model.py
python src/train/train_laur_stable_attention.py --config configs/phase4/laur_ltm_stable_attention_smoke.yaml
python src/eval/eval_laur_stable_attention.py --config configs/phase4/laur_ltm_stable_attention_smoke.yaml
```

### Full offline training

Use existing Repair3 / Repair1 full artifacts; do not rerun record/probe unless necessary.

```powershell
python src/czr004_teacher/stable_attention_dataset_laur.py --config configs/phase4/laur_ltm_full_repair4_stable_attention.yaml
python src/train/train_laur_stable_attention.py --config configs/phase4/laur_ltm_full_repair4_stable_attention.yaml --seed 61
python src/eval/eval_laur_stable_attention.py --config configs/phase4/laur_ltm_full_repair4_stable_attention.yaml --seed 61
```

Then run extra seeds:

```powershell
python src/train/train_laur_stable_attention.py --config configs/phase4/laur_ltm_full_repair4_stable_attention.yaml --seed 103
python src/eval/eval_laur_stable_attention.py --config configs/phase4/laur_ltm_full_repair4_stable_attention.yaml --seed 103
python src/train/train_laur_stable_attention.py --config configs/phase4/laur_ltm_full_repair4_stable_attention.yaml --seed 107
python src/eval/eval_laur_stable_attention.py --config configs/phase4/laur_ltm_full_repair4_stable_attention.yaml --seed 107
```

### Hyperparameter sweep limits

Do not run an unbounded sweep. First sweep:

```yaml
model:
  d_model: [64, 96]
  n_heads: [2, 4]
  n_layers: [1, 2]
  max_edge_tokens: [32, 64]
training:
  lr: [0.001, 0.003]
  weight_decay: [0.0005, 0.001]
loss:
  soft_target_temperature: [0.005, 0.010]
  safety_penalty: [0.01, 0.02]
  confidence_margin: [0.0, 0.002, 0.005]
```

Write a sweep report. Do not cherry-pick without reporting failed settings.

### Gate report

Required report:

```text
outputs/reports/phase4f_repair4_stable_attention_report.md
```

It must include:

```text
commit / branch / dirty state
input artifacts and sha256 if available
model architecture
parameter count
training time
GPU/CPU info
all seed results
comparison to Repair3 MLP
whether Phase5.5 is allowed
exact reason if not allowed
```

---

## 11. Phase5.5-A: Runtime export decision

Only start this section if Phase4F.4 passes offline promotion gate.

### 11.1 Preferred runtime model

For Phase5.5, prefer exporting:

```text
LAU-SetRuleTransformer-v1
```

Reason:

```text
It avoids raw trace sequence dependence and can be implemented as a small C++ JSON runtime.
```

`LAU-EdgeTraceTransformer-v3` may remain an offline evidence model unless a practical runtime export is confirmed.

### 11.2 Export options

Preferred:

```text
C++ JSON runtime for small SetRuleTransformer
```

Allowed fallback if C++ JSON runtime is too expensive:

```text
ONNX Runtime smoke only, if dependency is documented and does not break existing builds
TorchScript/Python-service only as experimental report, not as final Phase5 gate
```

Do not make ONNX / TorchScript a hidden dependency for ordinary Phase5 parity tests.

### 11.3 Export files

```text
scripts/export_phase5_laur_attention_runtime.py
artifacts/models/laur_ltm/<model_name>/laur_attention_v1_weights.json
artifacts/models/laur_ltm/<model_name>/laur_attention_v1_token_stats.json
artifacts/models/laur_ltm/<model_name>/laur_attention_v1_rules.json
artifacts/models/laur_ltm/<model_name>/laur_attention_v1_export_report.json
```

Export schema must include:

```text
model_name
schema_version
rule_vocab
feature names
token feature names
normalization stats
edge token limits
trace token limits, if used
all linear weights
attention projection weights
layer norm weights if used
activation type
selection policy defaults
safety threshold
confidence margin
```

### Tests

```text
test_attention_export_schema
test_python_export_forward_matches_pytorch
test_missing_required_weight_fails_loudly
test_bad_rule_vocab_falls_back_or_errors_by config
```

---

## 12. Phase5.5-B: C++ attention runtime

Only implement after export tests pass.

### New C++ files

```text
cpp/ntm/laur_attention_runtime.hpp
cpp/ntm/laur_attention_runtime.cpp
cpp/ntm/laur_attention_features.hpp
cpp/ntm/laur_attention_features.cpp
cpp/ntm/phase5_laur_attention_runtime_smoke.cpp
```

### Runtime modes

Add model type enum:

```text
additive_only
mlp_v1
set_rule_transformer_v1
edge_trace_transformer_v3_optional
```

CLI flags in `phase1a_batch`:

```text
--laur-model-type mlp_v1|set_rule_transformer_v1
--laur-attention-model-path <dir>
--laur-attention-max-edge-tokens <K>
--laur-attention-max-trace-tokens <K>
--laur-confidence-margin <float>
```

### Required fallback behavior

```text
--laur-disable -> exact LTM
--laur-force-additive -> exact LTM through LAUR update path
missing model file -> fail unless --laur-missing-model-fallback is set
unsupported rule -> fallback additive and log reason
NaN prediction -> fallback additive and log reason
all rules unsafe -> fallback additive and log reason
low confidence -> fallback additive and log reason
```

### Logging fields

Add or extend JSONL fields:

```text
laur_model_type
laur_attention_model_path
laur_attention_inference_count
laur_attention_feature_build_ms
laur_attention_model_inference_ms
laur_attention_total_policy_ms
laur_attention_edge_tokens_mean
laur_attention_trace_tokens_mean
laur_attention_low_confidence_fallback_count
laur_attention_unsafe_fallback_count
laur_attention_nan_fallback_count
laur_selected_rules
```

### C++ / Python parity test

For a fixed batch of small feature rows:

```text
Python PyTorch forward
Python exported JSON forward
C++ runtime forward
```

All must agree within tolerance:

```text
max_abs_error q_delta <= 1e-4
max_abs_error harmful_prob <= 1e-4
selected_rule identical
fallback reason identical
```

### Build/test commands

```powershell
./scripts/build_phase5_laur_runtime_smoke.ps1
./scripts/phase5_laur_runtime_smoke.ps1
python -m pytest tests/test_phase5_laur_runtime_parity.py tests/test_phase5_laur_attention_runtime.py
```

### Gate

Pass if:

```text
C++ runtime loads exported attention model
Python/C++ forward parity passes
fallback tests pass
force-additive parity remains true
MLP runtime path still works
no search semantics changed
```

---

## 13. Phase5.5-C: Solver integration smoke

Only start after Phase5.5-B passes.

### Methods to compare

Use the existing Phase5C smoke set and add advanced attention:

```text
lacam_star_ltm
lacam_star_lau_ltm_force_additive
lacam_star_lau_ltm_mlp_repair3_safety
lacam_star_lau_ltm_attention_safety
lacam_star_lau_ltm_attention_no_safety
lacam_star_lau_ltm_attention_every_k2
lacam_star_lau_ltm_attention_every_restart
static_block_heavy
static_decay_095
```

### Smoke maps

Keep the Phase5C maps and add one denser bottleneck if available:

```text
random-32-32-20 agents 50,100
maze-32-32-4 agents 50,100
warehouse-10-20-10-2-1 agents 50,100
optional dense/bottleneck case agents 200 if runtime allows
```

### Time limits

```text
3s smoke
10s pilot if 3s smoke passes
```

### Safety modes

Always test:

```text
post-first-solution-only
every K=2 restarts
every restart
safety on
safety off
low-confidence fallback on
```

### Required scripts

```text
scripts/phase5p5_laur_attention_closed_loop_smoke.ps1
scripts/summarize_phase5p5_laur_attention_smoke.py
outputs/reports/phase5p5_laur_attention_closed_loop_smoke_report.md
outputs/reports/phase5p5_laur_attention_metrics_replay.md
outputs/tables/phase5p5_laur_attention_closed_loop_smoke_summary.csv
```

### Phase5.5 smoke gate

Pass if:

```text
schema errors = 0
force-additive parity = true
C++ attention runtime exercised = true
success count not lower than LTM
TTFS is evaluable and not catastrophically worse
feature/model/total overhead reported
candidate domain unchanged by code audit
PIBT legality untouched by code audit
```

This gate is engineering/safety. It does not by itself prove performance benefit.

---

## 14. Phase5.5-D: Conservative pilot for learned benefit

Only start after smoke gate passes.

### Pilot goal

Determine whether stable-target attention has a real chance to beat ordinary LTM in closed loop.

### Pilot design

Use paired comparisons:

```text
baseline: lacam_star_ltm
contender: lacam_star_lau_ltm_attention_safety
reference: lacam_star_lau_ltm_mlp_repair3_safety
```

Recommended pilot:

```text
maps: random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
agents: 50, 100, 200 where feasible
instances/seeds: at least 5 per map-agent group
time_limit: 10s first, then 30s only if 10s is promising
```

### Metrics

Use existing `src/czr004_metrics`.

Report:

```text
success rate
sum_of_loss_ratio
TTFS
returned_solutions_count
expanded_nodes
high_level_expansions
low_level_pibt_calls
quality-time AUC if available
feature_build_ms
model_inference_ms
total_policy_ms
selected_rule distribution
fallback reason distribution
paired sign test
paired delta distribution
per-map grouped deltas
equal-node comparison
```

### Learned-benefit gate

Do not lower standards. For Phase5 completion with advanced model, require:

```text
success not lower than LTM
force-additive parity true
schema errors = 0
ratio mean <= LTM ratio mean on paired successes
or dense/bottleneck subset ratio clearly better while overall not worse
expanded_nodes not worse or equal-node ratio not worse
TTFS not catastrophically worse
policy overhead reported and not dominating runtime
paired deltas show at least nonnegative trend, not only one lucky seed
```

If this fails, do not enter Phase6. Return to Phase4F/5.5 diagnostics.

---

## 15. Phase5 completion definition for this route

This route completes Phase5 only if all of the following are true:

### 15.1 Offline advanced model gate

```text
Stable-target advanced model passes Phase4F gate.
Extra-seed robustness is reported.
Comparison to Repair3 MLP is reported.
```

### 15.2 Runtime gate

```text
Advanced model exported.
C++ or approved runtime path works.
Python/C++ parity passes if C++ JSON runtime is used.
Missing/bad model behavior tested.
Fallback parity still passes.
```

### 15.3 Solver safety gate

```text
Phase5.5 closed-loop smoke passes.
Success not lower than LTM.
TTFS evaluable.
Overhead reported.
Candidate domain and PIBT semantics unchanged.
```

### 15.4 Learned-benefit pilot gate

```text
The advanced model is not worse than LTM on paired smoke/pilot.
At least one meaningful improvement signal exists:
  - lower mean ratio,
  - better dense/bottleneck subset,
  - better equal-node result,
  - better AUC / post-first-solution improvement,
  - or lower guidance overhead with equal quality.
```

If 15.1-15.3 pass but 15.4 fails, Phase5 can be recorded as:

```text
advanced LAU runtime integrated safely, but no learned-benefit claim yet.
```

Do not proceed to Phase6 learned-benefit main table in that case.

---

## 16. If the advanced model fails again

Do not keep blindly scaling the model.

If `LAU-SetRuleTransformer-v1` and `LAU-EdgeTraceTransformer-v3` both fail, write a diagnostic report and inspect:

```text
probe label ambiguity remains too high
update-rule set is too coarse or wrong
best safe rule is unstable across short-budget probes
trace tokenization loses important event order
validation map family remains too OOD
model overfits training maps
safety threshold suppresses useful rules
```

Then choose one repair direction:

```text
A. improve update-rule set: add saturation / mixed block+decay / local bottleneck rules
B. improve probe labels: longer probe budget or repeated probe seeds
C. improve trace representation: richer raw-event sequence tokens
D. improve data split: add train maze-like map while preserving separate OOD test
E. fallback to MLP runtime as engineering baseline and report negative advanced-model result
```

Do not claim LAU-LTM beats LTM if closed-loop metrics do not support it.

---

## 17. Recommended immediate Codex sequence

Use this sequence exactly unless blocked.

```text
Step 1: Create / switch to branch phase4f5p5-stable-attention-lau.
Step 2: Append docs/codex-worklog.md.
Step 3: Implement stable-target token dataset audit and v3 builder.
Step 4: Implement LAU-SetRuleTransformer-v1.
Step 5: Train/evaluate local smoke.
Step 6: Train/evaluate full stable-target SetTransformer with seeds 61/103/107.
Step 7: If gate fails, implement EdgeTraceTransformer-v3 and rerun.
Step 8: If offline gate passes, export SetTransformer runtime.
Step 9: Implement C++ JSON runtime only for the passing small model.
Step 10: Run Phase5.5 runtime parity and closed-loop smoke.
Step 11: Run conservative pilot.
Step 12: Write final Phase5.5 report and decide whether Phase6 is allowed.
```

---

## 18. Commit naming

Recommended commit messages:

```text
data: add stable-target attention dataset for LAU updates
model: add LAU stable attention update-rule network
train: add stable-target attention training and eval
results: add Phase4F stable attention offline evidence
runtime: add LAU attention runtime export
ltm: integrate LAU attention runtime smoke
results: add Phase5.5 attention closed-loop evidence
```

---

## 19. Final interpretation rules

If the advanced model passes offline but fails closed-loop:

```text
Do not claim LAU improves LTM.
Say: advanced update-rule model passed offline target but did not transfer to solver-level improvement.
Return to probe labels or update-rule set.
```

If the advanced model improves dense/bottleneck but not global mean:

```text
This can be a valid research result if success, TTFS, and overhead remain acceptable.
Report it as subset-specific learned traffic-update benefit.
```

If the advanced model beats LTM in smoke/pilot:

```text
Proceed to Phase6 planning, but only after repeating with larger paired runs and metrics harness replay.
```

The final scientific contribution must remain:

```text
learning LTM update dynamics from PIBT traffic traces and downstream solver probes,
with exact fallback to additive LTM and no change to LaCAM*/PIBT legality.
```
