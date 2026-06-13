## 2026-05-29 Repair5 layered gate research policy

GPTPro's recommendation is incorporated as a Repair5 evaluation-policy update.
It does not lower the final runtime or paper-claim gate.

Key decision:

```text
Use layered gates for research triage.
Keep final runtime/paper gates strict.
Do not use Repair3-style hard-label top1/top3 as the only early signal for
attention-native labels.
Require closed-loop benefit over LTM before performance claims.
```

Repair5 now distinguishes:

```text
Development gate:
  asks whether a direction is worth continuing.
  It may use softer top1/top3/safety thresholds and opportunity-subset
  anti-escape diagnostics.

Promotion-candidate gate:
  asks whether a direction deserves larger training or tightly scoped
  closed-loop smoke planning.

Runtime / paper-claim gate:
  remains strict and requires original Phase4F, attention-native, safety,
  anti-escape, and multi-seed gates, followed by closed-loop evidence.
```

The new diagnostic evaluator is:

```text
src/eval/eval_laur_repair5_layered_gate.py
outputs/reports/phase4f_repair5_layered_gate_summary.json
outputs/reports/phase4f_repair5_layered_gate_report.md
```

Remote re-score of completed Repair5 summaries under this policy:

```text
summaries: 27
development pass: 0
promotion-candidate pass: 0
strict seed pass: 0
```

This means the layered policy is useful for analysis, but it does not make any
completed Repair5 scheme eligible for Phase5.5. Current nextwave/postnext
experiments remain necessary. Phase6 remains forbidden until closed-loop
learned-benefit evidence exists.

## 2026-05-31 Repair5B next-round research policy

GPTPro's `phase4f55_laur_repair5b_next_round_codex_plan.md` is incorporated as
the next research-policy update for Repair5B. This is not a direction switch and
not a gate relaxation.

Core interpretation:

```text
expand5000 / high-token data is valid and opportunity-rich.
Repair5 has not shown that the current flat attention selector can jointly
satisfy ranking + safety + anti-escape.
The next step is structured diagnosis and hierarchical LAUR, not another
unstructured loss-weight sweep.
```

The main route remains:

```text
learned UpdateLTM / LAUR only
no agent-action policy
no learned restart
no PIBT or LaCAM* semantic change
no collision/candidate/pruning/rewrite semantic change
no final-gate lowering
```

Repair5B research sequence:

```text
1. failure decomposition + oracle upper bound
2. per-rule / per-family safety calibration
3. hierarchical attention-native LAUR controller
4. curriculum training: rank-first, safety-first, high-margin specialist
5. stratified sampler and hard-case replay
6. active hard-case data aggregation when diagnostics justify it
7. bounded UpdateLTM parameter/residual head only if oracle shows the static
   rule space is limiting
8. recent AI / robotics / MAPF architecture memo for inspiration only
```

The most important new scientific question is the oracle gap:

```text
If oracle_best_safe_rule cannot beat additive LTM by a meaningful margin,
then the eight static update rules may be too coarse.
If oracle_best_safe_rule is strong but models have high regret, then the model,
training, calibration, or data balance is the bottleneck.
```

Hierarchical LAUR is preferred over the current flat selector because the failed
Repair5 runs show a recurring tradeoff:

```text
anti-escape pressure improves non-additive selection but can hurt recall;
safety pressure can suppress opportunity capture;
target-rule pressure can improve top3 while leaving safety/anti unstable.
```

Repair5B should separate these decisions:

```text
decision_head: defer_ltm vs use_nonadditive
safety_head: per-rule harmful probability
rank_head: rank safe non-additive rules
utility_head: risk-adjusted utility / selected-vs-additive gain
fallback logic: defer when safety or margin is insufficient
```

This is compatible with recent hybrid learning/planning practice only at the
architecture and experiment-design level. The project may borrow ideas such as
graph/cross attention, modular controllers, curriculum, uncertainty/abstention,
hard-case mining, pretrain/fine-tune, and ablation discipline. It must not
borrow agent action decoders, learned collision handling, diffusion robot action
generation, VLA action policies, learned restart, or replacements for PIBT /
LaCAM*.

New expected evidence artifacts:

```text
outputs/reports/phase4f_repair5_failure_decomposition.md
outputs/reports/phase4f_repair5_failure_decomposition.json
outputs/tables/phase4f_repair5_oracle_gap.csv
outputs/reports/phase4f_repair5_per_rule_safety_calibration.md
outputs/tables/phase4f_repair5_per_rule_safety_thresholds.csv
outputs/reports/phase4f_repair5_recent_ai_robotics_architecture_memo.md
artifacts/teacher/laur/repair5_hardcase_index.jsonl
```

Phase5.5 remains forbidden until strict Repair5B seed61 passes, seeds 103/107
also pass, final multi-seed gate passes, safety and anti-escape are clean,
selected-vs-additive delta is positive, deterministic export exists, and
fallback/defer reasons are logged. Phase6 still requires later closed-loop
learned-benefit evidence against LTM.

## 2026-05-31 GPTPro/Claude evaluation-policy clarification

The GPTPro/Claude discussion is incorporated as a distinction between paper
evaluation and engineering promotion. It does not make any current Repair5 or
Repair5B result eligible for Phase5.5.

Accepted:

```text
All-class Repair3-style top1 is not the main Repair5 research KPI.
Repair5 attention-native labels should be judged by closed-loop relevance:
  safe utility top-k
  utility regret to oracle
  selected_vs_additive_delta
  high-margin opportunity capture
  harmful recall / precision
  fallback/defer behavior
  later closed-loop benefit over additive LTM
The final paper claim must be closed-loop learned benefit over LTM,
not offline classifier fit alone.
```

Not accepted as a runtime rule:

```text
Do not replace Phase5.5 engineering gates with paper KPIs.
Do not use "closed-loop is what matters" to bypass offline safety,
anti-escape, force-additive/defer parity, deterministic export, or multi-seed.
Do not treat current Repair5 evidence as publication-ready.
It is directional signal, not a stable candidate.
```

The policy is:

```text
Development gate:
  softer research-triage gate, top1 diagnostic only, no runtime permission.

Promotion-candidate gate:
  may trigger diagnostic closed-loop preflight planning only.
  This is not Phase5.5 promotion and not Phase6 evidence.

Runtime / Phase5.5 gate:
  strict original or formally approved utility-equivalent gate,
  harmful recall >= 0.80, harmful precision >= 0.30,
  anti-escape hard pass or equivalent behavioral proof,
  final multi-seed evidence, parity, deterministic export,
  no solver semantic change.

Phase6 / paper gate:
  closed-loop > additive LTM / LaCAM*+LTM,
  multi-map / multi-seed statistics,
  ablations without learned LAUR, without anti-escape, without safety,
  Repair3 baseline, and additive LTM baseline.
```

Any diagnostic closed-loop preflight must be labeled:

```text
not Phase5.5 permission
not runtime promotion
not Phase6 evidence
hard safety mask enabled
force-additive/defer parity checked
only measuring offline-to-closed-loop transfer
```

# NTM for Lightweight Traffic Map 项目指南

生成日期：2026-05-20  
项目目录：`C:\PROGRAMING\czr004`  
当前材料：

- `C:\PROGRAMING\czr004\2603.07891v1.pdf`：*A Lightweight Traffic Map for Efficient Anytime LaCAM\**
- `C:\PROGRAMING\czr004\deep-research-report (1).md`：网页端 GPT-5.5 生成的粗略项目总纲
- `C:\PROGRAMING\czr003\deep-research-report.md`：参考项目指南风格与管理规范

## 执行摘要

本项目的目标是：**在 LTM 论文路线之上继续前进，引入 Neural Traffic Map，简称 NTM**。后续所有比较、复现和神经改进都围绕 LTM 论文同口径展开。

正确主线只有一条：

```text
LaCAM* baseline
  -> LaCAM* + LTM paper-faithful reimplementation
  -> LaCAM* + NTM
```

这里的 `LaCAM*+LTM paper-faithful reimplementation` 是为了建立 LTM teacher、指标口径和可复现实验框架；最终研究贡献是 `LaCAM*+NTM` 是否能在 LTM 同口径指标上打平或超过 `LaCAM*+LTM`，并在部分场景中带来更好的泛化、收敛或低开销表现。

本指南特别修正粗略报告里的一个方向性错误：**项目只沿 LTM 论文路线推进**。LTM 论文的实验对象是 LaCAM* 及其 guidance 变体，因此本项目不扩展成其他求解器工程对比。

第一步不是写 solver 代码，而是把研究路线、工程边界、指标口径、git 管理和 Markdown 记录纪律固定下来。MAPF 项目最容易失败的方式不是“模型不够复杂”，而是 baseline 口径漂移、实验日志不全、改了搜索底座却不知道改坏了什么。因此本项目把“底座保护”和“可复现记录”放在与算法同等重要的位置。

## 复审修订结论

以下修订点是后续执行的准绳。

| 修订点 | 结论 | 新要求 |
|---|---|---|
| 项目主线 | 只做 LTM -> NTM | 删除所有额外工程路线计划 |
| baseline | baseline 只按 LTM 论文口径设置 | 只比较 LaCAM*、LaCAM*+TO、LaCAM*+SUO、LaCAM*+LTM、LaCAM*+NTM |
| LTM 基座 | PDF 实验段写明 `LaCAM*+LTM` built on original LaCAM* codebase | 使用 LaCAM* 作为唯一搜索底座 |
| LTM 源码状态 | PDF 仓库脚注仍是占位地址 | 本项目实现称为 `paper-faithful reimplementation`，不能声称官方复现 |
| 边权范围 | PDF 方法段写实验使用 `[wLB, wUP] = [0, 10]` | 实现默认 `[0,10]`，粗略报告中的 `[1,5]` 作废 |
| gate 强度 | NTM 早期可能只在部分场景打平或改善 | gate 不要过严，早期以打平、可解释、低 overhead、语义正确为有效进展 |
| 科学故事 | 纯拟合 LTM 边权容易变成 teacher distillation | NTM 主线必须包含 online residual、ranking 或 safety 之一，证明闭环 solver 收益 |
| 节点级公平性 | wall-clock 可能掩盖搜索努力差异 | metrics 固化 expanded nodes / high-level expansions，支持 equal-node 对照 |

## 研究问题

在 LaCAM* 的 anytime 搜索框架中，能否用神经网络学习或修正 LTM 的 traffic map 更新机制，使 solver 在相同 wall-clock 预算下获得更好的 `sum-of-loss ratio`、更快的 anytime 收敛、更稳定的 dense/bottleneck 表现，或者更低的 guidance overhead？

换句话说，本项目不问“能不能换掉 LaCAM*”，而问：

- LTM 手工累计 traffic history 是否能被更好的 learned update 替代？
- NTM 能否保持 LTM 的低开销和可回退性？
- NTM 能否在 LTM 论文同口径指标上打平或超过 LTM？
- NTM 的收益来自 traffic map 学习本身，还是仅来自 restart、随机性或指标误差？
- NTM 是否能在跨 seed、跨 agent density 或留图测试中表现出比手工 LTM 更好的泛化？

## 主目标

- 复现 `LaCAM*+LTM`，作为 paper-faithful teacher 和强 baseline。
- 实现 `LaCAM*+NTM`，让神经网络输出 bounded directed edge costs 或 residual traffic corrections。
- 在 LTM 论文同口径指标上比较 `LaCAM*`、`LaCAM*+TO`、`LaCAM*+SUO`、`LaCAM*+LTM`、`LaCAM*+NTM`。
- 保护 LaCAM* 搜索语义：NTM 只能作为 guidance 层，不能删除合法动作，不能绕开 PIBT 冲突语义。
- 每次 Codex 写代码、改实验、跑评测，都必须同步写 Markdown 记录。

## 非目标

- 不引入其他工程化求解器作为 baseline。
- 不做额外工程路线实现。
- 不端到端替代 LaCAM*。
- 不重写 PIBT、LaCAM* high-level search、lazy constraint addition、rewrite / incumbent 语义。
- 不让未验证神经网络直接接管搜索控制权。
- 不把“NTM 必须一开始大幅超过 LTM”作为早期 gate。

## LTM 论文硬约束

| 维度 | LTM 论文口径 | 本项目采用方式 |
|---|---|---|
| 搜索底座 | original LaCAM* codebase | 全项目使用 LaCAM* 作为唯一底座 |
| LTM 结构 | 与原 MAPF 图同构的 directed weighted graph | NTM 也输出同构 directed edge cost |
| 边权范围 | `[0,10]` | 默认实现和配置采用 `[0,10]` |
| 信息来源 | PIBT committed actions + blocked actions | trace collector 必须记录两类事件 |
| wait action | 不显式建 self-loop，把拥堵传播到相邻出边；目标后等待不累加 | updater 单元测试覆盖 |
| guidance 接入 | 替换 PIBT evaluation distance、root priority、push-and-swap 等距离估计 | 只改排序/代价，不删候选动作 |
| anytime loop | `LaCAM* run -> collect history -> UpdateLTM -> SelectRestartNode` | LTM 先复现，NTM 再替代 update 或 residual |
| one-shot 设置 | 8 张 grid map，每图 25 random instances，30s | final 复现按此执行；早期 smoke 可缩小 |
| planning-and-execution | `E={0.1s,0.5s}`，`X={5,10,20}` | 主实验第二部分 |
| baselines | LaCAM*、LaCAM*+TO、LaCAM*+SUO；P&E 对 PIE | 本项目加入 LaCAM*+NTM |

## 必须保留的 LaCAM* 语义不变量

| 不变量 | 必须保持 | 验证方式 |
|---|---|---|
| high-level search | 不改变 OPEN/EXPLORED、rewrite、parent pointer、incumbent pruning 的基本语义 | fallback trace diff 或 output-level parity |
| low-level domain | 每个 agent 候选动作仍为 `neigh(v) union {v}` | tiny graph exhaustive candidate test |
| PIBT 冲突语义 | vertex conflict、edge swap conflict、priority inheritance/backtracking 不被绕开 | 小图单元测试 + random smoke |
| guidance 边界 | LTM/NTM 只能影响 ranking、distance、priority bias | 代码审计，禁止删除合法 child |
| fallback 等价 | 关闭 LTM/NTM 后退回 LaCAM* 原始行为 | `--no-ltm` / `--no-ntm` parity |
| first solution | 不明显拖慢快速可行解能力 | TTFS、success@30s、首解 trace |
| anytime 行为 | post-first-solution 改善曲线不被 guidance overhead 吞掉 | equal-wallclock 与 equal-node 双评估 |
| 可复现性 | 实验必须可定位 commit/config/seed/map/binary/env | JSONL metadata + Markdown 报告 |

## 工程结构

建议目录如下。上游 LaCAM* 保持 clean mirror 或 submodule，项目新增逻辑尽量放在 adapter 和独立模块中。

| 路径 | 用途 |
|---|---|
| `external/lacam_star` | LaCAM* 上游底座，记录 exact commit |
| `cpp/ltm` | LTM 数据结构、更新器、restart policy、LaCAM* adapter |
| `cpp/ntm` | NTM 推理接口和轻量 runtime |
| `src/czr004_metrics` | 统一 SoL、ratio、AUC、coverage、统计检验 |
| `src/repro` | LTM 论文复现实验入口 |
| `src/data` | benchmark 索引、teacher dataset、manifest |
| `src/models` | MLP/CNN/GNN traffic map 模型 |
| `src/train` | 训练脚本和 loss |
| `src/eval` | 批量评测、统计检验、图表 |
| `configs/ltm` | LTM 复现配置 |
| `configs/ntm` | NTM 模型、训练、推理配置 |
| `scripts` | 环境检查、一键 smoke、复现脚本 |
| `docs` | 设计决策、Codex worklog、实现说明 |
| `outputs/reports` | 每次实验和阶段报告 |
| `outputs/tables` | 汇总 CSV |
| `outputs/figures` | 可提交图表 |
| `outputs/logs` | 原始日志，默认不提交大文件 |
| `artifacts/teacher` | LTM teacher labels，默认不提交大文件 |
| `artifacts/models` | 训练模型，默认不提交大文件 |

## Git 管理规范

`C:\PROGRAMING\czr004` 已初始化为 git 仓库。后续必须保持提交粒度清晰。

推荐分支：

| 分支 | 用途 |
|---|---|
| `main` | 始终可构建、文档齐全、阶段成果稳定 |
| `phase0-project-hygiene` | git、环境、目录、baseline 获取 |
| `phase1-ltm-reimpl` | LaCAM*+LTM paper-faithful reimplementation |
| `phase1a-ltm-paper-parity` | LTM 论文级定量复现与结果对齐 |
| `phase2-metrics-harness` | 统一指标和日志，把 Phase1a 临时复现口径固化为长期管线 |
| `phase3-ntm-data` | teacher dataset、trace schema、训练样本 |
| `phase4-ntm-lite` | MLP/CNN/GNN traffic map |
| `phase5-solver-integration` | NTM 接入 LaCAM* guidance 层 |
| `phase6-paper-eval` | 主实验、统计、图表、论文级收尾 |

commit 前缀：

| 前缀 | 用途 |
|---|---|
| `docs:` | 指南、报告、README、worklog |
| `deps:` | conda、submodule、第三方依赖 |
| `build:` | CMake、Ninja、CI、构建脚本 |
| `baseline:` | LaCAM* 原始基线 |
| `ltm:` | 规则 LTM 复现 |
| `trace:` | PIBT history、日志、metadata |
| `metrics:` | SoL、AUC、coverage、统计检验 |
| `model:` | NTM/GNN/MLP/CNN |
| `eval:` | benchmark、表格、图 |
| `test:` | 单元测试、语义测试、smoke |
| `fix:` | bug fix |

禁止把大规模原始日志、build 目录、checkpoint、大 teacher labels 直接提交进 git。必要时提交摘要 CSV、图表和 Markdown 报告，并在报告中写明原始文件路径和生成命令。

## Markdown 研究纪律

Codex 每次写代码、改实验、跑重要命令，都必须同步写 Markdown。强制规则：

- 没有 `docs/codex-worklog.md` 条目，不开始写 solver 代码。
- 没有 `outputs/reports/exp_*.md`，不承认任何实验结论。
- 没有记录 commit/config/seed/map/agents/time limit，不进入主表。
- 发现语义 bug 时先写 `outputs/reports/bug_*.md`，再修代码；修完追加验证结果。
- 所有 phase 结束必须有 `outputs/reports/phase*_*.md`。

每次 Codex worklog 至少包含：

```markdown
## YYYY-MM-DD HH:MM - short title

- Request:
- Files changed:
- Commands run:
- Key observations:
- Tests / validation:
- Follow-up:
```

实验报告模板：

```markdown
# exp_YYYYMMDD_HHMM_name

## Question
本次实验回答什么问题？

## Code State
- commit:
- branch:
- dirty files:

## Config
- method:
- map/scen:
- agents:
- seeds:
- time limit:
- threads:
- hardware:

## Results
表格或关键数值。

## Interpretation
结论、失败模式、是否进入下一步。

## Repro Command
完整命令。
```

## 指标锁定

所有脚本、报告和图表必须共用同一个 metrics 实现，不允许每个脚本各写一遍。

```text
SoL(solution) = sum_t count(agent_i not at goal at time t)
lower_bound_sol = sum_i shortest_path_distance(start_i, goal_i)
sum_of_loss_ratio = SoL(solution) / lower_bound_sol
```

主指标：

| 指标 | 方向 | 用途 |
|---|---|---|
| `sum_of_loss_ratio` | 越低越好 | LTM 论文主指标 |
| `success_rate@30s` | 越高越好 | 防止质量高但经常无解 |
| `time_to_first_solution` | 越低越好 | 检查是否破坏 LaCAM* 快速首解 |
| `returned_solutions_count@30s` | 越高通常越好 | 对齐 anytime coverage 行为 |
| `quality_time_auc` | 若定义为 ratio 积分则越低越好 | 量化 30s 内整体曲线 |
| `planning_overhead_ms` | 越低越好 | 检查 LTM/NTM 附加成本 |
| `edge_weight_mae` | 越低越好 | 仅作为模型诊断，不作为最终 solver 指标 |
| `action_ranking_delta` | 视定义而定 | 诊断 NTM 是否改变了有意义的候选排序 |
| `expanded_nodes` | 越少通常越好 | 支撑 equal-node 与搜索努力分析 |
| `high_level_expansions` | 越少通常越好 | 区分 guidance 收益和“多搜了节点” |
| `low_level_pibt_calls` | 越少通常越好 | 诊断 PIBT 侧开销 |
| `ntm_inference_count` | 越少通常越好 | 诊断在线推理频率 |

模型离线误差不是主结论。最终只看 solver-level 指标。

## 创新叙事约束

NTM 的学术贡献不能只写成“用神经网络拟合 LTM 权重”。纯 edge-weight regression 可以作为稳定预训练，但不能作为最终主故事。最终方法必须至少包含以下一种 solver-facing 机制：

| 机制 | 作用 | 是否主推 |
|---|---|---|
| online residual | 学习 `w_ntm = clamp(w_ltm + delta, 0, 10)`，让模型修正而不是替代 LTM | 主推 |
| ranking supervision | 直接优化 PIBT 候选动作排序或 pairwise preference | 主推备选 |
| safety head | 预测何时关闭 NTM guidance，回退到 LTM 或 LaCAM* | 必做安全增强 |
| pure edge regression | 拟合 LTM normalized edge weights | 只作预训练和诊断 |

实验报告必须明确区分“teacher fitting 指标”和“closed-loop solver 指标”。如果 offline MAE 下降但 SoL ratio、AUC、TTFS 没有改善，不能称为算法收益。

## Phase4-6 备选路线隔离说明

2026-05-26 08:50 +08:00，用户提供了网页端 GPTPro 生成的两条 Phase4-Phase6 备选技术路线。GPTPro 原文未单独注明真实生成时刻，只包含“已思考 10m 19s”；因此本项目暂按本次归档时间记录来源时间，后续若获得原始生成时间再更新。

这两条路线只作为备选，不替换当前主线，也不与当前 Phase4-Phase6 主路线混写。完整辅助总纲见：

- `docs/phase4_6_gptpro_alternatives_20260526_0850.md`

备选 1：`CBR-LTM`，即 Counterfactual Bottleneck Residual LTM。核心是用 short closed-loop probes 生成 counterfactual residual / ranking / safety 标签，在 LTM 边权基础上学习 `w_cbr = clamp(w_ltm + gate * delta, 0, 10)`，优先作为 Phase4 的可交付主备选。

备选 2：`LAUR-LTM`，即 Learned Adaptive Update-and-Restart LTM。核心是学习 LTM 的 online update rule 与 restart-node scoring，输出 commit / block / wait gain、decay、local saturation、contraflow penalty、spillover radius、restart score 与 safety gate，作为创新性更强但风险更高的第二备选。

后续决策更新：2026-05-26 09:56 +08:00，用户明确希望优先推进 LAUR 方向。当前采用 **LAU-first** 执行原则：Phase4/Phase5 先实现 `LAU-LTM = Learned Adaptive Update LTM`，只学习 LTM online `UpdateLTM` rule，restart 仍保持 root restart；Full `LAUR-LTM` learned restart 仅在 LAU 通过 gate 后作为 optional extension。可执行计划入口：

- `phase4_6_laur_ltm_codex_execution_plan.md`

该执行计划已补充 Codex 可执行性评估和前置接口对齐附录。进入 Phase4B 前必须先按该计划钉死 force-additive parity 两级口径、checkpoint 字段来源表、trace wait 语义、独立 record/probe tool 边界、pilot 级 Phase4 learned-runtime gate。

后续决策更新：2026-05-27 +08:00，Phase5C 已经完成 `Repair3 MLP -> C++ runtime -> closed-loop smoke/ablation` 的工程闭环。结论是：MLP learned runtime 可以安全执行、保持 success、记录 TTFS 和 LAU overhead，但在 Phase5C smoke 中没有稳定优于普通 LTM 的 ratio / expanded-node 证据。因此，后续不应把 MLP 当成最终科学模型继续硬推，而应把它保留为 runtime / fallback / parity baseline。

新的可尝试路线记录为：

- `phase4f5p5_stable_attention_lau_ltm_plan.md`

该路线属于 **LAU-first 主线内部的高级 update-rule 模型修复**，不是方向切换。它采用 `Phase4F.4 / Phase5.5-update` 定位：

```text
Phase4F.4:
  historical first attempt: redo advanced LAU update-rule models with Repair3 stable targets
  current Repair5 update: regenerate attention-native LAUR labels and anti-escape gates

Phase5.5-update:
  only if offline gate and anti-escape gates pass, export and integrate the advanced update model
```

该路线被允许尝试的原因：

- 它仍然预测 LTM `UpdateLTM` rule / update parameters，不预测 agent action。
- 它不替换 PIBT、不替换 LaCAM*、不改变候选动作域和冲突语义。
- 历史 stable-attention 版本沿用 Repair3 stable target / tie-aware label，避免重复 Repair2 的 unstable hard-label 问题；2026-05-27 Repair5 更新后，Repair3 stable target 只保留为 conservative baseline / compatibility metric，不再作为高级 attention 模型的 primary label。
- 它保留 Phase5C MLP runtime 作为可回退 baseline。
- 它要求 advanced model 先过 offline gate 和 anti-escape gate，再进入 runtime；不得先接 solver 再找理由。

补充决策更新：2026-05-27 +08:00，用户提供 GPTPro `phase4f_repair5_attention_native_labels_codex_plan.md`，本总纲采纳其核心判断：Repair3 不是被否定，而是从“高级模型训练目标”降级为历史通过证据、conservative runtime baseline 和 fallback reference。Repair3 的 offline pass 主要来自 stable target / tie handling，且 tie policy 明显偏向 `additive_ltm`；Phase5C 也未证明 Repair3 MLP runtime 稳定优于普通 LTM。因此继续在 Repair3 label 上堆 Transformer，风险是学到更复杂的“回 additive 最稳”分类器，而不是更强的 learned UpdateLTM policy。

Repair5 的新主线是 `attention_native_label_v1`：

- 从 probe outcomes / rule utility / pairwise dominance / high-margin opportunity 重新生成 LAUR label。
- 训练目标从单一 hard stable target 改为 per-rule risk-adjusted utility、pairwise rule dominance、per-rule harmful、non-additive opportunity、explicit `defer_ltm`、high-margin safe-opportunity slices 和 anti-escape masks。
- `defer_ltm` 是非 executable meta-decision，runtime 映射到 `additive_ltm`，但 eval 必须单独统计，不能计为 non-additive learning success。
- Repair5 仍只学习 LTM `UpdateLTM` rule / update policy，不预测 agent action，不替换 PIBT / LaCAM*，不改 candidate domain、conflict semantics、incumbent pruning 或 learned restart。
- Phase5.5-update 只能在 original Phase4F gates、attention-native gates、safety gates、anti-escape gates 和多 seed evidence 全部通过后进入 parity/smoke；即使进入 Phase5.5，也不能直接声称 Phase6-scale learned-benefit。

Repair5 新增 anti-escape 验收必须报告并约束：

```text
validation high-margin opportunity count >= 50
high-margin non-additive capture rate >= 0.40
avoidable additive/defer rate <= 0.60
anti-escape mean selected-vs-additive delta >= 0.005
opportunity non-additive selection rate >= 0.35
global additive/defer rate <= 0.70
```

如果 original Phase4F gate 通过但 anti-escape fail，结论必须写成 `model still escapes to LTM/additive`，不得进入 Phase5.5 runtime。

推荐命名：

```text
umbrella: LAU-StableAttention-v1
primary:  LAU-SetRuleTransformer-v1
secondary: LAU-EdgeTraceTransformer-v3
optional: LAU-TopoBiasAttention-v1
```

其中 `LAU-SetRuleTransformer-v1` 是第一优先级，因为它比 aggregate MLP 更能表达 traffic edge set / rule-conditioned interaction，同时仍比 full trace Transformer 更容易导出到轻量 runtime。`LAU-EdgeTraceTransformer-v3` 只能在 tokenization 和 runtime export 成本可控时升级为候选。

该路线与 Full `LAUR-LTM` learned restart 的关系：

- stable-attention update route 排在 learned restart 之前。
- learned restart 仍是 optional extension，只能在 learned update 本身稳定后再做。
- 如果 stable-attention offline 或 closed-loop 仍失败，应回到 probe label、rule set、trace representation 或 map split 诊断，不能用 learned restart 掩盖 update-rule 模型失败。

## 相关工作定位

最终论文或报告需要把本项目放在“learning-enhanced MAPF guidance”这一窄切口里，而不是泛泛声称学习规划。至少要讨论：

- LTM：直接上游，本项目研究 learned update / residual 是否优于手工累计。
- Local guidance for LaCAM 类工作：同属 guidance，但常是局部时空 cue；本项目强调来自 PIBT trace 的 directed traffic map。
- Online Guidance Graph Optimization / guidance graph 类工作：同样学习 guidance，但任务闭环和目标通常偏 lifelong 或图优化；本项目绑定 one-shot / planning-and-execution 的 LaCAM* anytime loop。
- 学习启发式或边代价的其他搜索框架：相关但集成点不同，本项目不改 high-level search 和 PIBT 冲突语义。

这些工作不需要全部进入主实验表，但至少要在 related-work notes 和最终报告中解释问题差异，避免被误读为“又一个学 guidance 的泛化版本”。

## 阶段路线

### Phase0：项目卫生与环境

目标：让项目进入可追踪、可运行、可回退状态。

必须完成：

- git 已初始化。
- 建立 `.gitignore`。
- 导出并提交 `environment.yml`。
- 写 `docs/codex-worklog.md` 第一条。
- 写 `outputs/reports/phase0_startup_plan.md`。
- 检查 `czr004` conda 环境。
- 记录当前 PDF 核实结论，尤其是 LaCAM* 基座、baseline 口径、`[0,10]` 边权范围。

Gate：不看性能，只看环境和记录是否规范。

### Phase1：LaCAM*+LTM 结构复现

目标：按论文结构搭起 `LaCAM*+LTM` 的可运行结构，作为后续论文级定量复现、NTM teacher 和强 baseline 的工程基座。

必须实现：

- LaCAM* 基线获取和 smoke。
- `DirectedTrafficMap`，支持 directed edge weights、raw counts、`[0,10]` normalization。
- PIBT committed / blocked trace collector。
- wait action propagation 和 goal-wait ignore。
- weighted shortest-path distance 接口。
- frequent restart loop。
- 第一轮不加 node budget，第二轮起 `10 * current makespan`。
- LTM 实现偏差记录在 `docs/implementation-notes.md`。

Phase1 gate：

- structural gate：loop 可运行、边权会随 history 更新、fallback 不坏、指标同口径。
- lightweight quantitative smoke：在至少一个小型 benchmark smoke 和一个论文代表性图族小样本上，`LaCAM*+LTM` 不明显弱于 `LaCAM*`；若无法对齐，必须在 `docs/implementation-notes.md` 说明偏差原因。

Phase1 只验收结构正确和可运行，不再把完整论文级定量复现混在本阶段里。完整论文级结果对齐放入 Phase1a，并作为 Phase2 的前置 gate。

### Phase1a：LTM 论文级定量复现

目标：在进入 Phase2 统一 metrics harness 前，先完成与 LTM 论文设置对齐的完整定量复现，确认本地 `LaCAM*+LTM` 的结果趋势和论文主结论一致。

必须完成：

- 复核 LTM 论文 one-shot MAPF 实验设置，写入 `outputs/reports/phase1a_ltm_paper_parity_plan.md`。
- 执行细则以 `outputs/reports/phase1a_execution_checklist.md` 为准；若清单、总纲和 PDF 冲突，先按 PDF 和清单核实后更新文档。
- 明确实验地图、agent 数、instance 数、随机种子、time limit、objective 和硬件环境。
- 按论文 one-shot 设置生成或整理 8 张 grid maps、每图 25 random instances、30s setting 的实验入口；若本地素材缺失，先记录来源、缺口和补齐方式。
- 至少跑通 `LaCAM*` 与本项目 `LaCAM*+LTM` 两列；`LaCAM*+TO`、`LaCAM*+SUO` 仅在能获得原实现或可审计复现时纳入，否则必须在报告中标明 unavailable / not reproduced，不能用自造替代品冒充论文 baseline。
- 统计 LTM 论文主指标 `sum_of_loss_ratio`，同时记录 success、runtime、returned solution count、node/loop count，以及必要的随机种子和 commit。
- 输出原始 JSONL/CSV、汇总表格和复现实验报告：`outputs/reports/phase1a_ltm_paper_parity_report.md`。
- 若论文只给曲线而无 CSV，报告中用趋势、置信区间和相对排序作为验收，不伪造精确数值。
- 若 `LaCAM*+LTM` 不能达到论文同向趋势，先记录偏差诊断，再决定是修正 Phase1 实现还是降低复现声明强度。

Phase1a gate：

- paper setting 可复现：所有命令、commit、config、seed、map、agent 数、time limit 可追踪。
- result table 可解释：至少能回答 `LaCAM*+LTM` 相对 `LaCAM*` 是否复现论文主趋势。
- implementation deviations 已写入 `docs/implementation-notes.md`。
- 不完成 Phase1a，不进入 Phase2；除非用户明确暂停论文级复现并在 worklog 中记录原因。

### Phase2：统一 metrics harness

目标：在 Phase1a 已经完成论文级 LTM 定量对齐后，把复现实验中用到的指标、日志和统计脚本固化为可长期复用的统一管线，再谈 NTM 算法收益。

必须实现：

- SoL、lower bound、SoL ratio 单元测试。
- incumbent log parser。
- anytime AUC。
- returned solutions count。
- planning-and-execution metrics。
- expanded nodes / high-level expansions / low-level PIBT calls。
- paired statistical tests。
- JSONL metadata schema。

Gate：所有 baseline 和 NTM 使用同一统计代码。

### Phase3：teacher 数据与 NTM 问题定义

目标：把 NTM 的学习目标定义清楚，避免模型学到伪标签或泄漏。

必须输出：

- `artifacts/teacher/manifest.jsonl`
- edge-level teacher labels
- PIBT trace schema
- map/seed split 规则
- `outputs/reports/phase3_teacher_data_report.md`

候选监督目标：

- regression：预测 LTM normalized edge weight。
- residual：预测 `w_ntm = clamp(w_ltm + delta, 0, 10)`。
- ranking：预测候选动作相对排序改善。
- safety：预测何时不应该启用 NTM guidance。

Phase3 必须二选一确定主监督路线：

- 首选：online residual，以 LTM 为安全基线，学习闭环修正量。
- 备选：ranking supervision，以 solver 候选排序为直接学习目标。

pure edge regression 只作为 warm start，不作为最终主方法。Gate：teacher 数据可复现，训练/验证/测试 split 无泄漏，并且主监督路线已经写入 `outputs/reports/phase3_teacher_data_report.md`。

### Phase4：NTM-Lite 模型

目标：用轻量模型替代、平滑或修正 LTM 的手工 update。

优先顺序：

1. `MLP-Edge`：只用局部 edge features，作为最小学习基线。
2. `CNN-Map`：规则 grid 上的快速 spatial baseline。
3. `GraphSAGE-Map`：主图模型。
4. `GATv2-Map`：可选增强，不作为 Phase4 必做项。

原则：

- 第一版尽量用纯 PyTorch，不把 PyG 作为硬依赖。
- 模型输出 bounded directed edge weights 或 residual。
- 推理频率是核心设计变量：至少比较 every restart、every K restarts、first-solution-only / post-first-solution-only。
- 训练集、验证集、测试集按 map / seed 严格隔离。
- NTM 关闭后必须等价 fallback。

Gate：打平 LTM 或在 dense/bottleneck 子集有正收益即可继续，不要求平均大幅超过。

### Phase5：solver-level 集成

目标：把 NTM 接入 LaCAM* guidance 层，同时保护搜索语义。

必须比较：

- `LaCAM*`
- `LaCAM*+TO`
- `LaCAM*+SUO`
- `LaCAM*+LTM`
- `LaCAM*+NTM`
- `LaCAM*+LTM+NTM-residual`，作为优先主方法，除非 Phase3 明确放弃 residual

消融：

- LTM teacher regression only vs online residual。
- ranking supervision vs residual。
- safety head on/off。
- NTM without blocked-action features。
- NTM without wait-propagation features。
- NTM fixed after first solution。
- NTM update every restart vs every K restarts。
- NTM CPU inference vs cached inference。

Gate：fallback parity、candidate domain preserved、TTFS 不灾难性变差。

### Phase6：论文同口径主实验

目标：给出完整主表、曲线和统计检验。

实验：

- one-shot MAPF：8 张 map、每图 25 random instances、30s。
- anytime：至少复现 `random-64-64-20` 1000 agents coverage 曲线。
- planning-and-execution：`E={0.1,0.5}`，`X={5,10,20}`。
- planning-and-execution baseline：按 LTM 论文口径纳入 PIE。
- TO/SUO：若无法完整复现作者实现，必须在主表中标明 implementation status，并把缺口写入 `docs/implementation-notes.md`。
- NTM 消融：证明收益不是只来自 restart-only、随机性或指标误差。
- 泛化：至少做同图不同 seed、低密度训练高密度测试、留一图测试三类分析中的两类。

Gate：若 `LaCAM*+NTM` 与 `LaCAM*+LTM` 平均打平，但 dense/bottleneck 更好、overhead 更低、或在 planning-and-execution 更稳，也算正结果。

### Phase7：收尾与发表材料

必须交付：

- `README.md`：从零运行入口。
- `docs/implementation-notes.md`：与论文不可确认处。
- `outputs/reports/phase*_*.md`：每阶段报告。
- `outputs/reports/final_reproduction_report.md`：最终复现报告。
- `environment.yml` 和最终环境导出。
- 所有图表生成命令。

## Conda 环境

环境名固定为 `czr004`。当前机器上已有同名环境，Python 为 `3.11.15`。依赖安装曾因网络权限中断，后续需要重新执行并记录结果。

建议基础依赖：

- `cmake`
- `ninja`
- `git`
- `cxx-compiler`
- `make`
- `numpy`
- `scipy`
- `pandas`
- `matplotlib`
- `pyyaml`
- `networkx`
- `tqdm`
- `statsmodels`
- `pytest`
- `pybind11`
- PyTorch 在 Phase0 中已经改为 GPU 版官方 CUDA 12.4 pip wheels：`torch 2.5.1+cu124`、`torchvision 0.20.1+cu124`、`torchaudio 2.5.1+cu124`；`torch.cuda.is_available()` 已在 RTX 4070 Laptop GPU 上验证通过。
- C++ 基座构建使用 MSVC/Ninja；`external/lacam2` 不改源码，仅通过 `cpp/compat/lacam2_windows_compat.hpp` 做 Windows build shim。

实际安装结果以 `conda list -n czr004` 为准。

## 直接给后续 Codex 的工作要求

1. 每次开始前先看 `git status --short`。
2. 不得 revert 用户或其他 Codex 已有改动。
3. 写代码前先更新 `docs/codex-worklog.md`。
4. 跑实验前必须有对应 `outputs/reports/exp_*.md` 草稿。
5. 每个 solver patch 都要说明改了上游哪一处、为什么必须改、fallback 如何恢复。
6. 任何 LTM/NTM 结果都必须同时报告相对 baseline、相对 restart-only、相对 LTM 的 delta。
7. 若发现 LTM 机制和论文 PDF 不一致，优先写入 `docs/implementation-notes.md`，再改代码。
8. 不破坏 LaCAM* 搜索底座优先级高于短期性能提升。
9. 效果 gate 不要过严。早期以打平、稳定、可解释、低 overhead、语义正确为有效进展。
10. 不得自行加入额外求解器 baseline 或偏离 LTM 论文口径的实现计划。

## 下一步

最合理的下一步顺序：

1. 提交本次路线纠偏。
2. 补齐或重新执行 `czr004` conda 环境依赖安装。
3. 选择 LaCAM* 上游仓库，并记录 exact commit。
4. 跑最小 LaCAM* baseline smoke。
5. 建立 Phase1 结构复现所需的最小 LTM adapter。
6. 完成 Phase1：LaCAM*+LTM structural reimplementation。
7. 完成 Phase1a：LTM 论文级定量复现与结果对齐。
8. 再进入 Phase2：统一 metrics harness，把 Phase1a 的临时复现统计固化为长期管线。
9. 用 LTM 产生 teacher 数据后，再进入 NTM。

这个项目的核心品味应该是：底座单一、日志细、指标同口径、gate 不虚高、NTM 慢慢加。
## 2026-06 Repair5G AAAI-quality research policy

Core policy:
The project may target an AAAI-level paper only if the method is a learned `UpdateLTM` contribution, not merely a hand-tuned static flow-shield rule.

AAAI-level gates:

1. learned runtime selector exported and frozen
2. no LaCAM*/PIBT semantic change
3. clean learned-runtime heldout validation
4. comparison against additive LTM, scalar/C-equiv baselines, static flow-shield, and map-agent selector
5. shuffled-label and random-feature controls
6. ablations for C-channel, F-channel, flow-shield, fallback, and context features
7. time/iteration stress
8. multi-map/multi-agent analysis
9. paired bootstrap/statistical evidence
10. raw logs/manifests/hash reproducibility package
11. claim ledger mapping every paper claim to artifacts
12. limitation section covering static-vs-learned ambiguity, warehouse/no-op behavior, and parity policy

Do not:

- call static flow-shield alone an AAAI-ready learned method
- claim Phase5.5/Phase6 from diagnostic Repair5G runs
- use final IDs for tuning
- hide negative controls

## 2026-06 Repair5G.5.1 runtime selector failure update

G5.1 diagnosed the failed G5 learned runtime selector as an offline-to-runtime transfer failure, not a flow-shield representation failure. The bad G5 stump used `ltm_iterations <= 2.5` to choose an early C-equiv branch at runtime, which suppressed the flow-shield updates that had made G2/G4 strong.

Observed G5.1 status:

- `runtime_selector_integration = passed`
- `runtime_selector_smoke = failed`
- `learned_runtime_selector_performance = failed`
- `learned_runtime_fresh_holdout = blocked_not_run`
- `static_flow_shield = strong_baseline_not_learned_claim`
- `advanced_neural_network_stage = blocked_until_safe_runtime_selector_or_counterfactual_labels`
- `aaai_ready = false`

Runtime hook sanity on observed IDs 136..145 did not reproduce always-static/map-agent safe policies through the selector hook under the required smoke gate, and the policy-control reproducer still showed force-additive selector-path sensitivity. Therefore G5.1 final decision is `runtime_hook_bug_blocks_learning`. Safe selector smoke on IDs 146..165 was blocked and not run; IDs 166..205 remain reserved.

Counterfactual UpdateLTM context extraction produced observed pre-update feature rows, but true counterfactual labels were unavailable because replayable `traffic_before` / trace-event checkpoints are not exported. The next AAAI-relevant step is minimal C++ checkpoint export for causal iteration-level UpdateLTM labels before any MLP/GNN/Transformer selector work.

## 2026-06 Repair5G learning-insertion strategy for top-tier AI / MAPF venues

Repair5G has now established an important scientific fact:

```text
Goal-aware dual-channel LTM with flow-shielded cost projection is useful.
```

The current validated representation is:

```text
C-channel:
  congestion / blockage / wait-risk evidence

F-channel:
  goal-progress / successful-flow / corridor evidence

flow-shield projection:
  F does not make an edge globally cheap.
  F only reduces C-channel over-penalty on current-agent goal-progress edges.
```

This is the right representation direction. It is more promising than scalar / C-only Repair5F UpdateParams, and the repeated G2/G4 results show that flow-shielded dual-channel UpdateLTM can outperform plain additive LTM under closed-loop solver metrics.

However, Repair5G must not confuse three different levels of contribution:

```text
Level 0:
  hand-designed static flow-shield rule

Level 1:
  selector over a finite set of hand-designed UpdateLTM candidates

Level 2:
  learned bounded dual-channel UpdateLTM parameter / residual / mixture policy

Level 3:
  graph/trace neural UpdateLTM policy with explicit safety/fallback constraints
```

Only Level 2 or Level 3 can plausibly support a strong AAAI/ICLR/ICML/NeurIPS-style "learning-enhanced UpdateLTM" paper claim. Level 0 and Level 1 are valuable engineering bridges and ablations, but static flow-shield or a shallow selector over hand-tuned candidates is not, by itself, a strong learned-method contribution.

### 1. The learning insertion point

The only valid learning insertion point for the current project is:

```text
pre-update trace/context
  -> learned UpdateLTM policy
  -> bounded C/F-channel update parameters or safe candidate mixture
  -> DirectedTrafficMap update
  -> WeightedDistanceTable
  -> original LaCAM*/PIBT semantics unchanged
```

The learned component must not output:

```text
agent actions
PIBT priorities
restart nodes
heuristic h_i(v)
candidate deletions
collision outcomes
OPEN / EXPLORED / rewrite decisions
incumbent pruning decisions
```

The learned component may output:

```text
bounded alpha_cong_* parameters
bounded alpha_flow_* parameters
bounded rho_* decay parameters
bounded flow_shield_beta
bounded max_flow_shield
mixture weights over safe UpdateLTM experts
abstention / fallback to static flow-shield, C-equiv, or additive
```

This keeps the project story as:

```text
learning UpdateLTM dynamics
```

not:

```text
learning MAPF actions
```

### 2. Why selector exists

The runtime selector is not the final scientific goal. Its role is to provide a safe and auditable bridge between validated hand-designed UpdateLTM rules and learned UpdateLTM policies.

The selector is useful because it can:

```text
1. choose a validated flow-shield rule in normal cases;
2. abstain to additive or C-equiv fallback in no-op / high-risk cases;
3. expose decision logs for per-iteration auditing;
4. let the project test learning insertion without changing solver semantics;
5. provide a safety layer for later neural parameter policies.
```

But the selector is weak as a final top-tier contribution if it only chooses among a few manually designed candidate IDs. A paper whose main learned method is:

```text
if feature <= threshold:
    choose hand-coded rule A
else:
    choose hand-coded rule B
```

will likely look like engineering heuristics rather than a strong learned planning method.

Therefore the project must treat selector work as:

```text
necessary bridge,
not final method.
```

### 3. Why direct learned dual-channel parameters are more attractive to top-tier venues

A learned dual-channel parameter policy is more aligned with AAAI/ICLR/ICML/NeurIPS/ICRA expectations because it gives a clearer learning contribution:

```text
context / trace / traffic-map state
  -> learned bounded update dynamics
```

rather than:

```text
context
  -> choose one manually tuned rule
```

The top-venue-friendly method should learn **how to update the traffic map**, not merely learn which hand-coded rule name to use.

The preferred medium-term method is:

```text
Learned Bounded Dual-Channel UpdateLTM Policy
```

or:

```text
Contextual Residual Flow-Shield UpdateLTM
```

with one of the following output forms:

```text
A. bounded residual policy:
   base_params = validated static flow-shield
   model predicts small residuals:
     alpha' = clip(alpha_base + delta_alpha)
     beta'  = clip(beta_base  + delta_beta)
     max_shield' = clip(max_shield_base + delta_max)

B. safe mixture policy:
   model predicts mixture weights over safe experts:
     expert_1 = static flow-shield
     expert_2 = map-agent flow-shield
     expert_3 = additive / C-equiv fallback
   UpdateParams = convex / gated mixture of bounded safe experts

C. abstention policy:
   model predicts:
     use flow-shield
     use conservative fallback
     defer to static baseline
   with confidence/risk thresholds.
```

The preferred first AAAI-worthy version is **B + C**, not unconstrained continuous parameter prediction. It is safer and easier to validate:

```text
safe mixture over validated UpdateLTM experts
+
learned abstention / risk control
+
bounded parameter residuals only after counterfactual labels are available
```

### 4. Why unconstrained neural parameter prediction is not allowed yet

Do not jump directly to:

```text
large neural net -> arbitrary alpha/beta/rho values
```

This is not acceptable yet because:

```text
1. solver outcome is non-differentiable and noisy;
2. current full-run labels are too coarse for per-update parameter learning;
3. unconstrained parameter output can destabilize traffic-map costs;
4. it may overfit map/agent/ID artifacts;
5. it is harder to prove that benefits come from learned UpdateLTM rather than protocol drift;
6. reviewers will demand strong ablations and counterfactual evidence.
```

Before continuous parameter learning, the project must build:

```text
iteration-level context dataset
counterfactual UpdateLTM labels
oracle gap analysis
feature leakage audit
runtime feature availability audit
static / selector / random / shuffled controls
```

The learning target must be causally tied to the update context:

```text
same traffic_before + same trace_events
  apply candidate UpdateParams A -> downstream short-probe outcome A
  apply candidate UpdateParams B -> downstream short-probe outcome B
  compare A vs B
```

Do not train continuous parameter policies from final full-run outcomes alone unless the report explicitly marks that as weak, confounded, and diagnostic-only.

### 5. Top-venue taste assessment

The project should optimize for the following reviewer expectations.

#### AAAI / MAPF / heuristic-search taste

AAAI and MAPF reviewers are likely to favor:

```text
- clear algorithmic contribution;
- preservation of LaCAM*/PIBT semantics;
- strong baselines;
- ablations isolating C-channel, F-channel, flow-shield, and learning;
- clean closed-loop solver evidence;
- statistics and group-wise failure analysis;
- reproducibility and protocol clarity;
- not overclaiming from a single split or static heuristic.
```

They will be skeptical of:

```text
- static hand-tuned rules sold as learning;
- selectors that do not beat static baselines;
- action-policy style models that bypass solver semantics;
- weak or missing parity controls;
- cherry-picked maps / agents / IDs.
```

#### ICLR / ICML / NeurIPS taste

ML reviewers are likely to favor:

```text
- a real learned policy, not a hand-coded parameter table;
- generalization across heldout IDs / maps / agent counts;
- negative controls such as random features and shuffled labels;
- feature ablations;
- uncertainty / abstention / calibration;
- clear training objective and dataset construction;
- evidence that the learned component improves over strong non-learned baselines.
```

They will be skeptical of:

```text
- a decision stump over hand-designed candidate IDs as the main contribution;
- no clear learning objective;
- no learned-runtime fresh validation;
- lack of counterfactual labels;
- no comparison against static flow-shield.
```

#### ICRA / robotics-planning taste

ICRA-style planning reviewers are likely to favor:

```text
- reliability under time budgets;
- safety/fallback behavior;
- no illegal motion or collision-semantics change;
- robust anytime performance;
- interpretable failure modes;
- reproducible runtime benchmarks.
```

They will be skeptical of:

```text
- learned modules that introduce brittle behavior;
- no safety fallback;
- neural black boxes without closed-loop validation;
- failure to preserve solver guarantees / semantics.
```

### 6. Route comparison

The project should record the following route comparison as a standing decision table.

| Route | Description | Top-venue attractiveness | Current readiness | Main risk | Project decision |
|---|---|---:|---:|---|---|
| Static flow-shield | one or few fixed flow-shield rules | medium for heuristic-search, low for ML | high | looks hand-tuned | keep as strong baseline |
| Map-agent selector | table-like selector by map/agent group | medium-low | high | looks like benchmark-specific engineering | keep as baseline/fallback |
| Discrete learned selector | learned model chooses candidate ID | medium | partial | must beat static; G5 failed | use only as safe bridge |
| Safe learned-abstention selector | default flow-shield, learned fallback/abstention | medium-high | next step | may only match static | best immediate route |
| Learned mixture over safe experts | learned weights over static/map-agent/additive/C-equiv experts | high | requires runtime + labels | needs careful gates | preferred G6 route |
| Learned bounded residual parameters | learned small residuals over flow-shield parameters | high | requires counterfactual labels | overfit/instability | preferred G6/G7 route after labels |
| Graph/trace neural UpdateLTM | GNN/attention over trace/traffic graph outputs bounded UpdateLTM policy | high if well validated | not ready | data and ablation burden high | G7 only after counterfactual label quality |
| Action policy / priority policy | neural MAPF action/priority/restart | not allowed for this project | forbidden | violates project scope | reject |

### 7. Recommended stage ladder

The project should now follow this ladder.

#### Stage G5.1: safe runtime bridge and failure autopsy

Goal:

```text
explain why G5 runtime selector failed;
verify runtime hook with always-static and map-agent sanity selectors;
repair disable / force-additive policy controls;
build safe abstention selector.
```

Key rule:

```text
The safe selector defaults to validated flow-shield.
It only falls back to additive/C-equiv when risk or no-op evidence is high.
```

Do not let the selector choose weak C-equiv by default in early iterations.

#### Stage G6: learned safe mixture / residual UpdateLTM policy

Goal:

```text
move from selecting hand-coded candidates to learning bounded UpdateLTM dynamics.
```

Preferred architecture:

```text
input:
  allowed pre-update context / trace / C-F traffic summary features

encoder:
  small MLP or calibrated linear model first

output:
  mixture weights over safe experts
  optional bounded residuals over flow-shield parameters
  confidence / abstention score

fallback:
  static flow-shield
  map-agent selector
  additive / C-equiv only under high-risk abstention
```

This is the first stage that can plausibly become the main learned method in an AAAI-style paper.

#### Stage G7: advanced graph/trace neural UpdateLTM policy

Only after G6 demonstrates a real adaptive gap and counterfactual labels are reliable.

Possible architecture:

```text
edge/trace encoder:
  graph neural network or trace-attention module

inputs:
  local graph edge features
  C-channel statistics
  F-channel statistics
  trace event aggregates
  goal-progress summaries
  map topology summaries
  iteration context

outputs:
  bounded parameter residuals
  safe expert mixture weights
  abstention / fallback probability
```

Still forbidden:

```text
actions
priorities
restarts
h-values
candidate deletion
collision decisions
```

G7 is not allowed unless the project first proves:

```text
simple selector / mixture model has plateaued;
oracle gap remains;
counterfactual labels are sufficient;
runtime integration is stable;
safe fallback works.
```

#### Stage G8: formal AAAI/ICLR/ICML/NeurIPS/ICRA evidence package

Goal:

```text
turn the method into a paper-grade contribution.
```

Required artifacts:

```text
clean learned-runtime heldout validation
map/agent expansion
time/iteration stress
static-vs-learned ablation
C-only vs C+F ablation
flow-shield vs subtractive-F ablation
fallback/abstention ablation
random-feature and shuffled-label diagnostics
oracle-regret analysis
claim ledger
reproducibility manifest
paper outline
limitation report
```

### 8. Preferred final paper method

The preferred final method should not be called merely:

```text
selector
```

A stronger name is:

```text
Learned Goal-Aware Dual-Channel UpdateLTM
```

or:

```text
Contextual Flow-Shield UpdateLTM
```

The final method should consist of:

```text
1. dual-channel traffic-map state:
   C(e) congestion evidence
   F(e) goal-progress flow evidence

2. flow-shield projection:
   F shields useful goal-progress corridors from C over-penalty
   without making edges globally cheap

3. learned bounded UpdateLTM policy:
   predicts safe expert mixtures or bounded residual parameters
   from pre-update trace/context features

4. safety/fallback layer:
   confidence / OOD / no-op abstention to static flow-shield or additive/C-equiv

5. semantic preservation:
   LaCAM*/PIBT search, conflict handling, candidate generation, restart, and pruning are unchanged
```

### 9. Required claims and forbidden claims

Allowed current claim:

```text
Goal-aware flow-shielded dual-channel UpdateLTM is a validated representation-level improvement over additive LTM and scalar/C-only UpdateParams under the tested closed-loop protocols.
```

Forbidden current claim:

```text
We have an AAAI-ready learned runtime UpdateLTM method.
```

Allowed future claim only after G6/G7 gates:

```text
A learned bounded dual-channel UpdateLTM policy improves or safely matches static flow-shield while preserving solver semantics, and improves closed-loop anytime MAPF performance over plain additive LTM.
```

Forbidden permanently unless the project scope changes:

```text
The model learns MAPF actions.
The model learns PIBT priorities.
The model learns restart nodes.
The model changes LaCAM* candidate generation or pruning.
The model replaces LaCAM*/PIBT.
```

### 10. Immediate research instruction

The next research phase must not be:

```text
train a bigger neural network immediately.
```

The next research phase must be:

```text
1. complete G5.1 runtime selector autopsy;
2. verify runtime hook sanity with always-static and map-agent selectors;
3. repair force-additive / disable policy controls;
4. build safe abstention selector;
5. construct iteration-level counterfactual UpdateLTM label dataset;
6. only then move to G6 learned safe mixture / residual dual-channel parameter policy.
```

This strategy gives the project the highest chance of satisfying both:

```text
MAPF reviewer taste:
  solver semantics preserved, strong baselines, closed-loop evidence

ML top-venue taste:
  real learned update dynamics, not static hand-tuning
```

## 2026-06-09 G5.30 dataset-route strategy addendum

The following strategy note is incorporated into the project master plan as the G5.30 planning/documentation route for learned goal-aware dual-channel UpdateLTM datasets. It is a planning addendum only: it does not authorize runtime claims, Phase5.5, Phase6, AAAI-ready status, solver semantic changes, or large solver/data runs in this round.

# czr004 Strategy Note: Alternative Dataset Routes for Learned Goal-Aware Dual-Channel UpdateLTM

Date: 2026-06-09  
Project: `czr004` / `goal_aware_dual_channel_ltm`  
Purpose: Give Codex a strategy document to integrate optional dataset-generation and learning routes into the project master plan. This is not an implementation prompt for runtime claims.

## 0. Executive Summary

Recent czr004 G5.20–G5.28 work established three important facts:

1. **Candidate-space evidence is real.**  
   Goal-aware / dual-channel response-surface UpdateLTM candidates can outperform the old14/G5.18 baseline under offline oracle analysis.

2. **Manual counterfactual-teacher distillation is becoming a bottleneck.**  
   We spent many rounds building small counterfactual tables, conservative teachers, failure audits, and distillation labels. This was useful, but it is now too small, too hand-shaped, and too brittle to be the only training source.

3. **The next learning step needs a richer dataset style.**  
   Recent learning-MAPF work typically generates large trajectory/slice datasets from strong solvers or rule-based planners, then trains neural models by imitation, pretrain/fine-tune, shielding, or world-model auxiliary prediction.

Therefore, czr004 should keep the counterfactual teacher table as a **validation/calibration set**, but add a new major optional route:

```text
large-scale solver trace slice dataset
  -> learned UpdateLTM residual / dual-channel update model
  -> safety/risk/fallback head
  -> counterfactual holdout validation
```

This avoids remaining stuck in manual teacher design while preserving czr004's hard boundary:

```text
learning may update LTM guidance;
learning must not control MAPF actions, PIBT priority, LaCAM* search, candidate deletion, or solver semantics.
```

## 1. What Recent Learning-MAPF Work Does for Data

This section is a practical literature scan of 2024–2026 learning-MAPF trends. It is not exhaustive, but it covers the patterns that matter for czr004.

### 1.1 MAPF-GPT: Huge expert-solution imitation dataset

MAPF-GPT builds a foundation-style imitation model from expert MAPF solutions. The relevant pipeline is:

```text
generate many MAPF scenarios
  -> solve them with a strong solver
  -> convert solution trajectories into local observation/action pairs
  -> train a transformer with cross-entropy
```

Important data details:

- It uses POGEMA to generate maze-like and random maps.
- It reports generating 10K maze-like maps, 2.5K random maps, and 3.75M problem instances.
- It solves those with a LaCAM variant and converts individual plans into local observation/action pairs.
- It reports a 1B observation/action-pair dataset.
- It removes some duplicate observations and filters wait-at-target imbalance.

Source: MAPF-GPT, arXiv 2409.00134.  
URL: https://arxiv.org/abs/2409.00134

### 1.2 Work Smarter Not Harder: timestep graph examples + strong collision shield

This work tested large-scale imitation on EECBS-generated MAPF solutions and found that large imitation alone is not enough. The key contribution is the insight that learned local policies should be paired with CS-PIBT collision shielding.

Relevant data details:

- It splits MovingAI benchmark maps into train/test maps.
- It collects expert data by running EECBS on training maps with 20–1000 agents.
- Each timestep of each MAPF solution becomes a graph training example.
- The largest dataset has 712,751 full-graph timestep examples.
- 64 parallel EECBS solvers collected the 128-scene dataset in about 90 minutes.
- It emphasizes that CS-PIBT shielding and PIBT baselines are essential.

Source: Work Smarter Not Harder, arXiv 2409.14491.  
URL: https://arxiv.org/abs/2409.14491

### 1.3 SILLM / L-PIBT: iterative expert-improved first-action data

SILLM, accepted by ICRA 2025, uses imitation learning for lifelong MAPF. It does not merely collect one-shot expert paths. It runs a planning/improvement loop:

```text
current learnable PIBT generates short-horizon paths
  -> W-MAPF-LNS improves them
  -> collect first actions from refined paths
  -> train supervised policy
  -> repeat self-bootstrapping
```

Important data details:

- It chooses imitation because MARL exploration is hard in the huge joint action space.
- It imitates W-MAPF-LNS, an anytime search-based planner.
- It collects first actions from improved K-step paths.
- It can repeat the data-collection/training loop iteratively.
- It reports million-scale action-observation pairs per iteration and 12 iterations.
- It pairs neural policy with collision resolution and guidance.

Source: SILLM, arXiv 2410.21415, ICRA 2025.  
URL: https://arxiv.org/abs/2410.21415

### 1.4 LaGAT: pretrain on many solver trajectories, then map-wise fine-tune

LaGAT integrates a learned MAGAT-like policy into LaCAM as learned guidance. The relevant data idea is:

```text
general pretraining on generated instances
  -> expert trajectories from lacam3
  -> cross-entropy policy training
  -> target-map fine-tuning at higher densities
  -> safeguard/fallback/deadlock handling
```

Important data details:

- It uses POGEMA to generate 21K instances.
- The data mix is 80% maze-like and 20% random-obstacle environments.
- It collects expert trajectories using lacam3.
- It pretrains with cross-entropy, then map-wise fine-tunes on target maps.
- It uses safeguards because neural policies alone can deadlock or produce invalid decisions.
- It uses DAgger-like/on-demand data aggregation for failures.

Source: Graph Attention-Guided Search for Dense Multi-Agent Pathfinding, arXiv 2510.17382.  
URL: https://arxiv.org/abs/2510.17382

### 1.5 RAILGUN: centralized map-based supervised policy

RAILGUN, IROS 2025, differs from many decentralized action policies. It frames the learned policy as a map-based CNN policy rather than an agent-only policy.

Relevant data idea:

```text
collect trajectories from rule-based methods
  -> train centralized map-based policy in supervised fashion
  -> generalize across maps, task variants, and agent counts
```

Source: RAILGUN, arXiv 2503.02992, IROS 2025.  
URL: https://arxiv.org/abs/2503.02992

### 1.6 MAPF-World: temporal dynamics / future prediction

MAPF-World moves beyond reactive policies by training an action world model that predicts future states/actions and uses those predictions for decision-making.

Relevant data idea:

```text
dataset should encode temporal dynamics, not just one-step labels
world-model auxiliary labels:
  future occupancy
  future actions
  future conflicts/failures
  future congestion
```

It also introduces an automatic map generator grounded in practical layouts and reports strong data efficiency compared with larger models.

Source: MAPF-World, arXiv 2508.12087.  
URL: https://arxiv.org/abs/2508.12087

### 1.7 HMAGAT / hypergraph direction

A 2026 MAPF learning paper argues that pairwise GNN message passing is insufficient in dense MAPF and proposes hypergraph attention to capture group interactions.

Relevance to czr004:

```text
PIBT failures and congestion are often group-level motifs, not pairwise-only events.
A future UpdateLTM model may need event-hypergraph or group interaction encoders.
```

Source: Pairwise is Not Enough: Hypergraph Neural Networks for Multi-Agent Pathfinding, arXiv 2602.06733.  
URL: https://arxiv.org/abs/2602.06733

## 2. What czr004 Should Borrow and What It Must Not Borrow

### Borrow

```text
large solver-trace datasets
trajectory-to-slice conversion
pretrain then map-family/map-specific fine-tune
self-bootstrapping from model failure states
collision/fallback shields
temporal/world-model auxiliary prediction
topology-aware and event-graph state representation
heldout map-family and warehouse-specific validation
```

### Do Not Borrow

```text
learning MAPF actions
learning PIBT priority
learning candidate generation/deletion
learning h-values
learning restart/search control
replacing LaCAM*/PIBT semantics
treating learned policy as solver controller
```

czr004's unique research target remains:

```text
learned goal-aware dual-channel UpdateLTM
```

The learning target should be:

```text
traffic-map update residuals
dual-channel c/f update
risk/fallback head
safe parameter region
edge/event-level update targets
```

not:

```text
agent action logits
next move imitation
priority imitation
search control
```

## 3. Why the Current Manual Counterfactual Teacher Route Should Be Downgraded

The G5.20–G5.28 counterfactual-teacher line is not wasted. It gave us:

```text
positive candidate-space evidence
clean target semantics
exact failure audit infrastructure
safe conservative teacher
important negative distillation results
```

But as the main training-data strategy it has problems:

```text
too few context-budget labels
too much manual candidate design
too much iteration on teacher/risk semantics
too expensive to expand by hand
brittle exact-candidate imitation
warehouse safety remains hard
```

New role for counterfactual tables:

```text
validation/calibration benchmark
risk/fallback evaluation set
teacher sanity checker
small high-quality heldout suite
```

New main data source:

```text
large-scale trace slices generated by running solvers
```

## 4. Proposed New Dataset Routes for the Project Master Plan

Codex should add the following optional routes to the project master plan as selectable research paths.

---

## Route A: Solver Trace Slice Dataset for Neural UpdateLTM

### Goal

Create a large dataset from solver runs:

```text
solver checkpoint / iteration / local PIBT event / edge slice
  -> UpdateLTM residual / dual-channel update target / risk label
```

### Data generation

Run many solver configurations:

```text
LaCAM*
LaCAM* + paper LTM
LaCAM* + old14
LaCAM* + G5.22/G5.23 conservative teacher
```

Collect per checkpoint:

```text
map topology
agent positions and goals
current traffic map c/f channels
traffic before/after
PIBT committed/blocked events
exact failure audit
edge c/f snapshots
local rank margins
goal-progress / wait / nonprogress events
future local congestion/failure labels
```

### Labels

Do not use action labels. Use UpdateLTM labels:

```text
target_edge_congestion_delta
target_edge_flow_delta
target_dual_channel_update
target_residual_vs_additive_LTM
target_risk_of_candidate_induced_failure
target_should_fallback
target_safe_region
target_static_recovery_opportunity
```

### Why this helps

One solver run yields many dense samples:

```text
checkpoint samples
edge samples
event samples
failure samples
update residual samples
```

This is closer to neural learning than 120 context-budget decisions.

### Resource plan with 2×4090

```text
CPU:
  parallel solver trace collection
GPU 0:
  train edge/event UpdateLTM residual model
GPU 1:
  train risk/fallback/topology model or run batch inference
Storage:
  compressed parquet/npz/jsonl shards with SHA manifests
```

### Success criterion

```text
millions of edge/event/update slices
zero forbidden target leakage
residual model beats additive baseline on heldout map families
risk head improves candidate-induced failure prediction
counterfactual G5.23/G5.26 validation correlation is positive
```

---

## Route B: LaGAT-Style Pretrain Then Map-Family Fine-Tune for UpdateLTM

### Goal

Use LaGAT's data schedule but change the target.

LaGAT target:

```text
neural MAPF action/guidance policy
```

czr004 target:

```text
neural UpdateLTM residual / parameter region / safety head
```

### Pipeline

```text
pretrain:
  generated maze/random/warehouse-like maps
  moderate densities
  many solver trace slices

fine-tune:
  target map families:
    maze-32-32-4
    random-32-32-20
    warehouse-10-20-10-2-1
  higher densities
  exact failure audits
  conservative teacher labels
```

### Inputs

```text
map/topology encoder
traffic c/f channels
agent density
PIBT failure event features
candidate/update params
edge-local features
```

### Outputs

```text
region distribution
UpdateParams residual
edge c/f residual
risk/fallback probability
```

### Success criterion

```text
pretrained model > no-pretrain on heldout maps
map-family fine-tune improves warehouse safety
no runtime claims until offline gates pass
```

---

## Route C: Self-Bootstrapped Slice Aggregation

### Goal

Use a DAgger-like loop, inspired by SILLM and LaGAT data aggregation, but only for UpdateLTM.

### Loop

```text
1. Train provisional UpdateLTM residual/risk model.
2. Run solver offline with model in audit-only or shadow mode.
3. Collect failure / disagreement / high-risk checkpoints.
4. Ask strong solver or conservative teacher for labels.
5. Add those slices to dataset.
6. Retrain.
```

### Critical boundary

Initially run in **shadow mode**:

```text
model predicts update
solver still uses baseline update
record what model would have done
```

Only after strong offline evidence consider local smoke.

### Labels

```text
teacher residual
teacher fallback
teacher safety decision
failure correction label
```

### Success criterion

```text
model-specific failure slices improve heldout risk prediction
warehouse false positives decrease
safe-positive capture improves without increasing induced no-solution
```

---

## Route D: World-Model Auxiliary Prediction for UpdateLTM

### Goal

Use MAPF-World-style temporal prediction, but not action prediction.

### Auxiliary tasks

Given current trace/traffic/topology:

```text
predict future congestion channel
predict future flow channel
predict future blocked-event density
predict future no-solution risk
predict next-iteration exact failure reason distribution
predict future static-recovery opportunity
```

### Why

Current models struggle because the outcome of an UpdateLTM change is delayed. Predicting future traffic/failure dynamics may build a better representation.

### Model

```text
event encoder
topology encoder
traffic-map encoder
temporal transformer or GRU
edge/update decoder
risk head
```

### Success criterion

```text
future-failure prediction improves risk calibration
world-model representation improves teacher distillation
heldout warehouse safety improves
```

---

## Route E: Graph / Hypergraph Event Encoder

### Goal

Represent group interactions, not only pairwise features.

### Motivation

Dense MAPF failures often involve:

```text
multiple agents blocked by a bottleneck
priority inheritance chains
same corridor conflict group
warehouse intersection congestion
agent group wavefronts
```

### Hypergraph objects

```text
failure event hyperedge:
  agents involved in a dependency chain

bottleneck hyperedge:
  agents whose paths share a local corridor/cut

traffic hyperedge:
  edges with correlated c/f updates

goal-progress hyperedge:
  agents competing for progress through same region
```

### Outputs

```text
risk head
teacher action-class head
region head
UpdateLTM residual head
```

### Success criterion

```text
hypergraph/event encoder beats flat feature model
warehouse induced failures decrease
region/action-class accuracy improves
```

---

## Route F: Conservative Teacher as Validation, Not Main Training

### Goal

Keep the existing conservative teacher and counterfactual table but change its role.

### New role

Use it to validate:

```text
does residual model choose safe update?
does risk head predict candidate-induced failure?
does learned UpdateLTM correlate with counterfactual utility?
does model avoid warehouse unsafe updates?
```

### Do not rely on it as sole training source

Reason:

```text
too few labels
too hand-shaped
too brittle for neural learning
```

---

## 5. Proposed Near-Term Plan

Codex should add this as a selectable path to the tổng纲:

```text
G5.30 / Route-Slice:
  Build Neural UpdateLTM Slice Dataset Plan
```

This should be a planning/docs round first, not a huge solver round.

### G5.30 candidate deliverables

```text
czr004_neural_update_ltm_slice_dataset_strategy.md
docs/goal_aware_dual_channel_ltm_routes.md
outputs/reports/neural_update_ltm_slice_dataset_schema.md
scripts/plan_neural_update_ltm_slice_dataset.py
```

### G5.30 should define schemas

#### Context slice

```text
map_id
map_family
agent_count
seed
budget
iteration
solver_config
traffic_before_hash
traffic_after_hash
```

#### Edge slice

```text
from_id
to_id
topology features
c_before
f_before
c_after_additive
f_after_additive
teacher_c_after
teacher_f_after
target_c_residual
target_f_residual
```

#### Event slice

```text
agent_id
event_kind
from_id
to_id
goal_progress
wait_nonprogress
blocked_reason
rank_margin
failed_candidate_reason_histogram
```

#### Failure slice

```text
pibt_return_false_agent
failed_candidate_count
failed_reason_entropy
dependency_chain_proxy
candidate-induced risk label
```

#### Teacher / residual labels

```text
target_update_region
target_update_param_vector
target_edge_residual_vs_additive
target_flow_component
target_congestion_component
target_risk
target_fallback
```

### G5.30 should also define training routes

```text
small MLP baseline
edge CNN/UNet over grid maps
graph neural network over map graph
event DeepSets encoder
topology-event transformer
hypergraph encoder
world-model auxiliary head
```

### G5.30 should define evaluation

```text
heldout map family
heldout warehouse
heldout density
counterfactual G5.23/G5.26 validation
risk calibration
induced no-solution prediction
teacher residual MAE
solver-level offline correlation
```

## 6. Compute Plan with Two RTX 4090 GPUs

### Phase 1: data generation

Mostly CPU-bound:

```text
run solver traces with exact audit logging
write compressed shards
keep raw logs out of git
commit manifests and summaries only
```

### Phase 2: preprocessing

CPU + GPU optional:

```text
convert jsonl -> parquet/npz
build topology features
build edge/event tensors
deduplicate identical slices
```

### Phase 3: training

Use both 4090s:

```text
GPU 0:
  residual/update model

GPU 1:
  risk/fallback model or auxiliary world-model

or DDP:
  event/topology neural model
```

### Suggested scale

Start local but larger than current G5 tables:

```text
pilot:
  500-1000 solver runs
  50k-200k checkpoints/events
  1M+ edge/event slices

expanded:
  5k-20k solver runs
  10M+ edge/event slices
```

Do not commit raw data. Commit schemas, manifests, small samples, and summary statistics.

## 7. Changes to the Project Master Plan

Codex should update the master plan with these strategic points:

1. **Counterfactual teacher route remains valid but is no longer the only route.**
2. **New primary data route: solver trace slice dataset for learned UpdateLTM.**
3. **Learning target remains UpdateLTM guidance, not MAPF actions.**
4. **Adopt LaGAT/MAPF-GPT/SILLM-style data scale and pretrain/fine-tune strategy, adapted to UpdateLTM.**
5. **Use conservative teacher as validation/calibration, not only training label.**
6. **Add neural state encoders: topology, edge/event, traffic c/f, failure interaction motifs.**
7. **Add optional later offline RL/safe fine-tuning only after supervised residual/risk heads work.**
8. **Keep all runtime/Phase5.5/Phase6/AAAI claims closed until offline gates pass.**

## 8. Recommended Codex Task

Codex should not implement the full dataset yet. It should first update the project tổng纲 and route docs.

### Short Codex prompt

Continue `czr004` after the current branch head. This is a planning/documentation round, not a solver/runtime round. Update the project tổng纲 to add alternative dataset routes for `goal_aware_dual_channel_ltm`, based on recent learning-MAPF trends such as MAPF-GPT, CS-PIBT imitation, SILLM, LaGAT, RAILGUN, MAPF-World, and hypergraph MAPF models.

The key strategic change is: do not rely only on manually designed offline counterfactual candidate-teacher tables. Keep those tables as validation/calibration, but add a new primary optional route: large-scale solver trace slice dataset for neural UpdateLTM. The learning target must remain UpdateLTM residual / dual-channel c/f update / risk-fallback head, not MAPF action logits, PIBT priority, h-values, candidate deletion, restart, or search control.

Add route descriptions for: solver trace slice dataset, LaGAT-style pretrain then map-family fine-tune for UpdateLTM, self-bootstrapped slice aggregation, world-model auxiliary prediction, graph/hypergraph event encoder, and conservative teacher as validation. Include two-RTX-4090 compute plan, raw-data manifest policy, schema definitions, evaluation gates, and closed-claim guardrails. Do not modify `external/lacam2/lacam2/**`, do not open Phase5.5/Phase6/runtime/AAAI claims, and do not implement a large solver run in this round.

## 2026-06-12 - G5.39 strategic update: from selector to static-flow parameter optimization

1. Additive LTM is now only a floor baseline.
2. The main baseline ladder is:
   additive_ltm
   static_flow_shield
   best_fixed_static_goal_aware
   frozen_family_static_goal_aware
   posthoc/oracle static diagnostic only
3. G5.37 showed old selector over old candidates does not beat static baselines.
4. G5.38 rebuilt direct labels and found residual opportunity, but one global residual candidate failed blind safety.
5. Therefore the next learning target is not candidate-ID selection.
6. The next learning target is static-flow-relative UpdateParams optimization:
   learn safe residual parameters around static_flow / best static.
7. A GGO-style workflow is adopted:
   search / optimize guidance parameters first,
   identify safe regions,
   then train a model to predict/generate those parameters.
8. Runtime / Phase5.5 / Phase6 / AAAI claims remain closed.

The learned component is not allowed to claim progress by merely selecting among stale hand-written candidates. From G5.39 onward, the learning target is static-flow-relative parameter/residual generation: use real solver outcomes to discover safe UpdateParams regions around static_flow and train models to predict those bounded residual parameters under zero-regression constraints.

G5.37/G5.38 show that additive-relative success is not enough. Static_flow and best deployable static are now the
main baselines. Selector over stale candidates is insufficient. The G5.39 route is GGO-style static-flow parameter
optimization with bounded residual UpdateParams generation.
