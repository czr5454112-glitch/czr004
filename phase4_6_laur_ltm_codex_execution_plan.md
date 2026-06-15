# LAU/LAUR-LTM Phase4–Phase6 Codex 执行计划

## 2026-06-14 Repair5G.5.50 region-to-policy update

G5.50 does not change LaCAM*/PIBT/search semantics and does not open runtime, Phase5.5, Phase6, or AAAI claims. It keeps `static_flow_shield` as the primary learned/fulltheta UpdateParams baseline; `additive_ltm` remains the paper-faithful floor; stronger static variants remain diagnostics.

The round converts the G5.49 signal into a completed local region-to-policy gate sequence: G5.49 verification, signal semantics audit, true-region forensics, corrected fulltheta expansion replay (`68570` rows), active theta search (`50065` rows), safe expert-mixture offline policy evaluation, fresh targeted generated-theta replay (`30006` rows), blind gate skip, iteration-counterfactual label preflight, and final decision writing. The offline generator gate passed, but targeted replay produced `216` success regressions versus `static_flow_shield`, so SafeGate blocks blind/runtime promotion. The current decision is `g550_iteration_counterfactual_labels_needed_before_generator`.

## 2026-06-14 Repair5G.5.49 calibration/fulltheta update

G5.49 does not change LaCAM*/PIBT/search semantics and does not open runtime, Phase5.5, Phase6, or AAAI claims. It keeps `static_flow_shield` as the primary learned/fulltheta UpdateParams baseline; `additive_ltm` is the paper-faithful floor; stronger static variants are diagnostics.

The round produced calibrated-core development evidence: `8220` new calibration rows, `9780` cumulative finite-ratio rows, `30282` fulltheta replay rows, `18514` both-success pairs versus static_flow, and `10` true safe-gain regions. Coverage remains narrow (`4` unique evaluable strata, warehouse non-evaluable locally), so SafeGate status is `calibrated_core_subset_development_only`. The next valid step is generator model design / server-scale replay, not targeted/blind/runtime promotion.

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

### 12.1 Phase5 / Phase5.5 advanced architecture memo

来源：

```text
phase4f_repair2_advanced_update_rule_network_plan.md
```

该建议在 Repair2 当时用于替换 checkpoint-level MLP。Repair2 实测未通过 Phase4F gate，后续 Repair3 证明更关键的问题是 target formulation：大量 probe label 近 tie，使 hard best-rule label 不稳定。

因此后续若在 Phase5 / Phase5.5 重新启用高级模型，不应回到旧 hard target，而应沿用 Repair3 的 stable target formulation：

```text
stable target / tie-aware label
conservative additive fallback
safety-gated rule selection
```

2026-05-27 Repair5 更新后，上述判断只作为 Repair3/Repair4 的历史解释保留。Repair3 stable target 仍是 conservative baseline / compatibility metric，但不再作为后续高级 attention 模型的 primary training label。新的 primary label 见第 29 节：attention-native utility / opportunity / anti-escape labels。

高级模型和 stable target 曾经不是二选一：

```text
target formulation: defines what the model should learn
model architecture: defines how the model learns it
```

#### 12.1.1 Why MLP may still be limiting

Pro 建议中关于 MLP 限制的核心判断：

```text
The current model is LAU-MLP-v1.

Its effective learning problem is:

aggregate checkpoint features -> one best update rule

This is likely too weak for LAUR because choosing an LTM update rule depends on:

W_t: current traffic-map state
H_t: current iteration trace events
local bottlenecks / corridors / blocked regions
which candidate update rule is being evaluated
rule-family structure: additive / commit / block / wait / decay
near-ties between rules in short-budget probes

A single aggregate MLP loses most of this structure.
```

#### 12.1.2 Advanced model output must remain LAUR-compatible

后续高级模型不能变成 MAPF policy，也不能替换 PIBT。输出仍然只允许是 LTM update-rule / update-parameter family：

```text
input:
  checkpoint context + traffic-map tokens + trace/event tokens + candidate update-rule tokens

output:
  score for each candidate update rule
  harmful probability for each candidate update rule
  optional expected delta_ratio for each rule

selected update:
  safety-gated argmax over candidate update-rule scores
```

边界不变：

```text
Do not predict agent actions.
Do not replace PIBT.
Do not change LaCAM*/PIBT legality.
Do not change high-level LaCAM* search.
Only predict traffic-map update rule / update parameters.
```

#### 12.1.3 Primary candidate: LAU-EdgeTraceTransformer-v2

来自 Pro 建议的主架构：

```text
global_features
    -> global token encoder

edge_tokens
    -> edge token encoder
    -> type embedding + numeric projection + optional direction embedding

trace_tokens
    -> trace token encoder
    -> event kind embedding + count/numeric projection

rule_tokens
    -> rule token encoder
    -> rule family embedding + update-param numeric projection

context tokens = [global token, edge tokens, trace tokens]

Transformer encoder over context tokens

Rule-conditioned cross-attention:
    query = rule tokens
    key/value = context tokens

Rule-token self-attention:
    lets candidate rules compare against each other

Heads:
    q_delta_head(rule_token) -> expected delta_ratio score
    harmful_head(rule_token) -> harmful probability
    optional family_head(rule_token) -> family auxiliary logits
```

Pseudocode reference：

```python
class LAUEdgeTraceTransformerV2(nn.Module):
    def __init__(self, d_model=128, n_heads=4, n_layers=2):
        self.global_encoder = NumericEncoder(...)
        self.edge_encoder = EdgeTokenEncoder(...)
        self.trace_encoder = TraceTokenEncoder(...)
        self.rule_encoder = RuleTokenEncoder(...)

        self.context_encoder = nn.TransformerEncoder(...)
        self.rule_cross_attn = nn.MultiheadAttention(...)
        self.rule_self_attn = nn.TransformerEncoder(...)

        self.q_head = nn.Linear(d_model, 1)
        self.harmful_head = nn.Linear(d_model, 1)
        self.family_head = nn.Linear(d_model, num_families)

    def forward(batch):
        g = encode_global(batch.global_features)
        e = encode_edges(batch.edge_tokens)
        t = encode_trace(batch.trace_tokens)
        r = encode_rules(batch.rule_tokens)

        context = concat([g, e, t])
        context = context_encoder(context, key_padding_mask=context_mask)

        r2 = cross_attention(query=r, key=context, value=context)
        r2 = rule_self_attention(r2)

        q_delta = q_head(r2).squeeze(-1)
        harmful_logit = harmful_head(r2).squeeze(-1)

        return {
          "rule_score": q_delta,
          "harmful_logit": harmful_logit,
          "family_logits": family_head(r2)
        }
```

#### 12.1.4 Backup candidate: LAU-SetTransformer-v2

如果 raw trace tokenization 太慢、太重，或 EdgeTraceTransformer 过拟合，可用轻量 attention 模型：

```text
LAU-SetTransformer-v2

inputs:
  global token
  top-K traffic edge tokens
  top-K additive delta edge tokens
  rule tokens

architecture:
  edge token encoder
  Set Transformer / Transformer encoder over edge tokens
  pooling by multihead attention
  rule-conditioned cross-attention
  q_delta_head per rule
  harmful_head per rule
```

使用场景：

```text
raw trace zst is unavailable
trace tokenization is too slow
EdgeTraceTransformer overfits
GPU memory is too high
```

#### 12.1.5 Optional topology-biased attention

Pro 建议中有一个不引入 PyG 的 GAT-like bias：

```text
bias(i, j) =
  +b_shared_vertex if edge_i and edge_j share a vertex
  +b_reverse_edge if edge_i is reverse of edge_j
  +b_same_direction_corridor if directions align locally
  +b_nearby if endpoint distance <= 2
```

候选名：

```text
LAU-TopoEdgeAttention-v2
```

约束：

```text
pure PyTorch attention bias allowed
networkx preprocessing allowed
top-k sparse adjacency masks allowed
do not make PyTorch Geometric a Phase5 hard dependency
```

#### 12.1.6 Loss and rule selection for advanced model

后续高级模型不要只做 hard classifier，应直接利用 probe outcomes：

```text
score[rule] = predicted expected delta_ratio
harmful_logit[rule] = harmful probability
```

Loss 组件：

```text
L =
  lambda_listwise * listwise_kl_loss(score, soft_rule_target)
+ lambda_pairwise * pairwise_margin_ranking_loss(score, rule_delta_vector)
+ lambda_delta    * smooth_l1(score, rule_delta_vector)
+ lambda_safe     * per-rule_harmful_bce(harmful_logit, rule_harmful_vector)
+ lambda_family   * family_auxiliary_loss
+ lambda_additive * additive_fallback_regularization
```

Eval/runtime rule selection：

```python
score = model.rule_score
harmful_prob = sigmoid(model.harmful_logit)

allowed = harmful_prob < threshold
if not any(allowed):
    selected = additive_ltm
else:
    selected = argmax(score over allowed rules)
```

#### 12.1.7 Runtime export boundary

第一版 Phase5 应优先接入 Repair3 MLP，因为它已通过 offline gate、体积小、JSON export 简单、C++ 手写 forward 可控。

高级 attention 模型如果进入 Phase5.5 或后续 Phase6，应单独决定 runtime export：

```text
TorchScript
ONNX
Python service wrapper
C++ lightweight attention implementation
```

不要在 Phase5 parity 阶段强行解决 attention runtime export。

Phase5 第一优先级仍然是：

```text
--laur-disable parity
--laur-force-additive parity
conservative fallback smoke
closed-loop ablation
```

#### 12.1.8 2026-05-27 Phase5C 后的 stable-target attention 路线

Phase5C 已经证明 Repair3 MLP runtime 可以安全接入 solver loop，但没有在 smoke 中稳定优于普通 LTM。因此后续不应把 MLP 当作最终模型继续堆 runtime 实验；MLP 现在的定位是：

```text
safe engineering baseline
fallback/parity reference
closed-loop comparison reference
```

新的高级模型路线以用户提供的计划为准：

```text
phase4f5p5_stable_attention_lau_ltm_plan.md
```

该路线不是方向切换。它仍然属于 LAU-first：

```text
learn LTM UpdateLTM rule / update parameters
do not learn agent actions
do not replace PIBT
do not replace LaCAM*
do not learn restart before learned update is stable
```

命名约定：

```text
umbrella:  LAU-StableAttention-v1
primary:   LAU-SetRuleTransformer-v1
secondary: LAU-EdgeTraceTransformer-v3
optional:  LAU-TopoBiasAttention-v1
```

执行定位：

```text
Phase4F.4:
  historical first attempt: redo advanced update-rule models with Repair3 stable targets
  current Repair5 update: regenerate attention-native labels and anti-escape gates

Phase5.5-update:
  only after offline promotion gate and anti-escape gate, export and integrate the passing advanced update model
```

Promotion rule:

```text
If stable-target attention does not pass offline gate, do not implement C++ runtime.
If it passes offline but fails closed-loop smoke/pilot, report it as an advanced-model negative or partial result.
Do not use learned restart to hide an unstable learned update model.
```

Relationship to old Repair2:

```text
Repair2 attention failed before stable-target formulation became the central target.
Repair2 is not the final verdict on attention.
Any new attention attempt must not use Repair3 stable targets as the primary label.
It must compare against Repair3 MLP, but should train on the Repair5 attention-native label family in section 29.
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

## 15A. Phase4F.4 / Phase5.5-update：stable-target attention LAU

### 15A.1 Decision

This route is now an allowed next attempt after Phase5C.

2026-05-27 Repair5 supersession note: this section records the historical stable-target attention route. For new advanced attention attempts, Repair3 stable targets are baseline / compatibility targets only; the primary training target must be the Repair5 attention-native label family in section 29.

Reason:

```text
Phase5C MLP runtime is integrated safely, but it does not yet show solver-level learned benefit.
The next scientific question is whether a structured attention model can learn update-rule selection better than aggregate MLP features.
```

This route must remain LAU-compatible:

```text
LaGAT-inspired attention for LAU update-rule selection,
not LaGAT-style agent policy replacement.
```

Allowed:

```text
Repair3 stable target / tie-aware labels as baseline and compatibility metric
Repair5 attention-native labels as primary target for new runs
rule-conditioned attention
Set Transformer over global + top-K traffic edge tokens
compressed trace/event tokens if needed
topology-biased attention masks without PyG hard dependency
safety-gated fallback to additive_ltm
```

Not allowed:

```text
agent action prediction
PIBT replacement
LaCAM* high-level search replacement
candidate-domain changes
conflict-semantics changes
learned restart before learned update is stable
large raw trace commits
```

### 15A.2 Model sequence

Primary model:

```text
LAU-SetRuleTransformer-v1
```

Use it first because it is stronger than MLP but still plausibly exportable:

```text
global checkpoint token
top-K directed traffic edge tokens
candidate update-rule tokens
rule-conditioned cross-attention
q_delta head per rule
harmful head per rule
confidence/fallback head if useful
```

Secondary model:

```text
LAU-EdgeTraceTransformer-v3
```

Only attempt after SetRuleTransformer smoke works or if token evidence shows edge-set tokens are insufficient. It may remain offline-only unless runtime export is tractable.

Optional topology variant:

```text
LAU-TopoBiasAttention-v1
```

Use pure PyTorch masks / additive attention bias for:

```text
shared endpoint
reverse edge
same corridor direction
endpoint graph distance <= 2
```

### 15A.3 Dataset and target requirements

The dataset must expose both audit labels and stable labels:

```text
rule_class_original
rule_class_stable
rule_class_executable
best_minus_second_margin
best_minus_additive_margin
rule_delta_vector
rule_harmful_vector
soft_rule_target_stable
soft_rule_target_probe
```

Historical Repair3/Repair4 target:

```text
rule_class_stable
rule_delta_vector
rule_harmful_vector
```

Repair5 target, for any new advanced attention run:

```text
attention_native_target_rule
risk_adjusted_utility_vector
pairwise_dominance_matrix
safe_rule_mask
has_nonadditive_opportunity
has_high_margin_nonadditive_opportunity
defer_ltm meta-decision
anti_escape_candidate_mask
```

Executable rule vocabulary:

```text
additive_ltm
commit_heavy
block_heavy
block_light
wait_light
wait_heavy
decay_095
decay_090
```

`neutral_additive` may exist as a semantic stable target for audit, but execution maps it to `additive_ltm`.

### 15A.4 Offline gate

Do not lower the existing Phase4F gate:

```text
validation top1 >= 0.35
validation top3 >= 0.70
harmful recall >= 0.80
harmful precision >= 0.30
mean selected delta > 0.0
validation non-neutral checkpoints >= 50
```

Additional promotion conditions for stable attention:

```text
compare against Repair3 MLP seed-61
report seeds 61, 103, 107
top3 not worse than Repair3 MLP seed-61 by more than 0.02
harmful recall >= 0.80 for every reported seed
mean selected delta positive in aggregate, or positive for at least 2 of 3 seeds
no catastrophic per-map selected-delta failure
```

If this gate fails:

```text
stay in Phase4F.4
write negative/diagnostic report
do not implement Phase5.5 runtime
```

### 15A.5 Phase5.5-update runtime boundary

Only after the offline gate passes, decide runtime export.

Preferred:

```text
C++ JSON/CSV lightweight runtime for LAU-SetRuleTransformer-v1
```

Allowed fallback:

```text
ONNX Runtime smoke only if dependency is explicit and does not affect ordinary Phase5 tests
TorchScript/Python-service only as experimental report, not as final Phase5 gate
```

Required runtime behavior:

```text
--laur-disable -> exact LTM behavior
--laur-force-additive -> exact LTM through LAUR update path
missing model file -> fail loudly unless explicit fallback flag is set
unsupported rule -> additive fallback and logged reason
NaN prediction -> additive fallback and logged reason
all rules unsafe -> additive fallback and logged reason
low confidence -> additive fallback and logged reason
MLP runtime path remains available
```

### 15A.6 Phase5.5-update closed-loop smoke

Use the Phase5C smoke set and add attention methods:

```text
lacam_star_ltm
lacam_star_lau_ltm_force_additive
lacam_star_lau_ltm_mlp_repair3_safety
lacam_star_lau_ltm_attention_safety
lacam_star_lau_ltm_attention_no_safety
lacam_star_lau_ltm_attention_every_k2
lacam_star_lau_ltm_attention_every_restart
static_block_heavy
static_decay_095
```

Smoke gate:

```text
schema errors = 0
force-additive parity = true
attention runtime exercised = true
success count not lower than LTM
TTFS evaluable and not catastrophically worse
feature/model/total overhead reported
candidate domain unchanged by code audit
PIBT legality untouched by code audit
```

This gate is safety/engineering only. It does not prove learned benefit.

### 15A.7 Learned-benefit pilot gate

Only after Phase5.5 smoke passes, run paired pilot:

```text
baseline: lacam_star_ltm
contender: lacam_star_lau_ltm_attention_safety
reference: lacam_star_lau_ltm_mlp_repair3_safety
```

Phase5 learned-benefit for this route requires:

```text
success not lower than LTM
ratio mean <= LTM on paired successes, or dense/bottleneck subset clearly better while overall not worse
expanded_nodes not worse or equal-node ratio not worse
TTFS not catastrophically worse
policy overhead reported and not dominating runtime
paired deltas show a nonnegative trend, not one lucky seed
```

If 15A.4-15A.6 pass but 15A.7 fails:

```text
advanced LAU runtime integrated safely, but no learned-benefit claim yet
do not enter Phase6 learned-benefit main table
```

---

## 16. Optional Phase5.5：Full LAUR learned restart

Only start this after LAU-LTM passes Phase5 gate.

Naming note after the stable-attention update decision:

```text
Phase5.5-update = advanced learned UpdateLTM runtime path.
Phase5.5-restart / optional restart extension = learned restart-node policy.
```

If both are discussed in one report, keep them separate. Stable learned update must be evaluated before learned restart is promoted.

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
LaCAM*+LAU-LTM-attention
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

### 27.6 Repair3 conservative fallback calibration

继续对 seed `61`、`103`、`107` 做 safety fallback sweep。该诊断不改变 Phase4F exact-rule gate，只检查 safety head 是否能作为 Phase5 初始保守回退门。

候选策略：

```text
if harmful_update_probability >= 0.30:
    execute additive/neutral fallback
else:
    execute predicted update rule
```

共同阈值 `0.30` 在三个 seed 的 train/validation 上均满足 safety precision/recall 要求，并使 validation fallback 后 mean delta 为正：

```text
seed 61  validation: recall 0.8092, precision 0.4795, fallback 0.6362, mean delta after fallback 0.0064
seed 103 validation: recall 0.8150, precision 0.4747, fallback 0.6471, mean delta after fallback 0.0031
seed 107 validation: recall 0.8439, precision 0.4725, fallback 0.6732, mean delta after fallback 0.0014
```

结论：

- Phase4F 仍记录为 stable-target offline candidate pass。
- `0.30` 可作为 Phase5 第一个 conservative safety fallback threshold 候选。
- 该阈值回退率较高，只适合先做 runtime parity/smoke，不适合直接做性能声明。

---

## 28. 2026-05-27 Phase4F completion audit

完成一次 Phase4F completion audit：

```text
outputs/reports/phase4f_completion_audit.md
```

审计范围：只验收 Phase4F offline gate，不验收 Phase5 runtime。

当前 authoritative evidence：

```text
outputs/reports/phase4f_repair3_stable_tie001_performance_gate.json
outputs/reports/phase4f_repair3_stable_target_report.md
outputs/reports/phase4f_repair3_conservative_fallback_report.md
```

Phase4F offline gate 逐项结论：

```text
validation non-neutral = 293 >= 50 pass
rule top1 = 0.3899782135 >= 0.35 pass
rule top3 = 0.7690631808 >= 0.70 pass
harmful recall = 0.9421965318 >= 0.80 pass
harmful precision = 0.3908872902 >= 0.30 pass
predicted-rule mean delta = 0.0081308431 >= 0.0 pass
neutral/additive behavior documented pass
schema validation pass
git backup pass through commit 293ba8f
```

Completion decision：

```text
Phase4F offline stable-target pass, with Phase5 conservative fallback precondition.
```

该结论在当时只表示 Repair3 stable-target offline gate 可以关闭。2026-05-27 Repair5 更新后，若继续追求高级 neural attention learned update，则 Phase4F 需要以第 29 节的 attention-native label / anti-escape 口径重新打开；不得把 Repair3 offline pass 表述为 closed-loop learned runtime performance。

---

## 29. 2026-05-27 Phase4F Repair5：attention-native labels / anti-escape

### 29.1 Decision

采纳 GPTPro `phase4f_repair5_attention_native_labels_codex_plan.md` 的核心建议，并覆盖第 12.1.8 / 15A 中“继续以 Repair3 stable target 作为高级 attention primary label”的旧假设。

Repair3 不被否定，但定位调整为：

```text
offline-pass conservative baseline
Phase5C runtime/parity baseline
fallback reference
compatibility metric
```

Repair3 stable target 不能再作为后续高级 neural attention 模型的主训练目标。原因是：

```text
Repair3 的通过主要来自 stable target / tie handling，而不是强 learned update。
Repair3 tie policy 明显偏向 additive_ltm fallback。
Phase5C 没有证明 Repair3 MLP runtime 稳定优于普通 LTM。
Repair4 继承 Repair3 label 后虽有 ranking/delta 信号，但 safety tradeoff 未过，且仍有 additive/fallback 倾向。
继续堆 Transformer 很可能得到更复杂的 fallback classifier，而不是更强的 learned UpdateLTM policy。
```

Repair5 的研究目标改为：

```text
not: learn to pass the offline gate conservatively
yes: learn when a non-additive LTM update is genuinely safe and useful
```

### 29.2 Scope

Repair5 仍属于 LAU / LAUR-LTM 主线：

```text
LaCAM* + LTM
  -> teacher/probe/checkpoint/trace
  -> learned UpdateLTM policy
  -> C++ runtime parity/smoke only after all gates pass
```

Allowed:

```text
redesign Phase4F label
regenerate dataset
train rule-conditioned / edge-trace attention model
use Repair1 checkpoints/probes/raw trace
use Repair3 / Phase5C MLP runtime as baseline
add anti-escape evaluation
```

Not allowed:

```text
agent action prediction
PIBT replacement
LaCAM* conflict semantics changes
candidate action domain changes
incumbent pruning / rewrite changes
learned restart
validation/test threshold tuning
lowering any Phase4F gate
counting defer/additive as non-additive learning success
calling smoke/parity a Phase6-scale performance claim
```

### 29.3 Attention-native label schema

New schema:

```text
phase4_laur_attention_native_label_dataset_v1
```

Primary label family:

```text
per-rule risk-adjusted utility
pairwise rule dominance matrix
per-rule harmful labels
safe rule masks
non-additive opportunity labels
explicit defer_ltm meta-decision
high-margin safe-opportunity slices
anti-escape supervision masks
```

Executable rule vocabulary stays unchanged:

```text
additive_ltm
commit_heavy
block_heavy
block_light
wait_light
wait_heavy
decay_095
decay_090
```

`defer_ltm` is not an executable rule. Runtime maps it to `additive_ltm`; evaluation must count it separately and must not count it as non-additive learning success.

### 29.4 Utility and opportunity definitions

Per rule:

```text
delta_i = delta_ratio_vs_additive(rule_i)
harmful_i = harmful(rule_i)
success_i = success(rule_i) if available, else true
ttfs_regression_i = ttfs_regression_ratio(rule_i) if available, else 1.0
delta_additive = 0.0
```

Risk-adjusted utility:

```text
utility_i =
    delta_i
  - harm_penalty * I[harmful_i]
  - failure_penalty * I[success_i == false]
  - ttfs_penalty * max(0, ttfs_regression_i - 1.0)
```

Initial parameters:

```yaml
harm_penalty: 0.050
failure_penalty: 0.100
ttfs_penalty: 0.010
utility_clip_min: -0.100
utility_clip_max: 0.100
opportunity_margin: 0.010
high_margin_opportunity_margin: 0.020
pairwise_margin: 0.005
softmax_temperature: 0.010
harmful_floor: -0.050
```

Safe mask:

```text
safe_i = success_i && !harmful_i
```

If `harmful_i` is missing, treat `safe_i = false` and report missing coverage. Do not invent better labels from missing evidence.

Non-additive opportunity:

```text
best_safe_nonadditive =
    argmax_i utility_i where i != additive_ltm and safe_i

best_safe_nonadditive_advantage =
    utility_best_safe_nonadditive - utility_additive

has_nonadditive_opportunity =
    exists safe non-additive rule with
      utility_i - utility_additive >= 0.010
      and utility_i > 0.000

has_high_margin_nonadditive_opportunity =
    exists safe non-additive rule with
      utility_i - utility_additive >= 0.020
      and utility_i > 0.000
```

Defer decision:

```text
if no safe non-additive exists:
    decision_target = defer_ltm
    defer_reason = all_nonadditive_unsafe
elif best_safe_nonadditive_advantage < 0:
    decision_target = defer_ltm
    defer_reason = additive_is_best_safe
elif 0 <= best_safe_nonadditive_advantage < opportunity_margin:
    decision_target = defer_ltm
    defer_reason = ambiguous_low_margin
else:
    decision_target = use_nonadditive
    target_rule = best_safe_nonadditive
```

### 29.5 Label variants

Run Repair5 as a controlled comparison, not a single label guess:

```text
R5-A: risk_adjusted_listwise
R5-B: pairwise_dominance / RankNet
R5-C: opportunity_first two-stage
R5-A+C combined
R5-B+C combined
R5-D: trace-credit auxiliary, optional only
R5-E: defer-as-policy, required with A/B/C when possible
```

Model priority:

```text
1. LAU-EdgeTraceTransformer-v4
2. LAU-SetRuleTransformer-v2
3. LAU-TopoBiasAttention-v1 optional
```

Seeds:

```text
61
103
107
```

### 29.6 Original gates remain

Do not lower the existing Phase4F gate:

```text
validation top1 >= 0.35
validation top3 >= 0.70
harmful recall >= 0.80
harmful precision >= 0.30
mean selected delta > 0.0
validation non-neutral checkpoints >= 50
schema validation pass
split leakage == 0
```

For Repair5, top1/top3 are computed against the attention-native target. Also report compatibility metrics against Repair3 stable target, but those are not the primary pass condition.

### 29.7 Anti-escape gate

New required report:

```text
outputs/reports/phase4f_repair5_anti_escape_gate_summary.json
```

Definitions:

```text
opportunity_sample =
    has_nonadditive_opportunity == true

high_margin_opportunity_sample =
    has_high_margin_nonadditive_opportunity == true

captured_opportunity =
    selected_rule != additive_ltm
    and selected_decision != defer_ltm
    and selected_rule is safe
    and selected_delta - additive_delta >= opportunity_margin
```

Required metrics:

```text
validation_opportunity_count
validation_high_margin_opportunity_count
nonadditive_capture_rate
high_margin_nonadditive_capture_rate
avoidable_additive_fallback_rate
avoidable_defer_rate
anti_escape_mean_selected_vs_additive_delta
global_additive_or_defer_rate
opportunity_additive_or_defer_rate
selected_rule_distribution
decision_distribution
```

Initial thresholds:

```yaml
min_validation_high_margin_opportunity_count: 50
high_margin_nonadditive_capture_rate_min: 0.40
avoidable_additive_or_defer_rate_max: 0.60
anti_escape_mean_selected_vs_additive_delta_min: 0.005
opportunity_nonadditive_selection_rate_min: 0.35
global_additive_or_defer_rate_max: 0.70
```

If high-margin opportunity count `< 50`, anti-escape is inconclusive and Phase5.5 runtime is forbidden until the probe/validation evidence is expanded or regenerated.

### 29.8 Implementation tasks

Add Repair5 as a new experimental line; do not delete Repair3/Repair4 code.

```text
src/czr004_teacher/attention_native_labels_laur.py
src/czr004_teacher/attention_native_schema_laur.py
src/models/laur_attention_native.py
src/train/losses_laur_attention_native.py
src/train/train_laur_attention_native.py
src/eval/eval_laur_attention_native.py
src/eval/eval_laur_anti_escape.py
src/eval/eval_laur_repair5_final_gate.py
configs/phase4/laur_ltm_full_repair5_attention_native_labels.yaml
tests/test_phase4f_attention_native_labels.py
tests/test_phase4f_attention_native_eval.py
```

Required outputs:

```text
outputs/reports/phase4f_repair5_attention_native_label_audit.md
outputs/reports/phase4f_repair5_attention_native_label_audit.json
outputs/reports/phase4f_repair5_attention_native_eval_seed61.md
outputs/reports/phase4f_repair5_attention_native_eval_seed103.md
outputs/reports/phase4f_repair5_attention_native_eval_seed107.md
outputs/reports/phase4f_repair5_anti_escape_report.md
outputs/reports/phase4f_repair5_anti_escape_gate_summary.json
outputs/reports/phase4f_repair5_final_gate_summary.json
```

### 29.9 Runtime promotion rule

Repair5 runtime is allowed only if all required gates pass:

```text
runtime_allowed =
    original_phase4f_gate.pass
    and attention_native_phase4f_gate.pass
    and safety_gate.pass
    and anti_escape_gate.pass
    and multi_seed_gate.pass
```

If original Phase4F gate passes but anti-escape fails:

```text
runtime_allowed = false
conclusion = model still escapes to LTM/additive
```

If anti-escape passes but safety fails:

```text
runtime_allowed = false
conclusion = non-additive learning unsafe
```

If all gates pass:

```text
runtime_allowed = true for Phase5.5 parity/smoke only
not a Phase6-scale performance claim
```

The current raw-trace Repair5 edge-trace job may remain useful as an intermediate diagnostic, but the accepted next plan is attention-native Repair5 if stable-target raw-trace attention still fails or shows additive escape.

### 29.10 Current execution status - 2026-05-27 20:45 +08:00

Repair5 attention-native implementation is now running as the active advanced-model route.

Completed local/remote setup:

```text
label audit:
  outputs/reports/phase4f_repair5_attention_native_label_audit.json
  samples = 2985
  train / validation = 2526 / 459
  schema_errors = 0
  split_leakage = 0
  validation_high_margin_opportunity_count = 185
  passed = true

negative local diagnostic:
  seed61, 40 epochs, LAU-SetRuleTransformer-v2
  top1 = 0.2116 < 0.35
  top3 = 0.6688 < 0.70
  harmful_recall = 0.7689 < 0.80
  harmful_precision = 0.2847 < 0.30
  high_margin_nonadditive_capture = 0.3514 < 0.40
  conclusion = not Phase5.5 eligible
```

Server long run:

```text
server workspace:
  /root/shared-nvme/czr004_phase4_repair1_43633e7

tmux:
  repair5_attn_native_20260527

main log:
  outputs/logs/phase4f_repair5_attention_native_pipeline_20260527_204507.log

script:
  run_repair5_attention_native_pipeline.sh

sequence:
  1. LAU-SetRuleTransformer-v2, seeds 61/103/107, 160 epochs each
  2. eval each seed with safety calibration and anti-escape report
  3. run Repair5 final multi-seed gate
  4. if final gate fails, regenerate raw-trace attention-native labels
     and run LAU-EdgeTraceTransformer-v4, seeds 61/103/107
```

Raw-trace attention-native fallback:

```text
config:
  configs/phase4/laur_ltm_full_repair5_attention_native_rawtrace_edge.yaml

raw trace:
  artifacts/teacher/laur/full_repair1/traces/phase4_laur_trace_full_repair1.jsonl.zst

important boundary:
  raw trace is used only as richer Repair5 attention-native token evidence.
  It is not a return to Repair3 stable-target primary labels.
  It does not predict agent actions, replace PIBT/LaCAM*, or introduce learned restart.
```

### 29.11 Current execution status - 2026-05-28 08:45 +08:00

Repair5 remains active, but no runtime promotion is allowed yet.

Completed evidence:

```text
set-rule attention-native final gate:
  outputs/reports/phase4f_repair5_final_gate_summary.json
  runtime_allowed = false
  phase5p5_allowed = false
  phase6_allowed = false
  conclusion = non-additive learning unsafe

raw-trace edge attention final gate:
  outputs/reports/phase4f_repair5_rawtrace_edge_final_gate_summary.json
  runtime_allowed = false
  phase5p5_allowed = false
  phase6_allowed = false
  conclusion = non-additive learning unsafe

raw-trace label audit:
  outputs/reports/phase4f_repair5_attention_native_rawtrace_label_audit.json
  label audit passed

safety-focused seed61 sweep:
  outputs/logs/phase4f_repair5_rawtrace_safety_sweep_20260528_080336.log
```

Safety sweep summary:

| variant | top1 | top3 | harmful recall | harmful precision | anti-escape | result |
|---|---:|---:|---:|---:|---|---|
| `sf_hpw1_lh8` | 0.211604 | 0.593857 | 0.132723 | 0.337209 | pass | fail original/attention/safety |
| `sf_hpw2_lh8` | 0.191126 | 0.645051 | 0.231121 | 0.293605 | pass | fail original/attention/safety |
| `sf_hpw1_lh12` | 0.242321 | 0.655290 | 0.075515 | 0.308411 | pass | fail original/attention/safety |

Interpretation:

```text
Anti-escape can be made to pass, but the harmful head still cannot maintain
high recall and high precision together while preserving top3 ranking.
This is a negative result, not a promotion signal.
```

Repair5 next attempt now running:

```text
tmux:
  repair5_pairwise_waiter_20260528

log:
  outputs/logs/phase4f_repair5_pairwise_waiter_20260528_083008.log
  outputs/logs/phase4f_repair5_pairwise_resume_20260528_084526.log

new local/remote change:
  harmful safety pairwise-margin loss
  gate-balanced checkpoint selection
  optional calibrated-safety checkpoint selection

local tests:
  tests/test_phase4f_attention_native_eval.py
  tests/test_phase4f_attention_native_labels.py
  result: 12 passed

generated configs:
  configs/phase4/generated_repair5_pairwise/sf_pair_focal_m035_lh4.yaml
  configs/phase4/generated_repair5_pairwise/sf_pair_m035_lh4_neg1.yaml
  configs/phase4/generated_repair5_pairwise/sf_pair_m050_lh3_neg2.yaml
```

First pairwise seed61 result:

| variant | top1 | top3 | harmful recall | harmful precision | anti-escape | result |
|---|---:|---:|---:|---:|---|---|
| `sf_pair_focal_m035_lh4` | 0.180887 | 0.662116 | 0.816934 | 0.281768 | fail | fail attention/safety/anti |

This is a useful diagnostic because the new safety-balanced checkpoint selection preserved high recall better than the prior late anti-only checkpoints, but it still does not pass the gate.

Promotion boundary remains unchanged:

```text
Do not enter Phase5.5 until original Phase4F gate, attention-native gate,
safety gate, anti-escape gate, and multi-seed gate all pass.
Do not enter Phase6 from offline Repair5 evidence alone.
```

Promotion remains forbidden unless all of the following pass:

```text
original Phase4F gate
attention-native gate
safety gate
anti-escape gate
multi-seed gate
```

Phase5.5, if unlocked, is parity/smoke only. Phase6 still requires separate closed-loop learned-benefit evidence.

### 29.12 Current execution status - 2026-05-28 09:30 +08:00

Repair5 is still active. No runtime promotion is allowed.

Completed additional negative evidence:

```text
pairwise recovery log:
  outputs/logs/phase4f_repair5_pairwise_resume_20260528_084526.log

pairwise seed61:
  sf_pair_focal_m035_lh4:
    top1 = 0.180887
    top3 = 0.662116
    harmful recall = 0.816934
    harmful precision = 0.281768
    anti_escape = false
  sf_pair_m035_lh4_neg1:
    top1 = 0.208191
    top3 = 0.641638
    harmful recall = 0.684211
    harmful precision = 0.311458
    anti_escape = false
  sf_pair_m050_lh3_neg2:
    top1 = 0.153584
    top3 = 0.682594
    harmful recall = 0.743707
    harmful precision = 0.294918
    anti_escape = false

result:
  no seed61 promotion
  no Phase5.5
  no Phase6
```

Global-safety sweep is running:

```text
tmux:
  repair5_global_safety_waiter_20260528

log:
  outputs/logs/phase4f_repair5_global_safety_waiter_20260528_085606.log

first completed seed61 variant:
  sf_global_pair_neg2_anti2
  outputs/reports/phase4f_repair5_rawtrace_edge_sf_global_pair_neg2_anti2_eval_seed61_summary.json
  outputs/reports/phase4f_repair5_rawtrace_edge_sf_global_pair_neg2_anti2_anti_escape_gate_seed61_summary.json

metrics:
  top1 = 0.232082
  top3 = 0.706485
  harmful recall = 0.576659
  harmful precision = 0.313433
  anti_escape = true

result:
  top3 / precision / anti_escape improved
  top1 and harmful recall failed
  no promotion
```

The next queued Repair5 attempt adds target-rule pressure without changing gates:

```text
new optional loss terms:
  attention-native target-rule CE
  target-rule margin
  high-margin opportunity weighting for target-rule losses

default behavior:
  lambda_rule_ce = 0
  lambda_rule_margin = 0
  existing configs unchanged unless a generated Repair5 variant enables the terms

tests:
  local Repair5 tests = 15 passed
  remote Repair5 tests = 15 passed
```

Queued tmux:

```text
tmux:
  repair5_target_rule_margin_waiter_20260528

log:
  outputs/logs/phase4f_repair5_target_rule_margin_waiter_20260528_0930.log

script:
  run_repair5_target_rule_margin_waiter.sh

behavior:
  waits for repair5_global_safety_waiter_20260528
  runs seed61 first
  promotes to seeds 103/107 only if seed61 passes all required gates

generated configs:
  configs/phase4/generated_repair5_target_rule_margin/sf_target_ce1_margin1_hm4.yaml
  configs/phase4/generated_repair5_target_rule_margin/sf_target_ce2_margin1_hm3.yaml
  configs/phase4/generated_repair5_target_rule_margin/sf_target_margin2_rank3_safe5.yaml
```

Promotion boundary remains unchanged:

```text
Phase5.5 allowed only after original Phase4F gate,
attention-native gate, safety gate, anti-escape gate,
and multi-seed gate all pass.

Phase6 still requires separate closed-loop learned-benefit evidence.
```

### 29.13 Data-volume branch queued - 2026-05-28 10:00 +08:00

Repair5 remains active. No runtime promotion is allowed.

The current data-volume diagnosis is:

```text
raw-trace attention-native audit:
  total rows ~= 2985
  train rows ~= 2526
  validation rows ~= 459
  validation use_nonadditive rows ~= 293
  validation high-margin opportunity rows ~= 185

interpretation:
  data volume / opportunity coverage is a plausible blocker
  it is not a success claim
```

Global-safety sweep completed with no seed61 promotion:

```text
log:
  outputs/logs/phase4f_repair5_global_safety_waiter_20260528_085606.log

sf_global_pair_neg2_anti2:
  top1 = 0.232082
  top3 = 0.706485
  harmful recall = 0.576659
  harmful precision = 0.313433
  anti_escape = true
  result = fail top1 + safety recall

sf_global_pair_rank2_anti2:
  top1 = 0.187713
  top3 = 0.689420
  harmful recall = 0.745995
  harmful precision = 0.290036
  anti_escape = false
  result = fail attention/safety/anti

sf_global_rank3_anti3:
  top1 = 0.184300
  top3 = 0.689420
  harmful recall = 0.814645
  harmful precision = 0.275116
  anti_escape = false
  result = fail attention/safety precision/anti
```

The target-rule queue is active:

```text
tmux:
  repair5_target_rule_margin_waiter_20260528

log:
  outputs/logs/phase4f_repair5_target_rule_margin_waiter_20260528_0930.log

latest observed:
  sf_target_ce1_margin1_hm4 reached epoch 200
  selected validation metrics still below gate
  no promotion evidence yet
```

A 5000+ sample data branch is queued after the target-rule run:

```text
new configs:
  configs/phase4/laur_ltm_repair5_expand5000_scenario_manifest.jsonl
  configs/phase4/laur_ltm_full_repair5_expand5000.yaml
  configs/phase4/laur_ltm_full_repair5_attention_native_expand5000_rawtrace_edge.yaml

scope:
  instances = 1..25
  runs = 1275
  max checkpoints/probe rows ~= 5100
  outputs are under repair5_expand5000 paths
  original 2985-row evidence is preserved
```

Queued tmux:

```text
tmux:
  repair5_expand5000_waiter_20260528

log:
  outputs/logs/phase4f_repair5_expand5000_waiter_20260528.log

script:
  run_repair5_expand5000_waiter_20260528.sh

behavior:
  waits for repair5_target_rule_margin_waiter_20260528
  runs record/probe on the 25-instance config
  builds attention-native raw-trace labels
  audits expanded label distribution
  screens seed61 first for three variants
```

Generated expanded-data variants will be:

```text
configs/phase4/generated_repair5_expand5000/ex5000_mlp_target_global.yaml
configs/phase4/generated_repair5_expand5000/ex5000_linear_target_global.yaml
configs/phase4/generated_repair5_expand5000/ex5000_mlp_safety_light.yaml
```

Code and verification:

```text
new optional attention model head:
  head_hidden_dim
  head_dropout

default:
  head_hidden_dim = 0
  previous linear-head behavior is preserved

tests:
  local Repair5 tests = 16 passed, 1 warning
  remote Repair5 tests = 16 passed, 1 warning
```

Promotion boundary remains unchanged:

```text
No gate was lowered.
Phase5.5 remains forbidden.
Phase6 remains forbidden.
Only original Phase4F + attention-native + safety + anti-escape + multi-seed can unlock Phase5.5 parity/smoke.
```

### 29.14 Target-rule partial result and expanded-audit diagnostic - 2026-05-28 10:20 +08:00

Repair5 remains active. No runtime promotion is allowed.

The target-rule CE/margin queue has produced two formal seed61 negatives:

```text
sf_target_ce1_margin1_hm4:
  top1 = 0.191126
  top3 = 0.709898
  harmful recall = 0.745995
  harmful precision = 0.255686
  mean delta = 0.004458
  anti_escape = false
  result = no promotion

sf_target_ce2_margin1_hm3:
  top1 = 0.143345
  top3 = 0.706485
  harmful recall = 0.787185
  harmful precision = 0.277868
  mean delta = 0.002751
  anti_escape = false
  result = no promotion
```

The third target-rule variant is still training:

```text
sf_target_margin2_rank3_safe5:
  active under tmux repair5_target_rule_margin_waiter_20260528
  by epoch 80 there was no positive gate evidence
```

Observed pattern:

```text
target-rule pressure can make top3 pass on some checkpoints
but on the 2985-row dataset it still does not align top1,
safety, positive delta, and anti-escape at the same selected checkpoint
```

An audit-only diagnostic was added before expand5000 label generation:

```text
file:
  src/czr004_teacher/attention_native_schema_laur.py

new summary field:
  split_diagnostics

contains per split:
  sample_count
  decision_distribution
  target_rule_distribution
  defer_reason_distribution
  nonadditive_opportunity_count
  high_margin_nonadditive_opportunity_count
```

This does not change labels, training, eval, or gates. It only makes the expanded-data label audit stronger.

Verification:

```text
local Repair5 tests = 16 passed, 1 warning
remote Repair5 tests = 16 passed, 1 warning
```

Current remote queue:

```text
active:
  repair5_target_rule_margin_waiter_20260528

waiting:
  repair5_expand5000_waiter_20260528
```

Promotion boundary remains unchanged:

```text
No gate was lowered.
Phase5.5 remains forbidden.
Phase6 remains forbidden.
```

### 29.15 Target-rule completed; expand5000 active; high-token queued - 2026-05-28 10:40 +08:00

Repair5 remains active. No runtime promotion is allowed.

The target-rule CE/margin queue is now complete, with no seed61 promotion:

```text
sf_target_ce1_margin1_hm4:
  top1 = 0.191126
  top3 = 0.709898
  harmful recall = 0.745995
  harmful precision = 0.255686
  mean delta = 0.004458
  anti_escape = false

sf_target_ce2_margin1_hm3:
  top1 = 0.143345
  top3 = 0.706485
  harmful recall = 0.787185
  harmful precision = 0.277868
  mean delta = 0.002751
  anti_escape = false

sf_target_margin2_rank3_safe5:
  top1 = 0.221843
  top3 = 0.689420
  harmful recall = 0.814645
  harmful precision = 0.270517
  mean delta = 0.003933
  anti_escape = false
```

Conclusion:

```text
target-rule pressure can pass top3 or recall separately,
but it still does not satisfy top1, safety precision,
positive utility, and anti-escape together
```

The expanded-data run is now active:

```text
tmux:
  repair5_expand5000_waiter_20260528

log:
  outputs/logs/phase4f_repair5_expand5000_waiter_20260528.log

status at 2026-05-28 10:35 +08:00:
  record/probe stage active
  record logs = 372
  checkpoint rows = 738
  probe rows = not started yet
  disk free ~= 93G
```

Compression decision:

```text
zstd compression is lossless
compressed raw trace does not remove trace events
information bottleneck is tokenization/truncation, not compression
```

Therefore the next information-capacity branch keeps zstd but increases token budgets:

```text
config:
  configs/phase4/laur_ltm_full_repair5_attention_native_expand5000_rawtrace_hightoken.yaml

tokenization:
  max_edge_tokens = 96
  max_trace_tokens = 256

training:
  batch_size = 64
```

Queued high-token tmux:

```text
tmux:
  repair5_expand5000_hightoken_waiter_20260528

log:
  outputs/logs/phase4f_repair5_expand5000_hightoken_waiter_20260528.log

script:
  run_repair5_expand5000_hightoken_waiter_20260528.sh

behavior:
  waits for repair5_expand5000_waiter_20260528
  rebuilds high-token labels from the same compressed raw trace
  audits split/rule/opportunity coverage
  screens seed61 first
```

Generated high-token variants:

```text
configs/phase4/generated_repair5_expand5000_hightoken/ht_mlp_target_global.yaml
configs/phase4/generated_repair5_expand5000_hightoken/ht_linear_target_global.yaml
```

Promotion boundary remains unchanged:

```text
No gate was lowered.
Phase5.5 remains forbidden.
Phase6 remains forbidden.
```

### 29.16 Expand5000 sleep-check - 2026-05-28 10:50 +08:00

Repair5 remains active. No runtime promotion is allowed.

Remote health check:

```text
tmux alive:
  repair5_expand5000_waiter_20260528
  repair5_expand5000_hightoken_waiter_20260528

disk:
  100G total
  8.3G used
  92G free

GPU:
  RTX 4090 idle
```

This is expected because expand5000 is still generating record/probe data.
The neural-network training stage has not started yet.

Expand5000 progress at 2026-05-28 10:47 +08:00:

```text
record log files = 428
approx completed record commands = 214
checkpoint rows = 835
compressed raw trace = 1.46GB
probe rows = not started yet
normal-token label dataset = not generated yet
high-token label dataset = not generated yet
```

Error scan:

```text
searched:
  Traceback
  Exception
  ERROR
  FAILED
  No space
  Killed
  CUDA out of memory

result:
  no matching failure lines
  recent record stderr files empty
```

Recent record stdout contains both successful and infeasible MAPF samples.
Those are valid teacher-data outcomes, not process crashes.

Local Repair5 verification was rerun in the correct conda environment:

```text
conda run -n czr004 python -m pytest \
  tests/test_phase4f_attention_native_eval.py \
  tests/test_phase4f_attention_native_labels.py -q

result:
  16 passed, 1 warning
```

Compression status:

```text
zstd is lossless
turning compression off does not expose extra trace events
more raw-trace information is tested by increasing token budgets
```

Promotion boundary remains unchanged:

```text
No gate was lowered.
Phase5.5 remains forbidden.
Phase6 remains forbidden.
```

### 29.21 Final-gate explicit-field hardening - 2026-05-28 13:42 +08:00

Repair5 remains active. No runtime promotion is allowed.

While the expand5000 branch remained in the late probe tail, the queued waiters were prechecked:

```text
scripts:
  run_repair5_expand5000_waiter_20260528.sh
  run_repair5_expand5000_hightoken_waiter_20260528.sh
  run_repair5_expand5000_followup_waiter_20260528.sh
  run_repair5_progress_monitor_20260528.sh

remote validation:
  bash -n passed for all scripts
  required Repair5 configs and Python modules were present
```

The final gate was hardened:

```text
file:
  src/eval/eval_laur_repair5_final_gate.py

change:
  do not fallback missing top-level phase4f_gate to validation attention_native_gate
  do not fallback missing validation attention_native_gate to phase4f_gate
  do not fallback missing top-level anti_escape_gate to validation metrics
  record missing_required_gate_fields per seed result
```

Reason:

```text
The objective requires explicit evidence for:
  original Phase4F gate
  attention-native gate
  safety gate
  anti-escape gate
  multi-seed gate

If an eval summary is malformed or incomplete, final gate must fail loudly rather than infer a pass from a neighboring field.
```

Tests added:

```text
missing phase4f_gate fails final gate
missing metrics_by_split.validation.attention_native_gate fails final gate
```

Verification:

```text
local:
  tests/test_phase4f_attention_native_labels.py
  tests/test_phase4f_attention_native_eval.py
  result = 21 passed, 1 warning

remote:
  tests/test_phase4f_attention_native_labels.py
  tests/test_phase4f_attention_native_eval.py
  result = 21 passed, 1 warning
```

Promotion boundary remains unchanged:

```text
No gate was lowered.
Phase5.5 remains forbidden.
Phase6 remains forbidden.
```

Final lightweight remote status at 2026-05-28 13:42 +08:00:

```text
probe log files = 2068
probe rows = 32648 and increasing
active process = phase4_laur_probe at about 99.8% CPU
label datasets = not generated yet
expand5000 summaries = not generated yet
error scan = clean
```

### 29.22 Expand5000 recovery after script failures - 2026-05-28 18:42 +08:00

Repair5 remains active. No runtime promotion is allowed.

Remote state at 2026-05-28 18:35 +08:00:

```text
record log files = 2550
probe log files = 2550
checkpoint rows = 4956
probe rows = 40360
disk = 100G total, 13G used, 88G free
GPU = idle
```

Main normal-token waiter failed after data generation:

```text
log:
  outputs/logs/phase4f_repair5_expand5000_waiter_20260528.log

failure:
  scripts/run_phase4_laur_batch.py completed record/probe artifacts
  then failed while writing the batch report

exception:
  AttributeError: 'NoneType' object has no attribute 'get'

effect:
  normal-token attention-native label dataset/audit was not built

interpretation:
  data-generation succeeded
  this is a report/write-path failure, not a teacher-data failure
```

High-token branch status:

```text
label audit:
  outputs/reports/phase4f_repair5_attention_native_expand5000_rawtrace_hightoken_label_audit.json
  passed = true
  sample_count = 4956
  train / validation = 4194 / 762
  validation high-margin opportunity count = 310
  validation non-additive opportunity count = 483

training:
  did not actually start
  generated configs used unknown model name:
    LAU-EdgeTraceTransformer-v4-high-token
  error:
    ValueError: unknown LAU attention-native model

interpretation:
  this is a config naming bug, not a negative model result
```

Follow-up waiter status:

```text
log:
  outputs/logs/phase4f_repair5_expand5000_followup_waiter_20260528.log

result:
  failed fast because normal-token dataset/audit was missing
  no follow-up variants were evaluated
```

Fix:

```text
file:
  configs/phase4/laur_ltm_full_repair5_attention_native_expand5000_rawtrace_hightoken.yaml

change:
  model.name = LAU-EdgeTraceTransformer-v4

note:
  high-token is a tokenization/data-capacity variant
  it is not a new architecture name
```

Recovery queued:

```text
script:
  run_repair5_expand5000_recovery_20260528.sh

tmux:
  repair5_expand5000_recovery_20260528

log:
  outputs/logs/phase4f_repair5_expand5000_recovery_20260528.log

remote validation:
  bash -n passed
  hightoken model name check passed

sequence:
  rerun normal-token waiter
    skip completed record/probe artifacts
    build normal-token labels
    screen seed61 variants
  rerun high-token waiter
    reuse existing high-token labels
    regenerate configs with corrected model name
    screen seed61 variants
  rerun follow-up waiter
```

Liveness at 2026-05-28 18:41 +08:00:

```text
active process:
  attention_native_labels_laur.py
  config = configs/phase4/laur_ltm_full_repair5_attention_native_expand5000_rawtrace_edge.yaml
  CPU about 100%

trace aggregation progress:
  rows = 10,000,000
  matched = 9,999,999
  checkpoints = 713

normal-token dataset/audit:
  not finished yet
```

Promotion boundary remains unchanged:

```text
No gate was lowered.
High-token failed attempt is not counted as a model negative because no model was trained.
Phase5.5 remains forbidden.
Phase6 remains forbidden.
```

### 29.20 Expand5000 probe-stage health check - 2026-05-28 13:35 +08:00

Repair5 remains active. No runtime promotion is allowed.

Remote progress at 2026-05-28 13:32 +08:00:

```text
tmux alive:
  repair5_expand5000_waiter_20260528
  repair5_expand5000_hightoken_waiter_20260528
  repair5_expand5000_progress_monitor_20260528
  repair5_expand5000_followup_waiter_20260528

disk:
  100G total
  13G used
  88G free

GPU:
  RTX 4090 idle

record log files = 2550
record phase = complete for 1275 runs
checkpoint rows = 4956
compressed raw trace = 6.08GB

probe log files = 2034
approx completed probe commands = 1017 / 1275
probe rows = 32136 and increasing

label datasets = not generated yet
expand5000 summaries = not generated yet
```

Liveness evidence:

```text
active process:
  phase4_laur_probe
  about 99.9% CPU

latest probe logs:
  clean stdout/stderr
  still emitting probe_rows for warehouse-20-40-10-2-1 cases

error scan:
  clean
```

Interpretation:

```text
The job is slow in the late probe tail, not stuck.
No expand5000 label audit, train result, anti-escape result, or final gate exists yet.
The queued normal-token, high-token, and follow-up branches remain valid waiters.
```

Promotion boundary remains unchanged:

```text
No gate was lowered.
Phase5.5 remains forbidden.
Phase6 remains forbidden.
```

### 29.17 Expand5000 progress monitor - 2026-05-28 11:01 +08:00

Repair5 remains active. No runtime promotion is allowed.

Remote progress at 2026-05-28 10:58 +08:00:

```text
tmux alive:
  repair5_expand5000_waiter_20260528
  repair5_expand5000_hightoken_waiter_20260528

disk:
  100G total
  9.0G used
  91G free

GPU:
  RTX 4090 idle

record log files = 484
approx completed record commands = 242
checkpoint rows = 934
compressed raw trace = 2.25GB
probe rows = not started yet
label datasets = not generated yet
```

The record-log error scan remains clean:

```text
no Traceback / Exception / ERROR / FAILED / No space / Killed / CUDA OOM
```

A lightweight monitor tmux was started:

```text
tmux:
  repair5_expand5000_progress_monitor_20260528

log:
  outputs/logs/phase4f_repair5_expand5000_progress_monitor_20260528.log

cadence:
  every 10 minutes, up to 96 samples
```

First monitor sample at 2026-05-28 11:01 +08:00:

```text
disk:
  100G total
  9.3G used
  91G free

record log files = 508
approx completed record commands = 254
checkpoint rows = 975
compressed raw trace = 2.50GB
probe rows = not started yet
label datasets = not generated yet
```

This monitor is evidence-only. It does not modify record/probe/label/train
artifacts or any gate.

Promotion boundary remains unchanged:

```text
No gate was lowered.
Phase5.5 remains forbidden.
Phase6 remains forbidden.
```

### 29.18 Dataset strategy and union guardrail - 2026-05-28 11:20 +08:00

Repair5 remains active. No runtime promotion is allowed.

Dataset strategy:

```text
1. Evaluate expand5000 by itself first.
   Purpose: isolate whether data volume / opportunity coverage is the blocker.

2. If expand5000 improves but still misses the full gate,
   build a formal old+new union branch.

3. Do not manually cat JSONL files.
   A union dataset must pass schema audit, duplicate checks,
   token-shape checks, split leakage checks, and anti-escape audit.
```

The old 2985-row dataset remains useful as:

```text
historical diagnostic
compatibility / fallback reference
cross-dataset validation evidence
```

New guardrail tool:

```text
src/czr004_teacher/attention_native_union_laur.py
```

Default behavior:

```text
reject duplicate checkpoint_id values
reject token-shape mismatches
reuse audit_attention_native_rows
record union_source per row
write union audit JSON / MD
```

This prevents accidental mixing of normal-token and high-token rows, and
prevents old validation evidence from leaking into training through an
uncontrolled merge.

Verification:

```text
conda run -n czr004 python -m pytest \
  tests/test_phase4f_attention_native_labels.py \
  tests/test_phase4f_attention_native_eval.py -q

result:
  19 passed, 1 warning
```

Remote progress at 2026-05-28 11:16 +08:00:

```text
tmux alive:
  repair5_expand5000_waiter_20260528
  repair5_expand5000_hightoken_waiter_20260528
  repair5_expand5000_progress_monitor_20260528

disk:
  100G total
  11G used
  90G free

GPU:
  RTX 4090 idle

record log files = 1300
approx completed record commands = 650
checkpoint rows = 2543
compressed raw trace = 3.53GB
probe rows = not started yet
label datasets = not generated yet
```

The record-log error scan remains clean.

Promotion boundary remains unchanged:

```text
No gate was lowered.
Phase5.5 remains forbidden.
Phase6 remains forbidden.
```

### 29.19 Expand5000 follow-up waiter - 2026-05-28 11:30 +08:00

Repair5 remains active. No runtime promotion is allowed.

Remote progress at 2026-05-28 11:25 +08:00:

```text
tmux alive:
  repair5_expand5000_waiter_20260528
  repair5_expand5000_hightoken_waiter_20260528
  repair5_expand5000_progress_monitor_20260528

disk:
  100G total
  11G used
  90G free

GPU:
  RTX 4090 idle

record log files = 1428
approx completed record commands = 714
checkpoint rows = 2790
compressed raw trace = 4.16GB
probe rows = not started yet
label datasets = not generated yet
```

The record-log error scan remains clean.

A follow-up waiter was queued:

```text
script:
  run_repair5_expand5000_followup_waiter_20260528.sh

tmux:
  repair5_expand5000_followup_waiter_20260528

log:
  outputs/logs/phase4f_repair5_expand5000_followup_waiter_20260528.log

remote validation:
  bash -n passed
```

Behavior:

```text
waits for:
  repair5_expand5000_waiter_20260528
  repair5_expand5000_hightoken_waiter_20260528

if any expand5000 final gate already allows Phase5.5:
  skip follow-up variants

otherwise screen seed61 on normal-token expand5000 for:
  ex5000_follow_pair_focal_m035_lh4
  ex5000_follow_global_rank3_anti3
  ex5000_follow_target_ce2_margin1_hm3
  ex5000_follow_target_margin2_rank3_safe5
```

Promotion policy is unchanged:

```text
seed61 must pass:
  original Phase4F gate
  attention-native gate
  safety gate
  anti-escape gate

only then:
  run seeds 103/107
  run final multi-seed gate
```

This is still the isolated expand5000 branch, not the old+new union branch.

Promotion boundary remains unchanged:

```text
No gate was lowered.
Phase5.5 remains forbidden.
Phase6 remains forbidden.
```

### 29.23 Expand5000 negative result and nextwave launch - 2026-05-29 09:20 +08:00

Repair5 remains active. No runtime promotion is allowed.

The expand5000 recovery run completed. The larger dataset is valid, but all
seed61 model variants failed promotion. Phase5.5 and Phase6 are still
forbidden.

Evidence:

```text
normal-token label audit:
  outputs/reports/phase4f_repair5_attention_native_expand5000_rawtrace_label_audit.json

high-token label audit:
  outputs/reports/phase4f_repair5_attention_native_expand5000_rawtrace_hightoken_label_audit.json

sample_count:
  4956

train / validation:
  4194 / 762

validation high-margin opportunity count:
  310
```

Seed61 recovery outcomes:

| variant | top1 | top3 | harmful recall | harmful precision | delta | attention | anti-escape |
|---|---:|---:|---:|---:|---:|---|---|
| `ex5000_mlp_target_global` | 0.2133 | 0.6625 | 0.6769 | 0.3203 | 0.0062 | fail | fail |
| `ex5000_linear_target_global` | 0.1863 | 0.6646 | 0.7370 | 0.3084 | -0.0001 | fail | fail |
| `ex5000_mlp_safety_light` | 0.1967 | 0.6667 | 0.8224 | 0.2844 | 0.0006 | fail | fail |
| `hightoken_ht_mlp_target_global` | 0.1449 | 0.6998 | 0.7623 | 0.3143 | 0.0009 | fail | fail |
| `hightoken_ht_linear_target_global` | 0.1739 | 0.6687 | 0.8051 | 0.3006 | 0.0028 | fail | fail |
| `followup_ex5000_follow_pair_focal_m035_lh4` | 0.1284 | 0.6832 | 0.8051 | 0.2751 | 0.0021 | fail | fail |
| `followup_ex5000_follow_global_rank3_anti3` | 0.1843 | 0.6646 | 0.7477 | 0.3068 | 0.0019 | fail | fail |
| `followup_ex5000_follow_target_ce2_margin1_hm3` | 0.1615 | 0.6791 | 0.8652 | 0.2759 | 0.0030 | fail | fail |
| `followup_ex5000_follow_target_margin2_rank3_safe5` | 0.1718 | 0.6749 | 0.7303 | 0.3133 | 0.0004 | fail | fail |

Interpretation:

```text
The larger dataset helped coverage and produced near-top3 variants,
but no checkpoint passed ranking, safety, and anti-escape together.
The dominant failure remains anti-escape / safety-rank coupling,
not label-audit coverage.
```

Implementation update:

```text
added optional Repair5 losses:
  lambda_high_margin_harmful
  lambda_anti_candidate_safety

defaults:
  zero, so old configs remain comparable

verification:
  local Repair5 tests = 22 passed, 1 warning
  remote Repair5 tests = 22 passed, 1 warning
```

Naming clarification:

```text
Old generated names containing "mlp" meant a shallow output head on top of
LAU-EdgeTraceTransformer-v4. They did not mean the Phase5C MLP-only baseline.

New variants use:
  attn_mlp_head_*
  attn_linear_head_*
```

Nextwave run:

```text
script:
  run_repair5_expand5000_nextwave_20260529.sh

tmux:
  repair5_expand5000_nextwave_20260529

log:
  outputs/logs/phase4f_repair5_expand5000_nextwave_20260529.log

generated configs:
  configs/phase4/generated_repair5_expand5000_nextwave/hightoken_attn_mlp_head_candidate_safe_lh5.yaml
  configs/phase4/generated_repair5_expand5000_nextwave/hightoken_attn_linear_head_candidate_safe_lh6.yaml
  configs/phase4/generated_repair5_expand5000_nextwave/normal_attn_mlp_head_highcap_candidate_safe.yaml
  configs/phase4/generated_repair5_expand5000_nextwave/normal_attn_linear_head_rank_safe.yaml
```

The nextwave variants still train the LAUR / LAU LTM `UpdateLTM` rule only.
They do not predict agent actions, replace PIBT / LaCAM*, or introduce learned
restart.

Promotion policy remains unchanged:

```text
seed61 must pass:
  original Phase4F gate
  attention-native gate
  safety gate
  anti-escape gate

only then:
  run seeds 103/107
  run final multi-seed gate
```

Initial liveness at 2026-05-29 09:21 +08:00:

```text
tmux alive:
  repair5_expand5000_nextwave_20260529

active training:
  hightoken_attn_mlp_head_candidate_safe_lh5 seed61

GPU:
  1213 / 12282 MB

epoch1:
  top1 = 0.0497
  top3 = 0.6936
  harmful recall = 0.9065
  harmful precision = 0.2002
  anti_escape_capture = 0.1645
```

Promotion boundary remains unchanged:

```text
No gate was lowered.
Phase5.5 remains forbidden.
Phase6 remains forbidden.
```

### 29.24 Post-nextwave waiter queued - 2026-05-29 09:40 +08:00

Repair5 remains active. No runtime promotion is allowed.

Current nextwave first-variant trajectory:

| epoch | top1 | top3 | harmful recall | harmful precision | anti capture | anti gate |
|---:|---:|---:|---:|---:|---:|---|
| 1 | 0.0497 | 0.6936 | 0.9065 | 0.2002 | 0.1645 | fail |
| 20 | 0.1739 | 0.6729 | 0.8291 | 0.2739 | 0.3387 | fail |
| 40 | 0.2008 | 0.6418 | 0.6168 | 0.3014 | 0.4806 | pass |
| 60 | 0.1988 | 0.6749 | 0.5033 | 0.2655 | 0.4548 | pass |
| 80 | 0.2277 | 0.6480 | 0.3231 | 0.2597 | 0.4419 | pass |
| 100 | 0.2340 | 0.6253 | 0.2069 | 0.2230 | 0.4419 | pass |

Interpretation:

```text
The anti/high-margin losses can push anti-escape over the threshold,
but this first variant trades away harmful recall and still misses top1/top3.
```

A post-nextwave waiter was queued without interrupting the active run:

```text
script:
  run_repair5_expand5000_postnext_20260529.sh

tmux:
  repair5_expand5000_postnext_20260529

log:
  outputs/logs/phase4f_repair5_expand5000_postnext_20260529.log

waits for:
  repair5_expand5000_nextwave_20260529
```

If any expand5000 final gate already allows Phase5.5, the post-nextwave
script exits without training. Otherwise it screens seed61 with variants
that reduce direct anti-candidate safety pressure, increase target-rule
top1/ranking pressure, and use per-rule safety calibration:

```text
configs/phase4/generated_repair5_expand5000_postnext/hightoken_attn_mlp_head_rank_recall_perrule.yaml
configs/phase4/generated_repair5_expand5000_postnext/hightoken_attn_linear_head_rank_recall_lowanti.yaml
configs/phase4/generated_repair5_expand5000_postnext/normal_attn_mlp_head_top1_focus_perrule.yaml
configs/phase4/generated_repair5_expand5000_postnext/normal_attn_mlp_head_balanced_rank_anti.yaml
```

Promotion boundary remains unchanged:

```text
No gate was lowered.
No Repair5 runtime promotion is allowed.
Phase5.5 remains forbidden.
Phase6 remains forbidden.
```

Current liveness update at 2026-05-29 09:42 +08:00:

```text
tmux alive:
  repair5_expand5000_nextwave_20260529
  repair5_expand5000_postnext_20260529

active training:
  hightoken_attn_mlp_head_candidate_safe_lh5 seed61

epoch120:
  top1 = 0.2050
  top3 = 0.6315
  harmful recall = 0.1816
  harmful precision = 0.2278
  anti_capture = 0.4355
  anti gate = pass
```

No eval summary exists yet because training is still active. This continues
to support the same diagnosis: anti-escape pressure is effective, but this
variant is trading away recall and remains far below top1/top3 promotion.

### 29.25 Layered Repair5 gates after GPTPro advice - 2026-05-29 09:55 +08:00

Repair5 remains active. No runtime promotion is allowed.

GPTPro's recommendation is accepted as a diagnostic-policy correction, not as
a final-gate relaxation:

```text
Do not lower final claim gates.
Do split early Repair5 judgement into layered gates.
Do not let Repair3-style hard-label top1/top3 prematurely kill
attention-native utility/opportunity experiments.
Do require closed-loop LTM comparison before any performance claim.
```

The Repair5 gate stack is now documented as three layers:

```text
A. Development gate
   Purpose:
     decide whether a label/loss/model/data direction is worth continuing
   Thresholds:
     label/schema audit pass
     positive delta proxy
     top1 >= 0.25
     top3 >= 0.60
     harmful recall >= 0.70
     harmful precision >= 0.25
     high-margin opportunity capture better than additive/defer reference
     avoidable additive/defer fallback better than additive/defer reference
   Meaning:
     not runtime permission

B. Promotion-candidate gate
   Purpose:
     decide whether to spend larger training or prepare tightly scoped smoke
   Thresholds:
     top1 >= 0.32
     top3 >= 0.65
     harmful recall >= 0.78
     harmful precision >= 0.28
     mean delta > 0
     opportunity capture >= reference + 0.05
     avoidable fallback <= reference - 0.05
     multi-seed stability must be checked before any serious promotion
   Meaning:
     not final success

C. Runtime / paper-claim gate
   Purpose:
     decide Phase5.5 runtime parity/smoke permission and later claims
   Rule:
     original Phase4F + attention-native + safety + anti-escape + multi-seed
     remain strict; Phase6 still needs closed-loop learned-benefit evidence.
```

Added diagnostic evaluator:

```text
src/eval/eval_laur_repair5_layered_gate.py

outputs:
  outputs/reports/phase4f_repair5_layered_gate_summary.json
  outputs/reports/phase4f_repair5_layered_gate_report.md
```

This evaluator never sets `phase5p5_allowed` or `phase6_allowed` true.
It is only a research triage report.

Verification:

```text
local Repair5 tests:
  24 passed, 1 warning

remote Repair5 tests:
  24 passed, 1 warning
```

Remote re-score of completed Repair5 summaries:

```text
summaries re-scored:
  27

development pass:
  0

promotion-candidate pass:
  0

strict seed pass:
  0
```

Best diagnostic rows:

| variant | top1 | top3 | recall | precision | anti capture | anti pass | note |
|---|---:|---:|---:|---:|---:|---|---|
| `rawtrace_edge_sf_target_ce1_margin1_hm4` | 0.1911 | 0.7099 | 0.7460 | 0.2557 | 0.2811 | false | top3 OK, anti/top1 incomplete |
| `rawtrace_edge_sf_global_pair_neg2_anti2` | 0.2321 | 0.7065 | 0.5767 | 0.3134 | 0.4378 | true | anti OK, recall/top1 incomplete |
| `expand5000_hightoken_ht_mlp_target_global` | 0.1449 | 0.6998 | 0.7623 | 0.3143 | 0.2839 | false | near top3, anti/top1 incomplete |
| `expand5000_follow_target_ce2_margin1_hm3` | 0.1615 | 0.6791 | 0.8652 | 0.2759 | 0.2968 | false | recall OK, anti/top1 incomplete |

Interpretation:

```text
The layered framework is useful and should guide future Repair5 triage.
However, no completed historical Repair5 run passes even the development gate.
The current nextwave/postnext queue remains necessary.
```

Promotion boundary remains unchanged:

```text
No final gate was lowered.
No completed Repair5 result permits Phase5.5.
Phase6 remains forbidden.
```

### 29.26 Repair5B next-round plan from GPTPro - 2026-05-31 +08:00

GPTPro's `phase4f55_laur_repair5b_next_round_codex_plan.md` is accepted as
the next Repair5B research plan. It does not change the project direction and
does not relax any runtime or paper-claim gate.

Current interpretation:

```text
expand5000 / high-token data is valid and opportunity-rich
sample_count = 4956
train / validation = 4194 / 762
use_nonadditive = 3274
defer_ltm = 1682
high_margin_nonadditive_opportunity_count = 2325
schema_error_count = 0

27 completed Repair5 summaries:
  development pass = 0
  promotion-candidate pass = 0
  strict seed pass = 0
```

Therefore the failure is not "no signal" or "bad data pipeline." The sharper
diagnosis is:

```text
attention-native labels, raw-trace evidence, and anti-escape evaluation work;
individual subgoals can improve;
but the current flat multi-task selector has not jointly solved
ranking + safety + anti-escape + positive utility.
```

Repair5B next objective:

```text
Build hierarchical attention-native LAUR for learned UpdateLTM only.

No agent-action policy.
No learned restart.
No PIBT / LaCAM* semantic change.
No candidate/conflict/pruning/rewrite semantic change.
No final-gate lowering.
```

The next phase is not another blind loss sweep. The required sequence is:

```text
R5B-0 failure decomposition + oracle upper bound
R5B-1 per-rule / per-family safety calibration
R5B-2 hierarchical normal-token rank-first curriculum
R5B-3 hierarchical high-token rank-first curriculum
R5B-4 hierarchical high-token safety-first curriculum
R5B-5 high-margin specialist diagnostic

Only if these show real signal:
R5B-6 hierarchical high-token + stratified sampler
R5B-7 hierarchical high-token + per-rule safety + rank-first
R5B-8 hierarchical high-token + hard-case replay
R5B-9 hierarchical high-token + map-family balanced fine-tune
R5B-10 bounded parameter/residual head diagnostic
       only if oracle shows static rule action space is limiting
```

First required diagnostic:

```text
src/eval/diagnose_laur_repair5_failure_modes.py

outputs:
  outputs/reports/phase4f_repair5_failure_decomposition.md
  outputs/reports/phase4f_repair5_failure_decomposition.json
  outputs/tables/phase4f_repair5_failure_by_rule.csv
  outputs/tables/phase4f_repair5_failure_by_map.csv
  outputs/tables/phase4f_repair5_failure_by_opportunity.csv
  outputs/tables/phase4f_repair5_oracle_gap.csv
```

The failure decomposition must compare at least:

```text
always_additive / always_defer_ltm
Repair3 stable-target MLP baseline
best completed Repair5 by top3
best completed Repair5 by recall
best completed Repair5 by anti-escape
best completed expand5000 high-token variant
oracle_best_safe_rule
oracle_best_safe_nonadditive_rule
oracle_defer_when_no_safe_opportunity
```

Required grouped metrics:

```text
rule_top1 / rule_top3
safe_utility_top1 / safe_utility_top3
utility_regret_to_oracle
selected_vs_additive_delta
selected_vs_additive_utility
high_margin_nonadditive_capture
avoidable_additive_or_defer
harmful false negatives by selected rule
harmful false positives by selected rule
defer reason confusion
decision accuracy: defer_ltm vs use_nonadditive
```

Oracle decision rule:

```text
if oracle_vs_additive_mean_delta <= small_epsilon
   or oracle_high_margin_capture_possible is low:
       the current static rule space may be the bottleneck;
       consider bounded UpdateLTM parameter/residual heads only as a diagnostic.
else:
       continue hierarchical attention-native LAUR.
```

Hierarchical model target:

```text
LAU-HierEdgeTraceTransformer-v5

global_context_encoder
edge_trace_encoder
rule_token_encoder
cross_attention
decision_head: defer_ltm vs use_nonadditive
safety_head: per-rule harmful probability
rule_rank_head: rank non-additive rules only
utility_head: selected-vs-additive / risk-adjusted utility
optional uncertainty / abstention head
```

Hierarchical selection logic must be explicit and logged:

```text
if decision_head says defer_ltm:
    select additive_ltm / defer_ltm
else:
    apply calibrated per-rule safety mask
    rank safe non-additive rules
    select best safe non-additive only if margin over additive/defer is sufficient
    otherwise defer with reason = insufficient_margin

must log:
  selected_rule
  selection_stage
  defer_reason
  safety_threshold_by_rule
  safety_mask
  best_safe_nonadditive_rule
  best_safe_nonadditive_score
  margin_vs_additive
  margin_vs_defer
```

Per-rule / per-family safety calibration is now a first-class Repair5B step:

```text
src/eval/calibrate_laur_repair5_per_rule_safety.py

outputs:
  outputs/reports/phase4f_repair5_per_rule_safety_calibration.json
  outputs/reports/phase4f_repair5_per_rule_safety_calibration.md
  outputs/tables/phase4f_repair5_per_rule_safety_thresholds.csv

target remains:
  harmful recall >= 0.80
  harmful precision >= 0.30
```

Training must use structured curricula rather than simultaneous pressure on all
losses:

```text
configs/phase4/generated_repair5_hier_curriculum/

rank-first:
  early decision + ranking + utility
  middle add safety and calibration
  late add anti-escape / high-margin pressure

safety-first:
  early harmful + high-margin harmful + decision
  middle add rule ranking
  late add anti-escape and per-rule calibration

high-margin specialist:
  train/evaluate hard opportunity subset as diagnostic only
```

Sampler and data aggregation requirements:

```text
train_laur_attention_native.py:
  --sampler stratified

stratify by:
  split
  map family
  agent count bucket
  target rule family / target rule
  harmful positive / negative
  high-margin opportunity
  defer reason
  anti_escape_sample

hard-case replay index:
  artifacts/teacher/laur/repair5_hardcase_index.jsonl
```

Hard-case mining is preferred over blindly scaling the dataset. Generate new
Phase4F data only for buckets exposed by failure decomposition:

```text
specific map family has high regret
specific rule family has high harmful false-negative rate
high-margin opportunity is under-sampled for a rule family
anti-escape passes but selected utility remains poor
```

Recent AI / robotics / MAPF literature may be used only for architecture and
experiment inspiration. Required memo:

```text
outputs/reports/phase4f_repair5_recent_ai_robotics_architecture_memo.md

Scope:
  read at least six 2023-2026 AI / robotics / MAPF / planning-learning papers
  extract transferable architecture / training / gate / ablation ideas
  state what cannot be used because it violates LAUR constraints
  propose 2-4 LAUR-compatible variants
  do not bypass existing gates
```

Phase5.5 remains forbidden until all of the following hold:

```text
seed61 strict Repair5B gate pass
seeds 103/107 pass
final multi-seed gate pass
anti-escape pass by high-margin opportunity subset
per-rule or global safety calibration report clean
selected_vs_additive_delta positive
no missing gate fields
deterministic inference/export path exists
additive/defer fallback reasons logged
```

If Phase5.5 is unlocked, runtime smoke must compare:

```text
LaCAM*
LaCAM*+LTM
Repair3 MLP safe runtime
Repair5B LAUR
Repair5B force-additive / defer-only
Repair5B without anti-escape
Repair5B without safety
Repair5B static selected-rule ablations
```

Phase5.5 smoke output:

```text
outputs/reports/phase5p5_laur_repair5b_runtime_smoke_report.md
```

Scaling boundary:

```text
Do not start 20-40 hour or 100 hour training until Repair5B seed61 reaches
promotion-candidate or near-strict evidence, oracle gap shows the model rather
than static action space is the bottleneck, and high-margin capture / recall /
top3 improve together.

100 hour scale additionally requires 20k-50k checkpoint labels, enough
high-margin validation evidence, non-collapsing multi-seed behavior, Phase5.5
smoke not worse than LTM, and ablations proving attention/raw-trace/anti/safety
contribution.
```

### 29.27 GPTPro/Claude gate clarification - 2026-05-31 +08:00

The GPTPro/Claude discussion is accepted as a research-evaluation clarification,
not as a Phase5.5 runtime relaxation.

Key distinction:

```text
Research / paper KPI:
  eventually judged by closed-loop learned benefit over additive LTM and
  LaCAM*+LTM, with safety, utility regret, high-margin capture, overhead,
  and ablation evidence.

Engineering / Phase5.5 runtime gate:
  remains strict. It protects solver-loop semantics, fallback/parity behavior,
  safety, anti-escape, deterministic export, and multi-seed stability.
```

Repair5 attention-native labels are not Repair3-style stable hard labels.
Therefore all-class top1 is no longer the primary Repair5 research KPI:

```text
top1:
  diagnostic only for Repair5B research triage.

primary Repair5B research signals:
  safe utility top-k
  utility regret to oracle
  selected_vs_additive_delta
  harmful recall / precision
  high-margin opportunity capture
  avoidable additive/defer behavior
  fallback/defer reason distribution
  later closed-loop transfer versus additive LTM
```

The operational gate stack is now:

```text
A. Development / research-triage gate
   schema/split/audit clean
   top3 >= 0.60, or approaching 0.65 with clear positive delta
   harmful recall >= 0.70
   harmful precision >= 0.25
   selected_vs_additive_delta > 0
   high-margin capture better than always-additive / Repair3 reference
   utility regret to oracle reported
   top1 diagnostic only
   meaning: continue exploration only

B. Promotion-candidate / diagnostic preflight gate
   top3 >= 0.65
   harmful recall >= 0.78
   harmful precision >= 0.28
   selected_vs_additive_delta > 0
   anti-escape clearly improves versus additive/defer and Repair3 reference
   high-margin opportunity capture >= 0.30 or clearly above reference
   utility regret acceptable
   meaning: may plan diagnostic closed-loop preflight only

C. Runtime / Phase5.5 engineering gate
   original Phase4F or formally approved utility-equivalent gate
   attention-native gate
   harmful recall >= 0.80
   harmful precision >= 0.30
   anti-escape hard pass or behaviorally equivalent proof
   seed61 + seeds 103/107 + final multi-seed gate
   force-additive / defer parity
   deterministic export
   no solver semantic changes
   meaning: Phase5.5 parity/smoke only

D. Phase6 / paper-claim gate
   closed-loop > additive LTM / LaCAM*+LTM
   multi-map / multi-seed statistics
   success, SoL ratio, anytime AUC, expanded nodes, TTFS, runtime overhead
   ablations: no learned LAUR, no anti-escape, no safety,
     Repair3 baseline, additive LTM baseline
```

Diagnostic closed-loop preflight may be planned before Phase5.5 only if it is
explicitly labeled:

```text
not Phase5.5 permission
not runtime promotion
not Phase6 evidence
hard safety mask enabled
force-additive/defer parity checked
only measures offline-to-closed-loop transfer
```

This clarification changes interpretation, not final gates:

```text
Do lower the early research burden of all-class top1.
Do re-rank Repair5B by closed-loop relevance.
Do not lower Phase5.5 safety, anti-escape, parity, export, or multi-seed gates.
Do not claim Phase6 without closed-loop learned-benefit evidence.
```

## 2026-06 Repair5G AAAI evidence ladder

AAAI evidence ladder:

- Level A: representation validated
- Level B: static/map-agent runtime candidate validated
- Level C: learned runtime UpdateLTM selector validated
- Level D: AAAI paper package ready
- Level E: Phase5.5/Phase6 engineering promotion considered separately

Current status after G4:

- Level A = passed directionally and cleanly under parity policy
- Level B = partly passed
- Level C = not yet runtime-integrated
- Level D = not ready
- Level E = closed

Repair5G / learned UpdateLTM paper gates now require a learned runtime selector, clean heldout validation, static/map-agent/learned baselines, shuffled/random diagnostics, feature and channel ablations, time/iteration stress, multi-map/multi-agent analysis, reproducibility manifests, and a claim ledger. `aaai_ready=false` remains mandatory until all paper-grade gates pass.

## 2026-06 Repair5G.5.1 status correction

After G5 and G5.1:

- Level A = passed under G2/G4 interpretation
- Level B = strong static/map-agent baseline, not a learned claim
- Level C = blocked by runtime hook sanity failure
- Level D = not ready
- Level E = closed

Required AAAI correction:

- `runtime_selector_integration = passed`
- `runtime_selector_smoke = failed`
- `learned_runtime_selector_performance = failed`
- `learned_runtime_fresh_holdout = blocked_not_run`
- `aaai_ready = false`

Do not run IDs 166..205 until the runtime hook reproduces always-static/map-agent safe policies, policy controls pass or are formally classified, and a corrected selector passes observed-ID smoke before being frozen. G5.1 stopped at `runtime_hook_bug_blocks_learning`; safe selector smoke was blocked, counterfactual labels were unavailable without replayable UpdateLTM checkpoints, and small neural selector training stayed blocked.

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

Phase4 LAU-LTM now has two subtracks:

Subtrack A: executable static-flow / best-static baseline ladder and parity.
Subtrack B: static-flow-relative parameter/residual optimizer.

LAU-LTM is no longer only a classifier over update candidates. The target is now:

trace/context -> safe bounded UpdateParams residual around static_flow.

Phase4 labels move from short-probe update-rule labels to short-probe parameter-region labels, safe-region /
unsafe-region labels, residual parameter targets, and deployable-static-relative labels.

## 2026-06-12 - G5.40 strategic update: underpowered parameter search is not evidence

G5.39 established the GGO-style direction but was underpowered: only 8 contexts and 8 parameter candidates were run in the optimizer probe. Therefore G5.40 requires staged, sufficiently powered parameter search before model training or frozen policy claims.

A safe region must have support across multiple seeds and at least one nontrivial map/budget/agent stratum. The project will treat underpowered runs as continuation artifacts, not positive or negative scientific conclusions.

From G5.40 onward, parameter optimization rounds must report:

- candidate coverage
- stratum coverage
- seed-block coverage
- safe-region support
- blind support
- whether the result is underpowered

No generator, frozen policy, runtime, Phase5.5, Phase6, or AAAI claim is allowed until the safe-region support thresholds are met.

## 2026-06-12 - G5.41 strategic update: safe regions are per-stratum, not global candidates

G5.40 showed that no parameter candidate was globally supported safe/useful under the initial thresholds.
This does not prove the absence of learnable parameter regions.
Static-flow residuals may be safe only in specific strata:
  map family
  agent count
  budget
  iteration/final behavior
Therefore G5.41 changes the safe-region unit from candidate-level to candidate-stratum-level.
Learning target becomes:
  context/trace -> safe parameter region or static fallback
rather than:
  one global parameter candidate.

From G5.41 onward, a static-flow parameter region is evaluated at the deployable stratum level. A candidate that is unsafe globally may still be valuable if a frozen pre-replay policy can restrict it to strata where it has zero regression and nontrivial static-relative gain.

## 2026-06-12 - G5.42 strategic update: residual overlay must sit on a deployable static fallback ladder

G5.41 found per-stratum residual regions and achieved zero success regression versus static_flow in blind replay, but failed versus frozen_family_static.
This indicates that static_flow alone is not the correct fallback baseline in all strata.
From G5.42 onward, learned/static-flow residuals are evaluated as an overlay on a deployable static fallback ladder:
  additive_ltm
  static_flow_shield
  best_fixed_static_goal_aware
  frozen_family_static_goal_aware
Residual parameters are only allowed in supported strata where they beat the selected deployable static baseline with zero regression.

The learned residual component is not a replacement for the strongest deployable static baseline; it is a conditional overlay. The first decision is which deployable static baseline is safest for the stratum, and the second decision is whether a supported residual region can safely improve over that baseline.

## 2026-06-14 - G5.46 strategic update: real continuous-theta replay is mandatory

G5.45 built the neural continuous theta infrastructure but did not run new continuous-theta solver replay. From G5.46 onward, neural UpdateParams evidence requires real newly materialized continuous-theta solver rows. Retrospective rows may train diagnostic surrogates, but cannot satisfy generator or replay gates.

G5.46 therefore treats dataset construction, retrospective surrogate training, generated aliases, and offline generator outputs as insufficient without newly materialized solver-facing theta rows. A local smoke can validate materialization, but generator or replay gates require the hard real-row profile or an explicit documented blocker.

## 2026-06-14 - G5.47 strategic update: SafeGate v2 and full-theta evaluability

G5.47 supersedes the old selector-era SafeGate interpretation for neural bounded continuous `UpdateParams` exploration. G5.46 executed real solver-facing replay, but its negative interpretation is confounded unless both conditions are repaired:

```text
1. full bounded theta is materialized directly, not compressed through repair5g518_grid aliases
2. calibrated replay horizons produce finite paired quality outcomes
```

SafeGate is now a layered hierarchy:

```text
Tier I - invariant safety gates, never relax:
  external_lacam2_clean
  reserved_ids_untouched
  force_additive_parity_passed
  candidate_recognized_all
  bounded_updateparams_all
  no_nan_or_inf_updateparams
  fulltheta_fingerprint_match_rate = 1.0
  cost_audit_finite
  configured_cost_bounds_respected
  solver_semantics_changed = false

Tier E - evaluability gates before positive or negative interpretation:
  finite_ratio_rate >= 0.20
  finite_ratio_rows >= 3000 for large probes
  both_success_quality_pairs_vs_primary >= 2000
  primary baseline success is nontrivial
  paired baselines are materialized

Tier X - exploration gates:
  unsafe theta may be collected as risk-model data
  unsafe exploration cannot create positive/runtime/Phase5.5/Phase6/AAAI claims

Tier R/P - refinement and targeted generated-theta policy gates:
  promote only supported regions or generated policies against the declared primary baseline
  require controlled false-safe behavior, non-collapsed theta diversity, and primary-baseline utility evidence

Tier B - blind/runtime/paper gate:
  remains strict; G5.47 does not relax runtime or paper claims
```

The primary baseline for neural theta generation is `static_flow_shield`. `additive_ltm` remains the paper/LTM parity floor. Strong static variants such as `frozen_family_static_goal_aware`, `best_fixed_static_goal_aware`, and posthoc/oracle static policies are diagnostic stress tests unless a later experiment explicitly declares one of them as the primary baseline. Exploration must not be stopped merely because a continuous theta candidate loses to every hand-written static variant; conversely, static selector wins do not count as learned UpdateLTM progress.

If finite paired outcomes are absent, the only valid conclusion is:

```text
non_evaluable_replay_continue_evaluability_repair
```

not:

```text
continuous theta has no signal
```

## 2026-06-14 - G5.48 strategic update: static_flow primary baseline, real calibration only

From G5.48 onward, `static_flow_shield` is the primary fixed baseline for neural continuous `UpdateParams`. The gate asks whether learned/fulltheta UpdateLTM can safely improve over this hand-designed static-flow LTM variant. Additive LTM is a paper-faithful floor. Strong family/static variants are diagnostic baselines, not the primary target and not selector actions.

G5.48 changes the project-wide rule for this route: a budget/horizon grid must be materialized by real solver commands before it can support any positive or negative conclusion. Declared calibration rows, copied rows, and static-baseline selector wins do not count as learned UpdateLTM progress.

The G5.48 local run produced `3654` calibration solver/diagnostic rows over `522` context-horizons, with `522` static_flow rows, `1604` finite-ratio rows, `283` both-success pairs versus static_flow, and `12` locally evaluable stratum-horizons. This satisfies the real-calibration floor but not the `finite_ratio_rows >= 3000` full replay gate, so the decision is `g548_budget_calibration_underpowered_continue_calibration`. Fulltheta replay, generator training, targeted replay, blind replay, Phase5.5, Phase6, runtime, and AAAI claims remain closed.

## 2026-06-15 - G5.51 execution update: iteration-counterfactual SafeGate repair

G5.51 keeps static_flow_shield as the primary baseline and tightens SafeGate after
G5.50 targeted replay failures. Offline generator success is no longer sufficient
for promotion. A learned bounded UpdateParams policy must pass fresh targeted
replay with zero success regressions versus static_flow_shield before blind replay
or runtime claims. The next valid learning signal is iteration/checkpoint-level
counterfactual labels, not final full-run hindsight alone.
