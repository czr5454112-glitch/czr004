# G5.56 Surrogate Dataset

- decision: `g556_surrogate_dataset_created`
- rows: `968362`
- primary rows vs g554_c00051: `489227`
- auxiliary rows: `479135`
- parquet status: `/root/shared-nvme/czr004_g556_remote_artifacts/parquet/surrogate_rows.parquet`
- feature leakage: `False`

Primary labels are normalized to `g554_c00051`. Older historical rows without that baseline are retained only as auxiliary representation/ranking data.
