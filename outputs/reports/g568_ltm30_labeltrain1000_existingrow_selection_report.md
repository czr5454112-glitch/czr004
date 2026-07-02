# G5.68 LTM30 Existing-Row Selection

Diagnostic subset built from existing Gate-3B rows with LABEL_TRAIN backfill. This is training-contaminated and must not be reported as heldout validation.

- deterministic sampling seed: `56830`
- selected contexts: `1000`
- expected maximum solver rows: `3000`
- selected split counts: `{'CALIBRATION': 267, 'DEVELOPMENT': 370, 'LABEL_TRAIN': 363}`
- label-train backfill requested: `True`
- label-train backfill used: `True`
- training-contaminated diagnostic: `True`
- primary LTM-style contexts: `379`
- secondary backfill contexts: `621`
- selected stage counts: `{'primary_ltm_target_tier': 379, 'secondary_existing_target_map_backfill': 244, 'secondary_same_family_backfill': 377}`
- selected match-type counts: `{'normalized': 379, 'secondary_existing_target_map_backfill': 244, 'secondary_same_family_backfill': 377}`

## Map Binding

| LTM target | selected existing map | match type | fallback | available rows |
|---|---|---|---:|---:|
| empty-32-32 | empty_32_32 | normalized | False | 75 |
| empty-48-48 | empty_48_48 | normalized | False | 73 |
| random-32-32-20 | random_32_32_20 | normalized | False | 75 |
| maze-32-32-4 | maze_32_32_4 | normalized | False | 66 |
| random-64-64-20 | random_64_64_20 | normalized | False | 66 |
| room-64-64-8 | room_64_64_8 | normalized | False | 120 |
| warehouse-10-20-10-2-1 | warehouse_10_20_10_2_1 | normalized | False | 37 |
| warehouse-10-20-10-2-2 | warehouse_10_20_10_2_2 | normalized | False | 111 |

## Selected Contexts By Map And Tier

| target | map | tier | selected | available | dev | calibration | label_train |
|---|---|---:|---:|---:|---:|---:|---:|
| empty-32-32 | empty_32_32 | 16 | 5 | 5 | 0 | 5 | 0 |
| empty-32-32 | empty_32_32 | 64 | 10 | 10 | 0 | 10 | 0 |
| empty-32-32 | empty_32_32 | 256 | 16 | 16 | 0 | 16 | 0 |
| empty-32-32 | empty_32_32 | 384 | 8 | 8 | 0 | 8 | 0 |
| empty-32-32 | empty_32_32 | 512 | 2 | 2 | 0 | 2 | 0 |
| empty-48-48 | empty_48_48 | 16 | 4 | 4 | 4 | 0 | 0 |
| empty-48-48 | empty_48_48 | 80 | 12 | 12 | 12 | 0 | 0 |
| empty-48-48 | empty_48_48 | 256 | 8 | 8 | 8 | 0 | 0 |
| empty-48-48 | empty_48_48 | 768 | 16 | 16 | 16 | 0 | 0 |
| empty-48-48 | empty_48_48 | 1000 | 4 | 4 | 4 | 0 | 0 |
| random-32-32-20 | random_32_32_20 | 12 | 19 | 19 | 19 | 0 | 0 |
| random-32-32-20 | random_32_32_20 | 64 | 7 | 7 | 7 | 0 | 0 |
| random-32-32-20 | random_32_32_20 | 192 | 10 | 10 | 10 | 0 | 0 |
| random-32-32-20 | random_32_32_20 | 256 | 9 | 9 | 9 | 0 | 0 |
| random-32-32-20 | random_32_32_20 | 384 | 5 | 5 | 5 | 0 | 0 |
| maze-32-32-4 | maze_32_32_4 | 16 | 11 | 11 | 11 | 0 | 0 |
| maze-32-32-4 | maze_32_32_4 | 24 | 16 | 16 | 16 | 0 | 0 |
| maze-32-32-4 | maze_32_32_4 | 32 | 13 | 13 | 13 | 0 | 0 |
| maze-32-32-4 | maze_32_32_4 | 48 | 12 | 12 | 12 | 0 | 0 |
| maze-32-32-4 | maze_32_32_4 | 384 | 5 | 5 | 5 | 0 | 0 |
| random-64-64-20 | random_64_64_20 | 16 | 12 | 12 | 0 | 0 | 12 |
| random-64-64-20 | random_64_64_20 | 24 | 12 | 12 | 0 | 0 | 12 |
| random-64-64-20 | random_64_64_20 | 32 | 11 | 11 | 0 | 0 | 11 |
| random-64-64-20 | random_64_64_20 | 48 | 8 | 8 | 0 | 0 | 8 |
| random-64-64-20 | random_64_64_20 | 1500 | 6 | 6 | 0 | 0 | 6 |
| room-64-64-8 | room_64_64_8 | 12 | 8 | 8 | 0 | 0 | 8 |
| room-64-64-8 | room_64_64_8 | 64 | 12 | 12 | 0 | 0 | 12 |
| room-64-64-8 | room_64_64_8 | 256 | 6 | 6 | 0 | 0 | 6 |
| room-64-64-8 | room_64_64_8 | 1000 | 13 | 13 | 0 | 0 | 13 |
| room-64-64-8 | room_64_64_8 | 2000 | 8 | 8 | 0 | 0 | 8 |
| warehouse-10-20-10-2-1 | warehouse_10_20_10_2_1 | 48 | 11 | 11 | 0 | 0 | 11 |
| warehouse-10-20-10-2-1 | warehouse_10_20_10_2_1 | 80 | 10 | 10 | 0 | 0 | 10 |
| warehouse-10-20-10-2-1 | warehouse_10_20_10_2_1 | 384 | 16 | 16 | 0 | 0 | 16 |
| warehouse-10-20-10-2-2 | warehouse_10_20_10_2_2 | 16 | 6 | 6 | 0 | 0 | 6 |
| warehouse-10-20-10-2-2 | warehouse_10_20_10_2_2 | 64 | 17 | 17 | 0 | 0 | 17 |
| warehouse-10-20-10-2-2 | warehouse_10_20_10_2_2 | 256 | 14 | 14 | 0 | 0 | 14 |
| warehouse-10-20-10-2-2 | warehouse_10_20_10_2_2 | 384 | 11 | 11 | 0 | 0 | 11 |
| warehouse-10-20-10-2-2 | warehouse_10_20_10_2_2 | 512 | 6 | 6 | 0 | 0 | 6 |

## Limitations

- `LABEL_TRAIN` rows are included only as an explicit backfill request; this run is a training-contaminated diagnostic/capacity check.
- `CALIBRATION` rows are used only when DEVELOPMENT/VALIDATION rows alone are insufficient for the target subset size.
- Secondary backfill rows are from the same broad LTM target families and are not the primary 5-tier LTM-style subset.
- 3000-agent rows are excluded because this is the LTM-paper-style up-to-2000-agent subset.
- Missing LTM target maps are not generated; same-family fallback maps are explicitly marked.
