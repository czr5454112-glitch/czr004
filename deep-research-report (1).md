# NTM for Lightweight Traffic Map 粗略项目总纲（已校正）

生成日期：2026-05-20  
项目目录：`C:\PROGRAMING\czr004`

## 校正说明

本文件替换原网页端 GPT-5.5 生成的粗略大纲。原大纲把项目路线扩展到了不属于本课题的工程化求解器比较方向，容易误导后续实施。当前项目只保留一条研究线：

```text
LaCAM* baseline
  -> LaCAM* + LTM paper-faithful reimplementation
  -> LaCAM* + NTM
```

项目目标是在 *A Lightweight Traffic Map for Efficient Anytime LaCAM\** 的方法基础上迈进一步，引入 Neural Traffic Map（NTM）。不设置额外工程化求解器作为 baseline，不把研究问题扩展成求解器工程对比。

## 项目目标

本项目先复现 LTM，再用神经网络替代、平滑或修正 LTM 中手工累计 traffic map 的更新机制。NTM 只能作为 guidance 层接入 LaCAM*，不能改变 LaCAM* 的搜索语义。

最终希望回答：

- NTM 能否在 LTM 论文同口径指标上打平或超过 LTM？
- NTM 是否能在 dense、bottleneck、long-corridor 等高拥堵场景中更稳定？
- NTM 的收益是否来自 learned traffic map 本身，而不是 restart、随机性或指标误差？
- NTM 的推理开销是否足够低，不破坏 anytime 行为？
- NTM 是否能在跨 seed、跨 agent density 或留图测试中展现比手工 LTM 更好的泛化？

## Baselines

主实验 baseline 只包含 LTM 论文同口径对象：

- `LaCAM*`
- `LaCAM*+TO`
- `LaCAM*+SUO`
- `LaCAM*+LTM`
- `LaCAM*+NTM`，本项目方法
- planning-and-execution setting 中按论文口径补充 `PIE`

## LTM 复现要点

LTM 复现必须优先遵循本地 PDF：

- 搜索底座为 LaCAM*。
- traffic map 是与原 MAPF 图同构的有向带权图。
- 默认边权范围为 `[0,10]`。
- PIBT trace 需要记录 committed actions 和 blocked actions。
- wait action 不显式建 self-loop，而是把拥堵传播到相邻出边。
- 已经到达目标后的等待不继续增加 traffic。
- weighted distance 用于 PIBT evaluation、root priority 和相关距离估计。
- one-shot 中第一轮不加 node budget；第二轮起使用 `10 * current makespan`。
- LTM 官方源码未公开，因此本项目只能称为 paper-faithful reimplementation。

## NTM 设计方向

NTM 不替代 LaCAM*，只学习 traffic guidance。可选路线：

1. `MLP-Edge`：用局部边特征预测边权或 residual，作为最小学习基线。
2. `CNN-Map`：把 grid map 特征转成张量，验证规则地图上的轻量空间模型。
3. `GraphSAGE-Map`：用图消息传递预测 directed edge weights。
4. `GATv2-Map`：用图注意力增强拥堵区域表达。

模型输出应满足：

- 输出 bounded directed edge cost 或 residual correction。
- 能关闭并回退到原始 LTM 或 LaCAM*。
- 推理频率可控，例如每次 restart 前或每 `K` 次 restart 更新一次。
- 训练、验证、测试按 map / seed 隔离，避免数据泄漏。

## 指标

所有实验必须共用同一个 metrics 实现：

```text
SoL(solution) = sum_t count(agent_i not at goal at time t)
lower_bound_sol = sum_i shortest_path_distance(start_i, goal_i)
sum_of_loss_ratio = SoL(solution) / lower_bound_sol
```

主指标：

- `sum_of_loss_ratio`
- `success_rate@30s`
- `time_to_first_solution`
- `returned_solutions_count@30s`
- `quality_time_auc`
- `planning_overhead_ms`
- planning-and-execution setting 下的 SoL ratio

离线 edge-weight 误差只作为模型诊断，不作为最终研究结论。

## 创新叙事约束

NTM 不能只做“拟合 LTM 边权”。pure edge regression 只作为预训练或诊断。主方法必须至少走一条 solver-facing 路线：

- online residual：学习 `w_ntm = clamp(w_ltm + delta, 0, 10)`，修正 LTM。
- ranking supervision：直接学习 PIBT 候选动作排序。
- safety head：预测何时关闭 NTM guidance，回退到 LTM 或 LaCAM*。

如果 offline MAE 更好但 closed-loop SoL ratio、AUC、TTFS 没有改善，不能称为算法收益。

## Git 与 Markdown 纪律

项目必须从第一天开始做好记录：

- 每次 Codex 写代码、跑实验、改配置，都要更新 `docs/codex-worklog.md`。
- 每次重要实验都要写 `outputs/reports/exp_*.md`。
- 每个 phase 结束写 `outputs/reports/phase*_*.md`。
- 每个结果必须记录 commit、config、seed、map、agent 数、time limit、硬件和命令。
- 大规模日志、teacher labels、checkpoints 默认不进 git，只提交摘要、图表和报告。

## 阶段路线

### Phase0：项目卫生

- 初始化 git。
- 固定 `czr004` conda 环境。
- 记录 PDF 中的关键口径。
- 选择并记录 LaCAM* 上游 commit。

### Phase1：LTM 结构复现

- 跑通 LaCAM* baseline。
- 实现 directed traffic map。
- 接入 PIBT trace。
- 实现 LTM update、weighted distance、restart loop。
- 完成 small smoke 和 fallback parity。
- 完成 structural gate：LTM loop 可运行、边权会更新、fallback 不坏。

### Phase1a：LTM 论文级定量复现

- 在进入 Phase2 前，先按 LTM 论文 one-shot MAPF 口径做完整定量复现。
- 执行时遵循 `outputs/reports/phase1a_execution_checklist.md`。
- 复核 8 张 grid maps、每图 25 random instances、30s setting、agent 数范围、objective 和 seed。
- 至少复现 `LaCAM*` 与 `LaCAM*+LTM` 两列；`TO/SUO` 只有在原实现或可审计复现可用时纳入。
- 输出 raw CSV/JSONL、summary table 和 `outputs/reports/phase1a_ltm_paper_parity_report.md`。
- Gate：确认 `LaCAM*+LTM` 相对 `LaCAM*` 的趋势与论文主结论一致，或明确记录偏差原因。
- 不完成 Phase1a，不进入 Phase2，除非用户明确暂停并写入 worklog。

### Phase2：指标 harness

- 在 Phase1a 结果对齐后，固化 SoL、SoL ratio、AUC、coverage。
- 增加 expanded nodes、high-level expansions、low-level PIBT calls，支持 equal-node 分析。
- 统一 JSONL metadata schema。
- 所有 baseline 与 NTM 共用同一统计代码。

### Phase3：teacher 数据

- 用 LTM 生成 edge-level teacher labels。
- 保存 trace schema 和 manifest。
- 建立 map / seed split。
- 在 online residual 和 ranking supervision 中选择一个主监督路线。

### Phase4：NTM-Lite

- 先做 MLP/CNN，再做 GraphSAGE/GATv2。
- GraphSAGE 作为主图模型；GATv2 只作为可选增强。
- 只接入 guidance，不接管搜索。
- 评估推理开销和 fallback。
- 把 every restart、every K restarts、first-solution-only / post-first-solution-only 作为推理频率消融。

### Phase5：主实验

- one-shot MAPF：8 张 grid maps，每图 25 random instances，30s。
- anytime curve：复现论文 coverage / returned-solution 行为。
- planning-and-execution：`E={0.1,0.5}`，`X={5,10,20}`。
- P&E baseline 按论文口径纳入 PIE。
- 至少做同图不同 seed、低密度训练高密度测试、留一图测试三类泛化分析中的两类。
- 消融：确认收益来自 NTM traffic guidance。

## Gate 原则

早期 gate 不要过严。有效进展包括：

- NTM 与 LTM 打平但 overhead 更低。
- NTM 平均打平，但 dense/bottleneck 子集更好。
- NTM 没有显著提升质量，但提供稳定、可解释、可回退的 traffic prediction。
- LTM 复现趋势与论文一致，即使数值不能逐点匹配。

只有在指标同口径、fallback 正常、实现无明显 bug 的前提下，若方法在多数图族稳定明显退化，才暂停该方向。
