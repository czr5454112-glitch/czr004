# Phase5.5 Repair5G.0 C-Channel Semantic Gap

This report audits why G0 C-only dual-channel candidates were not scalar-equivalent to Repair5F bounded UpdateParams.

## Answers

- do_committed_progress_events_update_only_f_in_g0: `True`
- do_dual_c_only_alpha_flow_zero_candidates_ignore_committed_progress: `True`
- does_this_explain_scalar_vs_dual_c_only_mismatch: `True`
- is_g0_reduced_c_semantics_not_scalar_f4_c_channel: `True`

## Evidence

- G0 was analyzed at commit `85636b4` where possible via `git show`.
- G0 committed-progress updates only F: `True`
- Current code has `alpha_cong_commit_progress`: `True`
- scalar best F4 mean delta: `-0.0016039228914083343`
- dual C-only best-F4-observed mean delta: `0.007440336798399994`
- scalar-vs-dual best gap: `0.00904425968980833`
- locked scalar-vs-dual gap: `0.007132177553449994`

## Interpretation

G0 tested a reduced C-channel semantics for committed progress edges. When `alpha_flow_commit_progress=0`, a committed progress edge did not contribute to either channel, so the dual C-only controls could not reproduce scalar Repair5F C-only behavior. This makes G0 a valid negative result for its global-F candidate family, but not a rejection of scalar-equivalent or agent-aware dual-channel LTM.

`phase5p5_allowed=false` and `phase6_allowed=false` remain mandatory.
