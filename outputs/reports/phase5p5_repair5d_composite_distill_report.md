# Phase5.5 Repair5D Composite Distill Diagnostic

Date: 2026-05-31 14:21:50

This is diagnostic-only distillation into the existing LAUR MLP runtime format. It does not permit Phase5.5 or Phase6.

## Outputs

- weights_json: `C:\PROGRAMING\czr004\artifacts\models\laur_ltm\repair5d_composite_distilled\laur_mlp_v1_weights.json`
- runtime_dir: `C:\PROGRAMING\czr004\artifacts\models\laur_ltm\repair5d_composite_distilled`
- decisions_csv: `C:\PROGRAMING\czr004\outputs\tables\phase5p5_repair5d_composite_distill_decisions.csv`

## Metrics

### train

- sample_count: `4194`
- rule_top1: `0.6237482117310443`
- target_non_additive_rate: `0.6659513590844063`
- predicted_non_additive_rate: `0.6638054363376252`
- target_additive_or_defer_rate: `0.3340486409155937`
- target_selected_harmful_rate: `0.004768717215069146`
- harmful_precision: `0.0`
- harmful_recall: `0.0`
- predicted_rule_distribution: `{'additive_ltm': 1410, 'block_heavy': 863, 'block_light': 121, 'commit_heavy': 763, 'decay_090': 29, 'decay_095': 354, 'wait_heavy': 211, 'wait_light': 443}`
- target_rule_distribution: `{'additive_ltm': 1401, 'block_heavy': 673, 'block_light': 194, 'commit_heavy': 508, 'decay_090': 195, 'decay_095': 467, 'wait_heavy': 396, 'wait_light': 360}`

### validation

- sample_count: `762`
- rule_top1: `0.473753280839895`
- target_non_additive_rate: `0.7086614173228346`
- predicted_non_additive_rate: `0.7178477690288714`
- target_additive_or_defer_rate: `0.29133858267716534`
- target_selected_harmful_rate: `0.005249343832020997`
- harmful_precision: `0.0`
- harmful_recall: `0.0`
- predicted_rule_distribution: `{'additive_ltm': 215, 'block_heavy': 158, 'block_light': 59, 'commit_heavy': 174, 'decay_095': 80, 'wait_heavy': 32, 'wait_light': 44}`
- target_rule_distribution: `{'additive_ltm': 222, 'block_heavy': 144, 'block_light': 45, 'commit_heavy': 94, 'decay_090': 45, 'decay_095': 67, 'wait_heavy': 87, 'wait_light': 58}`

## Boundary

- phase5p5_allowed: `False`
- phase6_allowed: `False`
- This is a temporary transfer-test bridge, not a formal Repair5D native export.
