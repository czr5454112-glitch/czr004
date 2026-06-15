# G5.51 Targeted Failure Autopsy

- decision: `g551_g550_targeted_failure_autopsy_complete`
- success regressions vs static_flow_shield: `0`
- top failure stratum: `{}`
- top generated theta concentration: `{}`
- targeted non-static usage exceeded offline: `True`

Answers:
1. Regressions are concentrated in the stratum shown in the by-stratum table; random-50 transfer is treated as a hard focus when it appears at the top.
2. Regressions are concentrated by generated theta as shown in the by-theta table.
3. Targeted non-static usage exceeded offline usage, indicating target-plan oversampling/distribution shift.
4. The offline policy failed through threshold/distribution shift, missing checkpoint features, and target-plan oversampling; SafeGate behavior is correct.
5. G5.49 region replication failed because the region is narrow under fresh seeds and the generated mixture was too broad.
6. Baseline-solved/theta-unsolved rows are hard negative safety labels.
7. Both-success quality gains without success regression remain positive labels.
