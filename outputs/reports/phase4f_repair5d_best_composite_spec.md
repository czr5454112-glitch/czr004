# Phase4F Repair5D Best Composite Spec

This freezes the Repair5D composite as diagnostic-only input for Repair5E closed-loop transfer tests.

## Boundary

- Phase5.5 allowed: `False`
- Phase6 allowed: `False`
- Scope: LAUR / learned `UpdateLTM` only
- This spec does not change PIBT, LaCAM*, conflict semantics, candidate generation, or restart policy.

## Composite

- mode: `rank_model_top5_safety_model_per_rule_utility_rerank`
- composite_mode: `top3_per_rule_safety_utility`
- top_k: `5`
- ranking_csv: `C:\PROGRAMING\czr004\outputs\tables\phase4f_repair5_expand5000_nextwave_normal_attn_linear_head_rank_safe_eval_seed61.csv`
- safety_csv: `C:\PROGRAMING\czr004\outputs\tables\phase4f_repair5_expand5000_hightoken_ht_mlp_target_global_eval_seed61.csv`
- anti_csv: `C:\PROGRAMING\czr004\outputs\tables\phase4f_repair5_expand5000_postnext_hightoken_attn_mlp_head_rank_recall_perrule_eval_seed61.csv`
- safety_calibration: `C:\PROGRAMING\czr004\outputs\reports\phase4f_repair5_per_rule_safety_calibration.json`

## Offline Validation

| metric | value |
|---|---:|
| sample_count | 762 |
| rule_top1 | 0.4989648033126294 |
| rule_top3 | 0.8716356107660456 |
| safe_utility_top1 | 0.5328083989501312 |
| safe_utility_top3 | 0.7139107611548556 |
| harmful_recall | 0.8010680907877169 |
| harmful_precision | 0.30045067601402103 |
| high_margin_capture | 0.41935483870967744 |
| selected_vs_additive_delta | 0.008891221060077253 |
| selected_vs_additive_utility | 0.008654875096387227 |
| utility_regret_to_oracle | 0.021850990959392625 |
| selected_harmful_rate | 0.005249343832020997 |
| global_additive_or_defer_rate | 0.29133858267716534 |

## Runtime Use

Repair5E may use this spec for native export or diagnostic distillation only. It must not be treated as Phase5.5 or Phase6 evidence without closed-loop validation against `LaCAM*+LTM`.
