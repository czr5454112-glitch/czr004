# Phase5.5 Repair5E.4 Runtime Feature Stats Audit

- feature_stats_valid: `True`
- invalid_features: `[]`
- top_ood_trigger_share: `0.0`
- learned_choices_all_blocked_by_ood: `False`

## E3 vs E4 OOD Snapshot

{
  "e3_committed_count_max_abs_z": 126300.0,
  "e3_top_trigger_concentration": 0.8657718120805369,
  "e3_top_trigger_feature": "committed_count",
  "e4_committed_count_max_abs_z": 8.191661429636884,
  "e4_top_trigger_concentration": 0.0,
  "e4_top_trigger_feature": ""
}

## Top E4 Feature Z-Scores

| feature | rows | max abs z | mean abs z |
|---|---:|---:|---:|
| max_raw_before | 2720 | 13.802611164825265 | 0.610874417769798 |
| goal_wait_ignored_count | 2720 | 8.684536267054106 | 0.389596240700035 |
| committed_count | 2720 | 8.191661429636884 | 0.4884052600611191 |
| committed_per_agent | 2720 | 7.781196266220048 | 0.5252363109431745 |
| wait_event_count | 2720 | 6.747205195055991 | 0.8382370398033782 |
| blocked_per_agent | 2720 | 5.353605447211177 | 0.8520538496456168 |
| blocked_count | 2720 | 5.270827273247983 | 0.853302176735126 |
| blocked_per_committed | 2720 | 3.4075411672522375 | 0.8197671723324648 |
| wait_per_committed | 2720 | 3.223584619121613 | 0.8115524836544109 |
| entropy_edge_usage | 2720 | 3.17458596445598 | 0.5654743262357977 |
| nonzero_edges_before | 2720 | 2.957865257407054 | 0.7085723566079006 |
| map_width | 2720 | 1.8353258709644942 | 0.8485008392418572 |

## Before/After Guard Counts

{
  "additive_ltm->additive_ltm:force_additive": 299,
  "additive_ltm->additive_ltm:pre_first_solution": 780,
  "block_heavy->block_heavy:repair5e4_closed_loop_utility_selector": 30,
  "block_heavy->block_heavy:static_rule": 150,
  "block_light->block_light:static_rule": 150,
  "commit_heavy->additive_ltm:ood_guard": 295,
  "commit_heavy->additive_ltm:repair5e4_no_supported_neighbor_defer": 87,
  "commit_heavy->commit_heavy:runtime_mlp": 145,
  "commit_heavy->commit_heavy:static_rule": 150,
  "decay_090->decay_090:repair5e4_closed_loop_utility_selector": 30,
  "decay_090->decay_090:static_rule": 150,
  "decay_095->decay_095:static_rule": 150,
  "wait_heavy->wait_heavy:static_rule": 148,
  "wait_light->additive_ltm:ood_guard": 3,
  "wait_light->additive_ltm:repair5e4_no_supported_neighbor_defer": 2,
  "wait_light->wait_light:runtime_mlp": 2,
  "wait_light->wait_light:static_rule": 149
}
