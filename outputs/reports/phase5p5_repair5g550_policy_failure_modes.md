# G5.50 Policy Failure Modes

- decision: `g550_generator_offline_passed_continue_targeted_replay`
- best family: `safe_expert_mixture_with_abstention`
- feature insufficient: `False`
- label insufficient: `True`
- signal too concentrated: `True`
- needs iteration-level counterfactual labels: `True`

The offline suite promotes a safe expert-mixture candidate family for fresh targeted replay. Targeted and blind replay remain separate gates; offline success alone is not a runtime claim.
