# Phase1a Server Full Batch Integrity Report

Date: 2026-05-23
Status: integrity pass; scientific interpretation pending final paper-parity signoff

## Run Identity

- Server work directory: `/root/shared-nvme/czr004_phase1a_65984db`
- Manifest: `configs/phase1a/manifest_plus_3000.jsonl`
- Project commit recorded in JSONL: `65984dbf729e90177cb72cecab49cc222bd1bd1f`
- External LaCAM2 commit recorded in JSONL: `61a4c40ce91ce18c06eb2fe070aa9f1951eecb8d`
- Branch recorded in JSONL: `phase1a-ltm-paper-parity`
- Dirty state recorded in JSONL: `clean`
- Platform recorded in JSONL: `Linux server package via ssh-skill tmux`
- Preflight: `Phase1a preflight passed. Tasks=3800`
- Started: `2026-05-22T10:15:11+08:00`
- Finished: `2026-05-23T19:05:33+08:00`
- Elapsed wall time: about 32 h 50 m

## Downloaded Files

Raw logs are stored under ignored `outputs/logs/phase1a/`; summary artifacts are tracked.

| File | Local path | SHA256 |
| --- | --- | --- |
| JSONL results | `outputs/logs/phase1a/phase1a_plus_3000_runs.jsonl` | `9d491f0b0f7bafb1194363799ddac00ce446aa8edb2b7f485b4438999c1cbfec` |
| Summary CSV | `outputs/tables/phase1a_plus_3000_ratio_by_map.csv` | `e195ba30641e067d79dced648944c6b670daea972b4b1d779d9f52e550f1f59f` |
| Summary figure | `outputs/figures/phase1a_plus_3000_ratio_by_map.png` | `43a823fae9612290d18e7d1b0c9ba3e842dd17a627fbcde61e17a1437f0dd0cc` |
| Full stdout | `outputs/logs/phase1a/full_stdout.log` | `c91d46c37f76a7e4952e9169556b739da28a2985fa5bf4a1c0b3dbe26f982947` |
| Full stderr | `outputs/logs/phase1a/full_stderr.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| Preflight stdout | `outputs/logs/phase1a/full_preflight.log` | `4655ff779fba33c8f116fa40a7a4f7fc8b2c5d86e21e534cc7d0350ce87e7b62` |
| Started marker | `outputs/logs/phase1a/full_started_at.txt` | `86b6d101d0505bc74961cac582c6e6c1292733199359f70ade339804229cde53` |
| Finished marker | `outputs/logs/phase1a/full_finished_at.txt` | `cd1acf17c5c42783385777e743eaa3fa9b0447d7b6f928751212a7f010aeef79` |

The local hashes match the server-side `sha256sum` values.

## Structural Checks

| Check | Result |
| --- | ---: |
| JSONL rows | 3800 |
| Expected rows from manifest | 3800 |
| JSON parse errors | 0 |
| Unique `(map, agents, seed, method)` keys | 3800 |
| Duplicate keys | 0 |
| Missing expected keys | 0 |
| Unexpected keys | 0 |
| `valid_instance=true` rows | 3800 |
| `time_limit_sec=30` rows | 3800 |
| Methods | `lacam_star`: 1900; `lacam_star_ltm`: 1900 |
| Summary CSV groups | 152 |
| Re-summarized CSV hash | matched server CSV |
| Summary PNG signature | valid PNG signature |
| stderr | empty |

## Success Counts

| Scope | `lacam_star` | `lacam_star_ltm` |
| --- | ---: | ---: |
| Base 72 paper-parity points | 1799 / 1800 | 1787 / 1800 |
| 3000-agent extension | 57 / 100 | 58 / 100 |
| All plus-3000 manifest rows | 1856 / 1900 | 1845 / 1900 |

All successful rows were feasible; no successful infeasible solution was recorded.

## Preliminary Effect Snapshot

This is a sanity check on completed rows, not the final paper-parity writeup.

| Scope | Paired successful instances | LTM better | Average LaCAM* ratio | Average LTM ratio | Relative ratio improvement |
| --- | ---: | ---: | ---: | ---: | ---: |
| Base 72 paper-parity points | 1787 | 1758 | 2.884359 | 2.440896 | 15.3747% |
| 3000-agent extension | 53 | 21 | 6.104658 | 6.059662 | 0.7371% |
| All paired successes | 1840 | 1779 | 2.977118 | 2.545133 | 14.5102% |

At the group level, the base paper-parity schedule has lower mean ratio for `lacam_star_ltm` than `lacam_star` on all 72 base map-agent groups. The 3000-agent extension is mixed and must be reported separately.

## 3000-Agent Extension Notes

| Map | Agent count | LaCAM* success rate | LTM success rate | LaCAM* mean ratio | LTM mean ratio | Note |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `random-64-64-20` | 3000 | 0.28 | 0.32 | 9.652097 | 10.073940 | LTM solved more rows but had worse mean ratio among solved rows |
| `room-64-64-8` | 3000 | 0.00 | 0.00 | n/a | n/a | no solved rows in 30s |
| `warehouse-10-20-10-2-1` | 3000 | 1.00 | 1.00 | 9.848979 | 9.706904 | LTM better |
| `warehouse-10-20-10-2-2` | 3000 | 1.00 | 1.00 | 1.908131 | 1.912685 | LTM slightly worse |

## Verdict

The server full batch is complete and structurally valid. The base 72-point paper-parity subset is ready for final scientific comparison against the LTM paper figures. The 3000-agent rows are valid extension data but are not part of the paper-parity claim.
