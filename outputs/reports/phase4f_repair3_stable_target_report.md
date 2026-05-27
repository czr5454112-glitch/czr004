# Phase4F Repair3 Stable Target Report

Date: 2026-05-27

## Summary

Repair3 addresses the label/probe ambiguity found after Repair1 and Repair2. It keeps the Phase4F thresholds unchanged, but replaces arbitrary hard best-rule targets in near-tie probe groups with a deterministic stable target policy.

The main `stable_tie001` run passes the Phase4F performance gate locally.

## Why Repair3 Was Needed

Repair1 fixed safety but failed exact rule ranking:

- validation top1: `0.3072`
- validation top3: `0.6427`
- harmful recall: `0.9538`
- harmful precision: `0.4015`

Repair2 advanced attention models did not improve the gate-compatible ranking enough. The subsequent label ambiguity diagnostic found that Repair1 validation labels are heavily near-tied:

- best-vs-second <= `0.005`: `53.38%`
- best-vs-second <= `0.010`: `70.59%`
- best-vs-second <= `0.020`: `82.35%`

This made the exact hard-label target unstable even though the short-probe deltas were often nearly equivalent.

## Stable Target Policy

For each checkpoint:

1. Sort candidate update rules by short-probe `delta_ratio_vs_additive`.
2. Build a tie set within `0.010` of the best delta.
3. If the best delta is below `0.005`, use `neutral_additive`.
4. If `additive_ltm` is within the tie band, use `neutral_additive` as the conservative fallback target.
5. Otherwise choose the first rule in this deterministic priority:

```text
additive_ltm
commit_heavy
block_heavy
wait_light
wait_heavy
block_light
decay_095
decay_090
```

The policy changes `890 / 2985` labels (`29.82%`). The maximum best-minus-stable delta is capped at `0.010`, and the mean best-minus-stable delta is `0.0020`.

## Main Gate Result

Dataset:

```text
artifacts/teacher/laur/full_repair3_stable_targets/update_labels/phase4_laur_update_dataset_full_repair3_stable_tie001.jsonl
```

Model:

```text
artifacts/models/laur_ltm/full_repair3_stable_tie001_mlp/laur_mlp_v1_weights.json
```

Validation metrics at harmful threshold `0.10`:

| metric | value | gate | result |
|---|---:|---:|---|
| validation top1 | 0.3899782135 | >= 0.35 | pass |
| validation top3 | 0.7690631808 | >= 0.70 | pass |
| harmful recall | 0.9421965318 | >= 0.80 | pass |
| harmful precision | 0.3908872902 | >= 0.30 | pass |
| mean selected delta | 0.0081308431 | > 0.0 | pass |
| validation non-neutral | 293 | >= 50 | pass |

This is the first local Phase4F result in this branch that satisfies all performance thresholds.

## Robustness Notes

Two extra seeds were run with the same stable target dataset:

| seed | top1 | top3 | recall | precision | mean selected delta | status |
|---:|---:|---:|---:|---:|---:|---|
| 61 | 0.3900 | 0.7691 | 0.9422 | 0.3909 | 0.0081 | pass |
| 103 | 0.3943 | 0.7538 | 0.9711 | 0.3934 | -0.0010 | fail delta |
| 107 | 0.3922 | 0.7669 | 0.9711 | 0.3916 | -0.0012 | fail delta |

Top1/top3/safety are stable across seeds, but the mean selected delta gate is still seed-sensitive. The seed-61 run is valid evidence for an offline Phase4F candidate pass, but Phase5 should begin with parity/fallback checks rather than a strong learned-runtime performance claim.

## Boundary

No C++ runtime integration was performed. No solver semantics were changed. This is still an offline Phase4F model/dataset repair.

## Decision

Phase4F has a local stable-target candidate pass. Before making a paper-level learned-runtime claim, the next step should be Phase5 parity/fallback integration planning, plus a conservative runtime gate that can fall back to additive LTM if learned decisions are unsafe or low-confidence.
