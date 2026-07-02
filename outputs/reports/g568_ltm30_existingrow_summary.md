# G5.68 LTM30 Existing-Row Replay Summary

Diagnostic-only subset replay on existing Gate-3B non-training contexts. No training, no context/scenario generation, no full launch, no blind access.

- decision label: `actor_tied_or_negative_on_ltm30_subset`
- planned contexts: `238`
- completed same-context triples: `238`
- planned/executed rows: `714` / `714`
- partial stop: `False`
- primary actor: `/root/shared-nvme/g567_gate3b_bounded_2d334c79_tmux_r13_pool20000/models/gcst/phase5p5_repair5g567_a5_hierarchical_od_perceiver_actor_seed568.pt`
- selected splits: `{'CALIBRATION': 72, 'DEVELOPMENT': 166}`

## Method Metrics

| method | rows | success_rate | median_ratio_successes | hard_timeouts | infra_failures | mean_actor_ms |
|---|---:|---:|---:|---:|---:|---:|
| ltm_30s | 238 | 1 | 1.12906 | 0 | 0 | 0 |
| static_flow_30s | 238 | 1 | 1.10807 | 0 | 0 | 0 |
| gate3b_actor_30s | 238 | 0.966387 | 1.11855 | 0 | 0 | 15.3257 |

## Pairwise Same-Context Metrics

| pair | both_success | success_gain | success_regression | median_rel_quality_improvement | q95_harm | bootstrap_CI |
|---|---:|---:|---:|---:|---:|---|
| actor_vs_ltm | 230 | 0 | 8 | 0.00229625 | 0.109546 | [-0.00143781, 0.00727202] |
| actor_vs_static_flow | 230 | 0 | 8 | -0.00511535 | 0.0619054 | [-0.00843526, -0.0023844] |
| static_flow_vs_ltm | 238 | 0 | 0 | 0.00496218 | 0.0580388 | [0.00324813, 0.00701754] |

## Interpretation Guardrails

- This is a subset replay, not a full-campaign or paper claim.
- If exact anytime curves are absent from solver logs, this report uses final 30s metrics and available runtime fields only.
- CALIBRATION rows, if present, are reported as a limitation and are not training rows.
- 3000-agent rows are excluded from the primary LTM-style analysis.
