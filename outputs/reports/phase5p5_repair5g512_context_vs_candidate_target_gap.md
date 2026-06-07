# Phase5.5 Repair5G.5.12 Context-vs-Candidate Target Gap

- G5.11 context labels: `{'stable_high_confidence_parameter_candidate': 52, 'stable_static': 8}`
- G5.12 candidate labels: `{'additive_bad_baseline': 60, 'c_only_ablation_candidate': 60, 'harmful_parameter_candidate': 266, 'helpful_parameter_candidate': 193, 'neutral_parameter_candidate': 141, 'static_fallback_candidate': 120}`
- G5.12 candidate rows: `840`
- G5.12 contexts: `60`
- G5.12 candidates: `14`

G5.11 failed because context-level oracle class labels are too coarse for a parameter lattice. The full lattice mostly found stable non-static winners, so the old target had 52 parameter-candidate contexts, 8 static contexts, and no no-solution or longer-budget abstention examples. That is useful candidate-space evidence, but it is a poor training target for scoring fourteen parameter candidates.

Candidate-level regret, ranking, and harmful-risk labels are the right offline diagnostic target for learned bounded UpdateLTM parameter scoring. They expose helpful, harmful, neutral, static, additive-bad, and C-only examples within the same context. `no_solution_or_budget_abstain_count=0` must not block this offline candidate-ranking diagnostic.

Runtime, Phase5.5, Phase6, and AAAI claims remain closed because deployment still needs static, abstention, no-solution, budget-sensitive, and OOD safety coverage.
