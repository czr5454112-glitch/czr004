# Repair5G.5.60 Direct Actor Development Replay

- Planned contexts: 300
- Real solver rows: 600
- Replay pairs: 300
- Success regressions: 25
- Success gains: 1
- Mean quality delta vs g556: 0.11486412997058826

Actor-generated rows use `generated_theta_uid` as the solver materialization key; the exported actor bundle does not contain the registry.
