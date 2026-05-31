# Phase4F Repair5C Execution Summary

Date: 2026-05-31

## Completed Scope

Repair5C stayed inside LAUR / learned `UpdateLTM` only. No PIBT, LaCAM*, conflict semantics, candidate generation, pruning, restart, or solver-runtime semantics were changed.

Completed queue items:

- Q1.1 composite inference from existing models.
- Q1.2 train-split calibrated global/per-rule/per-family safety comparison.
- Q1.3 top3-to-top1 hardcase path via an offline top-k reranker.
- Q1.4 diagnostic closed-loop preflight plan.
- Q2.1 short seed61 top3-to-top1 reranker training/evaluation.

Phase5.5 and Phase6 remain forbidden.

## Main Artifacts

- `src/eval/eval_laur_repair5_composite_inference.py`
- `src/eval/calibrate_laur_repair5_per_rule_safety.py`
- `src/models/laur_attention_reranker.py`
- `src/train/train_laur_attention_reranker.py`
- `src/eval/eval_laur_attention_reranker.py`
- `scripts/run_phase5p5_laur_diagnostic_preflight.py`
- `outputs/reports/phase4f_repair5c_composite_inference.md`
- `outputs/reports/phase4f_repair5_safety_calibration_comparison.md`
- `outputs/reports/phase4f_repair5c_top3_reranker_eval.md`
- `outputs/reports/phase5p5_laur_diagnostic_preflight_plan.md`

## Key Results

Composite inference on 762 validation checkpoints:

| mode | top1 | top3 | selected-vs-additive | harmful recall | harmful precision | high-margin capture | additive/defer |
|---|---:|---:|---:|---:|---:|---:|---:|
| top3_per_rule_safety_utility | 0.4141 | 0.7060 | 0.00900 | 0.7837 | 0.2896 | 0.3903 | 0.3346 |
| anti_decision_top3_per_rule_safety | 0.1408 | 0.7060 | 0.00395 | 0.7837 | 0.2896 | 0.2581 | 0.6614 |
| top3_anti_margin_per_family_safety | 0.1781 | 0.7060 | 0.00456 | 0.7971 | 0.2891 | 0.3065 | 0.5866 |
| oracle_decision_learned_rerank | 0.2381 | 0.7060 | 0.00643 | 0.7837 | 0.2896 | 0.3484 | 0.6207 |
| learned_decision_oracle_safety | 0.2754 | 0.7060 | 0.04261 | 1.0000 | 1.0000 | 0.6677 | 0.3648 |

Safety calibration, calibrated on train and evaluated on validation:

- global: recall 0.8064, precision 0.2882, pass false.
- per-rule: recall 0.7837, precision 0.2896, pass false.
- per-family: recall 0.7971, precision 0.2891, pass false.

Short Repair5C top3 reranker validation:

- top1 among candidates: 0.4304.
- target in candidates: 0.6430.
- selected-vs-additive delta: 0.00996.
- utility regret: 0.01776.
- selected harmful rate: 0.1142.
- high-margin capture proxy: 0.7452.

## Interpretation

The largest failure mode is now confirmed as composition/reranking plus safety calibration, not absence of signal. Top-k reranking and utility-aware composition can recover useful selected-vs-additive delta, but strict safety still misses Phase5.5 thresholds. Oracle safety produces a large offline delta, so the next useful diagnostic is a tiny oracle-transfer closed-loop preflight, not runtime promotion.

P1 bounded UpdateParams and richer trace/LTM features remain conditional next work. They should be started only after the diagnostic preflight clarifies whether the offline oracle/reranker advantage transfers to closed-loop behavior.
