# Phase5.5 Repair5G.5.16 Targeted Repair Lattice

- decision: `targeted_repair_lattice_requires_adapter_followup`
- new_candidate_count: `10`
- executable_candidate_count: `0`
- gates: `{'error_bank_available': True, 'new_candidate_count_le_12': True, 'update_only': True, 'current_cpp_adapter_recognizes_all': False}`
- cplusplus_changed: `false`
- solver_probe_allowed: `false` unless the adapter recognition gate is satisfied later

## Candidate Neighborhood

- `repair5g516_slow_decay_safer_beta025_cap050` (safer_slow_decay): executable=`False`, hypothesis=`lower shield beta and cap to reduce slow-decay harmful false positives`
- `repair5g516_slow_decay_safer_beta020_cap045` (safer_slow_decay): executable=`False`, hypothesis=`slightly faster congestion decay and lower shield cap`
- `repair5g516_slow_decay_safer_beta015_cap040` (safer_slow_decay): executable=`False`, hypothesis=`conservative slow-decay boundary variant`
- `repair5g516_wait_aggressive_low_cap` (wait_neighborhood): executable=`False`, hypothesis=`capture wait-heavy maze opportunities with lower cap`
- `repair5g516_wait_conservative_mid_cap` (wait_neighborhood): executable=`False`, hypothesis=`near-static wait-safe boundary candidate`
- `repair5g516_wait_aggressive_fast_flow_decay` (wait_neighborhood): executable=`False`, hypothesis=`wait-aggressive with faster flow decay to reduce persistence risk`
- `repair5g516_commit_heavy_low_beta` (commit_neighborhood): executable=`False`, hypothesis=`random a50-style commit-heavy alternative to slow decay`
- `repair5g516_commit_heavy_static_guard` (commit_neighborhood): executable=`False`, hypothesis=`commit-heavy variant with conservative static-boundary guard`
- `repair5g516_static_boundary_light_flow` (conservative_static_boundary): executable=`False`, hypothesis=`minimal nonstatic boundary for abstention calibration`
- `repair5g516_static_boundary_c_only` (conservative_static_boundary): executable=`False`, hypothesis=`congestion-only static-boundary contrast`

The lattice is an update-parameter design artifact only in this round. Because these `repair5g516_*` names are not recognized by the current C++ adapter, the local probe must stop before solver execution.
