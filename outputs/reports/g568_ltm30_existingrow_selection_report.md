# G5.68 LTM30 Existing-Row Selection

Diagnostic subset built only from existing Gate-3B non-training rows. No solver replay has happened yet at this stage.

- deterministic sampling seed: `56830`
- selected contexts: `238`
- expected maximum solver rows: `714`
- selected split counts: `{'CALIBRATION': 72, 'DEVELOPMENT': 166}`

## Map Binding

| LTM target | selected existing map | match type | fallback | available rows |
|---|---|---|---:|---:|
| empty-32-32 | empty_32_32 | normalized | False | 75 |
| empty-48-48 | empty_48_48 | normalized | False | 73 |
| random-32-32-20 | random_32_32_20 | normalized | False | 75 |
| maze-32-32-4 | maze_32_32_4 | normalized | False | 66 |
| random-64-64-20 | random_64_64_10 | fallback_same_family | True | 33 |
| room-64-64-8 | MISSING | missing | False | 0 |
| warehouse-10-20-10-2-1 | g567-warehouse-64x40-b-v2 | fallback_same_family | True | 1 |
| warehouse-10-20-10-2-2 | warehouse_small | fallback_same_family | True | 50 |

## Selected Contexts By Map And Tier

| target | map | tier | selected | available | dev | calibration |
|---|---|---:|---:|---:|---:|---:|
| empty-32-32 | empty_32_32 | 16 | 5 | 5 | 0 | 5 |
| empty-32-32 | empty_32_32 | 64 | 10 | 10 | 0 | 10 |
| empty-32-32 | empty_32_32 | 256 | 16 | 16 | 0 | 16 |
| empty-32-32 | empty_32_32 | 384 | 8 | 8 | 0 | 8 |
| empty-32-32 | empty_32_32 | 512 | 2 | 2 | 0 | 2 |
| empty-48-48 | empty_48_48 | 16 | 4 | 4 | 4 | 0 |
| empty-48-48 | empty_48_48 | 80 | 12 | 12 | 12 | 0 |
| empty-48-48 | empty_48_48 | 256 | 8 | 8 | 8 | 0 |
| empty-48-48 | empty_48_48 | 768 | 16 | 16 | 16 | 0 |
| empty-48-48 | empty_48_48 | 1000 | 4 | 4 | 4 | 0 |
| random-32-32-20 | random_32_32_20 | 12 | 19 | 19 | 19 | 0 |
| random-32-32-20 | random_32_32_20 | 64 | 7 | 7 | 7 | 0 |
| random-32-32-20 | random_32_32_20 | 192 | 10 | 10 | 10 | 0 |
| random-32-32-20 | random_32_32_20 | 256 | 9 | 9 | 9 | 0 |
| random-32-32-20 | random_32_32_20 | 384 | 5 | 5 | 5 | 0 |
| maze-32-32-4 | maze_32_32_4 | 16 | 11 | 11 | 11 | 0 |
| maze-32-32-4 | maze_32_32_4 | 24 | 16 | 16 | 16 | 0 |
| maze-32-32-4 | maze_32_32_4 | 32 | 13 | 13 | 13 | 0 |
| maze-32-32-4 | maze_32_32_4 | 48 | 12 | 12 | 12 | 0 |
| maze-32-32-4 | maze_32_32_4 | 384 | 5 | 5 | 5 | 0 |
| random-64-64-20 | random_64_64_10 | 16 | 1 | 1 | 1 | 0 |
| random-64-64-20 | random_64_64_10 | 80 | 3 | 3 | 3 | 0 |
| random-64-64-20 | random_64_64_10 | 512 | 3 | 3 | 3 | 0 |
| random-64-64-20 | random_64_64_10 | 1000 | 3 | 3 | 3 | 0 |
| random-64-64-20 | random_64_64_10 | 1500 | 5 | 5 | 5 | 0 |
| warehouse-10-20-10-2-1 | g567-warehouse-64x40-b-v2 | 12 | 1 | 1 | 0 | 1 |
| warehouse-10-20-10-2-2 | warehouse_small | 16 | 8 | 8 | 0 | 8 |
| warehouse-10-20-10-2-2 | warehouse_small | 80 | 5 | 5 | 0 | 5 |
| warehouse-10-20-10-2-2 | warehouse_small | 192 | 3 | 3 | 0 | 3 |
| warehouse-10-20-10-2-2 | warehouse_small | 512 | 5 | 5 | 0 | 5 |
| warehouse-10-20-10-2-2 | warehouse_small | 768 | 9 | 9 | 0 | 9 |

## Limitations

- `LABEL_TRAIN` rows are excluded from primary evaluation.
- `CALIBRATION` rows are used only when DEVELOPMENT/VALIDATION rows alone are insufficient for the target subset size.
- 3000-agent rows are excluded because this is the LTM-paper-style up-to-2000-agent subset.
- Missing LTM target maps are not generated; same-family fallback maps are explicitly marked.
