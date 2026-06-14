# G5.50 Policy Failure Modes

- decision: `g550_generator_offline_failed_continue_model_design`
- best family: `none_offline_gate_failed`
- feature insufficient: `True`
- label insufficient: `True`
- signal too concentrated: `True`
- needs iteration-level counterfactual labels: `True`

The offline suite does not promote replay-region hindsight into a runtime learned policy. Targeted and blind replay remain gated unless a later policy family passes.
