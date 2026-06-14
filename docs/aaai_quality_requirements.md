# Repair5G AAAI Quality Requirements

AAAI-ready learning claims require a learned runtime UpdateLTM selector, clean heldout validation, negative controls, ablations, stress, reproducibility manifests, and a claim ledger.

- runtime_selector_integration: `passed`
- runtime_selector_smoke: `failed`
- learned_runtime_selector_performance: `failed`
- learned_runtime_fresh_holdout: `blocked_not_run`
- static_flow_shield: `strong_baseline_not_learned_claim`
- advanced_neural_network_stage: `blocked_until_safe_runtime_selector_or_counterfactual_labels`
- aaai_ready: `false`
- Phase5.5 and Phase6 remain closed until paper-grade gates pass.

## 2026-06-14 G5.49 AAAI gate note

G5.49 found calibrated-core fulltheta safe-gain regions versus `static_flow_shield`, but this is not AAAI-ready evidence. The result is limited to `4` unique evaluable strata, warehouse remains non-evaluable locally, and the generator/targeted/blind chain did not pass. Do not count selected horizon rows as unique-stratum coverage, and do not promote replay-region hindsight to a learned generator claim.

AAAI-facing status remains:

```text
primary baseline: static_flow_shield
additive_ltm: paper-faithful floor
strong static variants: diagnostic only
SafeGate: calibrated_core_subset_development_only
runtime_claim_allowed: false
phase5p5_allowed: false
phase6_allowed: false
aaai_ready: false
```

## 2026-06-14 G5.50 AAAI gate note

G5.50 does not promote the G5.49 fulltheta regions to an AAAI-ready learned method. The round adds audits, forensic tables, active replay plans, multiple offline policy-family diagnostics, skip artifacts for targeted/blind replay, and exact resume commands for the large local replay stages. The local result is `g550_blocked_with_exact_commands`: useful engineering progress, but not paper-grade validation.

AAAI-facing status remains:

```text
primary baseline: static_flow_shield
additive_ltm: paper-faithful floor
strong static variants: diagnostic only
SafeGate: calibrated_core_subset_development_only / large_replay_resume_required
runtime_claim_allowed: false
phase5p5_allowed: false
phase6_allowed: false
aaai_ready: false
```

## 2026-06 Repair5G learning-insertion strategy for top-tier AI / MAPF venues

Repair5G has now established an important scientific fact:

```text
Goal-aware dual-channel LTM with flow-shielded cost projection is useful.
```

The current validated representation is:

```text
C-channel:
  congestion / blockage / wait-risk evidence

F-channel:
  goal-progress / successful-flow / corridor evidence

flow-shield projection:
  F does not make an edge globally cheap.
  F only reduces C-channel over-penalty on current-agent goal-progress edges.
```

This is the right representation direction. It is more promising than scalar / C-only Repair5F UpdateParams, and the repeated G2/G4 results show that flow-shielded dual-channel UpdateLTM can outperform plain additive LTM under closed-loop solver metrics.

However, Repair5G must not confuse three different levels of contribution:

```text
Level 0:
  hand-designed static flow-shield rule

Level 1:
  selector over a finite set of hand-designed UpdateLTM candidates

Level 2:
  learned bounded dual-channel UpdateLTM parameter / residual / mixture policy

Level 3:
  graph/trace neural UpdateLTM policy with explicit safety/fallback constraints
```

Only Level 2 or Level 3 can plausibly support a strong AAAI/ICLR/ICML/NeurIPS-style "learning-enhanced UpdateLTM" paper claim. Level 0 and Level 1 are valuable engineering bridges and ablations, but static flow-shield or a shallow selector over hand-tuned candidates is not, by itself, a strong learned-method contribution.

### 1. The learning insertion point

The only valid learning insertion point for the current project is:

```text
pre-update trace/context
  -> learned UpdateLTM policy
  -> bounded C/F-channel update parameters or safe candidate mixture
  -> DirectedTrafficMap update
  -> WeightedDistanceTable
  -> original LaCAM*/PIBT semantics unchanged
```

The learned component must not output:

```text
agent actions
PIBT priorities
restart nodes
heuristic h_i(v)
candidate deletions
collision outcomes
OPEN / EXPLORED / rewrite decisions
incumbent pruning decisions
```

The learned component may output:

```text
bounded alpha_cong_* parameters
bounded alpha_flow_* parameters
bounded rho_* decay parameters
bounded flow_shield_beta
bounded max_flow_shield
mixture weights over safe UpdateLTM experts
abstention / fallback to static flow-shield, C-equiv, or additive
```

This keeps the project story as:

```text
learning UpdateLTM dynamics
```

not:

```text
learning MAPF actions
```

### 2. Why selector exists

The runtime selector is not the final scientific goal. Its role is to provide a safe and auditable bridge between validated hand-designed UpdateLTM rules and learned UpdateLTM policies.

The selector is useful because it can:

```text
1. choose a validated flow-shield rule in normal cases;
2. abstain to additive or C-equiv fallback in no-op / high-risk cases;
3. expose decision logs for per-iteration auditing;
4. let the project test learning insertion without changing solver semantics;
5. provide a safety layer for later neural parameter policies.
```

But the selector is weak as a final top-tier contribution if it only chooses among a few manually designed candidate IDs. A paper whose main learned method is:

```text
if feature <= threshold:
    choose hand-coded rule A
else:
    choose hand-coded rule B
```

will likely look like engineering heuristics rather than a strong learned planning method.

Therefore the project must treat selector work as:

```text
necessary bridge,
not final method.
```

### 3. Why direct learned dual-channel parameters are more attractive to top-tier venues

A learned dual-channel parameter policy is more aligned with AAAI/ICLR/ICML/NeurIPS/ICRA expectations because it gives a clearer learning contribution:

```text
context / trace / traffic-map state
  -> learned bounded update dynamics
```

rather than:

```text
context
  -> choose one manually tuned rule
```

The top-venue-friendly method should learn **how to update the traffic map**, not merely learn which hand-coded rule name to use.

The preferred medium-term method is:

```text
Learned Bounded Dual-Channel UpdateLTM Policy
```

or:

```text
Contextual Residual Flow-Shield UpdateLTM
```

with one of the following output forms:

```text
A. bounded residual policy:
   base_params = validated static flow-shield
   model predicts small residuals:
     alpha' = clip(alpha_base + delta_alpha)
     beta'  = clip(beta_base  + delta_beta)
     max_shield' = clip(max_shield_base + delta_max)

B. safe mixture policy:
   model predicts mixture weights over safe experts:
     expert_1 = static flow-shield
     expert_2 = map-agent flow-shield
     expert_3 = additive / C-equiv fallback
   UpdateParams = convex / gated mixture of bounded safe experts

C. abstention policy:
   model predicts:
     use flow-shield
     use conservative fallback
     defer to static baseline
   with confidence/risk thresholds.
```

The preferred first AAAI-worthy version is **B + C**, not unconstrained continuous parameter prediction. It is safer and easier to validate:

```text
safe mixture over validated UpdateLTM experts
+
learned abstention / risk control
+
bounded parameter residuals only after counterfactual labels are available
```

### 4. Why unconstrained neural parameter prediction is not allowed yet

Do not jump directly to:

```text
large neural net -> arbitrary alpha/beta/rho values
```

This is not acceptable yet because:

```text
1. solver outcome is non-differentiable and noisy;
2. current full-run labels are too coarse for per-update parameter learning;
3. unconstrained parameter output can destabilize traffic-map costs;
4. it may overfit map/agent/ID artifacts;
5. it is harder to prove that benefits come from learned UpdateLTM rather than protocol drift;
6. reviewers will demand strong ablations and counterfactual evidence.
```

Before continuous parameter learning, the project must build:

```text
iteration-level context dataset
counterfactual UpdateLTM labels
oracle gap analysis
feature leakage audit
runtime feature availability audit
static / selector / random / shuffled controls
```

The learning target must be causally tied to the update context:

```text
same traffic_before + same trace_events
  apply candidate UpdateParams A -> downstream short-probe outcome A
  apply candidate UpdateParams B -> downstream short-probe outcome B
  compare A vs B
```

Do not train continuous parameter policies from final full-run outcomes alone unless the report explicitly marks that as weak, confounded, and diagnostic-only.

### 5. Top-venue taste assessment

The project should optimize for the following reviewer expectations.

#### AAAI / MAPF / heuristic-search taste

AAAI and MAPF reviewers are likely to favor:

```text
- clear algorithmic contribution;
- preservation of LaCAM*/PIBT semantics;
- strong baselines;
- ablations isolating C-channel, F-channel, flow-shield, and learning;
- clean closed-loop solver evidence;
- statistics and group-wise failure analysis;
- reproducibility and protocol clarity;
- not overclaiming from a single split or static heuristic.
```

They will be skeptical of:

```text
- static hand-tuned rules sold as learning;
- selectors that do not beat static baselines;
- action-policy style models that bypass solver semantics;
- weak or missing parity controls;
- cherry-picked maps / agents / IDs.
```

#### ICLR / ICML / NeurIPS taste

ML reviewers are likely to favor:

```text
- a real learned policy, not a hand-coded parameter table;
- generalization across heldout IDs / maps / agent counts;
- negative controls such as random features and shuffled labels;
- feature ablations;
- uncertainty / abstention / calibration;
- clear training objective and dataset construction;
- evidence that the learned component improves over strong non-learned baselines.
```

They will be skeptical of:

```text
- a decision stump over hand-designed candidate IDs as the main contribution;
- no clear learning objective;
- no learned-runtime fresh validation;
- lack of counterfactual labels;
- no comparison against static flow-shield.
```

#### ICRA / robotics-planning taste

ICRA-style planning reviewers are likely to favor:

```text
- reliability under time budgets;
- safety/fallback behavior;
- no illegal motion or collision-semantics change;
- robust anytime performance;
- interpretable failure modes;
- reproducible runtime benchmarks.
```

They will be skeptical of:

```text
- learned modules that introduce brittle behavior;
- no safety fallback;
- neural black boxes without closed-loop validation;
- failure to preserve solver guarantees / semantics.
```

### 6. Route comparison

The project should record the following route comparison as a standing decision table.

| Route | Description | Top-venue attractiveness | Current readiness | Main risk | Project decision |
|---|---|---:|---:|---|---|
| Static flow-shield | one or few fixed flow-shield rules | medium for heuristic-search, low for ML | high | looks hand-tuned | keep as strong baseline |
| Map-agent selector | table-like selector by map/agent group | medium-low | high | looks like benchmark-specific engineering | keep as baseline/fallback |
| Discrete learned selector | learned model chooses candidate ID | medium | partial | must beat static; G5 failed | use only as safe bridge |
| Safe learned-abstention selector | default flow-shield, learned fallback/abstention | medium-high | next step | may only match static | best immediate route |
| Learned mixture over safe experts | learned weights over static/map-agent/additive/C-equiv experts | high | requires runtime + labels | needs careful gates | preferred G6 route |
| Learned bounded residual parameters | learned small residuals over flow-shield parameters | high | requires counterfactual labels | overfit/instability | preferred G6/G7 route after labels |
| Graph/trace neural UpdateLTM | GNN/attention over trace/traffic graph outputs bounded UpdateLTM policy | high if well validated | not ready | data and ablation burden high | G7 only after counterfactual label quality |
| Action policy / priority policy | neural MAPF action/priority/restart | not allowed for this project | forbidden | violates project scope | reject |

### 7. Recommended stage ladder

The project should now follow this ladder.

#### Stage G5.1: safe runtime bridge and failure autopsy

Goal:

```text
explain why G5 runtime selector failed;
verify runtime hook with always-static and map-agent sanity selectors;
repair disable / force-additive policy controls;
build safe abstention selector.
```

Key rule:

```text
The safe selector defaults to validated flow-shield.
It only falls back to additive/C-equiv when risk or no-op evidence is high.
```

Do not let the selector choose weak C-equiv by default in early iterations.

#### Stage G6: learned safe mixture / residual UpdateLTM policy

Goal:

```text
move from selecting hand-coded candidates to learning bounded UpdateLTM dynamics.
```

Preferred architecture:

```text
input:
  allowed pre-update context / trace / C-F traffic summary features

encoder:
  small MLP or calibrated linear model first

output:
  mixture weights over safe experts
  optional bounded residuals over flow-shield parameters
  confidence / abstention score

fallback:
  static flow-shield
  map-agent selector
  additive / C-equiv only under high-risk abstention
```

This is the first stage that can plausibly become the main learned method in an AAAI-style paper.

#### Stage G7: advanced graph/trace neural UpdateLTM policy

Only after G6 demonstrates a real adaptive gap and counterfactual labels are reliable.

Possible architecture:

```text
edge/trace encoder:
  graph neural network or trace-attention module

inputs:
  local graph edge features
  C-channel statistics
  F-channel statistics
  trace event aggregates
  goal-progress summaries
  map topology summaries
  iteration context

outputs:
  bounded parameter residuals
  safe expert mixture weights
  abstention / fallback probability
```

Still forbidden:

```text
actions
priorities
restarts
h-values
candidate deletion
collision decisions
```

G7 is not allowed unless the project first proves:

```text
simple selector / mixture model has plateaued;
oracle gap remains;
counterfactual labels are sufficient;
runtime integration is stable;
safe fallback works.
```

#### Stage G8: formal AAAI/ICLR/ICML/NeurIPS/ICRA evidence package

Goal:

```text
turn the method into a paper-grade contribution.
```

Required artifacts:

```text
clean learned-runtime heldout validation
map/agent expansion
time/iteration stress
static-vs-learned ablation
C-only vs C+F ablation
flow-shield vs subtractive-F ablation
fallback/abstention ablation
random-feature and shuffled-label diagnostics
oracle-regret analysis
claim ledger
reproducibility manifest
paper outline
limitation report
```

### 8. Preferred final paper method

The preferred final method should not be called merely:

```text
selector
```

A stronger name is:

```text
Learned Goal-Aware Dual-Channel UpdateLTM
```

or:

```text
Contextual Flow-Shield UpdateLTM
```

The final method should consist of:

```text
1. dual-channel traffic-map state:
   C(e) congestion evidence
   F(e) goal-progress flow evidence

2. flow-shield projection:
   F shields useful goal-progress corridors from C over-penalty
   without making edges globally cheap

3. learned bounded UpdateLTM policy:
   predicts safe expert mixtures or bounded residual parameters
   from pre-update trace/context features

4. safety/fallback layer:
   confidence / OOD / no-op abstention to static flow-shield or additive/C-equiv

5. semantic preservation:
   LaCAM*/PIBT search, conflict handling, candidate generation, restart, and pruning are unchanged
```

### 9. Required claims and forbidden claims

Allowed current claim:

```text
Goal-aware flow-shielded dual-channel UpdateLTM is a validated representation-level improvement over additive LTM and scalar/C-only UpdateParams under the tested closed-loop protocols.
```

Forbidden current claim:

```text
We have an AAAI-ready learned runtime UpdateLTM method.
```

Allowed future claim only after G6/G7 gates:

```text
A learned bounded dual-channel UpdateLTM policy improves or safely matches static flow-shield while preserving solver semantics, and improves closed-loop anytime MAPF performance over plain additive LTM.
```

Forbidden permanently unless the project scope changes:

```text
The model learns MAPF actions.
The model learns PIBT priorities.
The model learns restart nodes.
The model changes LaCAM* candidate generation or pruning.
The model replaces LaCAM*/PIBT.
```

### 10. Immediate research instruction

The next research phase must not be:

```text
train a bigger neural network immediately.
```

The next research phase must be:

```text
1. complete G5.1 runtime selector autopsy;
2. verify runtime hook sanity with always-static and map-agent selectors;
3. repair force-additive / disable policy controls;
4. build safe abstention selector;
5. construct iteration-level counterfactual UpdateLTM label dataset;
6. only then move to G6 learned safe mixture / residual dual-channel parameter policy.
```

This strategy gives the project the highest chance of satisfying both:

```text
MAPF reviewer taste:
  solver semantics preserved, strong baselines, closed-loop evidence

ML top-venue taste:
  real learned update dynamics, not static hand-tuning
```
