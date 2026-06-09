# Phase4F Repair5B Failure Decomposition

Date: 2026-05-31 09:25:24

## Code State

- branch: `phase4f5p5-stable-attention-lau`
- commit: `7bf0b0a`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `C:\PROGRAMING\czr004\artifacts\teacher\laur\full_repair5_attention_native_expand5000_rawtrace_hightoken\update_labels\phase4_laur_attention_native_expand5000_rawtrace_hightoken_dataset.jsonl.zst`
- repair5 eval CSVs: `30`
- repair3 eval CSVs: `1`

## Hard-Case Replay

- index: `C:\PROGRAMING\czr004\artifacts\teacher\laur\repair5_hardcase_index.jsonl`
- cases: `5000`
- distribution: `{'false_negative_harmful_selected': 178, 'high_margin_avoidable_defer': 1081, 'rule_family_confusion': 1194, 'top3_miss_high_utility': 753, 'wrong_rule_top1_but_top3_contains_target': 1794}`

## Oracle Gap

- validation oracle_vs_additive_mean_delta: `0.07490846923774867`
- validation oracle_high_margin_capture_possible: `1.0`
- decision: `continue_hierarchical_attention_native_laur`

## Best Completed Comparators

| comparator | top1 | top3 | recall proxy | precision proxy | high-margin capture | regret |
|---|---:|---:|---:|---:|---:|---:|
| `phase4f_repair5_expand5000_nextwave_normal_attn_linear_head_rank_safe` | 0.1532 | 0.7164 | 0.9816 | 0.7953 | 0.2581 | 0.0281 |
| `phase4f_repair5_expand5000_postnext_normal_attn_mlp_head_top1_focus_perrule` | 0.1035 | 0.7101 | 0.9934 | 0.8399 | 0.1903 | 0.0284 |
| `phase4f_repair5_rawtrace_edge_sf_target_ce1_margin1_hm4` | 0.1911 | 0.7099 | 0.9717 | 0.9150 | 0.2811 | n/a |
| `phase4f_repair5_rawtrace_edge_sf_global_pair_neg2_anti2` | 0.2321 | 0.7065 | 0.9237 | 0.9760 | 0.4378 | n/a |
| `phase4f_repair5_rawtrace_edge_sf_target_ce2_margin1_hm3` | 0.1433 | 0.7065 | 0.9782 | 0.8453 | 0.2541 | n/a |
| `phase4f_repair5_expand5000_postnext_hightoken_attn_mlp_head_rank_recall_perrule` | 0.1366 | 0.7060 | 0.9803 | 0.8215 | 0.2419 | 0.0286 |
| `phase4f_repair5_expand5000_nextwave_normal_attn_mlp_head_highcap_candidate_safe` | 0.1656 | 0.6998 | 0.9619 | 0.8268 | 0.3161 | 0.0286 |
| `phase4f_repair5_expand5000_hightoken_ht_mlp_target_global` | 0.1449 | 0.6998 | 0.9738 | 0.8530 | 0.2839 | 0.0291 |
| `phase4f_repair5_rawtrace_edge_sf_target_margin2_rank3_safe5` | 0.2218 | 0.6894 | 0.9717 | 0.8932 | 0.3568 | n/a |
| `phase4f_repair5_rawtrace_edge_sf_global_rank3_anti3` | 0.1843 | 0.6894 | 0.9847 | 0.8431 | 0.3027 | n/a |
| `phase4f_repair5_rawtrace_edge_sf_global_pair_rank2_anti2` | 0.1877 | 0.6894 | 0.9804 | 0.8911 | 0.2595 | n/a |
| `phase4f_repair5_expand5000_followup_ex5000_follow_pair_focal_m035_lh4` | 0.1284 | 0.6832 | 0.9869 | 0.8556 | 0.1806 | 0.0288 |

## Boundary

This diagnostic is offline-only. It does not lower Repair5B gates and does not allow Phase5.5 or Phase6.
