# G5.65 Static-Flow Supplement

- decision: `g565_static_flow_supplement_completed`
- supplemental_not_original_gate: `True`
- static baseline: `repair5g59_static_flow_shield` / `repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75`
- scope: same-context replay against the historical hand static-flow shield; the original G5.65 gate against `g556_c063174` is unchanged.

| panel | contexts | rich pairs | success gains/regressions | better/worse/tie | median delta | median relative improvement | actor/static success rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fresh | 751 | 10514 | 881 / 0 | 4343 / 976 / 29 | -0.055100767960000074 | 0.04680455614652907 | 0.5924481643522922 / 0.5086551264980027 |
| expanded | 1000 | 3000 | 398 / 6 | 1231 / 213 / 2 | -0.05774426712500014 | 0.04778592393138669 | 0.6146666666666667 / 0.484 |

Interpretation: G5.65 rich actors clearly beat the old static-flow shield on this supplemental same-instance replay. This supports the weaker/static-flow comparison, while the stricter G5.65 conclusion versus `g556_c063174` remains not supported because of tail risk and success regressions against that stronger baseline.
