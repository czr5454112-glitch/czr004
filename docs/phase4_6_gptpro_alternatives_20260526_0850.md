# Phase4-6 GPTPro 备选技术路线辅助总纲

来源备注：本文件根据用户提供的网页端 GPTPro 备选方案整理归档。GPTPro 原文未单独注明真实生成时刻，只包含“已思考 10m 19s”；因此本文暂按本次归档时间标注为 **2026-05-26 08:50 +08:00**。若后续获得原始 GPTPro 生成时间，应更新本备注。

归档分支：`phase1a-ltm-paper-parity`  
适用范围：仅作为 Phase4-Phase6 的备选路线，不替换当前主路线，不与主线混写。  
主线边界仍保持：

```text
LaCAM* baseline
  -> LaCAM* + LTM paper-faithful reimplementation
  -> LaCAM* + NTM guidance
```

## 0. 当前资产核对

GPTPro 方案基于对 `phase1a-ltm-paper-parity` 分支的核对：该分支包含 Phase1a-Phase3 的报告、LTM 代码、metrics harness 与 teacher schema；`src/models`、`src/train`、`cpp/ntm` 等 Phase4 模型和 NTM runtime 仍基本为空，适合从干净的 Phase4 模块开始。

已确认或可直接复用的资产：

- 分支和目录：`phase1a-ltm-paper-parity`，包含 `artifacts/`、`configs/`、`cpp/`、`docs/`、`outputs/`、`src/`、`tests/` 等目录。
- Phase1 已实现：
  - `DirectedTrafficMap`
  - `PibtTraceCollector`
  - `WeightedDistanceTable`
  - LTM-guided LaCAM* adapter
  - frequent restart wrapper
- Phase1a 结果：
  - full batch 有 `3800 / 3800` rows。
  - base paper-parity subset 中，LTM 在 `72 / 72` map-agent groups 上平均 ratio 更低。
- Phase2 已统一：
  - SoL
  - lower bound
  - SoL ratio
  - incumbent parser
  - AUC
  - paired tests
  - JSONL schema
- Phase3 teacher-data gate：
  - 生成 `8` runs。
  - 生成 `90,992` edge-label rows。
  - primary route 明确为 `online_residual`。
  - pure edge regression 只作为 diagnostic / pretraining。
- 项目指南边界：
  - 主线只能是 `LaCAM* baseline -> LaCAM* + LTM -> LaCAM* + NTM`。
  - 不新增无关 solver baseline。
  - NTM 只能作为 guidance 层。
  - 最终贡献不能写成“拟合 LTM 权重”，必须包含 online residual、ranking 或 safety 这类 solver-facing 机制。

## 1. 共同研究定位

LTM 论文关键点：

- LTM 不是预先离线生成 guide paths。
- LTM 在 LaCAM* anytime loop 中使用 PIBT 历史在线更新 directed weighted traffic map。
- LTM 收集 committed actions 和 blocked actions。
- wait action 不建 self-loop，而是把拥堵传播到相邻出边。
- 更新后的 LTM 影响 PIBT evaluation function、root priority 和 LaCAM* advanced distance estimates。

NTM 的自然创新缺口：

- LTM 为了效率采用 simple additive update。
- LTM 论文明确没有把更复杂的 update rule 作为目标。
- 因此“学习增强 LTM”的强贡献不应是拟合最终 LTM 权重，而应是学习：
  - 什么 traffic signal 真正导致 closed-loop improvement；
  - 什么时候应该启用、关闭或改变 LTM 更新策略；
  - 如何在不破坏 LaCAM* / PIBT 语义的前提下改善 solver-level 指标。

近两年相关工作启发：

- Guidance Graph Optimization, IJCAI 2024：把 guidance 表示为 graph edge weights，并提出直接优化 edge weights 或学习生成 edge weights 的 update model。对本项目的启发是“学习 traffic graph / update model”，但必须绑定到 LaCAM* + LTM 的 online PIBT trace，而不是转成 lifelong MAPF 的独立 guidance graph 项目。
- Online Guidance Graph Optimization, AAAI 2025：研究基于 real-time traffic patterns 动态生成 adaptive guidance，并把 guidance 接入 PIBT。对本项目的启发是“在线 traffic-aware guidance”叙事，但本项目任务仍是 one-shot / planning-and-execution LaCAM*，不换成 OGGO。
- Traffic Flow Optimisation, AAAI 2024：说明拥堵规避路径能改善 one-shot MAPF solution quality 和 lifelong MAPF throughput，但依赖预先生成 congestion-avoiding paths。LTM 的优势是避免高预计算开销，NTM 也必须维持在线、低 overhead。
- Local Guidance for Configuration-Based MAPF, AAAI 2026：说明 local spatiotemporal guidance 可以在 LaCAM 上显著改善质量，同时保持 1000 agents 级别的实时响应。启发是 NTM 应设计成 local / bottleneck / restart-aware，而不是全图重规划。
- LaGAT, AAAI 2026：把 learned heuristic 接入 LaCAM，并强调神经策略不可靠时需要 deadlock / safety safeguard。直接支持 safety head 和 fallback parity 设计。

---

## 2. 备选方案一：CBR-LTM

### 2.1 名称

英文名：`CBR-LTM: Counterfactual Bottleneck Residual Lightweight Traffic Map`

中文名：反事实瓶颈残差交通图增强的 `LaCAM* + LTM`

命名意图：

- 保留 LTM 主线。
- 强调不是简单 edge regression。
- 通过 counterfactual closed-loop signal 学习哪些 residual traffic corrections 能改善 solver 行为。

### 2.2 核心思想

CBR-LTM 的 pipeline：

```text
LTM 照常在线收集 PIBT history
  -> 形成 w_ltm
  -> NTM 只在 traffic bottleneck / ranking-sensitive edge 上预测 residual delta
  -> w_cbr = clamp(w_ltm + gate * delta, 0, 10)
  -> 用 w_cbr 更新 weighted distance table 和 PIBT candidate ranking
```

CBR-LTM 不直接学习 `ltm_normalized_weight`，而是学习：

- 在当前 restart / density / bottleneck context 下；
- 某条 directed edge 或某个 action 的 traffic cost 应该上调、下调，还是保持 LTM；
- 对 solver-level 指标真正有利的 residual correction。

关键创新是 counterfactual label。监督问题不是“LTM 最后给这条边多少权重”，而是：

> 如果在这一轮 restart 前，把这类 edge 的 cost 增加、减少或保持，后续 `LaCAM*+LTM` 的 SoL ratio、TTFS、AUC、returned solution count 是否变好？

这让 NTM 的监督目标和 solver closed-loop 指标绑定，避免退化成 teacher distillation。

### 2.3 与相关工作的联系

CBR-LTM 继承 LTM 的：

- directed weighted traffic map；
- PIBT committed / blocked trace；
- wait propagation；
- LaCAM* frequent restart loop。

与 GGO / OGGO 的联系：

- 借鉴“guidance graph edge weights 可以被优化或由 update model 生成”。
- 不做 lifelong MAPF 的独立 guidance graph。
- learned correction 限定在 LTM 已经存在的 directed edge cost 上。

与 Local Guidance 的联系：

- 不全局重规划所有 agent。
- 关注局部瓶颈、局部时空拥堵和 agent 附近 candidate ranking。
- local guidance 是 global guidance 和完整 collision-free paths 之间的折中。

与 LaGAT 的联系：

- 神经模块可以增强 LaCAM。
- 必须用搜索框架兜底。
- 必须处理 imperfect neural guidance。
- CBR-LTM 内置 safety gate，模型只改变排序 / 权重，不删除合法动作。

### 2.4 Phase0-Phase3 资产复用

直接复用：

```text
cpp/ltm/
  DirectedTrafficMap
  PibtTraceCollector
  WeightedDistanceTable
  LTM-guided LaCAM* adapter

src/czr004_metrics/
  SoL
  lower bound
  SoL ratio
  anytime AUC
  paired sign test
  JSONL schema

src/czr004_teacher/
  schema.py
  splits.py

artifacts/teacher/manifest.jsonl
  Phase3 manifest

outputs/reports/
  phase1a_ltm_paper_parity_report.md
  phase2_metrics_harness_completion.md
  phase3_teacher_data_report.md
```

Phase3 已有 edge-label rows、PIBT trace schema、map-holdout split 和 residual 主路线。CBR-LTM 只需在 Phase4 增加 counterfactual label generator，不推翻现有 teacher pipeline。

当前 `src/models`、`src/train`、`cpp/ntm` 仍基本为空，因此 Phase4 可以从模型、训练和 NTM runtime 三个最小模块干净开始。

### 2.5 Phase4：模型与训练

Phase4 目标：

- 建立最小但具有 closed-loop 含义的 residual + ranking + safety pipeline。
- 输入：LTM traffic map、PIBT trace-derived features、local bottleneck context。
- 输出：`delta_weight`、`action_rank_score`、`safety_gate`。
- 训练目标：预测 closed-loop useful correction，而不是拟合 LTM weight。

建议新增模块：

```text
src/models/cbr_ltm.py
src/train/train_cbr_ltm.py
src/train/losses_cbr.py
src/czr004_teacher/counterfactual.py
src/eval/eval_cbr_offline.py
configs/phase4/cbr_ltm.yaml
outputs/reports/phase4_cbr_ltm_plan.md
outputs/reports/phase4_cbr_ltm_report.md
```

Edge-level features：

- `from_id`, `to_id`
- `from_x`, `from_y`, `to_x`, `to_y`
- `edge_direction` one-hot
- `from_degree`, `to_degree`
- `is_corridor_edge`
- `is_bridge_like_edge`
- `local_free_cell_ratio_radius_1/2/3`
- `local_bottleneck_score`

LTM / trace features：

- `ltm_raw_count`
- `ltm_normalized_weight`
- `committed_count`
- `blocked_count`
- `blocked_to_committed_ratio`
- `wait_propagated_count`
- `goal_wait_ignored_count`
- `last_restart_committed_count`
- `last_restart_blocked_count`

Solver context features：

- map-name embedding 或 map-holdout-safe topology stats
- `agents`
- `density = agents / free_cells`
- `iteration_index`
- `time_budget_remaining`
- `current_best_sol_ratio`
- `last_iteration_improved_solution`
- `last_iteration_ttfs_ms`
- `last_iteration_high_level_expansions`
- `last_iteration_low_level_pibt_calls`

Candidate-ranking features：

- `agent_current_vertex`
- `candidate_to_vertex`
- `candidate_shortest_distance`
- `candidate_ltm_distance`
- `candidate_rank_ltm`
- `candidate_is_wait`
- `candidate_caused_blocked_event_before`
- `candidate_edge_delta_context`

模型输出三个 head：

- `delta_head`：预测 `delta_e in [-dmax, dmax]`，并使用 `w_cbr(e) = clamp(w_ltm(e) + gate_e * delta_e, 0, 10)`。
- `rank_head`：输出 `score(a, candidate)`，用于 PIBT candidate tie-breaking 或 ranking bias。
- `safety_head`：输出 `p_enable(e or local region)` 与 `p_harmful(e or local region)`；只有 calibrated confidence 过阈值时 `gate_e = 1`。

Counterfactual 数据生成采用 sampled probe，避免全图全组合爆炸：

```text
for each Phase3 run:
  load map, instance, LTM trace summary
  identify top-K bottleneck regions:
    high blocked_count
    high wait_propagated_count
    high edge betweenness proxy
    high LTM weight
    high local density

  for sampled restart states or replay checkpoints:
    run short-budget probes:
      baseline: LTM
      +delta group: increase selected edge group by eps
      -delta group: decrease selected edge group by eps
      rank-only: prefer alternate action around bottleneck
      safety-off: force model-like correction
    record:
      delta_ratio
      delta_auc_proxy
      delta_ttfs
      delta_returned_solutions
      delta_expanded_nodes
      solver_success
```

Counterfactual label examples：

- `beneficial_delta_e`：改善 short-budget SoL ratio 或 AUC 的方向。
- `pairwise_action_label`：若 candidate_i 对 probe outcome 更好，则 candidate_i 优于 candidate_j。
- `harmful_region_label`：若 perturbation 导致 TTFS / success 退化，则标为 harmful。

Phase4 成本控制：

- `time_limit_sec = 1, 2, 3`
- `max_probe_edges_per_run = 128`
- `max_probe_regions_per_map = 32`
- `probe_methods = {ltm, +eps, -eps, rank_alt}`

训练目标：

```text
L =
  λ_rank * pairwise_ranking_loss
+ λ_cf   * counterfactual_direction_loss
+ λ_res  * smooth_l1(delta_pred, delta_cf_target)
+ λ_safe * safety_bce_loss
+ λ_reg  * residual_magnitude_regularization
+ λ_mono * bottleneck_monotonicity_regularization
```

各 loss 含义：

- `pairwise_ranking_loss = max(0, margin - s(good_action) + s(bad_action))`
- `counterfactual_direction_loss = CE(sign(delta_pred), sign(best_probe_delta))`
- `safety_bce_loss`：harmful perturbation 禁用 NTM；neutral / beneficial perturbation 允许 NTM。
- `residual_magnitude_regularization`：除非有强 counterfactual evidence，否则保持 `||delta||` 小。

`ltm_normalized_weight` 可以用于 warm start，但只能作为预训练：

- Stage 4.0：训练 edge encoder 重构 LTM weight，作为 representation warm-up。
- Stage 4.1：冻结或 fine-tune，使用 counterfactual + ranking + safety losses。
- Stage 4.2：从主目标移除 regression loss，或只保留很小的 `λ`。

Offline validation 只作为诊断，不作为主贡献：

- held-out map：例如 `maze-32-32-4` 或 Phase3 test map。
- held-out seed：同 map family 的 unseen scenario seeds。
- density extrapolation：低 agent count 训练，高 agent count 测试。
- 指标：
  - pairwise ranking accuracy
  - counterfactual direction accuracy
  - safety calibration ECE
  - harmful-perturbation recall
  - residual magnitude distribution
  - nonzero residual edge ratio
  - bottleneck subset performance

Phase4 gate：

- Gate A：相对 `delta=0` baseline，counterfactual direction accuracy 明显高于随机。
- Gate B：safety head 对 harmful probes 有较高 recall，优先保证不伤害 TTFS / success。
- Gate C：ranking head 在 bottleneck candidate pairs 上优于 LTM ranking-only baseline。
- Gate D：residual magnitude 不塌缩到全 0，也不饱和到全 `±dmax`。

若 Phase4 只得到好看的 edge-weight MAE，但 counterfactual / ranking / safety 全无效，不能进入 Phase5 主线，只能保留为 diagnostic。

### 2.6 Phase5：solver-level 集成

接入位置：

```text
LaCAM* iteration
  -> PIBT trace collection
  -> UpdateLTM
  -> CBR-LTM inference
  -> w_cbr = clamp(w_ltm + gate * delta, 0, 10)
  -> WeightedDistanceTable recompute
  -> PIBT candidate ranking uses weighted distance + rank_score tie-break
  -> run next restart
```

建议新增 C++ 模块：

```text
cpp/ntm/cbr_ltm_runtime.hpp
cpp/ntm/cbr_ltm_runtime.cpp
cpp/ntm/cbr_ltm_features.hpp
cpp/ntm/cbr_ltm_features.cpp
cpp/ltm/ltm_ntm_adapter.hpp
cpp/ltm/ltm_ntm_adapter.cpp
```

必须保持的不变量：

- `candidate domain = neigh(v) union {v}`
- 不删除合法动作。
- 不绕过 vertex conflict。
- 不绕过 edge swap conflict。
- 不绕过 priority inheritance / backtracking。
- 不改变 high-level `OPEN` / `EXPLORED` / `parent` / `incumbent` semantics。

CLI / config：

```text
--method lacam_star
--method lacam_star_ltm
--method lacam_star_ltm_cbr
--ntm-disable
--ntm-safety-only
--ntm-delta-zero
--ntm-ranking-only
```

Fallback 检查：

- CBR disabled：output-level parity with `LaCAM*+LTM`。
- `delta=0` 且 ranking off：exact LTM behavior。
- LTM disabled：upstream LaCAM* behavior。

推理频率必须比较：

- every restart
- every K restarts, `K={2,4,8}`
- post-first-solution only
- dense / bottleneck-triggered only
- cached per-map inference
- CPU inference
- GPU batch inference

推荐默认：

```text
default = post-first-solution + bottleneck-triggered + cached CPU inference
```

理由：TTFS 不能被神经推理拖慢；LTM 主要价值是 anytime refinement，CBR-LTM 的主战场也应是 post-first-solution improvement。

Phase5 消融：

- LTM only
- LTM + pure edge regression residual
- LTM + CBR residual only
- LTM + CBR ranking only
- LTM + CBR residual + ranking
- LTM + CBR residual + ranking + safety
- CBR without blocked features
- CBR without wait-propagation features
- CBR without bottleneck features
- CBR every restart
- CBR every K restarts
- CBR post-first-solution only

Phase5 gate：

- fallback parity: pass
- candidate domain exhaustive tiny graph test: pass
- TTFS degradation: `<= 10%` on smoke，或 safety 在 first solution 前禁用 CBR。
- success@30s: 不低于 LTM on smoke。
- equal-node comparison: CBR-LTM 在 dense / bottleneck smoke 上不弱于 LTM。
- `planning_overhead_ms`: 显式报告。

### 2.7 Phase6：主实验

主表沿用 LTM 论文口径：

- one-shot MAPF
- 8 maps
- 每图 25 instances
- 30s
- `sum_of_loss_ratio`

methods：

- `LaCAM*`
- `LaCAM*+LTM`
- `LaCAM*+LTM+CBR`
- `TO/SUO` 仅在 auditable implementation 可用时纳入；否则标注 unavailable / not reproduced。

Anytime curve 必须画：

- ratio vs wall-clock
- incumbent improvements over time
- quality-time AUC
- returned_solutions_count@30s
- TTFS

Planning-and-execution：

- `E = {0.1, 0.5}`
- `X = {5, 10, 20}`

CBR-LTM 预期优势场景：

- high density
- random / warehouse bottleneck
- post-first-solution refinement
- planning-and-execution repeated replanning

证明收益不是伪收益，必须报告：

- equal-wallclock
- equal-node
- expanded_nodes
- high_level_expansions
- low_level_pibt_calls
- ntm_inference_count
- planning_overhead_ms
- random seed paired delta
- per-map grouped delta
- dense / bottleneck subset delta

Phase2 已支持 paired statistical tests 和这些 schema 字段，后续直接复用，不另写统计脚本。

Phase6 gate：

- CBR-LTM 不要求平均大幅超过 LTM。
- 合理正结果包括：
  - overall mean ratio 与 LTM 打平；
  - dense / bottleneck subset 明显更好；
  - TTFS 不坏；
  - AUC 更好；
  - equal-node 不劣；
  - planning-and-execution 更稳；
  - overhead 可解释。

预期论文贡献叙事：

1. We introduce CBR-LTM, a learning-enhanced traffic-map correction method that learns counterfactual residuals over LTM directed edge costs instead of imitating LTM weights.
2. We derive solver-facing supervision from short closed-loop `LaCAM*+LTM` probes, producing residual, ranking, and safety labels tied to SoL ratio, AUC, and TTFS.
3. We integrate CBR-LTM into `LaCAM*+LTM` without changing PIBT legality, candidate domains, or high-level search semantics, with exact fallback to LTM.
4. Experiments show that learned traffic-map corrections can improve dense / bottleneck anytime behavior while preserving LTM's low-overhead online nature.

风险：

- counterfactual probe 成本高。
- short-budget probe label 噪声大。
- 模型只学到 map-specific bias。
- safety gate 过保守。
- 推理 overhead 吞掉收益。

保底路径：

- 只启用 post-first-solution。
- 只启用 bottleneck-triggered edges。
- only residual, ranking off。
- only safety gate, delta off。
- every K restarts。
- `delta=0` fallback。
- 保留为 diagnostic，不称为主贡献。

---

## 3. 备选方案二：LAUR-LTM

### 3.1 名称

英文名：`LAUR-LTM: Learned Adaptive Update-and-Restart Lightweight Traffic Map`

中文名：学习式自适应更新与重启选择的 Lightweight Traffic Map

与 CBR-LTM 的区别：

- CBR-LTM 是“在 LTM 生成后修正边权和排序”。
- LAUR-LTM 是“学习 LTM 的 update rule 和 restart-node selection”。
- LAUR-LTM 直接攻击 LTM 论文的薄弱点：traffic map update 是手工 additive rule，restart selection 仍有可设计空间。

### 3.2 核心思想

LAUR-LTM 不输出最终 edge weight，而是输出 update parameters：

- committed action increment gain
- blocked action increment gain
- wait propagation gain
- decay factor
- local saturation factor
- directional contraflow penalty
- bottleneck spillover radius
- restart-node score
- safety / fallback score

也就是把 LTM 的：

```text
for every committed / blocked action:
  raw_count[e] += 1
normalize to [0,10]
```

改成：

```text
for every trace event:
  raw_count[e] = rho_local * raw_count[e] + alpha_event(context) * event_signal
normalize with learned local saturation
```

同时，当前 `cpp/ltm` one-shot implementation 记录了 root restart 是当前实现偏差；LTM 论文中 restart node 原则上可以从当前 search tree 中选择，并指出沿 solution branch 的节点更可能带来 improved solutions。LAUR-LTM 把 `SelectRestartNode` 作为 learning-enhanced LTM 的第二个切入点，但仍只在 LTM frequent restart loop 中选择合法 restart node，不改搜索语义。

### 3.3 与相关工作的联系

与 GGO：

- IJCAI 2024 GGO 明确提出 guidance graph edge weights 可以被直接优化，也可以由 update model 生成 edge weights。
- LAUR-LTM 把“update model”具体化为 LTM 的 online trace-to-traffic update rule。

与 OGGO：

- OGGO 针对 real-time traffic patterns 优化动态 guidance policy，并把它用于 PIBT。
- LAUR-LTM 不换成 lifelong MAPF，但借鉴“traffic pattern -> adaptive guidance”的思想，用 LaCAM* restart-level history 调整 LTM update。

与 Real-Time LaCAM：

- Real-Time LaCAM 强调跨迭代保留历史并在下一轮继续使用。
- 它说明增量式保留 LaCAM search history 可以在 planning-execution 场景中保持完整性与实用性，也展示 learned policy 可以通过 PIBT / search shield 使用。
- LAUR-LTM 不做 real-time LaCAM，而是把“跨迭代记忆”转成 learned traffic map update。

与 Hypergraph / higher-order learning：

- 瓶颈往往不是单条 edge 或 pairwise agent interaction，而是 corridor、intersection、room exit 这样的 group interaction。
- ICLR 2026 HMAGAT 强调高阶交互对密集 MAPF 的重要性。
- LAUR-LTM 可把 local region / bottleneck group 作为 update context，但不需要引入重型 HGNN solver。

### 3.4 Phase0-Phase3 资产复用

LAUR-LTM 比 CBR-LTM 更依赖 PIBT raw trace。

Phase3 报告已定义 raw PIBT trace schema：

- `run_id`
- `iteration`
- `event_index`
- `kind`
- `agent_id`
- `from_id`
- `to_id`
- `at_goal`

Phase3 默认保存 derived edge labels，raw traces 在启用时放在 ignored `artifacts/teacher/traces/`。

Phase4 不需要重做 Phase3，只需要：

- 在 Phase3 generator 中打开 raw trace export。
- 新增 update-sequence labels。
- 保留现有 edge-label manifest。
- 继续使用 map-holdout split。

直接复用：

```text
cpp/ltm/ltm.cpp
  UpdateLTM
  PibtTraceCollector
  DirectedTrafficMap

src/czr004_teacher/schema.py
  扩展 event sequence schema

src/czr004_metrics/
  统一评估

Phase1a full batch
  提供 LTM strong baseline
```

`cpp/ltm` 已有 `CMakeLists.txt`、`ltm.cpp`、`ltm.hpp`、`phase1_ltm_smoke.cpp`，因此 LAUR-LTM 的 C++ 修改应是 adapter 扩展，而不是推翻 LTM 实现。

### 3.5 Phase4：模型与训练

Phase4 目标：

- 训练轻量 trace-to-update model。
- 输入：PIBT event sequence、当前 LTM state、local topology、restart outcome。
- 输出：下一轮 LTM update parameters、restart node score、safety gate。
- 主贡献不是“预测边权”，而是学习 LTM 的 online update rule。

建议新增模块：

```text
src/models/laur_ltm.py
src/train/train_laur_ltm.py
src/train/losses_laur.py
src/czr004_teacher/update_sequences.py
src/czr004_teacher/restart_labels.py
src/eval/eval_laur_offline.py
configs/phase4/laur_ltm.yaml
outputs/reports/phase4_laur_ltm_plan.md
outputs/reports/phase4_laur_ltm_report.md
```

Event-level input：

- event kind:
  - committed
  - blocked
  - wait-propagated
  - goal-wait-ignored
- edge:
  - `from_id`, `to_id`, direction
  - local degree
  - corridor / room / intersection proxy
- agent context:
  - `at_goal`
  - `distance_to_goal`
  - priority rank if available
  - candidate rank before block
  - blocked reason if instrumented:
    - vertex occupancy
    - swap conflict
    - failed priority inheritance recursion

Traffic state input：

- current raw_count
- current normalized_weight
- last_restart raw_count_delta
- blocked_to_committed_ratio
- edge usage entropy
- local traffic concentration

Restart context：

- `iteration_index`
- current best ratio
- last iteration improved solution
- last iteration found first solution
- node budget used
- high_level_expansions
- low_level_pibt_calls
- candidate restart depth
- node on incumbent branch?
- node generated before improvement?

Topology / bottleneck context：

- local free-cell count
- cut-vertex proxy
- edge betweenness proxy
- corridor width
- degree histogram radius 2 / 3
- local agent density

模型输出：

- `alpha_commit(e, context) in [0, alpha_max]`
- `alpha_block(e, context) in [0, alpha_max]`
- `alpha_wait(v, context) in [0, alpha_wait_max]`
- `rho_decay(e, context) in [0,1]`
- `saturation_scale(region) in [0,10]`
- `spillover_radius(region) in {0,1,2}`
- `contraflow_penalty(e reverse pair)`
- `restart_score(node)`
- `safety_enable_update`

实际 update：

```text
raw_count_next[e] =
  rho_e * raw_count[e]
  + alpha_commit_e * committed_count[e]
  + alpha_block_e * blocked_count[e]
  + alpha_wait_e * wait_propagated_count[e]
  + alpha_contraflow_e * reverse_conflict_count[e]

w_laur[e] = normalize_or_sigmoid(raw_count_next[e], local_saturation)
w_laur[e] = clamp(w_laur[e], 0, 10)
```

数据生成方式：

LAUR-LTM 需要 update-level labels，而不是 static edge labels。

```text
for each Phase3 / newly generated trace:
  replay LTM iteration by iteration
  at each restart iteration t:
    collect trace segment H_t
    collect LTM state W_t
    collect outcome after next run:
      improved_solution?
      delta_ratio
      delta_auc_proxy
      TTFS if first solution
      expansions
      low_level_pibt_calls
```

LAUR-LTM 更适合做 update-rule candidate probes，而不是像 CBR-LTM 那样对每条 edge 做 perturbation。

candidate update rules：

- LTM additive baseline
- commit-heavy
- block-heavy
- wait-light
- wait-heavy
- decay-0.9
- decay-0.7
- local-saturation-low
- contraflow-penalty
- bottleneck-spillover

对每个 restart checkpoint 只跑少量 candidate update rule：

```text
run next short-budget LaCAM*+updated-LTM
record which update rule improves downstream solver behavior
```

得到 labels：

- `best_update_rule_class`
- `beneficial_alpha_commit / alpha_block direction`
- `harmful_update_label`
- `restart_node_preference_label`

训练目标：

```text
L =
  λ_rule  * update_rule_classification_loss
+ λ_rank  * restart_node_pairwise_ranking_loss
+ λ_delta * downstream_delta_regression_loss
+ λ_safe  * harmful_update_safety_loss
+ λ_reg   * deviation_from_LTM_regularization
+ λ_decay * stability_regularization
```

关键是 `deviation_from_LTM_regularization`：如果没有强证据，LAUR-LTM 应退回 simple additive LTM。这样模型天然更安全，不会为了训练误差大幅扭曲 traffic map。

Offline validation：

- update-rule selection accuracy
- restart-node pairwise accuracy
- harmful-update recall
- predicted improvement vs actual short-probe improvement Spearman correlation
- mean absolute deviation from LTM
- saturation frequency
- decay distribution
- alpha_commit / alpha_block distribution
- held-out map generalization
- density extrapolation

注意：不要把 `w_laur` 的 MAE 作为主结果，因为 LAUR-LTM 的目标不是拟合 LTM 权重。

Phase4 gate：

- Gate A：update model 在 held-out map 上能识别 harmful update，safety recall 过线。
- Gate B：learned update rule 在 short-probe replay 中优于 simple additive LTM 的次数显著多于随机。
- Gate C：restart_score 至少能区分 incumbent-improving branch vs neutral branch。
- Gate D：模型输出稳定：
  - clamp saturation 不频繁；
  - decay 不全为 1；
  - alpha 不全退化为 additive baseline。

如果 restart labels 噪声太大，Phase4 可以先只做 learned update，不做 restart scorer。

### 3.6 Phase5：solver-level 集成

接入位置：

```text
LaCAM* run
  -> collect PIBT history H_t
  -> LAUR update model predicts update parameters
  -> update DirectedTrafficMap
  -> recompute WeightedDistanceTable
  -> optional LAUR restart scorer selects restart node
  -> next LaCAM* run
```

这和 LTM Algorithm 1 完全同构：

```text
run -> collect history -> update traffic map -> select restart node -> next iteration
```

CLI / config：

```text
--method lacam_star_ltm
--method lacam_star_ltm_laur
--laur-disable
--laur-update-only
--laur-restart-only
--laur-safety-only
--laur-force-additive
--laur-root-restart
```

Fallback：

- LAUR disabled：exact `LaCAM*+LTM`。
- LAUR update disabled：original additive `UpdateLTM`。
- LAUR restart disabled：original root / LTM restart policy。
- safety failed：use additive LTM update and root restart。

必须保持的不变量：

- candidate domain 不变。
- PIBT legality 不变。
- LaCAM* high-level semantics 不变。
- legal child 不删除。
- edge weights bounded `[0,10]`。
- fallback exact。

LAUR-LTM 更安全的一点是：它甚至不直接改 PIBT candidate score，只改下一轮 traffic map 和 restart node。

Phase5 消融：

- LTM additive update
- LAUR learned update only
- LAUR learned restart only
- LAUR update + restart
- LAUR without blocked events
- LAUR without wait propagation
- LAUR without decay
- LAUR without contraflow feature
- LAUR without bottleneck topology
- LAUR safety off
- LAUR every restart
- LAUR every K restarts
- LAUR post-first-solution only

Phase5 gate：

- fallback parity pass。
- `UpdateLTM` unit tests still pass under force-additive mode。
- weights remain in `[0,10]`。
- candidate domain exhaustive tests pass。
- TTFS not worse than LTM by more than smoke threshold。
- learned update gives at least one dense / bottleneck smoke win under equal-node。
- restart scorer does not reduce success@30s。

### 3.7 Phase6：主实验

主表：

- `LaCAM*`
- `LaCAM*+LTM`
- `LaCAM*+LTM+LAUR`
- `TO/SUO` 仅在有 auditable implementation 时加入；否则继续标注 unavailable。

LAUR-LTM 重点实验：

- post-first-solution anytime refinement
- planning-and-execution stability
- dense corridor / warehouse map
- cross-density generalization
- restart behavior

Phase6 额外分析：

- restart-source analysis:
  - root restart vs incumbent-branch restart vs LAUR restart
- update-dynamics analysis:
  - additive count growth curve
  - learned decay curve
  - block/commit gain ratio
  - wait propagation gain
  - bottleneck saturation distribution
- traffic-map visualization:
  - LTM heatmap vs LAUR heatmap
  - edges increased by blocked events
  - edges decayed after resolved congestion

证明收益不是伪收益，必须报告：

- equal-wallclock
- equal-node
- same restart budget
- same inference budget
- same Phase2 metric code
- paired sign test
- bootstrap CI
- per-map grouped delta
- dense / bottleneck subset
- planning overhead

特别要证明 LAUR-LTM 不是“多搜了几轮”。Phase2 已要求 `expanded_nodes`、`high_level_expansions`、`low_level_pibt_calls`，LAUR 方案必须强制使用这些字段。

Phase6 gate：

- LAUR-LTM 平均 ratio 打平 LTM 即可。
- 至少满足一个增强结论：
  - dense / bottleneck subset 更好；
  - anytime AUC 更好；
  - P&E 更稳；
  - low-density train -> high-density test 更好；
  - restart efficiency 更高；
  - equal-node 不劣。

如果 learned restart 不稳定，但 learned update 有收益，论文主方法可降级为：

```text
LAU-LTM = learned adaptive update only
```

restart scorer 降级为 ablation / negative result。

预期论文贡献叙事：

1. We propose LAUR-LTM, a learned update-and-restart extension of Lightweight Traffic Map that learns how PIBT trace events should modify traffic costs, rather than imitating final LTM edge weights.
2. We formulate LTM enhancement as trace-to-update learning with delayed solver outcomes, including committed / blocked / wait-propagated events, local bottleneck context, and restart-level improvement signals.
3. We integrate learned update parameters and restart scoring into the original LTM anytime loop without changing LaCAM* search semantics or PIBT legality, preserving exact fallback to additive LTM.
4. Experiments show whether learned update dynamics can improve dense and planning-and-execution MAPF while keeping LTM's online and low-overhead character.

风险：

- raw trace export 数据量大。
- restart label 噪声高。
- learned update 不如 additive LTM 稳。
- closed-loop distribution shift。
- update-rule probes 成本高。
- learned decay 可能过度遗忘有用拥堵信息。

保底路径：

- 只做 learned update，不做 restart scorer。
- 只启用 post-first-solution。
- 只在 dense / bottleneck trigger 启用。
- decay 固定，只学 `alpha_commit / alpha_block`。
- safety gate 默认 additive LTM。
- every K restarts。
- 保留 negative result：simple additive LTM 很强，learned update 未显著改善。

---

## 4. 两个方案对比

| 维度 | CBR-LTM | LAUR-LTM |
|---|---|---|
| 核心机制 | 对 LTM edge cost 做 counterfactual residual，并直接影响 weighted distance / candidate ranking | 学习 LTM 的 update rule 和 restart-node selection |
| 与 Phase3 兼容度 | 最高，Phase3 已经明确 `online_residual` 是 primary route | 中高，需要打开 raw trace export，并新增 update-sequence labels |
| 创新性 | 高：counterfactual solver-facing residual，避免 pure distillation | 更高：学习 LTM update dynamics，直接填补 LTM additive rule 的方法空白 |
| 实现难度 | 中等 | 较高 |
| 预期 closed-loop 收益 | 较稳，尤其 dense / bottleneck 和 post-first-solution | 潜在更强，尤其 P&E / anytime / restart efficiency |
| 风险 | counterfactual labels 成本和噪声 | trace 数据量、restart label 噪声、closed-loop shift |
| 论文叙事 | 清晰：learned residual correction over LTM | 更有研究味：learned traffic-map update policy |
| 最小可交付性 | 强 | 中等 |
| 失败保底 | residual=0 / safety gate / ranking-only | additive LTM fallback / learned update-only |

GPTPro 推荐：

- 首选：CBR-LTM。
- 备选：LAUR-LTM。

推荐理由：

- CBR-LTM 更贴合当前 Phase3 已确定的 `online_residual` 路线。
- CBR-LTM 能最快进入 Phase4。
- CBR-LTM 最容易证明“不是拟合 LTM edge weights”。
- CBR-LTM 的 counterfactual labels 和 safety gate 足以把学术贡献从 teacher distillation 拉到 solver-facing learning。
- LAUR-LTM 创新性更强，但工程和实验风险更高。
- LAUR-LTM 适合作为第二条备选，或在 CBR-LTM 跑通后，把 learned update-only 部分作为增强版 Phase4.5 / Phase5 ablation。

建议执行安排：

- Phase4：
  - 先做 CBR-LTM offline + short-probe counterfactual labels。
  - 同时预留 LAUR raw trace export 开关。
- Phase5：
  - CBR-LTM 先集成到 solver。
  - 若 CBR 稳定，再实现 LAUR update-only，不急着做 learned restart。
- Phase6：
  - 主实验以 CBR-LTM 为主方法。
  - LAUR-LTM 若 closed-loop 有正收益，则作为第二贡献。
  - LAUR-LTM 若失败，则作为 learned update dynamics negative / diagnostic study，不影响主线。

一句话总结：

- CBR-LTM 解决“NTM 只是拟合 LTM 权重”的最稳方式，是把监督信号改成 counterfactual solver improvement。
- LAUR-LTM 解决同一问题的更强方式，是让模型学习 LTM 的在线 update rule，而不是学习 update 后的权重。

