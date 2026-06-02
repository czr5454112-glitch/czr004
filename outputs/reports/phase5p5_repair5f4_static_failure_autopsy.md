# Phase5.5 Repair5F.4 Static Failure Autopsy

Diagnostic-only autopsy of the fresh-ID F4-A static UpdateParams failure.

## Boundary

- diagnostic_only: `true`
- phase5p5_allowed: `false`
- phase6_allowed: `false`
- f4_outcomes_used_for_retuning: `false`

## Locked Rule

- method: `repair5f_static_c100_b100_w075_d090`
- rows: `120`
- better / equal / worse: `25 / 68 / 27`
- mean_delta_ratio_vs_ltm: `4.51908770666587e-05`
- bootstrap_95ci_mean_delta_ratio_vs_ltm: `[-0.0025520060482666805, 0.0027488667566999887]`
- ratio_worse_than_ltm_groups: `2`
- success_worse_than_ltm_groups: `0`

## Freshness And Parity

- force_additive_parity_exact: `True`
- exact_additive_candidate_parity_exact: `True`
- laur_disable_parity_exact: `True`
- laur_force_additive_direct_parity_exact: `True`
- support_validation_overlap_count: `0`
- f2f3_holdout_validation_overlap_count: `0`

## Worst Groups

| map | agents | rows | better | equal | worse | mean delta | success regressions |
|---|---:|---:|---:|---:|---:|---:|---:|
| maze-32-32-4 | 100 | 20 | 10 | 0 | 10 | 0.0013037860594999674 | 0 |
| random-32-32-20 | 50 | 20 | 0 | 18 | 2 | 0.0009064062550000029 | 0 |
| warehouse-10-20-10-2-1 | 50 | 20 | 0 | 20 | 0 | 0.0 | 0 |
| warehouse-10-20-10-2-1 | 100 | 20 | 0 | 20 | 0 | 0.0 | 0 |
| maze-32-32-4 | 50 | 20 | 8 | 6 | 6 | -0.0008071347669000139 | 0 |
| random-32-32-20 | 100 | 20 | 7 | 4 | 9 | -0.0011319122852000041 | 0 |

## Best Groups

| map | agents | rows | better | equal | worse | mean delta |
|---|---:|---:|---:|---:|---:|---:|
| random-32-32-20 | 100 | 20 | 7 | 4 | 9 | -0.0011319122852000041 |
| maze-32-32-4 | 50 | 20 | 8 | 6 | 6 | -0.0008071347669000139 |
| warehouse-10-20-10-2-1 | 50 | 20 | 0 | 20 | 0 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | 20 | 0 | 20 | 0 | 0.0 |
| random-32-32-20 | 50 | 20 | 0 | 18 | 2 | 0.0009064062550000029 |
| maze-32-32-4 | 100 | 20 | 10 | 0 | 10 | 0.0013037860594999674 |

## Component Dominance

| candidate | rows | better | equal | worse | mean delta | p(mean < 0) | pairwise W-L |
|---|---:|---:|---:|---:|---:|---:|---:|
| `c100_b100_w075_d100` | 120 | 25 | 72 | 23 | -0.0008398811590833434 | 0.727 | 8 |
| `c100_b100_w075_d095` | 120 | 22 | 76 | 22 | -0.0008186365335416705 | 0.7504 | -8 |
| `c100_b100_w100_d090` | 120 | 23 | 74 | 23 | -0.0003064312557916717 | 0.6148 | -3 |
| `c100_b100_w075_d090` | 120 | 25 | 68 | 27 | 4.51908770666587e-05 | 0.5014 | 17 |
| `c100_b100_w100_d095` | 120 | 25 | 74 | 21 | 0.00012301019519166494 | 0.4514 | -14 |

## Diagnostic Comparisons

- `repair5f_f4_deterministic_random_candidate_diagnostic`: 22 / 71 / 27, mean `-0.0007488671398916735`, locked_beats_on_mean=`False`
- `repair5e5_crossfold_utility_reranker`: 13 / 92 / 15, mean `0.0004546577450916643`, locked_beats_on_mean=`True`
- `repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic`: 15 / 92 / 13, mean `-0.00044926312444166876`, locked_beats_on_mean=`False`

## Interpretation

F4-A was a clean diagnostic failure, not an engineering failure. Coverage, freshness, and parity controls passed, but the locked c100_b100_w075_d090 rule did not generalize and did not beat the deterministic random candidate diagnostic on mean delta. Component evidence points to decay 0.90 and global static selection as plausible causes, but those observations are diagnostic-only.
