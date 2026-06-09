# G5.31 Decision

- decision: `g531_slice_dataset_pilot_promising_continue_scaleup`
- best residual model: `mlp_edge_residual_model_if_available`
- best risk model: `context_risk_logistic`
- context slices: `1200`
- edge slices: `72000`
- event slices: `9600`
- gold context-budget rows: `120`
- next scale: `continue_slice_dataset_route_scale_to_500_1000_contexts`
- claims remain closed: `true`

G5.31 created a neural-ready solver trace slice pilot and validated it against the existing counterfactual gold anchors. This is an offline diagnostic dataset route only; it does not authorize runtime learned policy, Phase5.5, Phase6, or AAAI claims.
