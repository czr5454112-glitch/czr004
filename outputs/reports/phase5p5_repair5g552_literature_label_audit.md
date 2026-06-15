# G5.52 Literature Label Audit

Label-v1 is insufficient for continuous/bounded UpdateParams because it treats theta candidates like selector actions. Label-v2 must separate safety, abstention, support, and utility; utility labels are only valid after safety labels pass.

| Source family | Lesson | G5.52 design change |
|---|---|---|
| Guidance Graph Optimization | guidance parameters should be optimized/evaluated through solver outcomes | use same-checkpoint counterfactual labels, not selector labels |
| Online GGO | guidance can depend on traffic patterns | include traffic_before, trace_window, and checkpoint features |
| CS-PIBT-style learning MAPF | learned outputs need shields and strong baselines | UpdateParams shield, forbidden theta, ABSTAIN_TO_STATIC_FLOW |
| MAPF-LNS benchmark | fair baselines and executable learned policies matter | policy-as-executed replay, static_flow vs additive margin |
| LaCAM2/LaCAM* | preserve search/PIBT semantics | only UpdateLTM guidance layer is learnable |
| MAPF survey | learning-based MAPF evaluation needs standardized baselines and scale awareness | keep claim ledger closed until executable policy evidence exists |
