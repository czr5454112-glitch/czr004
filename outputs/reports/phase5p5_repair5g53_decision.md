# Phase5.5 Repair5G.5.3 Decision

Decision: `minimal_hook_semantic_bug`

Refined failure class: `minimal_hook_time_budget_sensitivity`

G5.3 passed the UpdateLTM transform-equivalence audit but did not pass the primary 3s overhead-neutral minimal-hook equivalence gate.

## Evidence

- Transform equivalence: passed on 870 audit rows, with 0 params-hash mismatches, 0 traffic-after hash mismatches, and 0 C/F update-stat mismatches.
- Primary 3s overhead ladder: 1500 analyzed rows.
- Minimal-hook exact-match gates at 3s:
  - static minimal hook vs fixed static: false
  - map-agent minimal hook vs map-agent selector: false
  - shadow noop minimal vs fixed static: false
- Minimal-hook mismatch rows: 10.
- Mismatch classification: all 10 were `time_budget_sensitivity`; true semantic mismatch count was 0.
- Narrow failure set: warehouse map, 100 agents, IDs 146..155.
- Targeted warehouse/100 sensitivity:
  - 5s passed with 0 minimal-hook mismatches.
  - 10s passed with 0 minimal-hook mismatches.
- Dominant overhead component: `repair5g53_cost_audit_ms`.

## Consequence

Checkpoint export is still blocked at the primary gate, so checkpoint replayability and true counterfactual UpdateLTM labels remain unavailable. G6 learned selector/mixture/residual training is not allowed.

## Final Status

- `phase5p5_allowed=false`
- `phase6_allowed=false`
- `aaai_ready=false`
- `ids_166_205_untouched=true`
- `goal_aware_dual_channel_ltm_corrupted=false`
- `g6_training_allowed=false`

G5.3 does not close the runtime hook problem. It narrows it: the traffic-map transform is equivalent, but even a minimal UpdatePolicy hook can flip borderline warehouse/100 outcomes at the strict 3s deadline.
