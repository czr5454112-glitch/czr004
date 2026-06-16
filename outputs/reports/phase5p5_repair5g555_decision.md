# G5.55 Decision

- decision: `g555_fixed_global_staticflow_candidate_blind_passed_keep_claims_closed`
- G5.54 analysis/gate bug confirmed: `True`
- corrected Stage2 shortlist count: `82`
- best corrected candidate: `g554_c00894`
- validation rows: `120010`
- validation passed: `True`
- blind run: `True`
- blind passed: `True`
- optimized fixed candidate promoted: `True`
- promoted fixed candidate: `g554_c00051`
- primary baseline: `promoted fixed global staticflow candidate g554_c00051`
- hand static_flow remains primary: `False`

G5.55 keeps dynamic learned UpdateParams policy paused and audits G5.54 fixed-global staticflow results. Because G5.54 Stage2 contains candidate rows with zero regressions and strong quality gains but inconsistent readiness labels, G5.55 treats the G5.54 no-promotion decision as analysis-confounded until pair-schema and shortlist gates are repaired. Corrected validation and blind replay promoted `g554_c00051` as the stronger fixed staticflow baseline candidate; the hand static_flow_shield is no longer primary for this fixed-global route.
