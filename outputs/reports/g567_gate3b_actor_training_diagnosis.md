# Gate-3B Actor Training Diagnosis

Training matrix: `outputs/tables/g567_gate3b_actor_training_curve.csv`

Gradient summary: `outputs/tables/g567_gate3b_actor_gradient_summary.csv`

The saved artifacts contain per-seed summary rows, final losses, best epochs, validation normalized L1, resume checkpoints, and gradient norms. They do not contain a full per-epoch train/validation loss curve, so the exported curve table is marked `summary_only_no_per_epoch_curve_stored`.

Actor training decision: `gate3b_a5_actor_training_completed`

GPU-active hours: `4.0000057585581414`

CUDA BF16 training: `True`

Token-budget batching: `True`

Critic used for actor training: `False`

Current diagnosis: training completed mechanically, but the final development replay does not prove that the learned theta policy delivers robust utility over static-flow.
