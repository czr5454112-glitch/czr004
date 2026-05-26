# Phase4F LAU-LTM Ensemble Offline Evaluation

## Inputs

- dataset: `C:\PROGRAMING\czr004\artifacts\teacher\laur\full\update_labels\phase4_laur_update_dataset_full.jsonl`
- models:
  - `C:\PROGRAMING\czr004\artifacts\models\laur_ltm\soft_label_sweep\soft_t005_mix07_drop_top_h64\laur_mlp_v1_weights.json`
  - `C:\PROGRAMING\czr004\artifacts\models\laur_ltm\feature_drop_sweep\drop_top_h64_s43\laur_mlp_v1_weights.json`
  - `C:\PROGRAMING\czr004\artifacts\models\laur_ltm\feature_drop_sweep\drop_top_h48_s41\laur_mlp_v1_weights.json`
  - `C:\PROGRAMING\czr004\artifacts\models\laur_ltm\feature_drop_sweep\drop_top_h32_s59\laur_mlp_v1_weights.json`
  - `C:\PROGRAMING\czr004\artifacts\models\laur_ltm\feature_drop_sweep\drop_top_drift_h64\laur_mlp_v1_weights.json`
- harmful_threshold: `0.1`

## Metrics

### all

- sample_count: `1897`
- rule_top1_accuracy: `0.4765419082762256`
- rule_top3_accuracy: `0.7981022667369531`
- harmful_update_precision: `0.47761194029850745`
- harmful_update_recall: `0.9820971867007673`
- predicted_rule_validation_mean_delta_ratio: `0.02005698450337172`
- neutral_additive_rate: `0.26515550869794413`

### train

- sample_count: `1439`
- rule_top1_accuracy: `0.5496872828353023`
- rule_top3_accuracy: `0.8693537178596248`
- harmful_update_precision: `0.4966499162479062`
- harmful_update_recall: `0.9866888519134775`
- predicted_rule_validation_mean_delta_ratio: `0.02295405296516662`
- neutral_additive_rate: `0.2425295343988881`

### validation

- sample_count: `458`
- rule_top1_accuracy: `0.24672489082969432`
- rule_top3_accuracy: `0.574235807860262`
- harmful_update_precision: `0.4227053140096618`
- harmful_update_recall: `0.9668508287292817`
- predicted_rule_validation_mean_delta_ratio: `0.0109546231135838`
- neutral_additive_rate: `0.33624454148471616`

