# Repair5G.5.20 Opportunity-Gated New-Candidate Policy Plan

Date: 2026-06-08

## Scope

G5.18 candidate-space positive evidence remains valid: the full-primary 22-candidate lattice created real new-candidate oracle wins. G5.19 then reconstructed that signal but failed the ranker gate because the best OOF policy was `no_new_candidate_ablation`, selected zero new candidates, and did not exploit the new lattice.

G5.20 is a local/offline diagnostic round only. It audits target semantics, separates no-solution/nonfinite risk from solution-quality harm, builds corrected v9 targets/features, evaluates opportunity-gated policies, writes an autopsy, and plans a second-wave lattice only if the policy evidence says the current candidate space cannot be used safely.

Runtime, Phase5.5, Phase6, learned runtime-policy validation, and AAAI-ready claims remain closed:

```text
phase5p5_allowed=false
phase6_allowed=false
runtime_claim_allowed=false
learned_runtime_policy_validated=false
aaai_ready=false
```

## Deliverables

- `scripts/repair5g520_common.py`
- `scripts/verify_repair5g520_g519_artifacts.py`
- `scripts/analyze_repair5g520_target_metric_semantics.py`
- `scripts/create_repair5g520_corrected_candidate_targets_v9.py`
- `scripts/create_repair5g520_opportunity_feature_matrix_v9.py`
- `scripts/train_eval_repair5g520_opportunity_gated_policies.py`
- `scripts/analyze_repair5g520_new_candidate_policy_autopsy.py`
- `scripts/plan_repair5g520_second_wave_lattice_if_needed.py`
- `scripts/write_repair5g520_decision.py`

## Validation

Run the full local script chain, compile all new scripts, parse JSON summaries, check corrected target and feature row counts, verify 60 contexts and 22 candidates per context, ensure `forbidden_feature_count=0`, confirm the reserved-ID guard rejects `166`, verify `external/lacam2/lacam2/**` is unchanged, and run `git diff --check`.

## Boundaries

No solver-control semantics are changed. No PIBT, LaCAM*, candidate generation, conflicts, pruning, OPEN/EXPLORED, rewrite, incumbent, restart, h-value, action-prediction, priority-prediction, candidate-deletion, or MAPF action-logit behavior is changed. IDs `166..205` remain untouched.
