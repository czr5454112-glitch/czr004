# Phase5.5 Repair5G.5.5 G6 Safe Mixture Policy Design

The first G6 method should be a safe learned mixture over validated UpdateLTM experts, with static flow-shield fallback and abstention. It should not predict actions, priorities, restart nodes, h-values, collision outcomes, or candidate deletion.

Policy shape:
- input: allowed pre-update runtime features, trace aggregates, and C/F traffic summaries only
- encoder: small calibrated linear/MLP model first
- output: mixture weights over safe experts plus abstention/confidence
- fallback: static flow-shield by default; additive or C-equiv only under explicit high-risk abstention
- residuals: bounded residuals over flow-shield parameters only after mixture gap and budget stability are validated

G5.5 decision feeding this design: `scaled_labels_passed_adaptive_gap_strong_continue_g6_design`.
G6 training allowed now: `False`.
