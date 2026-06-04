# Phase5.5 Repair5G.5.1 Counterfactual Update Probe

- context_count: `500`
- label_rows: `3500`
- available_label_rows: `0`
- result: `true_counterfactual_labels_unavailable`

The probe refuses to derive labels from final full-run outcomes because those labels are not causally tied to the specific pre-update context. Minimal C++ checkpoint export is required before neural selector training.
