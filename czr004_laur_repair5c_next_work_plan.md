# czr004 LAUR Repair5C / Phase4F→5.5 Next Work Plan

**Scope:** `czr004` / `phase4f5p5-stable-attention-lau`  
**Current objective:** continue **LAUR / learned `UpdateLTM`** only, pass **Phase4F** and then **Phase5.5-update**, with the long-term goal of entering Phase6 and showing closed-loop improvement over `LaCAM*+LTM`.

This document intentionally does **not** switch to another project path. It keeps the czr004 constraints:

- Do not predict agent actions.
- Do not replace PIBT, LaCAM*, conflict semantics, candidate generation, pruning, or learned restart.
- Do not relax the final Phase4F / Phase5.5 gate.
- Repair3 remains a conservative baseline / fallback reference, not the primary Repair5 label route.
- The target remains: learned LAUR should replace or improve the simple additive `UpdateLTM` rule and eventually beat additive LTM in closed-loop MAPF metrics.

---

## 0. Current Read of the Latest GitHub State

The latest pushed work has moved Repair5 beyond a simple loss sweep. It added:

- Repair5 failure decomposition.
- Oracle-gap analysis.
- Per-rule / per-family safety calibration.
- Hierarchical curriculum configs.
- `LAU-HierEdgeTraceTransformer-v5` training results.
- A 5000-case hardcase index.
- Formal stop point after `hier_hightoken_safety_first` seed61.

Important current evidence:

```text
expand5000 / high-token dataset:
  samples: 4956
  train / validation: 4194 / 762
  validation non-additive opportunity: 483
  validation high-margin opportunity: 310
  schema errors: 0
  split leakage errors: 0
```

The label/data pipeline is no longer the primary suspected blocker.

The strongest new result is the oracle-gap analysis:

```text
validation oracle_best_safe_rule_mean_delta: 0.074908
validation oracle_vs_additive_mean_delta: 0.074908
validation oracle_best_safe_nonadditive_vs_additive_mean_delta: 0.074773
oracle_high_margin_capture_possible: 1.0
oracle_harmful_rate: 0.0
```

This is a major signal. It means the current data/probe space contains substantial headroom over additive LTM, at least in the offline oracle sense. The idea is not dead.

However, the learner still fails to assemble that headroom:

```text
failure hardcase index:
  wrong_rule_top1_but_top3_contains_target: 1794
  rule_family_confusion: 1194
  high_margin_avoidable_defer: 1081
  top3_miss_high_utility: 753
  false_negative_harmful_selected: 178
```

This strongly suggests the next blocker is not “no signal”. It is:

```text
decision/ranking/safety composition failure
+ action/output-space coarseness
+ LTM representation thinness
+ offline-to-closed-loop uncertainty
```

The recent per-rule safety calibration is a second important signal:

```text
global threshold 0.35:
  recall 0.81976
  precision 0.29491
  passed false

per-rule thresholding:
  recall 0.82911
  precision 0.30058
  passed true

per-family thresholding:
  recall 0.80240
  precision 0.30430
  passed true
```

So harmful safety is probably **not unsolvable**. It is miscalibrated or entangled with selection.

The latest `LAU-HierEdgeTraceTransformer-v5` safety-first run did not solve the problem:

```text
best selected validation epoch:
  top1: 0.140787
  top3: 0.666667
  harmful recall: 0.612817
  harmful precision: 0.247573
  selected-vs-additive delta: -0.003786
  high-margin capture: 0.264516
  global additive/defer rate: 0.729659

late epoch:
  high-margin capture reached 0.396774
  but harmful recall collapsed to 0.105474
```

Conclusion: hierarchy/curriculum in the current form did not fix the core conflict. More blind sweeps are unlikely to help.

---

## 1. Integrated Diagnosis

### 1.1 The idea is still viable

Additive LTM is crude, but it is a strong crude baseline. It already captures the first-order rule:

```text
congested / blocked / waited-on edges should become more expensive.
```

The learner must discover second-order deviations:

```text
which congestion is structural vs transient
which wait is harmful vs harmless
which bottleneck needs stronger update
which corridor should be decayed or preserved
which rule is safe only in a specific map/topology/phase
```

The oracle-gap result shows there is useful signal in the existing Repair5 data.

### 1.2 The current eight preset rules are both useful and limiting

The oracle result says the current eight-rule preset space still contains headroom. So the eight presets are not completely useless.

But the learner struggles to choose exactly among them. The largest hardcase class is:

```text
wrong_rule_top1_but_top3_contains_target: 1794
```

This means the model often knows the right neighborhood but cannot reliably make the final decision.

Therefore, the immediate priority is **top3-to-top1 reranking / decision composition**, not just “make model bigger”.

Still, the eight global presets remain a likely ceiling for closed-loop performance. Even if the learner chooses correctly, the update is still coarse:

```text
one global alpha_commit / alpha_block / alpha_wait / rho
for the whole checkpoint
```

A stronger LAUR should eventually move from “choose one global preset” to:

```text
bounded continuous UpdateParams
or sparse edge-level residual correction on top of LTM.
```

### 1.3 LTM representation is thin

Current LTM essentially stores a directed-edge traffic count, normalized into edge weights. It does not persistently store:

- separate commit / block / wait channels,
- burst vs persistent congestion,
- reverse-flow conflict,
- local saturation,
- search phase,
- edge age,
- corridor/intersection context,
- agent diversity on the edge,
- whether previous update helped or hurt.

Repair5 tokens partly compensate by using raw trace and topology features. But runtime LTM itself remains thin. This can limit both learning and deployment.

### 1.4 Current flat/hier multitask still entangles objectives

The v5 run shows the same tradeoff as earlier flat Repair5:

```text
anti improves -> harmful recall collapses
safety improves -> additive/defer dominates
ranking/top3 improves -> top1 and anti remain weak
```

So the next attempt should not be another monolithic objective sweep. It should separate:

```text
candidate generation
safety masking/calibration
reranking
defer/additive decision
utility validation
```

---

## 2. Gate Philosophy Going Forward

Claude’s point about paper-level evaluation is partly right: final scientific value should be judged by **closed-loop improvement over additive LTM**, not full validation top1 alone.

However, czr004 still needs strict internal gates for Phase5.5 runtime promotion.

Use this separation:

### 2.1 Development / diagnostic gate

Purpose: decide whether an idea deserves more exploration.

Can be flexible:

- top1 is diagnostic, not primary.
- top3, safe utility top-k, utility regret, high-margin capture, and selected-vs-additive delta matter more.
- anti-escape can be analyzed as behavior, not a single kill-switch.
- closed-loop diagnostic preflight may be allowed without Phase5.5 promotion.

### 2.2 Phase5.5 runtime gate

Purpose: decide whether a learned update model can be integrated as an official runtime candidate.

Do **not** relax:

```text
harmful recall >= 0.80
harmful precision >= 0.30
positive selected-vs-additive delta
anti-escape / no fake-additive behavior
multi-seed evidence
force-additive/defer parity
no solver semantic changes
```

### 2.3 Phase6 / paper claim gate

Purpose: decide whether LAUR is a successful learned improvement.

Must include closed-loop comparison:

```text
LaCAM*
LaCAM*+LTM
Repair3 conservative MLP runtime
Repair5/Repair5C LAUR
ablation without safety
ablation without anti-escape
force-additive/defer parity
```

Main metrics:

```text
success rate
sum_of_loss_ratio
anytime AUC
expanded nodes
TTFS
low-level PIBT calls
LAUR overhead
fallback/defer rate
non-additive update rate
```

---

## 3. Highest-Priority Next Work

The next phase should be called:

```text
Repair5C: LAUR output-space and composition repair
```

Do not launch more random configs until these steps are done.

---

## P0-A. Composite Inference Without Retraining

**Why:** Hardcase index shows many cases where the target is in top3 but not top1. Existing models have fragments of success: some have top3, some anti, some safety. Before training a new model, test whether composition can assemble these fragments.

### Implement

Add:

```text
src/eval/eval_laur_repair5_composite_inference.py
```

Inputs:

```text
- ranking model summary / eval CSV
- safety model summary / eval CSV
- anti model summary / eval CSV
- per-rule safety calibration JSON
- Repair5 label dataset
```

Candidate composition modes:

```text
mode A: top3-ranking + per-rule safety + utility rerank
mode B: anti model decides use_nonadditive/defer; ranking model chooses top3; safety model masks
mode C: top3-ranking + anti margin + per-rule family safety
mode D: oracle-decision + learned-rerank
mode E: learned-decision + oracle-safety diagnostic
```

Metrics:

```text
rule_top1
rule_top3
safe_utility_top1/top3
utility_regret_to_oracle
selected_vs_additive_delta
harmful precision/recall
high_margin_capture
avoidable defer/additive
```

Expected outcome:

- If composition improves strongly, the failure is mostly inference/selection architecture.
- If composition fails, output space or labels are likely the bottleneck.

Do not grant Phase5.5 from this script. It is diagnostic only.

---

## P0-B. Per-Rule Safety as Default Evaluation Mode

**Why:** The latest calibration report shows per-rule and per-family safety can pass where global threshold fails.

### Implement

Add or extend evaluation configs so every serious Repair5 variant can be evaluated with:

```text
global threshold
per-rule threshold
per-family threshold
calibration-split threshold
```

Required rule:

```text
Calibrate thresholds only on train/calibration split.
Evaluate on validation.
Report both.
```

Files:

```text
src/eval/calibrate_laur_repair5_per_rule_safety.py
src/eval/eval_laur_attention_native.py
src/eval/eval_laur_repair5_final_gate.py
```

Add report:

```text
outputs/reports/phase4f_repair5_safety_calibration_comparison.md
```

If a model only fails global safety but passes per-rule/per-family safety, it should be labeled:

```text
candidate_for_composite_or_preflight
```

not discarded as useless.

---

## P0-C. Top3-to-Top1 Reranker

**Why:** `wrong_rule_top1_but_top3_contains_target` is the largest hardcase class. This suggests the base attention model often retrieves the right candidate set, but the final rank is wrong.

### Implement

Add a second-stage reranker:

```text
src/models/laur_attention_reranker.py
src/train/train_laur_attention_reranker.py
src/eval/eval_laur_attention_reranker.py
```

Training data:

For each sample, take top-k candidates from a base model or oracle-safe candidate set:

```text
candidate rules = top3 or top4
features =
  shared context embedding
  candidate rule embedding
  candidate utility estimate
  harmful probability
  additive margin
  opportunity flags
  rule family
```

Loss:

```text
pairwise candidate ranking
target rule CE within candidate set
utility regret loss
safety-aware mask loss
```

Evaluation:

```text
top1 among candidates
utility regret
closed-loop proxy delta
harmful rate after rerank
```

This is a high-priority, concrete next attempt because it directly targets the largest failure mode.

---

## P0-D. Oracle-Transfer Closed-Loop Preflight

**Why:** The offline oracle gap is large. But we do not yet know how much offline oracle advantage transfers to actual LaCAM*+LTM closed-loop performance.

### Implement diagnostic only

Add a controlled preflight, not Phase5.5 promotion:

```text
scripts/run_phase5p5_laur_diagnostic_preflight.py
```

Compare on a tiny but meaningful subset:

```text
LaCAM*
LaCAM*+LTM
Repair3 MLP safe runtime
Repair5 learned candidate
oracle-replay diagnostic, if feasible
always-defer/additive
```

If true oracle replay is not feasible in runtime, use one of:

```text
offline replay over recorded checkpoints
short-budget closed-loop with teacher-forced update choices
closed-loop with model choices but strict safety mask
```

Metrics:

```text
success
sum_of_loss_ratio
expanded nodes
TTFS
defer rate
non-additive update rate
selected-vs-additive delta
```

Boundary:

```text
This is not Phase5.5 permission.
This is not Phase6 evidence.
This only tests whether offline signals transfer to closed-loop.
```

If no offline signal transfers to closed-loop, stop optimizing offline top1.

---

## 4. Output-Space Expansion

If P0 composition/reranking cannot assemble a good candidate, move beyond 8-class preset selection.

---

## P1-A. Bounded ΔUpdateParams Head

**Why:** The current output space may be too coarse. This is the cleanest next extension while staying inside LAUR.

Instead of selecting only:

```text
additive_ltm
commit_heavy
block_heavy
...
```

predict bounded deltas around additive/default parameters:

```text
alpha_commit = clamp(1.0 + Δcommit, lower, upper)
alpha_block  = clamp(1.0 + Δblock, lower, upper)
alpha_wait   = clamp(1.0 + Δwait, lower, upper)
rho_decay    = clamp(1.0 + Δrho, lower, upper)
saturation   = clamp(1.0 + Δsat, lower, upper)
contraflow   = clamp(0.0 + Δcontra, lower, upper)
```

### Supervision target

Use the existing probe utilities to build a continuous target:

```text
param_target = soft utility-weighted barycenter of safe high-utility preset params
```

For example:

```text
target_params = Σ softmax(utility / T)[rule] * params(rule)
```

Also train a residual target:

```text
delta_params = target_params - additive_params
```

### Model

Add:

```text
LAU-UpdateParamTransformer-v1
```

or extend v5 with:

```text
update_param_delta_head
```

### Safety

Runtime must clamp all outputs and keep additive fallback.

### Evaluation

Before any C++ runtime integration:

```text
probe-evaluate predicted UpdateParams against:
  additive
  best preset
  Repair3
  oracle-safe preset
```

If bounded Δparams outperforms preset selector in offline probe, continue.

This is likely one of the most promising next directions if top3-to-top1 reranking still struggles.

---

## P1-B. Phase-Aware UpdateParams

Add explicit phase-conditioned outputs:

```text
pre_first_solution
post_first_solution
early_iteration
late_iteration
high_incumbent_gap
low_incumbent_gap
```

The learner can output different update strengths depending on solver phase.

This is still LAUR. It does not learn restart or action policy.

---

## 5. LTM Representation Expansion

There are two layers: input representation for the learner and actual LTM runtime representation.

---

## P1-C. Give the Learner More LTM/Trace Context

This is lower-risk because it does not change C++ LTM semantics.

Add optional token/features:

```text
edge persistence:
  how many iterations this edge stayed hot

burstiness:
  blocked/wait events concentrated vs spread

reverse-flow:
  reverse edge hotness and reverse conflict count

saturation:
  raw count near normalized max

phase:
  iteration index, first solution found, incumbent gap, returned solution count

distance impact:
  weighted distance delta vs unweighted distance
  whether edge lies on many current shortest paths

agent diversity:
  unique agents on edge
  repeated same-agent conflict vs many-agent bottleneck

temporal trace buckets:
  early/mid/late trace event counts
```

Add flags in config:

```yaml
tokenization:
  use_extended_trace_stats: true
  use_persistence_features: true
  use_distance_impact_features: true
```

This should be tried before changing C++ runtime LTM structure.

---

## P2-A. Multi-Channel LTM Runtime

Only do this if bounded ΔUpdateParams and reranking still hit a ceiling.

Instead of one raw traffic count per edge, store channels:

```text
commit_count
block_count
wait_spill_count
reverse_conflict_count
decay_age
```

Then LAUR learns how to fuse channels into traversal cost.

This is a real LTM representation upgrade, but it is more invasive. It must be guarded by a separate parity plan.

---

## P2-B. Sparse Top-K Edge Residual / CBR-style Update

If eight global presets and bounded global params remain insufficient, use sparse edge residual:

```text
w_final(e) = clamp(w_ltm(e) + gate(e) * Δ(e), 0, 10)
```

Only for top-k bottleneck edges, with strict bounds.

This remains LAUR if framed as learned `UpdateLTM` correction, not agent-action policy. But it is closer to a new runtime update representation and should not be the first implementation unless oracle/closed-loop diagnostics justify it.

---

## 6. Literature-Inspired Exploration Space for Codex

Codex may read 2023–2026 AI / robotics / planning-learning literature for architecture ideas, but must obey czr004 constraints.

Use papers as inspiration for **architecture and training pattern**, not task transfer.

Allowed inspirations:

```text
hybrid learned guidance + classical safeguard
map/domain fine-tuning
hard-case aggregation / DAgger-like failure mining
attention over graph/trace tokens
sparse attention or token pruning
mixture-of-experts or per-family experts
uncertainty-triggered defer/fallback
continuous bounded output heads
sequence/diffusion-style modeling for multimodal update choices
block-wise adapters / lightweight fine-tuning
```

Forbidden transfers:

```text
agent action policy
learned collision handling
learned PIBT replacement
learned restart
changing LaCAM* semantics
unbounded neural edge weights
```

Recommended literature scan topics:

```text
MAPF learned heuristic search
graph attention for multi-agent coordination
robot foundation policies with transformer tokenization
diffusion / flow matching for continuous action distributions
uncertainty-aware robotics policies
hybrid planning-learning systems
safe learning with classical fallback
```

For each idea Codex wants to try, it must write:

```text
outputs/reports/phase4f_repair5_literature_inspiration_memo.md
```

with:

```text
paper / idea
what is abstracted
why it is LAUR-compatible
what is forbidden / not copied
implementation sketch
expected metric improvement
risk
```

---

## 7. Concrete Experiment Queue

Do not run all at once. Use this priority order.

### Queue 1: no new training

```text
Q1.1 composite inference from existing models
Q1.2 per-rule/per-family safety evaluation for all completed variants
Q1.3 top3-to-top1 hardcase breakdown
Q1.4 diagnostic closed-loop preflight design
```

### Queue 2: small training

```text
Q2.1 top3-to-top1 reranker
Q2.2 candidate-set reranker + per-rule safety
Q2.3 high-margin specialist reranker
```

### Queue 3: output-space expansion

```text
Q3.1 bounded ΔUpdateParams head from utility-weighted preset barycenter
Q3.2 phase-aware bounded ΔUpdateParams
Q3.3 compare predicted params vs preset oracle in probe
```

### Queue 4: representation expansion

```text
Q4.1 extended trace/persistence/distance-impact tokens
Q4.2 LTM multi-channel design memo
Q4.3 sparse top-k edge residual design memo
```

### Queue 5: closed-loop

Only after Q1/Q2 or Q3 produces a candidate that passes diagnostic criteria:

```text
Q5.1 diagnostic closed-loop preflight
Q5.2 Phase5.5 strict promotion only if gates pass
```

---

## 8. Stop / Continue Criteria

Continue LAUR if any of these occur:

```text
composite inference improves safety+anti+top3 together
reranker improves top1/utility regret without hurting safety
bounded ΔUpdateParams beats preset selector in probe
closed-loop preflight shows learned update not worse than LTM
oracle-transfer gap remains large
```

Pause or change output space if:

```text
oracle in preset space does not transfer to closed-loop
reranker cannot improve over top3 candidate set
per-rule safety cannot generalize
all models still collapse into additive/defer
```

Escalate to LTM representation change if:

```text
bounded global params are still too coarse
hardcase analysis shows edge-local bottleneck residual is needed
closed-loop bottlenecks are localized but global UpdateParams cannot fix them
```

---

## 9. What to Tell Codex in One Block

```text
Goal: Continue czr004 LAUR only. Do not switch paths. Do not lower final Phase4F/5.5 gates.

Latest evidence shows:
- expand5000 labels are clean.
- oracle_safe_rule beats additive by ~0.075 on validation.
- hardcases are dominated by target-in-top3-but-wrong-top1, family confusion, and avoidable defer.
- per-rule/per-family safety calibration can pass safety where global threshold fails.
- the first hierarchical v5 curriculum still failed; late anti improvements collapsed harmful recall.

Therefore stop blind loss sweeps.

Next tasks:
1. Build composite inference from existing models.
2. Make per-rule/per-family safety calibration a first-class evaluation path.
3. Train a top3-to-top1 reranker on hardcases.
4. Run an oracle-transfer diagnostic closed-loop preflight design, not Phase5.5 promotion.
5. If preset selector remains insufficient, implement bounded ΔUpdateParams output head.
6. Add richer LTM/trace context features.
7. Only later consider multi-channel LTM or sparse top-k edge residual.

Phase5.5 remains forbidden until strict original/attention-native/safety/anti-escape/multi-seed gates pass.
Phase6 remains forbidden until closed-loop learned benefit over additive LTM is shown.
```
