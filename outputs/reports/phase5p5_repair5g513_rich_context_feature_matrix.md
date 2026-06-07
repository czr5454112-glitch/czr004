# Phase5.5 Repair5G.5.13 Rich Context Feature Matrix

- decision: `rich_context_features_missing_requires_local_feature_probe`
- base_rows: `840`
- rich_matrix_rows: `1`
- present_allowed_rich_fields: `[]`
- forbidden_feature_count: `0`
- observed_ids_only: `True`
- ids_166_205_untouched: `True`
- runtime_claim_allowed: `false`

Existing tracked G5.11/G5.12 artifacts are scanned for explicitly allowed pre-choice rich runtime fields. When those fields are absent, this script records `rich_context_features_missing_requires_local_feature_probe` and does not fabricate rich features. Any later local probe must use approved observed IDs, `--max-workers 1`, and no solver semantic changes.
