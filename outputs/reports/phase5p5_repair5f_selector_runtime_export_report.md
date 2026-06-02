# Phase5.5 Repair5F.3 Runtime Export

This runtime export is diagnostic-only and does not permit Phase5.5 or Phase6.

## Boundary

- runtime_export_created: `true`
- diagnostic_only: `true`
- phase5p5_allowed: `false`
- phase6_allowed: `false`
- context_adaptive_claim_allowed: `false`

## Selected Runtime Candidate

- candidate_id: `c100_b100_w075_d090`
- alpha_commit: `1.0`
- alpha_block: `1.0`
- alpha_wait_spillover: `0.75`
- rho_decay: `0.9`

## Interpretation

The F2 selector selected the same bounded candidate on every final-holdout case. The exported runtime is therefore a support-trained static bounded UpdateParams policy, not evidence for context-adaptive selection.

## Artifacts

- selector runtime: `artifacts\models\laur_ltm\repair5f_bounded_updateparam_selector`
- static ablation runtime: `artifacts\models\laur_ltm\repair5f_static_c100_b100_w075_d090`
- summary JSON: `outputs\reports\phase5p5_repair5f_selector_runtime_export_summary.json`
