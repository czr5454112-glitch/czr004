# Phase5.5 Repair5G.5.16 Error Autopsy

- decision: `error_autopsy_too_conservative_continue_lattice_or_data`
- primary_policy_name: `balanced_bound`
- g514_false_positive_count: `2`
- g515_false_positive_count: `2`
- g516_false_positive_count: `0`
- contexts_fixed_by_g516: `['random-32-32-20|a50|s151|it0|14650fb0739d0383', 'warehouse-10-20-10-2-1|a100|s154|it0|14650fb0739d0383']`
- contexts_newly_harmed_by_g516: `[]`
- g516_missed_helpful_count: `52`
- falls_back_everywhere_or_hides_opportunity: `True`

G5.16 must not pass by hiding all opportunity behind static fallback. This report keeps that failure mode explicit.
