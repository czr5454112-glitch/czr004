# Phase5.5 Repair5G.5.14 Final Interpretation

- conclusion: `G5.14 recovered rich runtime-safe trace features, but failed strict promotion because harmful rate exceeded 0.05 and risk-adjusted utility did not improve over the reproduced G5.12/G5.13 ranker.`
- g514_decision: `rich_trace_features_insufficient_continue_probe_or_lattice`
- v4_mean_delta_vs_static: `-0.010721312411`
- v4_harmful_vs_static_rate: `0.06666666666666667`
- v4_risk_adjusted_utility_lambda_0p10: `-0.004054645744333333`
- reproduced_g512_mean_delta_vs_static: `-0.010423295036333333`
- reproduced_g512_harmful_vs_static_rate: `0.03333333333333333`
- reproduced_g512_risk_adjusted_utility_lambda_0p10: `-0.007089961702999999`
- interpretation: `The recovered rich features are useful evidence, but G5.14 joined them as context-only columns. They can shift gate/fallback behavior but cannot reliably reorder candidates in a linear scorer. G5.15 therefore tests rich-by-candidate interactions and pairwise ranking.`
- runtime_claim_allowed: `false`
