# Phase5.5 Repair5G.5.18 Surrogate Lattice Proposal

- decision: `surrogate_candidate_batches_selected_continue_adapter_verification`
- surrogate_model: `evidence_weighted_param_context_knn`
- training_example_count: `399`
- candidate_pool_count: `300`
- selected_new_candidate_count: `30`
- old14_control_count: `14`

## Selected Batches

- Batch `A`: new candidates `12`, total candidates `26`, families `{'block_heavy': 3, 'flow_decay': 3, 'high_beta': 1, 'static_boundary': 2, 'wait_conservative': 3}`
- Batch `B`: new candidates `10`, total candidates `24`, families `{'block_heavy': 3, 'flow_decay': 3, 'high_beta': 1, 'wait_conservative': 3}`
- Batch `C`: new candidates `8`, total candidates `22`, families `{'high_beta': 3, 'low_beta_high_cap': 2, 'static_boundary': 3}`

## Best Surrogate Rows

- `repair5g518_grid_c1p25_b1p25_f1p00_w0p50_dc0p95_df1p00_beta0p35_max0p75_c0` (wait_conservative): mean predicted gap `0.035209441609`, risk `0.02527248259`
- `repair5g518_grid_c1p25_b1p25_f1p00_w0p45_dc0p95_df1p00_beta0p35_max0p75_c0` (wait_conservative): mean predicted gap `0.037074743955`, risk `0.075452528675`
- `repair5g518_grid_c1p25_b1p25_f1p00_w0p50_dc0p95_df1p00_beta0p30_max0p75_c0` (wait_conservative): mean predicted gap `0.0376080874`, risk `0.081526778762`
- `repair5g518_grid_c1p25_b1p25_f1p00_w0p45_dc0p95_df1p00_beta0p30_max0p75_c0` (wait_conservative): mean predicted gap `0.038053656788`, risk `0.097445231214`
- `repair5g518_grid_c0p90_b1p50_f1p00_w0p45_dc0p95_df1p00_beta0p35_max0p75_c0` (block_heavy): mean predicted gap `0.03897500817`, risk `0.105059954447`
- `repair5g518_grid_c0p90_b1p50_f1p00_w0p45_dc0p95_df1p00_beta0p45_max0p75_c0` (block_heavy): mean predicted gap `0.039141146894`, risk `0.119570412755`
- `repair5g518_grid_c1p25_b1p25_f1p00_w0p35_dc0p95_df1p00_beta0p35_max0p75_c0` (wait_conservative): mean predicted gap `0.039254266166`, risk `0.135483481981`
- `repair5g518_grid_c1p25_b1p25_f1p00_w0p75_dc0p92_df0p98_beta0p35_max0p75_c0` (flow_decay): mean predicted gap `0.040672119063`, risk `0.047378640699`
- `repair5g518_grid_c1p25_b1p25_f1p00_w0p75_dc0p92_df0p95_beta0p35_max0p75_c0` (flow_decay): mean predicted gap `0.040755883279`, risk `0.051839706009`
- `repair5g518_grid_c0p90_b1p65_f1p00_w0p45_dc0p95_df1p00_beta0p35_max0p75_c0` (block_heavy): mean predicted gap `0.039619322817`, risk `0.141131793291`

The surrogate is used only to propose executable bounded UpdateParams candidates. Final claims remain tied to local counterfactual probe evidence, not this proposal score.
