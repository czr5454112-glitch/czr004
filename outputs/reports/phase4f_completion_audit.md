# Phase4F Completion Audit

Date: 2026-05-27

## Scope Audited

This audit checks whether the LAU/LAUR-LTM Phase4F offline objective is complete enough to close Phase4F and move future work into Phase5 planning.

It does not claim Phase5 runtime integration, closed-loop learned-runtime speedup, or paper-level runtime performance.

## Authoritative Gate

The Phase4F offline gate in `phase4_6_laur_ltm_codex_execution_plan.md` requires:

```text
validation non-neutral checkpoints >= 50
rule_top1_accuracy >= 0.35
rule_top3_accuracy >= 0.70
harmful_update_recall >= 0.80
harmful_update_precision >= 0.30
predicted-rule validation mean delta_ratio_vs_additive >= 0.0
neutral-additive behavior documented
```

## Primary Evidence

Primary candidate:

```text
configs/phase4/laur_ltm_full_repair3_stable_tie001.yaml
artifacts/teacher/laur/full_repair3_stable_targets/update_labels/phase4_laur_update_dataset_full_repair3_stable_tie001.jsonl
artifacts/models/laur_ltm/full_repair3_stable_tie001_mlp/laur_mlp_v1_weights.json
outputs/reports/phase4f_repair3_stable_tie001_performance_gate.json
outputs/reports/phase4f_repair3_stable_target_report.md
```

Git backup:

```text
43b242a phase4f: add repair3 stable target pass
293ba8f phase4f: record repair3 fallback calibration
origin/phase4-laur-ltm contains both commits
```

## Gate Checklist

| requirement | evidence | status |
|---|---|---|
| validation non-neutral checkpoints >= 50 | `validation_non_neutral = 293` in `phase4f_repair3_stable_tie001_performance_gate.json` | pass |
| rule top1 >= 0.35 | `0.3899782135` | pass |
| rule top3 >= 0.70 | `0.7690631808` | pass |
| harmful recall >= 0.80 | `0.9421965318` | pass |
| harmful precision >= 0.30 | `0.3908872902` | pass |
| predicted-rule validation mean delta >= 0.0 | `0.0081308431` | pass |
| neutral/additive behavior documented | stable-target tie policy and additive fallback behavior documented in `phase4f_repair3_stable_target_report.md` | pass |
| schema validation | eval gate reports `schema_validation_passes = true`; stable dataset summary reports schema errors `0` | pass |
| code/test sanity | latest focused Phase4F test run: `25 passed, 1 warning` | pass |
| git backup | commits pushed to `origin/phase4-laur-ltm` through `293ba8f` | pass |

## Robustness Notes

Additional Repair3 seeds `103` and `107` preserve top1/top3/safety gates but their raw validation mean selected delta is slightly negative:

```text
seed 103 raw mean delta = -0.0010
seed 107 raw mean delta = -0.0012
```

This does not invalidate the seed-61 Phase4F offline candidate pass because multi-seed unanimity was not part of the Phase4F gate. It does, however, constrain the next phase.

The conservative fallback diagnostic found a common safety threshold `0.30` that makes validation mean delta after additive fallback positive for all checked Repair3 seeds:

```text
seed 61  after fallback = 0.0064
seed 103 after fallback = 0.0031
seed 107 after fallback = 0.0014
```

This is recorded in:

```text
outputs/reports/phase4f_repair3_conservative_fallback_report.md
```

## Completion Decision

Phase4F offline work is complete under the current project gate:

- Repair1 repaired safety but failed ranking.
- Repair2 advanced rule-attention was a documented negative result.
- Repair3 stable-target formulation satisfies the Phase4F offline gate.
- Conservative fallback calibration is recorded for Phase5 startup.
- Required artifacts are committed and pushed.

Phase4F should now be closed as:

```text
Phase4F offline stable-target pass, with Phase5 conservative fallback precondition.
```

## Boundaries

The following are not complete and must remain Phase5 or later work:

- C++ runtime integration.
- `--laur-disable` / `--laur-force-additive` parity.
- Closed-loop solver smoke.
- Learned-runtime ablation.
- Paper-level runtime performance claim.

Do not claim learned runtime performance until Phase5 runtime gates pass.
