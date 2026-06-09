# Repair5G.5.24 Trace-Enriched Learning Plan

Date: 2026-06-09

G5.24 continues from the G5.23 result:

```text
candidate space positive
learning still blocked
best runtime-safe surrogate = region_prior_baseline
top3_safe_oracle_capture_rate = 0.13333333333333333
```

This round does not create a new response-surface candidate wave. It treats the
G5.22/G5.23 response-surface tables as an offline teacher and asks whether
budget-pair labels, richer pre-choice trace features, and a two-stage
region-to-parameter formulation make the useful G5.22 candidates more
learnable without introducing candidate-induced failure.

Execution stages:

1. Verify the G5.23 starting state, raw-log manifest, closed claims, observed-ID
   guard, and untouched `external/lacam2/lacam2/**` status.
2. Autopsy the G5.23 learning blocker by comparing oracle winners and learned
   top-k misses by map family, map-agent group, budget, region, and candidate.
3. Inventory raw checkpoint JSONL fields by streaming samples from the local
   manifest and classify each field as runtime pre-choice safe, audit-only
   post-update, target outcome, or ambiguous.
4. Build budget-pair teacher tables for context-budget, candidate-budget, and
   pairwise budget preferences.
5. Build trace-enriched runtime-safe feature matrices with budget, rich trace,
   pre-update channel, candidate-parameter, geometry, centered, and
   trace-parameter interaction features.
6. Run the trace-enrichment probe entrypoint only as a deterministic skip unless
   the inventory proves critical pre-choice fields are unavailable for this
   offline round.
7. Create region-to-parameter teacher tables and train/evaluate offline
   region-to-parameter, risk, specialist, ablation, shuffled, random, and oracle
   diagnostic models.
8. Train offline edge/update residual surrogates for neural-readiness only.
9. Write failure and next-trace-field autopsies.
10. Write the final G5.24 decision with all runtime, Phase5.5, Phase6,
    learned-runtime, and AAAI claims closed.

Closed claims remain:

```text
phase5p5_allowed=false
phase6_allowed=false
runtime_claim_allowed=false
learned_runtime_policy_validated=false
aaai_ready=false
```
