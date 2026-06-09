# Phase4F Repair5 Selected Safety Alignment

Date: 2026-05-31 13:23:16

This diagnostic compares all-rule harmful recall/precision with selected-rule behavior. It does not lower the final safety gate.

| mode | samples | all recall | all precision | selected harmful | selected FN | selected FP |
|---|---:|---:|---:|---:|---:|---:|
| anti_decision_top3_per_rule_safety | 762 | 0.783712 | 0.289591 | 0.022310 | 17 | 1 |
| learned_decision_oracle_safety | 762 | 1.000000 | 1.000000 | 0.000000 | 0 | 0 |
| oracle_decision_learned_rerank | 762 | 0.783712 | 0.289591 | 0.006562 | 5 | 1 |
| top3_anti_margin_per_family_safety | 762 | 0.797063 | 0.289104 | 0.023622 | 18 | 1 |
| top3_per_rule_safety_utility | 762 | 0.783712 | 0.289591 | 0.007874 | 6 | 1 |

## Boundary

Phase5.5 and Phase6 remain forbidden.
