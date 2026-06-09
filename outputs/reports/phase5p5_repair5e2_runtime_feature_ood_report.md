# Phase5.5 Repair5E.2 Runtime Feature OOD Report

- diagnostic-only: `true`
- phase5p5_allowed: `false`
- phase6_allowed: `false`

- analyzed rows: `4`
- rows with full runtime features: `4`
- missing required fields: `{}`
- top OOD trigger features: `{'entropy_edge_usage': 3}`
- entropy_edge_usage OOD trigger share: `1.0`
- one feature dominates OOD: `True`

## Top Feature Z-Scores

| feature | rows | max abs z | mean abs z | raw mean | raw std |
|---|---:|---:|---:|---:|---:|
| entropy_edge_usage | 4 | 109.20479714117205 | 101.83223652546113 | 6.4069146064825 | 0.31384301809771914 |
| has_solution_before | 4 | 5.228559824448444 | 1.4505828974155657 | 0.75 | 0.4330127018922193 |
| improved_last_iteration | 4 | 5.228559824448444 | 3.9692341821041515 | 0.25 | 0.4330127018922193 |
| weight_entropy | 4 | 4.370747077534367 | 3.5047643464320903 | 5.241885094625 | 3.037618017198674 |
| best_ratio_before | 4 | 1.667459265561642 | 0.651158187816536 | 0.8506178287724999 | 0.4911044324192978 |
| iteration | 4 | 1.3609895480094698 | 0.895090193563073 | 1.5 | 1.118033988749895 |
| agents | 4 | 0.9884488631783344 | 0.9884488631783344 | 50.0 | 0.0 |
| blocked_per_committed | 4 | 0.8630345580084731 | 0.6388820922570265 | 0.041327894629500005 | 0.01877032916140352 |
| wait_per_committed | 4 | 0.7350145698165568 | 0.5806923017930757 | 0.019910773103725 | 0.007793469704266843 |
| map_height | 4 | 0.6838767217057883 | 0.6838767217057883 | 32.0 | 0.0 |
| nonzero_edges_before | 4 | 0.6215968469426707 | 0.4743867714974077 | 1051.5 | 692.806069546161 |
| map_width | 4 | 0.5422680896627002 | 0.5422680896627002 | 32.0 | 0.0 |

## Rule Before/After Guard

{
  "additive_ltm->additive_ltm:pre_first_solution": 1,
  "commit_heavy->additive_ltm:ood_guard": 3
}

## OOD Trigger Rate By Map/Agents/Iteration

| map | agents | iteration | rows | trigger rate |
|---|---:|---:|---:|---:|
| random-32-32-20 | 50 | 0 | 1 | 0.0 |
| random-32-32-20 | 50 | 1 | 1 | 1.0 |
| random-32-32-20 | 50 | 2 | 1 | 1.0 |
| random-32-32-20 | 50 | 3 | 1 | 1.0 |
