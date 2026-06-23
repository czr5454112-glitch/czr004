# G5.67 Gate-3B r9 Pause Evidence

This is not Gate-3B pass evidence. The run was stopped on user request before solver replay/training/development replay.

- Remote stage root: `/root/shared-nvme/g567_gate3b_bounded_a7bf614e_tmux_r9_pool20000`
- HEAD: `a7bf614e3c92e9d96955dd3dd33274c68b08e30a`
- Runner rc/reason: `143` / `runner_received_signal`
- Forbidden full-campaign actions: `{'final_blind_panel_constructed_or_accessed': False, 'final_blind_solver_replay_launched': False, 'forty_eight_hour_training_launched': False, 'full_100k_generation_launched': False, 'million_row_solver_acquisition_launched': False}`
- Stderr bytes: `0`

## Progress Before Pause

- Context generation: 20000 valid / 21437 attempts, acceptance rate 0.9330
- LABEL_TRAIN materialization: 2000 contexts, 536.8s, `{'traffic_prior_v1_bfs': 2000}`
- DEVELOPMENT materialization: 500 contexts, 68.9s, `{'traffic_prior_v1_bfs': 500}`
- A5 seed actor inference started: True; completed: False
- A5 inference last progress: 318 / 2000 contexts, batch 96 / 602, rows_written=314

## Not Reached

- 60,000-row direct-exact label replay
- 2-4 GPU-active-hour BF16 training
- development replay
- one primary actor selection
- Gate-3B pass report
- full campaign
