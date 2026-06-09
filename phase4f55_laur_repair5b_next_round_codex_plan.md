# czr004 LAUR Repair5B：Phase4F / Phase5.5 下一轮 Codex 指导计划

**版本**：2026-05-29
**目标分支**：`phase4f5p5-stable-attention-lau`
**最新参考提交**：`7bf0b0ad077e2d26ca78dbb0133d167b24d5b62f`
**阶段定位**：`Phase4F.4 -> Phase5.5-update`
**唯一主线**：LAUR / learned `UpdateLTM`，用学习增强替换 LTM 中简单的加法更新规则，并在闭环性能上超过 `LaCAM*+LTM`。

---

## 0. 总原则：方向不变，gate 不放松，但研发判断要分层

当前阶段不要切换到其它候选路径，不做 agent-action policy，不做 learned restart，不替换 PIBT，不改 LaCAM* 的 collision / candidate / pruning / rewrite 语义。所有学习只发生在 **LTM update / LAUR UpdateLTM rule or parameter guidance** 层。

最终目标仍然是：

```text
LaCAM*
  -> LaCAM* + LTM
  -> LaCAM* + LAUR learned UpdateLTM
```

LAUR 必须证明：

```text
1. offline Phase4F / Repair5 strict gate 可过；
2. Phase5.5 runtime parity / safety 可过；
3. closed-loop 中至少在 hard / dense / high-opportunity cases 上超过 LTM 简单加法更新；
4. 最终才允许进入 Phase6。
```

**不要降低最终 gate。**

但是研发阶段不要把所有判断都做成一个硬门。建议继续使用三层判断：

```text
development diagnostic gate:
  判断方向是否值得继续；不允许 runtime。

promotion-candidate gate:
  判断是否值得较长训练或小规模 Phase5.5 smoke planning；不允许最终 claim。

runtime / paper-claim gate:
  严格 gate，不放松；需要 multi-seed + later closed-loop evidence。
```

### 0.1 2026-05-31 GPTPro/Claude 口径合并：论文评价和工程放行分离

GPTPro/Claude 新讨论的核心结论纳入本计划，但解释为 **评价口径分层**，不是 Phase5.5 放行门放松：

```text
Claude/GPTPro 合理部分：
  Repair5 attention-native label 不是 Repair3 stable hard target；
  全量 8-class top1 不能继续作为 Repair5 研发主 KPI；
  closed-loop learned benefit over additive LTM 是最终论文主 gate；
  high-margin capture / utility regret / selected_vs_additive_delta
  比单纯 hard-label top1 更贴近 LAUR 目标。

必须修正的部分：
  closed-loop 论文 gate 不能替换 Phase5.5 工程 gate；
  offline safety / anti-escape / parity / multi-seed 不能被绕过；
  当前 Repair5 只有方向性信号，还没有稳定投稿 candidate；
  diagnostic closed-loop preflight 不等于 runtime promotion。
```

因此从本轮开始，Repair5B 的 gate 解释固定为四层：

```text
A. Development / research-triage gate
   Purpose:
     判断是否值得继续训练、调 label、做 failure analysis。
   Primary signals:
     schema/split/audit clean
     top3 >= 0.60, or approaching 0.65 with clear positive delta
     harmful recall >= 0.70
     harmful precision >= 0.25
     mean selected_vs_additive_delta > 0
     high-margin capture better than always-additive / Repair3 reference
     utility regret to oracle is explainable
   top1:
     diagnostic only, not the Repair5 research kill switch.
   Meaning:
     no runtime permission; no Phase5.5 permission; no Phase6 evidence.

B. Promotion-candidate / diagnostic preflight gate
   Purpose:
     判断是否值得准备 tightly scoped diagnostic closed-loop preflight。
   Required signals:
     top3 >= 0.65
     harmful recall >= 0.78
     harmful precision >= 0.28
     mean selected_vs_additive_delta > 0
     anti-escape improves vs additive/defer and Repair3 reference
     high-margin opportunity capture >= 0.30 or clearly above reference
     utility regret acceptable and explainable
   Meaning:
     may plan diagnostic closed-loop preflight only;
     not Phase5.5 runtime promotion;
     not final success.

C. Runtime / Phase5.5 engineering gate
   Purpose:
     决定 learned LAUR 是否能进入 Phase5.5 parity/smoke。
   Rule:
     original Phase4F or formally approved utility-equivalent gate
     attention-native gate
     harmful recall >= 0.80
     harmful precision >= 0.30
     anti-escape hard pass or behaviorally equivalent proof
     final multi-seed evidence
     force-additive / defer parity clean
     deterministic export
     no solver semantic change
   Meaning:
     unlocks Phase5.5 parity/smoke only;
     still not Phase6 learned-benefit claim.

D. Phase6 / paper-claim gate
   Purpose:
     支撑论文主张。
   Required evidence:
     closed-loop > additive LTM / LaCAM*+LTM on success, SoL ratio,
       anytime AUC, expanded nodes, TTFS, and overhead-adjusted utility
     multi-map / multi-seed statistics
     ablations without learned LAUR, without anti-escape, without safety,
       Repair3 baseline, and additive LTM baseline
```

如果触发 diagnostic closed-loop preflight，必须写清：

```text
not Phase5.5 permission
not runtime promotion
not Phase6 evidence
hard safety mask enabled
force-additive/defer parity checked
only measures offline-to-closed-loop transfer
```

---

## 1. 当前 GitHub 最新证据总结

### 1.1 数据扩展已经有效，不是数据管线坏了

新提交中 expand5000 / high-token label audit 已经通过。关键事实：

```text
sample_count = 4956
train / validation = 4194 / 762
validation high-margin opportunity count = 310
validation non-additive opportunity count = 483
schema_error_count = 0
split_leakage_error_count = 0
uses_raw_trace_tokens = true
```

target rule 分布在 validation 中不是单一类：

```text
block_heavy: 171
commit_heavy: 167
wait_light: 118
wait_heavy: 104
decay_095: 69
block_light: 65
decay_090: 45
None: 23
```

这说明 Repair5 不是没有 non-additive 学习机会。expand5000 分支里：

```text
use_nonadditive = 3274
defer_ltm = 1682
nonadditive_opportunity_rate = 0.6606
high_margin_nonadditive_opportunity_rate = 0.4691
```

因此，下一轮不要再先怀疑 “完全没有信号”。更准确的判断是：

```text
信号存在；
但当前模型/目标/训练方式没有把 ranking + safety + anti-escape 同时打通。
```

### 1.2 当前 flat attention-native selector 没有过任何一层 gate

layered diagnostic 重新打分了 27 个 Repair5 summaries：

```text
development pass = 0
promotion-candidate pass = 0
strict seed pass = 0
Phase5.5 allowed = false
Phase6 allowed = false
```

这说明不能靠“稍微放宽早期 gate”解释当前失败。现在需要重构方法，而不是继续盲目扫 loss 权重。

### 1.3 当前正信号：局部指标已经能单独打通

已有 variants 可以单独打通某些子目标：

#### 例 1：anti-escape + top3 + precision 可以过，但 recall / top1 掉

`rawtrace_edge_sf_global_pair_neg2_anti2`：

```text
top1 = 0.2321
top3 = 0.7065
harmful recall = 0.5767
harmful precision = 0.3134
mean delta = 0.0021
anti_escape = true
high_margin_capture = 0.4378
opportunity_nonadditive_selection_rate = 0.5939
```

解释：

```text
模型可以学会不逃避 additive；
也可以让 top3 接近/超过 0.70；
但 aggressive non-additive selection 让 harmful recall 崩。
```

#### 例 2：high-token + expand5000 接近 top3 和 precision，但 recall / anti 不稳

`expand5000_hightoken_ht_mlp_target_global`：

```text
top1 = 0.1449
top3 = 0.6998
harmful recall = 0.7623
harmful precision = 0.3143
mean delta = 0.0009
anti_escape = false
high_margin_capture = 0.2839
opportunity_nonadditive_selection_rate = 0.4617
```

解释：

```text
高 token / 更多数据有一定帮助；
但仍无法同时做到 high-margin capture、recall、top1/top3。
```

### 1.4 当前核心失败模式

现在不是 “attention 完全没用”，而是 flat multi-task attention-native selector 把以下任务绑得太紧：

```text
A. 是否 defer_ltm / use_nonadditive；
B. use_nonadditive 后选哪个 rule；
C. 所选 rule 是否 harmful；
D. high-margin opportunity 上不能逃避；
E. mean delta 要正；
F. top1/top3 要过。
```

现象是：

```text
anti 强 -> recall / ranking 掉；
safety 强 -> anti / ranking 掉；
target-rule CE 强 -> top3 有时上来，但 anti / safety 不稳；
global safety calibration 可过 train，但 validation 泛化不够。
```

所以下一轮的核心不是“再扫 lambda”，而是：

```text
failure decomposition + hierarchical LAUR controller + per-rule safety + curriculum + hard-case mining
```

---

## 2. 对近两三年 AI / 机器人顶会工作的借鉴方式

这里的 “学习 LaGAT / 近期 AI 机器人顶会” 不是照搬任务、不是去学 agent action，也不是把 LAUR 变成 action policy。

应借鉴的是 **架构和实验范式**：

```text
1. hybrid learned guidance + classical planner safeguard；
2. learned module 不单独承担 correctness；
3. 分层 decision / safety / fallback；
4. map- or domain-specific fine-tuning；
5. hard-case mining / on-demand data aggregation；
6. attention 用于结构化 token 关系，而不是简单分类；
7. ablation 必须证明 learned component 有净贡献；
8. final claim 依赖 closed-loop 超过 strong baseline。
```

可让 Codex 阅读、吸收设计灵感的近期方向包括：

```text
LaGAT / graph-attention guided search:
  hybrid neural guidance + LaCAM, pretrain/fine-tune, deadlock/failure-triggered override。

Real-Time LaCAM:
  iterative replanning / constraints / learned policy interface 的安全化思路。

HiMAP / heuristic-informed MAPF learning:
  heuristic teacher、inference-time techniques、scalable decentralized guidance。

SACHA / heuristic-based attention:
  用 heuristic signals 引导 attention，而不是裸 attention。

Neural ATTF / learned heuristic + classical constraints:
  学习 heuristic，但保留 collision/dynamic constraints。

Octo / generalist robot policy:
  大规模预训练 + 少量 domain fine-tune；模块化 attention / data ablation。

Diffusion Policy / Causal Diffusion Policy:
  distributional / sequence-level prediction、temporal consistency、receding-horizon 思路；这里只能抽象为 LAUR update-sequence / uncertainty modeling，不能直接输出 robot action。

近期 VLA / dual-system robot policies:
  慢速大模型理解上下文 + 快速小模型执行动作的分层思想；在 LAUR 中可对应 “global map/traffic context encoder + fast per-rule update decoder”。
```

这些只作为 **inspiration**。任何尝试必须落回 czr004 约束：

```text
learned UpdateLTM only;
no agent-action policy;
no replacement of PIBT / LaCAM*;
no learned restart;
no conflict/candidate/pruning semantic change.
```

---

## 3. 优先级最高：Repair5B failure decomposition + oracle upper bound

### 3.1 为什么最优先

当前结果已经足以说明：

```text
数据管线有效；
机会样本足够；
attention 可以打通局部指标；
但不知道真正上限在哪里。
```

下一步必须先回答：

```text
如果有 oracle，它能不能明显超过 additive LTM / Repair3？
当前模型离 oracle 差在哪里？
是 safety classification 差？
是 rule ranking 差？
是 decision/defer 差？
还是八个旧 rule 的 action space 本身太粗？
```

如果 oracle 本身不明显强于 additive，继续训练更大网络没有意义；需要扩 action space 或学习 continuous/bounded update parameters。
如果 oracle 明显强于 additive，则说明 idea 有信号，只是当前模型没吃到。

### 3.2 Codex 具体任务

新增：

```text
src/eval/diagnose_laur_repair5_failure_modes.py
```

输出：

```text
outputs/reports/phase4f_repair5_failure_decomposition.md
outputs/reports/phase4f_repair5_failure_decomposition.json
outputs/tables/phase4f_repair5_failure_by_rule.csv
outputs/tables/phase4f_repair5_failure_by_map.csv
outputs/tables/phase4f_repair5_failure_by_opportunity.csv
outputs/tables/phase4f_repair5_oracle_gap.csv
```

### 3.3 必须比较的对象

```text
always_additive / always_defer_ltm
Repair3 stable-target MLP baseline
best completed Repair5 variant by top3
best completed Repair5 variant by recall
best completed Repair5 variant by anti-escape
best completed expand5000 high-token variant
oracle_best_safe_rule
oracle_best_safe_nonadditive_rule
oracle_defer_when_no_safe_opportunity
```

### 3.4 必须计算的指标

按 split / map / target rule / high-margin opportunity / harmful class 分组：

```text
rule_top1
rule_top3
safe_utility_top1
safe_utility_top3
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

### 3.5 Oracle 定义

```text
oracle_best_safe_rule:
  在所有 rule 中选 risk-adjusted utility 最高且不 harmful 的 rule；
  如果没有安全非 additive，允许 defer/additive。

oracle_best_safe_nonadditive:
  只在非 additive safe candidates 中选最高 utility；
  用于测量非 additive 学习上限。

oracle_defer_when_unsafe:
  只有当无 safe non-additive opportunity 时才 defer。
```

报告：

```text
oracle_vs_additive_mean_delta
oracle_vs_repair3_mean_delta
oracle_high_margin_capture_possible
oracle_harmful_rate
model_regret_to_oracle
oracle_capture_by_rule_family
```

### 3.6 决策

```text
if oracle_vs_additive_mean_delta <= small_epsilon
   or oracle_high_margin_capture_possible is low:
       当前八个 static rules 可能限制太强；
       优先尝试 bounded UpdateLTM parameter/residual head，而不是继续 rule selector。

else:
       继续 hierarchical attention-native LAUR。
```

---

## 4. 优先级最高：从 flat selector 改成 hierarchical LAUR controller

### 4.1 现有模型的问题

当前 `LAU-EdgeTraceTransformer-v4` 已经有 rule/context attention 和 multi-head：

```text
rule_score
delta_pred
harmful_logit
family_logits
opportunity_logit
defer_logit
```

但训练和选择仍然像 flat multitask scorer。多个目标互相拉扯，导致 anti、safety、ranking 无法共存。

### 4.2 新模型目标

新增或扩展模型：

```text
LAU-HierEdgeTraceTransformer-v5
```

仍然只做 LAUR / UpdateLTM。

### 4.3 模型结构建议

```text
global_context_encoder:
  global + map + density + iteration + traffic summary tokens

edge_trace_encoder:
  raw trace / edge tokens / topology features

rule_token_encoder:
  rule parameter tokens + rule family embeddings

cross_attention:
  rule tokens query edge/trace/context tokens

decision_head:
  defer_ltm vs use_nonadditive

safety_head:
  per-rule harmful probability

rule_rank_head:
  rank non-additive rules only

utility_head:
  selected-vs-additive utility / risk-adjusted utility

uncertainty_head optional:
  confidence / abstention reason
```

### 4.4 分层选择逻辑

```text
if decision_head says defer_ltm:
    select additive_ltm / defer_ltm
else:
    apply calibrated per-rule safety mask
    rank safe non-additive rules
    select best safe non-additive only if margin over additive/defer is sufficient
    otherwise defer with reason = insufficient_margin
```

必须记录：

```text
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

### 4.5 为什么这个方向优先

当前结果显示：

```text
anti-escape 过时 recall 掉；
recall 过时 anti/ranking 掉；
top3 过时 top1/safety 不稳。
```

这正是 flat multitask score 的症状。hierarchical controller 能让：

```text
decision / safety / ranking / utility
```

成为相对独立的可诊断模块。

---

## 5. 优先级最高：per-rule / per-family safety calibration

### 5.1 动机

当前 global safety threshold 经常出现：

```text
precision 过，recall 不过；
recall 过，precision 不过；
anti-escape aggressive selection 后 recall 崩。
```

这说明 harmful separability 可能按 rule family 不同。`wait_heavy`、`block_heavy`、`decay_090` 的 harmful 分布未必能用同一个 threshold 解决。

### 5.2 Codex 任务

新增：

```text
src/eval/calibrate_laur_repair5_per_rule_safety.py
```

输出：

```text
outputs/reports/phase4f_repair5_per_rule_safety_calibration.json
outputs/reports/phase4f_repair5_per_rule_safety_calibration.md
outputs/tables/phase4f_repair5_per_rule_safety_thresholds.csv
```

### 5.3 必须搜索

```text
threshold_by_rule:
  additive_ltm
  commit_heavy
  block_heavy
  block_light
  wait_light
  wait_heavy
  decay_095
  decay_090

threshold_by_family:
  additive
  commit
  block
  wait
  decay
```

目标不变：

```text
harmful recall >= 0.80
harmful precision >= 0.30
```

### 5.4 输出诊断

```text
global threshold pass/fail
per-rule threshold pass/fail
which rules cause false negatives
which rules cause false positives
anti-escape selected harmful false negative distribution
```

如果 per-rule safety 可以过，而 global 不过，说明当前失败是 calibration/heterogeneity，不是 LAUR idea 不 work。

---

## 6. 优先级高：curriculum，不要继续单阶段同时压所有 loss

### 6.1 当前问题

现在 loss 已经很丰富，但 simultaneous optimization 可能让目标互相打架：

```text
lambda_anti_escape high -> recall collapse
lambda_harmful high -> anti/ranking collapse
lambda_rule_ce high -> top3 improves, anti/safety unstable
```

### 6.2 建议训练 curriculum

新增配置目录：

```text
configs/phase4/generated_repair5_hier_curriculum/
```

#### Curriculum A：rank-first

```text
epochs 1-60:
  decision + rule ranking + utility
  anti_escape low
  harmful low

epochs 61-120:
  add harmful BCE + harmful pairwise
  calibrate safety on validation
  freeze or slow rule encoder if ranking collapses

epochs 121-180:
  add anti_escape / high-margin pressure
  reduce anti_candidate_safety if recall collapses
```

#### Curriculum B：safety-first

```text
epochs 1-60:
  harmful + high_margin_harmful + decision
  low anti_escape

epochs 61-120:
  add rule CE / rule margin / pairwise ranking

epochs 121-180:
  add anti_escape
  calibrate per-rule safety
```

#### Curriculum C：high-margin specialist diagnostic

```text
train ranking/safety only on high-margin safe non-additive opportunity subset
evaluate full validation
```

目的不是 runtime，而是回答：

```text
模型到底能不能学会核心 hard case？
```

### 6.3 Checkpoint selection

不要只按 anti 或 top3 选 checkpoint。选择分数应分阶段：

```text
early:
  rule_top3 + utility_regret + decision_accuracy

middle:
  top3 + harmful recall/precision balance

late:
  strict gate proxy + anti_escape + selected_vs_additive_delta
```

如果 late anti 过但 recall 崩，不要选。

---

## 7. 优先级高：stratified sampler / hard-case replay

### 7.1 动机

expand5000 validation target rule 分布仍然不均衡。模型容易偏向 `commit_heavy / block_heavy / wait_light`，对 `decay` / `wait_heavy` / `block_light` 的 safety/ranking 学不好。

### 7.2 Codex 任务

在 `train_laur_attention_native.py` 增加可选 sampler：

```text
--sampler stratified
```

按以下维度采样：

```text
split
map family
agent count bucket
target rule family
target rule
harmful positive / negative
high-margin opportunity
defer reason
anti_escape_sample
```

配置项：

```yaml
training:
  sampler: stratified
  high_margin_weight: 2.0
  harmful_positive_weight: 2.0
  rare_rule_weight: 2.0
  defer_reason_balance: true
```

### 7.3 Hard-case replay

从 failure decomposition 中抽取 hard cases：

```text
false_negative_harmful_selected
high_margin_avoidable_defer
wrong_rule_top1_but_top3_contains_target
top3_miss_high_utility
rule_family_confusion
```

生成：

```text
artifacts/teacher/laur/repair5_hardcase_index.jsonl
```

训练时以一定比例 replay hard cases。

---

## 8. 优先级中高：active data aggregation / hard-case mining

这部分借鉴的是近年 hybrid learning / robot learning 的做法：不是一次性造完数据，而是在模型暴露 failure 后补数据。

### 8.1 原则

仍然只在 Phase4F data/probe 层扩展，不回退 Phase1a/Phase2/Phase3，不改 solver semantics。

### 8.2 触发条件

如果 failure decomposition 发现：

```text
specific map family has high regret
specific rule family has high false-negative harmful
high-margin opportunity count is insufficient for some rule family
anti-escape passes but closed-loop utility low
```

则针对这些 bucket 生成新的 record/probe 数据。

### 8.3 输出

```text
configs/phase4/laur_ltm_repair5_hardcase_scenario_manifest.jsonl
configs/phase4/laur_ltm_full_repair5_hardcase.yaml
outputs/reports/phase4f_repair5_hardcase_data_audit.md
```

不要无脑扩到超大数据。先用 hard-case mining 提高有效样本密度。

---

## 9. 可探索方向：bounded UpdateLTM parameter / residual head

### 9.1 为什么值得考虑

如果 oracle 分析发现：

```text
八个 static rules 的 oracle gain 不够；
或者模型经常知道 additive 不好，但没有合适非 additive rule 可选；
```

那么问题可能是 action space 太粗，而不是 attention 不够强。

这时可以尝试仍然属于 LAUR 的连续/半连续 update 参数 head：

```text
predict bounded deltas for:
  alpha_commit
  alpha_block
  alpha_wait
  rho_decay
  saturation_scale
  contraflow_penalty
```

或者更安全：

```text
predict rule-family residual:
  base rule = additive_ltm or selected static rule
  learned bounded residual parameters = small deltas
```

### 9.2 必须严格限制

```text
no direct edge weight arbitrary output
no agent action
no learned restart
no PIBT/LaCAM* change
parameters bounded by conservative clamp
must have additive fallback
must pass oracle/offline/safety/anti gates before runtime
```

### 9.3 作为中优先级原因

它可能比继续在 8 个粗 rule 里做分类更有表达力；但 runtime parity 和 C++ export 会更复杂，所以应在 oracle 表明 static action space 不足后再做。

---

## 10. 可探索方向：近两年 AI / 机器人顶会结构灵感

这一节留给 Codex 更多探索空间。Codex 可以主动阅读近期论文并提出实现，但必须写入 design memo，不能直接大改主线。

### 10.1 可借鉴结构，不可照搬任务

可以借鉴：

```text
graph attention / cross-attention
set transformer / Perceiver-style latent tokens
dual-system policy
mixture-of-experts
curriculum / fine-tuning
self-supervised auxiliary losses
temporal memory / recency encoding
uncertainty / abstention
distributional prediction
hard-case mining
```

不可照搬：

```text
agent action policy
VLA action decoder
diffusion robot action generation
learned collision handling
learned restart
replacement of PIBT / LaCAM*
```

### 10.2 建议 Codex 阅读并抽象

Codex 可以阅读最近两三年以下方向，并将想法落到 LAUR：

```text
1. LaGAT / graph attention guided search:
   学 hybrid learned guidance + classical search + failure-triggered fallback。

2. Real-Time LaCAM:
   学 iterative/receding-horizon planning interface，但不要改 LaCAM semantics。

3. HiMAP / SACHA / recent learning-based MAPF:
   学 heuristic-informed attention、agent-centered credit assignment 的抽象；不要学 agent action。

4. Octo / generalist robot policies:
   学 pretrain + domain fine-tune、模块化 transformer、数据/architecture ablation 的实验规范。

5. Diffusion Policy / Causal Diffusion:
   学 sequence/distributional modeling、temporal consistency、receding-horizon 观念；
   可抽象成 UpdateLTM parameter trajectory uncertainty，不要直接做 diffusion action policy。

6. Recent VLA / dual-system robot controllers:
   学 slow global context + fast local controller 的架构；
   可抽象成 global traffic context encoder + fast per-rule update decoder。
```

### 10.3 Codex 需要输出 memo

新增：

```text
outputs/reports/phase4f_repair5_recent_ai_robotics_architecture_memo.md
```

要求：

```text
- 至少读 6 篇 2023-2026 AI / robotics / MAPF / planning-learning 相关论文；
- 每篇只提取可迁移的 architecture / training / gate / ablation idea；
- 明确说明哪些不能用于 czr004，因为会偏离 LAUR；
- 给出 2-4 个可实现的 LAUR-compatible architecture variants；
- 不允许绕开现有 gate。
```

---

## 11. 推荐实验矩阵：结构化，而不是随机扫

每个 variant 先 seed61。只有 seed61 过 strict gate，才跑 103/107 和 final multi-seed gate。

### 11.1 第一批：failure decomposition 后必跑

```text
R5B-0:
  diagnose_laur_repair5_failure_modes.py
  no training

R5B-1:
  per-rule safety calibration on best previous flat model
  no retraining

R5B-2:
  hierarchical normal-token rank-first curriculum

R5B-3:
  hierarchical high-token rank-first curriculum

R5B-4:
  hierarchical high-token safety-first curriculum

R5B-5:
  high-margin specialist diagnostic
```

### 11.2 第二批：如果 R5B-2/3/4 有发展信号

```text
R5B-6:
  hierarchical high-token + stratified sampler

R5B-7:
  hierarchical high-token + per-rule safety + rank-first

R5B-8:
  hierarchical high-token + hard-case replay

R5B-9:
  hierarchical high-token + map-family balanced fine-tune

R5B-10:
  bounded parameter/residual head diagnostic
  only if oracle suggests static rule action space is limiting
```

### 11.3 每个 variant 必须写统一 summary

```text
outputs/reports/phase4f_repair5b_<variant>_summary.json
outputs/reports/phase4f_repair5b_<variant>_report.md
```

包含：

```text
phase4f gate
attention-native gate
safety gate
anti-escape gate
layered gate
oracle regret
per-rule safety calibration
map/rule/family breakdown
failure reason
promotion decision
```

---

## 12. Phase5.5 进入条件

不要提前做 runtime。只有满足以下条件才进入 Phase5.5-update smoke：

```text
1. seed61 strict Repair5 gate pass；
2. seeds 103/107 pass；
3. final multi-seed gate pass；
4. anti-escape pass by high-margin opportunity subset；
5. per-rule or global safety calibration report clean；
6. selected_vs_additive_delta positive；
7. no missing gate fields；
8. model exported with deterministic inference path；
9. additive/defer fallback reasons logged。
```

Phase5.5 smoke 对比：

```text
LaCAM*
LaCAM*+LTM
Repair3 MLP safe runtime
Repair5B LAUR
Repair5B force-additive / defer-only
Repair5B without anti-escape
Repair5B without safety
Repair5B static selected rule ablations
```

指标：

```text
success
sum_of_loss_ratio
expanded_nodes
high_level_expansions
low_level_pibt_calls
time_to_first_solution_ms
runtime_ms
LAUR overhead
fallback/defer rate
non-additive update rate
harmful veto rate
per-map and per-agent bucket results
```

必须写：

```text
outputs/reports/phase5p5_laur_repair5b_runtime_smoke_report.md
```

Phase5.5 smoke 也不等于 Phase6。Phase6 需要更大规模闭环 learned-benefit evidence。

在 Phase5.5 之前允许存在一个更弱的 **diagnostic closed-loop preflight plan**，但它只用于测量 offline signal 是否能转移到 closed-loop，不得写成 Phase5.5 unlock。preflight 必须满足：

```text
promotion-candidate signal reached or near reached
hard safety mask enabled
force-additive / defer-only parity path checked first
no C++ solver semantic changes
all reports label it as diagnostic only
no Phase6 learned-benefit claim
```

---

## 13. 什么时候考虑几十/上百小时训练

当前不建议直接大训。满足以下信号后才考虑：

### 13.1 可以考虑 20-40 小时训练

```text
R5B hierarchical seed61 达到 promotion-candidate gate；
或 strict gate 只差一项且 oracle gap 明确；
且 failure decomposition 显示模型而不是 action space 是主瓶颈；
且 validation high-margin capture / recall / top3 有稳定共同提升。
```

### 13.2 可以考虑 100 小时级训练

需要同时满足：

```text
1. 数据量至少 20k-50k checkpoint labels；
2. high-margin opportunity train >= 2k，validation >= 300-500；
3. hierarchical model small->medium scaling 有正向收益；
4. multi-seed 不崩；
5. Phase5.5 smoke 不输 LTM；
6. ablation 证明 attention / raw trace / anti-escape / safety 都有贡献；
7. Codex 生成 architecture memo 并解释为何该模型值得 scale。
```

---

## 14. 最终给 Codex 的压缩目标

```text
Continue czr004 LAUR Repair5 from commit 7bf0b0ad077e2d26ca78dbb0133d167b24d5b62f.

Do not change the main direction:
  learned UpdateLTM / LAUR only.
  No agent action policy.
  No PIBT or LaCAM* semantic changes.
  No learned restart.
  No gate lowering.

Current evidence:
  expand5000 data/audit is valid and opportunity-rich,
  but 27 completed Repair5 runs have zero development/promotion/strict passes.
  Some variants pass anti-escape or top3 or precision individually,
  but none pass ranking + safety + anti-escape together.

Next goal:
  Build Repair5B hierarchical attention-native LAUR.

Required stages:
  1. finish current queues and rescore layered gate;
  2. build failure decomposition + oracle upper bound report;
  3. add per-rule/per-family safety calibration;
  4. implement LAU-HierEdgeTraceTransformer-v5;
  5. train rank-first / safety-first / high-margin-specialist curricula;
  6. add stratified sampler and hard-case replay;
  7. optionally explore bounded UpdateLTM parameter/residual head if oracle shows static rule space is limiting;
  8. read recent 2023-2026 AI/robotics/MAPF literature for architecture inspiration only, then write a LAUR-compatible design memo;
  9. only if strict seed61 passes, train seeds 103/107 and final gate;
  10. only if multi-seed strict Repair5 passes, prepare Phase5.5 runtime smoke.
```

---

## 15. 结论

当前结果不支持 Phase5.5，也不支持 Phase6。
但它也没有证明 LAUR idea 不 work。

更准确的判断是：

```text
Repair5 已经证明：
  attention-native labels / raw-trace data / anti-escape eval can be built;
  non-additive opportunities exist;
  individual sub-goals can be improved.

Repair5 还没证明：
  one flat attention model can jointly satisfy ranking + safety + anti-escape;
  learned UpdateLTM can beat additive LTM closed-loop.
```

下一轮要从 “flat multi-task attention sweep” 进入：

```text
hierarchical learned UpdateLTM controller
+ oracle gap diagnosis
+ per-rule safety
+ curriculum
+ hard-case mining
+ literature-inspired architecture exploration
```

这样仍然遵守 czr004 总纲，也给 Codex 足够探索空间。最终目标不变：**LAUR 过 Phase4F / Phase5.5，进入 Phase6，并在闭环性能上超过 LTM 简单加法更新。**
