# Phase5.5 Repair5G.2 Candidate Subset

Diagnostic-only candidate subset for a non-leaky flow-shield selector protocol.

## Boundary

- phase5p5_allowed: `false`
- phase6_allowed: `false`
- final_ids_used: `false`
- solver_semantic_changes: `false`

## Summary

- rows: `60`
- solver_methods: `57`
- synthetic_diagnostics: `3`
- component_counts: `{'agent_progress_f': 6, 'c_equiv_baseline': 5, 'control': 9, 'diagnostic': 1, 'flow_shield': 36, 'synthetic': 3}`

## Top Flow-Shield Carry-Forward

| method | beta | max_shield | G1 better/equal/worse | G1 mean delta |
|---|---:|---:|---:|---:|
| `repair5g1_shield_c125_b125_w075_d095_beta0p05_max0p25` | 0.05 | 0.25 | 33/54/33 | -0.0002251170495555612 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p05_max0p5` | 0.05 | 0.5 | 40/55/25 | -0.0023666628169059884 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p05_max0p75` | 0.05 | 0.75 | 40/54/26 | -0.0023870650825689715 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p1_max0p25` | 0.1 | 0.25 | 36/56/28 | -0.001593697708551729 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p1_max0p5` | 0.1 | 0.5 | 43/53/24 | -0.007072366789991304 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p1_max0p75` | 0.1 | 0.75 | 48/46/26 | -0.0026863721548017307 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p25` | 0.2 | 0.25 | 34/57/29 | -0.0021444721513304435 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p5` | 0.2 | 0.5 | 52/46/22 | -0.004920278463801723 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p75` | 0.2 | 0.75 | 61/40/19 | -0.012989982687452996 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p25` | 0.35 | 0.25 | 37/54/29 | -0.0005991043379035194 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p5` | 0.35 | 0.5 | 49/51/20 | -0.005907960302170944 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75` | 0.35 | 0.75 | 67/37/16 | -0.014306860332393171 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p05_max0p25` | 0.05 | 0.25 | 35/58/27 | 0.00027866310941379114 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p05_max0p5` | 0.05 | 0.5 | 32/56/32 | 0.0009561530283846038 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p05_max0p75` | 0.05 | 0.75 | 32/55/33 | 0.00039484131190515995 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p1_max0p25` | 0.1 | 0.25 | 36/58/26 | -0.0017390998173675203 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p1_max0p5` | 0.1 | 0.5 | 45/51/24 | -0.0045738271352069 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p1_max0p75` | 0.1 | 0.75 | 43/45/32 | -0.0051169978255263295 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p2_max0p25` | 0.2 | 0.25 | 35/56/29 | -0.0009222363696239405 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p2_max0p5` | 0.2 | 0.5 | 52/46/22 | -0.008704894452051727 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p2_max0p75` | 0.2 | 0.75 | 57/42/21 | -0.010387837632398303 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p25` | 0.35 | 0.25 | 39/51/30 | -0.0004800171596724249 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p5` | 0.35 | 0.5 | 49/46/25 | -0.007922400645637168 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75` | 0.35 | 0.75 | 64/35/21 | -0.013736227771605257 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p05_max0p25` | 0.05 | 0.25 | 27/54/39 | 0.0028609675180603367 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p05_max0p5` | 0.05 | 0.5 | 37/55/28 | 0.0009032956611965781 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p05_max0p75` | 0.05 | 0.75 | 37/54/29 | 0.0009110826927586175 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p1_max0p25` | 0.1 | 0.25 | 38/58/24 | -0.0011234881815344868 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p1_max0p5` | 0.1 | 0.5 | 41/49/30 | -0.0026021448838879422 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p1_max0p75` | 0.1 | 0.75 | 43/49/28 | -0.004360946869547013 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p2_max0p25` | 0.2 | 0.25 | 29/57/34 | 0.0007870065483589693 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p2_max0p5` | 0.2 | 0.5 | 52/53/15 | -0.0077079518753898416 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p2_max0p75` | 0.2 | 0.75 | 50/44/26 | -0.007929312204278265 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p35_max0p25` | 0.35 | 0.25 | 37/56/27 | -0.0009268661120431137 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p35_max0p5` | 0.35 | 0.5 | 48/48/24 | -0.00613575942311966 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p35_max0p75` | 0.35 | 0.75 | 63/40/17 | -0.013149905779432201 |
