# Phase5.5 Repair5G.1 Final Interpretation

Repair5G.0 was a clean negative for a global edge-level flow bonus. Its dual-channel design made flow evidence globally cheap, and the oracle did not show useful headroom.

Repair5G.1 changed the interpretation. The useful signal was not a global attraction to high-flow edges; it was a flow shield that lets current-agent progress evidence reduce over-penalization from the congestion channel. The G1 smoke parity gates passed exactly, and the G1 development oracle over IDs 26..45 found strong diagnostic headroom:

```text
oracle better / equal / worse = 82 / 38 / 0
oracle mean_delta_ratio_vs_ltm = -0.033505006472296615
top flow-shield static candidate = repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75
top static better / equal / worse = 67 / 37 / 16
top static mean_delta_ratio_vs_ltm = -0.014306860332393171
```

The top G1 candidates remained diagnostic-only because IDs 26..45 were already observed during candidate design and oracle analysis. G2 therefore had to use a frozen, non-leaky selector/static protocol and untouched final IDs before any stronger claim.

The Repair5G boundary remains unchanged:

```text
phase5p5_allowed=false
phase6_allowed=false
no learned actions
no learned restart
no LaCAM*/PIBT semantic change
```
