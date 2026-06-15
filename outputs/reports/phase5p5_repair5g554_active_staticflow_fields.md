# G5.54 Active static_flow Field Audit

- decision: `g554_active_field_audit_ready`
- goal projection mode: `flow_shield`
- primary active search fields: `theta_alpha_cong_commit_nonprogress, theta_alpha_flow_commit_progress, theta_alpha_flow_wait_progress, theta_lambda_cong, theta_flow_shield_beta, theta_max_flow_shield, theta_min_edge_cost, theta_max_edge_cost, theta_rho_cong_decay`
- theta_lambda_flow is kept diagnostic unless fresh smoke shows response under flow_shield.
- theta_alpha_flow_wait_progress is searched carefully because the current hand value is zero.
