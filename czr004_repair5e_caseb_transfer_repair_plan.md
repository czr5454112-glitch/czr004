# czr004 LAUR Repair5E.1 Plan: Case-B Composite/Reranker Transfer Repair

**Branch:** `phase4f5p5-stable-attention-lau`  
**Latest pushed commit reviewed:** `df8801c1ed0e23db813511d4982c87e1376528de`  
**Prior plan:** `czr004_laur_repair5e_composite_preflight_plan.md`  
**Current decision:** Case B — oracle/static proxy is positive, but current learned Repair5D distilled runtime does not transfer.

This document continues the LAUR / learned `UpdateLTM` route only. It does not switch to learned action prediction, learned restart, PIBT/LaCAM* replacement, conflict-semantics changes, candidate-generation changes, pruning changes, or gate relaxation.

Phase5.5 and Phase6 remain forbidden.

---

## 1. What the latest Repair5E result actually says

The latest commit completed the intended Repair5E diagnostic step far enough to answer the next scientific question:

```text
Can the Repair5D offline composite be put through a closed-loop diagnostic path,
and does the preset update space still have closed-loop headroom?
```

The answer is split:

```text
- Repair5D native composite export: not implemented.
- Repair5D composite-like distilled bridge: executed.
- Full teacher-forced per-update oracle hook: not implemented.
- Static-rule oracle proxy: executed and positive.
```

Main metrics from the pushed Repair5E preflight:

```text
Repair5D distilled diagnostic vs LaCAM*+LTM:
  paired rows: 18
  better / equal / worse: 1 / 12 / 5
  mean ratio delta vs LTM: +0.0025935989  # worse because lower ratio is better
  ratio worse than LTM groups: 2 / 6
  success worse than LTM groups: 0
  zero non-additive groups: 0

Oracle static proxy vs LaCAM*+LTM:
  paired rows: 18
  better / equal / worse: 8 / 9 / 1
  mean ratio delta vs LTM: -0.0101318977  # positive
  ratio worse than LTM groups: 0 / 6
  success worse than LTM groups: 0

Repair3 safe runtime vs LaCAM*+LTM:
  paired rows: 18
  better / equal / worse: 4 / 11 / 3
  mean ratio delta vs LTM: -0.0019803575
```

Decision-table interpretation:

```text
Case B:
  oracle_positive = true
  repair5d_positive = false
  recommended_action = improve_composite_or_reranker_do_not_jump_to_delta_updateparams
```

This is not a dead end. It means the remaining blocker is probably learned inference / export / transfer alignment, not absence of closed-loop headroom in the preset update space.

---

## 2. Important nuance: do not over-read the distilled result

The current closed-loop method is:

```text
repair5d_composite_diagnostic_distilled
```

It is not the native three-component Repair5D composite from the offline grid. It is a temporary MLP bridge trained to imitate composite decisions in the existing runtime format.

Therefore:

```text
Valid claim:
  The distilled bridge did not transfer well enough.

Invalid claim:
  The true Repair5D composite has been disproven.
```

The distill validation result was already imperfect:

```text
validation rule_top1: 0.473753
predicted_non_additive_rate: 0.717848
selected_harmful_rate target: 0.005249
```

In closed-loop preflight, the distilled policy also shows a likely action-selection collapse / domain shift:

```text
maze-50:       commit_heavy x9, ratio delta +0.014434
maze-100:      commit_heavy x9, ratio delta -0.000246
random-50:     commit_heavy x9, ratio delta  0.000000
random-100:    commit_heavy x9, ratio delta +0.001374
warehouse-50:  commit_heavy x6, ratio delta  0.000000
warehouse-100: commit_heavy x1 + wait_light x2, ratio delta 0.000000
```

The oracle/static proxy chooses a more diverse set of rules, including `block_heavy`, `block_light`, `wait_light`, `wait_heavy`, `decay_090`, and `commit_heavy`. That mismatch is the first thing to debug.

---

## 3. Immediate next objective

Call the next step:

```text
Repair5E.1: Case-B Composite/Reranker Transfer Repair
```

Primary questions:

```text
Q1. Is the Repair5D distilled bridge failing because of runtime feature distribution shift?
Q2. Is it failing because distillation loses the composite's top-k/safety/rerank behavior?
Q3. Is it failing because offline labels are not aligned with closed-loop ratio gains?
Q4. Can a closed-loop-aware reranker/distill probe beat LTM without changing solver semantics?
Q5. Should the next serious implementation be native composite/Python diagnostic selector rather than MLP distillation?
```

Do not start bounded `ΔUpdateParams` yet. The oracle/static proxy is positive, so the preset update space still has headroom.

---

## 4. P0 Tasks

### P0-A. Add provenance addendum for the pushed Repair5E result

The pushed summary records:

```text
commit: f27ac22
state: tracked-dirty_untracked-present
```

This is expected because the diagnostic was generated before commit `df8801c` and while unrelated local changes/untracked outputs existed. Do not rewrite historical result files to pretend they were clean.

Instead create:

```text
outputs/reports/phase5p5_repair5e_preflight_provenance_addendum.md
outputs/reports/phase5p5_repair5e_preflight_provenance_addendum.json
```

Required content:

```text
- pushed commit reviewed: df8801c1ed0e23db813511d4982c87e1376528de
- generated report internal commit: f27ac22
- reason: generated before staging/committing Repair5E files
- dirty state: tracked-dirty_untracked-present
- note: unrelated existing local changes and historical outputs were intentionally not staged
- scientific result remains diagnostic-only
- Phase5.5 allowed: false
- Phase6 allowed: false
```

If practical, also run a quick non-preflight validation from a clean worktree/worktree clone:

```text
git worktree add ../czr004-clean-repair5e df8801c1ed0e23db813511d4982c87e1376528de
python -m pytest tests/test_repair5e_composite_preflight.py
python -m pytest
```

Do not rerun expensive preflight just to update the commit SHA unless there is a code/report bug.

---

### P0-B. Build a Case-B transfer analysis report

Create:

```text
scripts/analyze_repair5e_caseb_transfer.py
outputs/reports/phase5p5_repair5e_caseb_transfer_analysis.md
outputs/reports/phase5p5_repair5e_caseb_transfer_analysis.json
outputs/tables/phase5p5_repair5e_caseb_decision_alignment.csv
outputs/tables/phase5p5_repair5e_caseb_rule_outcomes.csv
```

Inputs:

```text
outputs/logs/phase5p5_repair5e_preflight/phase5p5_repair5e_preflight.jsonl
outputs/logs/phase5p5_repair5e_preflight/phase5p5_repair5e_preflight_laur_updates.jsonl
outputs/tables/phase5p5_repair5e_preflight_summary.csv
outputs/tables/phase5p5_repair5e_preflight_paired.csv
outputs/tables/phase5p5_repair5d_composite_distill_decisions.csv
```

Required analysis:

```text
1. Per scenario, compare:
     LaCAM*+LTM
     Repair3 safe runtime
     Repair5D distilled
     oracle/static proxy selected rule

2. Identify where Repair5D distilled is worse than LTM:
     map
     agents
     instance seed
     selected rules
     fallback/defer count
     expanded-node delta
     ratio delta
     TTFS delta

3. Quantify rule-collapse/domain-shift:
     selected rule distribution in offline validation
     selected rule distribution in closed-loop preflight
     oracle/static proxy rule distribution in closed-loop preflight
     KL/JS divergence or simpler distribution deltas

4. Add feature OOD diagnostics:
     runtime feature vector z-score vs distill training mean/std
     per-feature max |z|
     percent of update decisions outside ±3σ and ±5σ
     correlate OOD with bad ratio delta

5. Compare Repair3 vs Repair5D distilled:
     cases where Repair3 wins and Repair5D loses
     cases where both choose non-additive but different rules
     cases where Repair5D commit_heavy is inferior to Repair3 block_light

6. Preserve boundaries:
     no Phase5.5 claim
     no Phase6 claim
     no solver semantic change
```

Stop after the report if the failure is clearly caused by feature OOD or rule-collapse. Do not do more random training sweeps without a targeted fix.

---

### P0-C. Implement one targeted diagnostic policy repair

Pick at most one primary repair for the next run. Do not stack several changes and make the result uninterpretable.

Preferred repair order:

#### Option 1: Python-side true composite selector diagnostic

If feasible, execute the frozen Repair5D composite more directly instead of distilling it to the single MLP runtime format.

Create:

```text
scripts/run_phase5p5_repair5d_true_composite_diagnostic.py
outputs/reports/phase5p5_repair5d_true_composite_diagnostic_report.md
outputs/reports/phase5p5_repair5d_true_composite_diagnostic_summary.json
```

Boundary:

```text
- diagnostic-only
- not production C++ runtime
- log every decision
- force-additive parity mode required
- no solver semantic changes
```

This is the cleanest way to distinguish:

```text
true composite fails
vs
MLP distillation bridge fails
```

#### Option 2: Closed-loop-aware second-stage reranker/distill probe

If true composite execution is still infeasible, train a small closed-loop-aware second-stage selector using the static-proxy support rows.

Create:

```text
scripts/train_repair5e_caseb_closedloop_reranker.py
artifacts/models/laur_ltm/repair5e_caseb_closedloop_reranker_diagnostic/
outputs/reports/phase5p5_repair5e_caseb_closedloop_reranker_report.md
outputs/reports/phase5p5_repair5e_caseb_closedloop_reranker_summary.json
```

Design:

```text
- target is not offline top1.
- target should prefer the static rule that improves ratio vs LTM on the same scenario.
- if no static rule improves ratio, defer/additive.
- include a safety/defer guard.
- mark diagnostic-only.
```

Because the current oracle support set is tiny, start with analysis and a probe, not a final training claim. If training data is too small, expand the static-proxy diagnostic grid before training.

#### Option 3: OOD/defer guard for the existing distill bridge

If feature OOD explains bad choices, add a diagnostic defer guard:

```text
if runtime feature vector is far outside distill training distribution:
    defer/additive
else:
    use Repair5D distilled prediction
```

Create:

```text
artifacts/models/laur_ltm/repair5d_composite_distilled_ood_guard/
outputs/reports/phase5p5_repair5e_ood_guard_report.md
```

This should be treated as a safety/transfer diagnostic, not a final method.

---

### P0-D. Rerun the same closed-loop preflight, but only after P0-B and one P0-C repair

Use the same scenario scope:

```text
maps:
  random-32-32-20
  maze-32-32-4
  warehouse-10-20-10-2-1
agent_counts:
  50
  100
instances_per_setting:
  3
time_limit_sec:
  3.0
ltm_max_iterations:
  4
```

Required methods:

```text
LaCAM*
LaCAM*+LTM
always_additive_defer
Repair3 safe runtime
old Repair5D composite distilled
new Repair5E.1 targeted repair candidate
force-additive/defer parity for the new candidate
oracle/static proxy
```

Outputs:

```text
outputs/logs/phase5p5_repair5e_caseb_preflight/*.jsonl
outputs/reports/phase5p5_repair5e_caseb_preflight_report.md
outputs/reports/phase5p5_repair5e_caseb_preflight_summary.json
outputs/tables/phase5p5_repair5e_caseb_preflight_summary.csv
outputs/tables/phase5p5_repair5e_caseb_preflight_paired.csv
```

Diagnostic pass criteria:

```text
- success not lower than LaCAM*+LTM
- mean ratio delta vs LTM <= 0
- better/equal/worse vs LTM improves over old Repair5D distilled
- ratio_worse_than_ltm_groups <= 1 / 6
- non-additive update rate does not collapse to zero unless the candidate is an explicit defer/guard probe
- force-additive parity matches LTM
```

This is still not Phase5.5. It is only a go/no-go for continuing toward native export/multi-seed.

---

## 5. Decision table after Repair5E.1

### Case B1: True composite or repaired reranker beats/matches LTM

Then continue LAUR:

```text
1. Prepare native C++ composite export or formal runtime equivalent.
2. Re-run preflight under clean worktree provenance.
3. Expand to more instances.
4. Then consider seeds 103/107 for component models.
```

### Case B2: True composite works but distill/reranker does not

The blocker is runtime export / distillation.

```text
1. Prioritize native composite export or Python diagnostic bridge.
2. Stop using single-MLP distillation as the main evidence path.
3. Keep Repair3 as runtime fallback reference.
```

### Case B3: Oracle/static proxy positive, but true composite and repaired reranker both fail

The blocker is label alignment.

```text
1. Stop optimizing offline top1/top3.
2. Build closed-loop labels from static probes or per-update teacher-force hook.
3. Only then consider richer output space.
```

### Case B4: Oracle/static proxy stops being positive after larger scope

The preset update space may not transfer robustly.

```text
1. Write failure report.
2. Consider bounded ΔUpdateParams design doc.
3. Do not implement ΔUpdateParams before the failure report.
```

---

## 6. Codex execution prompt

```text
Continue czr004 on branch phase4f5p5-stable-attention-lau after pushed commit df8801c1ed0e23db813511d4982c87e1376528de.

Goal:
  Repair5E.1 Case-B transfer repair.
  Stay strictly within LAUR / learned UpdateLTM.
  Do not predict agent actions, replace PIBT/LaCAM*, alter conflict semantics, change candidate generation/pruning, add learned restart, or lower final gates.
  Phase5.5 and Phase6 remain forbidden.

Current evidence from Repair5E:
  - Repair5D native composite export was not feasible; the current closed-loop result used a diagnostic MLP distillation bridge.
  - Full per-update teacher-forced oracle hook was not available; a static-rule oracle proxy was executed.
  - Static-rule oracle proxy is positive vs LaCAM*+LTM:
      better/equal/worse = 8/9/1
      mean ratio delta vs LTM = -0.0101318977
  - Repair5D composite distilled bridge is not positive:
      better/equal/worse = 1/12/5
      mean ratio delta vs LTM = +0.0025935989
      ratio worse than LTM groups = 2/6
      success worse than LTM groups = 0
  - Safety mask did not block all learned choices.
  - Decision table case is B: oracle positive, learned composite/distill not positive.
  - Do not jump to bounded ΔUpdateParams yet.

Tasks:
  1. Add a provenance addendum for Repair5E:
       outputs/reports/phase5p5_repair5e_preflight_provenance_addendum.md
       outputs/reports/phase5p5_repair5e_preflight_provenance_addendum.json
     Explain that the preflight report was generated before commit df8801c and records internal commit f27ac22 with dirty state tracked-dirty_untracked-present. Do not falsify old report files.

  2. Build a Case-B transfer analysis:
       scripts/analyze_repair5e_caseb_transfer.py
       outputs/reports/phase5p5_repair5e_caseb_transfer_analysis.md
       outputs/reports/phase5p5_repair5e_caseb_transfer_analysis.json
       outputs/tables/phase5p5_repair5e_caseb_decision_alignment.csv
       outputs/tables/phase5p5_repair5e_caseb_rule_outcomes.csv

     Required analysis:
       - Compare LaCAM*+LTM, Repair3, Repair5D distilled, and oracle/static proxy per scenario.
       - Identify every Repair5D distilled worse-than-LTM case.
       - Quantify selected-rule distribution mismatch.
       - Check whether Repair5D distilled collapses toward commit_heavy under preflight runtime features.
       - Add feature OOD diagnostics using distill mean/std.
       - Compare Repair3 vs Repair5D distilled rule choices and outcomes.

  3. Implement exactly one targeted diagnostic repair, chosen by the analysis:
       Preferred A: Python-side true Repair5D composite diagnostic selector.
       Preferred B: closed-loop-aware second-stage reranker/distill probe using static-proxy support rows.
       Preferred C: OOD/defer guard around the existing distill bridge.

     All candidates must be diagnostic-only, log every learned update, include force-additive parity, and forbid Phase5.5/Phase6.

  4. Rerun the same small preflight only after the analysis and one targeted repair:
       maps: random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
       agents: 50, 100
       instances_per_setting: 3
       time_limit_sec: 3.0
       ltm_max_iterations: 4

     Required methods:
       LaCAM*
       LaCAM*+LTM
       always_additive_defer
       Repair3 safe runtime
       old Repair5D composite distilled
       new Repair5E.1 targeted candidate
       force-additive/defer parity for the new candidate
       oracle/static proxy

  5. Write:
       outputs/reports/phase5p5_repair5e_caseb_preflight_report.md
       outputs/reports/phase5p5_repair5e_caseb_preflight_summary.json
       outputs/tables/phase5p5_repair5e_caseb_preflight_summary.csv
       outputs/tables/phase5p5_repair5e_caseb_preflight_paired.csv

  6. Verification:
       python -m pytest tests/test_repair5e_composite_preflight.py
       python -m pytest

Diagnostic pass criteria:
  - success not lower than LaCAM*+LTM
  - mean ratio delta vs LTM <= 0
  - better/equal/worse improves over old Repair5D distilled
  - ratio_worse_than_ltm_groups <= 1/6
  - force-additive parity remains equal to LTM

Do not claim Phase5.5 or Phase6 from this evidence.
```
