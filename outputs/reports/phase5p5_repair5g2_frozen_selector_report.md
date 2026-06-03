# Phase5.5 Repair5G.2 Frozen Selector Spec

Frozen before looking at IDs 46..65. Diagnostic-only; Phase5.5 and Phase6 remain closed.

- `selected_selector_type`: `map_agent_group_static_selector`
- `selected_static_candidate`: `repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75`
- `selected_group_selector_default_candidate`: `repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75`
- `selected_c_equiv_baseline`: `repair5g_dual_c_equiv_c100_b100_w075_d100`
- `support_dev_data_used`: `{'support_ids': '1..25', 'development_validation_ids': '26..45', 'support_long_csv': 'outputs\\tables\\phase5p5_repair5g2_support_utility_long.csv', 'g1_dev_long_csv': 'outputs\\tables\\phase5p5_repair5g1_dev_utility_long.csv', 'train_contexts_csv': 'outputs\\tables\\phase5p5_repair5g2_selector_train_contexts.csv'}`
- `final_ids_used_for_tuning`: `False`
- `phase5p5_allowed`: `False`
- `phase6_allowed`: `False`

## Group Rules

- `maze-32-32-4` a50: `repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75`
- `maze-32-32-4` a100: `repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p5`
- `random-32-32-20` a50: `repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75`
- `random-32-32-20` a100: `repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75`
- `warehouse-10-20-10-2-1` a50: `repair5g_dual_c_equiv_c100_b100_w075_d095`
- `warehouse-10-20-10-2-1` a100: `repair5g_dual_c_equiv_additive`
