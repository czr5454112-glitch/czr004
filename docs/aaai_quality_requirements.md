# Repair5G AAAI Quality Requirements

AAAI-ready learning claims require a learned runtime UpdateLTM selector, clean heldout validation, negative controls, ablations, stress, reproducibility manifests, and a claim ledger.

- runtime_selector_integration: `passed`
- runtime_selector_smoke: `failed`
- learned_runtime_selector_performance: `failed`
- learned_runtime_fresh_holdout: `blocked_not_run`
- static_flow_shield: `strong_baseline_not_learned_claim`
- advanced_neural_network_stage: `blocked_until_safe_runtime_selector_or_counterfactual_labels`
- aaai_ready: `false`
- Phase5.5 and Phase6 remain closed until paper-grade gates pass.
