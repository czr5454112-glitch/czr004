# Phase5.5 RepairG.5.1 Policy-Control Failure Analysis

G5 strict smoke reported force-additive and disable policy controls as noncompliant. The row-level failures are short-budget strict outcome mismatches, while group-level semantic policy metrics remain within the accepted G3.1/G4 parity policy.

- g5_force_additive_policy_compliant: `False`
- g5_disable_policy_compliant: `False`
- force_additive_group_policy_ok: `True`
- disable_group_policy_ok: `True`
- strict_failure_cases: `19`
- g51_next_step: run `scripts/run_repair5g51_policy_control_reproducer.py` on observed IDs.

`phase5p5_allowed=false`, `phase6_allowed=false`, and `aaai_ready=false` remain closed.
