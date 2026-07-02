# G5.68 LTM30 Existing-Row Replay Summary

Diagnostic-only subset replay on existing Gate-3B contexts with LABEL_TRAIN backfill. This is training-contaminated and is not a heldout-validation claim. No training, no context/scenario generation, no full launch, no blind access.

- decision label: `actor_tied_or_negative_on_ltm30_subset`
- planned contexts: `1000`
- completed same-context triples: `1000`
- planned/executed rows: `3000` / `3000`
- partial stop: `False`
- primary actor: `/root/shared-nvme/g567_gate3b_bounded_2d334c79_tmux_r13_pool20000/models/gcst/phase5p5_repair5g567_a5_hierarchical_od_perceiver_actor_seed568.pt`
- selected splits: `{'CALIBRATION': 267, 'DEVELOPMENT': 370, 'LABEL_TRAIN': 363}`
- selected stages: `{'primary_ltm_target_tier': 379, 'secondary_existing_target_map_backfill': 244, 'secondary_same_family_backfill': 377}`
- label-train backfill used: `True`
- training-contaminated diagnostic: `True`

## Method Metrics

| method | rows | success_rate | median_ratio_successes | hard_timeouts | infra_failures | mean_actor_ms |
|---|---:|---:|---:|---:|---:|---:|
| ltm_30s | 1000 | 0.988 | 1.07899 | 0 | 0 | 0 |
| static_flow_30s | 1000 | 0.988 | 1.05946 | 0 | 0 | 0 |
| gate3b_actor_30s | 1000 | 0.969 | 1.05643 | 0 | 0 | 20.09 |

## Pairwise Same-Context Metrics

| pair | both_success | success_gain | success_regression | median_rel_quality_improvement | q95_harm | bootstrap_CI |
|---|---:|---:|---:|---:|---:|---|
| actor_vs_ltm | 969 | 0 | 19 | 0.00587199 | 0.0988678 | [0.00418911, 0.00766703] |
| actor_vs_static_flow | 969 | 0 | 19 | 0 | 0.05072 | [0, 0] |
| static_flow_vs_ltm | 988 | 0 | 0 | 0.0039708 | 0.0567871 | [0.00212129, 0.00554194] |

## Interpretation Guardrails

- This is a subset replay, not a full-campaign or paper claim.
- If exact anytime curves are absent from solver logs, this report uses final 30s metrics and available runtime fields only.
- CALIBRATION rows, if present, are reported as a limitation and are not training rows.
- LABEL_TRAIN rows, if present, are only a requested backfill diagnostic and contaminate heldout interpretation.
- 3000-agent rows are excluded from the primary LTM-style analysis.
