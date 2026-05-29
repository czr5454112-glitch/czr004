# Phase4F Repair5 Layered Gate Diagnostic

This report is diagnostic only. It does not lower the strict Repair5 runtime/final gate.

## Counts

- summaries: `27`
- development pass: `0`
- promotion-candidate pass: `0`
- strict seed gate pass: `0`
- Phase5.5 allowed: `False` from this diagnostic report
- Phase6 allowed: `False`

## Top Results

| variant | seed | dev | candidate | strict seed | top1 | top3 | recall | precision | anti capture | anti pass | interpretation |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---|---|
| `phase4f_repair5_rawtrace_edge_sf_target_ce1_margin1_hm4` | `61` | False | False | False | 0.1911 | 0.7099 | 0.7460 | 0.2557 | 0.2811 | False | `diagnostic_fail` |
| `phase4f_repair5_rawtrace_edge_sf_global_pair_neg2_anti2` | `61` | False | False | False | 0.2321 | 0.7065 | 0.5767 | 0.3134 | 0.4378 | True | `diagnostic_fail` |
| `phase4f_repair5_rawtrace_edge_sf_target_ce2_margin1_hm3` | `61` | False | False | False | 0.1433 | 0.7065 | 0.7872 | 0.2779 | 0.2541 | False | `diagnostic_fail` |
| `phase4f_repair5_expand5000_hightoken_ht_mlp_target_global` | `61` | False | False | False | 0.1449 | 0.6998 | 0.7623 | 0.3143 | 0.2839 | False | `diagnostic_fail` |
| `phase4f_repair5_rawtrace_edge_sf_target_margin2_rank3_safe5` | `61` | False | False | False | 0.2218 | 0.6894 | 0.8146 | 0.2705 | 0.3568 | False | `diagnostic_fail` |
| `phase4f_repair5_rawtrace_edge_sf_global_pair_rank2_anti2` | `61` | False | False | False | 0.1877 | 0.6894 | 0.7460 | 0.2900 | 0.2595 | False | `diagnostic_fail` |
| `phase4f_repair5_rawtrace_edge_sf_global_rank3_anti3` | `61` | False | False | False | 0.1843 | 0.6894 | 0.8146 | 0.2751 | 0.3027 | False | `diagnostic_fail` |
| `phase4f_repair5_expand5000_followup_ex5000_follow_pair_focal_m035_lh4` | `61` | False | False | False | 0.1284 | 0.6832 | 0.8051 | 0.2751 | 0.1806 | False | `diagnostic_fail` |
| `phase4f_repair5_rawtrace_edge_sf_pair_m050_lh3_neg2` | `61` | False | False | False | 0.1536 | 0.6826 | 0.7437 | 0.2949 | 0.3027 | False | `diagnostic_fail` |
| `phase4f_repair5_expand5000_followup_ex5000_follow_target_ce2_margin1_hm3` | `61` | False | False | False | 0.1615 | 0.6791 | 0.8652 | 0.2759 | 0.2968 | False | `diagnostic_fail` |
| `phase4f_repair5_expand5000_followup_ex5000_follow_target_margin2_rank3_safe5` | `61` | False | False | False | 0.1718 | 0.6749 | 0.7303 | 0.3133 | 0.3355 | False | `diagnostic_fail` |
| `phase4f_repair5_expand5000_hightoken_ht_linear_target_global` | `61` | False | False | False | 0.1739 | 0.6687 | 0.8051 | 0.3006 | 0.2935 | False | `diagnostic_fail` |
| `phase4f_repair5_expand5000_ex5000_mlp_safety_light` | `61` | False | False | False | 0.1967 | 0.6667 | 0.8224 | 0.2844 | 0.2903 | False | `diagnostic_fail` |
| `phase4f_repair5_expand5000_ex5000_linear_target_global` | `61` | False | False | False | 0.1863 | 0.6646 | 0.7370 | 0.3084 | 0.3677 | False | `diagnostic_fail` |
| `phase4f_repair5_expand5000_followup_ex5000_follow_global_rank3_anti3` | `61` | False | False | False | 0.1843 | 0.6646 | 0.7477 | 0.3068 | 0.3419 | False | `diagnostic_fail` |
| `phase4f_repair5_expand5000_ex5000_mlp_target_global` | `61` | False | False | False | 0.2133 | 0.6625 | 0.6769 | 0.3203 | 0.3806 | False | `diagnostic_fail` |
| `phase4f_repair5_rawtrace_edge_sf_pair_focal_m035_lh4` | `61` | False | False | False | 0.1809 | 0.6621 | 0.8169 | 0.2818 | 0.2757 | False | `diagnostic_fail` |
| `phase4f_repair5_rawtrace_edge` | `61` | False | False | False | 0.2457 | 0.6553 | 0.1465 | 0.2397 | 0.5351 | True | `diagnostic_fail` |
| `phase4f_repair5_rawtrace_edge_sf_hpw1_lh12` | `61` | False | False | False | 0.2423 | 0.6553 | 0.0755 | 0.3084 | 0.5514 | True | `diagnostic_fail` |
| `phase4f_repair5_attention_native` | `107` | False | False | False | 0.2287 | 0.6553 | 0.2265 | 0.2532 | 0.4649 | True | `diagnostic_fail` |
| `phase4f_repair5_rawtrace_edge_sf_hpw2_lh8` | `61` | False | False | False | 0.1911 | 0.6451 | 0.2311 | 0.2936 | 0.5081 | True | `diagnostic_fail` |
| `phase4f_repair5_rawtrace_edge_sf_pair_m035_lh4_neg1` | `61` | False | False | False | 0.2082 | 0.6416 | 0.6842 | 0.3115 | 0.3351 | False | `diagnostic_fail` |
| `phase4f_repair5_rawtrace_edge` | `103` | False | False | False | 0.2389 | 0.6143 | 0.3753 | 0.3410 | 0.4919 | True | `diagnostic_fail` |
| `phase4f_repair5_attention_native` | `103` | False | False | False | 0.2287 | 0.6109 | 0.2426 | 0.3003 | 0.4811 | True | `diagnostic_fail` |
| `phase4f_repair5_rawtrace_edge_sf_hpw1_lh8` | `61` | False | False | False | 0.2116 | 0.5939 | 0.1327 | 0.3372 | 0.4649 | True | `diagnostic_fail` |
| `phase4f_repair5_attention_native` | `61` | False | False | False | 0.2150 | 0.5768 | 0.2815 | 0.2617 | 0.4649 | True | `diagnostic_fail` |
| `phase4f_repair5_rawtrace_edge` | `107` | False | False | False | 0.2048 | 0.5734 | 0.1396 | 0.2574 | 0.4378 | True | `diagnostic_fail` |

## Boundary

Development or promotion-candidate pass means only that the direction deserves more analysis, larger training, or tightly scoped closed-loop smoke planning. It is not runtime permission. Phase5.5 still requires the strict original Phase4F, attention-native, safety, anti-escape, and multi-seed final gate. Phase6 requires later closed-loop learned-benefit evidence.
