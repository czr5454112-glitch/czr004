# Phase5.5 Repair5G.5.11 Final Interpretation

G5.11 is a strong positive candidate-space result and a target-design failure.

- Full lattice rows: `3360`
- Measured contexts: `60`
- Candidates: `14`
- Primary budgets: `1000ms`, `2000ms`
- Candidate-space oracle beats static fraction: `0.8666666666666667`
- Candidate-space oracle beats additive fraction: `1.0`
- Mean oracle gap over static: `-0.035097435576500004`
- Mean oracle gap over additive: `-0.12287598200416668`
- Best single candidate: `repair5g59_slow_decay_high_shield`
- IDs `166..205` untouched: `true`

The failed G5.11 decision, `confidence_targets_v5_failed_continue_label_design`, does not mean the bounded goal-aware dual-channel UpdateLTM lattice failed. It means the v5 context-level target compressed a 14-candidate lattice into one oracle class per context and then required static/abstention/no-solution coverage that the positive candidate-space result did not provide.

G5.12 therefore moves from context-level oracle-class labels to candidate-level regret, ranking, and harmful-risk labels. Runtime learned-policy, Phase5.5, Phase6, and AAAI-ready claims remain closed.

