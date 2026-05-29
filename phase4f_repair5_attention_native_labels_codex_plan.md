# Phase4F Repair5：Attention-Native LAUR Label 重构计划（反逃避版）

> 目标：抛弃 Repair3 stable-target 作为高级神经网络的训练 label 基础，重新设计一套更适合 rule-conditioned / edge-trace attention 的 LAUR label。  
> 约束：不放松现有 Phase4F gate；不偏离 `czr004` 的 LTM / LAUR 主线；不预测 agent action；不替换 PIBT / LaCAM*；不引入 learned restart；必须新增“防止无脑退回 additive/LTM 混过 gate”的 anti-escape gate。

---

## 0. 结论先行

当前 Repair3 可以作为 **conservative runtime baseline** 和 **Phase4F historical baseline** 保留，但不要继续把 Repair3 stable-target 当作高级 attention 模型的主训练目标。

原因：

1. Repair3 的核心成功来自 stable target / tie handling，而不是强模型。
2. Repair3 的 tie policy 明显偏向 `additive_ltm` fallback。
3. Repair3 过了 offline Phase4F，但 Phase5C closed-loop smoke 没证明 learned runtime 优于普通 LTM。
4. Repair4 StableAttention 继承 Repair3 label 后，ranking/delta 有改善，但 safety tradeoff 没过，而且仍有明显 fallback/additive 倾向。
5. 如果继续在 Repair3 label 上堆 Transformer，很可能只是训练出一个更复杂的“保守回 additive”分类器，而不是更强的 learned update policy。

Repair5 的方向应该是：

```text
从 probe outcomes / rule utility / pairwise dominance / high-margin opportunity 重新生成 attention-native labels，
让高级模型学习“什么时候安全地使用非 additive update”，
而不是学习“什么时候回 additive 最稳”。
```

---

## 1. 项目边界：必须保持 czr004 主线

### 1.1 In scope

Repair5 仍然属于 LAUR / LAU-LTM 主线：

```text
LaCAM* + LTM
  -> teacher/probe/checkpoint/trace
  -> LAUR learned UpdateLTM policy
  -> C++ runtime parity/smoke
```

允许做：

- 重新设计 Phase4F label；
- 重新生成 dataset；
- 训练更强的 rule-conditioned / edge-trace attention model；
- 使用 existing Repair1 checkpoints / probes / raw trace；
- 使用 Repair3 / Phase5C MLP runtime 作为 baseline；
- 增加 anti-escape evaluation；
- 只有 gate 全部通过后才考虑 Phase5.5 update runtime。

### 1.2 Out of scope

严格禁止：

- 不预测 agent action；
- 不替换 PIBT；
- 不改 LaCAM* conflict semantics；
- 不改 candidate action domain；
- 不改 incumbent pruning / rewrite 逻辑；
- 不引入 learned restart；
- 不用 validation/test 调 threshold；
- 不降低任何现有 Phase4F gate；
- 不把 `defer/additive` 伪装成 non-additive learning 成功；
- 不把 smoke / parity 说成 Phase6-scale performance claim。

---

## 2. 现有证据与问题定位

### 2.1 Repair1

Repair1 修好了 safety，但没修好 ranking：

```text
validation top1 = 0.3072 < 0.35
validation top3 = 0.6427 < 0.70
harmful recall = 0.9538 pass
harmful precision = 0.4015 pass
mean delta = 0.01099 pass
```

说明：原始 hard label / feature / map split 下，模型不是完全没信号；主要问题是 exact rule ranking 泛化不够。

### 2.2 Repair2

Repair2 第一次上高级 attention / token dataset，但仍失败：

```text
best top1 = 0.3159 < 0.35
best top3 = 0.5033 < 0.70
safety pass
mean delta pass
```

threshold sweep 最高 top3 到 0.6580，但 harmful recall 掉到 0.6127，不能过 gate。

说明：只换模型不够；label 和目标定义不适合 attention。

### 2.3 Repair3

Repair3 成功点是 stable target：

```text
tie_epsilon = 0.010
neutral_delta_threshold = 0.005
如果 additive_ltm 在 tie band 内，优先 additive fallback
```

Repair3 seed61 offline pass：

```text
top1 = 0.389978 >= 0.35
top3 = 0.769063 >= 0.70
harmful recall = 0.942197 >= 0.80
harmful precision = 0.390887 >= 0.30
mean selected delta = 0.008131 > 0
validation non-neutral = 293 >= 50
```

但是 Repair3 的问题：

```text
它把 label ambiguity 大量折回 additive / neutral；
它可能是合法的 conservative pass，但不是强 learning 证明；
Phase5C learned runtime 没有稳定优于 LTM。
```

### 2.4 Repair4 StableAttention

Repair4 继承 Repair3 stable target 后：

```text
SetRuleTransformer:
  ranking/delta/recall 有信号，但 harmful precision 不过

EdgeTraceTransformer gate-select:
  top1 = 0.400871
  top3 = 0.749455
  mean delta = 0.005734
  harmful precision = 0.287154 < 0.30
  harmful recall = 0.782609 < 0.80
```

说明：Repair3 label 能让 advanced model 学到一点 ranking，但 safety / opportunity / anti-escape 没解决。

---

## 3. Repair5 总目标

Repair5 不再把 Repair3 stable-target label 作为 primary label。

Repair5 目标是生成一套新的 `attention_native_label_v1`：

```text
每个 checkpoint/sample 不只给一个 hard best rule，
而是给：
  1. per-rule risk-adjusted utility
  2. pairwise rule dominance matrix
  3. per-rule harmful labels
  4. non-additive opportunity labels
  5. defer/additive reason labels
  6. high-margin safe-opportunity slices
  7. anti-escape supervision masks
```

这套 label 要让模型学：

```text
什么时候非 additive update 明显、安全、值得使用；
什么时候确实应该 defer/additive；
哪些样本是 ambiguous，不应该被 hard CE 强行拟合；
哪些样本如果回 additive 就是逃避。
```

---

## 4. 新 label 设计：Attention-Native Label v1

### 4.1 输入

使用已有 Repair1 / Repair3 证据，不要求重新跑 full batch：

```text
artifacts/teacher/laur/full_repair1/checkpoints/phase4_laur_checkpoints_full_repair1.jsonl
artifacts/teacher/laur/full_repair1/probes/phase4_laur_probe_full_repair1.jsonl
artifacts/teacher/laur/full_repair1/update_labels/phase4_laur_update_dataset_full_repair1.jsonl
artifacts/teacher/laur/full_repair1/traces/phase4_laur_trace_full_repair1.jsonl.zst  # optional but preferred
```

规则集合先沿用 executable LAUR update rules：

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

不要新增 agent-action policy。

### 4.2 基础变量

对每个 sample，probe 结果给出每个 rule 的结果：

```text
delta_i = delta_ratio_vs_additive(rule_i)
harmful_i = harmful(rule_i)
success_i = success(rule_i) if available
ttfs_regression_i = ttfs_regression_ratio(rule_i) if available
```

默认：

```text
additive_index = index(additive_ltm)
delta_additive = 0.0
```

如果某些字段不存在：

```text
ttfs_regression_i = 1.0
success_i = true
```

不得因为字段缺失伪造更好的 label；必须在 label audit 中报告 coverage。

### 4.3 Risk-adjusted utility

定义每个 rule 的风险修正 utility：

```text
utility_i =
    delta_i
  - harm_penalty * I[harmful_i]
  - failure_penalty * I[success_i == false]
  - ttfs_penalty * max(0, ttfs_regression_i - 1.0)
```

推荐初始参数：

```yaml
harm_penalty: 0.050
failure_penalty: 0.100
ttfs_penalty: 0.010
utility_clip_min: -0.100
utility_clip_max: 0.100
```

解释：

- `delta_i` 是性能信号；
- harmful rule 即使 delta 高，也不应该成为 target；
- failure / TTFS regression 如果可用，应进入 utility；
- penalty 必须大于 typical small delta margin，避免“高收益但有害”的 rule 污染 soft label。

### 4.4 Safe rule mask

```text
safe_i = success_i && !harmful_i
```

如果 `harmful_i` 缺失，保守处理：

```text
safe_i = false
```

并在 audit 里记录 missing harmful label count。

### 4.5 Non-additive opportunity label

定义：

```text
best_safe_nonadditive =
    argmax_i utility_i
    where i != additive_ltm and safe_i

best_safe_nonadditive_advantage =
    utility_best_safe_nonadditive - utility_additive
```

推荐 threshold：

```yaml
opportunity_margin: 0.010
high_margin_opportunity_margin: 0.020
min_safe_utility: 0.000
```

标签：

```text
has_nonadditive_opportunity =
    exists safe non-additive rule with
      utility_i - utility_additive >= opportunity_margin
      and utility_i > min_safe_utility

has_high_margin_nonadditive_opportunity =
    exists safe non-additive rule with
      utility_i - utility_additive >= high_margin_opportunity_margin
      and utility_i > min_safe_utility
```

这两个 label 是 anti-escape 的核心。

### 4.6 Defer label：不要把 defer 污染成 additive hard target

Repair3 把大量 ambiguity 变成 additive/neutral。Repair5 要把“真的应该回 LTM”与“模型逃避”分开。

新增非 executable meta-decision：

```text
defer_ltm
```

注意：

```text
defer_ltm 不是 executable rule；
runtime 中 defer_ltm 映射到 additive_ltm；
eval 中 defer_ltm 必须单独统计；
不能把 defer_ltm 计为 non-additive learning 成功。
```

定义：

```text
defer_reason =
  all_nonadditive_unsafe
  no_safe_nonadditive_opportunity
  ambiguous_low_margin
  additive_is_best_safe
  missing_probe_evidence
```

推荐规则：

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

重点：  
**只有“没有高质量非 additive 机会”时，defer 才是合理的。**  
如果存在 high-margin safe non-additive opportunity，回 additive/defer 就是逃避。

### 4.7 Listwise soft target

对 rule-conditioned attention，单一 hard label 太粗。生成 soft target：

```text
p_i = softmax(utility_i / temperature)
```

但要处理 harmful：

```text
if !safe_i:
    utility_i_for_softmax = min(utility_i, harmful_floor)
```

推荐：

```yaml
softmax_temperature: 0.010
harmful_floor: -0.050
softmax_safe_only: false
```

也可以试两个版本：

```text
Variant A: softmax over all rules with harmful_floor
Variant B: softmax over safe rules only, harmful rules target probability = 0
```

必须在 audit 里报告 label entropy，避免 label 过于平或过于 one-hot。

### 4.8 Pairwise dominance matrix

生成 rule pair preference：

```text
dominates[i][j] = true
if:
  safe_i
  and utility_i - utility_j >= pairwise_margin
```

推荐：

```yaml
pairwise_margin: 0.005
```

如果两者差距小：

```text
dominates[i][j] = null / ignored
```

这样 attention model 可以学 ranking，而不是被 noisy hard label 误导。

### 4.9 Anti-escape mask

定义：

```text
anti_escape_sample =
    has_high_margin_nonadditive_opportunity == true
```

在这些样本上：

```text
forbidden_escape =
    selected additive_ltm
    or selected defer_ltm
    or selected unsafe rule
    or selected rule delta < additive_delta + opportunity_margin
```

训练时生成：

```text
anti_escape_target = 1
anti_escape_best_rule = best_safe_nonadditive
anti_escape_candidate_mask = safe_nonadditive_rules_with_advantage >= opportunity_margin
```

eval 时必须统计：

```text
anti_escape_count
anti_escape_selected_nonadditive_count
anti_escape_capture_rate
avoidable_additive_fallback_rate
avoidable_defer_rate
anti_escape_mean_selected_vs_additive_delta
```

---

## 5. 新 dataset schema

新增：

```text
schema_version: phase4_laur_attention_native_label_dataset_v1
```

每行建议字段：

```json
{
  "schema_version": "phase4_laur_attention_native_label_dataset_v1",
  "split": "train|validation",
  "run_id": "...",
  "checkpoint_id": "...",
  "map_name": "...",
  "agents": 100,
  "seed": 1,
  "iteration": 3,

  "global_features": [],
  "edge_tokens": [],
  "edge_mask": [],
  "trace_tokens": [],
  "trace_mask": [],
  "rule_tokens": [],

  "rule_ids": [
    "additive_ltm",
    "commit_heavy",
    "block_heavy",
    "block_light",
    "wait_light",
    "wait_heavy",
    "decay_095",
    "decay_090"
  ],

  "probe_delta_vector": [],
  "probe_harmful_vector": [],
  "probe_success_vector": [],
  "risk_adjusted_utility_vector": [],
  "soft_utility_target": [],

  "pairwise_dominance_matrix": [],
  "pairwise_observed_mask": [],

  "safe_rule_mask": [],
  "safe_nonadditive_mask": [],

  "has_nonadditive_opportunity": true,
  "has_high_margin_nonadditive_opportunity": false,
  "best_safe_nonadditive_rule": "commit_heavy",
  "best_safe_nonadditive_index": 1,
  "best_safe_nonadditive_advantage": 0.013,

  "decision_target": "use_nonadditive|defer_ltm",
  "target_rule": "commit_heavy",
  "defer_reason": null,

  "anti_escape_sample": true,
  "anti_escape_candidate_mask": [],

  "coverage": {
    "has_probe_delta": true,
    "has_probe_harmful": true,
    "has_ttfs": false,
    "has_raw_trace": true
  }
}
```

---

## 6. Label variants to try

不要一次只做一个 label。Repair5 应该系统比较多个 label variant。

### Variant R5-A：Risk-Adjusted Utility Listwise

核心：

```text
soft target = softmax(risk_adjusted_utility / T)
hard target only for high-confidence safe winner
```

Loss：

```text
KL(q_rule_scores, soft_utility_target)
+ SmoothL1(q_delta, utility_or_delta)
+ BCE(harmful_head, harmful_vector)
+ opportunity BCE
+ anti_escape hinge loss
```

适合：

- SetRuleTransformer；
- EdgeTraceTransformer；
- listwise ranking。

优点：

- 不再硬选一个 noisy best rule；
- harmful 不会污染 positive target；
- 比 Repair3 更少 additive tie preference。

风险：

- 如果 temperature 太低，仍会 one-hot；
- 如果 penalty 太大，可能全变 defer；
- 必须用 anti-escape gate 防止保守退化。

### Variant R5-B：Pairwise Dominance / RankNet Label

核心：

```text
只相信 utility 差距超过 pairwise_margin 的 pair；
小 margin pair 不训练 hard order。
```

Loss：

```text
for each observed pair (i, j):
    log_sigmoid(score_i - score_j)
```

额外：

```text
safe non-additive opportunity 样本上，
要求 max_nonadditive_score > additive_score + model_margin
```

适合：

- attention model；
- noisy label；
- rule ranking；
- margin ambiguity 高的 dataset。

优点：

- 不强行拟合 ambiguous label；
- 直接学“哪个 rule 比哪个 rule 好”；
- 不天然偏 additive。

风险：

- top1 label 可能不如 listwise 好；
- 需要单独 decision head。

### Variant R5-C：Opportunity-First Two-Stage Label

核心：

```text
Stage 1: 是否存在 safe non-additive opportunity
Stage 2: 如果存在，在 safe non-additive rules 里 ranking
Stage 3: 如果不存在，defer -> additive runtime
```

Heads：

```text
opportunity_logit
rule_score_per_rule
harmful_logit_per_rule
defer_logit
```

Loss：

```text
BCE(opportunity_logit, has_nonadditive_opportunity)
+ pairwise/listwise rule ranking on opportunity samples
+ BCE(harmful_head)
+ defer_reason CE on no-opportunity samples
+ anti_escape loss on high-margin opportunity samples
```

优点：

- 明确区分“真的该回 LTM”和“逃避”；
- 最适合新增 anti-escape gate；
- runtime behavior 可解释。

风险：

- 如果 opportunity labels 太少，需要 class balancing；
- 需要报告 opportunity count 是否足够。

### Variant R5-D：Trace-Credit Auxiliary Label

核心：

attention model 不能只看 global summary；应该利用 edge/trace tokens。

从 raw trace / checkpoint top-k 生成辅助 label：

```text
edge_credit_token =
    该 edge 是否贡献了 non-additive opportunity
```

近似规则：

```text
edge has high blocked_count / wait_count / reverse_conflict / boundary / corridor pattern
and corresponding winning rule family is block / wait / decay / commit
```

输出：

```text
edge_attention_target_mask
trace_event_credit_target
```

Loss：

```text
token_attention_alignment_loss
```

这不是 primary gate。它是辅助项，不能因为它失败就阻塞 R5-A/B/C。

优点：

- 更适合 EdgeTraceTransformer；
- 逼模型看 trace，而不是只学 additive prior；
- 有助于解释。

风险：

- credit assignment 可能粗；
- 不要用它替代 utility / safety label。

### Variant R5-E：Defer-as-policy, not Additive-as-label

核心：

把 `defer_ltm` 显式作为 decision label，而不是把所有不确定样本写成 `additive_ltm`。

训练：

```text
decision_target = use_nonadditive | defer_ltm
runtime_selected_rule = additive_ltm if defer_ltm else selected_rule
```

评估：

```text
defer_ltm 不计为 additive_ltm top1；
在 anti_escape_sample 上 defer 是 failure；
在 no-opportunity/all-unsafe 上 defer 是 success。
```

这是强烈建议实现的 variant，可以和 R5-A/B/C 同时使用。

---

## 7. 推荐模型：LAU-EdgeTraceTransformer-v4

不要只复用 Repair4 的 heads。Repair5 model 应该匹配新 labels。

### 7.1 Inputs

沿用 Repair4 tokenization，但可以增加字段：

```text
global_features
edge_tokens
trace_tokens
rule_tokens
rule_family embeddings
map/topology local features
```

可选新增：

```text
edge_token rule-family interaction features
trace event order bucket
blocked/committed/wait normalized per-agent features
reverse-edge pressure features
```

### 7.2 Outputs

```python
{
  "rule_score": [B, R],                  # utility / ranking
  "delta_pred": [B, R],                  # delta or utility regression
  "harmful_logit": [B, R],               # per-rule harmful
  "opportunity_logit": [B],              # safe non-additive opportunity exists
  "defer_logit": [B],                    # explicit defer decision
  "family_logits": [B, R, F],            # optional
  "edge_credit_logit": [B, E],           # optional auxiliary
}
```

### 7.3 Loss

推荐总 loss：

```text
total =
  lambda_listwise      * listwise_utility_kl
+ lambda_pairwise      * pairwise_dominance_loss
+ lambda_delta         * smooth_l1_delta_or_utility
+ lambda_harmful       * harmful_bce_or_focal
+ lambda_opportunity   * opportunity_bce
+ lambda_defer         * defer_bce_or_reason_ce
+ lambda_anti_escape   * anti_escape_margin_loss
+ lambda_family        * family_ce
+ lambda_edge_credit   * edge_credit_aux_loss
```

推荐初始权重：

```yaml
lambda_listwise: 1.0
lambda_pairwise: 1.0
lambda_delta: 0.5
lambda_harmful: 2.0
lambda_opportunity: 1.0
lambda_defer: 0.5
lambda_anti_escape: 2.0
lambda_family: 0.1
lambda_edge_credit: 0.1
anti_escape_score_margin: 0.005
```

### 7.4 Anti-escape margin loss

对 high-margin safe-opportunity samples：

```text
best_safe_nonadditive_score =
    max score_i where anti_escape_candidate_mask_i == true

loss =
    relu(additive_score + margin - best_safe_nonadditive_score)
  + relu(defer_score + margin - best_safe_nonadditive_score)
```

如果没有 `defer_score`，只用 additive_score。

---

## 8. Evaluation：原 gates 不放松

### 8.1 Original Phase4F gate 保留

必须继续通过：

```text
validation_top1 >= 0.35
validation_top3 >= 0.70
harmful_recall >= 0.80
harmful_precision >= 0.30
mean_selected_delta > 0.0
validation_non_neutral >= 50
schema_validation_passes
split_leakage == 0
```

说明：

- top1/top3 对新 `attention_native_target_rule` 计算；
- 同时必须报告 against Repair3 stable target 的 compatibility metrics，但不要把 Repair3 target 作为 primary pass 条件；
- 不得因为新 label 更难而降低 gate；
- 不得用 `defer_ltm` 冒充 `additive_ltm` 来抬高 top1。

### 8.2 Safety gate 保留

```text
harmful_recall >= 0.80
harmful_precision >= 0.30
```

要求：

- safety threshold 必须在 train/calibration split 选；
- validation 只能评估；
- 可以使用 per-rule threshold，但必须记录；
- 不能为了提高 anti-escape 而牺牲 harmful recall/precision。

### 8.3 Runtime promotion 仍然禁止，直到 offline gate 全过

即使 Repair5 offline 过了，也不能直接宣称成功。Phase5.5 runtime 需要额外：

```text
Python/C++ parity pass
force-additive parity pass
schema replay pass
closed-loop smoke not worse than LTM
```

---

## 9. 新增 Anti-Escape Gate

新增 gate 文件：

```text
outputs/reports/phase4f_repair5_anti_escape_gate_summary.json
```

### 9.1 Definitions

在 validation split 上定义：

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

### 9.2 Required anti-escape metrics

必须报告：

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

### 9.3 Anti-escape gate thresholds

初始建议：

```yaml
anti_escape:
  min_validation_high_margin_opportunity_count: 50

  # 在 high-margin safe-opportunity 样本上，不能大多数都回 additive/defer
  high_margin_nonadditive_capture_rate_min: 0.40

  # high-margin opportunity 上，无脑回 additive/defer 的比例必须受限
  avoidable_additive_or_defer_rate_max: 0.60

  # captured/noncaptured 全部算，平均选择必须比 additive 有收益
  anti_escape_mean_selected_vs_additive_delta_min: 0.005

  # 在 opportunity 样本上，选择 non-additive 的比例不能低于 35%
  opportunity_nonadditive_selection_rate_min: 0.35

  # 如果全 validation 的 additive/defer rate 超过 70%，需要 fail 或人工审查
  global_additive_or_defer_rate_max: 0.70
```

如果 validation high-margin opportunity 数量 < 50：

```text
anti_escape_gate = inconclusive
Phase5.5 runtime = forbidden
必须扩大/重采样 validation 或重新生成 probe。
```

### 9.4 Anti-escape 不允许被 mean delta 掩盖

即使：

```text
mean_selected_delta > 0
```

只要 high-margin opportunity 大量回 additive/defer，就 fail。

原因：

```text
mean delta 可能来自少量容易样本；
真正需要 learning 的高机会样本被逃避时，模型不是强 learned update。
```

---

## 10. Always-additive / LTM baseline comparison

新增 baseline：

```text
always_additive_ltm
```

每个 model 必须报告：

```text
mean_delta_vs_always_additive
opportunity_capture_vs_always_additive
closed_loop_ratio_vs_ltm_if_runtime
expanded_nodes_vs_ltm_if_runtime
ttfs_vs_ltm_if_runtime
```

最低要求：

```text
offline mean_selected_delta > 0 仍保留；
anti_escape_mean_selected_vs_additive_delta >= 0.005；
Phase5.5 smoke 中 success 不低于 LTM；
Phase5.5 smoke 中 ratio 不得高于 LTM 超过 0.5%；
expanded nodes 不得明显高于 LTM，除非 ratio/TTFS 明显改善并记录原因。
```

---

## 11. Training / evaluation protocol

### 11.1 Seeds

至少跑：

```text
61
103
107
```

### 11.2 Model families

优先顺序：

```text
1. LAU-EdgeTraceTransformer-v4
2. LAU-SetRuleTransformer-v2
3. LAU-TopoBiasAttention-v1 optional
```

### 11.3 Label variants

至少跑：

```text
R5-A: risk_adjusted_listwise
R5-B: pairwise_dominance
R5-C: opportunity_first
R5-A+C combined
R5-B+C combined
```

R5-D trace-credit 可以先作为 optional auxiliary，不要阻塞主线。

### 11.4 Selection policy

Runtime/offline selection 必须区分：

```text
model_decision:
  use_nonadditive
  defer_ltm

runtime_selected_rule:
  additive_ltm if defer_ltm else selected_rule
```

评估时：

```text
defer_ltm 不算 non-additive capture；
defer_ltm 在 no-opportunity/all-unsafe 样本上可接受；
defer_ltm 在 high-margin opportunity 样本上算 escape failure。
```

---

## 12. Implementation tasks for Codex

### Task 1：新增 label builder

新增：

```text
src/czr004_teacher/attention_native_labels_laur.py
```

功能：

```text
- read checkpoint_jsonl
- read probe_jsonl
- optionally read raw trace zst
- join rows by run/checkpoint
- compute risk_adjusted_utility_vector
- compute safe masks
- compute opportunity labels
- compute pairwise dominance matrix
- compute soft utility target
- compute defer reason
- compute anti_escape masks
- write dataset JSONL
- write audit report
```

### Task 2：新增 schema validation

新增：

```text
src/czr004_teacher/attention_native_schema_laur.py
tests/test_phase4f_attention_native_labels.py
```

验证：

```text
- required fields
- vector lengths == len(EXECUTABLE_RULE_IDS)
- pairwise matrix shape R x R
- no NaN/inf
- soft target sums to 1
- split no leakage
- anti_escape_sample implies high_margin opportunity
- defer_ltm is not in executable rule ids
```

### Task 3：新增 config

新增：

```text
configs/phase4/laur_ltm_full_repair5_attention_native_labels.yaml
```

核心字段：

```yaml
schema_version: phase4_laur_attention_native_config_v1
mode: phase4-full-repair5-attention-native-labels

inputs:
  checkpoint_jsonl: artifacts/teacher/laur/full_repair1/checkpoints/phase4_laur_checkpoints_full_repair1.jsonl
  probe_jsonl: artifacts/teacher/laur/full_repair1/probes/phase4_laur_probe_full_repair1.jsonl
  raw_trace_zst: artifacts/teacher/laur/full_repair1/traces/phase4_laur_trace_full_repair1.jsonl.zst

outputs:
  dataset_jsonl: artifacts/teacher/laur/full_repair5_attention_native/update_labels/phase4_laur_attention_native_dataset.jsonl
  label_audit_json: outputs/reports/phase4f_repair5_attention_native_label_audit.json
  label_audit_md: outputs/reports/phase4f_repair5_attention_native_label_audit.md

label:
  harm_penalty: 0.050
  failure_penalty: 0.100
  ttfs_penalty: 0.010
  opportunity_margin: 0.010
  high_margin_opportunity_margin: 0.020
  pairwise_margin: 0.005
  softmax_temperature: 0.010
  harmful_floor: -0.050
```

### Task 4：新增 model / heads

新增或扩展：

```text
src/models/laur_attention_native.py
src/train/losses_laur_attention_native.py
src/train/train_laur_attention_native.py
src/eval/eval_laur_attention_native.py
```

不要删 Repair3 / Repair4 文件；Repair5 是新实验线。

### Task 5：新增 anti-escape eval

新增：

```text
src/eval/eval_laur_anti_escape.py
```

输出：

```text
outputs/reports/phase4f_repair5_anti_escape_gate_summary.json
outputs/reports/phase4f_repair5_anti_escape_report.md
outputs/tables/phase4f_repair5_opportunity_slices.csv
outputs/tables/phase4f_repair5_decision_distribution.csv
```

### Task 6：新增 final gate aggregator

新增：

```text
src/eval/eval_laur_repair5_final_gate.py
```

必须同时检查：

```text
original_phase4f_gate
attention_native_phase4f_gate
safety_gate
anti_escape_gate
multi_seed_gate
runtime_allowed
```

规则：

```text
runtime_allowed = (
    original_phase4f_gate.pass
    and attention_native_phase4f_gate.pass
    and safety_gate.pass
    and anti_escape_gate.pass
    and multi_seed_gate.pass
)
```

不要使用 Repair4 那种 “advanced promotion any condition” 作为 runtime pass 条件。  
高级模型 runtime 必须是 all required gates pass。

---

## 13. Required reports

必须生成：

```text
outputs/reports/phase4f_repair5_attention_native_label_audit.md
outputs/reports/phase4f_repair5_attention_native_label_audit.json
outputs/reports/phase4f_repair5_attention_native_train_seed61.md
outputs/reports/phase4f_repair5_attention_native_eval_seed61.md
outputs/reports/phase4f_repair5_attention_native_eval_seed103.md
outputs/reports/phase4f_repair5_attention_native_eval_seed107.md
outputs/reports/phase4f_repair5_anti_escape_report.md
outputs/reports/phase4f_repair5_anti_escape_gate_summary.json
outputs/reports/phase4f_repair5_final_gate_summary.json
```

Report 必须包含：

```text
- label distribution
- opportunity count
- high-margin opportunity count
- defer reason distribution
- selected rule distribution
- additive/defer rate
- non-additive capture rate
- avoidable fallback rate
- harmful precision/recall
- top1/top3
- mean selected delta
- comparison with Repair3 MLP
- comparison with always_additive_ltm
- runtime allowed yes/no
```

---

## 14. Acceptance criteria

Repair5 成功标准：

```text
1. Dataset/schema/split audit pass.
2. Existing Phase4F gates pass:
   - top1 >= 0.35
   - top3 >= 0.70
   - harmful recall >= 0.80
   - harmful precision >= 0.30
   - mean selected delta > 0
   - validation non-neutral >= 50
3. Anti-escape gate pass:
   - high-margin opportunity count >= 50
   - high-margin non-additive capture rate >= 0.40
   - avoidable additive/defer rate <= 0.60
   - anti-escape mean selected-vs-additive delta >= 0.005
   - opportunity non-additive selection rate >= 0.35
   - global additive/defer rate <= 0.70
4. Multi-seed evidence: seeds 61/103/107 pass or explicitly report which seed failed.
5. No Phase5.5 runtime integration unless all gates pass.
```

如果 Repair5 fails：

```text
Do not lower gates.
Do not claim success.
Record as negative result.
Diagnose whether failure is:
  label opportunity count too low
  safety calibration failure
  attention overfitting
  trace-credit failure
  map-family OOD
  rule set too weak
```

---

## 15. Direct Codex instruction

Use this exact instruction block when starting Codex:

```text
Goal: Implement Phase4F Repair5 attention-native LAUR labels with anti-escape gates.

Do not continue Repair4 StableAttention as-is.
Do not use Repair3 stable-target labels as the primary training target.
Keep Repair3 MLP only as a baseline and runtime fallback reference.

Create branch:
  phase4f-repair5-attention-native-labels

Main objective:
  Build a new attention-native label dataset for LAUR update-rule learning:
    - risk-adjusted per-rule utility
    - pairwise rule dominance
    - explicit non-additive opportunity labels
    - explicit defer_ltm meta-decision
    - anti-escape masks for high-margin safe non-additive opportunities

Hard constraints:
  - Stay on LTM / LAUR update-rule learning.
  - Do not predict agent actions.
  - Do not modify PIBT or LaCAM* semantics.
  - Do not introduce learned restart.
  - Do not lower Phase4F gates.
  - Add anti-escape gates so models cannot pass by blindly reverting to additive_ltm / defer_ltm.
  - Do not integrate Phase5.5 runtime unless all offline gates and anti-escape gates pass.

Use existing artifacts:
  artifacts/teacher/laur/full_repair1/checkpoints/phase4_laur_checkpoints_full_repair1.jsonl
  artifacts/teacher/laur/full_repair1/probes/phase4_laur_probe_full_repair1.jsonl
  artifacts/teacher/laur/full_repair1/update_labels/phase4_laur_update_dataset_full_repair1.jsonl
  artifacts/teacher/laur/full_repair1/traces/phase4_laur_trace_full_repair1.jsonl.zst if available

Implement:
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

Try label variants:
  R5-A risk_adjusted_listwise
  R5-B pairwise_dominance
  R5-C opportunity_first
  R5-A+C combined
  R5-B+C combined

Train/evaluate seeds:
  61, 103, 107

Original Phase4F gates remain:
  top1 >= 0.35
  top3 >= 0.70
  harmful recall >= 0.80
  harmful precision >= 0.30
  mean selected delta > 0
  validation non-neutral >= 50

New anti-escape gates:
  validation high-margin opportunity count >= 50
  high-margin non-additive capture rate >= 0.40
  avoidable additive/defer rate <= 0.60
  anti-escape mean selected-vs-additive delta >= 0.005
  opportunity non-additive selection rate >= 0.35
  global additive/defer rate <= 0.70

Reports:
  outputs/reports/phase4f_repair5_attention_native_label_audit.md
  outputs/reports/phase4f_repair5_attention_native_label_audit.json
  outputs/reports/phase4f_repair5_anti_escape_report.md
  outputs/reports/phase4f_repair5_anti_escape_gate_summary.json
  outputs/reports/phase4f_repair5_final_gate_summary.json

Final decision:
  If original Phase4F gate passes but anti-escape fails:
    runtime_allowed = false
    conclusion = "model still escapes to LTM/additive"
  If anti-escape passes but safety fails:
    runtime_allowed = false
    conclusion = "non-additive learning unsafe"
  If all gates pass:
    runtime_allowed = true for Phase5.5 parity/smoke only, not Phase6-scale performance claim.
```

---

## 16. Important interpretation note

Repair5 不是否定 Repair3。

Repair3 仍然是：

```text
offline-pass conservative baseline
Phase5C runtime/parity baseline
fallback reference
```

但 Repair5 的研究目标不同：

```text
not:  learn to pass the gate conservatively
yes:  learn when non-additive LTM update is genuinely safe and useful
```

所以 Repair5 成功不能只看 top1/top3。必须同时看：

```text
anti_escape
opportunity capture
non-additive safe utility
closed-loop LTM comparison
```

否则高级神经网络仍可能只是更复杂的 fallback machine。

---

## 17. 2026-05-28 execution update

Status:

```text
Repair5 attention-native is still active.
No Phase5.5 runtime promotion is allowed.
No Phase6 claim is allowed.
```

Negative evidence recorded:

```text
outputs/reports/phase4f_repair5_final_gate_summary.json
outputs/reports/phase4f_repair5_rawtrace_edge_final_gate_summary.json
outputs/logs/phase4f_repair5_rawtrace_safety_sweep_20260528_080336.log
```

Observed pattern:

```text
set-rule attention-native: fails final gate
raw-trace edge attention: fails final gate
safety-weight sweep: anti-escape passes, but safety/ranking still fails
```

The next attempt is not a threshold relaxation. It adds harmful safety pairwise separation and changes checkpoint selection so an anti-escape-only late checkpoint does not beat a better balanced safety/ranking checkpoint.

Active run:

```text
tmux: repair5_pairwise_waiter_20260528
log:  outputs/logs/phase4f_repair5_pairwise_waiter_20260528_083008.log
configs:
  configs/phase4/generated_repair5_pairwise/sf_pair_focal_m035_lh4.yaml
  configs/phase4/generated_repair5_pairwise/sf_pair_m035_lh4_neg1.yaml
  configs/phase4/generated_repair5_pairwise/sf_pair_m050_lh3_neg2.yaml
```

Gate policy remains unchanged: only original Phase4F + attention-native + safety + anti-escape + multi-seed pass can unlock Phase5.5 parity/smoke.

---

## 18. 2026-05-28 target-rule CE/margin queue

Pairwise recovery completed without a seed61 promotion:

```text
sf_pair_focal_m035_lh4:
  top1 0.180887, top3 0.662116, recall 0.816934, precision 0.281768, anti false
sf_pair_m035_lh4_neg1:
  top1 0.208191, top3 0.641638, recall 0.684211, precision 0.311458, anti false
sf_pair_m050_lh3_neg2:
  top1 0.153584, top3 0.682594, recall 0.743707, precision 0.294918, anti false
```

Global-safety sweep remains active:

```text
tmux: repair5_global_safety_waiter_20260528
log:  outputs/logs/phase4f_repair5_global_safety_waiter_20260528_085606.log
```

First global seed61 result:

```text
sf_global_pair_neg2_anti2:
  top1 0.232082
  top3 0.706485
  recall 0.576659
  precision 0.313433
  anti true
  result: fail top1 + safety recall, no promotion
```

Next queued attempt:

```text
tmux: repair5_target_rule_margin_waiter_20260528
log:  outputs/logs/phase4f_repair5_target_rule_margin_waiter_20260528_0930.log
```

It adds optional target-rule CE and target-rule margin losses for attention-native `use_nonadditive` samples, with high-margin opportunity weighting. Defaults are zero, so old configs remain comparable.

```text
generated configs:
  configs/phase4/generated_repair5_target_rule_margin/sf_target_ce1_margin1_hm4.yaml
  configs/phase4/generated_repair5_target_rule_margin/sf_target_ce2_margin1_hm3.yaml
  configs/phase4/generated_repair5_target_rule_margin/sf_target_margin2_rank3_safe5.yaml

verification:
  local Repair5 tests: 15 passed
  remote Repair5 tests: 15 passed
```

No gate is lowered. Phase5.5 and Phase6 remain forbidden until the full Repair5 promotion rule passes.

---

## 19. 2026-05-28 data-volume branch

The data-size hypothesis is now tracked as an explicit Repair5 branch.

Current raw-trace attention-native data is small for the transformer route:

```text
total rows: about 2985
train rows: about 2526
validation rows: about 459
validation use_nonadditive rows: about 293
validation high-margin opportunity rows: about 185
```

This may explain part of the pattern where training metrics improve but validation top1 / harmful safety remain unstable. It is not treated as success evidence.

The global-safety sweep finished with no seed61 promotion:

```text
sf_global_pair_neg2_anti2:
  top1 0.232082, top3 0.706485, recall 0.576659, precision 0.313433, anti true
sf_global_pair_rank2_anti2:
  top1 0.187713, top3 0.689420, recall 0.745995, precision 0.290036, anti false
sf_global_rank3_anti3:
  top1 0.184300, top3 0.689420, recall 0.814645, precision 0.275116, anti false
```

Expansion configs:

```text
configs/phase4/laur_ltm_repair5_expand5000_scenario_manifest.jsonl
configs/phase4/laur_ltm_full_repair5_expand5000.yaml
configs/phase4/laur_ltm_full_repair5_attention_native_expand5000_rawtrace_edge.yaml
```

Expansion scope:

```text
instances: 1..25
runs: 1275
max probe rows: about 5100
raw trace: zstd compressed
original 2985-row evidence: preserved
```

Queued tmux:

```text
tmux: repair5_expand5000_waiter_20260528
log:  outputs/logs/phase4f_repair5_expand5000_waiter_20260528.log
script: run_repair5_expand5000_waiter_20260528.sh
```

It waits for `repair5_target_rule_margin_waiter_20260528`, then generates the larger dataset, rebuilds attention-native labels, audits the expanded label distribution, and screens seed61 for:

```text
configs/phase4/generated_repair5_expand5000/ex5000_mlp_target_global.yaml
configs/phase4/generated_repair5_expand5000/ex5000_linear_target_global.yaml
configs/phase4/generated_repair5_expand5000/ex5000_mlp_safety_light.yaml
```

Optional MLP heads were added to `LAURAttentionNativeModel` for this branch, with default linear-head behavior preserved.

Verification:

```text
local Repair5 tests: 16 passed, 1 warning
remote Repair5 tests: 16 passed, 1 warning
```

No gate is lowered. Phase5.5 and Phase6 remain forbidden.

---

## 20. 2026-05-28 target-rule partial result and audit diagnostics

Target-rule CE/margin on the original 2985-row raw-trace dataset has two formal seed61 negatives so far:

```text
sf_target_ce1_margin1_hm4:
  top1 0.191126, top3 0.709898, recall 0.745995, precision 0.255686, anti false
sf_target_ce2_margin1_hm3:
  top1 0.143345, top3 0.706485, recall 0.787185, precision 0.277868, anti false
```

These are not promoted. The third variant is still training under:

```text
tmux: repair5_target_rule_margin_waiter_20260528
log:  outputs/logs/phase4f_repair5_target_rule_margin_waiter_20260528_0930.log
```

An audit-only diagnostic was added for the queued expanded-data branch:

```text
summary field: split_diagnostics
per split:
  sample_count
  decision_distribution
  target_rule_distribution
  defer_reason_distribution
  nonadditive_opportunity_count
  high_margin_nonadditive_opportunity_count
```

This helps decide whether the 5000+ sample branch actually improves validation/high-margin/rule coverage. It does not change labels, model training, evaluation, or gates.

Verification:

```text
local Repair5 tests: 16 passed, 1 warning
remote Repair5 tests: 16 passed, 1 warning
```

No gate is lowered. Phase5.5 and Phase6 remain forbidden.

---

## 21. 2026-05-28 target-rule completion and high-token branch

Target-rule CE/margin completed on the original 2985-row raw-trace dataset with no seed61 promotion:

```text
sf_target_ce1_margin1_hm4:
  top1 0.191126, top3 0.709898, recall 0.745995, precision 0.255686, anti false
sf_target_ce2_margin1_hm3:
  top1 0.143345, top3 0.706485, recall 0.787185, precision 0.277868, anti false
sf_target_margin2_rank3_safe5:
  top1 0.221843, top3 0.689420, recall 0.814645, precision 0.270517, anti false
```

The 5000+ sample branch is active:

```text
tmux: repair5_expand5000_waiter_20260528
log:  outputs/logs/phase4f_repair5_expand5000_waiter_20260528.log
status: record/probe stage active, checkpoint rows 738 at 2026-05-28 10:35 +08:00
```

Compression note:

```text
zstd raw trace is lossless
turning compression off does not expose more raw-trace events to labels/model
more information should be tested through tokenization and trace aggregation
```

Queued high-token branch:

```text
config:
  configs/phase4/laur_ltm_full_repair5_attention_native_expand5000_rawtrace_hightoken.yaml

tokenization:
  max_edge_tokens: 96
  max_trace_tokens: 256

tmux:
  repair5_expand5000_hightoken_waiter_20260528

log:
  outputs/logs/phase4f_repair5_expand5000_hightoken_waiter_20260528.log
```

It waits for the current expand5000 run, rebuilds high-token attention-native labels from the same compressed trace, audits split/rule/opportunity coverage, and screens seed61 for:

```text
configs/phase4/generated_repair5_expand5000_hightoken/ht_mlp_target_global.yaml
configs/phase4/generated_repair5_expand5000_hightoken/ht_linear_target_global.yaml
```

No gate is lowered. Phase5.5 and Phase6 remain forbidden.

---

---

## 22. 2026-05-28 expand5000 sleep-check

Remote status at 2026-05-28 10:47 +08:00:

```text
tmux alive:
  repair5_expand5000_waiter_20260528
  repair5_expand5000_hightoken_waiter_20260528

disk:
  100G total, 8.3G used, 92G free

GPU:
  RTX 4090 idle
```

The idle GPU is expected: expand5000 is still in record/probe generation,
not neural-network training.

Progress:

```text
record log files: 428
approx completed record commands: 214
checkpoint rows: 835
compressed raw trace: 1.46GB
probe rows: not started
attention-native label datasets: not generated yet
```

Error scan:

```text
searched record logs for:
  Traceback / Exception / ERROR / FAILED / No space / Killed / CUDA OOM

result:
  no failure matches
  recent record stderr files empty
```

Local verification in the project conda environment:

```text
conda run -n czr004 python -m pytest \
  tests/test_phase4f_attention_native_eval.py \
  tests/test_phase4f_attention_native_labels.py -q

result:
  16 passed, 1 warning
```

Compression note remains unchanged:

```text
zstd is lossless
uncompressed raw trace does not contain more information than compressed zstd
the information bottleneck is tokenization/truncation/model capacity
the high-token branch is the correct information-capacity test
```

No gate is lowered. Phase5.5 and Phase6 remain forbidden.

---

## 23. 2026-05-28 expand5000 progress monitor

Remote progress at 2026-05-28 10:58 +08:00:

```text
tmux alive:
  repair5_expand5000_waiter_20260528
  repair5_expand5000_hightoken_waiter_20260528

disk:
  100G total, 9.0G used, 91G free

GPU:
  RTX 4090 idle

record log files: 484
approx completed record commands: 242
checkpoint rows: 934
compressed raw trace: 2.25GB
probe rows: not started
attention-native label datasets: not generated yet
```

The record-log error scan remained clean:

```text
no Traceback / Exception / ERROR / FAILED / No space / Killed / CUDA OOM
```

Added evidence-only monitor:

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
record log files: 508
approx completed record commands: 254
checkpoint rows: 975
compressed raw trace: 2.50GB
probe/dataset/high-token dataset: missing
disk: 100G total, 9.3G used, 91G free
```

The monitor does not alter labels, training, evaluation, or gates.
No gate is lowered. Phase5.5 and Phase6 remain forbidden.

---

## 24. 2026-05-28 dataset strategy and union guardrail

The next dataset decision is staged:

```text
first:
  run expand5000 as an isolated dataset
  answer whether data volume / high-margin opportunity coverage is the blocker

then, only if useful:
  build an old+new union branch
  do not manually concatenate JSONL files
```

The old 2985-row dataset remains useful for:

```text
historical diagnostics
compatibility / fallback reference
cross-dataset validation
```

New safe-union utility:

```text
src/czr004_teacher/attention_native_union_laur.py
```

Default checks:

```text
duplicate checkpoint_id values are rejected
token-shape mismatches are rejected
schema audit is rerun
split leakage audit is rerun
union_source is recorded per row
```

This keeps normal-token and high-token rows from being mixed accidentally,
and keeps union datasets auditable before any training run.

Tests added:

```text
compatible union succeeds
duplicate checkpoint_id fails by default
token-shape mismatch fails by default
```

Verification:

```text
conda run -n czr004 python -m pytest \
  tests/test_phase4f_attention_native_labels.py \
  tests/test_phase4f_attention_native_eval.py -q

result:
  19 passed, 1 warning
```

Remote status at 2026-05-28 11:16 +08:00:

```text
record log files: 1300
approx completed record commands: 650
checkpoint rows: 2543
compressed raw trace: 3.53GB
probe/dataset/high-token dataset: missing
disk: 100G total, 11G used, 90G free
error scan: clean
```

No gate is lowered. Phase5.5 and Phase6 remain forbidden.

---

## 25. 2026-05-28 expand5000 follow-up waiter

Remote progress at 2026-05-28 11:25 +08:00:

```text
record log files: 1428
approx completed record commands: 714
checkpoint rows: 2790
compressed raw trace: 4.16GB
probe/dataset/high-token dataset: missing
disk: 100G total, 11G used, 90G free
error scan: clean
```

Queued follow-up script:

```text
script:
  run_repair5_expand5000_followup_waiter_20260528.sh

tmux:
  repair5_expand5000_followup_waiter_20260528

log:
  outputs/logs/phase4f_repair5_expand5000_followup_waiter_20260528.log
```

It waits for both current queues:

```text
repair5_expand5000_waiter_20260528
repair5_expand5000_hightoken_waiter_20260528
```

If any expand5000 final gate already permits Phase5.5, the follow-up script
skips all variants. Otherwise it screens seed61 on the isolated normal-token
expand5000 dataset for:

```text
ex5000_follow_pair_focal_m035_lh4
ex5000_follow_global_rank3_anti3
ex5000_follow_target_ce2_margin1_hm3
ex5000_follow_target_margin2_rank3_safe5
```

Only a seed61 pass on original Phase4F + attention-native + safety +
anti-escape can trigger seeds 103/107 and final multi-seed gate.

This is not the old+new union branch. No gate is lowered. Phase5.5 and
Phase6 remain forbidden.

---

## 26. 2026-05-29 expand5000 negative and nextwave

Recovery finished and produced valid expand5000 attention-native datasets, but
all seed61 recovery variants failed promotion. No Phase5.5 runtime work is
allowed.

Evidence:

```text
normal audit:
  outputs/reports/phase4f_repair5_attention_native_expand5000_rawtrace_label_audit.json

high-token audit:
  outputs/reports/phase4f_repair5_attention_native_expand5000_rawtrace_hightoken_label_audit.json

sample_count:
  4956

train / validation:
  4194 / 762

validation high-margin opportunity count:
  310
```

Best recovery signal:

```text
hightoken_ht_mlp_target_global:
  top3 = 0.6998
  harmful recall = 0.7623
  harmful precision = 0.3143
  anti-escape = fail

follow_target_ce2_margin1_hm3:
  harmful recall = 0.8652
  harmful precision = 0.2759
  top3 = 0.6791
  anti-escape = fail
```

Interpretation:

```text
The larger dataset helped but did not solve the coupling problem.
Some variants approach top3 or safety recall separately, but none pass
ranking, safety precision/recall, and anti-escape at the same selected
checkpoint.
```

Repair5 loss update:

```text
new optional losses:
  lambda_high_margin_harmful
  lambda_anti_candidate_safety

purpose:
  preserve safety on high-margin opportunity samples
  reduce "capturing" opportunity by selecting harmful anti-escape candidates

defaults:
  zero, preserving old configs unless explicitly enabled

tests:
  local = 22 passed, 1 warning
  remote = 22 passed, 1 warning
```

Naming clarification:

```text
The older "mlp" variant names meant MLP output heads on an attention backbone.
They were not the Phase5C MLP-only baseline. New configs use explicit names:
  attn_mlp_head_*
  attn_linear_head_*
```

Nextwave is running:

```text
script:
  run_repair5_expand5000_nextwave_20260529.sh

tmux:
  repair5_expand5000_nextwave_20260529

log:
  outputs/logs/phase4f_repair5_expand5000_nextwave_20260529.log
```

Screened seed61 configs:

```text
configs/phase4/generated_repair5_expand5000_nextwave/hightoken_attn_mlp_head_candidate_safe_lh5.yaml
configs/phase4/generated_repair5_expand5000_nextwave/hightoken_attn_linear_head_candidate_safe_lh6.yaml
configs/phase4/generated_repair5_expand5000_nextwave/normal_attn_mlp_head_highcap_candidate_safe.yaml
configs/phase4/generated_repair5_expand5000_nextwave/normal_attn_linear_head_rank_safe.yaml
```

Initial liveness:

```text
time:
  2026-05-29 09:21 +08:00

active:
  hightoken_attn_mlp_head_candidate_safe_lh5 seed61 training

GPU:
  1213 / 12282 MB

epoch1:
  top1 = 0.0497
  top3 = 0.6936
  harmful recall = 0.9065
  harmful precision = 0.2002
  anti_escape_capture = 0.1645
```

No gate is lowered. Phase5.5 and Phase6 remain forbidden until the full
Repair5 promotion rule and later closed-loop evidence are satisfied.

---

## 27. 2026-05-29 post-nextwave waiter

The first nextwave variant shows the intended anti-escape movement but an
unacceptable recall/ranking trade-off:

```text
epoch40:
  anti_escape = pass
  harmful precision = 0.3014
  harmful recall = 0.6168
  top1 = 0.2008
  top3 = 0.6418

epoch100:
  anti_escape = pass
  harmful recall = 0.2069
  top1 = 0.2340
  top3 = 0.6253
```

This is not a pass. It is a diagnostic: the model can be pushed away from
additive/LTM escape, but too much high-margin safety pressure currently
damages recall and does not solve top1.

A follow-on waiter is queued:

```text
script:
  run_repair5_expand5000_postnext_20260529.sh

tmux:
  repair5_expand5000_postnext_20260529

log:
  outputs/logs/phase4f_repair5_expand5000_postnext_20260529.log
```

It waits for:

```text
repair5_expand5000_nextwave_20260529
```

Then it exits if any expand5000 final gate already allows Phase5.5. Otherwise
it screens seed61 variants with:

```text
lower anti_candidate_safety pressure
higher target-rule CE / margin pressure
per-rule safety calibration
the same attention-native gates
```

No gate is lowered. This remains LAUR / LAU LTM `UpdateLTM` rule learning
only, with no agent-action prediction, no PIBT/LaCAM* replacement, and no
learned restart.

---

## 28. 2026-05-29 layered gate policy

GPTPro's advice is accepted as a Repair5 research-gate correction:

```text
Final claim gates stay strict.
Early Repair5 research gates become layered diagnostics.
Hard-label top1/top3 do not alone define attention-native progress.
Closed-loop learned benefit over LTM remains mandatory for claims.
```

This is not a rollback to Repair3 labels and not a permission to enter
runtime. It is a better way to avoid prematurely discarding attention-native
experiments that show utility/opportunity progress before they satisfy the
final gate.

Layer A: development gate

```text
schema / label audit: pass
positive delta proxy: > 0
top1: >= 0.25
top3: >= 0.60
harmful recall: >= 0.70
harmful precision: >= 0.25
anti-escape: high-margin safe-opportunity capture better than reference
avoidable additive/defer fallback: better than reference

Meaning:
  worth continued label/loss/model/data work only
```

Layer B: promotion-candidate gate

```text
top1: >= 0.32
top3: >= 0.65
harmful recall: >= 0.78
harmful precision: >= 0.28
mean delta: > 0
opportunity capture: >= reference + 0.05
avoidable fallback: <= reference - 0.05
multi-seed: must be checked before serious promotion

Meaning:
  worth larger training or tightly scoped closed-loop smoke planning only
```

Layer C: runtime / paper-claim gate

```text
strict original Phase4F gate
strict attention-native gate
strict safety gate
strict anti-escape gate
strict multi-seed gate
closed-loop smoke not worse than LTM before Phase5.5 conclusions
Phase6-scale learned-benefit evidence before paper performance claims
```

Added evaluator:

```text
src/eval/eval_laur_repair5_layered_gate.py

outputs/reports/phase4f_repair5_layered_gate_summary.json
outputs/reports/phase4f_repair5_layered_gate_report.md
```

The evaluator is diagnostic. It always keeps:

```text
phase5p5_allowed = false
phase6_allowed = false
```

Re-score of completed Repair5 results on the remote:

```text
summaries: 27
development pass: 0
promotion-candidate pass: 0
strict seed pass: 0
```

Best partial signals:

```text
rawtrace_edge_sf_target_ce1_margin1_hm4:
  top3 = 0.7099
  recall = 0.7460
  precision = 0.2557
  anti = fail
  top1 = 0.1911

rawtrace_edge_sf_global_pair_neg2_anti2:
  anti = pass
  top3 = 0.7065
  precision = 0.3134
  recall = 0.5767
  top1 = 0.2321

expand5000_hightoken_ht_mlp_target_global:
  top3 = 0.6998
  precision = 0.3143
  recall = 0.7623
  anti = fail
  top1 = 0.1449
```

Conclusion:

```text
The layered policy helps interpret partial progress, but it does not rescue
the completed historical Repair5 runs. Current nextwave/postnext experiments
remain active and necessary.
```

No final gate is lowered. Phase5.5 and Phase6 remain forbidden.

---

