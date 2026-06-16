# G5.55 Remote Archive

Remote large artifacts were copied to:

```text
/root/shared-nvme/czr004_g555_remote_artifacts
```

The remote root disk filled because the G5.55 blind replay wrote large intermediate JSONL files under `/root/czr004_g554_remote`, which is on the 30 GB root filesystem. The 150 GB shared storage is a separate mount at `/root/shared-nvme`; jobs must write large retained artifacts there directly or move them there after completion.

After archiving the useful validation/blind plan and result CSVs to shared storage, the root-only intermediate logs and archived duplicates were removed. Final remote storage state:

```text
/: 30G size, 2.4G used, 28G available, 8% used
/root/shared-nvme: 150G size, 449M used, 150G available, 1% used
```

Archived files:

```text
blind_plan.csv          49M
blind_results.csv      165M
validation_plan.csv    60M
validation_results.csv 177M
```

SHA256:

```text
e02e0e08dd543690fca8a2c7349e9c50cab576fee1c63aa109fe899d894394b3  blind_plan.csv
cea67cbf4ff211ce55f0edc2a649b526558425588085174cfa9dc935799867cf  blind_results.csv
cc5c774b4ee5d18c0106df684cbffb4212bc3a318a4864893d4109c5c4ff646e  validation_plan.csv
34b37fc0c0940565755d17407749407c99850527096b9159d14895b4d015a7c0  validation_results.csv
```
