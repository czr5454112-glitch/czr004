# Repair5G.5.56 Server Environment And Code Audit

Date: 2026-06-16
Scope: audit only. No G5.56 replay, tmux job, training, validation, or blind run was launched.

## Verdict

The KCS/Paratera server is operational for a future G5.56 run, but the current remote working directory is not an authoritative synced git checkout. It is a run-package directory from G5.54/G5.55:

```text
/root/czr004_g554_remote
```

It has no `.git` metadata, so a future G5.56 launch must first create or upload a fresh package from local commit:

```text
9e083eb139a1525128cf42ef967553b9dfeec669
```

Recommended launch state for G5.56:

```text
/root/shared-nvme/czr004_g556_9e083eb/
```

Do not run G5.56 from `/root/czr004_g554_remote` without syncing first.

## Server Identity

SSH target audited:

```text
host: ssh.zw1.paratera.com
port: 2222
user: root@ackcs-00gjh3x3
hostname: p-bf62b534b438-ackcs-00gjh3x3
kernel: Linux 5.15.0-119-generic x86_64
server time: 2026-06-16T13:17:28+08:00
```

## Storage

Live `df -h` result:

```text
/: 30G size, 2.4G used, 28G available, 8% used
/root/shared-nvme: 250G size, 449M used, 250G available, 1% used
```

The live mount reports `250G` for `/root/shared-nvme`, even though the original instance description said `150 GB`. Treat the live `df` value as the operational source of truth for this session.

Root-only large file audit:

```text
find /root/czr004_g554_remote -xdev -type f -size +50M
```

Result: no files larger than 50 MB remain under the root-disk run package.

Useful G5.55 large artifacts are archived on shared storage:

```text
/root/shared-nvme/czr004_g555_remote_artifacts
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

G5.56 storage rule: write plans, results, raw CSVs, JSONLs, and tmux logs under `/root/shared-nvme`, not `/root`.

## GPU And Runtime Environment

GPU audit:

```text
NVIDIA GeForce RTX 4090, 23028 MiB total, 1 MiB used, driver 550.54.14
NVIDIA GeForce RTX 4090, 23028 MiB total, 1 MiB used, driver 550.54.14
```

Python audit:

```text
python3: /usr/bin/python3
Python: 3.12.3
torch: 2.7.0a0+7c8ec84dab.nv25.03
torch.cuda.is_available(): true
torch.cuda.device_count(): 2
numpy: 1.26.4
pandas: 2.2.3
sklearn: 1.6.1
```

Toolchain audit:

```text
g++: Ubuntu 13.3.0
cmake: 3.31.6
ninja: 1.11.1.git.kitware.jobserver-1
```

Process audit:

```text
tmux ls: no active sessions
nvidia-smi: GPUs idle
```

The only notable long-running services are the base Jupyter/SSHD supervisor services from the image. No G5.55 or G5.56 solver job is active.

## Remote Code State

Remote code directory:

```text
/root/czr004_g554_remote
```

Git audit:

```text
NO_GIT_REPO
```

This is the main code risk. The directory contains source files and generated outputs, but it cannot prove branch, commit, or dirty state.

Binary audit:

```text
/root/czr004_g554_remote/build/phase1a-batch/phase1a_batch
size: 1.8M
sha256: 593724507e25b7f7380cd7e609c6faed76f964825eac31e56fdab3861cf5ef03
type: ELF 64-bit LSB pie executable, x86-64, dynamically linked
```

Key source/script SHA256 comparison:

```text
file                                      remote sha256                                                     local 9e083eb sha256                                                status
scripts/repair5g555_common.py             a104b4ff553f25e8249501926b3658053fe0e275d24961da46ad17c9a15f8391  866af8dd16a40222d53b18406372a5513952801769ac7db6661f92eb58e63494  mismatch
scripts/run_repair5g555_corrected_validation.py 92024f544499270d8a2127633242d284caab40198a139be38581b64ea620a108 92024f544499270d8a2127633242d284caab40198a139be38581b64ea620a108 match
scripts/run_repair5g555_blind_if_warranted.py 6fa412193e40e9612b9b5299779909d3c555c600832f89ecfaea6d0fc21af9d6 6fa412193e40e9612b9b5299779909d3c555c600832f89ecfaea6d0fc21af9d6 match
scripts/write_repair5g555_decision.py     1f26db092ad4c3909efab37ef12c7ac1971675c7731922acc83785cf78880c0b  1f26db092ad4c3909efab37ef12c7ac1971675c7731922acc83785cf78880c0b  match
scripts/repair5g554_common.py             ddf51dff8d1a8b177bbed31580877e3e290c7273bc00a6443f81b940f8216df3  ddf51dff8d1a8b177bbed31580877e3e290c7273bc00a6443f81b940f8216df3  match
scripts/repair5g553_common.py             297cccf326e73aabb840d355119b2fc99f72af2d0865c34f8ab232e7e8bd9f7d  297cccf326e73aabb840d355119b2fc99f72af2d0865c34f8ab232e7e8bd9f7d  match
cpp/ltm/ltm.cpp                           1fcfaa98949009ac233f6711aecae77a4ec627b8dc2b31ea5e308123ac83d4cf  1fcfaa98949009ac233f6711aecae77a4ec627b8dc2b31ea5e308123ac83d4cf  match
cpp/tools/phase1a_batch.cpp               37bac53d492d0a2cd40eb7bbd055871b0945b36f06d32fa1ba7ee3c794a28fe7  37bac53d492d0a2cd40eb7bbd055871b0945b36f06d32fa1ba7ee3c794a28fe7  match
```

The `repair5g555_common.py` mismatch is expected from the final local governance/manifest update after remote G5.55 execution. It is still a blocker for using the old remote directory as the authoritative G5.56 launch source.

## G5.55 Baseline Evidence Available For G5.56 Planning

Local G5.55 final decision:

```text
decision: g555_fixed_global_staticflow_candidate_blind_passed_keep_claims_closed
promoted fixed candidate: g554_c00051
primary baseline: promoted fixed global staticflow candidate g554_c00051
previous primary baseline: current hand static_flow_shield
validation rows: 120010
blind rows: 120000
phase5p5_allowed: false
phase6_allowed: false
runtime_claim_allowed: false
aaai_ready: false
```

Final candidate evidence:

```text
candidate_id: g554_c00051
success_regression_count_vs_static_flow: 0
success_gain_count_vs_static_flow: 37
both_success_quality_delta_mean_vs_static_flow: -0.0210143833861
bootstrap_ci_upper: -0.0205820545487
shortlist_ready: true
```

G5.56 should treat `g554_c00051` as the active stronger fixed staticflow baseline candidate for this route. Dynamic learned UpdateParams, runtime, Phase5.5, Phase6, and AAAI claims remain closed.

## G5.56 Absence Check

Clean remote file-name check:

```text
find . -maxdepth 5 -iname '*g556*' -o -iname '*repair5g556*' -o -iname '*phase5p5_repair5g556*'
```

Result:

```text
<none>
```

There is no named G5.56 plan, script, or output on the server yet. Earlier broad `*556*` matches were only random task IDs inside G5.54/G5.55 log filenames.

## Required Actions Before Running G5.56

1. Create a fresh shared-storage workdir, preferably `/root/shared-nvme/czr004_g556_9e083eb`.
2. Sync local commit `9e083eb139a1525128cf42ef967553b9dfeec669` to that directory, or clone/fetch from GitHub if network access is reliable.
3. Record a launch manifest with:
   - local commit
   - remote workdir
   - binary SHA256
   - key script SHA256
   - promoted baseline candidate `g554_c00051`
   - root/shared disk state
4. Rebuild `build/phase1a-batch/phase1a_batch` only if G5.56 changes C++ or build flags. If reusing the current binary, record SHA256 `593724507e25b7f7380cd7e609c6faed76f964825eac31e56fdab3861cf5ef03`.
5. Start G5.56 only under tmux, with all large outputs directed to `/root/shared-nvme`.
6. Keep raw result CSV/JSONL out of git; commit compact reports/tables and a large-artifact manifest only.

## Audit Result

```text
g556_server_environment_ready_after_code_sync
```

The environment is healthy, idle, and has enough storage. The code state is not launch-clean because the current remote directory is not a git checkout and is not fully synced to the local pushed commit. This audit is complete, but G5.56 should not be started until the fresh synced workdir exists.

## Post-Run Closeout - 2026-06-18

G5.56 was run from the fresh synced workdir `/root/shared-nvme/czr004_g556_9e083eb` under tmux session `g556`. Large artifacts were kept under `/root/shared-nvme/czr004_g556_remote_artifacts` and raw solver logs were not pulled into git.

The blind replay initially exposed an execution-memory issue in the shared replay runner, caused by aggregate JSONL/checkpoint/result accumulation during a `360,000` row blind run. The runner was repaired by enabling aggregate JSONL skipping, streaming result CSV append, and bounded in-flight futures. After that infrastructure fix, blind replay completed with stable memory.

Final remote decision:

```text
decision: g556_transformer_fixed_global_candidate_blind_passed_keep_claims_closed
promoted fixed candidate: g556_c063174
prior fixed baseline: g554_c00051
blind rows: 360000
blind success regressions vs g554_c00051: 0
blind quality delta vs g554_c00051: -0.0032705119799
learned_safegate_promoted: false
runtime_claim_allowed: false
phase5p5_allowed: false
phase6_allowed: false
aaai_ready: false
```
