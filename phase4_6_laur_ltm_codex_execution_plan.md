# LAU/LAUR-LTM Phase4–Phase6 Codex 执行计划

生成日期：2026-05-26  
目标仓库：`https://github.com/czr5454112-glitch/czr004.git`  
正确分支：`phase1a-ltm-paper-parity`  
建议新建执行分支：`phase4-laur-ltm`  
建议落库路径：`outputs/reports/phase4_laur_ltm_plan.md` 或 `docs/phase4_6_laur_ltm_codex_plan.md`

---

## 0. 总结性决策

本计划选择 **LAUR-LTM** 方向，但第一期实现必须收敛为 **LAU-LTM**：

```text
LAU-LTM  = Learned Adaptive Update LTM
           只学习 LTM 的 online UpdateLTM rule；
           restart 仍保持当前 root restart。

LAUR-LTM = Learned Adaptive Update-and-Restart LTM
           在 LAU-LTM 通过 Phase4/Phase5 gate 后，
           再可选加入 learned SelectRestartNode。
```

第一期不直接做 Full LAUR-restart，原因很具体：

1. 当前仓库的 `OneShotLtmPlanner` 每轮结束后会销毁 search tree。
2. Phase1 报告已经记录当前 one-shot restart selection 是 root restart。
3. 若要学习 restart，需要持久化 `LtmHNode` 或至少 dump restart candidate node metadata。
4. 这会扩大 C++ 改造面，容易在 Phase4 还没有 learned update 数据前破坏 LaCAM* / LTM 语义。
5. learned update 本身已经足以解决“NTM 只是拟合 LTM edge weights”的学术贡献弱问题，因为它学习的是 `trace -> update dynamics -> downstream solver outcome`，不是学习终态边权。

因此 Codex 执行时的主路线是：

```text
Phase4:
  参数化 LTM update
  iteration-level trace/checkpoint export
  update-rule short-probe labels
  LAU-LTM light model
  offline gate

Phase5:
  LAU runtime 接入 LaCAM*+LTM guidance loop
  force-additive fallback
  closed-loop smoke / ablation

Phase6:
  LTM 论文同口径主实验
  LAU-LTM vs LaCAM*+LTM
  learned restart 仅作为 optional extension / ablation
```

---

## 1. 必须遵守的项目边界

### 1.1 主线不变

全项目仍然只沿：

```text
LaCAM*
  -> LaCAM* + LTM paper-faithful reimplementation
  -> LaCAM* + learning-enhanced LTM / NTM
```

推进。

禁止事项：

- 不引入额外 MAPF solver baseline。
- 不端到端替代 LaCAM*。
- 不重写 PIBT、high-level search、lazy constraint addition、rewrite、incumbent pruning 语义。
- 不删除合法 child。
- 不绕过 vertex conflict / edge swap conflict / priority inheritance。
- 不把 offline edge-weight MAE 当最终贡献。
- 不把 learned restart 放在 learned update 之前。

### 1.2 LAU-LTM 的唯一合法作用范围

LAU-LTM 只允许影响：

```text
PIBT trace -> UpdateLTM -> DirectedTrafficMap raw_count / normalized_weight
           -> WeightedDistanceTable
           -> 原 LTM guidance 路径
```

也就是说，第一期只替换或参数化 `UpdateLTM`，而不直接改：

```text
candidate domain
vertex / swap conflict logic
priority inheritance / backtracking
OPEN / EXPLORED / rewrite
parent pointers
incumbent pruning
```

### 1.3 Fallback 规则

必须支持三层 fallback：

```text
--laur-disable
  完全等价 LaCAM*+LTM。

--laur-force-additive
  使用新 API，但参数强制为 additive LTM；
  输出必须与旧 update_from_trace(events) 一致。

--no-ltm 或 LTM disabled
  退回 LaCAM* baseline。
```

其中 `--laur-force-additive` 是 Phase5 的核心 parity gate。没有这个 gate，不允许做 closed-loop LAU 性能声明。

---

## 2. 当前仓库状态与缺口

本计划基于 `phase1a-ltm-paper-parity` 分支，而不是默认 `main`。

### 2.1 已有可复用模块

当前可复用内容：

```text
cpp/ltm/
  DirectedTrafficMap
  PibtTraceCollector
  WeightedDistanceTable
  solve_with_ltm loop
  LTM-guided local adapter

src/czr004_metrics/
  SoL
  lower bound
  SoL ratio
  incumbent parser
  anytime AUC
  returned solutions count
  expanded_nodes
  high_level_expansions
  low_level_pibt_calls
  paired tests
  schema normalization

src/czr004_teacher/
  Phase3 edge-label schema
  teacher manifest schema
  map-holdout split audit

artifacts/teacher/manifest.jsonl
  Phase3 smoke manifest

outputs/reports/
  Phase1 / Phase1a / Phase2 / Phase3 reports
```

### 2.2 已知现状

Phase1 已实现：

```text
DirectedTrafficMap
PibtTraceCollector
WeightedDistanceTable
LTM-guided LaCAM* adapter
frequent restart wrapper
```

Phase2 已实现统一 metrics harness。

Phase3 已完成 teacher-data gate，但当前 Phase3 主要产物是：

```text
edge-label rows
manifest
PIBT trace schema definition
```

Phase3 不是 LAUR 所需的完整 iteration-level dataset。LAUR 需要的是：

```text
每轮 trace segment H_t
每轮 update 前后 W_t / W_{t+1}
每轮 solver outcome
short-probe update-rule counterfactual labels
```

### 2.3 LAUR 独有缺口

当前 LAUR 必补缺口：

| 缺口 | 当前状态 | 为什么阻塞 LAUR |
|---|---|---|
| 参数化 UpdateLTM | `increment_event` 固定 `+1.0`，`renormalize` 固定 max normalization | 无法学习 `alpha_commit / alpha_block / rho_decay / saturation` |
| raw trace 落盘 | Phase3 有 trace schema，但默认只存 derived edge labels | 无法训练 `trace -> update` |
| iteration checkpoint | 当前没有每轮 `H_t, W_t, outcome_t` | 无法构造 delayed outcome label |
| update-rule probe | 没有 candidate update rules 或 replay/probe 管线 | 无法得到 solver-facing label |
| LAUR config | 没有 `configs/phase4/laur_ltm.yaml` | Codex 无法统一参数 |
| model/train/runtime | `src/models`、`src/train`、`cpp/ntm` 当前为空或只有 `.gitkeep` | Phase4/5 尚未开始 |
| restart labels | 当前 root restart，search tree 每轮销毁 | Full LAUR-restart 暂不具备数据基础 |

---

## 3. 命名与论文叙事

### 3.1 第一主方法名

第一主方法写作：

```text
LAU-LTM: Learned Adaptive Update for Lightweight Traffic Map
```

中文：

```text
学习式自适应更新的 Lightweight Traffic Map
```

### 3.2 第二阶段扩展名

可选扩展写作：

```text
LAUR-LTM: Learned Adaptive Update-and-Restart Lightweight Traffic Map
```

但只有在 learned restart gate 通过后才在主文使用 LAUR-LTM。否则报告中写：

```text
We use LAUR-LTM as the overall research direction, but the validated method in this release is LAU-LTM, which learns the LTM update rule while keeping root restart unchanged.
```

### 3.3 学术贡献叙事

不能写：

```text
We train a neural network to predict LTM edge weights.
```

必须写：

```text
We learn how PIBT committed / blocked / wait-propagated trace events should update the directed traffic map, using delayed solver outcomes from short closed-loop probes.
```

核心创新点：

1. 学习 `UpdateLTM` 的动态规则，而不是拟合 `w_ltm`。
2. 监督信号来自 short-probe downstream solver improvement。
3. learned update 仍然输出 bounded traffic-map-compatible update parameters。
4. fallback 到 additive LTM 是精确的。
5. solver 语义不变，closed-loop 指标为最终评价。

---

## 4. Phase4 总目标

Phase4 目标不是“训练一个大模型”，而是建立完整的 LAU 数据与训练闭环：

```text
C++ parameterized UpdateLTM
  -> iteration-level checkpoint / raw trace export
  -> update-rule short probes
  -> update-label dataset
  -> LAU light model
  -> offline validation
  -> Phase4 report
```

Phase4 通过后，必须能回答：

```text
给定一轮 PIBT trace H_t 和当前 LTM 状态 W_t，
模型是否能预测哪种 update rule 在下一轮 short-budget solver probe 中更有利？
```

---

## 5. Phase4A：文档与配置骨架

### 5.1 Codex 开始前命令

```powershell
git status --short
git checkout phase1a-ltm-paper-parity
git pull origin phase1a-ltm-paper-parity
git checkout -b phase4-laur-ltm
```

若已经存在分支：

```powershell
git checkout phase4-laur-ltm
git status --short
```

### 5.2 必须先写 worklog

追加 `docs/codex-worklog.md`：

```markdown
## 2026-05-26 HH:MM - Start Phase4 LAU-LTM

- Request:
  Implement the LAU-LTM Phase4 execution package: parameterized LTM update,
  iteration checkpoints, raw trace export, update-rule probes, and model/training skeleton.
- Files planned:
  - outputs/reports/phase4_laur_ltm_plan.md
  - configs/phase4/laur_ltm.yaml
  - cpp/ltm/ltm.hpp
  - cpp/ltm/ltm.cpp
  - cpp/tools/phase4_laur_record.cpp
  - src/czr004_teacher/update_sequences.py
  - src/models/laur_ltm.py
  - src/train/train_laur_ltm.py
- Key constraints:
  Force-additive fallback must match current LTM.
  No search semantics changes.
- Follow-up:
```

### 5.3 新增配置文件

创建：

```text
configs/phase4/laur_ltm.yaml
```

建议初版内容：

```yaml
schema_version: phase4_laur_config_v1

repo:
  expected_branch: phase4-laur-ltm
  upstream_branch: phase1a-ltm-paper-parity

mode:
  primary_method_name: LAU-LTM
  full_laur_restart_enabled: false
  learned_restart_enabled: false
  force_additive_default: true

paths:
  phase1a_manifest_jsonl: configs/phase1a/manifest_plus_3000.jsonl
  phase3_manifest_jsonl: artifacts/teacher/manifest.jsonl
  checkpoints_root: artifacts/teacher/laur/checkpoints
  traces_root: artifacts/teacher/laur/traces
  probes_root: artifacts/teacher/laur/probes
  labels_root: artifacts/teacher/laur/update_labels
  model_root: artifacts/models/laur_ltm
  reports_root: outputs/reports
  tables_root: outputs/tables

record:
  sample_policy: smoke
  maps:
    train:
      - empty-32-32
      - random-32-32-20
      - random-64-64-20
      - room-64-64-8
      - warehouse-10-20-10-2-1
      - warehouse-10-20-10-2-2
    validation:
      - empty-48-48
    test:
      - maze-32-32-4
  agents: [50]
  instances: [1]
  time_limit_sec: 3
  max_iterations: 4
  export_raw_trace: true
  export_checkpoints: true
  checkpoint_topk_edges: 256
  trace_event_sample_rate: 1.0
  compress_raw_trace: false

update_params:
  lower_bound: 0.0
  upper_bound: 10.0
  alpha_commit_max: 2.0
  alpha_block_max: 2.0
  alpha_wait_max: 2.0
  rho_decay_min: 0.70
  rho_decay_max: 1.00
  saturation_scale_min: 0.50
  saturation_scale_max: 2.00
  contraflow_penalty_max: 1.00
  spillover_radius_max: 1
  phase4_enabled_params:
    alpha_commit: true
    alpha_block: true
    alpha_wait: true
    rho_decay: true
    saturation_scale: true
    contraflow_penalty: false
    spillover_radius: false

probe:
  enabled: true
  short_budget_sec: 1.0
  max_checkpoints_per_run: 8
  max_rules_per_checkpoint: 8
  min_delta_ratio_for_label: 0.005
  harmful_delta_ratio_threshold: -0.02
  harmful_ttfs_regression_ratio: 1.20
  rule_set:
    - additive_ltm
    - commit_heavy
    - block_heavy
    - block_light
    - wait_light
    - wait_heavy
    - decay_095
    - decay_090
    - saturation_low
    - saturation_high

model:
  architecture: laur_mlp_v1
  feature_set: aggregate_checkpoint_v1
  hidden_dim: 64
  num_hidden_layers: 1
  dropout: 0.0
  output_heads:
    rule_logits: true
    safety_harmful: true
    continuous_params: false
  export_format: linear_mlp_json

loss:
  lambda_rule_ce: 1.0
  lambda_safety_bce: 1.0
  lambda_delta_regression: 0.25
  lambda_ltm_regularization: 0.10
  lambda_entropy: 0.00

train:
  seed: 20260526
  batch_size: 256
  epochs: 50
  learning_rate: 0.001
  weight_decay: 0.0001
  early_stop_patience: 8
  map_holdout: true

gates:
  schema_validation_required: true
  force_additive_parity_required: true
  force_additive_ratio_abs_tol: 1.0e-9
  force_additive_weight_abs_tol: 1.0e-12
  min_validation_non_neutral_checkpoints: 50
  min_rule_top1_accuracy: 0.35
  min_rule_top3_accuracy: 0.70
  min_safety_harmful_recall: 0.80
  min_safety_harmful_precision: 0.30
  min_predicted_probe_mean_delta_ratio: 0.0

runtime:
  default_inference_mode: post_first_solution_only
  update_period_restarts: 1
  bottleneck_trigger_only: false
  max_inference_overhead_ms_per_restart: 5.0
  safety_default_to_additive: true
```

### 5.4 Phase4A gate

Phase4A gate：

```text
configs/phase4/laur_ltm.yaml exists
outputs/reports/phase4_laur_ltm_plan.md exists
docs/codex-worklog.md updated
git status shows only intended files
```

Commit：

```powershell
git add configs/phase4/laur_ltm.yaml outputs/reports/phase4_laur_ltm_plan.md docs/codex-worklog.md
git commit -m "docs: add LAU-LTM phase4 execution plan and config"
```

---

## 6. Phase4B：C++ 参数化 UpdateLTM

### 6.1 设计原则

保留当前旧接口：

```cpp
void DirectedTrafficMap::update_from_trace(const std::vector<TraceEvent>& events);
```

新增重载：

```cpp
void DirectedTrafficMap::update_from_trace(
    const std::vector<TraceEvent>& events,
    const UpdateParams& params);
```

旧接口必须内部调用：

```cpp
update_from_trace(events, UpdateParams::additive());
```

或保持原实现不变，新接口独立实现。但无论哪种方式，`UpdateParams::additive()` 必须和当前行为一致。

### 6.2 修改 `cpp/ltm/ltm.hpp`

新增结构体：

```cpp
enum class TraceEventKind {
  Committed,
  Blocked
};

enum class TracePropagationKind {
  None,
  WaitPropagated,
  GoalWaitIgnored
};

struct TraceEvent {
  TraceEventKind kind;
  uint agent_id;
  uint from_id;
  uint to_id;
  bool at_goal;

  // Phase4 LAU export fields.
  // Do not use these to change old fallback behavior unless params require it.
  TracePropagationKind propagation_kind = TracePropagationKind::None;
  uint propagated_to_id = std::numeric_limits<uint>::max();
  int blocked_reason = 0;
  int candidate_rank = -1;
};

struct UpdateParams {
  double alpha_commit = 1.0;
  double alpha_block = 1.0;
  double alpha_wait = 1.0;
  double rho_decay = 1.0;
  double saturation_scale = 1.0;
  double contraflow_penalty = 0.0;
  uint spillover_radius = 0;
  bool force_additive = false;

  static UpdateParams additive()
  {
    UpdateParams p;
    p.alpha_commit = 1.0;
    p.alpha_block = 1.0;
    p.alpha_wait = 1.0;
    p.rho_decay = 1.0;
    p.saturation_scale = 1.0;
    p.contraflow_penalty = 0.0;
    p.spillover_radius = 0;
    p.force_additive = true;
    return p;
  }
};
```

新增只读导出接口：

```cpp
std::vector<std::tuple<uint, uint, double>> raw_edges_topk(uint k) const;
std::vector<std::tuple<uint, uint, double>> normalized_edges_topk(uint k) const;
std::vector<std::tuple<uint, uint, double>> raw_edges_nonzero() const;
```

### 6.3 修改 `cpp/ltm/ltm.cpp`

新增内部函数：

```cpp
void DirectedTrafficMap::apply_decay(const UpdateParams& params)
{
  if (params.force_additive || params.rho_decay >= 1.0) return;
  for (auto& [_, count] : raw_counts_) {
    count *= std::clamp(params.rho_decay, 0.0, 1.0);
  }
}
```

参数化事件：

```cpp
void DirectedTrafficMap::increment_event(
    const TraceEvent& event,
    const UpdateParams& params)
{
  if (event.from_id == event.to_id) {
    if (event.at_goal) {
      return;
    }
    const auto* from = graph_.V[event.from_id];
    const double delta = params.force_additive ? 1.0 : params.alpha_wait;
    for (const auto* to : from->neighbor) {
      increment_edge(from->id, to->id, delta);
    }
    return;
  }

  double delta = 1.0;
  if (!params.force_additive) {
    if (event.kind == TraceEventKind::Committed) delta = params.alpha_commit;
    if (event.kind == TraceEventKind::Blocked) delta = params.alpha_block;
  }
  increment_edge(event.from_id, event.to_id, delta);

  if (!params.force_additive && params.contraflow_penalty > 0.0) {
    if (has_edge(event.to_id, event.from_id)) {
      increment_edge(event.to_id, event.from_id, params.contraflow_penalty);
    }
  }
}
```

参数化 normalization：

```cpp
void DirectedTrafficMap::renormalize(const UpdateParams& params)
{
  const auto max_count = max_raw_count();

  if (max_count <= 0.0) {
    for (auto& [edge, weight] : normalized_weights_) {
      weight = std::min(std::max(1.0, lower_bound_), upper_bound_);
    }
    return;
  }

  const double saturation = params.force_additive
      ? max_count
      : std::max(1.0e-9, max_count * std::max(0.01, params.saturation_scale));

  for (const auto& [edge, raw] : raw_counts_) {
    const auto scaled =
        lower_bound_ + std::min(raw / saturation, 1.0) * (upper_bound_ - lower_bound_);
    normalized_weights_[edge] = std::min(std::max(scaled, lower_bound_), upper_bound_);
  }
}
```

旧的 `renormalize()` 保留，并调用 additive：

```cpp
void DirectedTrafficMap::renormalize()
{
  renormalize(UpdateParams::additive());
}
```

新接口：

```cpp
void DirectedTrafficMap::update_from_trace(
    const std::vector<TraceEvent>& events,
    const UpdateParams& params)
{
  const UpdateParams effective = params.force_additive ? UpdateParams::additive() : params;
  apply_decay(effective);
  for (const auto& event : events) {
    increment_event(event, effective);
  }
  renormalize(effective);
}
```

### 6.4 必须新增单元测试

建议新增：

```text
tests/test_phase4_laur_update_params.py
```

如果 C++ 目前没有独立 gtest target，则先新增 C++ smoke binary：

```text
cpp/ltm/phase4_laur_update_smoke.cpp
scripts/build_phase4_laur_smoke.ps1
scripts/phase4_laur_update_smoke.ps1
```

测试项目：

| 测试 | 要求 |
|---|---|
| force-additive parity | 新接口 additive 与旧接口 raw/normalized 完全一致 |
| weight bound | 所有 normalized weight 在 `[0,10]` |
| commit/block alpha | committed / blocked 分别按 alpha 加权 |
| wait propagation | 非 goal wait 分发到 outgoing edges，乘 `alpha_wait` |
| goal wait ignore | goal wait 不改变 raw count |
| decay | `rho_decay < 1` 时旧 raw count 先衰减再加新事件 |
| saturation | saturation_scale 改变 normalized curve 但不越界 |
| contraflow off | Phase4 默认 off，不影响 additive parity |

### 6.5 验证命令

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_phase1_ltm.ps1
powershell -ExecutionPolicy Bypass -File scripts\phase1_ltm_smoke.ps1
powershell -ExecutionPolicy Bypass -File scripts\phase0_smoke.ps1
```

新增 smoke 后：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_phase4_laur_smoke.ps1
powershell -ExecutionPolicy Bypass -File scripts\phase4_laur_update_smoke.ps1
```

### 6.6 Phase4B gate

必须满足：

```text
旧 Phase1 LTM smoke 仍通过
Phase0 upstream smoke 仍通过
force-additive parity 通过
normalized weight bound 通过
goal wait ignore 通过
```

Commit：

```powershell
git add cpp/ltm tests scripts
git commit -m "ltm: add parameterized update rule with additive fallback"
```

---

## 7. Phase4C：iteration-level checkpoint 与 raw trace 导出

当前进入条件：

```text
branch: phase4-laur-ltm
Phase4B handoff commit: fef6956
Phase4B gate: passed
```

Phase4C 只做 LAU record smoke pipeline。不得做 learning/training，不改 `cpp/ntm`，不实现 learned restart，也不得回滚 Phase4B 已有的 `UpdateParams` / force-additive parity 代码。

### 7.1 新增 C++ 导出结构

新增文件：

```text
cpp/tools/phase4_laur_record.cpp
```

新增 target / binary：

```text
phase4_laur_record
phase4_laur_record.exe
```

若复用 `cpp/tools/phase1a_batch.cpp` 更省事，也可以在其基础上加参数，但建议新工具隔离 Phase4 逻辑，避免污染 Phase1a 主复现入口。

### 7.2 CLI 设计

新 binary：

```text
phase4_laur_record.exe
```

参数：

```text
--map <path>
--scen <path>
--agents <N>
--seed <seed>
--time-limit-sec <sec>
--max-iterations <K>
--run-id <id>
--checkpoint-jsonl <path>
--trace-jsonl <path>
--traffic-snapshot-root <path>
--checkpoint-topk-edges <K>
--export-raw-trace
--export-checkpoints
--force-additive
```

Python wrapper：

```text
scripts/run_phase4_laur_record.py
```

命令：

```powershell
& "$env:USERPROFILE\.conda\envs\czr004\python.exe" scripts\run_phase4_laur_record.py `
  --config configs\phase4\laur_ltm.yaml `
  --mode smoke `
  --overwrite
```

### 7.3 checkpoint schema

Schema 名称：

```text
phase4_laur_checkpoint_v1
```

每行一个 checkpoint，建议字段：

```json
{
  "schema_version": "phase4_laur_checkpoint_v1",
  "run_id": "string",
  "checkpoint_id": "string",
  "split": "train|validation|test",
  "map_name": "string",
  "map_path": "string",
  "scen_path": "string",
  "agents": 50,
  "seed": 20260526,
  "time_limit_sec": 3.0,
  "max_iterations": 4,

  "iteration": 0,
  "node_budget": 0,
  "elapsed_ms_before_iteration": 0.0,
  "elapsed_ms_after_iteration": 100.0,

  "solution_found_this_iteration": true,
  "sum_of_loss_this_iteration": 1234,
  "lower_bound_sol": 456,
  "sum_of_loss_ratio_this_iteration": 2.706,
  "best_sum_of_loss_before_update": 1300,
  "best_sum_of_loss_after_iteration": 1234,
  "best_ratio_before_update": 2.85,
  "best_ratio_after_iteration": 2.706,
  "improved_incumbent": true,

  "returned_solutions_count_so_far": 1,
  "expanded_nodes_this_iteration": 100,
  "high_level_expansions_this_iteration": 100,
  "low_level_pibt_calls_this_iteration": 999,

  "trace_event_count": 1305,
  "committed_count": 1000,
  "blocked_count": 305,
  "wait_event_count": 20,
  "goal_wait_ignored_count": 5,

  "traffic_before_nonzero_edges": 100,
  "traffic_before_max_raw": 12.0,
  "traffic_after_nonzero_edges": 130,
  "traffic_after_max_raw": 20.0,
  "traffic_after_max_normalized": 10.0,

  "raw_before_topk": [
    {"from_id": 1, "to_id": 2, "raw": 3.0}
  ],
  "raw_after_topk": [
    {"from_id": 1, "to_id": 2, "raw": 4.0}
  ],
  "normalized_after_topk": [
    {"from_id": 1, "to_id": 2, "weight": 5.0}
  ],

  "trace_path": "artifacts/teacher/laur/traces/<run_id>.jsonl",
  "traffic_snapshot_path": "artifacts/teacher/laur/checkpoints/<checkpoint_id>.json",

  "branch": "phase4-laur-ltm",
  "commit": "git-sha",
  "dirty": "clean|dirty"
}
```

硬性要求：

- 每个 run 必须输出 `run_id`。
- 每个 LTM iteration 必须输出 `checkpoint_id`。
- `checkpoint_id` 必须能和 raw trace rows join。
- `sum_of_loss_this_iteration` 和 `sum_of_loss_ratio_this_iteration` 在未找到解或 smoke 暂无该值时允许为 `null`。
- `raw_before_topk`、`raw_after_topk`、`normalized_after_topk` 中的 normalized weight 必须有审计，范围为 `[0, 10]`。
- `trace_path` 与 `traffic_snapshot_path` 必须指向本次 run 实际产物。

### 7.4 raw trace schema

Schema 名称：

```text
phase4_laur_trace_event_v1
```

每行一个 event。字段：

```json
{
  "schema_version": "phase4_laur_trace_event_v1",
  "run_id": "string",
  "checkpoint_id": "string",
  "iteration": 0,
  "event_index": 0,

  "kind": "committed|blocked",
  "agent_id": 0,
  "from_id": 1,
  "to_id": 2,
  "at_goal": false,

  "is_wait": false,
  "propagation_kind": "none|wait_propagated|goal_wait_ignored",
  "propagated_to_id": null,

  "blocked_reason": "unknown|occupied_next|swap_conflict|priority_inheritance_failed",
  "candidate_rank": null,

  "map_name": "string",
  "agents": 50,
  "seed": 20260526
}
```

注意：C++ 里的原始 event 仍可保持 `kind=Committed/Blocked`。`wait_propagated` 和 `goal_wait_ignored` 可以作为 `propagation_kind`，不一定要改 `TraceEventKind` 的主枚举，以降低破坏面。

硬性要求：

- `schema_version` 固定为 `phase4_laur_trace_event_v1`。
- `run_id`、`checkpoint_id`、`iteration` 必须与 checkpoint row 对齐。
- `event_index` 在同一 checkpoint 内稳定递增。
- `is_wait` 从 `from_id == to_id` 派生。
- `at_goal` 必须显式写入，供 `goal_wait_ignored_count` 审计。
- `map_name`、`agents`、`seed` 必须随 trace row 写入，便于单文件审计。

### 7.5 snapshot 存储策略

大文件默认不进 git。checkpoint JSONL 可以提交小型 smoke 摘要，但原始 trace 和 snapshot 放：

```text
artifacts/teacher/laur/traces/
artifacts/teacher/laur/checkpoints/
```

若当前 `.gitignore` 没覆盖，补充：

```gitignore
artifacts/teacher/laur/traces/
artifacts/teacher/laur/checkpoints/
artifacts/teacher/laur/probes/
artifacts/teacher/laur/update_labels/
```

提交的内容只包括：

```text
schema
manifest
summary CSV
outputs/reports/phase4_laur_trace_checkpoint_report.md
small smoke fixture if necessary
```

### 7.6 Python schema helper

新增：

```text
src/czr004_teacher/update_sequences.py
```

职责：

```python
validate_checkpoint_row(row: dict) -> None
validate_trace_event_row(row: dict) -> None
read_checkpoint_jsonl(path) -> Iterator[dict]
read_trace_jsonl(path) -> Iterator[dict]
build_checkpoint_features(checkpoint_row, trace_rows) -> dict
audit_checkpoint_trace_join(checkpoint_jsonl, trace_jsonl) -> dict
```

审计要求：

- checkpoint JSONL schema validation 0 errors。
- raw trace JSONL schema validation 0 errors。
- `trace_event_count == grouped trace rows`。
- `committed_count` / `blocked_count` 与 trace rows 一致。
- `wait_event_count` / `goal_wait_ignored_count` 与 `is_wait`、`at_goal` 一致。
- normalized weights bounded in `[0, 10]`。
- split 不泄漏；优先沿用 Phase3 split helper，若不能直接复用，必须在 helper 中明确复用规则并写进报告。

### 7.7 测试

新增：

```text
tests/test_phase4_laur_schema.py
```

测试：

```text
checkpoint required fields
trace required fields
run_id / checkpoint_id join
no map split leakage
all weights bounded
trace_event_count equals grouped trace rows
committed_count / blocked_count consistency
wait_event_count / goal_wait_ignored_count consistency
```

### 7.8 Phase4C gate

```text
1. build phase4_laur_record passed
2. 1-map 50-agent 3s max_iterations=4 smoke record passed
3. checkpoint JSONL schema validation 0 errors
4. trace JSONL schema validation 0 errors
5. checkpoint-trace join audit passed
6. trace_event_count consistency passed
7. committed/blocked/wait count consistency passed
8. split audit passed
9. old Phase1 LTM smoke still passes
10. Phase4B force-additive smoke still passes
11. outputs/reports/phase4_laur_trace_checkpoint_report.md written
```

Smoke 命令必须覆盖：

```text
build phase4_laur_record
run 1-map 50-agent 3s max_iterations=4 smoke
run Python schema audit
rerun Phase1 LTM smoke
rerun Phase4B update smoke
```

报告必须记录 exact command、branch、commit、dirty status、output paths、file sizes、schema/audit 结果和旧 smoke 回归结果。

Commit：

```powershell
git add cpp/tools scripts src/czr004_teacher tests configs outputs/reports .gitignore
git commit -m "trace: add LAU iteration checkpoints and raw trace export"
```

---

## 8. Phase4D：update-rule short-probe 标签

### 8.1 设计目标

LAU-LTM 的标签不是终态边权，而是：

```text
在 checkpoint t 上，
哪种 update rule 产生的 W_{t+1}
会让下一轮 short-budget LaCAM*+LTM outcome 更好？
```

因此必须做 LAUR 版 counterfactual probe。

### 8.2 candidate update rules

规则表写入：

```text
src/czr004_teacher/update_sequences.py
configs/phase4/laur_ltm.yaml
```

建议 rule set：

| rule_id | alpha_commit | alpha_block | alpha_wait | rho_decay | saturation_scale | contraflow_penalty | 说明 |
|---|---:|---:|---:|---:|---:|---:|---|
| additive_ltm | 1.0 | 1.0 | 1.0 | 1.00 | 1.00 | 0.0 | 当前 LTM |
| commit_heavy | 1.5 | 1.0 | 1.0 | 1.00 | 1.00 | 0.0 | 强化已通过路径 |
| block_heavy | 1.0 | 1.5 | 1.0 | 1.00 | 1.00 | 0.0 | 强化拥堵阻塞 |
| block_light | 1.0 | 0.5 | 1.0 | 1.00 | 1.00 | 0.0 | 降低 blocked 噪声 |
| wait_light | 1.0 | 1.0 | 0.5 | 1.00 | 1.00 | 0.0 | 减少 wait propagation |
| wait_heavy | 1.0 | 1.0 | 1.5 | 1.00 | 1.00 | 0.0 | 强化局部等待拥堵 |
| decay_095 | 1.0 | 1.0 | 1.0 | 0.95 | 1.00 | 0.0 | 轻微遗忘旧拥堵 |
| decay_090 | 1.0 | 1.0 | 1.0 | 0.90 | 1.00 | 0.0 | 更快遗忘旧拥堵 |
| saturation_low | 1.0 | 1.0 | 1.0 | 1.00 | 0.75 | 0.0 | 更早饱和 |
| saturation_high | 1.0 | 1.0 | 1.0 | 1.00 | 1.50 | 0.0 | 更平滑饱和 |

Phase4 初期不启用：

```text
contraflow_penalty
spillover_radius
region-level params
learned restart
```

这些进入 Phase5/Phase6 ablation 或未来扩展。

### 8.3 Probe binary / script

新增：

```text
cpp/tools/phase4_laur_probe.cpp
scripts/run_phase4_laur_probes.py
```

如果 C++ probe 过重，先用 `phase4_laur_record` 的 replay 功能加参数实现：

```text
--probe-checkpoint-jsonl <path>
--probe-rule-id <rule_id>
--probe-output-jsonl <path>
--probe-short-budget-sec <sec>
```

但更清晰的方式是独立 `phase4_laur_probe.exe`。

### 8.4 Probe 语义

对每个 checkpoint：

1. 读 `W_t` 或 checkpoint 前 traffic state。
2. 读该 iteration 的 trace segment `H_t`。
3. 对每个 candidate rule 生成 `W_{t+1}^{rule}`。
4. 用 `W_{t+1}^{rule}` recompute `WeightedDistanceTable`。
5. 从 root restart 运行下一轮 one-shot solver，short budget 固定。
6. 记录 outcome。
7. 与 `additive_ltm` outcome 比较。

由于当前 implementation 是 root restart，本 probe 不需要保留 search tree。这是 LAU-only 的关键工程降维。

### 8.5 Probe label schema

Schema 名称：

```text
phase4_laur_update_label_v1
```

每行一个 `(checkpoint, rule)` outcome：

```json
{
  "schema_version": "phase4_laur_update_label_v1",
  "run_id": "string",
  "checkpoint_id": "string",
  "probe_id": "string",
  "split": "train",
  "map_name": "random-32-32-20",
  "agents": 50,
  "seed": 20260526,
  "iteration": 2,

  "rule_id": "block_heavy",
  "rule_params": {
    "alpha_commit": 1.0,
    "alpha_block": 1.5,
    "alpha_wait": 1.0,
    "rho_decay": 1.0,
    "saturation_scale": 1.0
  },

  "probe_short_budget_sec": 1.0,
  "solution_found": true,
  "sum_of_loss": 1234,
  "lower_bound_sol": 456,
  "sum_of_loss_ratio": 2.706,
  "time_to_first_solution_ms": 123.0,
  "returned_solutions_count": 1,
  "expanded_nodes": 99,
  "high_level_expansions": 99,
  "low_level_pibt_calls": 1000,

  "additive_sum_of_loss_ratio": 2.800,
  "delta_ratio_vs_additive": 0.094,
  "improved_vs_additive": true,
  "harmful_vs_additive": false,

  "is_best_rule_for_checkpoint": true,
  "best_rule_id_for_checkpoint": "block_heavy",
  "label_confidence": 0.094,

  "branch": "phase4-laur-ltm",
  "commit": "git-sha",
  "dirty": "clean|dirty"
}
```

约定：

```text
delta_ratio_vs_additive = additive_ratio - rule_ratio
positive means better than additive LTM
```

如果 additive 或 rule 未找到解：

```text
success-aware ordering:
  solved beats unsolved
  both solved -> lower ratio wins
  both unsolved -> compare expanded_nodes / returned_solutions only as diagnostic
```

### 8.6 Best-rule label 生成

新增函数：

```python
build_best_rule_labels(probe_rows, min_delta_ratio=0.005)
```

规则：

```text
if best_delta_ratio < min_delta_ratio:
  label = neutral_additive
else:
  label = best_rule_id

harmful label:
  harmful = true if
    rule loses success compared to additive
    or delta_ratio_vs_additive < -0.02
    or TTFS > additive_TTFS * 1.20
```

对于 neutral checkpoint：

```text
可以用于 safety / no-op 训练
不要用于 rule CE 主训练，或以小权重加入
```

### 8.7 Phase4D gate

```text
probe smoke 产生 label JSONL
每个 checkpoint 至少有 additive_ltm 和 >=3 个非 additive rules
delta_ratio_vs_additive 方向正确
best_rule_id_for_checkpoint 可生成
schema validation 0 errors
```

Commit：

```powershell
git add cpp/tools scripts src/czr004_teacher tests configs outputs/reports
git commit -m "trace: add LAU update-rule probe labels"
```

---

## 9. Phase4E：训练样本构造

### 9.1 样本粒度

第一期使用 checkpoint-level 样本：

```text
one sample = one checkpoint
input      = aggregate features from W_t, H_t, topology, solver context
target     = best_update_rule_class + harmful_update labels
```

暂不做 per-edge neural update。原因：

1. 实现更稳。
2. C++ inference 更轻。
3. 标签来自 rule-class probe，而非 edge-wise perturbation。
4. 更符合“学习 update rule”的叙事。

### 9.2 输入特征表

新增：

```text
src/czr004_teacher/features_laur.py
```

特征：

| 组 | 字段 |
|---|---|
| run context | agents, free_cells, density, map_width, map_height, obstacle_ratio |
| iteration context | iteration, node_budget, elapsed_ms, time_remaining, max_iterations |
| incumbent context | has_solution_before, best_ratio_before, improved_last_iteration, returned_solutions_count_so_far |
| trace summary | committed_count, blocked_count, wait_event_count, goal_wait_ignored_count |
| trace ratios | blocked/committed, wait/committed, blocked_per_agent, committed_per_agent |
| traffic state | nonzero_edges_before, max_raw_before, mean_topk_raw_before, max_weight_before |
| traffic delta | topk_raw_delta_mean, topk_raw_delta_max, new_nonzero_edges_count |
| bottleneck proxy | topk_blocked_edge_concentration, entropy_edge_usage, local_degree_mean_topk |
| LTM behavior | current additive max_normalized_weight, weight_entropy, saturated_edge_count |
| map split | split only for audit, not model input |
| map name | not model input by default, to avoid leakage |

### 9.3 输出标签

输出：

```text
rule_class:
  additive_ltm
  commit_heavy
  block_heavy
  block_light
  wait_light
  wait_heavy
  decay_095
  decay_090
  saturation_low
  saturation_high
  neutral_additive

harmful_update:
  0/1

delta_ratio_best:
  best additive-normalized improvement

label_confidence:
  abs(best_delta_ratio)
```

### 9.4 数据 split

必须沿用 Phase3 map-holdout split：

```text
train:
  empty-32-32
  random-32-32-20
  random-64-64-20
  room-64-64-8
  warehouse-10-20-10-2-1
  warehouse-10-20-10-2-2

validation:
  empty-48-48

test:
  maze-32-32-4
```

不要随机按 row split，因为 checkpoint 同图同 seed 会泄漏。

### 9.5 数据规模路线

分三层：

| 规模 | 用途 | 建议 |
|---|---|---|
| smoke | 验 schema / probe / train loop | 8 maps × 1 instance × 50 agents × 3s × max_iter=4 |
| pilot | 验 validation 指标和 overhead | 8 maps × 5 instances × agents={50,100} × 5s |
| phase4-full | 进入 Phase5 前训练 | train maps × 10–25 instances × 多 agent counts × 5–10s |

Phase4 smoke 的 8-run 数据不足以得出模型结论，只能证明管线正确。Phase4 report 必须明确这一点。

### 9.6 样本构造命令

```powershell
& "$env:USERPROFILE\.conda\envs\czr004\python.exe" src\czr004_teacher\update_sequences.py `
  build-dataset `
  --config configs\phase4\laur_ltm.yaml `
  --checkpoint-jsonl artifacts\teacher\laur\checkpoints\phase4_laur_checkpoints_smoke.jsonl `
  --probe-jsonl artifacts\teacher\laur\probes\phase4_laur_probe_smoke.jsonl `
  --output-jsonl artifacts\teacher\laur\update_labels\phase4_laur_update_dataset_smoke.jsonl `
  --summary-csv outputs\tables\phase4_laur_update_dataset_smoke_summary.csv
```

---

## 10. Phase4F：模型与训练

### 10.1 模型选择

第一版不要上 Transformer / GNN。使用：

```text
LAU-MLP-v1
```

原因：

1. 输入是 checkpoint aggregate features。
2. 输出是 update-rule class，不需要 per-edge message passing。
3. 可导出为小型 JSON/CSV 权重，在 C++ 手写 forward。
4. 训练/部署风险低。
5. 后续可以扩展为 region-level model。

### 10.2 新增文件

```text
src/models/laur_ltm.py
src/train/train_laur_ltm.py
src/train/losses_laur.py
src/eval/eval_laur_offline.py
```

### 10.3 模型结构

`src/models/laur_ltm.py`：

```python
class LaurMlpV1(torch.nn.Module):
    def __init__(self, input_dim: int, num_rules: int, hidden_dim: int = 64):
        super().__init__()
        self.encoder = torch.nn.Sequential(
            torch.nn.Linear(input_dim, hidden_dim),
            torch.nn.ReLU(),
        )
        self.rule_head = torch.nn.Linear(hidden_dim, num_rules)
        self.safety_head = torch.nn.Linear(hidden_dim, 1)
        self.delta_head = torch.nn.Linear(hidden_dim, 1)

    def forward(self, x):
        h = self.encoder(x)
        return {
            "rule_logits": self.rule_head(h),
            "safety_logit": self.safety_head(h).squeeze(-1),
            "delta_pred": self.delta_head(h).squeeze(-1),
        }
```

### 10.4 Loss

`src/train/losses_laur.py`：

```python
loss =
  lambda_rule_ce * CE(rule_logits, best_rule_class)
+ lambda_safety_bce * BCEWithLogits(safety_logit, harmful_update)
+ lambda_delta_regression * SmoothL1(delta_pred, delta_ratio_best)
+ lambda_ltm_regularization * additive_deviation_penalty
```

`additive_deviation_penalty` 可先定义为：

```python
penalty = mean(softmax(rule_logits) probability assigned to non-additive rules)
```

只对 low-confidence neutral samples 加较高权重，防止模型乱改 LTM。

### 10.5 训练指标

必须报告：

```text
rule_top1_accuracy
rule_top3_accuracy
non_neutral_rule_top1_accuracy
harmful_update_precision
harmful_update_recall
harmful_update_f1
safety AUROC if available
predicted best-rule mean delta_ratio in validation probes
neutral-additive rate
map-holdout test performance
```

禁止把 `ltm_normalized_weight_mae` 放在主表。可以完全不训练 edge-weight regression。

### 10.6 模型导出

新增：

```text
artifacts/models/laur_ltm/laur_mlp_v1_weights.json
artifacts/models/laur_ltm/laur_mlp_v1_feature_stats.json
artifacts/models/laur_ltm/laur_mlp_v1_rules.json
```

JSON 内容：

```json
{
  "schema_version": "laur_mlp_v1_weights",
  "input_features": ["agents", "density", "..."],
  "normalization": {
    "mean": [...],
    "std": [...]
  },
  "layers": [
    {"type": "linear", "weight": [[...]], "bias": [...]},
    {"type": "relu"},
    {"type": "linear_rule_head", "weight": [[...]], "bias": [...]},
    {"type": "linear_safety_head", "weight": [[...]], "bias": [...]},
    {"type": "linear_delta_head", "weight": [[...]], "bias": [...]}
  ],
  "rules": {
    "0": "additive_ltm",
    "1": "commit_heavy"
  }
}
```

不要把大 checkpoint 提交 git。可以提交 small smoke model 或只提交 report + command。

### 10.7 训练命令

```powershell
& "$env:USERPROFILE\.conda\envs\czr004\python.exe" src\train\train_laur_ltm.py `
  --config configs\phase4\laur_ltm.yaml `
  --dataset artifacts\teacher\laur\update_labels\phase4_laur_update_dataset_smoke.jsonl `
  --output-dir artifacts\models\laur_ltm\smoke `
  --report outputs\reports\phase4_laur_ltm_train_smoke.md
```

Eval：

```powershell
& "$env:USERPROFILE\.conda\envs\czr004\python.exe" src\eval\eval_laur_offline.py `
  --config configs\phase4\laur_ltm.yaml `
  --dataset artifacts\teacher\laur\update_labels\phase4_laur_update_dataset_smoke.jsonl `
  --model artifacts\models\laur_ltm\smoke\laur_mlp_v1_weights.json `
  --report outputs\reports\phase4_laur_ltm_offline_eval.md `
  --summary-csv outputs\tables\phase4_laur_ltm_offline_eval.csv
```

### 10.8 Phase4F gate

Phase4 smoke gate：

```text
train script runs end-to-end
eval script runs end-to-end
schema validation passes
model export file exists
validation metrics computed
```

Phase4 pilot/full gate：

```text
validation non-neutral checkpoints >= 50
rule_top1_accuracy >= 0.35
rule_top3_accuracy >= 0.70
harmful_update_recall >= 0.80
harmful_update_precision >= 0.30
predicted-rule validation mean delta_ratio_vs_additive >= 0.0
neutral-additive behavior documented
```

如果这些 gate 不通过，不能进入 Phase5 learned runtime；只能进入 Phase5 force-additive / oracle-rule integration smoke。

Commit：

```powershell
git add src/models src/train src/eval src/czr004_teacher tests outputs/reports outputs/tables
git commit -m "model: add LAU-LTM checkpoint-level update model"
```

---

## 11. Phase4 总执行清单

完整 Phase4 smoke 命令链：

```powershell
git status --short

powershell -ExecutionPolicy Bypass -File scripts\build_phase1_ltm.ps1
powershell -ExecutionPolicy Bypass -File scripts\phase1_ltm_smoke.ps1

powershell -ExecutionPolicy Bypass -File scripts\build_phase4_laur_smoke.ps1
powershell -ExecutionPolicy Bypass -File scripts\phase4_laur_update_smoke.ps1

& "$env:USERPROFILE\.conda\envs\czr004\python.exe" scripts\run_phase4_laur_record.py `
  --config configs\phase4\laur_ltm.yaml `
  --mode smoke `
  --overwrite

& "$env:USERPROFILE\.conda\envs\czr004\python.exe" scripts\run_phase4_laur_probes.py `
  --config configs\phase4\laur_ltm.yaml `
  --mode smoke `
  --overwrite

& "$env:USERPROFILE\.conda\envs\czr004\python.exe" -m pytest tests\test_phase4_laur_schema.py

& "$env:USERPROFILE\.conda\envs\czr004\python.exe" src\czr004_teacher\update_sequences.py `
  build-dataset `
  --config configs\phase4\laur_ltm.yaml `
  --output-jsonl artifacts\teacher\laur\update_labels\phase4_laur_update_dataset_smoke.jsonl `
  --summary-csv outputs\tables\phase4_laur_update_dataset_smoke_summary.csv

& "$env:USERPROFILE\.conda\envs\czr004\python.exe" src\train\train_laur_ltm.py `
  --config configs\phase4\laur_ltm.yaml `
  --dataset artifacts\teacher\laur\update_labels\phase4_laur_update_dataset_smoke.jsonl `
  --output-dir artifacts\models\laur_ltm\smoke `
  --report outputs\reports\phase4_laur_ltm_train_smoke.md

& "$env:USERPROFILE\.conda\envs\czr004\python.exe" src\eval\eval_laur_offline.py `
  --config configs\phase4\laur_ltm.yaml `
  --dataset artifacts\teacher\laur\update_labels\phase4_laur_update_dataset_smoke.jsonl `
  --model artifacts\models\laur_ltm\smoke\laur_mlp_v1_weights.json `
  --report outputs\reports\phase4_laur_ltm_offline_eval.md `
  --summary-csv outputs\tables\phase4_laur_ltm_offline_eval.csv
```

Phase4 报告必须写：

```text
outputs/reports/phase4_laur_ltm_report.md
```

包含：

```text
code state
config
data scale
schema validation
force-additive parity
probe label distribution
training metrics
held-out map metrics
failure cases
whether Phase5 is allowed
```

---

## 12. Phase5 总目标

Phase5 把 LAU model 接入 solver-level loop，但必须先做 runtime fallback 和 force-additive parity。

Phase5 顺序：

```text
5A: C++ LAUR runtime skeleton
5B: force-additive runtime integration
5C: rule-table / heuristic integration smoke
5D: exported MLP inference integration
5E: closed-loop LAU smoke and ablation
```

---

## 13. Phase5A：C++ runtime skeleton

### 13.1 新增文件

```text
cpp/ntm/laur_ltm_runtime.hpp
cpp/ntm/laur_ltm_runtime.cpp
cpp/ntm/laur_ltm_features.hpp
cpp/ntm/laur_ltm_features.cpp
```

### 13.2 Runtime API

```cpp
namespace czr004::ntm {

struct LaurRuntimeOptions {
  bool enabled = false;
  bool force_additive = true;
  bool safety_enabled = true;
  bool post_first_solution_only = true;
  bool bottleneck_trigger_only = false;
  uint update_period_restarts = 1;
  std::string model_path;
};

struct LaurFeatureVector {
  std::vector<double> values;
  std::vector<std::string> names;
};

struct LaurPrediction {
  czr004::ltm::UpdateParams params;
  std::string rule_id = "additive_ltm";
  double safety_harmful_prob = 1.0;
  double predicted_delta_ratio = 0.0;
  double inference_ms = 0.0;
  bool enabled = false;
};

class LaurLtmRuntime {
 public:
  bool load(const LaurRuntimeOptions& options);
  LaurPrediction predict(const LaurFeatureVector& features) const;

 private:
  LaurRuntimeOptions options_;
  // loaded standardization stats and small MLP weights
};

}  // namespace czr004::ntm
```

### 13.3 Feature extraction

`cpp/ntm/laur_ltm_features.hpp`：

```cpp
LaurFeatureVector build_laur_features(
    const Instance& instance,
    const czr004::ltm::DirectedTrafficMap& traffic_map,
    const std::vector<czr004::ltm::TraceEvent>& trace_events,
    const LtmIterationStats& stats);
```

If `LtmIterationStats` does not exist, create minimal struct in `cpp/ltm`:

```cpp
struct LtmIterationStats {
  uint iteration = 0;
  uint node_budget = 0;
  bool has_incumbent_before = false;
  bool improved_incumbent = false;
  double best_ratio_before = 0.0;
  double best_ratio_after = 0.0;
  uint returned_solutions_count_so_far = 0;
  uint expanded_nodes_this_iteration = 0;
  uint low_level_pibt_calls_this_iteration = 0;
  double elapsed_ms = 0.0;
};
```

### 13.4 C++ model loading strategy

不要依赖 LibTorch。第一期 C++ runtime 手写小 MLP forward：

```text
JSON/CSV load standardized feature stats
linear layer
ReLU
linear heads
softmax
sigmoid
rule_id -> UpdateParams
```

如果不想引入 JSON parser，模型导出为：

```text
features.txt
mean.csv
std.csv
layer0_weight.csv
layer0_bias.csv
rule_head_weight.csv
rule_head_bias.csv
safety_head_weight.csv
safety_head_bias.csv
rules.csv
```

推荐 CSV，因为 Windows/MSVC 环境更简单。

### 13.5 Phase5A gate

```text
runtime loads additive-only config
predict returns additive params when disabled or force_additive
no solver integration yet
unit smoke passes
```

Commit：

```powershell
git add cpp/ntm cpp/ltm scripts tests
git commit -m "model: add LAU-LTM C++ runtime skeleton"
```

---

## 14. Phase5B：solver loop integration

### 14.1 Integration point

当前 `solve_with_ltm` loop 应变为：

```cpp
for each iteration:
  run OneShotLtmPlanner using current traffic_map
  collect trace H_t
  compute iteration stats
  if laur runtime enabled and allowed:
      features = build_laur_features(...)
      pred = runtime.predict(features)
      if pred safety allows:
          traffic_map.update_from_trace(H_t, pred.params)
      else:
          traffic_map.update_from_trace(H_t, UpdateParams::additive())
  else:
      traffic_map.update_from_trace(H_t)
```

必须保留原入口：

```cpp
LtmRunResult solve_with_ltm(const Instance& instance, const LtmOptions& options);
```

新增 options：

```cpp
struct LtmOptions {
  ...
  bool laur_enabled = false;
  bool laur_force_additive = false;
  std::string laur_model_path;
  bool laur_post_first_solution_only = true;
  uint laur_update_period_restarts = 1;
};
```

或新增单独 API：

```cpp
LtmRunResult solve_with_laur_ltm(const Instance& instance, const LtmOptions& options);
```

更推荐第一种，减少重复 planner 代码。

### 14.2 CLI flags

在 Phase1a batch runner 或新 Phase5 runner 中加入：

```text
--method lacam_star_ltm
--method lacam_star_lau_ltm
--laur-enable
--laur-disable
--laur-force-additive
--laur-model-path <path>
--laur-post-first-solution-only
--laur-every-k-restarts <K>
--laur-safety-threshold <float>
```

### 14.3 Runtime logging fields

每个 JSONL run row 必须新增：

```json
{
  "method": "lacam_star_lau_ltm",
  "laur_enabled": true,
  "laur_force_additive": false,
  "laur_model_path": "artifacts/models/laur_ltm/...",
  "laur_inference_count": 3,
  "laur_inference_total_ms": 5.2,
  "laur_additive_fallback_count": 1,
  "laur_safety_disabled_count": 1,
  "laur_selected_rules": {
    "additive_ltm": 1,
    "block_heavy": 2
  },
  "laur_update_period_restarts": 1,
  "laur_post_first_solution_only": true
}
```

These fields should be schema-normalized by `src/czr004_metrics/schema.py`.

### 14.4 Force-additive parity test

新增 test：

```text
tests/test_phase5_laur_runtime_parity.py
```

Procedure:

1. Run `lacam_star_ltm` smoke.
2. Run `lacam_star_lau_ltm --laur-force-additive`.
3. Compare:

```text
success
sum_of_loss
sum_of_loss_ratio
returned_solutions_count
expanded_nodes if deterministic
low_level_pibt_calls if deterministic
traffic nonzero/max stats
```

Tolerance:

```text
ratio_abs_diff <= 1e-9
success identical
```

If low-level fields differ due nondeterminism, report but do not fail unless solution quality differs.

### 14.5 Phase5B gate

```text
--laur-force-additive matches LTM on smoke
--laur-disable matches LTM on smoke
old Phase1a batch dry-run schema still validates
candidate domain tests pass
TTFS coverage not regressed by logging additions
```

Commit：

```powershell
git add cpp scripts src/czr004_metrics tests outputs/reports
git commit -m "ltm: integrate LAU update runtime with additive parity"
```

---

## 15. Phase5C：closed-loop smoke and ablation

### 15.1 Smoke methods

Run:

```text
LaCAM*
LaCAM*+LTM
LaCAM*+LAU-LTM-force-additive
LaCAM*+LAU-LTM-static-best-rule
LaCAM*+LAU-LTM-learned
```

`static-best-rule` can be a diagnostic method, e.g.:

```text
always block_heavy
always decay_095
```

This isolates whether parameterized update rules have any solver-level effect before neural selection.

### 15.2 Smoke maps

Use:

```text
random-32-32-20
maze-32-32-4
warehouse-10-20-10-2-1
```

Agents:

```text
50
100
```

Time:

```text
3s smoke
10s pilot
```

### 15.3 Metrics

Use Phase2 metrics:

```text
sum_of_loss_ratio
success@time
TTFS
returned_solutions_count
quality-time AUC
planning overhead
expanded_nodes
high_level_expansions
low_level_pibt_calls
laur_inference_count
laur_inference_total_ms
```

### 15.4 Required ablations

At minimum:

```text
LTM only
LAU force-additive
LAU learned update
LAU learned update without safety
LAU every restart
LAU every K=2 restarts
LAU post-first-solution-only
LAU static block-heavy
LAU static decay_095
```

### 15.5 Phase5 gate

Phase5 gate should be realistic:

```text
fallback parity: pass
candidate domain preserved: pass
success@30s: not lower than LTM on smoke
TTFS: not worse than LTM by >10% on smoke, unless post-first-solution only makes TTFS identical
equal-node or equal-wallclock: at least one not worse than LTM on dense/bottleneck smoke
overhead: laur_inference_total_ms reported and not silently hidden
```

If learned model fails but static rules show promise:

```text
Return to Phase4 label/model quality.
Do not claim solver-level learned benefit.
```

If force-additive fails:

```text
Stop. Fix parity before any experiment.
```

---

## 16. Optional Phase5.5：Full LAUR learned restart

Only start this after LAU-LTM passes Phase5 gate.

### 16.1 Why optional

Current one-shot implementation restarts from root and does not preserve search tree metadata across iterations. Full LAUR-restart requires new data:

```text
candidate restart nodes
node depth
node f/g/h
node on incumbent branch?
node generated before improvement?
node local traffic context
```

### 16.2 Minimal restart candidate dump

Add to `OneShotLtmPlanner` optional export:

```cpp
struct RestartCandidate {
  uint node_id;
  uint parent_id;
  uint depth;
  double g;
  double h;
  double f;
  bool on_incumbent_branch;
  bool expanded;
  bool generated_before_incumbent_improvement;
  uint config_hash;
};
```

Dump schema:

```text
phase5_laur_restart_candidate_v1
```

### 16.3 restart_labels.py

Add:

```text
src/czr004_teacher/restart_labels.py
```

Label rules:

```text
positive:
  candidate lies on branch that led to later incumbent improvement
  or candidate's subtree produced better solution in short probe

negative:
  candidate expanded but no improvement
  or high f and no returned solution
```

### 16.4 Restart fallback flags

```text
--laur-restart-enable
--laur-restart-disable
--laur-root-restart
--laur-restart-force-root
```

### 16.5 Full LAUR gate

```text
root fallback parity passes
restart candidate schema validates
learned restart does not reduce success
learned restart shows at least one equal-node gain
```

If noisy:

```text
Keep main method as LAU-LTM.
Report learned restart as attempted extension or ablation.
```

---

## 17. Phase6 主实验设计

### 17.1 Methods

Main methods:

```text
LaCAM*
LaCAM*+LTM
LaCAM*+LAU-LTM
```

Optional if available:

```text
LaCAM*+TO
LaCAM*+SUO
LaCAM*+LAUR-LTM-restart
```

If TO/SUO original or auditable implementation remains unavailable, mark:

```text
TO/SUO: not reproduced / unavailable
```

Do not invent substitutes.

### 17.2 One-shot MAPF

Use LTM paper style:

```text
8 maps
25 random instances per map
30s
sum_of_loss_ratio
```

Agent schedules should match Phase1a frozen setup unless deliberately running extension.

### 17.3 Anytime curves

At minimum:

```text
ratio vs wall-clock
quality-time AUC
TTFS
returned_solutions_count
incumbent improvement count
```

At least one dense map:

```text
random-64-64-20, 1000 agents
```

if feasible.

### 17.4 Planning-and-execution

Use:

```text
E = {0.1, 0.5}
X = {5, 10, 20}
```

Report:

```text
success
average ratio
runtime
replanning stability
LAU overhead
safety fallback count
```

### 17.5 Generalization

At least two:

```text
same map unseen seed
low-density train -> high-density test
held-out map test
dense/bottleneck subset
```

LAU-LTM is especially expected to show value in:

```text
dense corridors
maze bottlenecks
warehouse aisles
post-first-solution refinement
planning-and-execution repeated replanning
```

### 17.6 Mandatory ablation table

```text
LTM
LAU force-additive
LAU static best rule
LAU learned no safety
LAU learned with safety
LAU every restart
LAU every K restarts
LAU post-first-solution only
LAU no blocked features
LAU no wait features
LAU no decay rules
```

### 17.7 Proving gains are real

Every Phase6 claim must include:

```text
same metrics harness
same maps/scenarios/seeds
same time limit
paired instance deltas
paired sign test
bootstrap confidence interval
equal-wallclock result
equal-node result if available
expanded_nodes / high_level_expansions / low_level_pibt_calls
planning_overhead_ms
laur_inference_count
```

### 17.8 Phase6 gate

Positive result is not only “mean beats LTM everywhere.” Acceptable positive outcomes:

```text
mean ratio <= LTM or statistically tied
and at least one:
  dense/bottleneck subset better
  anytime AUC better
  planning-and-execution more stable
  overhead lower than expected
  held-out map generalization better
  equal-node not worse
```

Negative result handling:

```text
If LAU improves offline labels but not solver-level metrics:
  write as negative closed-loop result.
  Do not claim learned traffic update improves LaCAM*.

If safety gate disables most updates:
  report as evidence that additive LTM is already strong or probes are noisy.

If static rule beats learned:
  diagnose model/features/labels; do not claim learned update.
```

---

## 18. Reports to produce

### 18.1 Phase4 report

```text
outputs/reports/phase4_laur_ltm_report.md
```

Template:

```markdown
# Phase4 LAU-LTM Report

## Code State
- branch:
- commit:
- dirty:

## Goal
Learn LTM update dynamics from PIBT trace/checkpoint data.

## Architecture Decision
- LAU-only first
- learned restart deferred

## Data
- checkpoint rows:
- trace rows:
- probe rows:
- label rows:
- split:

## Parameterized Update Validation
- force-additive parity:
- weight bound:
- wait propagation:
- goal wait ignore:

## Probe Labels
- rule distribution:
- neutral checkpoints:
- harmful update count:
- best-rule histogram:

## Model
- architecture:
- features:
- heads:
- loss:

## Offline Results
- rule top1/top3:
- harmful recall/precision:
- predicted probe delta:
- held-out map:

## Gate
- pass/fail:
- blockers:

## Repro Commands
```

### 18.2 Phase5 report

```text
outputs/reports/phase5_laur_solver_integration_report.md
```

Include:

```text
fallback parity
solver smoke
overhead
ablation
TTFS
candidate domain tests
```

### 18.3 Phase6 report

```text
outputs/reports/phase6_laur_main_eval_report.md
```

Include:

```text
main table
anytime curves
P&E table
ablation
stat tests
failure analysis
artifact manifest
```

---

## 19. Commit sequence for Codex

Recommended commits:

```text
docs: add LAU-LTM phase4 execution plan and config
ltm: add parameterized update rule with additive fallback
trace: add LAU iteration checkpoints and raw trace export
trace: add LAU update-rule probe labels
model: add LAU-LTM checkpoint-level update model
metrics: add LAU schema fields and summaries
model: add LAU C++ runtime skeleton
ltm: integrate LAU runtime with additive parity
eval: add LAU closed-loop smoke and ablations
docs: report LAU-LTM phase4 gate
```

Do not combine all work into one commit.

---

## 20. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---:|---:|---|
| force-additive not identical | medium | very high | stop Phase5, fix update path |
| trace/checkpoint files huge | high | medium | top-K snapshots, raw traces ignored, compression |
| short-probe labels noisy | high | high | neutral threshold, repeated seeds, safety labels |
| model learns map-specific bias | medium | high | map-holdout split, no map-name feature |
| learned update hurts TTFS | medium | high | post-first-solution-only default |
| C++ MLP runtime too complex | medium | medium | start linear/1-hidden MLP with CSV weights |
| learned restart needs search tree | high | high | defer restart until LAU passes |
| static rule beats model | medium | medium | report diagnostic, improve features/labels |
| overhead hides gains | medium | high | report inference_ms and equal-node |

---

## 21. Immediate next step

For Codex, the next concrete task is **not** model training. It is:

```text
Implement Phase4B parameterized UpdateLTM with force-additive parity.
```

Minimal first instruction to Codex:

```text
Start on branch phase4-laur-ltm from phase1a-ltm-paper-parity.
Before code, append docs/codex-worklog.md.
Implement UpdateParams and update_from_trace(events, params) in cpp/ltm.
Keep old update_from_trace(events) behavior unchanged.
Add force-additive parity smoke.
Do not implement model or restart yet.
Run Phase1 smoke and new LAU update smoke.
Write outputs/reports/phase4_laur_ltm_update_api_report.md.
```

Only after this passes should Codex work on raw trace/checkpoint export.

---

## 22. Codex 可执行性评估（2026-05-26 补充）

Codex 对本执行计划的当前判断：**可执行性 8/10，可以进入 Phase4B，但必须先落实第 23 章的接口对齐约束。**

强项：

- 路线已经从完整 LAUR 收敛为 LAU-only first，避免一开始改持久化 search tree / learned restart。
- Phase4B -> Phase4C -> Phase4D -> Phase4E -> Phase4F 的依赖顺序合理。
- `--laur-force-additive` / force-additive parity 被放在核心 gate，是保护 LTM 语义的正确生命线。
- C++ 端不依赖 LibTorch，采用轻量参数 / JSON 权重 / 手写 forward 的部署策略，适合当前 Windows/MSVC 仓库。
- 数据 split、schema validation、fallback、overhead、equal-node 的要求比较完整。

主要缺口：

- 部分 checkpoint / metric 字段在当前仓库中还不是一等字段，需要明确来源、nullable 策略或新增 instrumentation。
- trace wait 语义需要固定为派生字段，不能扩散修改 `TraceEventKind`。
- Phase4 tool 边界需要固定为新 tool 隔离，不能污染 Phase1a paper-parity runner。
- force-additive parity 的比较口径需要分成 strict fail 与 warn-only 两级。
- Phase4 gate 必须基于 pilot，不应把 smoke 管线通过误判为 learned runtime 可进入 Phase5。

本计划补完第 23 章后，可执行性可视为 **9/10 到 9.5/10**；真正开工时仍以 Phase4B 的 update API parity 为第一里程碑。

---

## 23. 前置接口对齐附录（必须先钉死）

本章覆盖 Claude review 中提出的 5 个钉死点，并结合当前仓库实际接口补充执行约束。若本章和前文计划冲突，Phase4B-Phase4D 执行时优先按本章。

### 23.1 force-additive parity 两级比较口径

Phase4B 的 update API parity 和 Phase5B 的 solver runtime parity 分开验收。

Phase4B：`DirectedTrafficMap::update_from_trace(events, UpdateParams::additive())` 必须与旧 `update_from_trace(events)` 对同一事件序列产生一致 traffic map。

严格 fail 字段：

- every edge `raw_count`
- every edge `normalized_weight`
- `nonzero_raw_edges`
- `max_raw_count`
- `max_normalized_weight`

建议容差：

```text
abs_tol = 1e-12
rel_tol = 1e-12
```

Phase5B：`lacam_star_lau_ltm --laur-force-additive` 必须在 solver 输出层与 `lacam_star_ltm` 对齐。

严格 fail 字段：

- `success`
- `feasible`
- `sum_of_loss`
- `sum_of_loss_ratio`
- 若两边都 success：`lower_bound`、`makespan`

warn-only 字段：

- `runtime_ms`
- `time_to_first_solution_ms`
- `returned_solutions_count`
- `expanded_nodes`
- `high_level_expansions`
- `low_level_pibt_calls`
- `ltm_iterations`
- `committed_events`
- `blocked_events`
- `nonzero_ltm_edges`

解释：

- Phase4B 是纯 update API，对 deterministic edge map 必须严格一致。
- Phase5B 涉及完整 solver run，低层计数理论上应接近或一致，但 Windows timing、日志聚合、未来 runtime wrapper 可能引入非语义差异；这些字段必须报告和调查，但不应在第一层 gate 上阻塞。
- 如果 warn-only 字段出现大幅漂移，不能做性能声明，只能继续 parity diagnosis。

### 23.2 当前字段来源表

下表是 Phase4C checkpoint / Phase4D probe 开工前的字段口径。字段状态分为：

- `existing`: 当前仓库已直接写出或可直接解析。
- `derive`: 可从当前字段或 trace 派生。
- `new`: 需要新增 instrumentation。
- `nullable`: 第一版允许为空，但必须在 schema 中显式允许。

| 字段 | 状态 | 当前来源 / 新增位置 | Phase4 口径 |
|---|---|---|---|
| `success` | existing | `cpp/tools/phase1a_batch.cpp` JSONL | run-level strict metric |
| `feasible` | existing | `cpp/tools/phase1a_batch.cpp` JSONL | run-level strict metric |
| `sum_of_loss` | existing | final solution + `get_sum_of_loss` | run / probe outcome |
| `lower_bound` | existing | `get_sum_of_costs_lower_bound` | run / probe outcome |
| `sum_of_loss_ratio` | existing | `sum_of_loss / lower_bound` | run / probe outcome |
| `makespan` | existing | `get_makespan` | run / probe outcome |
| `runtime_ms` | existing | wall-clock around solve | diagnostic / overhead |
| `time_to_first_solution_ms` | nullable -> new | currently always `null` in `phase1a_batch.cpp` | Phase4 smoke 可为空；pilot 前若用 TTFS label，需要在 `solve_with_ltm` 或 record tool 中新增 first-solution timing |
| `returned_solutions_count` | existing but coarse | currently `0/1` final run-level count | Phase4 smoke 可用；`returned_solutions_count_so_far` 需要新增 per-iteration improvement count |
| `loop_cnt` | existing | sum of `ltm_one_shot_loop_cnt` | run-level high-level work proxy |
| `expanded_nodes` | existing | sum of `ltm_one_shot_num_node_gen` | run-level work proxy |
| `high_level_expansions` | existing | currently equals `loop_cnt` in Phase1a runner | run-level work proxy |
| `low_level_pibt_calls` | existing | sum of `ltm_one_shot_low_level_pibt_calls` | run-level work proxy |
| `ltm_iterations` | existing | `LtmRunResult.iterations` | run-level |
| `committed_events` | existing | `LtmRunResult.trace_summary.committed` | run-level trace summary |
| `blocked_events` | existing | `LtmRunResult.trace_summary.blocked` | run-level trace summary |
| `nonzero_ltm_edges` | existing | `DirectedTrafficMap::nonzero_raw_edges()` | final map summary |
| `iteration` | existing in additional_info / new for JSONL | `solve_with_ltm` writes text `ltm_iteration=` | Phase4C record tool must write structured JSON field; public schema uses `iteration` |
| `node_budget` | existing in additional_info / new for JSONL | `ltm_one_shot_node_budget` | Phase4C record tool must write structured JSON field; public schema uses `node_budget` |
| `expanded_nodes_this_iteration` | derive -> new | per-iteration `ltm_one_shot_num_node_gen` text exists | Phase4C record tool should parse/write structured field |
| `high_level_expansions_this_iteration` | derive -> new | per-iteration loop count / high-level expansion count | Phase4C record tool should parse/write structured field |
| `low_level_pibt_calls_this_iteration` | derive -> new | per-iteration `ltm_one_shot_low_level_pibt_calls` text exists | Phase4C record tool should parse/write structured field |
| `trace_event_count` | derive | grouped raw trace rows per checkpoint | required Phase4C consistency check |
| `committed_count` | derive | raw trace rows where `kind=committed` | checkpoint feature |
| `blocked_count` | derive | raw trace rows where `kind=blocked` | checkpoint feature |
| `wait_event_count` | derive | raw trace rows where `is_wait=true` and `at_goal=false` | checkpoint feature |
| `goal_wait_ignored_count` | derive | raw trace rows where `is_wait=true` and `at_goal=true` | checkpoint feature |
| `current_best_sol_ratio` | new / nullable | needs best-so-far solution before/after iteration | nullable in smoke; required before ratio-based labels |
| `last_iteration_improved_solution` | new | compare solution vs previous best in `solve_with_ltm` loop | useful Phase4C field |
| `returned_solutions_count_so_far` | new / nullable | count best-solution improvements over iterations | nullable in smoke |
| `traffic_snapshot_path` | new | Phase4C record tool | required when probes need replayed `W_t` |
| `trace_path` | new | Phase4C record tool | required for checkpoint-trace join |

Hard rule:

- Phase4 smoke may allow `time_to_first_solution_ms`, `current_best_sol_ratio`, and `returned_solutions_count_so_far` to be `null`.
- Phase4 pilot labels that claim TTFS / ratio / AUC supervision must first implement the relevant non-null instrumentation.

### 23.3 trace wait 语义定案

当前 C++ 接口为：

```cpp
enum class TraceEventKind { Committed, Blocked };

struct TraceEvent {
  TraceEventKind kind;
  uint agent_id;
  uint from_id;
  uint to_id;
  bool at_goal;
};
```

Phase4B-Phase4D 不扩展 `TraceEventKind`。固定规则如下：

- `kind` 只允许 `committed` 或 `blocked`。
- `is_wait = (from_id == to_id)` 作为导出 JSONL 的派生字段。
- `at_goal` 保留现有语义。
- `propagation_kind` 是导出字段，不是主事件类型。

推荐 JSONL 字段：

```json
{
  "kind": "committed",
  "from_id": 10,
  "to_id": 10,
  "at_goal": false,
  "is_wait": true,
  "propagation_kind": "wait_spillover"
}
```

`propagation_kind` 允许值：

- `none`: 非 wait action。
- `wait_spillover`: `from_id == to_id` 且 `at_goal == false`，对应 LTM 把拥堵传播到相邻出边。
- `goal_wait_ignored`: `from_id == to_id` 且 `at_goal == true`，对应 LTM 不增加 traffic。

Phase4B 的 `UpdateParams` additive parity 必须复现当前 `increment_event` 行为：

- 非 wait committed：对 `(from_id, to_id)` 加 `alpha_commit=1.0`。
- 非 wait blocked：对 `(from_id, to_id)` 加 `alpha_block=1.0`。
- wait 且非 goal：对 `from_id` 的每条 outgoing edge 加 `alpha_wait_spillover=1.0`。
- goal wait：不加任何 raw count。

Phase4D 若需要 edge-level wait propagation features，可以在 Python feature builder 中从 wait self-loop 展开到 outgoing edges；raw trace 不写成多条 propagated edge event。

### 23.4 Phase4 tool 边界定案

Phase4 record / probe 使用独立 tool，不扩展 `cpp/tools/phase1a_batch.cpp`。

固定新增：

```text
cpp/tools/phase4_laur_record.cpp
cpp/tools/phase4_laur_probe.cpp
scripts/run_phase4_laur_record.py
scripts/run_phase4_laur_probes.py
```

`phase1a_batch.cpp` 的地位：

- 保持 Phase1a / Phase3 paper-parity 与 final traffic-map label 入口。
- 不加入 Phase4 checkpoint / probe 逻辑。
- 只在确有必要时抽取共享 JSON helper 或 shared LTM API，不能让 Phase4 flags 进入 Phase1a runner。

理由：

- Phase1a 是已完成 gate 的复现入口，污染后会影响历史结果可信度。
- Phase4C/4D 需要 checkpoint、trace、snapshot、probe replay 等实验性字段，应该隔离演进。
- 独立 tool 更容易做 destructive-free rollback 和 schema versioning。

### 23.5 Phase4 数据规模与 gate 定案

三层数据规模含义固定如下：

| 层级 | 作用 | 是否允许进入 Phase5 learned runtime |
|---|---|---|
| `smoke` | 证明 config、record、schema、probe、dataset、train loop 能跑通 | 不允许 |
| `pilot` | 产生足够 non-neutral checkpoints，验证 offline signal 和 overhead | 允许，若满足 Phase4F gate |
| `phase4-full` | 论文级或 Phase6 前训练数据 | 不是 Phase5 smoke 的前置，但进入 Phase6 主实验前需要 |

Phase4 learned runtime gate 必须基于 `pilot`，不是 `smoke`。

最低 gate：

- validation non-neutral checkpoints `>= 50`。
- additive / neutral class 不得压倒到让 best-rule classifier 无意义；若严重不平衡，必须报告 class distribution 并调整 sampling。
- validation update-rule selection accuracy 高于 additive-only 或 majority baseline。
- harmful-update recall 过线；若 safety head 不可靠，只允许进入 force-additive / oracle-rule integration，不允许 learned model closed-loop。
- Phase4 report 明确区分 smoke success 与 pilot evidence。

### 23.6 UpdateParams C++ 接口对齐

第一版 `UpdateParams` 必须保持最小、可 parity、可扩展。

建议字段：

```cpp
struct UpdateParams {
  double alpha_commit = 1.0;
  double alpha_block = 1.0;
  double alpha_wait_spillover = 1.0;
  double rho_decay = 1.0;
  bool enable_contraflow_penalty = false;
  double contraflow_penalty = 0.0;
  bool enable_local_saturation = false;

  static UpdateParams additive();
};
```

第一版实现约束：

- `UpdateParams::additive()` 必须完全复现旧 update。
- `rho_decay=1.0` 等价不衰减；若 `rho_decay < 1.0`，应在处理新事件前对 raw counts 乘 decay。
- `enable_local_saturation=false` 时必须使用当前 `renormalize()` 的 max-count normalization。
- local saturation / sigmoid / spillover radius 可以先保留 config 字段，但不应在 Phase4B 第一版实现，避免 parity 面扩大。
- contraflow 默认关闭；任何非零 contraflow 只能在 Phase4D probe candidate rule 或后续 learned runtime 中启用。

API：

```cpp
void update_from_trace(const std::vector<TraceEvent>& events);
void update_from_trace(const std::vector<TraceEvent>& events,
                       const UpdateParams& params);
```

旧 API 必须只是 wrapper：

```cpp
void DirectedTrafficMap::update_from_trace(
    const std::vector<TraceEvent>& events) {
  update_from_trace(events, UpdateParams::additive());
}
```

### 23.7 checkpoint / trace schema 对齐

新增 schema helper 不直接塞进 Phase3 `schema.py` 主体，避免影响已经完成的 Phase3 gate。

推荐新增：

```text
src/czr004_teacher/update_sequences.py
tests/test_phase4_laur_schema.py
```

schema version：

```text
phase4_laur_checkpoint_v1
phase4_laur_trace_event_v1
phase4_laur_update_label_v1
```

checkpoint row 必须至少包含：

- `schema_version`
- `run_id`
- `checkpoint_id`
- `map_name`
- `agents`
- `seed`
- `time_limit_sec`
- `iteration`
- `node_budget`
- `sum_of_loss_this_iteration`
- `lower_bound_sol`
- `sum_of_loss_ratio_this_iteration`
- `expanded_nodes_this_iteration`
- `high_level_expansions_this_iteration`
- `low_level_pibt_calls_this_iteration`
- `trace_event_count`
- `committed_count`
- `blocked_count`
- `wait_event_count`
- `goal_wait_ignored_count`
- `traffic_before_nonzero_edges`
- `traffic_after_nonzero_edges`
- `traffic_before_max_raw`
- `traffic_after_max_raw`
- `traffic_after_max_normalized`
- `raw_before_topk`
- `raw_after_topk`
- `normalized_after_topk`
- `traffic_snapshot_path`
- `trace_path`
- `branch`
- `commit`
- `dirty`

nullable allowed in smoke：

- `sum_of_loss_this_iteration`
- `sum_of_loss_ratio_this_iteration`
- `time_to_first_solution_ms`
- `returned_solutions_count_so_far`
- `expanded_nodes_this_iteration`
- `high_level_expansions_this_iteration`
- `low_level_pibt_calls_this_iteration`

trace event row 必须至少包含：

- `schema_version`
- `run_id`
- `checkpoint_id`
- `iteration`
- `event_index`
- `kind`
- `agent_id`
- `from_id`
- `to_id`
- `at_goal`
- `is_wait`
- `propagation_kind`
- `propagated_to_id`
- `map_name`
- `agents`
- `seed`

join audit 必须检查：

- 每个 `checkpoint_id` 至少有 0 条或多条 trace rows，但 `trace_event_count` 必须等于实际 join 后行数。
- `committed_count + blocked_count == trace_event_count`。
- `wait_event_count + goal_wait_ignored_count <= trace_event_count`。
- `committed_count`、`blocked_count`、`wait_event_count`、`goal_wait_ignored_count` 必须分别与 grouped trace rows 一致。
- 所有 trace row 的 `run_id`、`checkpoint_id`、`iteration`、`map_name`、`agents`、`seed` 与 checkpoint 对齐。
- 所有 normalized traffic weights 必须 bounded in `[0, 10]`。
- split 不泄漏；沿用 Phase3 split helper 或在 `update_sequences.py` 中明确复用同一规则。

### 23.8 命令与路径约定

当前仓库已有脚本多使用：

```powershell
& 'C:\PROGRAMING\anaconda\Scripts\conda.exe' run -n czr004 python ...
```

Phase4 文档和脚本应优先沿用这个口径，不硬编码：

```powershell
$env:USERPROFILE\.conda\envs\czr004\python.exe
```

建议：

- 文档中的命令示例统一写 `conda run -n czr004 python ...` 或现有绝对 conda 路径。
- PowerShell scripts 内部可接收 `-CondaExe` 参数，默认 `C:\PROGRAMING\anaconda\Scripts\conda.exe`。
- 所有 artifact 输出仍遵守 `.gitignore`：raw traces、snapshots、models 默认不进 git；提交 report、summary CSV、小 smoke fixture。

### 23.9 Phase5 runtime logging 接口

Phase5 引入 learned runtime 时，run JSONL 需要新增 LAU 字段，并由 `src/czr004_metrics/schema.py` 做 optional normalization。

建议字段：

- `laur_enabled`
- `laur_force_additive`
- `laur_update_mode`
- `laur_inference_count`
- `laur_safety_fallback_count`
- `laur_update_runtime_ms`
- `laur_model_path`
- `laur_alpha_commit_mean`
- `laur_alpha_block_mean`
- `laur_alpha_wait_spillover_mean`
- `laur_rho_decay_mean`

这些字段在 Phase5 前全部 optional。Phase5 report 中必须报告：

- LAU runtime 是否实际启用。
- force-additive 是否为 true。
- inference / update overhead。
- safety fallback 次数。
- 与 LTM 的 strict parity / warn-only parity 差异。

---

## 24. 修订后的立即开工顺序

Phase4B 已在 `phase4-laur-ltm` 分支以 commit `fef6956` 通过 gate。当前开始 Phase4C 前，第一步必须收窄为：

```text
1. git status --short。
2. 确认只有用户已知的 untracked 1.txt 可忽略。
3. 先追加 docs/codex-worklog.md。
4. 不做 learning/training。
5. 不改 cpp/ntm。
6. 不实现 learned restart。
7. 不回滚已有 UpdateParams / force-additive parity 代码。
```

随后 Phase4C 执行顺序为：

```text
1. 新增 phase4_laur_record C++ target。
2. 新增 scripts/run_phase4_laur_record.py wrapper。
3. 新增 src/czr004_teacher/update_sequences.py helper。
4. 新增 tests/test_phase4_laur_schema.py。
5. 产出 phase4_laur_checkpoint_v1 checkpoint JSONL。
6. 产出 phase4_laur_trace_event_v1 raw trace JSONL。
7. 跑 checkpoint/trace schema validation。
8. 跑 checkpoint-trace join audit。
9. 跑 trace_event_count 与 committed/blocked/wait consistency audit。
10. 跑 Phase1 LTM smoke 回归。
11. 跑 Phase4B force-additive update smoke 回归。
12. 写 outputs/reports/phase4_laur_trace_checkpoint_report.md。
```

Phase4C 不包含 `phase4_laur_probe.cpp`、update-rule labels、model training 或 runtime learned update；这些仍属于 Phase4D 以后。

---

## 25. 2026-05-27 Phase4F Repair2：advanced update-rule network 预案记录

### 25.1 当前状态

Phase4F `full_repair1` 已在旧服务器 `ackcs-00gjgxxy` 上完成并备份：

- record/probe/dataset/train/eval operational gate 全部通过。
- 中小型证据已提交到 git。
- compressed raw trace `.zst` 已完整下载到本地并通过 sha256 校验，但不进入 git。
- repair1 仍未通过 Phase4F performance gate：
  - validation rule top1 `0.3072 < 0.35`
  - validation rule top3 `0.6427 < 0.70`
  - harmful recall `0.9538 >= 0.80`
  - harmful precision `0.4015 >= 0.30`
  - predicted-rule mean delta `0.0110 > 0.0`

结论：repair1 修好了 safety/fallback 方向，但 exact update-rule ranking 仍不足，不能进入 Phase5 learned runtime。

### 25.2 GPT Pro repair2 建议稿

建议稿文件：

```text
phase4f_repair2_advanced_update_rule_network_plan.md
```

该建议与当前证据一致，可以作为下一轮 Phase4F repair2 的候选执行方案。它不改变 LAU/LAUR-LTM 路线，不降低 gate，也不进入 Phase5 runtime。

### 25.3 Repair2 可以尝试的原因

当前失败不像是纯 safety 问题：

- safety recall/precision 已通过。
- train top3 已超过 gate，但 validation top3 仍未过，说明存在泛化与规则排序问题。
- 旧 MLP-v1 的输入是 aggregate checkpoint features，输出是 hard best-rule class，可能丢失 traffic map state、trace/event 结构和 candidate-rule 条件信息。

因此 repair2 可以尝试把任务从：

```text
checkpoint -> best rule class
```

改成：

```text
Q(checkpoint, candidate update rule)
P_harmful(checkpoint, candidate update rule)
```

再用 safety-gated argmax 选择 update rule。

### 25.4 Repair2 允许做的范围

Repair2 仍属于 offline Phase4F。

Allowed：

- 清理 executable update-rule target。
- 把 `neutral_additive` 从 executable rule class 中折叠到 `additive_ltm`，同时保留 original label / neutral flag 供 audit。
- 构建 token/rule-aware dataset v2。
- 使用已有 repair1 artifacts：
  - checkpoints JSONL
  - probe JSONL
  - update dataset JSONL
  - verified local raw trace zst
  - traffic snapshots / checkpoint top-k 信息（如需要）
- 实现 LAU-SetTransformer-v2 / LAU-EdgeTraceTransformer-v2。
- 使用 listwise / pairwise / delta regression / per-rule harmful BCE / family auxiliary loss。
- 离线训练、离线评估、写 repair2 report。

Not allowed：

- 不降低 Phase4F gate。
- 不进入 Phase5 runtime。
- 不改 C++ learned runtime / `solve_with_ltm` 行为。
- 不替换 PIBT。
- 不预测 agent actions。
- 不实现 learned restart。
- 不把 large raw trace `.zst` 提交进 git。

### 25.5 Repair2 最小执行顺序

等待用户明确命令后再开始。默认顺序：

```text
R2-A. Clean executable update-rule target
R2-B. Build token/rule-aware dataset v2
R2-C. Implement LAU-SetTransformer-v2 smoke baseline
R2-D. Implement LAU-EdgeTraceTransformer-v2
R2-E. Train/evaluate locally on repair1 artifacts
R2-F. 若本地 evidence 超过 repair1，再考虑服务器 full offline training
R2-G. 写 outputs/reports/phase4f_repair2_advanced_update_rule_network_report.md
R2-H. 根据 Phase4F gate 判断 pass/fail；未过则继续留在 Phase4F
```

### 25.6 Repair2 gate 不变

Repair2 仍必须满足：

```text
validation rule top1 >= 0.35
validation rule top3 >= 0.70
harmful recall >= 0.80
harmful precision >= 0.30
predicted-rule mean delta > 0.0
validation non-neutral checkpoints >= 50
```

可以新增 executable-rule metrics、family metrics、per-map confusion、oracle/top-k delta diagnostics，但这些不能替代主 gate。

### 25.7 Repair2 后续决策

- 如果 SetTransformer 或 EdgeTraceTransformer 通过 Phase4F gate：记录 pass，随后单独规划 Phase5 runtime，不在同一轮直接进入 Phase5。
- 如果 advanced models 提升 top1/top3 但仍未过 gate：继续留在 Phase4F，下一步考虑 label/probe ambiguity、map-family balance、topology-biased attention 或 sequence-of-checkpoints。
- 如果 advanced models 不优于 repair1：记录 negative result，优先怀疑 probe label ambiguity / update-rule set / target formulation，而不是继续盲目扩大 MLP。

当前状态：**repair2 已由用户授权并完成本地离线执行；结果未通过 Phase4F gate，不能进入 Phase5 learned runtime。详见第 26 节。**

---

## 26. 2026-05-27 Phase4F Repair2 本地执行结果

### 26.1 已完成内容

Repair2 已按 offline Phase4F 范围完成：

- 新增 `phase4_laur_update_dataset_v2` token/rule-aware dataset builder。
- 将 executable target 从 original label 中拆出：
  - `neutral_additive -> additive_ltm`
  - 保留 `rule_class_original`、`best_rule_original`、`is_neutral_label` 供 audit。
- 新增 LAU-EdgeTraceTransformer-v2。
- 新增 LAU-SetTransformer-v2。
- 使用 listwise soft target、pairwise margin、delta regression、per-rule harmful BCE、family auxiliary loss。
- 只做离线训练/评估；未进入 C++ runtime，未改 `solve_with_ltm`，未实现 learned restart。

### 26.2 主要输出

```text
configs/phase4/laur_ltm_full_repair2_attention.yaml
configs/phase4/laur_ltm_repair2_attention_smoke.yaml
src/czr004_teacher/token_features_laur.py
src/czr004_teacher/token_dataset_laur.py
src/models/laur_rule_attention.py
src/train/losses_laur_rule_attention.py
src/train/train_laur_rule_attention.py
src/eval/eval_laur_rule_attention.py
outputs/reports/phase4f_repair2_advanced_update_rule_network_report.md
outputs/reports/phase4f_repair2_threshold_sweep_summary.json
```

### 26.3 最好结果

在保持 harmful recall / precision / positive delta 通过的条件下，最好 validation 结果来自：

```text
model: LAU-SetTransformer-v2
dataset soft target: temperature 0.010, hard_mix 0.55
harmful threshold: 0.10
```

结果：

```text
validation top1       = 0.3159   < 0.35  fail
validation top3       = 0.5033   < 0.70  fail
harmful recall        = 0.9711   pass
harmful precision     = 0.3916   pass
mean selected delta   = 0.0050   pass
validation nonneutral = 359      pass
```

阈值 sweep 中，最高 top3 可到 `0.6580`，但此时 harmful recall 只有 `0.6127`，不满足 safety gate。

### 26.4 与 repair1 对比

Repair1：

```text
validation top1 = 0.3072
validation top3 = 0.6427
harmful recall  = 0.9538
harmful precision = 0.4015
mean delta = 0.0110
```

Repair2：

```text
best gate-compatible top1 = 0.3159
best gate-compatible top3 = 0.5033
best top3 under threshold sweep = 0.6580, but safety recall fails
```

结论：Repair2 的 advanced rule-conditioned architecture 没有通过 Phase4F gate，也没有稳定优于 repair1。它略微改善了 best gate-compatible top1，但显著损失 top3 ranking。

### 26.5 当前决策

Phase4F **尚未通过**。

不要进入 Phase5 learned runtime。下一步如果继续 Phase4F，应优先排查：

- label/probe ambiguity：许多 rule delta 接近，hard exact-rule top3 可能不稳定。
- rule set / target formulation：当前 8 个 executable rules 可能粒度不合适。
- trace richness：本轮 Repair2 首先使用 checkpoint top-k + count trace tokens，尚未把 3.5GB raw trace 解成高密度 event-token sequence。
- validation map-family generalization：repair2 advanced model 对 held-out map 的 top3 不如 repair1。

---

## 27. 2026-05-27 Phase4F Repair3：stable target formulation

### 27.1 触发原因

Repair2 后继续检查 repair1 的 label/probe ambiguity，得到当前 full_repair1 validation：

```text
best-vs-second <= 0.005 : 53.38%
best-vs-second <= 0.010 : 70.59%
best-vs-second <= 0.020 : 82.35%
```

这说明 hard best-rule label 在大量 checkpoint 上并不稳定。Repair3 因此不再继续扩大模型，而是先修复 target formulation。

### 27.2 Stable target policy

Stable target 不降低 Phase4F 阈值，只改变近 tie probe group 的 deterministic tie-break：

```text
tie_epsilon = 0.010
neutral_delta_threshold = 0.005
prefer_additive_if_tied = true
priority = additive_ltm, commit_heavy, block_heavy, wait_light, wait_heavy, block_light, decay_095, decay_090
```

规则：

1. 如果 best delta `< 0.005`，label 为 `neutral_additive`。
2. 如果 `additive_ltm` 在 best delta `0.010` 以内，label 为 `neutral_additive`。
3. 否则在 tie band 内按 priority 选 stable rule。

Stable target 数据：

```text
artifacts/teacher/laur/full_repair3_stable_targets/update_labels/phase4_laur_update_dataset_full_repair3_stable_tie001.jsonl
```

变更统计：

```text
rows = 2985
changed_rule_class = 890 / 2985 = 29.82%
max_best_minus_stable = 0.010
mean_best_minus_stable = 0.0020
schema errors = 0
```

### 27.3 Phase4F gate result

使用 repair1 MLP 配置重新训练，seed `61`，harmful threshold `0.10`。

Validation：

```text
rule top1       = 0.3899782135  pass >= 0.35
rule top3       = 0.7690631808  pass >= 0.70
harmful recall  = 0.9421965318  pass >= 0.80
harmful precision = 0.3908872902 pass >= 0.30
mean selected delta = 0.0081308431 pass > 0.0
validation non-neutral = 293 pass >= 50
```

这是当前分支第一次本地满足 Phase4F performance gate 的结果。

### 27.4 稳定性备注

额外 seed：

```text
seed 103: top1/top3/safety pass, mean selected delta = -0.0010 fail
seed 107: top1/top3/safety pass, mean selected delta = -0.0012 fail
```

因此 Phase4F 可以记录为 **stable-target candidate pass**，但 Phase5 不能直接做 learned runtime 性能声明。下一步只能进入 Phase5 parity / fallback / conservative runtime gate 规划，并保留 additive fallback。

### 27.5 当前决策

Phase4F offline gate 在 stable-target formulation 下已有 candidate pass。

允许进入 Phase5 规划的前置条件：

- Phase5 首先做 `--laur-disable` / `--laur-force-additive` parity。
- learned runtime 接入必须 safety-gated，低置信或 unsafe rule 回退 `additive_ltm`。
- 不得声称 closed-loop learned runtime 性能，直到 Phase5 runtime smoke/ablation 另行通过。
