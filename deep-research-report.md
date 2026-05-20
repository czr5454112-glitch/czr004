# NTM for Lightweight Traffic Map 项目指南

生成日期：2026-05-20  
项目目录：`C:\PROGRAMING\czr004`  
当前材料：

- `C:\PROGRAMING\czr004\2603.07891v1.pdf`：*A Lightweight Traffic Map for Efficient Anytime LaCAM\**
- `C:\PROGRAMING\czr004\deep-research-report (1).md`：网页端 GPT-5.5 生成的粗略项目总纲
- `C:\PROGRAMING\czr003\deep-research-report.md`：参考项目指南风格与管理规范

## 执行摘要

本项目的目标是：**在 LTM 论文路线之上继续前进，引入 Neural Traffic Map，简称 NTM**。项目不研究 LaCAM3，不把 LaCAM3 作为 baseline，不做 `LaCAM3+LTM`，也不做 `LaCAM3+NTM`。后续所有比较、复现和神经改进都围绕 LTM 论文同口径展开。

正确主线只有一条：

```text
LaCAM* baseline
  -> LaCAM* + LTM paper-faithful reimplementation
  -> LaCAM* + NTM
```

这里的 `LaCAM*+LTM paper-faithful reimplementation` 是为了建立 LTM teacher、指标口径和可复现实验框架；最终研究贡献是 `LaCAM*+NTM` 是否能在 LTM 同口径指标上打平或超过 `LaCAM*+LTM`，并在部分场景中带来更好的泛化、收敛或低开销表现。

本指南特别修正粗略报告里的一个方向性错误：**不存在“双底座”，也不存在 LaCAM3 迁移线**。LTM 论文的实验对象是 LaCAM* 及其 guidance 变体，论文还明确没有把 hybrid LaCAM3 放进直接比较。因此本项目不把 LaCAM3 纳入 baseline，不在 LaCAM3 上加 LTM/NTM，也不把 LaCAM3 作为项目目标。

第一步不是写 solver 代码，而是把研究路线、工程边界、指标口径、git 管理和 Markdown 记录纪律固定下来。MAPF 项目最容易失败的方式不是“模型不够复杂”，而是 baseline 口径漂移、实验日志不全、改了搜索底座却不知道改坏了什么。因此本项目把“底座保护”和“可复现记录”放在与算法同等重要的位置。

## 复审修订结论

以下修订点是后续执行的准绳。

| 修订点 | 结论 | 新要求 |
|---|---|---|
| 项目主线 | 只做 LTM -> NTM，不做 LaCAM3 线 | 删除所有 `LaCAM3+LTM/NTM` 计划 |
| baseline | baseline 不包含 LaCAM3 | 只比较 LaCAM*、LaCAM*+TO、LaCAM*+SUO、LaCAM*+LTM、LaCAM*+NTM |
| LTM 基座 | PDF 实验段写明 `LaCAM*+LTM` built on original LaCAM* codebase | 使用 LaCAM* 作为唯一搜索底座 |
| LTM 源码状态 | PDF 仓库脚注仍是占位地址 | 本项目实现称为 `paper-faithful reimplementation`，不能声称官方复现 |
| 边权范围 | PDF 方法段写实验使用 `[wLB, wUP] = [0, 10]` | 实现默认 `[0,10]`，粗略报告中的 `[1,5]` 作废 |
| gate 强度 | NTM 早期可能只在部分场景打平或改善 | gate 不要过严，早期以打平、可解释、低 overhead、语义正确为有效进展 |

## 研究问题

在 LaCAM* 的 anytime 搜索框架中，能否用神经网络学习或修正 LTM 的 traffic map 更新机制，使 solver 在相同 wall-clock 预算下获得更好的 `sum-of-loss ratio`、更快的 anytime 收敛、更稳定的 dense/bottleneck 表现，或者更低的 guidance overhead？

换句话说，本项目不问“能不能换掉 LaCAM*”，而问：

- LTM 手工累计 traffic history 是否能被更好的 learned update 替代？
- NTM 能否保持 LTM 的低开销和可回退性？
- NTM 能否在 LTM 论文同口径指标上打平或超过 LTM？
- NTM 的收益来自 traffic map 学习本身，还是仅来自 restart、随机性或指标误差？

## 主目标

- 复现 `LaCAM*+LTM`，作为 paper-faithful teacher 和强 baseline。
- 实现 `LaCAM*+NTM`，让神经网络输出 bounded directed edge costs 或 residual traffic corrections。
- 在 LTM 论文同口径指标上比较 `LaCAM*`、`LaCAM*+TO`、`LaCAM*+SUO`、`LaCAM*+LTM`、`LaCAM*+NTM`。
- 保护 LaCAM* 搜索语义：NTM 只能作为 guidance 层，不能删除合法动作，不能绕开 PIBT 冲突语义。
- 每次 Codex 写代码、改实验、跑评测，都必须同步写 Markdown 记录。

## 非目标

- 不研究 LaCAM3。
- 不把 LaCAM3 作为 baseline。
- 不做 `LaCAM3+LTM` 或 `LaCAM3+NTM`。
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
| baselines | LaCAM*、LaCAM*+TO、LaCAM*+SUO；P&E 对 PIE | 本项目加入 LaCAM*+NTM，不加入 LaCAM3 |

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
| `phase2-metrics-harness` | 统一指标和日志 |
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

模型离线误差不是主结论。最终只看 solver-level 指标。

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
- 记录当前 PDF 核实结论，尤其是 LaCAM* 基座、无 LaCAM3 baseline、`[0,10]` 边权范围。

Gate：不看性能，只看环境和记录是否规范。

### Phase1：LaCAM*+LTM 复现

目标：按论文结构复现 `LaCAM*+LTM`，作为 NTM teacher 和强 baseline。

必须实现：

- LaCAM* 基线获取和 smoke。
- `DirectedTrafficMap`，支持 directed edge weights、raw counts、`[0,10]` normalization。
- PIBT committed / blocked trace collector。
- wait action propagation 和 goal-wait ignore。
- weighted shortest-path distance 接口。
- frequent restart loop。
- 第一轮不加 node budget，第二轮起 `10 * current makespan`。
- LTM 实现偏差记录在 `docs/implementation-notes.md`。

Gate 不要求一开始超过论文曲线，只要求 loop 可运行、边权会随 history 更新、fallback 不坏、指标同口径。

### Phase2：统一 metrics harness

目标：先把指标管线做扎实，再谈算法收益。

必须实现：

- SoL、lower bound、SoL ratio 单元测试。
- incumbent log parser。
- anytime AUC。
- returned solutions count。
- planning-and-execution metrics。
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

Gate：teacher 数据可复现，训练/验证/测试 split 无泄漏。

### Phase4：NTM-Lite 模型

目标：用轻量模型替代、平滑或修正 LTM 的手工 update。

优先顺序：

1. `MLP-Edge`：只用局部 edge features，作为最小学习基线。
2. `CNN-Map`：规则 grid 上的快速 spatial baseline。
3. `GraphSAGE-Map`：稳定图模型。
4. `GATv2-Map`：增强图注意力版本。

原则：

- 第一版尽量用纯 PyTorch，不把 PyG 作为硬依赖。
- 模型输出 bounded directed edge weights 或 residual。
- 推理频率要可配置，不得明显破坏 anytime。
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
- `LaCAM*+LTM+NTM-residual`，如果 residual 路线保留

消融：

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
- NTM 消融：证明收益不是只来自 restart-only、随机性或指标误差。

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
- `pytorch` CPU 版

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
10. 不再引入 LaCAM3 线。任何 LaCAM3 相关想法都必须先问用户，不得自行加入总纲、baseline 或实现计划。

## 下一步

最合理的下一步顺序：

1. 提交本次路线纠偏。
2. 补齐或重新执行 `czr004` conda 环境依赖安装。
3. 选择 LaCAM* 上游仓库，并记录 exact commit。
4. 跑最小 LaCAM* baseline smoke。
5. 建立 metrics library 雏形。
6. 开始 LTM paper-faithful reimplementation。
7. 用 LTM 产生 teacher 数据后，再进入 NTM。

这个项目的核心品味应该是：底座单一、日志细、指标同口径、gate 不虚高、NTM 慢慢加。
