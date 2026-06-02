# Phase5.5 Repair5F to Repair5G Transition Interpretation

Repair5F.4-A was a clean static-rule failure: parity and freshness controls
passed, but the locked support-trained static rule `c100_b100_w075_d090` did
not generalize on fresh diagnostic IDs 26..45.

Repair5F.4.1 then showed that bounded `UpdateParams` still have strong oracle
headroom on the F4 diagnostic split:

```text
better / equal / worse = 67 / 53 / 0
mean_delta_ratio_vs_ltm = -0.017388555948699997
ratio_worse_than_ltm_groups = 0
success_worse_than_ltm_groups = 0
```

The best observed F4 static candidate was `c125_b125_w075_d095`:

```text
better / equal / worse = 35 / 64 / 21
mean_delta_ratio_vs_ltm = -0.0028050352278249997
ratio_worse_than_ltm_groups = 0
```

That candidate is diagnostic-only because F4 outcomes observed it. It cannot be
promoted or retuned into a final method.

Support-to-F4 rank transfer was poor:

```text
Spearman = 0.18987049028677153
locked support rank = 1
locked F4 rank = 27
```

Interpretation:

- F4.1 showed strong bounded `UpdateParams` oracle headroom.
- F4.1 also showed support-to-F4 transfer was poor.
- The locked static rule failed fresh validation.
- F4 observed best static candidates are diagnostic-only.
- Repair5G is a new representation diagnostic, not a promotion.
- `phase5p5_allowed=false` and `phase6_allowed=false` remain mandatory.

Repair5G therefore tests whether LTM should represent successful goal-progress
flow separately from congestion, while preserving the project story as
learning-enhanced `UpdateLTM` rather than a learned MAPF action policy.
