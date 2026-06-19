# Repair5G.5.60 Plan — Identity-Safe Label-v5.1 Recovery, Valid-Instance Repair, and Real GCST Critic Training

Project: `czr004`
Repository: `czr5454112-glitch/czr004`
Required branch: `server-code`
Start commit: `6c9de29909535df138e7b7dd0a6a4fce29024689`
Primary promotion baseline: `g556_c063174`
Round name: `Repair5G.5.60 evidence-integrity repair and real graph-conditioned static-theta learning`

---

## 0. Executive decision

G5.60 continues the same scientific direction:

```text
physical MAPF map
+ actual paired starts/goals
+ complete agent/goal distributions
+ goal-aware C0/F0 traffic priors
+ solver budget
    -> neural graph/traffic encoder
    -> one bounded dual-channel UpdateParams theta
    -> theta stays fixed for the complete solver run
```

This is:

```text
instance-conditioned
run-static
trace-updated
```

It is not:

```text
one universal theta for all instances
checkpoint-conditioned theta
runtime dynamic learned UpdateLTM
MAPF action policy
priority/restart policy
```

G5.59 generated the first large real-solver Label-v5 pilot:

```text
130,000 real solver rows
128,000 candidate-vs-g556 pair rows
2,000 evaluation contexts
24 physical map hashes
8 map families
```

Those rows are scientifically valuable and must be recovered before launching another full solver sweep.

The G5.59 decision is not evidence that GCST cannot learn. Three implementation failures prevented the learnability experiment:

```text
1. the legacy solver runner overwrote the SHA-256 instance_uid with a
   context_horizon_key-style string, so pair rows did not join to the
   instance/graph feature manifest;

2. train_repair5g559_codebook_critic.py and
   train_repair5g559_continuous_generator.py both call
   main_eval_real_learnability instead of a training function;

3. main_run_all never trains the graph-conditioned critic or generator, and
   Stage1/Stage2/blind are unconditional skip stubs.
```

G5.60 must first repair evidence identity, validate scenarios, train a real codebook critic, and evaluate it on held-out physical maps. Only then may it run targeted top-up, continuous generation, or solver Stage1.

---

## 1. Required interpretation of G5.59

Write a source-of-truth audit from commit:

```text
6c9de29909535df138e7b7dd0a6a4fce29024689
```

Required inputs:

```text
scripts/repair5g559_pipeline.py
scripts/train_repair5g559_codebook_critic.py
scripts/train_repair5g559_continuous_generator.py
scripts/pretrain_repair5g559_instance_encoder.py
scripts/run_repair5g559_active_round.py
src/gcst/label_v5.py
src/gcst/scenario_features.py
src/gcst/traffic_prior.py
tests/test_repair5g559_gcst.py

outputs/reports/phase5p5_repair5g559_*summary.json
outputs/tables/phase5p5_repair5g559_instance_manifest.csv
outputs/tables/phase5p5_repair5g559_labelv5_pair_rows.csv
outputs/tables/phase5p5_repair5g559_labelv5_safe_sets.csv
outputs/tables/phase5p5_repair5g559_real_learnability_split_manifest.csv
```

### 1.1 What succeeded

Record without qualification:

```text
real solver materialization succeeded
real pair outcomes exist
24 physical map hashes exist
full graph connectivity repair exists
per-graph attention repair exists
real C0/F0 flow computation exists
artifact/checksum infrastructure exists
```

### 1.2 What did not run

Record:

```text
real GCST codebook critic trained = false
real continuous theta generator trained = false
self-supervised instance pretraining executed = false
active Label-v5 acquisition executed = false
Stage1 solver policy replay executed = false
Stage2 solver replay executed = false
blind replay executed = false
```

Evidence:

```text
train_repair5g559_codebook_critic.py
  imports main_eval_real_learnability

train_repair5g559_continuous_generator.py
  imports main_eval_real_learnability

pretrain_repair5g559_instance_encoder.py
  imports main_synthetic_contract

run_repair5g559_active_round.py
  imports main_plan_active_round
```

The synthetic contract also constructed scores directly from labels; it did not train the model.

### 1.3 Identity-chain failure

The instance manifest uses a SHA-256 `instance_uid`.

The committed pair rows instead contain legacy keys such as:

```text
random-8-8-20|32|7075|5000|g559_b5000_i2
```

The learnability join uses exact `instance_uid`, so 128,000 pair rows join to zero instance features.

This explains:

```text
heldout_examples = 0
all controls unavailable
main model unavailable
```

### 1.4 Hidden validity/gate failures

Audit these additional issues:

```text
instance manifest rows = 2,000
unique SHA instance_uids = 1,762
pilot minimum unique instance_uids = 2,000
path_found_rate_min = 0.84375
```

Yet the pipeline continued because the plan/pilot gate checked row count rather than valid unique SHA instances.

The current `_sample` function cycles through region cells when requested agents exceed region capacity:

```python
return [cells[i % len(cells)] for i in range(count)]
```

This can create duplicate start or goal vertices and repeated scenario assignments.

### 1.5 Label aggregation defects

Audit:

```text
grouped[(uid, candidate_id)] = row
```

This overwrites repeated evaluation rows instead of retaining replicates.

Future baseline pairing must be by:

```text
(instance_uid, evaluation_uid)
```

not by `instance_uid` alone.

Classify outcomes lexicographically:

```text
baseline success + candidate fail = unsafe regression
candidate success + baseline fail = success gain
both success + finite quality = comparable quality label
both fail = non-evaluable, not a safe-improving target
invalid materialization = unsafe/invalid
```

Do not include NaN-quality both-fail rows in soft safe-utility targets.

Write:

```text
outputs/reports/phase5p5_repair5g560_g559_truth_audit.md
outputs/reports/phase5p5_repair5g560_g559_truth_audit_summary.json
outputs/tables/phase5p5_repair5g560_stage_implementation_audit.csv
outputs/tables/phase5p5_repair5g560_identity_failure_audit.csv
outputs/tables/phase5p5_repair5g560_scenario_validity_pre_audit.csv
outputs/tables/phase5p5_repair5g560_training_entrypoint_audit.csv
```

---

## 2. Do not rerun the 130,000 solver rows first

The first G5.60 activity is lossless data recovery.

### 2.1 Deterministic legacy-key crosswalk

For every instance-manifest row, reconstruct:

```text
legacy_context_key =
  map
  + "|" + agent_count
  + "|" + solver_seed
  + "|" + nominal_budget_ms
  + "|" + horizon_id
```

This should match the legacy string stored in the pair-row `instance_uid`.

Build:

```text
legacy_context_key
  -> sha256_instance_uid
  -> sha256_evaluation_uid
  -> physical_map_sha256
  -> start_goal_assignment_sha256
  -> context_id
  -> graph/traffic feature URIs
```

Required audits:

```text
legacy key uniqueness
pair-row join rate
baseline/candidate evaluation consistency
candidate theta integrity
row-count preservation
duplicate pair-key count
```

### 2.2 Fallback recovery sources

Use recovery sources in this order:

```text
1. remote raw result CSV + 144 MB pilot plan sidecar;
2. committed pair rows + committed instance manifest crosswalk;
3. command JSONL / run JSONL / scenario manifest;
4. rerun only irrecoverable rows.
```

Never rerun all 130,000 rows merely because the generic UID field was overwritten.

### 2.3 Namespaced immutable identity

Do not send generic identity names through the legacy runner.

Use:

```text
g560_plan_row_uid
g560_instance_uid
g560_evaluation_uid
g560_physical_map_sha256
g560_start_goal_assignment_sha256
g560_solver_scenario_sha256
g560_identity_digest
```

After solver execution, restore scientific identity from the immutable plan sidecar keyed by `g560_plan_row_uid`.

The legacy runner's `instance_uid` and `context_horizon_key` remain diagnostic fields only.

### 2.4 Identity digest

Define:

```text
g560_identity_digest = SHA256(
  plan_row_uid,
  instance_uid,
  evaluation_uid,
  theta_id,
  physical_map_sha256,
  start_goal_assignment_sha256,
  solver_scenario_sha256
)
```

Verify the digest at:

```text
plan creation
raw solver output enrichment
pair construction
training dataset load
```

### 2.5 Required recovery gate

Before any model training:

```text
pair_row_count_before = 128,000
pair_row_count_after = 128,000, unless explicitly invalid rows are quarantined
identity_join_rate = 1.0
physical_map_join_rate = 1.0
scenario_join_rate = 1.0
theta_join_rate = 1.0
evaluation_uid_nonempty_rate = 1.0
baseline_pair_same_evaluation_rate = 1.0
identity_digest_match_rate = 1.0
ambiguous_legacy_key_count = 0
```

Write recovered data as:

```text
Label-v5.1
```

Outputs:

```text
outputs/reports/phase5p5_repair5g560_labelv51_recovery.md
outputs/reports/phase5p5_repair5g560_labelv51_recovery_summary.json
outputs/tables/phase5p5_repair5g560_identity_crosswalk.csv
outputs/tables/phase5p5_repair5g560_labelv51_join_audit.csv
outputs/tables/phase5p5_repair5g560_labelv51_quarantine.csv
```

Large recovered rows go to shared NVMe as partitioned Parquet.

---

## 3. Scenario validity and effective sample size

Do not equate 2,000 evaluation rows with 2,000 valid unique instances.

### 3.1 Parse actual scenario files

For every scenario:

```text
all starts are traversable
all goals are traversable
start vertices are unique
goal vertices are unique
agent count matches scenario row count
every paired start-goal path is reachable
scenario SHA matches manifest
map SHA matches manifest
```

Required rates:

```text
unique_start_rate = 1.0
unique_goal_rate = 1.0
path_found_rate = 1.0
scenario_hash_match_rate = 1.0
map_hash_match_rate = 1.0
```

Invalid scenarios are quarantined. Their solver outcomes may remain diagnostic but cannot train the main model.

### 3.2 Repair assignment generation

Replace cyclic repeated sampling with weighted sampling without replacement.

For clustered regimes:

```text
prefer target region
expand progressively to neighboring regions when region capacity is insufficient
never duplicate starts
never duplicate goals
sample only from one connected component
```

Select the largest connected component before scenario generation.

### 3.3 Treat duplicate instance UIDs correctly

If two evaluations have the same SHA instance UID but different solver seeds:

```text
they are replicates
```

Do not count them as distinct instances.

If they have duplicate/invalid start-goal vertices:

```text
they are invalid and must be regenerated
```

### 3.4 Top-up rule

After recovery and filtering:

```text
minimum valid unique instance_uids = 2,000
preferred pilot valid unique instance_uids = 3,000
minimum heldout physical map hashes = 4
minimum validation physical map hashes = 4
```

Only generate additional solver rows needed to:

```text
replace invalid contexts
reach unique-instance minimum
add missing heldout-map support
add replicate confirmation
```

Do not repeat valid rows.

---

## 4. Versioned schema contracts

Create explicit dataclasses or Pydantic/Arrow schemas:

```text
G560PlanRow
G560RawSolverRow
G560PairedOutcomeRow
G560InstanceFeatureRow
G560GroupedTrainingExample
G560PolicyExecutionRow
```

Each schema contains:

```text
schema_version
required fields
types
identity fields
provenance fields
allowed null fields
semantic validators
```

### 4.1 Canary before scale

Before any solver top-up, run:

```text
3 physical maps
2 instances per map
baseline + 3 theta candidates
```

Required end-to-end result:

```text
24 plan rows
24 raw result rows
18 candidate pair rows
100% identity roundtrip
100% baseline pairing
100% graph/traffic join
```

The canary must use the real solver runner and real enrichment path.

### 4.2 Wrapper and stage audit

Use Python AST inspection to verify:

```text
train_*.py calls an actual training function
pretrain_*.py calls actual pretraining
run_active_round.py calls an execution function
run_stage1.py calls a solver runner
run_stage2.py calls a solver runner
run_blind.py calls a solver runner
```

A wrapper calling an evaluator or planner instead of a trainer/runner fails CI.

### 4.3 Anti-stub gate

Training stage must produce:

```text
checkpoint
optimizer state
optimizer_step_count > 0
nonzero gradients
training curves
validation curves
model config
checkpoint hash
```

Solver execution stage must produce:

```text
planned_solver_rows > 0
actual_solver_rows > 0
paired rows > 0
```

A function that only writes a skip summary is not implemented.

---

## 5. Label-v5.1 semantics

### 5.1 Exact pairing key

Pair candidate and baseline by:

```text
(g560_instance_uid, g560_evaluation_uid)
```

Each candidate must share with its baseline:

```text
map
scenario SHA
solver RNG seed
budget
LTM iteration budget
```

### 5.2 Replicate aggregation

Group by:

```text
(instance_uid, theta_id)
```

but preserve all evaluation rows.

Report:

```text
replicate_count
success_regression_count
success_gain_count
both_success_count
both_fail_count
quality_delta_mean
quality_delta_median
quality_delta_CI
worst_replicate_delta
```

### 5.3 Safe-set rules

Development safe:

```text
no observed success regression
valid materialization
at least one evaluable outcome
```

Promotion safe:

```text
zero success regression across required fresh replicates
```

Do not treat both-fail-only candidates as safe improving.

### 5.4 Comparable ranking pairs

Create ranking preferences only when:

```text
one candidate is unsafe and the other safe;
one is success-gain and the other is not;
both succeed and finite quality difference exceeds noise margin;
or replicate confidence supports the ordering.
```

Treat near-ties as ties.

### 5.5 Add baseline pseudo-candidate

For each instance, add `g556_c063174` as:

```text
quality_delta = 0
success_regression = false
fallback candidate = true
```

This makes fallback an explicit ranked action.

---

## 6. Oracle-opportunity and candidate-space audit before neural training

The first scientific analysis after identity recovery is not model training.

Compute real per-instance oracle over the evaluated slate:

```text
fraction with safe improvement
mean oracle quality gain
oracle success gains
oracle success regressions
oracle by physical map
oracle by map family
oracle by density
oracle by budget
oracle by start-goal regime
```

### 6.1 Interpret the result

If safe oracle opportunity is weak:

```text
the candidate slate is the blocker
```

If oracle opportunity is strong but controls fail:

```text
features or labels are the blocker
```

If simple density lookup is strong:

```text
density is a real explanatory variable and a strong teacher/control
```

### 6.2 Audit the G5.59 codebook

The current codebook is Gaussian perturbation but is labeled `sobol_like_trust_region`.

Correct the naming and report:

```text
normalized distance from g556
field-bound saturation rate
per-field variance
candidate support count
candidate regression rate
candidate improvement rate
```

Build an improved codebook containing:

```text
g556 baseline
G5.54–G5.56 elites and near-misses
true Sobol/Latin-hypercube residuals
small trust-region shells
field-group perturbations
C-only / F-only diagnostics
goal-mode diagnostics
CMA-ES/CEM elites
hard-negative boundary candidates
```

Do not launch a new large solver sweep until the real oracle audit says additional candidate diversity is needed.

---

## 7. Train the real codebook critic first

The continuous generator remains closed until codebook selection works.

### 7.1 Task

```text
(instance graph/traffic representation, candidate theta)
    -> regression risk
    -> success-gain probability
    -> finite quality delta distribution
    -> uncertainty
```

At inference:

```text
score candidate codebook
select the calibrated best safe theta
or use g556
```

### 7.2 Instance representation

Use:

```text
full or connectivity-preserving graph
actual paired start-goal information
full-agent start/goal density fields
real C0 congestion/conflict prior
real F0 directed goal-progress prior
physical density
budget token
```

The model must not use:

```text
map ID
candidate ID
solver seed
posthoc outcomes
```

### 7.3 Model-size sweep

The number of independent pilot instances is much smaller than the row count.

Train at least:

```text
Small GCST critic: hidden 96–128, approximately 0.5–1.5M parameters
Medium GCST critic: hidden 160–192, approximately 2–4M parameters
Large GCST critic: hidden 256, approximately 5–7M parameters
```

A smaller model may generalize better on 2–3K independent instances.

### 7.4 Grouped training batches

Every batch must contain complete or sampled candidate groups from the same instances:

```text
B instances × K candidates
```

Suggested:

```text
8–32 instances per batch
8–32 candidates per instance
balanced safe/unsafe/hard-negative sampling
```

Do not train only with independent random rows.

### 7.5 Loss

Use:

```text
asymmetric focal BCE for success regression
BCE for success gain
quality regression only on both-success finite rows
quantile loss
pairwise margin ranking
listwise safe-utility KL/ListNet
hard-negative margin
calibration loss
```

Do not regress quality for both-fail or non-comparable rows.

### 7.6 Real training entrypoint

Implement:

```text
main_train_g560_codebook_critic
```

It must save:

```text
artifacts/models/gcst/g560_codebook_critic_<seed>.pt
```

and include:

```text
model state
optimizer state
scheduler state
step
best validation metric
feature schema
split hashes
source dataset hashes
```

### 7.7 Training protocol

On RTX5090:

```text
bf16 mixed precision
gradient accumulation if necessary
checkpoint/resume
minimum 20,000 optimizer steps before early stop
target 50,000–150,000 optimizer steps
3 model seeds for final comparison
```

Log each loss component separately.

---

## 8. Physical-map evaluation

With only 24 pilot maps, a single hash split is unstable.

Use:

```text
5-fold grouped cross-validation by physical_map_sha256
```

and additionally freeze:

```text
one final heldout-map panel
```

Stratify folds across map families where possible.

Report:

```text
mean across folds
standard deviation
worst physical map
worst map family
density-bin performance
budget performance
```

No physical map hash may occur in two splits.

---

## 9. Real controls

Implement independently on the identical Label-v5.1 folds:

```text
always g556
agent-density lookup
map-family lookup diagnostic
ridge/linear
real LightGBM/XGBoost/CatBoost if installed
fallback sklearn HistGradientBoosting if not
tabular MLP
Set Transformer over OD tokens without graph adjacency
raster CNN over map/start/goal/C0/F0 channels
graph critic without traffic
graph critic without paired goals
full GCST critic
```

The main scientific question at this stage is:

```text
Does graph + paired goals + traffic beat density and tabular summaries?
```

---

## 10. Metrics must be prediction-derived

No hard-coded or identity metrics.

Critic metrics:

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
selected-policy quality delta
oracle regret
coverage-risk curve
```

Fallback metrics must compare model fallback predictions against real labels.

Coverage-risk must be recomputed from actual model scores.

---

## 11. Layered learnability gates

### 11.1 Data-integrity gate

Requires:

```text
100% identity join
valid scenario rate = 1
valid graph/traffic join = 1
heldout-map examples > 0
real solver labels only
```

### 11.2 Critic learnability gate

Requires averaged heldout-map evidence:

```text
main critic available
beats density lookup
beats strongest GBDT
beats tabular MLP
nonfallback coverage >= 5%
selected mean quality delta < 0
useful calibrated risk operating point
graph+goal+traffic beats ablations
```

This gate may tolerate small observed regression because it is a research gate.

### 11.3 Continuous generator gate

Only opens after critic learnability passes.

### 11.4 Final promotion gate

Remains strict:

```text
zero fresh solver success regressions vs g556
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

## 12. Required failure exploration matrix

Do not stop after a single critic configuration fails.

If the main critic does not pass, run at least these diagnoses.

### Branch A — label diagnosis

```text
oracle opportunity
label noise by budget
short/full budget rank transfer
tie margin sweep
both-fail filtering
replicate consistency
```

### Branch B — feature diagnosis

```text
density only
graph only
goal distribution only
traffic only
graph + goals
graph + traffic
full graph + goals + traffic
```

### Branch C — model/loss diagnosis

```text
small/medium/large model
quality regression only
pairwise ranking
listwise ranking
risk + ranking joint
with/without pretraining
```

### Branch D — candidate-space diagnosis

```text
near-g556 trust region
existing G5.56 elites
wide codebook
C/F field-group candidates
CMA-ES/CEM teacher candidates
```

Write a failure attribution table rather than only a final gate boolean.

---

## 13. Actual self-supervised pretraining

`pretrain_repair5g559_instance_encoder.py` did not pretrain.

Implement real pretraining on 20,000–100,000 unlabeled valid instances:

```text
masked node-feature reconstruction
masked C0/F0 edge-flow reconstruction
OD distance histogram prediction
start-goal pairing contrast
bottleneck-demand quantiles
graph augmentation consistency
```

Save a real checkpoint and compare:

```text
scratch
pretrained frozen encoder
pretrained fine-tuned encoder
```

Pretraining is optional for the first repaired critic baseline, but required as an ablation if scratch underperforms.

---

## 14. Continuous generator only after critic success

Train:

```text
instance -> K bounded residual theta proposals
```

with:

```text
safe-set cluster representatives
best-of-K set matching
listwise safe utility
critic-guided utility
per-instance proposal diversity
fallback classification
```

Do not train to one oracle theta.

The trained critic scores generated proposals.

---

## 15. Targeted top-up and active learning

After critic evaluation, add only informative real labels.

Acquisition:

```text
critic/control disagreement
high uncertainty
predicted high utility
hard-negative boundary
underrepresented maps/densities/budgets
generator/critic disagreement
```

### 15.1 First top-up

Recommended:

```text
replace invalid scenarios
top up to 3,000 valid unique instances
add 2–3 evaluation seeds for selected hard cases
evaluate 16–32 targeted candidates per instance
```

Expected new rows are far below a full 130K rerun.

### 15.2 Scale-up after signal

If heldout-map learnability passes:

```text
valid unique instances >= 10,000
physical map hashes >= 48
real pair rows >= 500,000
```

Preferred AAAI-development scale:

```text
valid unique instances 30,000–60,000
physical map hashes >= 80
real pair rows 1.5M–4M
```

Count independent instances separately from pair rows.

---

## 16. Implement real Stage1/Stage2/blind runners

Current G5.59 stage functions only write skip summaries.

G5.60 must implement:

```text
create policy execution plan
materialize predicted theta per instance
run g556 baseline and selected theta with same evaluation UID
pair outcomes
analyze by map/density/budget
```

### Diagnostic Stage1

```text
minimum 200,000 fresh paired rows
preferred 400,000
multiple calibrated coverage thresholds
```

### Stage2

```text
minimum 600,000 fresh rows
heldout physical maps
```

### Blind

```text
minimum 720,000 fresh rows
new physical map hashes
no tuning after freeze
```

Stage1 may be diagnostic. Stage2 and blind remain gated.

---

## 17. Code quality and anti-regression tests

Required tests:

```text
test_legacy_uid_crosswalk_unique
test_labelv51_join_rate_100_percent
test_baseline_candidate_same_evaluation_uid
test_identity_digest_roundtrip
test_canary_solver_identity_roundtrip
test_unique_starts
test_unique_goals
test_all_pairs_reachable
test_no_duplicate_valid_instance_count_inflation
test_train_critic_wrapper_calls_trainer
test_train_generator_wrapper_calls_trainer
test_pretrain_wrapper_calls_pretrainer
test_active_runner_calls_executor
test_stage1_runner_not_stub
test_stage2_runner_not_stub
test_blind_runner_not_stub
test_training_script_writes_checkpoint
test_grouped_candidate_batch
test_quality_loss_masks_noncomparable_rows
test_both_fail_not_safe_improving
test_replicates_not_overwritten
test_physical_map_group_split
test_candidate_id_not_feature
test_solver_seed_not_feature
test_theta_fixed_for_full_run
test_reserved_ids_166_205_rejected
```

Use AST/static tests plus an end-to-end canary.

---

## 18. Stage state machine

Create a versioned state file:

```text
outputs/reports/phase5p5_repair5g560_state.json
```

Stages:

```text
truth_audit
identity_recovery
scenario_validation
labelv51_ready
oracle_audit
critic_controls
critic_training
critic_evaluation
targeted_topup
generator_training
policy_freeze
stage1
stage2
blind
decision
```

Each stage records:

```text
status
input hashes
output hashes
row counts
gate result
producer command
source commit
```

A downstream stage cannot run on stale hashes.

---

## 19. Artifact durability

Use:

```text
/root/shared-nvme/czr004_g560_remote_artifacts
/root/shared-nvme/tmp
```

Partition:

```text
identity_crosswalk/
valid_instances/
labelv51/
graph_features/
traffic_features/
checkpoints/
model_predictions/
solver_topup/
stage1/
stage2/
blind/
```

Raw Label-v5 and Label-v5.1 must have two verified copies before cleanup.

Maintain:

```text
artifact_registry.json
SHA256
row count
schema version
producer command
source commit
```

---

## 20. Required files

Recommended modular structure:

```text
src/gcst/
  schemas_v51.py
  identity_recovery.py
  scenario_validation.py
  grouped_dataset.py
  real_critic_training.py
  real_critic_eval.py
  pretraining.py
  continuous_generator_training.py
  solver_policy_replay.py
  stage_state.py

scripts/
  audit_repair5g560_g559_truth.py
  recover_repair5g560_labelv51.py
  validate_repair5g560_scenarios.py
  run_repair5g560_identity_canary.py
  analyze_repair5g560_oracle_gap.py
  pretrain_repair5g560_instance_encoder.py
  train_repair5g560_codebook_critic.py
  eval_repair5g560_codebook_critic.py
  plan_repair5g560_targeted_topup.py
  run_repair5g560_targeted_topup.py
  train_repair5g560_continuous_generator.py
  freeze_repair5g560_policy.py
  run_repair5g560_stage1.py
  run_repair5g560_stage2.py
  run_repair5g560_blind.py
  write_repair5g560_decision.py
```

Do not put the entire round into another monolithic pipeline file.

---

## 21. Server execution strategy

Run on the RTX5090 server under tmux.

### Phase 0 — no new solver replay

```text
audit code
recover identity
validate scenarios
rebuild Label-v5.1
compute oracle opportunity
train controls
train real critic
run grouped heldout-map evaluation
```

### Phase 1 — targeted solver top-up

Only if needed for:

```text
invalid scenarios
missing unique instances
replicate confirmation
candidate-space gaps
hard negatives
```

### Phase 2 — continuous generator and Stage1

Only if the critic demonstrates real heldout-map signal.

This ordering prevents another large solver run from being wasted by a schema or training-entrypoint bug.

---

## 22. Literature/code lessons to retain

Audit official implementations:

```text
GGO:
  https://github.com/lunjohnzhang/ggo_public

LaGAT:
  https://github.com/proroklab/lagat

MAPF-GPT:
  https://github.com/CognitiveAISystems/MAPF-GPT

ML-MAPF-with-Search:
  https://github.com/Rishi-V/ML-MAPF-with-Search
```

Adopt:

```text
GGO:
  solver-facing simulation and strong black-box controls

LaGAT:
  real edge-aware attention, pretrain/fine-tune, hybrid safeguards

MAPF-GPT:
  streaming datasets, explicit train/validation splits, reproducible configs

CS-PIBT:
  strong fallback/shield and architecture-task alignment
```

Do not copy action-policy targets or modify LaCAM*/PIBT semantics.

---

## 23. Claim policy

Keep closed:

```text
phase5p5_allowed = false
phase6_allowed = false
runtime_claim_allowed = false
learned_runtime_policy_validated = false
aaai_ready = false
```

A critic learnability pass is not a runtime claim.

A diagnostic Stage1 pass is not a paper claim.

Only fresh solver promotion evidence can replace `g556_c063174`.

---

## 24. Decision labels

```text
g560_g559_identity_bug_confirmed
g560_labelv51_recovery_failed
g560_labelv51_recovered_without_full_rerun
g560_scenario_validity_failed_topup_required
g560_real_oracle_gap_absent_candidate_space_repair
g560_controls_show_context_signal
g560_real_gcst_critic_failed_continue_attribution
g560_real_gcst_critic_heldout_passed
g560_targeted_topup_completed
g560_continuous_generator_failed_keep_codebook_route
g560_continuous_generator_heldout_passed
g560_stage1_failed_keep_g556
g560_stage2_failed_keep_g556
g560_blind_failed_keep_g556
g560_graph_conditioned_static_theta_blind_passed_keep_claims_closed
```

---

## 25. Minimum substantive completion

G5.60 is not complete after writing scripts, recovering joins, or running tests.

Minimum substantive completion:

```text
1. recover or explicitly quarantine all 128,000 real pair rows;
2. achieve 100% identity join for retained rows;
3. complete actual scenario-validity audit;
4. produce a real heldout physical-map split;
5. train a real GCST codebook critic checkpoint;
6. evaluate density, GBDT, MLP, and GCST on identical folds;
7. write oracle-gap and failure-attribution reports;
8. if the critic passes, continue through targeted top-up and continuous generator;
9. if it fails, complete the predefined label/feature/model/candidate-space branches.
```

---

## 26. Main scientific question

G5.60 must answer:

```text
After repairing the real Label-v5 identity chain and training the model that
G5.59 never trained, do physical topology, paired goals, and dual-traffic priors
contain enough information to choose a per-instance static UpdateLTM theta that
beats density/tabular controls and improves over g556_c063174?
```

Do not answer this question from row count, wrapper names, synthetic contracts, or missing checkpoints.
