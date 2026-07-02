# G5.67 Gate-3B Split Feasibility

- decision: `gate3b_joint_split_allocation_feasible`
- allocator: `scipy_milp_parent_tier_official_bucket_v1`
- MILP status/message/gap/runtime: `0` / `Optimization terminated successfully. (HiGHS Status 7: Optimal)` / `0.0` / `10.650275859981775`
- candidate pool reused: `True`
- candidate pool source commit: `2d334c79a5e6e2585a04128cc06a6e6d2a8c3b90`
- selection allocator commit: `533ad963f4621b5a2e4c219f3bdf19fe57b3ef36`
- candidate pool manifest SHA256: `57081c40646f8d8949c1c59688e2002a770f8e5cc6903fd071151b3554ce05b4`
- parent leakage: `0`

## LABEL_TRAIN
- rows/public/official: `2000` / `1000` / `694`
- public fraction / official fraction: `0.5` / `0.347`
- parents/families: `32` / `11`
- public parents / official parents: `13` / `10`
- max parent share / max family share: `0.15` / `0.3`
- tier counts: `{"1000": 143, "12": 108, "128": 3, "1500": 93, "16": 113, "192": 88, "2000": 112, "24": 110, "2500": 132, "256": 135, "3000": 250, "32": 114, "384": 145, "48": 127, "512": 75, "64": 113, "768": 1, "8": 42, "80": 96}`

## CALIBRATION
- rows/public/official: `500` / `350` / `213`
- public fraction / official fraction: `0.7` / `0.426`
- parents/families: `12` / `9`
- public parents / official parents: `6` / `4`
- max parent share / max family share: `0.15` / `0.3`
- tier counts: `{"1000": 9, "12": 28, "128": 43, "1500": 1, "16": 29, "192": 22, "2000": 11, "24": 27, "2500": 93, "256": 55, "3000": 1, "32": 47, "384": 11, "48": 20, "512": 7, "64": 35, "768": 17, "8": 1, "80": 43}`

## DEVELOPMENT
- rows/public/official: `500` / `350` / `168`
- public fraction / official fraction: `0.7` / `0.336`
- parents/families: `16` / `9`
- public parents / official parents: `6` / `5`
- max parent share / max family share: `0.15` / `0.298`
- tier counts: `{"1000": 21, "12": 38, "128": 1, "1500": 28, "16": 34, "192": 24, "2000": 8, "24": 42, "2500": 17, "256": 17, "3000": 9, "32": 49, "384": 20, "48": 58, "512": 19, "64": 28, "768": 36, "8": 18, "80": 33}`

