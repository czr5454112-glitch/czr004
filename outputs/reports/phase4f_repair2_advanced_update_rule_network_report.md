# Phase4F Repair2 Advanced Update-Rule Network Report

Date: 2026-05-27

## Summary

Repair2 was completed as an offline Phase4F attempt. It implemented the GPT Pro recommendation in a scoped way: cleaned executable rule targets, built a token/rule-aware v2 dataset, trained LAU-EdgeTraceTransformer-v2 and LAU-SetTransformer-v2 variants, and evaluated safety-gated rule selection.

Repair2 did not pass the Phase4F performance gate. It should not advance into Phase5 learned runtime.

## Inputs

- source artifacts: `full_repair1`
- checkpoint rows: `2985`
- probe rows: `24216`
- v2 dataset rows: `2985`
- train rows: `2526`
- validation rows: `459`
- validation non-neutral checkpoints: `359`
- raw trace backup: verified `.zst` exists locally, but this Repair2 run used checkpoint top-k edge tokens plus trace-count fallback tokens first.

## Implemented

- `phase4_laur_update_dataset_v2`
- executable rule cleanup:
  - `neutral_additive -> additive_ltm`
  - original label preserved as `rule_class_original`
  - neutral semantic preserved as `is_neutral_label`
- per-rule targets:
  - `rule_delta_vector`
  - `rule_harmful_vector`
  - `soft_rule_target`
- models:
  - `LAU-EdgeTraceTransformer-v2`
  - `LAU-SetTransformer-v2`
- losses:
  - listwise soft target loss
  - pairwise margin ranking
  - delta regression
  - per-rule harmful BCE
  - family auxiliary loss
  - additive fallback regularization

## Main Results

| attempt | validation top1 | validation top3 | harmful recall | harmful precision | mean selected delta | gate |
|---|---:|---:|---:|---:|---:|---|
| repair1 MLP baseline | 0.3072 | 0.6427 | 0.9538 | 0.4015 | 0.0110 | fail top1/top3 |
| EdgeTrace t0.010 mix0.55 | 0.3050 | 0.5163 | 0.9538 | 0.4253 | 0.0070 | fail top1/top3 |
| Set t0.010 mix0.55 | 0.3159 | 0.5033 | 0.9711 | 0.3916 | 0.0050 | fail top1/top3 |
| EdgeTrace t0.005 mix0.70 | 0.3094 | 0.4989 | 0.9711 | 0.3871 | 0.0045 | fail top1/top3 |
| Set t0.005 mix0.70 | 0.3094 | 0.5033 | 0.9827 | 0.3953 | 0.0080 | fail top1/top3 |

Best gate-compatible Repair2 top1 was `0.3159`, but top3 was only `0.5033`.

The threshold sweep found the best top3 at `0.6580` for `edge_t005_hard070` with harmful threshold `0.30`, but harmful recall dropped to `0.6127`, so that setting is not gate-compatible.

## Gate Decision

Repair2 fails Phase4F:

- validation top1: best `0.3159` vs required `0.35`
- validation top3: best gate-compatible `0.5033` vs required `0.70`
- harmful recall: pass in gate-compatible setting
- harmful precision: pass in gate-compatible setting
- mean selected delta: pass in gate-compatible setting
- validation non-neutral count: pass

## Interpretation

The result is a useful negative result. Rule-conditioned attention did not solve the held-out exact-rule ranking problem using only aggregate checkpoint features, top-k edge tokens, rule params, and trace-count fallback tokens. It slightly improved top1 over repair1 in one setting, but it lost too much top3 ranking quality.

The likely next Phase4F blockers are label/probe ambiguity and target formulation, not just MLP capacity. A future attempt should inspect near-tie probe deltas, consider family-first labels or calibrated tie groups, and only then decide whether decoding the full raw trace into richer event tokens is worth the extra data cost.

## Boundary

No Phase5 runtime integration was done. No C++ solver behavior was changed. The Phase4F gate was not lowered.
