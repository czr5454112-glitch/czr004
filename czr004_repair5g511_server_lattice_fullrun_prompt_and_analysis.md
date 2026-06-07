# czr004 Repair5G.5.11 分析与 Codex 推进 Prompt

生成日期：2026-06-07
基准提交：`dc500f2 repair5g: execute goal-aware lattice and gate parameter policy`
分支：`phase4f5p5-stable-attention-lau`

---

## 0. 一句话结论

Repair5G.5.10 是一个**好结果**，但不是性能成功，也不是 learned runtime 成功。

它最重要的贡献是：

```text
G5.9 的 bounded goal-aware dual-channel UpdateLTM parameter lattice
已经从“纸面候选设计”
推进到“C++ harness 可执行 + parity smoke 通过 + 本地 2-context counterfactual 产生正 oracle gap”。
```

但它的最终 decision 是：

```text
lattice_adapter_smoke_passed_server_required_for_full_run
```

这意味着：

```text
方向继续成立；
adapter / executable lattice 是重大工程进展；
本地 smoke 太小，不能训练策略、不能 claim Phase5.5/Phase6/AAAI/runtime；
下一步必须跑 full server lattice counterfactuals 并回灌分析。
```

当前最重要的判断是：

```text
不是 goal-aware dual-channel LTM 方向错了；
也不是 bounded parameter lattice 失败了；
而是 full-run evidence 还没跑完，只有 2 个 measured contexts。
```

---

## 1. G5.10 关键事实

最终 summary：

```text
decision = lattice_adapter_smoke_passed_server_required_for_full_run

adapter_decision = lattice_adapter_parity_passed
counterfactuals_run = true
candidate_count = 14
measured_contexts = 2
candidate_space_improves_g58 = true
candidate_space_oracle_gap_vs_g58 = -0.015080627924999979
confidence_targets_decision = confidence_targets_v4_training_gate_failed
feature_signal_decision = feature_signal_v2_failed_continue_feature_design
policy_decision = abstention_parameter_policy_failed_continue_features_or_lattice
server_plan_available = true

phase5p5_allowed = false
phase6_allowed = false
aaai_ready = false
runtime_claim_allowed = false
ids_166_205_untouched = true
```

Adapter parity：

```text
decision = lattice_adapter_parity_passed
lattice_candidate_count = 14
recognized_lattice_rows = 56
additive_fallback_matches_additive_ltm = true
static_flow_shield_matches_prior_static = true
static_abstain_alias_matches_static = true
c_only_f_disabled_candidate_runs = true
c_only_f_disabled_params_verified = true
```

本地 lattice counterfactual smoke：

```text
counterfactuals_run = true
measured_contexts = 2
complete_primary_contexts = 2
primary_1000_2000_stable_contexts = 2
oracle_beats_static_fraction = 1.0
oracle_beats_additive_fraction = 1.0
mean_oracle_gap_over_static = -0.028712565610000018
mean_oracle_gap_over_additive = -0.15941233049000003
candidate_space_oracle_gap_vs_g58 = -0.015080627924999979
per_candidate_win_distribution:
  repair5g59_low_beta_high_cap = 2
```

Confidence targets v4：

```text
decision = confidence_targets_v4_training_gate_failed
measured_confidence_contexts = 2
head_b_training_rows = 2
stable_high_confidence_parameter_candidate = 2
stable_static_or_abstain = 0
no_solution_or_budget_abstain_count = 0
abstain_to_static_count = 0
```

Feature v2：

```text
decision = feature_signal_v2_failed_continue_feature_design
rows = 60
labeled_rows = 2
feature_count = 64
constant_feature_count = 33
dev_rows = 0 in all reported ablations
features_strong_enough_to_distinguish_static_vs_nonstatic_safely = false
```

Policy：

```text
training_skipped = true
blocked_reasons:
  - confidence_targets_v4_training_gate_failed
  - feature_signal_v2_failed_continue_feature_design

eval_skipped = true
skip_reason = abstention_parameter_policy_training_skipped_gate_failed
```

Server plan：

```text
expected_contexts = 60
expected_candidates = 14
expected_full_rows_with_250_500_1000_2000 = 3360
expected_primary_rows = 1680
primary budgets = 1000 / 2000 ms
stress budget = 250 ms
bonus budget = 500 ms
```

---

## 2. 这轮是好是坏？

这是好结果。

原因分三层：

### 2.1 它解决了 G5.9 的最大 blocker

G5.9 的最大问题是：

```text
candidate lattice 设计好了，但不能执行；
counterfactuals_run = false；
candidate_space_oracle_gap_vs_g58 = null。
```

G5.10 已经把这个问题推进到：

```text
C++ phase1a_batch 可以识别 G5.9 lattice candidates；
同一个 counterfactual probe hook 能运行这些 bounded UpdateLTM 参数；
adapter parity 通过；
本地 bounded smoke 产生了可解释正信号。
```

这不是小修小补，而是从 selector 时代真正迈到：

```text
bounded dual-channel UpdateLTM parameter candidate execution
```

### 2.2 它不是“只会写计划”的结果

G5.9 写了 14-candidate lattice，但没有结果。
G5.10 的本地 smoke 虽然只有 2 个 contexts，但它真的跑了 counterfactual：

```text
counterfactuals_run = true
candidate_space_improves_g58 = true
```

这说明候选参数不是报告里的名字，而是可以进入 `UpdateLTM -> DirectedTrafficMap -> WeightedDistanceTable` 的执行路径。

### 2.3 它保留了科学纪律

G5.10 没有因为 2-context smoke 正信号就硬训模型或 claim runtime：

```text
phase5p5_allowed = false
phase6_allowed = false
aaai_ready = false
runtime_claim_allowed = false
```

这很重要。当前正信号非常诱人，但只有 N=2，硬训或 claim 会破坏项目可信度。

---

## 3. 为什么“失败”？

严格说，G5.10 没有在方法方向上失败；它失败在**训练/claim gate** 上。

失败原因非常具体：

```text
measured_contexts = 2 < 60
primary_1000_2000_stable_contexts = 2 < 40
head_b_training_rows = 2 < 40
stable_static_or_abstain = 0 < 10
no_solution_or_budget_abstain_count = 0
feature ablation dev_rows = 0
```

因此：

```text
confidence_targets_v4_training_gate_failed
feature_signal_v2_failed_continue_feature_design
abstention_parameter_policy_training_skipped_gate_failed
```

这不是模型在完整数据上输给 static。
这是因为完整数据还没有跑，policy 根本不应该训练。

---

## 4. 是我们的方向有问题吗？

不是。

反而，G5.10 比 G5.8/G5.9 更支持项目主线。

项目主线是：

```text
learning-enhanced UpdateLTM
替换 LTM 论文中的粗糙 additive update
最终在 closed-loop solver metrics 上超过 LaCAM*+plain additive LTM
同时不改 LaCAM*/PIBT semantics
```

G5.10 的 C++ adapter 正是沿着这条路：

```text
candidate_id
  -> bounded dual-channel UpdateParams
  -> UpdateLTM
  -> DirectedTrafficMap
  -> WeightedDistanceTable
  -> existing LaCAM*/PIBT guidance loop
```

它没有输出：

```text
agent actions
PIBT priorities
restart nodes
h-values
candidate deletion
OPEN/EXPLORED/rewrite/incumbent decisions
```

这说明路线没有偏成 learned MAPF action policy，而是仍然在 learned / parameterized UpdateLTM 内部推进。

---

## 5. “不是已经证明双通道 LTM 有效了吗？”

要区分三件事：

### 5.1 已经证明 static goal-aware dual-channel flow-shield 是强 baseline

之前的 G5/G5.8/G5.9 结果一直说明：

```text
plain additive 往往很弱；
static flow-shield 很强；
nonstatic flow-shield 有机会，但有 harmful risk。
```

### 5.2 G5.8/G5.9 证明 narrow selector 不够

G5.8/G5.9 的二分类 selector 没有打过 train-only majority / map-agent prior / true random-feature model，说明：

```text
只学 static vs 一个固定 nonstatic candidate
不够成为论文主方法。
```

### 5.3 G5.10 开始证明 parameter lattice 有潜力

G5.10 本地 smoke 里：

```text
candidate_space_oracle_gap_vs_g58 = -0.015080627924999979
best candidate = repair5g59_low_beta_high_cap
```

这说明：

```text
扩展 bounded dual-channel parameter space
可能比 G5.8 两候选 selector 有更高 oracle upper bound。
```

但注意，这目前只有 2 contexts，不能 claim。
下一步就是用 60 contexts full run 验证这个 oracle upper bound 是否稳定。

---

## 6. 下一步应该干什么？

下一步不应该再写一个抽象设计，也不应该训练旧 policy。
下一步必须做 **Repair5G.5.11：Full Server Lattice Counterfactual Run + Re-ingest + Parameter-Lattice Oracle Gate**。

核心目标：

```text
运行 G5.10 server plan 的 60 contexts × 14 candidates × 4 budgets = 3360 rows。
```

然后只回答一个问题：

```text
在完整 observed-ID confidence bank 上，
G5.9/G5.10 bounded goal-aware dual-channel parameter lattice
是否稳定提高 oracle upper bound？
```

具体需要：

```text
1. 执行 full lattice run：
   IDs 146..155
   maps random / maze / warehouse
   agents 50 / 100
   budgets 250 / 500 / 1000 / 2000 ms
   candidates = 14
   expected rows = 3360

2. Re-ingest artifacts：
   results CSV
   probe JSONL
   checkpoints JSONL
   oracle_by_context
   feature_matrix_v2
   confidence_targets_v4
   JSON/MD reports

3. 分析：
   measured_contexts >= 60
   primary_1000_2000_stable_contexts >= 40
   oracle_beats_static_fraction
   mean_oracle_gap_over_static
   mean_oracle_gap_over_additive
   candidate_space_oracle_gap_vs_g58
   per-map/agent/seed/candidate distribution
   winner stability between 1000 and 2000 ms
   stress 250 disagreement
   500 bonus agreement

4. 只有 candidate-space gate 过，才允许：
   feature_matrix_v3
   confidence_targets_v5
   abstention-aware parameter policy
```

---

## 7. 下一轮 Codex Prompt

下面这段可以直接发给 Codex。

```text
Continue czr004 on branch phase4f5p5-stable-attention-lau after commit dc500f2 repair5g: execute goal-aware lattice and gate parameter policy.

Implement Repair5G.5.11: full server-scale execution and re-ingest of the executable goal-aware dual-channel UpdateLTM parameter lattice.

Main interpretation to preserve:
- G5.10 is a good result, not a direction failure.
- G5.10 made the G5.9 bounded goal-aware dual-channel lattice executable in C++/phase1a_batch.
- Adapter parity passed:
  lattice_adapter_parity_passed,
  additive fallback matches additive_ltm,
  static flow-shield matches prior static,
  static abstain alias matches static,
  c_only_f_disabled candidate runs,
  all lattice rows recognized.
- G5.10 local smoke ran true counterfactuals, but only on 2 measured contexts.
- Smoke result is promising but insufficient:
  measured_contexts=2,
  primary_1000_2000_stable_contexts=2,
  oracle_beats_static_fraction=1.0,
  oracle_beats_additive_fraction=1.0,
  mean_oracle_gap_over_static=-0.028712565610000018,
  mean_oracle_gap_over_additive=-0.15941233049000003,
  candidate_space_oracle_gap_vs_g58=-0.015080627924999979,
  best smoke winner=repair5g59_low_beta_high_cap.
- Training/policy remains blocked:
  confidence_targets_v4_training_gate_failed,
  feature_signal_v2_failed_continue_feature_design,
  abstention_parameter_policy_training_skipped_gate_failed.
- The next required step is not another paper plan and not another narrow selector.
- The next required step is the full server lattice counterfactual run and artifact re-ingest.

Project objective:
Use learning-enhanced UpdateLTM to replace the coarse additive update in the LTM paper and eventually beat LaCAM*+plain additive LTM under closed-loop solver metrics, without changing LaCAM*/PIBT semantics.

Hard constraints:
- Do not modify external/lacam2/lacam2/**
- Do not change PIBT, LaCAM*, candidate generation, conflicts, pruning, OPEN/EXPLORED, rewrite, incumbent, or restart semantics.
- Do not introduce action prediction, priority prediction, learned restart, h-values, candidate deletion, or MAPF action logits.
- Do not run or peek IDs 166..205.
- Do not claim Phase5.5, Phase6, runtime learned policy, or AAAI-ready.
- Do not train a policy unless full-run candidate-space, confidence-target, and feature gates pass.
- Keep phase5p5_allowed=false, phase6_allowed=false, aaai_ready=false, runtime_claim_allowed=false.

Read first:
- czr004_repair5g510_executable_goal_aware_dual_channel_lattice_plan.md
- outputs/reports/phase5p5_repair5g510_decision.md
- outputs/reports/phase5p5_repair5g510_decision_summary.json
- outputs/reports/phase5p5_repair5g510_lattice_adapter_parity_summary.json
- outputs/reports/phase5p5_repair5g510_lattice_counterfactual_analysis_summary.json
- outputs/reports/phase5p5_repair5g510_confidence_targets_v4_summary.json
- outputs/reports/phase5p5_repair5g510_feature_signal_v2_summary.json
- outputs/reports/phase5p5_repair5g510_abstention_parameter_policy_train_summary.json
- outputs/reports/phase5p5_repair5g510_abstention_parameter_policy_eval_summary.json
- outputs/reports/phase5p5_repair5g510_server_command_plan_summary.json
- scripts/run_repair5g510_goal_aware_dual_channel_lattice_counterfactuals.py
- scripts/analyze_repair5g510_lattice_counterfactual_oracle_gap.py
- cpp/tools/phase1a_batch.cpp

Tasks:

1. Add:
   czr004_repair5g511_full_server_lattice_reingest_plan.md
   and update docs/codex-worklog.md.

2. Verify G5.10 artifacts.
   If required G5.10 artifacts are missing, stop with:
   missing_g510_artifacts_stop.

3. Write:
   outputs/reports/phase5p5_repair5g511_g510_final_interpretation.md
   outputs/reports/phase5p5_repair5g511_protocol_overview.md

4. Execute or prepare the full server lattice counterfactual run.
   Use the G5.10 server command plan as the required full-run baseline:

   powershell -ExecutionPolicy Bypass -File scripts\build_phase1a_batch.ps1

   python scripts/run_repair5g510_executable_lattice_smoke.py --overwrite --max-workers 1

   python scripts/analyze_repair5g510_lattice_adapter_parity.py

   python scripts/run_repair5g510_goal_aware_dual_channel_lattice_counterfactuals.py --overwrite --instance-ids 146..155 --budgets-ms 250 500 1000 2000 --max-contexts-per-group 1 --max-workers 4 --checkpoint-topk-edges 256 --include-full-traffic

   python scripts/analyze_repair5g510_lattice_counterfactual_oracle_gap.py

   If local machine cannot finish, write a server launch package and stop with:
   server_required_for_full_lattice_counterfactuals

   Required server plan artifacts:
   outputs/reports/phase5p5_repair5g511_server_launch_plan.md
   outputs/reports/phase5p5_repair5g511_server_launch_plan_summary.json
   scripts/server_run_repair5g511_full_lattice.sh
   or a Windows/Powershell equivalent if that is the project convention.

5. Re-ingest full-run artifacts.
   Required expected counts:
   expected_contexts = 60
   expected_candidates = 14
   expected_full_rows_with_250_500_1000_2000 = 3360
   expected_primary_rows = 1680

   Write:
   scripts/ingest_repair5g511_full_lattice_artifacts.py
   scripts/analyze_repair5g511_full_lattice_integrity.py

   Gates:
   full_lattice_rows_ge_3360
   candidate_count_eq_14
   measured_contexts_ge_60
   primary_1000_2000_contexts_ge_60
   observed_ids_only=true
   ids_166_205_untouched=true
   JSON/CSV parse clean
   no duplicate context/candidate/budget rows unless explicitly explained

6. Analyze full lattice oracle gap.
   Write:
   scripts/analyze_repair5g511_lattice_oracle_gap_full.py

   Required outputs:
   outputs/reports/phase5p5_repair5g511_lattice_oracle_gap_full.md
   outputs/reports/phase5p5_repair5g511_lattice_oracle_gap_full_summary.json
   outputs/tables/phase5p5_repair5g511_lattice_oracle_by_context.csv
   outputs/tables/phase5p5_repair5g511_lattice_candidate_distribution.csv
   outputs/tables/phase5p5_repair5g511_lattice_by_map_agent.csv

   Required metrics:
   measured_contexts
   primary_1000_2000_stable_contexts
   oracle_beats_static_fraction
   oracle_beats_additive_fraction
   mean_oracle_gap_over_static
   mean_oracle_gap_over_additive
   candidate_space_oracle_gap_vs_g58
   candidate_space_oracle_gap_vs_g510_smoke
   best_single_candidate
   per_candidate_win_distribution
   per_map_agent_candidate_wins
   stress_250_disagreement_rate
   bonus_500_agreement_rate
   warehouse/no-solution/longer-budget counts
   later_iteration_measured_contexts

   Candidate-space gate:
   measured_contexts >= 60
   primary_1000_2000_stable_contexts >= 40
   candidate_space_oracle_gap_vs_g58 < 0
   oracle_beats_static_fraction > 0
   oracle_beats_additive_fraction > 0
   no candidate-space result may use IDs 166..205.

7. Only if full lattice candidate-space gate passes, create confidence targets v5.
   Write:
   scripts/create_repair5g511_confidence_targets_v5.py
   scripts/analyze_repair5g511_confidence_targets_v5.py

   Label classes:
   stable_high_confidence_parameter_candidate
   stable_static
   abstain_to_static
   no_solution_abstain
   longer_budget_needed
   budget_sensitive_exclude
   exclude_from_training

   Required gates:
   measured_confidence_contexts >= 60
   primary_1000_2000_stable_contexts >= 40
   head_b_training_rows >= 40
   stable_high_confidence_parameter_candidate >= 10
   stable_static_or_abstain >= 10
   no_solution_or_budget_abstain_count > 0
   abstain_to_static searched and reported

8. Only if targets v5 gate passes, build feature matrix v3.
   Write:
   scripts/create_repair5g511_feature_matrix_v3.py
   scripts/analyze_repair5g511_feature_signal_v3.py

   Feature requirements:
   - runtime-safe pre-update only
   - no oracle/probe/outcome/candidate-label leakage
   - train/dev split explicit
   - train-only normalization for all model experiments
   - separate measured labeled rows from unlabeled audit rows
   - include richer C/F traffic-before summary if exported:
     c/f nonzero, entropy, quantiles, max, mean, local goal-corridor proxies if available
   - include event burst and progress/nonprogress/wait/block summaries
   - report constant features, train/dev shift, map-agent leakage risk

   Feature gate:
   labeled_rows >= 40
   dev_rows > 0
   constant_feature_count not excessive, or explicitly pruned
   features_strong_enough_to_distinguish_static_vs_parameter_candidate_safely = true
   forbidden_outcome_features_excluded = true

9. Only if candidate-space, targets, and feature gates all pass, train offline abstention-aware parameter policy.
   Write:
   scripts/train_repair5g511_abstention_parameter_policy.py
   scripts/eval_repair5g511_abstention_parameter_policy.py

   Architecture:
   Head A:
     feasibility / abstention / static fallback / longer-budget classifier
   Head B:
     parameter-candidate mixture over bounded UpdateLTM candidates

   Required baselines / controls:
   static flow-shield
   additive
   best single candidate on train only
   train-only majority
   train-only map-agent prior
   true random-feature model
   true shuffled-label model
   oracle upper bound

   Pass gates:
   mean_delta_vs_static < 0
   mean_delta_vs_additive < 0
   beats_best_train_single_candidate or clearly explain why not
   beats_train_only_majority
   beats_train_only_map_agent_prior
   beats_true_random_feature_model
   beats_true_shuffled_label_model
   harmful_vs_static_rate <= 0.10, preferably <= 0.05
   calibration reported
   coverage-risk curve reported
   observed-dev-only evaluation
   ids_166_205_untouched = true

10. If full server run confirms repair5g59_low_beta_high_cap dominates, do not overclaim.
    Write a follow-up lattice refinement note:
    outputs/reports/phase5p5_repair5g511_lattice_refinement_note.md

    It should propose a local neighborhood around:
    low beta / high max_flow_shield
    but should not run fresh reserved IDs.

11. Write final decision:
    outputs/reports/phase5p5_repair5g511_decision.md
    outputs/reports/phase5p5_repair5g511_decision_summary.json

Decision options:
  missing_g510_artifacts_stop
  server_required_for_full_lattice_counterfactuals
  full_lattice_integrity_failed
  full_lattice_candidate_space_failed_expand_lattice
  full_lattice_candidate_space_passed_continue_targets
  confidence_targets_v5_failed_continue_label_design
  feature_signal_v3_failed_continue_feature_design
  abstention_parameter_policy_failed_continue_features_or_lattice
  abstention_parameter_policy_passed_continue_runtime_preflight_design
  stop_for_protocol_or_semantic_bug

Validation:
  python -m py_compile all new/modified Python scripts
  if C++ changed, run scripts/build_phase1a_batch.ps1
  reserved-ID guard rejects 166
  JSON summaries parse
  CSV row-count sanity checks pass
  candidate_count == 14 unless explicitly changing the lattice in a separate gated section
  git diff --check
  push only G5.11-related tracked files/reports
  leave unrelated dirty/untracked files untouched

Commit message:
repair5g: run full goal-aware lattice and reingest oracle gap
```

---

## 8. 服务器执行交接

这轮用户已经给出可用服务器，因此 G5.11 的 prompt 不应该只停在“如果需要服务器就写计划”。
正确交接方式是：

```text
优先把 G5.10 已经通过 parity 的 executable lattice 放到服务器上跑完整 60-context run；
本地仓库负责保留 protocol / ingest / analysis / decision 文件；
服务器只承担 full counterfactual execution，不改变实验边界。
```

### 8.1 服务器信息

```text
实例名称：kcs-hbnefmmg
实例 ID：ackcs-00gjh3x3
站点：中卫二区
资源：RTX4090，2 卡，每卡 24GB 显存
CPU / 内存：22 vCPU / 120GB
系统：Ubuntu 24.04
框架：PyTorch 2.7.0 / PyTorch-25.03-py3
SSH host：ssh.zw1.paratera.com
SSH port：2222
SSH user：root@ackcs-00gjh3x3
```

密码由当前任务上下文提供。不要把原始密码写进 GitHub-tracked markdown、shell 脚本、日志、PR 描述或 commit message。交互登录时使用即可。

推荐 SSH 形式：

```bash
ssh -p 2222 -l 'root@ackcs-00gjh3x3' ssh.zw1.paratera.com
```

### 8.2 服务器启动意图

服务器端优先使用 Linux build script，而不是 Windows PowerShell build command：

```bash
cd /workspace
git clone https://github.com/czr5454112-glitch/czr004.git
cd czr004
git checkout phase4f5p5-stable-attention-lau

python -m pip install -U pip
python -m pip install -r requirements.txt || true

bash scripts/build_phase1a_batch.sh

python scripts/run_repair5g510_executable_lattice_smoke.py \
  --overwrite \
  --max-workers 1

python scripts/analyze_repair5g510_lattice_adapter_parity.py

python scripts/run_repair5g510_goal_aware_dual_channel_lattice_counterfactuals.py \
  --overwrite \
  --instance-ids 146..155 \
  --budgets-ms 250 500 1000 2000 \
  --max-contexts-per-group 1 \
  --max-workers 4 \
  --checkpoint-topk-edges 256 \
  --include-full-traffic

python scripts/analyze_repair5g510_lattice_counterfactual_oracle_gap.py
```

G5.11 实现时应把上面的 server baseline 包装为：

```text
scripts/server_run_repair5g511_full_lattice.sh
outputs/reports/phase5p5_repair5g511_server_launch_plan.md
outputs/reports/phase5p5_repair5g511_server_launch_plan_summary.json
```

脚本应至少包含：

```bash
#!/usr/bin/env bash
set -euo pipefail

export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-4}"

bash scripts/build_phase1a_batch.sh
python scripts/run_repair5g510_executable_lattice_smoke.py --overwrite --max-workers 1
python scripts/analyze_repair5g510_lattice_adapter_parity.py
python scripts/run_repair5g510_goal_aware_dual_channel_lattice_counterfactuals.py \
  --overwrite \
  --instance-ids 146..155 \
  --budgets-ms 250 500 1000 2000 \
  --max-contexts-per-group 1 \
  --max-workers 4 \
  --checkpoint-topk-edges 256 \
  --include-full-traffic
python scripts/analyze_repair5g510_lattice_counterfactual_oracle_gap.py
```

推荐用 `tmux` 或 `nohup` 启动，避免 SSH 断开中止：

```bash
mkdir -p outputs/logs/phase5p5_repair5g511
nohup bash scripts/server_run_repair5g511_full_lattice.sh \
  > outputs/logs/phase5p5_repair5g511/full_lattice_$(date +%Y%m%d_%H%M%S).log 2>&1 &
```

### 8.3 回传与本地 re-ingest

服务器完成后，必须先回传 artifacts，再在本地或服务器上跑 G5.11 re-ingest / integrity / oracle-gap scripts。
至少需要回传：

```text
outputs/tables/phase5p5_repair5g510_lattice_counterfactual_results.csv
outputs/reports/phase5p5_repair5g510_lattice_counterfactual_*.json
outputs/reports/phase5p5_repair5g510_lattice_counterfactual_*.md
outputs/reports/phase5p5_repair5g510_lattice_adapter_parity_summary.json
outputs/logs/phase5p5_repair5g510_lattice_counterfactuals/
```

G5.11 re-ingest 后的最终命名必须使用 `repair5g511` 前缀，而不是把 G5.10 server run 直接冒充为 G5.11 decision：

```text
outputs/reports/phase5p5_repair5g511_full_lattice_integrity.*
outputs/reports/phase5p5_repair5g511_lattice_oracle_gap_full.*
outputs/tables/phase5p5_repair5g511_lattice_oracle_by_context.csv
outputs/tables/phase5p5_repair5g511_lattice_candidate_distribution.csv
outputs/tables/phase5p5_repair5g511_lattice_by_map_agent.csv
outputs/reports/phase5p5_repair5g511_decision.*
```

### 8.4 服务器运行仍然不能放宽 gate

即使 2x4090 服务器完成 full run，也必须继续保持：

```text
phase5p5_allowed = false
phase6_allowed = false
aaai_ready = false
runtime_claim_allowed = false
ids_166_205_untouched = true
```

只有当完整 observed-ID full lattice gate、confidence-target gate、feature gate 和 policy-control gate 依次通过，才允许进入下一轮 runtime preflight 设计。G5.11 的默认结束点仍应是严谨 decision，而不是宣传性 claim。

---

## 9. 底线

G5.10 的正确解读是：

```text
可执行 bounded dual-channel parameter lattice 打通了；
本地 smoke 方向很好；
但只有 2 个 contexts，不能训练，不能 claim；
下一步必须跑完整 server lattice counterfactuals。
```

如果 G5.11 full run 仍显示：

```text
candidate_space_oracle_gap_vs_g58 < 0
mean_oracle_gap_over_static < 0
oracle_beats_static_fraction > 0
```

那项目就真正进入：

```text
learned bounded goal-aware dual-channel UpdateLTM parameter policy
```

而不是继续停在 selector 诊断阶段。
