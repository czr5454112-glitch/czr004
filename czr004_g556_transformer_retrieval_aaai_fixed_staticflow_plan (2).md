# Repair5G.5.56 Plan — AAAI-Scale Transformer/Retrieval Surrogate for Fixed Global StaticFlow Coefficients

Project: `czr004`
Branch: `codex/g531-slice-pilot`
Start point: after G5.55 commit `9e083eb` (`repair5g: finish g555 staticflow analysis repair`)
Round name: `Repair5G.5.56 AAAI-scale Transformer/Retrieval surrogate fixed-global staticflow optimization`

---

## 0. Executive decision

G5.56 continues the **fixed-global staticflow coefficient** route.

Do **not** resume the dynamic learned UpdateParams policy line in this round:

```text
contextual selector: paused
checkpoint-level policy: paused
abstention policy: paused
per-context theta generator: paused
runtime learned UpdateParams policy: paused
dynamic neural UpdateLTM policy: paused
```

G5.55 promoted a stronger fixed global coefficient vector:

```text
promoted_fixed_candidate_id = g554_c00051
blind_passed = true
blind_new_solver_rows = 120000
success_regression_count_vs_old_hand_static_flow = 0
success_gain_count_vs_old_hand_static_flow = 37
success_rate_delta_vs_old_hand_static_flow = +0.00185
both_success_quality_delta_mean_vs_old_hand_static_flow = -0.0210143833861
bootstrap_ci_upper = -0.0205820545487
support_strata = 216
support_seed_blocks = 1000
fingerprint_match_rate = 1
candidate_recognized_all = true
cost_finite_all = true
```

Therefore G5.56 must treat:

```text
primary baseline = g554_c00051
```

not the old hand `repair5g59_static_flow_shield`.

The G5.56 objective is:

```text
Train an offline attention/retrieval surrogate on solver-facing fixed-theta data,
use it to propose one fixed global coefficient vector,
and test proposed candidates by real paired solver replay against g554_c00051.
```

The neural model is **training-time only**. It is not deployed at runtime and it does not choose different coefficients by context.

---

## 1. Why Transformer/retrieval, not just MLP?

The previous draft used TabM-style MLP ensemble as primary. That is strong and should remain a required control, but the user wants a more advanced attention-based architecture suitable for an AAAI-quality experiment and two RTX 4090 GPUs.

G5.56 therefore uses a **Transformer/retrieval-first** design.

Rationale:

```text
1. The row-level input is tabular but highly structured:
   theta coefficients + solver settings + map/agent/budget/horizon context.

2. The candidate-level objective is set/distributional:
   one theta vector is good only if it performs well across many evaluation contexts.

3. Attention is useful for:
   - theta-field interactions;
   - context-theta interactions;
   - map/agent/budget/horizon conditional effects;
   - retrieving similar historical candidate-context outcomes;
   - aggregating a set of predicted context outcomes into a global candidate score.

4. Fixed-global optimization still needs a safety shield:
   neural predictions only propose candidates;
   promotion still requires real solver replay with zero success regressions.
```

The main model should therefore be:

```text
FixedTheta Retrieval-Set Transformer (FTRST)
```

with:

```text
row-level theta/context Transformer
+ retrieval memory over similar historical rows
+ candidate-set Transformer / DeepSets aggregation
+ distributional multi-head outputs
+ constrained candidate generator
```

This is a more advanced and attention-based route, while still respecting the fixed-global coefficient constraint.

---

## 2. Literature and design anchors

G5.56 should include a short literature grounding report, not citation padding.

### 2.1 MAPF / guidance optimization anchors

Relevant lessons:

```text
Guidance Graph Optimization (GGO):
  Guidance can be optimized through solver-facing outcomes.
  It optimizes edge weights and an update model capable of generating guidance.
  Lesson: learned/optimized guidance should be judged by closed-loop solver replay.

Online GGO:
  Dynamic guidance can outperform static guidance when traffic-conditioned policies are allowed.
  Lesson: dynamic guidance is plausible but harder; G5.56 deliberately stays fixed-global.

CS-PIBT / learning-MAPF shield lesson:
  Learned predictions require a strong safety/shield layer and strong non-learned baselines.
  Lesson: neural surrogate output cannot be promoted without zero-regression solver replay.

MAPF-LNS benchmark:
  Baseline alignment, unified evaluation protocol, and executable learned models are mandatory.
  Lesson: G5.56 must evaluate candidates against g554_c00051 under paired replay.
```

### 2.2 Tabular / surrogate modeling anchors

Use the following model families in the literature audit:

```text
FT-Transformer:
  strong tabular Transformer baseline; useful for feature-token attention.

TabR:
  retrieval-augmented tabular deep learning; strong fit because our task benefits from
  retrieving similar theta/context/outcome rows.

SAINT:
  row-and-column attention with contrastive/self-supervised pretraining;
  useful inspiration for context-row attention and masked-feature pretraining.

AMFormer:
  additive/multiplicative attention for arithmetic feature interactions;
  highly relevant because theta fields interact arithmetically.

TabPFN / TabICL:
  tabular foundation/in-context models; use as small/medium diagnostic only,
  not primary for 1M-3M row training.

TabM:
  parameter-efficient MLP ensemble; required strong neural control.

GBDT controls:
  LightGBM/XGBoost/CatBoost-style controls remain required because tabular deep
  learning papers repeatedly show tree baselines are hard to beat.
```

The report should explicitly justify why FTRST is chosen as the main architecture:

```text
Transformer attention for theta/context interactions
retrieval memory for local empirical outcome neighborhoods
set aggregation for global fixed candidate scoring
multi-head risk/utility labels matching the solver-facing objective
```

---

## 3. Candidate object and forbidden shortcuts

A candidate is exactly:

```text
one deterministic global fixed UpdateParams theta vector
```

It is shared across:

```text
all maps
all agent counts
all seeds
all budgets
all horizons
all checkpoints
all runtime states
```

It must not depend on:

```text
map_family
map
agents
seed
budget
horizon
checkpoint
trace
traffic state
runtime context
selector decision
model output at runtime
```

Forbidden in G5.56:

```text
contextual selector
checkpoint policy
runtime learned policy
abstention policy
per-context theta generator
per-map fixed vector as main claim
per-agent fixed vector as main claim
policy-as-executed dynamic action log
```

Allowed:

```text
offline neural surrogate proposes fixed global theta vectors
real paired solver replay decides promotion
```

---

## 4. Baseline hierarchy

Primary baseline for promotion:

```text
g554_c00051
```

Previous baseline diagnostic:

```text
old hand static_flow_shield / repair5g59_static_flow_shield
```

Paper/parity floor:

```text
additive_ltm
```

Diagnostics:

```text
frozen_family_static_goal_aware
best_fixed_static_goal_aware
family_static variants
g554_c00894 diagnostic high-quality but unsafe in blind because it had 1 success regression
```

Promotion can only happen if a candidate beats:

```text
g554_c00051
```

A candidate that beats old hand staticflow but loses to g554_c00051 is not a new promotion.

---

## 5. Claim flags

Keep all closed:

```json
{
  "phase5p5_allowed": false,
  "phase6_allowed": false,
  "runtime_claim_allowed": false,
  "learned_runtime_policy_validated": false,
  "aaai_ready": false
}
```

Even if blind passes, the result is only:

```text
stronger fixed global baseline candidate
```

not:

```text
runtime learned UpdateLTM policy
```

---

## 6. Solver / code guardrails

Do not modify:

```text
external/lacam2/lacam2/**
PIBT conflict semantics
candidate domain
agent actions
agent priorities
h-values
OPEN / EXPLORED
LaCAM* high-level search
rewrite / incumbent pruning
restart semantics
candidate deletion semantics
```

Do not use reserved IDs:

```text
166..205
```

All fixed candidate theta must satisfy:

```text
candidate_recognized_all = true
fulltheta_fingerprint_match_rate = 1
cost_finite_all = true
theta_in_bounds_all = true
goal_projection_mode canonical
```

---

## 7. Remote storage and 2x4090 setup

The remote root disk `/` is small, about 30GB. The large shared storage is:

```text
/root/shared-nvme
```

Use:

```bash
export REMOTE_ARTIFACT_ROOT=/root/shared-nvme/czr004_g556_remote_artifacts
export TMPDIR=/root/shared-nvme/tmp
mkdir -p "$REMOTE_ARTIFACT_ROOT" "$TMPDIR"
```

All large artifacts go under:

```text
/root/shared-nvme/czr004_g556_remote_artifacts/raw/
/root/shared-nvme/czr004_g556_remote_artifacts/parquet/
/root/shared-nvme/czr004_g556_remote_artifacts/model_checkpoints/
/root/shared-nvme/czr004_g556_remote_artifacts/solver_results/
/root/shared-nvme/czr004_g556_remote_artifacts/tmp/
```

Do not write large raw files under:

```text
/root/czr004/outputs/logs
/root/czr004/outputs/tmp
/tmp
```

unless they are symlinks to shared NVMe.

Commit only compact summaries, leaderboards, manifests, hashes, and small previews.

No raw CSV >50MB in git.

---

## 8. Required worklog and governance entry

Before coding, append to `docs/codex-worklog.md`:

```markdown
## 2026-06-16 - Repair5G.5.56 Transformer/retrieval fixed-global surrogate optimization

- Request:
  Continue after G5.55 commit 9e083eb. G5.55 promoted g554_c00051 as a stronger fixed global staticflow baseline candidate after validation and blind replay. Dynamic learned UpdateParams policy remains paused.

- Objective:
  Use a Transformer/retrieval offline surrogate to optimize one fixed global staticflow coefficient vector. The neural model is training-time only and proposes fixed candidate vectors; it is not a contextual selector or runtime learned policy.

- Primary baseline:
  g554_c00051 is now the primary fixed baseline. Old hand static_flow_shield and additive_ltm are diagnostics.

- Model:
  Main model is FixedTheta Retrieval-Set Transformer (FTRST): row-level theta/context Transformer, retrieval memory over historical solver rows, candidate-set aggregation, and multi-head risk/utility/quantile outputs. TabM/MLP ensemble, FT-Transformer, SAINT/AMFormer-inspired diagnostics, TabPFN/TabICL small-split diagnostics, and GBDT controls are required baselines.

- Resources:
  Use two RTX 4090 GPUs where available. Store large data/checkpoints/results under /root/shared-nvme/czr004_g556_remote_artifacts, not root disk.

- Constraints:
  No external/lacam2/lacam2 edits, no solver semantic changes, no dynamic policy, no selector, no checkpoint policy, no abstention gate, no per-context theta, no IDs 166..205, no runtime/Phase5.5/Phase6/AAAI claims.
```

Update governance docs if baseline or SafeGate wording changes:

```text
deep-research-report.md
docs/aaai_quality_requirements.md
docs/goal_aware_dual_channel_ltm_research_strategy.md
phase4_6_laur_ltm_codex_execution_plan.md
```

Required governance statement:

```text
After G5.55, g554_c00051 is the primary fixed global staticflow baseline. G5.56 uses a Transformer/retrieval surrogate only as an offline optimizer for fixed global coefficient vectors. It is not a dynamic learned UpdateParams policy. Any candidate must beat g554_c00051 by paired solver validation/blind replay with zero success regressions before becoming a stronger fixed baseline candidate.
```

---

## 9. Required scripts

Create:

```text
czr004_g556_transformer_retrieval_fixed_staticflow_plan.md

scripts/repair5g556_common.py
scripts/verify_repair5g556_g555_artifacts.py
scripts/audit_repair5g556_promoted_baseline.py
scripts/create_repair5g556_literature_model_audit.py
scripts/create_repair5g556_unified_fixedtheta_dataset_manifest.py
scripts/create_repair5g556_surrogate_dataset.py
scripts/train_eval_repair5g556_ftrst_surrogate.py
scripts/train_eval_repair5g556_ft_transformer_baseline.py
scripts/train_eval_repair5g556_saint_amformer_diagnostics.py
scripts/train_eval_repair5g556_tabm_and_mlp_controls.py
scripts/train_eval_repair5g556_gbdt_controls.py
scripts/generate_repair5g556_surrogate_candidates.py
scripts/create_repair5g556_stage1_solver_screen_plan.py
scripts/run_repair5g556_stage1_solver_screen.py
scripts/analyze_repair5g556_stage1_solver_screen.py
scripts/create_repair5g556_stage2_elite_validation_plan.py
scripts/run_repair5g556_stage2_elite_validation.py
scripts/analyze_repair5g556_stage2_elite_validation.py
scripts/create_repair5g556_blind_if_warranted.py
scripts/run_repair5g556_blind_if_warranted.py
scripts/analyze_repair5g556_blind_if_warranted.py
scripts/write_repair5g556_decision.py
```

---

## 10. Stage A — Verify G5.55 and promoted baseline

Inputs:

```text
outputs/reports/phase5p5_repair5g555_decision_summary.json
outputs/reports/phase5p5_repair5g555_corrected_validation_summary.json
outputs/reports/phase5p5_repair5g555_blind_summary.json
outputs/tables/phase5p5_repair5g555_blind_candidate_leaderboard.csv
outputs/tables/phase5p5_repair5g555_final_candidate_theta.csv
```

Write:

```text
outputs/reports/phase5p5_repair5g556_g555_verification.md
outputs/reports/phase5p5_repair5g556_g555_verification_summary.json
outputs/reports/phase5p5_repair5g556_promoted_baseline_audit.md
outputs/reports/phase5p5_repair5g556_promoted_baseline_audit_summary.json
outputs/tables/phase5p5_repair5g556_g555_artifact_audit.csv
outputs/tables/phase5p5_repair5g556_promoted_baseline_theta.csv
outputs/tables/phase5p5_repair5g556_claim_flag_audit.csv
```

Required checks:

```text
g555_decision = g555_fixed_global_staticflow_candidate_blind_passed_keep_claims_closed
promoted_fixed_candidate_id = g554_c00051
blind_passed = true
blind_new_solver_rows = 120000
blind_success_regression_count_vs_old_hand_static_flow = 0
blind_quality_delta_vs_old_hand_static_flow = -0.0210143833861
fingerprint = 1
recognized = true
cost finite = true
all claim flags closed
external_lacam2_clean = true
```

Stop if baseline is not verified.

---

## 11. Stage B — Literature/model audit

Create:

```text
scripts/create_repair5g556_literature_model_audit.py
```

Write:

```text
outputs/reports/phase5p5_repair5g556_literature_model_audit.md
outputs/reports/phase5p5_repair5g556_literature_model_audit_summary.json
outputs/tables/phase5p5_repair5g556_model_family_decision_matrix.csv
```

The report should compare:

```text
FTRST primary architecture
FT-Transformer
TabTransformer
SAINT
AMFormer
TabR
TabPFN / TabICL
TabM
GBDT controls
CEM / CMA-ES / trust-region controls
```

For each:

```text
attention/retrieval support
fits 1M-3M rows?
fits 2x4090?
handles mixed numeric/categorical features?
supports uncertainty/risk outputs?
code feasibility in czr004?
role in G5.56
```

Required decision:

```text
primary_model_family = FixedTheta Retrieval-Set Transformer
required_controls = TabM, FT-Transformer, GBDT, heuristic optimizers
```

---

## 12. Stage C — Unified fixed-theta dataset manifest

Create:

```text
scripts/create_repair5g556_unified_fixedtheta_dataset_manifest.py
```

Collect sources:

```text
G5.49 fulltheta replay
G5.50 fulltheta expansion
G5.50 active theta search
G5.51 targeted / iteration labels
G5.52 Label-v2 dataset
G5.53 fixed search
G5.54 fresh fixed search
G5.55 validation / blind
```

Write:

```text
outputs/reports/phase5p5_repair5g556_unified_dataset_manifest.md
outputs/reports/phase5p5_repair5g556_unified_dataset_manifest_summary.json
outputs/tables/phase5p5_repair5g556_source_artifact_manifest.csv
outputs/tables/phase5p5_repair5g556_source_schema_audit.csv
outputs/tables/phase5p5_repair5g556_available_raw_artifacts.csv
outputs/tables/phase5p5_repair5g556_missing_raw_artifacts.csv
```

Minimum:

```text
usable row-level examples >= 1,000,000
unique theta candidates >= 10,000
unique contexts >= 5,000
```

Preferred:

```text
usable row-level examples >= 3,000,000
unique theta candidates >= 50,000
unique contexts >= 10,000
```

If insufficient, write a solver top-up plan before training.

---

## 13. Stage D — Surrogate dataset construction

Create:

```text
scripts/create_repair5g556_surrogate_dataset.py
```

Primary labels must be normalized to:

```text
baseline = g554_c00051
```

If historical rows compare only to old hand staticflow, mark them as auxiliary or create/rerun paired baseline rows.

Raw dataset:

```text
/root/shared-nvme/czr004_g556_remote_artifacts/parquet/surrogate_rows.parquet
/root/shared-nvme/czr004_g556_remote_artifacts/parquet/candidate_context_pairs.parquet
/root/shared-nvme/czr004_g556_remote_artifacts/parquet/candidate_sets.parquet
```

Committed outputs:

```text
outputs/reports/phase5p5_repair5g556_surrogate_dataset.md
outputs/reports/phase5p5_repair5g556_surrogate_dataset_summary.json
outputs/tables/phase5p5_repair5g556_surrogate_dataset_preview.csv
outputs/tables/phase5p5_repair5g556_surrogate_split_summary.csv
outputs/tables/phase5p5_repair5g556_surrogate_feature_manifest.csv
outputs/tables/phase5p5_repair5g556_surrogate_label_manifest.csv
outputs/tables/phase5p5_repair5g556_surrogate_leakage_audit.csv
```

Features:

```text
theta numeric fields
theta mode one-hot
distance from g554_c00051
distance from old hand staticflow
active field deltas
map_family
map id
agents
nominal_budget_ms
short_budget_ms
base_time_limit_sec
ltm_max_iterations
horizon id
source round
candidate family
```

Forbidden as features:

```text
candidate_success
baseline_success
success_regression
success_gain
both_success
quality_delta
future replay outcome
oracle labels
post-hoc rank
```

Labels:

```text
success_regression_vs_g554_c00051
success_gain_vs_g554_c00051
quality_delta_vs_g554_c00051
success_regression_vs_additive
quality_delta_vs_additive
fingerprint/materialization feasibility
```

Splits:

```text
train: older rounds and non-heldout seeds
val: heldout seed blocks and heldout candidate families
test: heldout maps/horizons/candidate families
candidate-generation-blind: no labels exposed after candidate generation
```

---

## 14. Stage E — Train FTRST primary model

Create:

```text
scripts/train_eval_repair5g556_ftrst_surrogate.py
```

Architecture:

```text
FixedTheta Retrieval-Set Transformer

Components:
  feature tokenizer for scalar theta/context fields
  categorical embeddings
  row-level Transformer encoder
  retrieval memory over nearest historical rows
  cross-attention from query row to retrieved neighbors
  candidate-set aggregator over canonical context panel
  multi-head risk/gain/quality/quantile outputs
```

Row-level outputs:

```text
p_success_regression_vs_g554_c00051
p_success_gain_vs_g554_c00051
p_success_regression_vs_additive
expected_quality_delta_vs_g554_c00051
quality_delta_q10/q50/q90
uncertainty
```

Candidate-level outputs:

```text
global_regression_risk
global_success_gain_estimate
global_quality_delta_mean
global_quality_ci_upper
support_coverage
pareto_score
```

Training:

```text
2x4090
mixed precision
gradient accumulation
DDP if stable
checkpoint every epoch to shared-nvme
early stopping
hard-negative oversampling
source-round balancing
heldout-map/horizon validation
```

Minimum training:

```text
epochs >= 50 unless early stopping
batch_size auto based on GPU memory
train_rows >= 1M
```

Loss:

```text
weighted BCE for regression risk
weighted BCE for success gain
Huber loss for quality delta
quantile pinball loss
pairwise ranking loss
calibration/Brier penalty
tail-risk false-safe penalty
```

Write:

```text
outputs/reports/phase5p5_repair5g556_ftrst_eval.md
outputs/reports/phase5p5_repair5g556_ftrst_eval_summary.json
outputs/tables/phase5p5_repair5g556_ftrst_metrics.csv
outputs/tables/phase5p5_repair5g556_ftrst_calibration.csv
outputs/tables/phase5p5_repair5g556_ftrst_oof_sample.csv
artifacts/models/laur_ltm/repair5g556_ftrst_manifest.json
```

Offline gate:

```text
false_safe_hard_negative_count = 0
regression risk PR-AUC reported
calibration ECE <= 0.05 or justify
quality ranking Spearman > 0.20 or justify
top-k recall includes known passing fixed candidates
heldout map/agent/horizon degradation reported
negative controls fail
feature leakage false
```

---

## 15. Stage F — Train controls

Create:

```text
scripts/train_eval_repair5g556_ft_transformer_baseline.py
scripts/train_eval_repair5g556_saint_amformer_diagnostics.py
scripts/train_eval_repair5g556_tabm_and_mlp_controls.py
scripts/train_eval_repair5g556_gbdt_controls.py
```

Required controls:

```text
FT-Transformer
TabTransformer-style categorical Transformer
SAINT-style row/column attention diagnostic
AMFormer-inspired additive/multiplicative attention diagnostic
TabR-style retrieval diagnostic if feasible
TabM / MLP ensemble
LightGBM / XGBoost / CatBoost if installed
logistic/ridge risk baseline
random candidate baseline
G5.54 trust-region heuristic
CEM/CMA-ES-style non-neural optimizer
```

If some package is unavailable, write exact blocker and implement a simple fallback where possible.

Control gate:

```text
At least one non-transformer strong control must run.
If FTRST does not beat controls offline, candidate generation may still use an ensemble,
but report the failure.
```

---

## 16. Stage G — Surrogate candidate generation

Create:

```text
scripts/generate_repair5g556_surrogate_candidates.py
```

Generate:

```text
candidate_vectors_generated >= 100000
preferred >= 500000
candidate_vectors_selected_for_solver >= 3000
preferred selected >= 5000
```

Sources:

```text
FTRST gradient-guided search
FTRST acquisition sampling
retrieval-neighbor interpolation
candidate-set aggregator Pareto scoring
CEM elite refit
CMA-ES-style evolution
trust-region around g554_c00051
trust-region around g554_c00051 and old candidates
TabM/GBDT ensemble disagreement sampling
random/wide negative controls
```

Acquisition constraints:

```text
predicted regression risk vs g554_c00051 low
predicted additive catastrophic risk low
predicted quality delta negative
uncertainty penalized
support coverage high
distance from g554_c00051 recorded
all fields in bounds
goal mode canonical
fingerprint precheck passes
```

Write:

```text
outputs/reports/phase5p5_repair5g556_candidate_generation.md
outputs/reports/phase5p5_repair5g556_candidate_generation_summary.json
outputs/tables/phase5p5_repair5g556_candidate_registry_preview.csv
outputs/tables/phase5p5_repair5g556_candidate_acquisition_scores.csv
outputs/tables/phase5p5_repair5g556_candidate_family_breakdown.csv
```

Raw registry:

```text
/root/shared-nvme/czr004_g556_remote_artifacts/raw/surrogate_candidate_registry.csv
```

---

## 17. Stage H — Stage1 real solver screen

Create:

```text
scripts/create_repair5g556_stage1_solver_screen_plan.py
scripts/run_repair5g556_stage1_solver_screen.py
scripts/analyze_repair5g556_stage1_solver_screen.py
```

Run:

```text
new_solver_rows >= 300000
preferred >= 600000
candidate_vectors_screened >= 3000
contexts >= 1500
baseline g554_c00051 rows >= 1500
old hand staticflow diagnostic rows >= 1500
additive diagnostic rows >= 1500
```

Promotion baseline:

```text
g554_c00051
```

Stage1 outputs:

```text
outputs/reports/phase5p5_repair5g556_stage1_solver_screen.md
outputs/reports/phase5p5_repair5g556_stage1_solver_screen_summary.json
outputs/tables/phase5p5_repair5g556_stage1_candidate_leaderboard.csv
outputs/tables/phase5p5_repair5g556_stage1_by_stratum.csv
outputs/tables/phase5p5_repair5g556_stage1_surrogate_vs_actual.csv
outputs/tables/phase5p5_repair5g556_stage1_failure_cases.csv
```

Stage1 shortlist for Stage2:

```text
success_regression_count_vs_g554_c00051 <= 2
or zero-regression low-support high-gain
mean quality delta <= -0.001
fingerprint=1
recognized=true
cost_finite=true
```

Do not promote from Stage1.

---

## 18. Stage I — Stage2 elite validation

Create:

```text
scripts/create_repair5g556_stage2_elite_validation_plan.py
scripts/run_repair5g556_stage2_elite_validation.py
scripts/analyze_repair5g556_stage2_elite_validation.py
```

Select:

```text
top_transformer_candidates <= 30
top_control_candidates <= 10
g554_c00051 baseline
old hand staticflow diagnostic
additive diagnostic
g554_c00894 unsafe high-quality diagnostic
```

Run:

```text
new_solver_rows >= 240000
preferred >= 480000
candidate_rows_per_candidate >= 10000
```

Stage2 pass:

```text
success_regression_count_vs_g554_c00051 = 0
success_rate_delta_vs_g554_c00051 >= 0
quality_delta_mean_vs_g554_c00051 <= -0.001
bootstrap_ci_upper <= 0
better_count > worse_count
fingerprint=1
recognized=true
cost_finite=true
theta_in_bounds=true
support_strata >= 100
support_seed_blocks >= 500
```

Outputs:

```text
outputs/reports/phase5p5_repair5g556_stage2_elite_validation.md
outputs/reports/phase5p5_repair5g556_stage2_elite_validation_summary.json
outputs/tables/phase5p5_repair5g556_stage2_candidate_leaderboard.csv
outputs/tables/phase5p5_repair5g556_stage2_by_stratum.csv
outputs/tables/phase5p5_repair5g556_stage2_vs_old_hand_staticflow.csv
outputs/tables/phase5p5_repair5g556_stage2_vs_additive.csv
outputs/tables/phase5p5_repair5g556_stage2_validation_shortlist.csv
```

---

## 19. Stage J — Blind replay if warranted

Create:

```text
scripts/create_repair5g556_blind_if_warranted.py
scripts/run_repair5g556_blind_if_warranted.py
scripts/analyze_repair5g556_blind_if_warranted.py
```

Only if Stage2 passes.

Blind:

```text
candidate_count <= 3
new_solver_rows >= 240000
preferred >= 480000
fresh seeds only
no tuning after blind plan
```

Blind pass:

```text
success_regression_count_vs_g554_c00051 = 0
success_rate_delta_vs_g554_c00051 >= 0
quality_delta_mean_vs_g554_c00051 <= -0.001
bootstrap_ci_upper <= 0
better_count > worse_count
fingerprint=1
recognized=true
cost_finite=true
theta_in_bounds=true
```

Even if blind passes, claims remain closed.

---

## 20. Stage K — Decision

Create:

```text
scripts/write_repair5g556_decision.py
```

Write:

```text
outputs/reports/phase5p5_repair5g556_decision.md
outputs/reports/phase5p5_repair5g556_decision_summary.json
outputs/tables/phase5p5_repair5g556_claim_ledger.csv
outputs/tables/phase5p5_repair5g556_final_candidate_theta.csv
outputs/tables/phase5p5_repair5g556_large_artifact_manifest.csv
```

Decision labels:

```text
g556_baseline_not_verified_stop
g556_dataset_underpowered_need_topup
g556_ftrst_failed_controls_better
g556_candidates_failed_stage1_keep_g554_c00051
g556_stage2_no_candidate_beats_g554_c00051_keep_baseline
g556_blind_failed_keep_g554_c00051
g556_transformer_fixed_global_candidate_blind_passed_keep_claims_closed
```

Final summary must include:

```json
{
  "primary_baseline": "g554_c00051",
  "candidate_object": "one fixed global coefficient vector",
  "dynamic_learned_policy_paused": true,
  "primary_model_family": "FixedTheta Retrieval-Set Transformer",
  "training_rows": 0,
  "candidate_vectors_generated": 0,
  "stage1_solver_rows": 0,
  "stage2_solver_rows": 0,
  "blind_solver_rows": 0,
  "best_candidate_id": "",
  "best_candidate_success_regressions_vs_g554_c00051": 0,
  "best_candidate_quality_delta_vs_g554_c00051": "",
  "optimized_fixed_candidate_promoted": false,
  "phase5p5_allowed": false,
  "phase6_allowed": false,
  "runtime_claim_allowed": false,
  "learned_runtime_policy_validated": false,
  "aaai_ready": false
}
```

---

## 21. Recommended server commands

```bash
export REMOTE_ARTIFACT_ROOT=/root/shared-nvme/czr004_g556_remote_artifacts
export TMPDIR=/root/shared-nvme/tmp
mkdir -p "$REMOTE_ARTIFACT_ROOT" "$TMPDIR"
df -h /
df -h /root/shared-nvme

python scripts/verify_repair5g556_g555_artifacts.py
python scripts/audit_repair5g556_promoted_baseline.py
python scripts/create_repair5g556_literature_model_audit.py
python scripts/create_repair5g556_unified_fixedtheta_dataset_manifest.py
python scripts/create_repair5g556_surrogate_dataset.py

python scripts/train_eval_repair5g556_ftrst_surrogate.py --device cuda --gpus 2 --epochs 80 --batch-size auto
python scripts/train_eval_repair5g556_ft_transformer_baseline.py --device cuda --gpus 2
python scripts/train_eval_repair5g556_saint_amformer_diagnostics.py --device cuda --gpus 2
python scripts/train_eval_repair5g556_tabm_and_mlp_controls.py --device cuda --gpus 2
python scripts/train_eval_repair5g556_gbdt_controls.py

python scripts/generate_repair5g556_surrogate_candidates.py --candidate-count 100000 --selected-count 3000
python scripts/create_repair5g556_stage1_solver_screen_plan.py
python scripts/run_repair5g556_stage1_solver_screen.py --row-limit 300000 --max-workers 24
python scripts/analyze_repair5g556_stage1_solver_screen.py

python scripts/create_repair5g556_stage2_elite_validation_plan.py
python scripts/run_repair5g556_stage2_elite_validation.py --row-limit 240000 --max-workers 24
python scripts/analyze_repair5g556_stage2_elite_validation.py

python scripts/create_repair5g556_blind_if_warranted.py
python scripts/run_repair5g556_blind_if_warranted.py --row-limit 240000 --max-workers 24
python scripts/analyze_repair5g556_blind_if_warranted.py

python scripts/write_repair5g556_decision.py
```

---

## 22. Success interpretation

A real G5.56 success:

```text
FTRST or ensemble proposes fixed global candidate
candidate passes Stage2 against g554_c00051
candidate passes blind against g554_c00051
zero success regression
negative quality delta
fingerprint=1
cost finite
all claims closed
```

A useful negative:

```text
no candidate beats g554_c00051 under real paired replay
```

Then:

```text
g554_c00051 is likely a strong fixed-global Pareto baseline.
Future work may require per-family fixed diagnostics or a later return to dynamic learned policy.
```

---

## 23. Forbidden shortcuts

Do not:

```text
call the Transformer a runtime policy
choose theta per context
switch coefficients by map/agent/horizon
promote by surrogate prediction alone
skip g554_c00051 comparison
promote candidate that only beats old hand staticflow
relax zero-regression gate
skip additive diagnostics
fill root disk
commit large raw CSVs
```

---

## 24. Main question

G5.56 should answer:

```text
Can a modern attention/retrieval offline surrogate, trained on AAAI-scale
solver-facing fixed-theta data, find a single global coefficient vector that
improves over g554_c00051?
```

## Final Outcome - 2026-06-18

Yes for the fixed-global coefficient route, no for learned SafeGate/runtime policy.

The server run completed under `tmux` on `/root/shared-nvme/czr004_g556_9e083eb`. The final decision is:

```text
g556_transformer_fixed_global_candidate_blind_passed_keep_claims_closed
```

`g556_c063174` is promoted as the stronger deterministic fixed global staticflow candidate versus `g554_c00051`.

Key evidence:

```text
unified usable row-level examples: 1,001,437
surrogate training rows: 968,362
candidate vectors generated: 100,000
Stage1 solver rows: 304,500
Stage2 solver rows: 430,000
blind solver rows: 360,000
blind passing candidates: 2
best blind candidate: g556_c063174
blind success regressions vs g554_c00051: 0
blind quality delta vs g554_c00051: -0.0032705119799
blind CI upper: -0.00305603582661
blind better vs worse pairs: 28,508 vs 20,887
support strata: 216
support seed blocks: 3,000
```

FTRST and FT-Transformer did not pass the offline learned-SafeGate gate, so this is not a learned runtime policy result. The valid claim is narrower: offline Transformer/retrieval-assisted search found a stronger fixed global coefficient vector, and real paired solver replay promoted that fixed vector. Runtime, Phase5.5, Phase6, learned-runtime, and AAAI claims remain closed.
