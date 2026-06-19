# G5.60 Mandatory Addendum — Direct Continuous GCST Generator, No Selector Deployment

Project: `czr004`
Repository: `czr5454112-glitch/czr004`
Branch: `server-code`
Start commit: `6c9de29909535df138e7b7dd0a6a4fce29024689`
Applies to: `czr004_g560_identity_safe_labelv51_real_gcst_training_plan.md`

---

## 0. This addendum overrides the route ordering in the original G5.60 plan

The main scientific method must be a **direct continuous parameter generator**:

```text
MAPF instance
  = physical map graph
  + actual paired starts/goals
  + complete agent distribution
  + goal-aware C0/F0 traffic priors
  + solver budget
        ↓
neural graph/traffic model
        ↓
one continuous bounded dual-channel UpdateParams theta
        ↓
theta is frozen for the entire solver run
```

The final deployed method must not be:

```text
a codebook selector
a candidate-ID classifier
a nearest-neighbor theta retriever
a map-ID lookup
an agent-density lookup
a contextual table
a fixed candidate enumerator
```

The codebook critic remains legal only as:

```text
a diagnostic control
a training-time auxiliary critic
a label-quality analysis tool
a hard-negative mining tool
```

It is not a prerequisite promotion route and is not the final candidate object.

---

## 1. Exact final inference contract

For one MAPF instance `x`, the primary model performs exactly one deterministic inference:

```text
theta_hat = DirectGCST(x)
```

Recommended bounded residual form:

```text
delta_raw = Generator(InstanceEncoder(x))

trust = sigmoid(trust_head(x))              # scalar or field-wise continuous shrinkage
delta = trust * field_scale * tanh(delta_raw)

theta_hat = project_to_valid_bounds(
    theta_g556_c063174 + delta
)
```

Properties:

```text
one network forward pass
one continuous theta vector
one theta per instance
theta fixed throughout the solver run
no checkpoint-dependent change
no runtime trace used before prediction
no candidate enumeration at inference
no codebook loaded at inference
no discrete fallback action
```

`trust=0` may continuously shrink the residual back to `g556_c063174`, but this is still one continuous neural output. It is not a selector or abstention policy.

The model may also predict goal-projection-mode logits. The selected mode is part of the generated theta.

---

## 2. Hard anti-selector requirements

The frozen primary inference artifact must pass all of these checks:

```text
inference_reads_theta_codebook = false
inference_reads_candidate_id = false
candidate_id_used_as_feature = false
inference_runs_nearest_neighbor = false
inference_enumerates_historical_theta = false
inference_calls_CMA_ES_or_CEM = false
inference_uses_map_id_lookup = false
inference_uses_agent_density_lookup = false
inference_loads_auxiliary_critic = false
```

The final export should contain only:

```text
instance encoder weights
continuous theta generator weights
feature normalization/configuration
theta bounds and g556 anchor
```

It must not contain:

```text
theta_codebook.csv
candidate leaderboard
candidate-ID embeddings
selector table
critic checkpoint
retrieval memory
```

The auxiliary critic can exist in training artifacts but must not be required by the primary inference command.

---

## 3. Why an auxiliary critic is still allowed

The real solver is non-differentiable:

```text
theta
 -> LaCAM*/LTM search trajectory
 -> success/failure
 -> solution quality
```

A continuous generator cannot receive gradients directly through the solver.

Therefore G5.60 may jointly train:

```text
Actor:
  instance -> continuous theta

Auxiliary critic:
  instance + theta -> risk / gain / quality
```

But the role distinction is mandatory:

```text
actor = final method
critic = training-time differentiable surrogate only
```

The critic must not become:

```text
a final codebook selector
a learned SafeGate claim
a runtime policy
an inference dependency
```

At deployment:

```text
use actor only
```

At training:

```text
use real Label-v5.1 safe sets
+ observed solver outcomes
+ auxiliary critic gradients
```

---

## 4. Revised G5.60 execution sequence

### Phase A — repair the real evidence chain

Before neural training:

```text
recover all retained Label-v5 rows into Label-v5.1
restore SHA instance/evaluation identity
validate real scenarios
preserve replicates
create physical-map-heldout folds
clean both-fail and non-comparable outcomes
compute real safe sets and oracle opportunity
```

Do not rerun all 130,000 solver rows unless recovery proves impossible.

Required retained-row gates:

```text
identity join rate = 1.0
graph join rate = 1.0
traffic join rate = 1.0
scenario join rate = 1.0
theta join rate = 1.0
baseline same-evaluation pairing rate = 1.0
```

### Phase B — direct continuous generator baseline

Immediately train a direct generator from the recovered real labels.

Do not require a completed selector experiment first.

Primary baseline architecture:

```text
DualTraffic graph/traffic encoder
+ paired-OD encoder
+ budget encoder
+ direct bounded residual theta head
```

Primary output:

```text
one continuous theta
```

### Phase C — joint actor/critic refinement

Train an auxiliary critic on real `(instance, theta, solver outcome)` rows and refine the actor conservatively.

The actor remains the primary method throughout.

### Phase D — controls and ablations

Train selector/lookup methods only as controls:

```text
always g556
agent-density lookup
GBDT
tabular MLP
neural codebook selector diagnostic
direct continuous generator without critic
direct continuous generator with auxiliary critic
```

### Phase E — generated-theta solver replay

Run real solver replay on theta generated directly by the actor.

No candidate ID may be materialized for the actor output. Assign a generated-instance hash instead:

```text
generated_theta_uid = SHA256(model_checkpoint, instance_uid, theta_values)
```

---

## 5. Direct generator training labels

The recovered Label-v5.1 data provides, for every instance:

```text
observed safe theta set
safe-improving theta set
Pareto theta set
quality ranking
success-regression labels
success-gain labels
fallback-required / no-safe-improvement status
```

Do not collapse these labels to one arithmetic-average oracle theta.

### 5.1 Set-to-point mode-seeking loss

The actor produces one theta:

```text
theta_hat(x)
```

For instances with a safe-improving set `S(x)`, use a soft minimum over safe Pareto modes:

```text
L_safe_set =
  -tau * log sum_{theta_j in S(x)}
      w_j * exp(-d(theta_hat, theta_j) / tau)
```

This is mode-seeking and avoids averaging distant safe solutions.

Weights `w_j` should reflect:

```text
real quality delta
success gain
replicate confidence
distance from unsafe boundary
```

### 5.2 No-safe-improvement contexts

For contexts with no observed safe improvement:

```text
L_anchor = d(theta_hat, theta_g556)
```

The actor learns to return a near-zero residual, not a discrete fallback action.

### 5.3 Auxiliary critic-guided objective

Train the critic to predict:

```text
p_success_regression
p_success_gain
expected quality delta
quality quantiles
uncertainty
```

Actor refinement:

```text
L_actor_critic =
    lambda_risk * predicted_regression_risk(theta_hat)
  + lambda_quality * predicted_quality_delta(theta_hat)
  - lambda_gain * predicted_success_gain(theta_hat)
```

Use conservative penalties so the actor cannot exploit critic extrapolation outside observed theta support.

### 5.4 Trust-region regularization

Because real labels cover only a finite candidate slate:

```text
L_trust =
  distance of theta_hat to nearest observed safe region
  + field-wise residual magnitude penalty
```

Start with small residual scales around `g556_c063174`, then expand only if heldout evidence supports it.

### 5.5 Final actor loss

Recommended:

```text
L_actor =
    L_safe_set
  + lambda_anchor * L_anchor
  + lambda_critic * L_actor_critic
  + lambda_trust * L_trust
  + lambda_smooth * L_consistency
  + lambda_bounds * L_bounds
```

---

## 6. Critic training without selector deployment

Critic batches must be grouped:

```text
B independent instances
× K observed theta candidates per instance
```

Critic losses:

```text
asymmetric/focal BCE for success regression
BCE for success gain
quality regression only for both-success finite rows
quantile pinball loss
pairwise ranking within instance
listwise safe-utility loss
calibration loss
hard-negative loss
```

The critic checkpoint is used for:

```text
actor training
offline diagnostics
hard-negative acquisition
```

It is not copied into the primary inference bundle.

---

## 7. Primary architecture variants to explore

Run these direct-generation variants rather than only one configuration.

### G0 — direct single-output residual actor

```text
instance encoder -> one bounded theta
```

No critic-guided actor loss.

Purpose:

```text
cleanest proof that direct supervised safe-set learning works
```

### G1 — direct actor + auxiliary critic

```text
instance encoder -> one bounded theta
critic only supplies training gradients
```

Primary recommended route.

### G2 — probabilistic direct actor

Predict:

```text
per-field mean
per-field scale/uncertainty
```

Inference uses deterministic mean or mode only.

No sampled candidate selection at deployment.

### G3 — multi-head direct actor ensemble diagnostic

Multiple independently trained actors each output one theta.

Use only to estimate epistemic uncertainty in analysis.

Do not select among them at final inference unless explicitly approved later.

### Selector control

A neural codebook selector may be trained only as:

```text
diagnostic upper/lower control
```

It cannot satisfy the main-method gate.

---

## 8. Mandatory output-novelty and non-collapse audit

For generated theta on heldout instances, report:

```text
exact match rate to any training theta
nearest observed-theta distance
nearest safe-theta distance
unique generated theta count
theta hash count
per-field mean/std/min/max
per-field residual variance
fraction exactly equal to g556
fraction within epsilon of g556
pairwise generated-theta distance
map-family conditional variation
density conditional variation
traffic-regime conditional variation
```

Interpretation:

```text
all theta equal g556:
  actor collapsed

all theta equal one global non-g556 vector:
  actor collapsed to global tuning

all theta copied from codebook:
  implementation violates direct-generation goal

theta changes only with map ID:
  memorization

theta changes with paired goals/C0/F0 and generalizes:
  desired behavior
```

Do not impose an arbitrary minimum nearest-codebook distance; interpolating near a safe observed theta is legitimate. Exact copying and candidate-ID dependence are what must be excluded.

---

## 9. Instance-sensitivity tests

The frozen actor must pass:

```text
same instance repeated -> identical theta

same map, changed start-goal assignment -> theta changes when traffic changes

same start set and goal set, shuffled pairing -> theta changes when OD flow changes

same instance, perturbed C0/F0 -> relevant theta fields change

same graph/traffic, changed solver budget -> theta may change consistently

batch composition/order -> theta unchanged

node ordering permutation -> theta unchanged

solver RNG seed change alone -> theta unchanged
```

These are required to prove that the actor uses instance information rather than IDs.

---

## 10. Real heldout evaluation

Split by:

```text
physical_map_sha256
```

Use grouped cross-validation because the current pilot has only 24 map hashes.

For each heldout instance:

```text
actor(instance) -> one theta_hat
run theta_hat in the real solver
run g556_c063174 with the same evaluation conditions
pair results
```

The primary direct actor is evaluated independently of any codebook selector.

Report:

```text
success regressions
success gains
quality delta
CI
better/worse
per-map results
per-family results
per-density results
per-budget results
generated-theta distribution
```

---

## 11. Efficient replay ladder

Do not immediately launch another huge sweep.

### Development replay A

```text
300–500 heldout instances
one generated theta + g556 baseline
2–3 fresh solver seeds
```

Purpose:

```text
verify materialization
detect catastrophic extrapolation
compare direct actor variants
```

### Development replay B

If A is promising:

```text
2,000–5,000 heldout/new instances
generated theta + g556
multiple budget/map panels
```

### Stage1

Only after direct actor heldout signal:

```text
minimum 200,000 fresh paired rows
```

### Stage2 and blind

Retain the existing strict gates.

---

## 12. Controls cannot substitute for the main method

The report must distinguish:

```text
Main method:
  Direct Continuous GCST Actor

Training aid:
  Auxiliary Solver-Outcome Critic

Controls:
  g556
  density lookup
  GBDT
  tabular MLP
  codebook selector
```

Allowed conclusions:

```text
selector works but actor fails:
  instance-dependent theta signal exists,
  but direct continuous generation remains unsolved

actor works:
  primary hypothesis supported

neither works:
  inspect labels/features/candidate opportunity
```

Forbidden conclusion:

```text
codebook selector passes, therefore direct GCST succeeds
```

---

## 13. Required code changes

Implement separate modules:

```text
src/gcst/direct_actor.py
src/gcst/actor_losses.py
src/gcst/auxiliary_critic.py
src/gcst/actor_critic_training.py
src/gcst/direct_actor_inference.py
src/gcst/generated_theta_audit.py
```

Scripts:

```text
scripts/train_repair5g560_direct_actor.py
scripts/train_repair5g560_direct_actor_critic.py
scripts/eval_repair5g560_direct_actor.py
scripts/run_repair5g560_direct_actor_dev_replay.py
scripts/export_repair5g560_direct_actor.py
```

The exported actor script must not import selector/codebook modules.

---

## 14. Required tests

```text
test_direct_actor_outputs_continuous_theta
test_direct_actor_does_not_load_codebook
test_direct_actor_does_not_use_candidate_id
test_export_bundle_excludes_critic
test_export_bundle_excludes_codebook
test_no_safe_improvement_shrinks_to_g556
test_safe_set_softmin_is_mode_seeking
test_actor_loss_uses_real_safe_set
test_critic_quality_masks_noncomparable_rows
test_actor_inference_single_forward_pass
test_actor_theta_fixed_for_run
test_pairing_shuffle_changes_theta_when_flow_changes
test_solver_seed_does_not_change_theta
test_generated_theta_uid_depends_on_values
test_generated_theta_materialization
```

Use AST/import audits to enforce forbidden dependencies.

---

## 15. Revised minimum completion requirement

This addendum does not permit completion after:

```text
identity recovery only
critic-only training
selector comparison only
offline actor loss only
```

Minimum substantive completion:

```text
1. recover valid Label-v5.1 real labels;
2. train at least G0 and G1 direct continuous actors;
3. produce actor checkpoints and actor-only inference bundles;
4. pass anti-selector and sensitivity audits;
5. compare against density/GBDT/MLP/selector controls;
6. run fresh generated-theta development solver replay;
7. write failure attribution if the direct actor does not improve.
```

---

## 16. Final scientific claim target

The intended method is:

> A goal-aware dual-traffic graph neural network that reads one MAPF instance and directly generates the bounded dual-channel LTM update coefficients used for that entire solver run.

It is not:

> A learned selector that chooses an ID from a fixed parameter library.

All implementation, evaluation, and language must preserve this distinction.
