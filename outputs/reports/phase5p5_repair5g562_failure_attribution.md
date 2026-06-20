# G5.62 Failure Attribution

- decision: `g562_rich_actor_no_supported_gain_continue_representation_or_label_repair`
- exact materialized candidate rows: `18200`
- max exact contexts: `1000`
- best cycle3 method: `A1_seed562_dual_stream_c0_f0_graph_actor`
- best mean quality delta vs g556: `-0.10119481235057097`
- best success regressions: `6`

If the promotion gate is not met, the failure is attributed only to exact solver evidence: success regression, mean/CI quality, better/worse balance, or incomplete materialization. It is not inferred from offline loss, critic score, or checkpoint existence.
