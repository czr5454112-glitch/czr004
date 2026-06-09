# Phase1a 执行清单（交给 Codex）

Date: 2026-05-21
Project: `C:\PROGRAMING\czr004`
Branch 建议: `phase1a-ltm-paper-parity`
前置阶段: Phase0 + Phase1 已完成（见 `phase1_ltm_reimpl_report.md`）
本阶段目标: **LTM 论文 one-shot 设置的完整定量复现**，对齐论文主趋势后再进入 Phase2。

---

## 0. 一句话任务

在 LTM 论文 §6.1 one-shot 实验口径下，批量运行 `LaCAM*` 与本地 `LaCAM*+LTM`，产出可复现的 raw 日志、汇总表和 parity 报告，回答：

> 本地 paper-faithful `LaCAM*+LTM` 是否在 `sum_of_loss_ratio` 上复现论文相对 `LaCAM*` 的主结论（LTM 更低、密集场景优势更明显）？

**未完成本清单的 gate，不得开始 Phase2（统一 metrics harness）。**

---

## 1. 硬约束（必须遵守）

| 约束 | 要求 |
|------|------|
| 搜索底座 | 仅 `Kei18/lacam2` @ `61a4c40ce91ce18c06eb2fe070aa9f1951eecb8d` |
| 上游源码 | **不得修改** `external/lacam2/lacam2/**` |
| LTM 实现 | 仅改 `cpp/ltm/**` 与项目 adapter/脚本 |
| 实验入口 | **禁止**依赖上游 `main.exe -v ...`；用 `phase1_ltm_smoke` 扩展出的 batch runner 或新 `phase1a_batch` |
| baseline 口径 | 论文路线内：`LaCAM*`、`LaCAM*+LTM` 必做；`TO/SUO` 仅原实现或可审计复现，否则标 `unavailable` |
| 边权范围 | `[0, 10]`（与 PDF 一致） |
| 声明 | 无官方 LTM 源码，结果称 **paper-faithful reimplementation**，不写 official reproduction |
| 记录纪律 | 每次跑实验前写 `outputs/reports/exp_*.md` 草稿；每次改代码写 `docs/codex-worklog.md` |

---

## 2. 论文实验规格（§6.1 One-shot MAPF）

### 2.1 实验设置（从 PDF / arXiv HTML 提取）

| 项 | 论文口径 |
|----|----------|
| 问题变体 | Classic one-shot MAPF |
| 地图来源 | MAPF benchmark（Stern et al. 2019） |
| 地图数量 | **8 张** grid maps |
| 每图实例 | **25 random instances** |
| 时间限制 | **30 s / run** |
| 主指标 | **sum-of-loss ratio**（相对 trivial lower bound：各 agent 最短路径长度之和） |
| 目标函数 | Sum-of-loss（`Objective::OBJ_SUM_OF_LOSS`） |
| 对比方法 | LaCAM*、LaCAM*+TO、LaCAM*+SUO、LaCAM*+LTM |

### 2.2 八张地图（Figure 1 文件名）

Codex 第一步必须把下面 8 张 map **逐字核对**进 `phase1a_ltm_paper_parity_plan.md`（含本地文件路径）：

| # | Map 名（论文图） | 预期本地文件 |
|---|----------------|--------------|
| 1 | `empty-32-32` | `empty-32-32.map` |
| 2 | `empty-48-48` | `empty-48-48.map` |
| 3 | `random-32-32-20` | `random-32-32-20.map` |
| 4 | `maze-32-32-4` | `maze-32-32-4.map` |
| 5 | `random-64-64-20` | `random-64-64-20.map` |
| 6 | `room-64-64-8` | `room-64-64-8.map` |
| 7 | `warehouse-10-20-10-2-1` | `warehouse-10-20-10-2-1.map` |
| 8 | `warehouse-10-20-10-2-2` | `warehouse-10-20-10-2-2.map` |

地图下载: [MAPF benchmark](https://movingai.com/benchmarks/mapf.html)
本地可先检查: `external/lacam2/assets/` 仅有少量 smoke 图，**不能代替**论文八图全集。

### 2.3 Agent 数量曲线（必须先文档化再开跑）

论文写法: 每图 25 个 random instance，agent 数从少到多直至约 **2000**（Figure 1 横轴为 agent count）。

**Codex 必须在开批量实验前完成一张表** `configs/phase1a/agent_schedule.yaml`（或同等 manifest），写明每张 map 的 agent 列表。来源优先级：

1. 论文 Figure 1 各子图横轴刻度（从 PDF/图数据读取）
2. 若论文未给 CSV，参考 Okumura LaCAM* / lacam3 同 benchmark 实验脚本中的 agent 列表，并在 `implementation-notes.md` 注明 **secondary reference**
3. 绝不允许 Codex 随意挑 3 个 agent 数冒充论文复现

若 agent 表未冻结，只允许做 **dry-run**，不得写 parity 结论。

### 2.4 本阶段明确不做

| 不做项 | 放到哪 |
|--------|--------|
| Planning-and-execution（§6.2, E×X） | Phase6 或单独 Phase1b（需用户另批） |
| Figure 3 coverage（1000 agents, random-64-64-20） | Phase1a 可选扩展，非 gate 必需 |
| NTM / 训练 | Phase3 之后 |
| 统一 metrics 库重构 | Phase2（在 Phase1a 口径验证后固化） |

---

## 3. 与 Phase1 已实现的差异（必须在报告中披露）

Phase1 报告 (`phase1_ltm_reimpl_report.md`) 已记录，Phase1a 不得忽略：

| 偏差项 | Phase1 现状 | 论文期望 | Phase1a 处理 |
|--------|-------------|----------|--------------|
| Restart 策略 | 固定 **root restart** | one-shot 下“时间充足时 root 更稳”；时间受限可选近 goal 配置 | 在 parity 报告单列 **known deviation**；可选做 ablation 但不作为 gate 必需 |
| 遍历代价 | `1 + normalized_ltm_weight` | 在 LTM 加权图上最短路 | 保持一致，写入 notes |
| 第一轮 node budget | 已实现：首轮无 budget，之后 `10 * makespan` | §5.1 一致 | 批量 runner 必须暴露该逻辑 |
| TO 预计算 | 未实现 | 论文 TO 先跑 **15s** Frank-Wolfe 再 LaCAM* | TO 列 unavailable 除非接入 Chen et al. 原实现 |
| SUO 预计算 | 未实现 | 跑到 guide path 稳定 | SUO 列 unavailable 除非接入 Okumura 2024 原实现 |
| 硬件 | Windows + MSVC 本地 | 论文 Linux workstation | 报告记录 **platform delta**，不伪造 Linux 数值 |

---

## 4. 指标定义（Phase1a 临时实现即可，Phase2 再固化）

与 `deep-research-report.md` 保持一致：

```text
SoL(solution) = sum_t |{ i | agent_i 在 t 时刻未到 goal }|
lower_bound = sum_i shortest_path_distance(start_i, goal_i)
sum_of_loss_ratio = SoL(solution) / lower_bound
```

每个 run 额外记录（JSONL 字段）：

| 字段 | 说明 |
|------|------|
| `method` | `lacam_star` / `lacam_star_ltm` / `lacam_star_to` / `lacam_star_suo` |
| `map` | 地图名 |
| `scen` | scen 文件或 generated seed |
| `agents` | N |
| `seed` | 实例种子 |
| `time_limit_sec` | 30 |
| `success` | 是否在时限内得到可行解 |
| `sum_of_loss` | 整数 |
| `sum_of_loss_ratio` | float |
| `runtime_ms` | wall-clock |
| `time_to_first_solution_ms` | 若有 incumbent 日志 |
| `loop_cnt` | 来自 solver additional_info（若有） |
| `ltm_iterations` | LTM 外层 restart 次数 |
| `committed_events` / `blocked_events` | trace 规模诊断 |
| `git_commit` | 项目 + 上游 submodule |

---

## 5. 工程任务分解（按顺序执行）

### Task A — 冻结实验 manifest（文档，1 天内）

- [x] 更新 `outputs/reports/phase1a_ltm_paper_parity_plan.md`：补全 §2.2 八图路径、§2.3 agent 表、种子规则
- [x] 新建 `configs/phase1a/manifest.yaml`（或 `manifest.jsonl`）
- [x] 新建 `src/data/benchmark_index.md`：记录地图/scen 来源、缺失项、补齐命令
- [x] 在 `docs/implementation-notes.md` 增加 **Phase1a parity tolerance** 小节（见 §6）

### Task B — 批量 runner（代码）

在 **不修改上游** 前提下扩展：

- [x] 新建 `cpp/tools/phase1a_batch.cpp`（或 Python 驱动 `phase1_ltm` 库）
  - 输入: manifest 中的一行（map, scen, agents, seed, method, time_limit）
  - 输出: 单行 JSONL + 可选 solution 文件
- [x] 新建 `scripts/build_phase1a_batch.ps1`（复用 MSVC + `lacam2_windows_compat.hpp`）
- [x] 新建 `scripts/run_phase1a_batch.ps1`
  - 支持 `--dry-run`（1 map × 1 agent × 1 instance × 2 methods）
  - 支持 `--full`（8 maps × agent_schedule × 25 instances × 2 methods）

**工作目录**: 运行 solver 时 `cwd` 设为含 `assets/` 的 benchmark 根目录（或传绝对路径）。

**时间预算估算**（供计划）:
若 8 图 × ~10–15 个 agent 点 × 25 instance × 2 methods × 30s ≈ 数万秒量级，需并行或分夜跑；先在 manifest 里支持 `--map-subset` / `--agent-subset`。

### Task C — 汇总与作图（脚本）

- [x] `src/eval/phase1a_summarize.py`（或同级脚本）
  - 读 JSONL → 按 map、agents 聚合 mean/median/std
  - 输出 `outputs/tables/phase1a_ratio_by_map.csv`
  - 生成与论文 Figure 1 **同结构** 的折线图（ratio vs agents）
- [x] 不要求与论文像素级一致，但趋势方向必须可判定

### Task D — Dry-run gate（必须先过）

配置: 建议 `loop` 或 `random-32-32-10`，agents=3，1 instance，30s（或 5s smoke + 30s 正式）

| 检查 | 通过标准 |
|------|----------|
| `lacam_star` 可解 | feasible solution |
| `lacam_star_ltm` 可解 | feasible solution |
| JSONL 字段齐全 | commit/seed/map/method 非空 |
| ratio 可计算 | 有限正数 |
| 不回归 Phase0/1 | `scripts/phase0_smoke.ps1` + `scripts/phase1_ltm_smoke.ps1` 仍通过 |

### Task E — Full batch + 报告

- [ ] 跑完全部 manifest（或用户批准的子集） — 未完成；当前完成 dry-run + 30s single-point probe
- [x] 写 `outputs/reports/phase1a_ltm_paper_parity_report.md`，结构见 §7
- [x] 更新 `phase1a_ltm_paper_parity_plan.md` 状态为 `completed` 或 `partial + reason`

---

## 6. 验收标准（Parity Gate）

### 6.1 可复现性（硬性）

- [x] 报告含完整 `git commit`（项目 + `external/lacam2`）
- [x] 每条命令可一键重跑（PowerShell 脚本 + manifest 路径）
- [x] raw 数据在 `outputs/logs/phase1a/`（大文件不进 git，路径写进报告）

### 6.2 定量结论（硬性，允许“趋势对齐”）

论文主结论（§6.1.1）: **LaCAM*+LTM 的 sum-of-loss ratio 整体低于 LaCAM***，agent 越多、越密集优势越明显。

本地验收采用 **三级**（写入 `implementation-notes.md`）:

| 等级 | 条件 | 判定 |
|------|------|------|
| **Pass-A** | ≥6/8 地图上，≥70% 的 agent 点满足 `ratio(LTM) < ratio(LaCAM*)` | 可进 Phase2，声明 close paper-parity |
| **Pass-B** | 全部 8 图的中位趋势同向，但幅度偏差 >20% 或 2–3 张图逆势 | 可进 Phase2，但 NTM 论文叙事降级为“local reimplementation trend-aligned” |
| **Fail** | 多数图 LTM 不优于 LaCAM*，且无合理解释 | **不得进 Phase2**；回修 Phase1（restart、LTM update、distance、budget） |

> 70% / 20% 为项目暂定容忍度，Codex 若从 PDF 读到更精确表格可建议修订，但必须先写入 `implementation-notes.md` 再跑 full batch。

### 6.3 基线完整性（硬性）

- [ ] 报告含表格列: `LaCAM*`, `LaCAM*+LTM`, `TO status`, `SUO status`
- [ ] TO/SUO 若未跑: 必须写 `unavailable — reason: no auditable upstream integration in czr004`

---

## 7. 最终报告模板（`phase1a_ltm_paper_parity_report.md`）

```markdown
# Phase1a LTM Paper Parity Report

## Code State
- project commit:
- external/lacam2 commit:
- branch / dirty:

## Experiment Setting
- maps (8):
- agents per map:
- instances per map: 25
- time limit: 30s
- objective: sum-of-loss
- platform:

## Methods Run
| Method | Status | Notes |
| LaCAM* | done | |
| LaCAM*+LTM | done | paper-faithful reimplementation |
| LaCAM*+TO | unavailable / done | |
| LaCAM*+SUO | unavailable / done | |

## Known Deviations from Paper
- restart policy:
- platform:
- ...

## Results Summary
- 附 CSV 路径
- 附 Figure 对比图路径
- Pass-A / Pass-B / Fail 判定

## Interpretation
- 是否复现论文主趋势:
- 哪些 map/agent 区间逆势:
- 对 Phase2/NTM 的影响:

## Repro Commands
（完整命令块）
```

---

## 8. 推荐命令备忘

```powershell
# 环境
conda activate czr004

# 回归 smoke（改代码后必跑）
powershell -ExecutionPolicy Bypass -File C:\PROGRAMING\czr004\scripts\phase0_smoke.ps1
powershell -ExecutionPolicy Bypass -File C:\PROGRAMING\czr004\scripts\phase1_ltm_smoke.ps1

# 构建（示例名，按实际脚本为准）
powershell -ExecutionPolicy Bypass -File C:\PROGRAMING\czr004\scripts\build_phase1_ltm.ps1
powershell -ExecutionPolicy Bypass -File C:\PROGRAMING\czr004\scripts\build_phase1a_batch.ps1

# Dry-run（示例）
powershell -ExecutionPolicy Bypass -File C:\PROGRAMING\czr004\scripts\run_phase1a_batch.ps1 -DryRun

# GPU 检查（Phase4 前用，Phase1a 不强制）
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

---

## 9. 与后续阶段的关系

```text
Phase1   结构复现（已完成）
   ↓
Phase1a  论文 one-shot 定量对齐（本清单）  ← 当前
   ↓
Phase2   把 Phase1a 的 JSONL/指标/统计固化为长期 harness
   ↓
Phase3+  teacher / NTM / 主实验
```

**Phase6** 的 full benchmark 是 **含 NTM** 的终局实验，不是 Phase1a 的重复；Phase1a 只验证 **LTM 复现链** 可信。

---

## 10. Codex 交付物检查表（给用户验收）

- [x] `configs/phase1a/manifest.yaml` 含 8 图 + agent 表 + 25×seed 规则
- [x] `scripts/run_phase1a_batch.ps1` 可 dry-run
- [x] `outputs/logs/phase1a/*.jsonl` 存在
- [x] `outputs/tables/phase1a_ratio_by_map.csv` 存在
- [x] `outputs/figures/phase1a_*` 对比图存在
- [x] `outputs/reports/phase1a_ltm_paper_parity_report.md` 含 Pass-A/B/Fail 判定
- [x] `docs/codex-worklog.md` 有对应条目
- [x] 未修改 `external/lacam2/lacam2/**`

---

## 11. 常见失败模式（预防）

| 失败模式 | 预防 |
|----------|------|
| 只跑 2 张 smoke 图就宣称论文复现 | manifest 必须 8 图 |
| 用 `main.exe -v` 跑实验 | 用 project batch binary |
| 自写 TO/SUO 假 baseline | unavailable 列 |
| ratio 分母算错 | 单元测试对齐 `deep-research-report.md` 公式 |
| 无 seed 记录 | JSONL 必填 seed + scen |
| LTM 与 LaCAM* 用时不同 | 统一 30s wall-clock deadline |

---

*本文件为 Phase1a 执行主清单；细则以 `deep-research-report.md` §Phase1a 与 `phase1a_ltm_paper_parity_plan.md` 为准，冲突时以本清单 + 论文 PDF 为准。*
