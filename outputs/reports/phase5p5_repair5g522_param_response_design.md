# Repair5G.5.22 Parameter Response Design

- decision: `param_response_design_passed_continue_adapter`
- raw_pool_count: `529`
- selected_g522_candidate_count: `48`
- old14_candidate_count: `14`
- g518_retained_candidate_count: `8`
- g521_previous_wave_candidate_count: `16`
- probe_candidate_count: `70`
- selected_region_counts: `{'A_g518_winner_neighborhood': 12, 'B_static_recovery_feasibility': 12, 'C_risk_boundary': 8, 'D_fractional_coverage': 16}`
- gates: `{'old14_count_eq_14': True, 'g518_retained_count_eq_8': True, 'g521_selected_count_eq_16': True, 'raw_pool_count_ge_240': True, 'selected_g522_count_le_48': True, 'selected_g522_count_eq_48': True, 'raw_method_string_dedup': True, 'selected_fingerprint_dedup': True, 'no_selected_exact_duplicate_of_g518': True, 'probe_candidate_count_le_70': True, 'g521_analysis_only': True}`

G5.21 candidates are retained as analysis-only previous-wave controls. The probe set is old14 + retained G5.18 + selected G5.22 response-surface candidates.
