# Phase1a Server Shutdown Preservation

Date: 2026-05-23
Status: preservation complete; server can be shut down after user review

## Purpose

Before shutting down the rented server, preserve every server-side artifact that is useful for auditing or reproducing the completed Phase1a run.

## Already Preserved Main Results

The main full-batch artifacts were downloaded earlier and verified in `outputs/reports/phase1a_server_full_integrity_report.md`.

- Raw full JSONL: `outputs/logs/phase1a/phase1a_plus_3000_runs.jsonl`
- Full stdout/stderr and preflight logs: `outputs/logs/phase1a/`
- Started/finished markers: `outputs/logs/phase1a/`
- Summary CSV: `outputs/tables/phase1a_plus_3000_ratio_by_map.csv`
- Summary figure: `outputs/figures/phase1a_plus_3000_ratio_by_map.png`
- Server scenario metadata copy: `outputs/logs/phase1a/phase1a_generated_scenarios_manifest_server.json`

The generated scenario zip was not re-downloaded because the local file already matches the server hash:

- Local path: `outputs/tmp/phase1a/generated/phase1a-generated-random.zip`
- SHA256: `de0308757a107e845de0cf9a200c6bb8144ed1da3134ca8484f86468bb722a93`

## Additional Preserved Server Files

These files were downloaded to ignored local directory `outputs/logs/phase1a/server_preserve/`.

| File | Size | SHA256 |
| --- | ---: | --- |
| `czr004_phase1a_server_package.tar.gz` | 31,861,223 | `b980f8463b11b9d9fbde4e77a79ee0afba2133bfbf89f362b2c2b15126beefbf` |
| `phase1a_batch_linux` | 378,552 | `cb373aec93c8eb07c89ec876257882cf75d30d9e65e3057d967d6076eb494b94` |
| `phase1a_server_3000_probe.jsonl` | 1,118 | `2322278bed8d3a0d4bee4cf448128ab9e5396d7cfbb4f718c7cc1a27ed27cf2b` |
| `phase1a_server_dry_run.jsonl` | 1,988 | `8226459c03833d0178b11fe257eb23a04df3fb9a2280fe0093dfd93ce373b0d7` |
| `phase1a_server_generated_highN_probe.jsonl` | 2,242 | `1acf72f2f075a76315ecd2f587abca6103a1006561a4574e64013ddbe231efa0` |
| `server_setup_phase1a.sh` | 2,304 | `b1ae67590cd2e13ffc12fd157d168259e7c584a7329552b3a18a9e4e5ad4edc5` |
| `server_start_phase1a_full.sh` | 1,591 | `67a3daa57c0d453b4da7bccdc7fa1c4a41811cd24078c067dcf16aa001026fa2` |
| `server_start_phase1a_setup_tmux.sh` | 499 | `04569d960cd16ead688b508ae4b218c3cda2778467df996ee3a712119a9f9b74` |

## Server-Side Comparison

The server still contained the following useful files before shutdown:

- `/root/shared-nvme/czr004_phase1a_65984db`: full server work directory, about 100 MB.
- `/root/shared-nvme/czr004_phase1a_server_package.tar.gz`: original uploaded runtime package, about 31 MB.
- `/root/shared-nvme/server_setup_phase1a.sh`
- `/root/shared-nvme/server_start_phase1a_full.sh`
- `/root/shared-nvme/server_start_phase1a_setup_tmux.sh`

The full work directory is reproducible from the preserved runtime package, source repository, generated scenario zip, downloaded results, and preserved Linux binary. The large full work directory was not downloaded recursively because it contains rebuildable source/build/cache copies.

## Verdict

No important Phase1a server artifact remains uniquely available only on the server. The server can be shut down from the Phase1a audit perspective.
