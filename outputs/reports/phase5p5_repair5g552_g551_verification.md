# G5.52 G5.51 Artifact Verification

- decision: `g552_g551_artifacts_verified_autopsy_field_ignored`
- required artifacts present: `True`
- raw static_flow regression rows: `352`
- raw additive regression rows: `300`
- autopsy summary field inconsistent: `True`
- all claim flags closed: `True`

Authoritative fields are the final decision, targeted replay, checkpoint policy, and iteration summaries. The G5.51 autopsy field `targeted_success_regression_count_vs_static_flow` is marked non-authoritative when it disagrees with the targeted summary.
