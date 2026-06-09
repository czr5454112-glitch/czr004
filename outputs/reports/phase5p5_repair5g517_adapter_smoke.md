# Phase5.5 Repair5G.5.17 Adapter Smoke

- decision: `adapter_smoke_passed_continue_targeted_probe`
- context: `{'map': 'maze-32-32-4', 'agents': 50, 'seed': 151}`
- repair_candidate_count: `10`
- probe_rows: `10`
- candidate_recognized_all: `True`
- updateparams_fingerprint_all: `True`
- external_lacam2_solver_untouched: `True`
- gates: `{'smoke_probe_ran': True, 'repair_candidate_count_eq_10': True, 'repair_candidate_rows_eq_10': True, 'candidate_recognized_all': True, 'updateparams_fingerprint_all': True, 'checkpoint_rows_gt_0': True, 'ids_166_205_untouched': True, 'observed_ids_only': True, 'external_lacam2_solver_untouched': True, 'max_workers_eq_1': True}`

The smoke uses one observed context, `max_workers=1`, and only the ten targeted repair candidates. It is an adapter-recognition check, not a runtime-policy validation.
