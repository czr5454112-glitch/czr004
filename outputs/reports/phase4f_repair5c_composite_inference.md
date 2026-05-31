# Phase4F Repair5C Composite Inference Diagnostic

Date: 2026-05-31 12:14:12

## Boundary

This is no-retraining diagnostic evidence only. It does not permit Phase5.5 runtime promotion and does not relax any Repair5 gate.

## Inputs

- dataset: `C:\PROGRAMING\czr004\artifacts\teacher\laur\full_repair5_attention_native_expand5000_rawtrace_hightoken\update_labels\phase4_laur_attention_native_expand5000_rawtrace_hightoken_dataset.jsonl.zst`
- ranking_csv: `C:\PROGRAMING\czr004\outputs\tables\phase4f_repair5_expand5000_postnext_hightoken_attn_mlp_head_rank_recall_perrule_eval_seed61.csv`
- safety_csv: `C:\PROGRAMING\czr004\outputs\tables\phase4f_repair5_expand5000_postnext_hightoken_attn_mlp_head_rank_recall_perrule_eval_seed61.csv`
- anti_csv: `C:\PROGRAMING\czr004\outputs\tables\phase4f_repair5_expand5000_postnext_hightoken_attn_mlp_head_rank_recall_perrule_eval_seed61.csv`
- calibration_json: `C:\PROGRAMING\czr004\outputs\reports\phase4f_repair5_per_rule_safety_calibration.json`

## Mode Metrics

| mode | samples | top1 | top3 | safe utility top1 | regret | selected-vs-additive | harm recall | harm precision | high-margin capture | additive/defer |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| top3_per_rule_safety_utility | 762 | 0.414079 | 0.706004 | 0.425197 | 0.022927 | 0.009003 | 0.783712 | 0.289591 | 0.390323 | 0.334646 |
| anti_decision_top3_per_rule_safety | 762 | 0.140787 | 0.706004 | 0.104987 | 0.028700 | 0.003951 | 0.783712 | 0.289591 | 0.258065 | 0.661417 |
| top3_anti_margin_per_family_safety | 762 | 0.178054 | 0.706004 | 0.133858 | 0.028160 | 0.004557 | 0.797063 | 0.289104 | 0.306452 | 0.586614 |
| oracle_decision_learned_rerank | 762 | 0.238095 | 0.706004 | 0.150919 | 0.025452 | 0.006432 | 0.783712 | 0.289591 | 0.348387 | 0.620735 |
| learned_decision_oracle_safety | 762 | 0.275362 | 0.706004 | 0.215223 | 0.015401 | 0.042605 | 1.000000 | 1.000000 | 0.667742 | 0.364829 |

## Interpretation

Use this to decide whether selection composition or a second-stage reranker is worth training. If all modes stay flat, the next repair should focus on output space or representation.
