# czr004 LAUR Repair5D: Diagnostic Preflight + Output-Space Repair Plan

**Branch context:** `phase4f5p5-stable-attention-lau`  
**Latest referenced commit:** `387003a Add Repair5C LAUR diagnostics`  
**Stage objective:** continue **LAUR / learned `UpdateLTM` only**, pass **Phase4F** and then **Phase5.5-update**, with the long-term goal of entering Phase6 and showing closed-loop improvement over `LaCAM*+LTM`.

This plan is intentionally narrow. It does **not** switch to another project path.

## Non-negotiable czr004 boundaries

- Do not predict agent actions.
- Do not replace PIBT, LaCAM*, conflict semantics, candidate generation, pruning, or learned restart.
- Do not relax the final Phase4F / Phase5.5 gate.
- Do not promote Phase6 from offline evidence alone.
- Repair3 remains a conservative baseline / fallback reference, not the primary Repair5 label route.
- The target remains: learned LAUR should replace or improve the simple additive `UpdateLTM` rule and eventually beat additive LTM in closed-loop MAPF metrics.

---

## 0. Current state after Repair5C

Repair5C is an important positive step, not a runtime pass.

The latest diagnostics show that the previous framing “maybe there is no learnable signal” is now less likely. The stronger current interpretation is:

```text
The signal exists.
The current learner can retrieve useful candidate rules.
The current final-selection / safety / defer composition is still wrong.
```

### Evidence from current pushed results

#### 0.1 Oracle gap says LAUR has real offline headroom

`outputs/reports/phase4f_repair5_failure_decomposition.md` and `outputs/tables/phase4f_repair5_oracle_gap.csv` show:

```text
validation oracle_best_safe_rule_mean_delta: 0.074908
validation oracle_vs_additive_mean_delta: 0.074908
oracle_best_safe_nonadditive_vs_additive_mean_delta: 0.074773
oracle_high_margin_capture_possible: 1.0
oracle_harmful_rate: 0.0
```

This is a major signal. The eight-preset space is not empty: in the offline oracle view, there is substantial headroom over additive LTM.

#### 0.2 Hardcase distribution points to top3-to-top1 / composition failure

The hardcase index distribution:

```text
wrong_rule_top1_but_top3_contains_target: 1794
rule_family_confusion: 1194
high_margin_avoidable_defer: 1081
top3_miss_high_utility: 753
false_negative_harmful_selected: 178
```

The largest bucket is not “model sees nothing.” It is: target is often in candidate set, but final rule selection is wrong.

#### 0.3 Per-rule/per-family safety almost solves the safety side

The per-rule safety calibration report shows:

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

So harmful safety is not hopeless. It is miscalibrated / entangled with selection.

#### 0.4 Composite inference is the best Repair5 signal so far

`top3_per_rule_safety_utility` composite mode:

```text
sample_count: 762
top1: 0.414079
top3: 0.706004
safe_utility_top1: 0.425197
utility_regret_to_oracle: 0.022927
selected_vs_additive_delta: 0.009003
harmful_recall: 0.783712
harmful_precision: 0.289591
high_margin_capture: 0.390323
global_additive_or_defer_rate: 0.334646
selected_harmful_rate: 0.007874
```

This is the first result that looks like a real LAUR direction:

- top1 clears the old 0.35 line;
- top3 clears the 0.70 line;
- selected-vs-additive delta is positive and much better than earlier weak variants;
- additive/defer behavior is no longer Repair3-style escape;
- selected harmful rate is low;
- recall/precision and high-margin capture are still slightly short.

#### 0.5 Oracle-safety diagnostic says safety is a bottleneck

`learned_decision_oracle_safety` has:

```text
selected_vs_additive_delta: 0.042605
high_margin_capture: 0.667742
selected_harmful_rate: 0.0
harmful_recall/precision: 1.0 / 1.0
```

This means that if safety selection were solved, the learned decision/ranking side could produce much larger utility gains. Do not interpret this as a runtime candidate. Interpret it as a strong diagnosis.

#### 0.6 Current hierarchical training did not solve the conflict

`LAU-HierEdgeTraceTransformer-v5` safety-first seed61 failed:

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
  high-margin capture: 0.396774
  harmful recall collapsed to 0.105474
```

So the current v5 hierarchy/curriculum did not fix the problem. Do not continue blind curriculum/lambda sweeps.

---

## 1. Integrated diagnosis with Claude/GPTPro feedback

Claude/GPTPro’s useful framing is:

```text
The current strict offline joint gate is not the same as the paper-level LAUR claim.
The paper-level claim must eventually be closed-loop improvement over additive LTM.
LTM representation may be too thin.
The eight preset output space may be too coarse.
```

We should absorb that, but with czr004 boundaries:

```text
Development interpretation can be flexible.
Formal Phase5.5 runtime promotion cannot be loose.
Closed-loop diagnostic preflight can be run before strict promotion, but it is diagnostic-only.
```

### 1.1 What is likely true now

- The idea is still viable.
- The eight preset space contains offline oracle headroom.
- The eight preset space may still be too coarse for final closed-loop gains.
- Current failure is mostly composition / safety / final-selection, not lack of signal.
- LTM representation is probably too thin for the strongest final LAUR version.
- We should test closed-loop transfer now rather than spending another week only improving offline top1.

### 1.2 What not to do next

Do **not** immediately run another 20-variant Transformer/loss sweep.

Do **not** treat `top1 >= 0.35` alone as the new research endpoint.

Do **not** promote Phase5.5 because composite top1/top3/delta look promising.

Do **not** abandon LAUR or jump to agent-action learning.

---

## 2. Gate philosophy for the next phase

### 2.1 Development gate

Flexible. Use it to decide if something deserves more exploration.

Important diagnostics:

```text
selected_vs_additive_delta
utility_regret_to_oracle
high-margin capture
selected_harmful_rate
closed-loop diagnostic transfer
safe_utility_top1/top3
top3-to-top1 improvement
fallback/defer behavior
```

### 2.2 Phase5.5 runtime gate

Still strict. Do not relax.

Required before official runtime promotion:

```text
safety recall >= 0.80
safety precision >= 0.30
positive selected-vs-additive delta
anti-escape / no fake-additive behavior
multi-seed evidence
force-additive/defer parity
no solver semantic changes
```

If a result is promising but misses one of these, it may justify diagnostic preflight, not runtime promotion.

### 2.3 Phase6 / paper claim gate

Must be closed-loop and comparative:

```text
LaCAM*
LaCAM*+LTM
Repair3 conservative MLP runtime
Repair5C/Repair5D LAUR
ablation without safety
ablation without anti-escape
force-additive/defer parity
```

Primary metrics:

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

# 3. Immediate next work: Repair5D

Name the next phase:

```text
Repair5D: diagnostic closed-loop transfer + composite hardening
```

This stage should answer:

```text
Does the promising offline composite signal transfer into solver behavior?
```

If yes, focus on safety/multi-seed/runtime preparation.

If no, stop optimizing offline preset selection and move to output-space / LTM-representation expansion.

---

## P0-A. Run diagnostic closed-loop preflight now

This is now the highest priority.

The repository already has `scripts/run_phase5p5_laur_diagnostic_preflight.py`, but it currently builds a plan; it does not run the solver. Extend it into an actual diagnostic runner or add a sibling script:

```text
scripts/run_phase5p5_laur_diagnostic_preflight_exec.py
```

### Boundary

This is diagnostic-only.

It must print and write:

```text
phase5p5_allowed: false
phase6_allowed: false
```

It must not claim runtime promotion.

### Candidate methods

Use the plan’s candidates:

```text
LaCAM*
LaCAM*+LTM
Repair3 safe runtime
Repair5C top3_per_rule_safety_utility composite
always-additive/defer
oracle replay or teacher-forced update choices if feasible
```

### Minimum scope

Start tiny but meaningful:

```text
maps: 2 or 3
agent_counts: 50, 100
instances_per_setting: 3
runtime: 3s or 5s
```

Suggested maps:

```text
random-32-32-20
maze-32-32-4
warehouse-10-20-10-2-1
```

Do not expand scope until the small preflight is clean.

### Outputs

```text
outputs/logs/phase5p5_laur_diagnostic_preflight/*.jsonl
outputs/reports/phase5p5_laur_diagnostic_preflight_report.md
outputs/reports/phase5p5_laur_diagnostic_preflight_summary.json
outputs/tables/phase5p5_laur_diagnostic_preflight_summary.csv
outputs/tables/phase5p5_laur_diagnostic_preflight_paired.csv
```

### Required metrics

```text
success
sum_of_loss_ratio
expanded_nodes
TTFS
returned_solutions_count
low_level_pibt_calls
fallback/defer rate
non-additive update rate
selected harmful update rate
LAUR overhead
```

### Stop conditions

Stop and report if:

```text
Repair5C composite is worse than LTM on success or ratio.
strict safety mask blocks all learned choices.
non-additive update rate collapses to zero.
oracle replay cannot transfer any measurable advantage.
```

### Success interpretation

If Repair5C composite is equal or better than LTM on success and ratio, with nonzero non-additive update rate and low selected harmful rate, then proceed to P0-B/P0-C.

If oracle replay beats LTM but learned composite does not, then focus on selection/safety/reranking.

If oracle replay also fails to beat LTM, then offline labels/probe objective are not transferring; stop offline sweeps and redesign labels/output space.

---

## P0-B. Re-run composite using actually specialized models

Claude noted an important limitation: the current composite used the same per-rule model CSV as ranking/safety/anti input. That still gave a strong result, which is good, but it did not test true multi-model composition.

Add a composite grid runner:

```text
src/eval/eval_laur_repair5_composite_grid.py
```

### Candidate pools

Ranking candidates:

```text
phase4f_repair5_expand5000_postnext_hightoken_attn_mlp_head_rank_recall_perrule_eval_seed61.csv
phase4f_repair5_expand5000_nextwave_normal_attn_linear_head_rank_safe_eval_seed61.csv
phase4f_repair5_rawtrace_edge_sf_target_ce1_margin1_hm4_eval_seed61.csv
```

Safety candidates:

```text
per-rule safety from phase4f_repair5_per_rule_safety_calibration.json
per-family safety from same calibration
hightoken target/global safety variants
```

Anti/decision candidates:

```text
phase4f_repair5_rawtrace_edge_sf_global_pair_neg2_anti2_eval_seed61.csv
phase4f_repair5_rawtrace_edge_sf_global_rank3_anti3_eval_seed61.csv
current hightoken perrule model as fallback
```

### Modes to test

```text
rank_model_top3 + safety_model_per_rule + utility_rerank
rank_model_top5 + safety_model_per_rule + utility_rerank
rank_model_top3 + anti_decision_margin + safety_model_per_family
rank_model_top3 + learned_defer_penalty + per-rule safety
rank_model_top5 + utility_regret_minimization + selected_harmful_rate constraint
```

### Target score

Do not optimize only top1.

Rank composites by:

```text
selected_vs_additive_delta
selected_harmful_rate <= 0.01 or <= 0.02
harmful recall/precision proximity to gate
high_margin_capture
utility_regret_to_oracle
fallback/defer rate
```

Report all modes. Do not promote runtime.

---

## P0-C. Harden selection-conditioned safety

The composite best has low selected harmful rate but harmful recall/precision proxy is just short. This suggests a mismatch between all-rule safety metrics and final selected-rule behavior.

Add a diagnostic report:

```text
outputs/reports/phase4f_repair5_selected_safety_alignment.md
outputs/reports/phase4f_repair5_selected_safety_alignment.json
```

It should compare:

```text
all-rule harmful recall/precision
selected-rule harmful rate
selected harmful false negatives
selected harmful false positives
per-rule selected harmful counts
per-family selected harmful counts
calibration threshold used for each selected rule
```

Do not use this to bypass final safety gate. Use it to identify whether the remaining 0.01–0.02 safety miss is real or a metric-alignment problem.

---

## P0-D. Safe reranker wrapper

The current reranker direction is useful but unsafe alone. If a reranker exists or is added, it must be wrapped in composite safety.

Add / extend:

```text
src/eval/eval_laur_repair5_safe_reranker.py
```

Pipeline:

```text
base model gives top-k candidates
per-rule/per-family safety masks candidates
reranker ranks remaining safe candidates
utility margin decides whether to use non-additive or defer
```

Required diagnostics:

```text
top1 among candidates
target in candidate set
selected_vs_additive_delta
utility_regret_to_oracle
selected_harmful_rate
high_margin_capture
fallback/defer rate
```

If reranker improves utility but selected_harmful_rate rises, it is not usable without stricter safety mask.

---

# 4. Output-space expansion path

Only move here after P0 preflight/composite results are interpreted.

## Trigger for output-space expansion

Move beyond eight preset rules if any of these holds:

```text
closed-loop preflight shows offline composite does not transfer,
while oracle replay transfers;

composite top3/reranking remains high but final utility stalls;

safe non-additive choices are repeatedly blocked because no preset fits;

oracle analysis says best safe preset still underuses bottleneck-specific information.
```

## P1-A. Bounded ΔUpdateParams head

This is the preferred first output-space extension. It stays within LAUR.

Instead of selecting only one preset, model predicts bounded small deltas around additive/default params:

```text
alpha_commit = clamp(1.0 + Δcommit, min, max)
alpha_block  = clamp(1.0 + Δblock,  min, max)
alpha_wait   = clamp(1.0 + Δwait,   min, max)
rho_decay    = clamp(1.0 + Δrho,    min, max)
saturation_scale = clamp(1.0 + Δsat, min, max)
contraflow_penalty = clamp(0.0 + Δcontra, min, max)
```

Constraints:

```text
small bounded range only
additive fallback remains available
no C++ solver semantic changes beyond existing UpdateParams hook
exportable to JSON/C++ runtime
force-additive parity preserved
```

Training options:

```text
1. supervised from local interpolation between presets;
2. regression to oracle utility-improving direction;
3. black-box short-probe fitted labels on a small param lattice;
4. distill from oracle-safe preset plus residual correction.
```

Do not jump straight to edge-level residual before this low-dimensional continuous head is tested.

## P1-B. More LTM/context information to learner first

Before modifying C++ LTM storage, add richer tokens for the model:

```text
per-edge committed / blocked / wait channel counts
non-goal wait vs goal-wait split
burstiness: first/last event bucket, event span, repeated blocking
reverse edge / contraflow paired counts
edge age / persistent hotness across iterations
local corridor / intersection / boundary features
incumbent phase: no solution, first solution, post-first-solution
iteration index / restart count / returned solution count
previous update effect if available
```

This is lower risk than changing LTM core. It may let attention better decide when to deviate from additive.

## P1-C. Multi-channel LTM core design doc

If bounded ΔUpdateParams still fails, write a design doc before code:

```text
outputs/reports/phase4f_repair5_multichannel_ltm_design.md
```

Possible channels:

```text
commit_count
block_count
wait_spill_count
reverse_conflict_count
persistent_hotness
recent_decay_memory
```

A learned combiner can then produce final LTM weight:

```text
w_ltm_final(e) = clamp(base_additive_weight(e) + learned_channel_mix(e), 0, 10)
```

This is more invasive. Do not implement until diagnostic preflight clarifies that preset/ΔUpdateParams are insufficient.

## P1-D. Sparse top-k edge residual

This is a stronger, later output-space option:

```text
w_final(e) = clamp(w_ltm(e) + gate(e) * Δ(e), 0, 10)
```

Only for top-k bottleneck edges. This remains LAUR if it is framed as learned `UpdateLTM` correction, not agent-action prediction.

Use this only if:

```text
oracle gap remains high,
preset/ΔUpdateParams fails,
closed-loop preflight says edge-specific correction is needed.
```

---

# 5. Literature-inspired exploration lane

Codex may explore recent 2023–2026 AI / robotics / MAPF / planning-learning papers for architecture ideas, but must obey czr004 boundaries.

Allowed inspirations:

```text
hybrid learned guidance + classical safeguard
attention over graph/trace tokens
sparse top-k token routing
mixture-of-experts / rule-family experts
uncertainty-aware defer / abstention
curriculum / hard-case replay
map-family or density-bucket fine-tuning
world-model or diffusion-style denoising as representation learning only
```

Forbidden:

```text
agent-action policy
learned restart
PIBT replacement
conflict/candidate/pruning semantic changes
unbounded learned edge weights
runtime promotion without gates
```

Codex should write a short memo before using any external idea:

```text
outputs/reports/phase4f_repair5_literature_inspiration_memo.md
```

Memo must include:

```text
paper / architecture idea
what is being borrowed abstractly
why it is LAUR-compatible
what is explicitly not being borrowed
what gate will test it
```

---

# 6. Recommended execution order

Do this order. Do not skip to more training sweeps.

## Step 1: finish report consolidation

Ensure current Repair5C reports are committed and readable:

```text
phase4f_repair5c_composite_inference_summary.json
phase4f_repair5c_composite_inference.md
phase5p5_laur_diagnostic_preflight_plan.md/json
per-rule safety calibration reports
failure decomposition reports
```

## Step 2: run diagnostic preflight execution

Implement actual preflight runner and run tiny closed-loop diagnostic.

## Step 3: composite grid with specialized models

Run no-retraining composite grid using best ranking/safety/anti CSVs.

## Step 4: selected-safety alignment

Explain why selected harmful rate is low while harmful recall/precision is slightly below gate.

## Step 5: safe reranker wrapper

If composite grid identifies stable candidate set, add safe reranking.

## Step 6: decide based on preflight

Use the decision table below.

---

# 7. Decision table after preflight

| Result | Interpretation | Next action |
|---|---|---|
| Composite beats or matches LTM with nonzero non-additive rate | Offline signal transfers | Fix safety gap, run multi-seed, prepare Phase5.5 candidate |
| Oracle replay beats LTM but composite does not | Selection/safety/rerank bottleneck | Continue composite/reranker/per-rule safety |
| Neither oracle nor composite beats LTM | Probe/offline label mismatch | Redesign labels; stop optimizing offline top1 |
| Composite improves cost but safety blocks most updates | Safety over-conservative | Selected-safety calibration / per-rule thresholding |
| Composite uses many unsafe updates | Safety too weak | Strengthen selected safety, do not runtime promote |
| Composite close but update space stalls | Eight presets too coarse | Start bounded ΔUpdateParams head |
| ΔUpdateParams still insufficient | LTM representation too thin | Design multi-channel LTM / sparse top-k residual |

---

# 8. Codex prompt block

Use this as the next Codex goal.

```text
Goal: Continue czr004 LAUR Repair5D from branch phase4f5p5-stable-attention-lau after commit 387003a. Do not change project direction. The goal remains learned LAUR / UpdateLTM only, passing Phase4F and then Phase5.5-update, eventually enabling Phase6 only after closed-loop benefit over LaCAM*+LTM.

Do not predict agent actions. Do not replace PIBT, LaCAM*, conflict semantics, candidate generation, pruning, or learned restart. Do not lower final gates. Phase5.5 and Phase6 remain forbidden unless existing strict conditions are met.

Immediate tasks:

1. Implement actual diagnostic closed-loop preflight execution, not just a plan.
   - Compare LaCAM*, LaCAM*+LTM, Repair3 safe runtime, Repair5C composite/reranker diagnostic, always-additive/defer, and oracle replay or teacher-forced update choices if feasible.
   - Use a tiny scope: 2-3 maps, 2 agent counts, <=3 instances per setting, 3-5s time budget.
   - Report success, sum_of_loss_ratio, expanded nodes, TTFS, low-level PIBT calls, LAUR overhead, defer rate, non-additive rate, selected harmful rate.
   - Output JSONL, summary CSV, paired CSV, and report MD.
   - Mark the result diagnostic-only: no Phase5.5 permission, no Phase6 permission.

2. Run true multi-source composite grid without retraining.
   - Combine different ranking/safety/anti CSVs, not only the same perrule model.
   - Include top3/top5 + per-rule safety + utility rerank; anti-margin modes; per-family safety modes.
   - Rank modes by selected_vs_additive_delta, utility_regret_to_oracle, high-margin capture, selected_harmful_rate, recall/precision proximity.

3. Add selected-safety alignment diagnostics.
   - Compare all-rule harmful recall/precision with selected-rule harmful rate.
   - Identify selected harmful false negatives by rule/family/map.
   - Do not use this to lower final gate.

4. Add safe reranker wrapper if the composite grid shows stable candidate sets.
   - Base model proposes top-k.
   - Per-rule/per-family safety masks candidates.
   - Reranker ranks remaining candidates.
   - Utility margin decides use_nonadditive vs defer.

5. Only after diagnostic preflight is interpreted, decide whether to start bounded ΔUpdateParams.
   - If closed-loop signal transfers, first fix safety/multi-seed and prepare Phase5.5 candidate.
   - If oracle transfers but composite does not, continue composition/reranker/safety.
   - If preset space is the ceiling, implement bounded ΔUpdateParams head.
   - If LTM representation is the ceiling, write multi-channel LTM / sparse top-k residual design doc before coding.

Verification:
- Keep or improve current tests. Run relevant pytest group.
- Record all results in docs/codex-worklog.md.
- Do not launch blind lambda sweeps.
```

---

# 9. Final interpretation

This stage is no longer “does LAUR have any signal?”

It is now:

```text
Can the offline composite signal transfer into closed-loop LTM improvement?
Can safety be aligned with final selected update behavior?
Does the eight-preset space suffice, or do we need bounded continuous UpdateParams?
Does LTM need richer memory channels for the next jump?
```

The answer should come from preflight and oracle-transfer diagnostics, not from another large sweep.

If preflight is positive, push toward Phase5.5 hardening.

If preflight is negative, expand output space and/or LTM representation.

Either way, stay on LAUR.
