# Phase5.5 Repair5E.2 Runtime Feature OOD Report

- diagnostic-only: `true`
- phase5p5_allowed: `false`
- phase6_allowed: `false`

- analyzed rows: `149`
- rows with full runtime features: `149`
- missing required fields: `{}`
- top OOD trigger features: `{'committed_count': 129, 'nonzero_edges_before': 20}`
- top OOD trigger share: `0.8657718120805369`
- entropy_edge_usage OOD trigger share: `0.0`
- any one feature accounts for >50% of OOD triggers: `True`

## Top Feature Z-Scores

| feature | rows | max abs z | mean abs z | raw mean | raw std |
|---|---:|---:|---:|---:|---:|
| committed_count | 149 | 126300.0 | 8750.335570469799 | 8750.335570469799 | 15136.613347964654 |
| goal_wait_ignored_count | 149 | 117237.0 | 5950.3892617449665 | 5950.3892617449665 | 14047.779930986066 |
| nonzero_edges_before | 149 | 6162.0 | 2272.1275167785234 | 2272.1275167785234 | 1464.4777216339926 |
| blocked_count | 149 | 2509.0 | 523.4563758389262 | 523.4563758389262 | 538.7195418222991 |
| committed_per_agent | 149 | 1263.0 | 110.1006711409396 | 110.1006711409396 | 150.13017818624652 |
| wait_event_count | 149 | 1262.0 | 226.80536912751677 | 226.80536912751677 | 237.4426579410251 |
| max_raw_before | 149 | 501.0 | 50.61744966442953 | 50.61744966442953 | 69.02179378759192 |
| blocked_per_agent | 149 | 25.09 | 6.392684563758389 | 6.392684563758389 | 5.259498870005319 |
| weight_entropy | 149 | 8.48993308133 | 7.202171212261208 | 7.202171212261208 | 0.5862455405068882 |
| entropy_edge_usage | 149 | 7.84572594715 | 5.7995420884333555 | 5.7995420884333555 | 2.304469082712511 |
| obstacle_ratio | 149 | 3.0212426754946757 | 1.0204833539816913 | 0.2579098107425503 | 0.08950452458259614 |
| map_height | 149 | 1.8618986725025257 | 0.7949355715847127 | 38.033557046979865 | 12.273404491713595 |

## Rule Before/After Guard

{
  "commit_heavy->additive_ltm:ood_guard": 146,
  "wait_light->additive_ltm:ood_guard": 3
}

## OOD Trigger Rate By Map/Agents/Iteration

| map | agents | iteration | rows | trigger rate |
|---|---:|---:|---:|---:|
| maze-32-32-4 | 50 | 1 | 10 | 1.0 |
| maze-32-32-4 | 50 | 2 | 10 | 1.0 |
| maze-32-32-4 | 50 | 3 | 10 | 1.0 |
| maze-32-32-4 | 100 | 1 | 10 | 1.0 |
| maze-32-32-4 | 100 | 2 | 10 | 1.0 |
| maze-32-32-4 | 100 | 3 | 10 | 1.0 |
| random-32-32-20 | 50 | 1 | 10 | 1.0 |
| random-32-32-20 | 50 | 2 | 10 | 1.0 |
| random-32-32-20 | 50 | 3 | 10 | 1.0 |
| random-32-32-20 | 100 | 1 | 10 | 1.0 |
| random-32-32-20 | 100 | 2 | 10 | 1.0 |
| random-32-32-20 | 100 | 3 | 10 | 1.0 |
| warehouse-10-20-10-2-1 | 50 | 1 | 10 | 1.0 |
| warehouse-10-20-10-2-1 | 50 | 2 | 9 | 1.0 |
| warehouse-10-20-10-2-1 | 100 | 1 | 10 | 1.0 |
