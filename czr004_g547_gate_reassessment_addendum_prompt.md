# G5.47 Addendum: Safety Gate Reassessment for Neural Continuous UpdateParams

Project: `czr004`
Branch: `codex/g531-slice-pilot`
Attach and execute together with: `czr004_g547_fulltheta_budget_calibrated_neural_updateparams_plan.md`
Starting point: G5.46 commit `c9ab4bb`
Round name: `Repair5G.5.47 gate reassessment addendum for neural continuous UpdateParams`

## 0. Why this addendum exists

G5.39-G5.43 used safety gates originally designed for selector-like policies and hand-designed static/update-rule aliases. G5.45-G5.46 changed the research target to a neural bounded continuous `UpdateParams` generator. The old gates may be too strict for *exploration* and too broad for *final claims*, especially if they require zero regression against every hand-written static variant before the generator has a valid full-theta materialization and evaluable solver horizon.

This addendum does **not** relax runtime, Phase5.5, Phase6, or AAAI claims. It asks Codex to audit whether the gate hierarchy should be revised for neural parameter optimization while keeping all claims closed.

Core question:

```text
Should czr004 keep the selector-era zero-regression gates unchanged,
or replace them with a layered gate hierarchy for neural continuous UpdateParams:
  invariant safety gates
  evaluability gates
  exploration gates
  refinement/promotion gates
  blind/runtime gates
?
```

## 1. Non-negotiable guardrails

Keep closed in every summary:

```json
{
  "phase5p5_allowed": false,
  "phase6_allowed": false,
  "runtime_claim_allowed": false,
  "learned_runtime_policy_validated": false,
  "aaai_ready": false
}
```

Do not modify:

```text
external/lacam2/lacam2/**
PIBT conflict semantics
candidate domain
agent actions
priority inheritance / backtracking
LaCAM* OPEN / EXPLORED / rewrite / pruning / restart semantics
```

Do not use reserved IDs `166..205`.

Do not train or present a static baseline selector as the method. The learned component must output bounded continuous `UpdateParams` theta or an `ALLOW_THETA / ABSTAIN` decision. Static baselines are diagnostics and fallback only.

## 2. Literature-inspired gate principles to encode

Use recent learning-augmented MAPF / neural solver-optimization practice as design inspiration:

1. Guidance / parameter learning should be judged by evaluator-in-loop solver outcomes, not offline fit alone.
2. Exploration should allow unsafe candidates because unsafe candidates train the risk model.
3. Positive runtime claims require much stricter safety than exploration.
4. Average quality gains are not enough if the learned component causes avoidable no-solution failures.
5. Do not require dominance over every hand-written static variant at every stage; distinguish:
   - primary paper/fallback baseline
   - diagnostic stronger baseline
   - oracle or posthoc baseline
6. Do not call a negative result if the replay is non-evaluable, e.g. finite quality pairs are absent.

## 3. Required worklog entry before code

Append to `docs/codex-worklog.md`:

```markdown
## 2026-06-14 - Repair5G.5.47 safety gate reassessment addendum

- Request:
  Audit whether selector-era safety gates remain appropriate after shifting to neural bounded continuous UpdateParams generation. G5.46 ran real continuous-theta replay but was confounded by full-theta materialization and evaluability. Before drawing stronger conclusions or relaxing/keeping gates, G5.47 must define a layered gate hierarchy: invariant safety, evaluability, exploration, refinement/promotion, and blind/runtime gates.
- Planned outputs:
  - outputs/reports/phase5p5_repair5g547_gate_reassessment.md
  - outputs/reports/phase5p5_repair5g547_gate_reassessment_summary.json
  - outputs/tables/phase5p5_repair5g547_selector_vs_generator_gate_diff.csv
  - outputs/tables/phase5p5_repair5g547_gate_matrix_v2.csv
  - outputs/tables/phase5p5_repair5g547_baseline_role_policy.csv
  - outputs/tables/phase5p5_repair5g547_evaluability_requirements.csv
  - outputs/tables/phase5p5_repair5g547_gate_backtest_on_g539_g546.csv
- Constraints:
  No solver semantic changes, no external/lacam2/lacam2 edits, no static selector method, no Phase5.5/Phase6/runtime/AAAI claims.
```

## 4. Stage A — Verify current G5.46 evidence and old gate provenance

Create a gate provenance audit over G5.39-G5.46.

Inputs:

```text
outputs/reports/phase5p5_repair5g546_decision_summary.json
outputs/reports/phase5p5_repair5g546_real_continuous_theta_evidence_summary.json
outputs/reports/phase5p5_repair5g546_theta_materialization_smoke_summary.json
outputs/reports/phase5p5_repair5g546_risk_utility_surrogates_summary.json
outputs/tables/phase5p5_repair5g546_feature_validity_audit.csv
outputs/tables/phase5p5_repair5g546_theta_region_leaderboard.csv
G5.39-G5.45 decision/evidence summaries where available
```

Answer explicitly:

```text
Which gates were selector-era gates?
Which gates are invariant solver-safety gates?
Which gates are evaluability gates?
Which gates are claim/promotion gates?
Which gates incorrectly block exploration data collection?
Which gates should be primary-baseline hard gates?
Which gates should be diagnostic-only against stronger static baselines?
```

Output:

```text
outputs/tables/phase5p5_repair5g547_selector_vs_generator_gate_diff.csv
```

Required columns:

```text
gate_name
first_seen_round
old_gate_definition
old_gate_role
appropriate_for_selector
appropriate_for_continuous_theta_generator
keep_modify_drop
new_gate_tier
reason
```

## 5. Stage B — Define layered gate matrix v2

Create `outputs/tables/phase5p5_repair5g547_gate_matrix_v2.csv`.

Use this tier structure.

### Tier I — Invariant safety gates, never relax

These are always hard blockers:

```text
external_lacam2_clean = true
reserved_ids_untouched = true
force_additive_parity_passed = true
candidate_recognized_all = true
bounded_updateparams_all = true
no_nan_or_inf_updateparams = true
fulltheta_fingerprint_match_rate = 1.0
cost_audit_finite = true
configured_cost_bounds_respected = true
solver_semantics_changed = false
```

If any fail, stop and do not interpret performance.

### Tier E — Evaluability gates, required before saying positive or negative

These decide whether an experiment is interpretable:

```text
finite_ratio_rate >= 0.20
finite_ratio_rows >= 3000 for large probes
both_success_quality_pairs_vs_primary >= 2000
baseline_success_rate_primary is nontrivial
paired_baselines_materialized = true
primary_baseline_rows >= required minimum
```

If these fail, decision must be:

```text
non_evaluable_replay_continue_evaluability_repair
```

not:

```text
no_signal
```

### Tier X — Exploration gates, intentionally permissive

Exploration may include unsafe theta. Unsafe theta is useful risk-model data.

Allow:

```text
nonzero_success_regression
unsafe_but_useful_regions
negative_controls
risk_boundary theta
```

Do not allow:

```text
positive claims
runtime claims
blind replay
```

Exploration output should be:

```text
risk_dataset_created
theta_space_mapped
or
no_evaluable_signal
```

### Tier R — Refinement / candidate promotion gates

A theta region or generated-theta policy can enter refinement if one of these profiles passes:

Strict profile:

```text
support_pairs >= 120
seed_block_support >= 3
success_regression_count_vs_primary = 0
quality_only_mean_delta_vs_primary < 0
better_count > worse_count
```

Literature-aligned development profile:

```text
support_pairs >= 240
seed_block_support >= 4
success_regression_rate_vs_primary <= 0.005
success_gain_count >= success_regression_count
catastrophic_regression_count = 0
quality_only_mean_delta_vs_primary < 0
bootstrap_CI_high_quality_delta < 0 or better_count >= 1.5 * worse_count
```

The strict profile is required for frozen policy by default. The literature-aligned profile is only for further refinement, not runtime claims.

### Tier P — Targeted generated-theta policy gates

A generated-theta policy may run targeted replay if:

```text
non_static_theta_usage_rate >= 0.05
risk_false_safe_count_at_tau = 0 on validation/test or Wilson upper bound acceptable
offline_expected_utility_vs_primary < 0
theta_diversity_noncollapse_passed = true
passes either strict R or literature-aligned R profile
```

Targeted replay may use relaxed exploration gate for measuring but cannot claim success unless strict profile is met.

### Tier B — Blind/runtime/paper gate

Do not change this gate in G5.47 without explicit later approval.

Default blind/runtime candidate gate remains strict:

```text
blind_rows >= required minimum
success_regression_count_vs_primary = 0
non_static_theta_usage_rate >= 0.05
quality_only_mean_delta_vs_primary < 0
better_count > worse_count
no solver semantic change
overhead acceptable
```

Also report diagnostic comparisons vs family_static/additive/best_fixed, but do not let every diagnostic static variant become a hard blocker for exploration.

## 6. Stage C — Clarify baseline roles

Create `outputs/tables/phase5p5_repair5g547_baseline_role_policy.csv`.

Required rows:

```text
baseline_name, role, hard_gate_tiers, diagnostic_tiers, reason
additive_ltm, paper/LTM parity floor, I/E/R/P/B where paired, all, must not break paper-faithful fallback
static_flow_shield, primary fixed fallback baseline for theta generator, R/P/B hard primary, all, current generator is static-flow-relative
frozen_family_static_goal_aware, strong diagnostic static baseline, B diagnostic and failure autopsy; R hard only if explicitly claiming family-static dominance, all, avoid turning method into static selector
best_fixed_static_goal_aware, diagnostic/legacy stronger static, diagnostic unless selected as primary in a declared experiment, all, static selection gains are not learned UpdateLTM
posthoc_oracle_static, diagnostic upper bound only, never hard gate, all, not deployable
```

This is important: do not require continuous theta to dominate every hand-written static variant during exploration. The core project goal is learned UpdateLTM improvement over the LTM/static-flow baseline, with stronger static variants used for stress-testing and failure analysis.

## 7. Stage D — Backtest old vs new gates on G5.39-G5.46

Create `outputs/tables/phase5p5_repair5g547_gate_backtest_on_g539_g546.csv`.

For each prior round, compute:

```text
old_decision
new_tiered_decision
would_exploration_continue
would_refinement_continue
would_targeted_replay_run
would_blind_replay_run
reason
```

Important examples to classify:

```text
G5.41:
  should be research-positive vs static_flow but blocked for runtime by family-static failure.

G5.42:
  should be residual-not-guilty; static-ladder failure not residual failure.

G5.43:
  should be hand-alias unstable; not learned UpdateLTM death.

G5.46:
  should be non-decisive for full neural generator if finite quality pairs or fulltheta materialization are missing.
```

## 8. Stage E — Write final gate reassessment report

Create:

```text
outputs/reports/phase5p5_repair5g547_gate_reassessment.md
outputs/reports/phase5p5_repair5g547_gate_reassessment_summary.json
```

The summary must include:

```json
{
  "decision": "...",
  "selector_epoch_gate_reuse_safe": false,
  "tiered_gate_matrix_created": true,
  "final_runtime_gate_relaxed": false,
  "exploration_gate_relaxed": true_or_false,
  "primary_baseline_for_theta_generator": "static_flow_shield",
  "strong_static_baselines_diagnostic_not_exploration_blockers": true,
  "phase5p5_allowed": false,
  "phase6_allowed": false,
  "runtime_claim_allowed": false,
  "learned_runtime_policy_validated": false,
  "aaai_ready": false
}
```

Allowed decisions:

```text
g547_gate_v2_created_use_for_fulltheta_exploration
g547_keep_old_gates_no_change
g547_gate_reassessment_blocked_missing_evidence
```

## 9. How this addendum interacts with the main G5.47 plan

Execute this addendum before interpreting G5.47 full-theta performance.

Main G5.47 must still:
- implement/verify full-theta materialization,
- calibrate budget/evaluability,
- run real full-theta replay only after fulltheta and evaluability smoke pass.

But the interpretation of G5.47 should use gate matrix v2:

```text
If finite_ratio_rate is too low:
  report non-evaluable, not no-signal.

If theta has regressions during exploration:
  retain as risk data, do not stop exploration.

If generated theta improves vs static_flow but loses to family_static:
  report learned UpdateLTM primary-baseline signal plus strong-static diagnostic gap,
  not automatic method success and not automatic exploration failure.

If static baseline selection alone wins:
  report static-selector diagnostic only, not LAU/NTM progress.
```

## 10. Validation

Run:

```text
python -m py_compile scripts/repair5g547*.py scripts/*g547*gate*.py
python scripts/<gate_reassessment_script>.py
python scripts/write_repair5g547_decision.py  # or integrate with main G5.47 decision writer
python - <<'PY'
import json, pathlib
for p in pathlib.Path("outputs/reports").glob("phase5p5_repair5g547_*summary.json"):
    d=json.loads(p.read_text())
    assert d.get("phase5p5_allowed") is False
    assert d.get("phase6_allowed") is False
    assert d.get("runtime_claim_allowed") is False
    assert d.get("learned_runtime_policy_validated") is False
    assert d.get("aaai_ready") is False
print("G5.47 gate summaries claim flags closed")
PY
git diff --check
git status --short -- external/lacam2/lacam2
```
