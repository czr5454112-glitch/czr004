# Gate-3B Candidate Acquisition Diagnosis

Family summary: `outputs/tables/g567_gate3b_candidate_acquisition_family_summary.csv`

Oracle table: `outputs/tables/g567_gate3b_top_candidate_oracle_by_context.csv`

This is computed on Label-v5.4 LABEL_TRAIN candidate rows. Gate-3B did not materialize a full development candidate-pool replay; development contains the two trained A5 actor seeds plus baselines.

Safe oracle median relative improvement vs additive/LTM on label candidate pool: `None`

Safe oracle median relative improvement vs static-flow on label candidate pool: `None`

If the oracle-safe label pool has strong improvement but the trained actor does not, the failure is more likely in target selection/training/transfer. If the oracle-safe label pool itself is weak against static-flow, the candidate acquisition/label target ceiling is likely too low.
