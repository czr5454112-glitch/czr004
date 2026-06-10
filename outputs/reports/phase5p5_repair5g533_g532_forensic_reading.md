# G5.33 G5.32 Forensic Reading

## Strong Evidence

- G5.32 used the project-owned real solver checkpoint exporter.
- Artifact-backed replay count is zero.
- Real trace events, exact failure audits, solver outcomes, and C/F traffic hashes are present.
- Slice conversion materialized context, edge, event, failure, and update tables.

## Pipeline-Only Evidence

- Residual labels predict observed traffic deltas, not utility-selected update rules.
- Risk labels are small context-level proxies and include direct target/proxy feature risk.
- Micro-counterfactual replay reuses selected existing slices rather than rerunning new checkpoint counterfactuals.

## Leakage Concerns

- G5.32 risk features include failure density while the target derives from failure density.
- G5.32 risk features include `target_candidate_induced_failure_proxy` directly.
- Random row splits can leak context/seed/config identity.
- Residual config one-hot can learn static rule identity rather than context-conditioned updates.

## Reusable Code Paths

- cpp/ltm/ltm.hpp UpdateParams dual channel fields
- cpp/ltm/ltm.cpp DirectedTrafficMap::update_from_trace and FlowShield traversal cost
- cpp/tools/phase1a_batch.cpp repair5g59 bounded UpdateParams aliases
- scripts/repair5g532_common.py checkpoint export and slice conversion helpers

Decision: `g532_forensic_reading_completed`
