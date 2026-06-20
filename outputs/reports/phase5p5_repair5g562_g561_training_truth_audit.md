# Repair5G.5.62 G5.61 Training Truth Audit

- decision: `g562_g561_synthetic_target_training_confirmed`
- G5.61 final decision: `g561_goal_aware_actor_dev_replay_failed_continue_hard_negative_acquisition`
- analytic target smoke confirmed: `True`
- valid scenario bank as main actor dataset: `False`
- real calibrated graph-conditioned critic present: `False`

G5.61 repaired materialization and representation plumbing, but its first graph actors were trained on analytic targets and later safety shrinkage. G5.62 must train from real Label-v5.1 safe/improving, harmful, and censored solver rows.

Claims remain closed.
