# czr004 Repair5F Decision Plan: Bounded UpdateParams Diagnostic for Learned UpdateLTM

**Status:** F1 diagnostic completed / safety-blocked / diagnostic-only
**Recommended branch:** `phase4f5p5-stable-attention-lau`  
**Create after:** `1b0f93e01f71a19ae1137f0710e29639d802952d`  
**Promotion status:** `phase5p5_allowed=false`, `phase6_allowed=false`  
**Primary project goal:** use learning-enhanced `UpdateLTM` to replace the coarse additive update in the LTM paper and beat `LaCAM*+LTM` under closed-loop solver metrics.

**F1 execution note (2026-06-01):** the full final-holdout bounded lattice probe was run over all required maps, agent counts, and IDs 21..25. The lattice oracle metric gate is strong (`17 / 13 / 0`, mean delta ratio vs LTM `-0.018311948514033324`), but the strict force-additive defer parity control failed on one full-holdout group. The exact additive lattice candidate itself is parity-exact, so the lattice evidence remains useful, but selector/runtime export is deferred until the parity-control discrepancy is resolved.

---

## 0. Executive decision

Repair5E.5 should be closed as a **useful but non-promotable diagnostic result**.

The correct next step is **not** to keep tuning the same 8-rule preset selector. The correct next step is also **not** to jump to a solver rewrite, learned restart, action prediction, or richer traffic-map representation.

The next step should be:

```text
Repair5F:
  Bounded UpdateParams lattice / constrained UpdateParams selector
  for learned UpdateLTM,
  as a controlled side branch.
```

This remains aligned with the main project only if it stays inside:

```text
PIBT trace
  -> UpdateLTM
  -> DirectedTrafficMap raw_count / normalized_weight
  -> WeightedDistanceTable
  -> existing LTM guidance path
```

It is not aligned if it becomes:

```text
manual per-map tuning
exact map/agent/instance recovery table
action prediction
learned restart
PIBT / LaCAM* replacement
candidate pruning
conflict semantic changes
richer traffic-map representation before UpdateParams is exhausted
offline-only fitting without closed-loop metrics
```

---

## 1. What Repair5E.5 tells us

### 1.1 E5 improved the evidence quality

E5 added:

```text
- cross-fold support over scenario IDs 1..25
- no support/eval fold overlap
- soft/listwise utility tables
- threshold/risk sweep
- runtime artifact
- final holdout and OOF diagnostics
- force-additive and recovery-disabled parity controls
- shuffled-label diagnostic
```

This is good. It means the current negative result is much more informative than earlier E2/E3/E4 results.

### 1.2 E5 OOF was weak-positive

OOF result:

```text
repair5e5_crossfold_utility_reranker:
  better / equal / worse = 22 / 114 / 14
  mean_delta_ratio_vs_ltm = -0.0013255900057666681
  ratio_worse_than_ltm_groups = 1
  success_worse_than_ltm_groups = 0
```

This shows nonzero signal, but not enough for a method claim.

### 1.3 E5 final holdout failed

Final holdout:

```text
repair5e5_crossfold_utility_reranker:
  better / equal / worse = 4 / 22 / 4
  mean_delta_ratio_vs_ltm = -0.0009245170596666741
  ratio_worse_than_ltm_groups = 2
  success_worse_than_ltm_groups = 0
```

It fails because:

```text
better > worse is false
ratio_worse_than_ltm_groups <= 1 is false
```

### 1.4 The shuffled-label result is the key blocker

Final holdout shuffled-label diagnostic:

```text
repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic:
  better / equal / worse = 7 / 20 / 3
  mean_delta_ratio_vs_ltm = -0.0039024738501666654
```

This is stronger than the real selector. Therefore the E5 selector has not proven that learned utility structure, rather than group bias or accidental safe choices, is responsible for the gain.

### 1.5 E5 reports were generated under dirty provenance

Several E5 reports record:

```text
git commit: db0f494
git dirty state: tracked-dirty_untracked-present
clean tracked worktree: false
```

The final commit later pushed the artifacts, but the reports themselves were not produced from a clean committed state. This is acceptable for diagnostic work, but not acceptable for promotion or final method claims.

---

## 2. Are we still moving toward the main goal?

Yes, if Repair5F is framed correctly.

The main target is not “beat LTM with any trick.” The target is:

```text
learn or data-drive the traffic-map update dynamics
that replace LTM's hand-written additive accumulation,
while preserving LaCAM* / PIBT semantics and fallback safety.
```

Repair5F is aligned because it still learns/selects `UpdateLTM` parameters from closed-loop evidence. It does not change the solver.

Repair5F would become misaligned if it degenerates into:

```text
a static hand-tuned parameter set,
a per-map lookup table,
or a hidden extra baseline.
```

So the core scientific requirement for Repair5F is:

```text
The lattice oracle may diagnose headroom,
but the method claim requires a selector that beats shuffled/random controls
on held-out closed-loop metrics.
```

---

## 3. Why stop Repair5E-style tuning?

Repair5E tested:

```text
- recovery table style selection
- OOD guard calibration
- closed-loop utility labels
- cross-fold support
- soft/listwise utility tables
- threshold/risk calibration
- false-positive suppression
- shuffled-label diagnostics
```

The remaining bottleneck appears to be the output space:

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

This 8-rule space is too coarse. It cannot express moderate combined changes such as:

```text
slightly reduce block accumulation
slightly increase wait spillover
add mild decay
leave commit weight neutral
```

or other context-dependent combinations. The static/oracle proxy still shows that update choices matter, but the selector cannot robustly recover them from the coarse rule set.

Therefore the next controlled experiment should expand `UpdateParams`, not solver semantics.

---

## 4. Repair5F scope

### 4.1 Name

```text
Repair5F: Bounded UpdateParams Lattice for Learned UpdateLTM
```

### 4.2 First question

```text
Does a bounded UpdateParams candidate lattice contain stronger closed-loop headroom
than the 8-rule Repair5E preset space?
```

This is an oracle/headroom question. It is not a method claim.

### 4.3 Second question

```text
Can a selector recover that headroom on held-out instances
better than shuffled/random controls?
```

This is the method question.

### 4.4 Candidate dimensions

Use a sparse bounded lattice around additive LTM:

```text
alpha_commit          in {0.5, 0.75, 1.0, 1.25, 1.5}
alpha_block           in {0.5, 0.75, 1.0, 1.25, 1.5}
alpha_wait_spillover  in {0.5, 0.75, 1.0, 1.25, 1.5}
rho_decay             in {0.90, 0.95, 1.0}
```

Always include exact additive:

```text
alpha_commit = 1.0
alpha_block = 1.0
alpha_wait_spillover = 1.0
rho_decay = 1.0
```

Do **not** start with the full Cartesian product unless runtime is explicitly acceptable. Prefer about 25–60 candidates:

```text
- exact additive
- one-axis variations around additive
- limited two-axis interactions
- several conservative decay combinations
- candidates corresponding approximately to old preset rules
```

### 4.5 Deferred dimensions

Do not enable in F0/F1:

```text
contraflow_penalty
local_saturation
spillover_radius > 0
richer traffic-map state
learned restart
free continuous neural output
```

These are later branches only if bounded UpdateParams lattice proves insufficient or promising.

---

## 5. Required F0 deliverables

Create/update:

```text
czr004_repair5f_bounded_updateparams_decision_plan.md
docs/codex-worklog.md
outputs/reports/phase5p5_repair5e5_final_interpretation.md
```

The E5 interpretation must state:

```text
- E5 is diagnostic-only and not promotable.
- E5 OOF is weak-positive.
- E5 final holdout fails.
- Shuffled-label diagnostic is stronger than the real selector.
- The 8-preset-rule selector is not trustworthy enough.
- Oracle/static proxy still shows UpdateLTM headroom.
- Repair5F is justified only as a bounded UpdateLTM side branch.
```

---

## 6. Required F1 deliverables

### 6.1 Candidate lattice

Implement:

```text
scripts/create_repair5f_updateparam_candidates.py
```

Write:

```text
outputs/tables/phase5p5_repair5f_candidate_lattice.csv
outputs/reports/phase5p5_repair5f_candidate_lattice_report.md
outputs/reports/phase5p5_repair5f_candidate_lattice_summary.json
```

Report:

```text
candidate_count
parameter ranges
exact additive candidate ID
old-preset-equivalent candidates
new candidates
sparse vs full-Cartesian construction
```

### 6.2 Candidate probe table

Implement:

```text
scripts/run_repair5f_updateparam_probe_table.py
```

Write:

```text
outputs/logs/phase5p5_repair5f_candidate_probe/*.jsonl
outputs/tables/phase5p5_repair5f_updateparam_utility_long.csv
outputs/tables/phase5p5_repair5f_updateparam_utility_wide.csv
outputs/reports/phase5p5_repair5f_candidate_probe_report.md
outputs/reports/phase5p5_repair5f_candidate_probe_summary.json
```

### 6.3 Optional selector artifact

Only after F1-oracle headroom is confirmed, implement:

```text
scripts/create_repair5f_updateparam_selector_runtime.py
artifacts/models/laur_ltm/repair5f_bounded_updateparam_selector/
```

The first selector should be conservative and interpretable, for example KNN/radius utility selection. Do not make neural runtime a dependency before the candidate-lattice oracle is validated.

---

## 7. Splits and leakage controls

Use available scenario IDs `1..25`.

Minimum final split:

```text
support/train IDs: 1..20
final holdout IDs: 21..25
```

Keep five-fold OOF if feasible:

```text
fold_0_eval = [1, 2, 3, 4, 5]
fold_1_eval = [6, 7, 8, 9, 10]
fold_2_eval = [11, 12, 13, 14, 15]
fold_3_eval = [16, 17, 18, 19, 20]
fold_4_eval = [21, 22, 23, 24, 25]
```

Hard rules:

```text
No support/eval overlap.
No eval logs used while creating runtime artifacts.
No exact map/agent/instance recovery table as selector.
```

---

## 8. Evaluation methods

At minimum compare:

```text
lacam_star
lacam_star_ltm
always_additive_defer
repair5e5_crossfold_utility_reranker
repair5f_candidate_lattice_oracle_static_proxy
repair5f_bounded_updateparam_selector
repair5f_bounded_updateparam_selector_force_additive_parity
repair5f_bounded_updateparam_selector_random_candidate_diagnostic
repair5f_bounded_updateparam_selector_shuffled_utility_diagnostic
```

Optional comparisons:

```text
repair5d_composite_diagnostic_distilled
repair5e3_split_guarded_selector
repair5e4_closed_loop_utility_selector
```

---

## 9. Required metrics

Use the shared metrics/schema path. Report:

```text
better / equal / worse vs LaCAM*+LTM
mean_delta_ratio_vs_ltm
ratio_worse_than_ltm_groups
success_worse_than_ltm_groups
zero_nonadditive_groups
expanded_delta_vs_ltm
low_level_pibt_delta_vs_ltm
TTFS delta
inference overhead
selected parameter distribution
parameter sensitivity by map/agents
support count vs realized delta
nearest distance vs realized delta
shuffled/random diagnostic result
force-additive parity result
```

---

## 10. F1 gates

### 10.1 Safety gates

```text
force-additive parity exact
recovery-disabled parity exact if implemented
support/eval leakage = false
phase5p5_allowed = false
phase6_allowed = false
solver_semantic_changes = false
```

### 10.2 Lattice oracle gate

Continue only if:

```text
candidate_lattice_oracle better > worse
candidate_lattice_oracle mean_delta_ratio_vs_ltm <= -0.003
candidate_lattice_oracle ratio_worse_than_ltm_groups <= 1
candidate_lattice_oracle success_worse_than_ltm_groups = 0
```

Strong evidence would be:

```text
candidate_lattice_oracle mean_delta_ratio_vs_ltm <= -0.008
better - worse >= 5 on final holdout or equivalent OOF scale
```

### 10.3 Selector gate

The selector is useful only if:

```text
selector better > worse
selector mean_delta_ratio_vs_ltm < 0
selector ratio_worse_than_ltm_groups <= 1
selector success_worse_than_ltm_groups = 0
selector beats shuffled/random diagnostic
selector does not collapse to exact additive parity
```

If shuffled/random is as good as or better than the selector, do not promote.

---

## 11. Decision table after F1

### Case A: lattice oracle strong, selector positive

Proceed to larger multi-map validation and cleaner runtime export design.

### Case B: lattice oracle strong, selector fails

Do not change solver semantics. Improve selector representation/objective:

```text
better checkpoint features
utility ranking objective
calibrated abstention
map-family balanced support
pairwise/listwise loss
```

### Case C: lattice oracle weak

Bounded UpdateParams lattice is insufficient. Only then discuss:

```text
richer traffic-map update representation
or residual edge-weight update
```

### Case D: selector positive but shuffled/random positive too

Treat as spurious. Diagnose group bias and leakage-like artifacts.

---

## 12. Codex prompt

```text
Continue czr004 on branch phase4f5p5-stable-attention-lau after commit 1b0f93e01f71a19ae1137f0710e29639d802952d.

Goal:
  Begin Repair5F as a controlled bounded UpdateParams diagnostic for learned UpdateLTM.

Main project objective:
  Use learning-enhanced UpdateLTM to replace the coarse additive LTM update from the LTM paper and eventually beat LaCAM*+plain additive LTM under closed-loop solver metrics.

Read first:
  deep-research-report.md
  phase4_6_laur_ltm_codex_execution_plan.md
  czr004_repair5e5_crossfold_utility_reranker_plan.md
  czr004_repair5f_bounded_updateparams_decision_plan.md
  outputs/reports/phase5p5_repair5e5_preflight_summary.json
  outputs/reports/phase5p5_repair5e5_ablation_summary.json
  outputs/reports/phase5p5_repair5e5_oof_preflight_summary.json

Preserve this interpretation:
  Repair5E.5 is implemented and evaluated, but it is not promotable.
  OOF was weak-positive:
    22 / 114 / 14
    mean_delta_ratio_vs_ltm = -0.0013255900057666681
  Final holdout failed:
    4 / 22 / 4
    mean_delta_ratio_vs_ltm = -0.0009245170596666741
    ratio_worse_than_ltm_groups = 2
  Shuffled-label diagnostic was stronger than the real selector:
    7 / 20 / 3
    mean_delta_ratio_vs_ltm = -0.0039024738501666654
  Therefore the 8-preset-rule Repair5E selector is not trustworthy enough.
  Oracle/static proxy still shows UpdateLTM headroom, so do not abandon learned UpdateLTM.

Do not:
  - claim Phase5.5 or Phase6
  - modify external/lacam2/lacam2/**
  - change PIBT, LaCAM*, candidate generation, pruning, conflict semantics, OPEN/EXPLORED, incumbent pruning, or restart semantics
  - introduce action prediction
  - introduce learned restart
  - introduce richer LTM representation in F0/F1
  - use exact map/agent/instance recovery table as the selector
  - consume eval logs while creating runtime artifacts

F0 tasks:
  1. Confirm or create czr004_repair5f_bounded_updateparams_decision_plan.md.
  2. Update docs/codex-worklog.md.
  3. Write outputs/reports/phase5p5_repair5e5_final_interpretation.md.

F1 tasks:
  1. Implement scripts/create_repair5f_updateparam_candidates.py.
     Generate a sparse bounded UpdateParams lattice with roughly 25 to 60 candidates.
     Dimensions:
       alpha_commit in {0.5,0.75,1.0,1.25,1.5}
       alpha_block in {0.5,0.75,1.0,1.25,1.5}
       alpha_wait_spillover in {0.5,0.75,1.0,1.25,1.5}
       rho_decay in {0.90,0.95,1.0}
     Always include exact additive: 1.0,1.0,1.0,1.0.
     Write:
       outputs/tables/phase5p5_repair5f_candidate_lattice.csv
       outputs/reports/phase5p5_repair5f_candidate_lattice_report.md
       outputs/reports/phase5p5_repair5f_candidate_lattice_summary.json

  2. Implement scripts/run_repair5f_updateparam_probe_table.py.
     Probe bounded UpdateParams candidates in closed loop.
     Minimum split:
       support/train IDs: 1..20
       final holdout IDs: 21..25
     Keep five-fold OOF if feasible.
     Write:
       outputs/logs/phase5p5_repair5f_candidate_probe/*.jsonl
       outputs/tables/phase5p5_repair5f_updateparam_utility_long.csv
       outputs/tables/phase5p5_repair5f_updateparam_utility_wide.csv
       outputs/reports/phase5p5_repair5f_candidate_probe_report.md
       outputs/reports/phase5p5_repair5f_candidate_probe_summary.json

  3. Compare candidate-lattice oracle against:
       lacam_star_ltm
       repair5e5_crossfold_utility_reranker
       random candidate diagnostic
       shuffled utility diagnostic

  4. Only if candidate-lattice oracle headroom is materially stronger than E5, implement one conservative selector:
       scripts/create_repair5f_updateparam_selector_runtime.py
       artifacts/models/laur_ltm/repair5f_bounded_updateparam_selector/
     The first selector may be deterministic KNN/radius utility selection.

F1 gates:
  - force-additive parity exact
  - support/eval leakage false
  - phase5p5_allowed=false
  - phase6_allowed=false
  - candidate_lattice_oracle better > worse
  - candidate_lattice_oracle mean_delta_ratio_vs_ltm <= -0.003
  - candidate_lattice_oracle ratio_worse_than_ltm_groups <= 1
  - selector, if implemented, must beat shuffled/random diagnostic

Validation:
  - py_compile all new/modified Python scripts
  - build scripts/build_phase1a_batch.ps1 if C++ changed
  - run targeted pytest if pytest is available; otherwise record pytest unavailable clearly
  - run git diff --check
  - commit and push only Repair5F-related files and required records
  - leave unrelated dirty/untracked files untouched

Commit message:
  repair5f: add bounded updateparam candidate probe plan
```
