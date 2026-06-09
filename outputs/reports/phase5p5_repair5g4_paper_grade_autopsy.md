# Phase5.5 Repair5G.4 Paper-Grade Autopsy

Diagnostic-only consolidation. Static flow-shield is not an AAAI-ready learned runtime method.

## Answers

- Flow-shield representation validated: `True`.
- Frozen map-agent selector better than static: `True` (selector mean -0.01862021635864017, static mean -0.016410173082962193).
- Learned runtime selector necessary for AAAI story: `true`; G4 only validates static/map-agent flow-shield and an offline bridge.
- Map-agent gains are concentrated in non-warehouse random/maze groups; warehouse remains no-op or fallback-heavy.
- Stress preserves sign: `True`.
- Safe claims are representation/protocol/diagnostic claims; learned runtime and AAAI-ready claims remain forbidden.

## Safe Claims

- Flow-shielded goal-aware dual-channel UpdateLTM is protocol-clean under the accepted parity policy on G4.
- Static/map-agent flow-shield beats additive LTM and scalar/C-equiv controls on G4 diagnostics.
- Offline decision-stump selector is promising as a bridge but not yet a runtime-validated learned method.

## Forbidden Claims

- AAAI-ready learned method.
- Phase5.5 or Phase6 promotion.
- Learned selector fresh validation passed.
- Static flow-shield alone is the final learned contribution.

## Artifact Index

- `selector_vs_static_cases`: `outputs\tables\phase5p5_repair5g4_selector_vs_static_cases.csv`
- `ablation_effect_table`: `outputs\tables\phase5p5_repair5g4_ablation_effect_table.csv`
- `group_risk_table`: `outputs\tables\phase5p5_repair5g4_group_risk_table.csv`
- `stress_effect_table`: `outputs\tables\phase5p5_repair5g4_stress_effect_table.csv`
- `oracle_regret_table`: `outputs\tables\phase5p5_repair5g4_oracle_regret_table.csv`
- `contextual_selector_sweep`: `outputs\tables\phase5p5_repair5g4_contextual_selector_sweep.csv`
