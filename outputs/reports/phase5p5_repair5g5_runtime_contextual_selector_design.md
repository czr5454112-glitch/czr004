# Phase5.5 Repair5G.5 Runtime Contextual Selector Design

Diagnostic-only learned UpdateLTM runtime bridge. `phase5p5_allowed=false`, `phase6_allowed=false`, and `aaai_ready=false` remain closed.

## Selector

- selector_name: `decision_stump_selector`
- selector_type: `decision_stump`
- feature_extraction_time: `pre_update_before_UpdateLTM`
- runtime_hook: `cpp/tools/phase1a_batch.cpp LtmOptions.update_policy`
- fallback_policy: unsupported/missing candidates defer to exact additive LTM and log the reason

## Rule

`ltm_iterations <= 2.5` selects `repair5g_dual_c_equiv_c100_b100_w100_d090`, otherwise `repair5g2_best_frozen_static_candidate`.

## Boundaries

- allowed output: finite bounded UpdateParams candidate ID
- forbidden output: actions, restart nodes, priorities, h_i(v), candidate deletion, conflict decisions
