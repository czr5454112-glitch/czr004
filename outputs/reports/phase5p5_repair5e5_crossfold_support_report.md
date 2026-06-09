# Phase5.5 Repair5E.5 Cross-Fold Support

- diagnostic_only: `true`
- phase5p5_allowed: `false`
- phase6_allowed: `false`
- leakage_detected: `False`
- available_instance_ids: `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]`
- missing_instance_ids: `[]`
- raw_rows: `1350`
- update_rows: `4173`

## Folds

### fold_0

- eval_instance_ids: `[1, 2, 3, 4, 5]`
- train_support_instance_ids: `[6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]`
- support_eval_overlap: `[]`
- raw_rows: `1080`
- update_rows: `3344`

### fold_1

- eval_instance_ids: `[6, 7, 8, 9, 10]`
- train_support_instance_ids: `[1, 2, 3, 4, 5, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]`
- support_eval_overlap: `[]`
- raw_rows: `1080`
- update_rows: `3342`

### fold_2

- eval_instance_ids: `[11, 12, 13, 14, 15]`
- train_support_instance_ids: `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]`
- support_eval_overlap: `[]`
- raw_rows: `1080`
- update_rows: `3337`

### fold_3

- eval_instance_ids: `[16, 17, 18, 19, 20]`
- train_support_instance_ids: `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 21, 22, 23, 24, 25]`
- support_eval_overlap: `[]`
- raw_rows: `1080`
- update_rows: `3333`

### fold_4

- eval_instance_ids: `[21, 22, 23, 24, 25]`
- train_support_instance_ids: `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]`
- support_eval_overlap: `[]`
- raw_rows: `1080`
- update_rows: `3336`
