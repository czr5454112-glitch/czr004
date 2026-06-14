# Repair5G.5.45 Deep Direction Plan — Neural Continuous UpdateParams Generator for Static-Flow / Dual-Channel LTM

Project: `czr004`  
Branch: `codex/g531-slice-pilot`  
Starting point: after G5.43 commit `fca925f` and any partial G5.44 work should be treated as superseded unless it produced reusable audits/features.  
Round name: `Repair5G.5.45 neural continuous static-flow UpdateParams generator`  
Main objective: stop hand-designed alias sweeping as the main method and build a neural, bounded, continuous `UpdateParams` generator that learns how to replace the LTM paper's coarse additive update while preserving LaCAM*/PIBT semantics.

---

## 0. Core decision

G5.45 should pivot from:

```text
manual candidate aliases -> safe region lookup -> maybe predictor
```

to:

```text
large solver-evaluated parameter dataset
  -> risk/utility surrogate models
  -> neural bounded continuous UpdateParams generator
  -> real solver replay validation
```

This is not a static selector. The model must not output:

```text
additive_ltm / static_flow / best_fixed / frozen_family_static
```

as the learned action.

The learned action is a continuous bounded parameter vector:

```text
theta = UpdateParams for static-flow / dual-channel LTM
```

The only allowed high-level decision outside the parameter vector is:

```text
ALLOW_GENERATED_PARAMS / ABSTAIN_TO_FIXED_STATIC_FLOW
```

Static baselines are diagnostic comparators and fallback only. Gains from choosing among static baselines must be reported as static-selector baseline gain, not LAU-LTM progress.

---

## 1. Why G5.45 supersedes the current G5.44 direction

G5.43 gave enough evidence that another hand-designed alias sweep is unlikely to be the right next step.

Observed G5.43 facts:

```text
decision = g543_static_ladder_confounded_g542_overlay_continue_repair
stage1_probe_rows = 12960
stage1_candidate_aliases = 101
stage1_safe_useful_region_count = 19
refinement_rows = 15120
final_supported_edge_event_region_count = 0
frozen_non_static_selection_rate = 0
blind_rows = 0
```

Interpretation:

```text
1. Stage1 has signal.
2. Refinement destroys the signal.
3. The failure mode is not "no information in traces".
4. The failure mode is "manual discrete aliases are too brittle and sparse".
5. Therefore use the solver data to train a continuous generator and safety model.
```

G5.43 also showed:

```text
G5.42 static_flow regressions were static-ladder caused:
  overlay_caused_count = 0
  static_ladder_caused_count = 2
  same_failure_set_p2_p3 = true
```

Therefore do not keep repairing static selectors. Use static baselines only to detect residual-caused regressions.

---

## 2. What to learn from recent successful work

### 2.1 Guidance Graph Optimization for Lifelong MAPF — most directly relevant

Paper: `Guidance Graph Optimization for Lifelong Multi-Agent Path Finding`, IJCAI 2024.  
Repo: `lunjohnzhang/ggo_public`.

Relevant lessons:

```text
1. MAPF guidance can be optimized as continuous edge weights or as an update model.
2. Use a black-box simulator/evaluator loop rather than differentiating through the solver.
3. Keep C++ simulator and Python optimization/model code separated.
4. Maintain full config, seed, reload, metrics, and archive logs.
5. Support local and HPC execution profiles.
6. Use CMA-ES / learned update model (PIU) as optimizer families.
```

What to adopt in czr004:

```text
- Treat LaCAM*+LTM replay as the evaluator.
- Treat UpdateParams theta as the optimizable guidance/update object.
- Add robust logging:
    config.json
    seed
    reload.pkl or resumable JSONL checkpoints
    metrics.json
    parameter_archive.csv
    failed_contexts.csv
    replay_commands.jsonl
- Add local-PC long profile and optional Slurm/HPC profile, but do not require HPC.
```

### 2.2 DIFUSCO — generate multiple candidates, not one point

Paper: `DIFUSCO: Graph-based Diffusion Solvers for Combinatorial Optimization`, NeurIPS 2023.  
Repo: `Edward-Sun/DIFUSCO`.

Relevant lessons:

```text
1. A generative model can produce multiple candidate solutions.
2. Inference schedule and sampling matter; final performance is not one deterministic forward pass.
3. Store pretrained checkpoints and reproducibility scripts.
4. Separate meta-model training/evaluation from problem-specific logic.
```

What to adopt in czr004:

```text
- Generator must output K candidate theta samples per context, not only one theta.
- A risk/utility scorer selects among generated samples.
- Evaluate top-1, top-3, top-8 generated theta candidates.
- Add diversity regularization so all samples do not collapse to static_flow.
- Save model checkpoints, model manifests, and exact replay materialization commands.
```

### 2.3 CL-LNS — collect expert/evaluator data, then train a model

Paper/repo: `Searching Large Neighborhoods for Integer Linear Programs with Contrastive Learning`, ICML 2023, `facebookresearch/CL-LNS`.

Relevant lessons:

```text
1. Collect dataset by running a strong expert/heuristic/evaluator over multiple iterations.
2. Train neural model on solver-collected data.
3. Test by inserting ML heuristic into the solver loop under clear mode flags.
4. Keep ML heuristic prefixes/names explicit in logs.
```

What to adopt in czr004:

```text
- Solver replay rows are not just reports; they are the training dataset.
- Each data row must include:
    context features x
    parameter vector theta
    baseline outcomes
    selected/generated outcome
    success regression labels
    quality delta labels
- Method names must clearly distinguish:
    neural_generator_sample_k
    risk_filtered_neural_generator
    oracle diagnostic
    static baseline
```

### 2.4 Efficient Active Search — per-instance adaptation without updating the whole model

Paper: `Efficient Active Search for Combinatorial Optimization Problems`.

Relevant lessons:

```text
1. Active search adapts model behavior to a single instance.
2. Efficient versions update only a small subset of parameters.
3. This is useful when general model predictions need instance-specific refinement.
```

What to adopt in czr004:

```text
- Do not update the whole generator at test time.
- Optionally adapt a tiny latent vector z or small output head per context using surrogate models.
- The adaptation target is theta, not solver actions.
- Any adapted theta must still pass risk gate and real solver replay before positive claims.
```

### 2.5 TabPFN / modern tabular models — strong surrogates for small/medium solver tables

Paper: `TabPFN: A Transformer That Solves Small Tabular Classification Problems in a Second`, ICLR 2023.  
Repo: `PriorLabs/TabPFN`.

Relevant lessons:

```text
1. Many solver labels are tabular: x, theta -> risk / utility.
2. Strong tabular baselines are often more reliable than a custom deep model early on.
3. Use classifier/regressor baselines before claiming neural architecture novelty.
```

What to adopt in czr004:

```text
- Train several risk/utility surrogate families:
    gradient boosted trees if available
    sklearn MLP / PyTorch MLP
    TabPFN if installed and data size fits
    calibrated logistic risk model
- Do not skip simple baselines.
- Positive generator claims require beating simple surrogate-driven search baselines.
```

### 2.6 FunSearch — evaluator-in-loop search discipline

Paper/repo: `Mathematical discoveries from program search with large language models`, Nature 2023, `google-deepmind/funsearch`.

Relevant lessons:

```text
1. Keep an automated evaluator central.
2. The generator proposes candidates; the evaluator scores them.
3. Archive high-performing candidates and use them to improve later search.
4. Code/reports should separate generated candidates from verified candidates.
```

What to adopt in czr004:

```text
- Maintain a parameter archive.
- Never treat neural output as valid until solver replay verifies it.
- Every G5.45 report must separate:
    generated theta
    risk-filtered theta
    solver-verified theta
    blind-verified theta
```

---

## 3. Feasibility assessment

### 3.1 Feasible aspects

The idea is feasible because czr004 already has a rich continuous parameterization:

```text
alpha_cong_commit_progress
alpha_cong_commit_nonprogress
alpha_cong_block
alpha_cong_wait_progress
alpha_cong_wait_nonprogress
alpha_flow_commit_progress
alpha_flow_wait_progress
rho_cong_decay
rho_flow_decay
lambda_cong
lambda_flow
min_edge_cost
max_edge_cost
goal_projection_mode
flow_shield_beta
max_flow_shield
```

The solver already supports project-owned replay/evaluation, and G5.39-G5.43 already generated many `(context, theta/candidate, outcome)` rows. These should be unified into a reusable dataset.

### 3.2 Main risks

```text
R1. Sparse positive labels:
    Most parameter settings may be equal or unsafe.

R2. Noisy black-box objective:
    Single-seed quality deltas are fragile.

R3. Hard safety:
    success regression is lexicographic and cannot be averaged away.

R4. Feature insufficiency:
    Existing light logs may not include full event arrays; use full checkpoint exporter when needed.

R5. Generator collapse:
    A neural generator may learn static_flow-like parameters only.

R6. Overfitting to seed/map strata:
    Split must be by seed block and map family, not random rows.

R7. Runtime materialization:
    Direct C++ runtime export is not required in G5.45. Generate temporary executable aliases for replay first.
```

### 3.3 Feasibility verdict

```text
Neural continuous UpdateParams generation is plausible and better aligned with the project goal than hand alias sweeping.

But G5.45 must be framed as:
  offline neural generator + surrogate + solver-replay validation

not:
  runtime integration
  Phase5.5 promotion
  AAAI-ready result
```

---

## 4. G5.45 research design

### 4.1 Data schema

Create a canonical dataset:

```text
outputs/tables/phase5p5_repair5g545_param_replay_dataset.csv
```

Each row should include:

```text
context_id
map
map_family
agents
budget_ms
seed
seed_block
iteration_bucket

feature_* columns:
  map topology summary
  obstacle ratio
  degree histogram
  bottleneck/corridor/junction counts if available
  trace committed count
  trace blocked count
  trace wait count
  progress / nonprogress event counts
  blocked reason aggregate counts
  rank audit aggregates
  DualChannelUpdateStats aggregates
  traffic snapshot summary
  previous normalized congestion/flow summary if available

theta_* columns:
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
  theta_goal_projection_mode_onehot

outcome columns:
  selected_success
  baseline_static_flow_success
  baseline_additive_success
  baseline_family_static_success
  selected_ratio
  baseline_static_flow_ratio
  baseline_family_static_ratio
  quality_delta_vs_static_flow
  quality_delta_vs_family_static
  success_regression_vs_static_flow
  success_regression_vs_family_static
  success_regression_vs_additive_if_available
  both_fail flags
  safe_high_margin flags
```

Forbidden model-facing features:

```text
seed as numeric predictor
oracle_best
posthoc winner
quality_delta
success_regression label
baseline outcome labels
candidate_id
method string if it leaks target
```

Allowed only for grouping/evaluation:

```text
seed
candidate_id
method
outcome labels
```

### 4.2 Parameter domain

Use bounded continuous output. This is not a candidate grid; it is the safe output range.

Initial recommended ranges:

```text
theta_alpha_cong_commit_progress      in [0.00, 1.50]
theta_alpha_cong_commit_nonprogress   in [0.50, 1.75]
theta_alpha_cong_block                in [0.50, 2.25]
theta_alpha_cong_wait_progress        in [0.00, 1.25]
theta_alpha_cong_wait_nonprogress     in [0.00, 1.75]
theta_alpha_flow_commit_progress      in [0.00, 1.50]
theta_alpha_flow_wait_progress        in [0.00, 1.25]
theta_rho_cong_decay                  in [0.90, 1.00]
theta_rho_flow_decay                  in [0.90, 1.00]
theta_lambda_cong                     in [0.50, 1.50]
theta_lambda_flow                     in [0.00, 1.50]
theta_flow_shield_beta                in [0.00, 0.80]
theta_max_flow_shield                 in [0.25, 1.50]
theta_min_edge_cost                   in [0.25, 1.00]
theta_max_edge_cost                   in [8.00, 12.00]
theta_goal_projection_mode            in {FlowShield initially; AgentProgress diagnostic only}
```

Network output transform:

```text
theta_i = lo_i + (hi_i - lo_i) * sigmoid(z_i)
```

For categorical `goal_projection_mode`, start with fixed `FlowShield` to reduce search variance. Add categorical prediction only after continuous version shows safety.

### 4.3 Data generation

Do not use only existing hand aliases.

Required stages:

#### Stage A — Consolidate prior data

Harvest all prior solver evidence from G5.39-G5.43:

```text
G5.39 param optimizer rows
G5.40 Stage1/Stage2 rows
G5.41 balanced/refinement/blind rows
G5.42 ladder overlay probe rows
G5.43 Stage1/refinement rows
```

Normalize every executable alias into `theta_*` fields.

#### Stage B — Continuous parameter sampling

Generate new continuous samples using multiple policies:

```text
Sobol / Latin-hypercube broad samples
local perturbations around G5.41/G5.42/G5.43 promising theta
CMA-ES / CEM around true-gain regions
risk-aware negative-control samples
near-static_flow low-amplitude samples
```

Minimum local-PC profile:

```text
contexts >= 1080
theta samples per context >= 16
new_solver_rows >= 30000
distinct theta rows >= 16000
```

Preferred local-PC long profile:

```text
contexts >= 1440
theta samples per context >= 32
new_solver_rows >= 60000
distinct theta rows >= 40000
```

Longer profile if local PC can handle it:

```text
contexts >= 2160
theta samples per context >= 32
new_solver_rows >= 100000
```

### 4.4 Models

Train three model families.

#### 4.4.1 Risk model

```text
R(x, theta) -> calibrated probability of success regression
```

Separate heads:

```text
R_static_flow
R_family_static
R_additive_if_available
R_any_regression
```

Metrics:

```text
harmful recall
harmful precision
AUROC
AUPRC
Brier score
ECE calibration
false-safe count at threshold
```

Gate:

```text
false-safe count must be zero on validation splits at chosen threshold
or generator cannot proceed to solver replay except diagnostic.
```

#### 4.4.2 Utility model

```text
U(x, theta) -> predicted quality improvement if safe
```

Use robust targets:

```text
quality_delta_vs_static_flow
quality_delta_vs_family_static
better_vs_worse classification
safe_high_margin gain
```

Recommended losses:

```text
Huber regression for delta
pairwise ranking loss among theta candidates within same context
quantile regression for pessimistic lower confidence bound
```

#### 4.4.3 Generator

```text
G(x, z) -> K bounded theta samples
```

Start simple:

```text
MLP generator with random latent z
K = 8 samples per context
diversity penalty in theta space
imitation loss toward best safe theta per context
surrogate-guided loss:
  maximize U_LCB(x, theta)
  penalize R_any_regression(x, theta)
  penalize distance outside conservative range
```

Training objective:

```text
L = L_imitation
  + lambda_rank * L_pairwise
  + lambda_risk * max(0, R_any - tau_risk)
  - lambda_utility * U_LCB
  + lambda_diversity * diversity_regularizer
  + lambda_static_collapse * penalty_if_theta_too_close_to_static_flow_for_all_samples
```

Do not require diffusion in G5.45, but leave file structure ready for a later diffusion/CEM generator.

### 4.5 Inference and solver replay

Inference procedure:

```text
for each context:
  generate K theta samples
  score each theta by R and U
  keep theta if:
    R_any <= tau_risk
    U_LCB < 0 or better_prob high
    theta finite and within bounds
  choose top candidate by utility among safe candidates
  if none safe:
    abstain to fixed static_flow_shield
```

Important:

```text
abstain fallback = fixed static_flow_shield only
do not choose among static baselines
```

Materialization:

```text
outputs/tables/phase5p5_repair5g545_generated_theta_candidates.csv
outputs/tables/phase5p5_repair5g545_generated_theta_alias_map.csv
```

Convert generated theta to temporary executable aliases for solver replay. Direct C++ runtime export is optional and not required for G5.45.

---

## 5. Evaluation design

### 5.1 Splits

Use strict splits:

```text
train seeds
validation seeds
targeted fresh seeds
blind fresh seeds
map-family holdout diagnostic if enough data
```

Do not random-split rows from the same seed/context into train and validation.

### 5.2 Baselines

Required baselines:

```text
static_flow_shield
additive_ltm
frozen_family_static_goal_aware
G5.41 best residual
G5.42 high-margin overlay diagnostic
G5.43 best Stage1 true-gain candidates
random continuous theta samples
CMA-ES/CEM best diagnostic theta if available
```

Static selector baseline may be evaluated only as:

```text
static_selector_upper_bound_diagnostic
```

It must never be counted as learned UpdateLTM progress.

### 5.3 Gates

Offline gate:

```text
risk false-safe count = 0 on validation
generator non-static/counterfactual parameter rate >= 0.10
generator does not collapse to static_flow
utility top-k capture > random continuous baseline
```

Targeted solver gate:

```text
new_solver_rows >= 14400 minimum
preferred >= 28800
contexts >= 720
generated theta usage rate >= 0.10
success_regression_vs_static_flow = 0
success_regression_vs_family_static = 0 where paired
success_regression_vs_additive = 0 where paired
quality_only_mean_delta_vs_static_flow < 0
better_count_vs_static_flow >= worse_count_vs_static_flow
```

Blind replay gate only if targeted passes:

```text
blind_rows >= 14400 minimum
preferred >= 28800
fresh seeds only
zero success regression vs static_flow
zero success regression vs family_static where paired
quality delta <= 0
better >= worse or safe_high_margin_count substantial
```

### 5.4 Failure taxonomy

Every failure must be categorized:

```text
model_false_safe
surrogate_utility_miscalibration
generator_static_collapse
theta_out_of_domain
alias_materialization_bug
seed_fragile_gain
feature_insufficient
baseline_conflict_not_residual_caused
true_residual_regression
no_solver_signal
```

---

## 6. Required artifacts

### 6.1 Plan and worklog

```text
czr004_g545_neural_continuous_updateparams_generator_plan.md
docs/codex-worklog.md
```

### 6.2 Scripts

```text
scripts/repair5g545_common.py
scripts/verify_repair5g545_g543_artifacts.py
scripts/write_repair5g545_supersede_g544_note.py
scripts/create_repair5g545_param_replay_dataset.py
scripts/audit_repair5g545_dataset_leakage_and_coverage.py
scripts/create_repair5g545_continuous_param_sampling_plan.py
scripts/run_repair5g545_continuous_param_probe.py
scripts/analyze_repair5g545_continuous_param_evidence.py
scripts/train_eval_repair5g545_risk_utility_surrogates.py
scripts/train_eval_repair5g545_neural_theta_generator.py
scripts/materialize_repair5g545_generated_theta_aliases.py
scripts/run_repair5g545_generated_theta_targeted_replay.py
scripts/analyze_repair5g545_generated_theta_targeted_evidence.py
scripts/run_repair5g545_generated_theta_blind_replay_if_warranted.py
scripts/analyze_repair5g545_blind_evidence.py
scripts/write_repair5g545_decision.py
```

### 6.3 Reports

```text
outputs/reports/phase5p5_repair5g545_g543_verification.md
outputs/reports/phase5p5_repair5g545_g544_superseded_note.md
outputs/reports/phase5p5_repair5g545_dataset_coverage.md
outputs/reports/phase5p5_repair5g545_continuous_sampling_plan.md
outputs/reports/phase5p5_repair5g545_continuous_param_evidence.md
outputs/reports/phase5p5_repair5g545_risk_utility_surrogates.md
outputs/reports/phase5p5_repair5g545_neural_theta_generator.md
outputs/reports/phase5p5_repair5g545_generated_theta_targeted_evidence.md
outputs/reports/phase5p5_repair5g545_blind_evidence.md
outputs/reports/phase5p5_repair5g545_decision.md
```

### 6.4 Tables

```text
outputs/tables/phase5p5_repair5g545_param_replay_dataset.csv
outputs/tables/phase5p5_repair5g545_feature_columns.csv
outputs/tables/phase5p5_repair5g545_theta_columns.csv
outputs/tables/phase5p5_repair5g545_dataset_leakage_audit.csv
outputs/tables/phase5p5_repair5g545_continuous_param_sampling_plan.csv
outputs/tables/phase5p5_repair5g545_continuous_param_probe_results.csv
outputs/tables/phase5p5_repair5g545_risk_model_eval.csv
outputs/tables/phase5p5_repair5g545_utility_model_eval.csv
outputs/tables/phase5p5_repair5g545_generator_eval.csv
outputs/tables/phase5p5_repair5g545_generated_theta_candidates.csv
outputs/tables/phase5p5_repair5g545_generated_theta_alias_map.csv
outputs/tables/phase5p5_repair5g545_targeted_replay_results.csv
outputs/tables/phase5p5_repair5g545_targeted_selected_vs_static_flow.csv
outputs/tables/phase5p5_repair5g545_targeted_selected_vs_family_static.csv
outputs/tables/phase5p5_repair5g545_targeted_failure_cases.csv
```

### 6.5 Models

Only if trained:

```text
artifacts/models/laur_ltm/repair5g545_risk_model.pt
artifacts/models/laur_ltm/repair5g545_utility_model.pt
artifacts/models/laur_ltm/repair5g545_theta_generator.pt
artifacts/models/laur_ltm/repair5g545_model_manifest.json
```

Manifest must include:

```text
training rows
feature columns
theta columns and bounds
splits
random seeds
model architecture
calibration threshold
claim flags closed
```

---

## 7. Guardrails

Do not modify:

```text
external/lacam2/lacam2/**
PIBT conflict semantics
candidate domain
agent actions
agent priorities
h-values
candidate deletion
LaCAM* high-level search
OPEN / EXPLORED / rewrite / incumbent pruning
restart semantics
```

Do not use reserved IDs:

```text
166..205
```

Do not claim:

```text
phase5p5_allowed=true
phase6_allowed=true
runtime_claim_allowed=true
learned_runtime_policy_validated=true
aaai_ready=true
```

All G5.45 outputs must keep:

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

## 8. Stop / continue rules

Stop early with diagnostic decision if:

```text
dataset cannot recover theta for prior aliases
continuous probe has < 30000 rows and cannot proceed
risk model has nonzero false-safe cases at any usable threshold
generator collapses to static_flow-like theta
generated theta cannot be materialized for solver replay
targeted replay has any residual-caused success regression
```

Continue to blind only if:

```text
targeted replay has zero residual-caused success regression
targeted quality delta vs static_flow is nonpositive
generated theta usage rate >= 0.10
better >= worse or safe_high_margin strong
```

---

## 9. Expected final decision options

Use one of these explicit final decisions:

```text
g545_neural_theta_generator_targeted_positive_continue_blind
g545_neural_theta_generator_blind_positive_continue_runtime_design_later
g545_surrogate_safe_but_generator_collapsed_continue_model_design
g545_continuous_probe_no_safe_signal_rethink_param_space
g545_risk_model_false_safe_blocks_generator
g545_generated_theta_targeted_regression_blocks_blind
g545_dataset_or_materialization_blocked_continue_infrastructure
```

Do not use vague decisions like `continue_refinement` without naming the bottleneck.

---

## 10. Short Codex prompt

Continue czr004 after G5.43 commit fca925f on branch codex/g531-slice-pilot. Supersede any current G5.44 static-selector / hand-alias-sweep direction and implement Repair5G.5.45 as a neural bounded continuous UpdateParams generator for static-flow / dual-channel LTM.

G5.43 showed that manual edge/event aliases have Stage1 signal but fail refinement: Stage1 had 12,960 solver rows, 101 aliases, 720 contexts, and 19 safe/useful regions, but refinement had 15,120 rows and 0 final supported regions. It also showed G5.42 static_flow regressions were static-ladder caused, not overlay-caused. Therefore do not keep repairing static selectors and do not treat choosing among additive/static_flow/best_fixed/family_static as learned UpdateLTM progress.

Build a canonical dataset of (context features, continuous UpdateParams theta, solver outcomes) from G5.39-G5.43 plus new continuous parameter probes. Use large solver-evaluated continuous sampling: Sobol/LHS, local perturbations around promising theta, CMA-ES/CEM around true-gain regions, and negative controls. Minimum new continuous probe: >=30,000 solver rows, >=1,080 contexts, >=16 theta samples/context; preferred local-PC long profile: >=60,000 rows, >=1,440 contexts, >=32 theta samples/context.

Train calibrated risk models R(context, theta) for success regression, utility models U(context, theta) for quality delta/ranking, and a generator G(context,z)->K bounded theta samples. The generator outputs continuous UpdateParams fields, not candidate IDs and not static baseline IDs. Use bounded sigmoid transforms for alpha/rho/lambda/flow_shield/cost parameters. At inference, generate K theta samples, risk-filter them, choose by pessimistic utility, or abstain to fixed static_flow_shield. Static baselines are diagnostics only.

Materialize generated theta into temporary executable aliases for targeted solver replay. Run targeted replay only if offline risk calibration has zero false-safe validation cases. Blind replay only if targeted replay has zero success regression vs static_flow and paired family_static/additive baselines, nontrivial generated-theta usage, and nonpositive quality delta. Keep all Phase5.5/Phase6/runtime/AAAI claims closed. Do not touch external/lacam2/lacam2 and do not use reserved IDs 166..205.

Final decision must identify the bottleneck precisely: dataset/materialization, risk false-safe, generator collapse, no continuous safe signal, targeted regression, or blind positive.
