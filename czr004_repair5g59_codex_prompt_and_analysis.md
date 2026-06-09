# czr004 / Repair5G G5.8 结果复盘与下一轮 Codex 推进 Prompt

**建议下一轮名称：** `Repair5G.5.9: G5.8 Offline-G6 Autopsy + Goal-Aware Dual-Channel UpdateLTM Expansion`
**当前提交：** `d78b6908c29d8778961f68aaba290e8a772b26ea`
**当前分支：** `phase4f5p5-stable-attention-lau`
**核心目标：** 用 learning-enhanced `UpdateLTM` 替换 LTM 论文中的粗糙 additive 更新，并最终在闭环 solver 指标上超过 `LaCAM*+plain additive LTM`，同时不改变 LaCAM*/PIBT 语义。

---

## 1. 一句话结论

G5.8 是一个**中等偏好的推进结果**，不是坏结果，也不是方向失败。

它把 G5.7 的主要 blocker 从：

```text
confidence labels insufficient; offline G6 cannot train
```

推进到了：

```text
confidence/warehouse/feature gates passed; offline G6 trained, but did not beat controls safely
```

这说明项目已经越过“能不能构造稳定标签”的第一道墙，进入“当前二分类 safe-mixture 模型是否真的学到可泛化 UpdateLTM 选择规律”的第二道墙。

当前失败不是 goal-aware dual-channel LTM 方向失败，而是：

1. G5.8 的 offline G6 太小、太二分类、太依赖浅层 context features；
2. safe abstention bank 被统计了，但没有真正作为训练头学习；
3. candidate space 可能太窄，只在 `static` 与一个 nonstatic flow-shield expert 之间二选一；
4. train/dev 只有 `20/20` rows，评估易被 seed/map-agent prior、随机控制、label noise 淹没；
5. 当前负控实现和命名还需要修正，不能把“random candidate control”写成“random features control”；
6. 当前 learned selector 不是最终科研贡献，下一轮必须往 **learned bounded goal-aware dual-channel UpdateLTM dynamics / parameter policy** 推。

---

## 2. G5.8 的好消息

### 2.1 G5.7 的窄 blocker 已经被补上

G5.7 卡在：

```text
primary_1000_2000_stable_contexts = 20
training_eligible_contexts = 20
stable_high_confidence_nonstatic_count = 11
stable_static_or_abstain_count = 9
```

G5.8 扩到：

```text
measured_confidence_contexts = 60
primary_1000_2000_stable_contexts = 40
training_eligible_contexts = 40
stable_high_confidence_nonstatic_count = 21
stable_static_or_abstain_count = 19
no_solution_or_budget_abstain_count = 20
```

这很关键。G5.8 证明：1000/2000 ms primary-pair confidence label protocol 是可扩展的，不再只是 G5.7 的 30-context 小样本偶然现象。

### 2.2 Warehouse 没有被隐藏

G5.8 warehouse policy：

```text
warehouse_contexts = 40
no_solution_abstain = 30
longer_budget_needed = 10
warehouse_abstention_policy_passed = true
```

这说明 warehouse/no-solution contexts 没有被静默丢弃。它们被明确分类为 abstention / longer-budget-needed 信号，这与 safe UpdateLTM mixture 的安全策略一致。

### 2.3 Feature matrix 仍然干净

G5.8 feature matrix：

```text
perf_safe_rows = 60
training_eligible_perf_safe_rows = 40
forbidden_feature_count = 0
audit_features_in_perf_safe = []
cost_min/cost_max/cost_span/cost_bounds_respected = audit-only
```

这说明这轮没有用 oracle/probe/future/cost-audit 泄漏来“作弊”训练 perf-safe model。

### 2.4 Offline G6 有弱正信号

G5.8 offline eval：

```text
mean_selected_score = 1.2606729472165
mean_static_score   = 1.271451123822
mean_additive_score = 1.3794258228775
mean_oracle_score   = 1.2519910848995

mean_delta_vs_static   = -0.010778176605500178
mean_delta_vs_additive = -0.11875287566100012
oracle_regret          = 0.008681862316999966
nonstatic_selection_rate = 0.55
```

这说明 learned selector 不是完全无效；它在 dev rows 上确实比 static/additive 的均值更好。但它还没有达到“可信学习策略”的要求。

---

## 3. 为什么最终 decision 仍然失败

最终 decision 是：

```text
offline_g6_safe_mixture_failed_continue_labels_or_candidate_space
```

原因不是 mean selected 没有改善，而是安全学习 gate 没过：

```text
beats_majority_expert = false
beats_random_features = false
beats_shuffled_labels = false
harmful_vs_static_rate_bounded = false
```

尤其是：

```text
mean_selected_score        = 1.2606729472165
mean_majority_score        = 1.2581121034769998
mean_random_control_score  = 1.2565677593865
mean_shuffled_control_score= 1.260300123338
harmful_vs_static_rate     = 0.15
```

这意味着当前 model 的一点改善不能被解释为可靠学习；它甚至没有稳定超过 very simple controls。

### 3.1 训练规模太小

G5.8 train summary：

```text
training_rows = 40
train_rows = 20
dev_rows = 20
feature_count = 25
classes = [
  repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75,
  repair5g2_best_frozen_static_candidate
]
```

20 train / 20 dev 对 25 features 的二分类 logistic 来说非常脆弱。模型很容易学到 seed/map-agent prior 或噪声，而不是真实 UpdateLTM context rule。

### 3.2 当前模型其实只是 binary selector，不是完整 safe mixture

G5.8 target class counts 包含：

```text
no_solution_abstain = 10
longer_budget_needed = 10
```

但 offline model 的 `classes` 只有两个 expert candidate：

```text
nonstatic flow-shield expert
static flow-shield candidate
```

这说明 no-solution / longer-budget bank 被报告了，但没有真正进入训练成为 abstention / feasibility / longer-budget head。当前 G6 不是完整的 safe mixture；它是 `static vs one nonstatic expert` 的浅层二分类器。

### 3.3 abstain_to_static 仍然是 0

G5.8 在三个 margin threshold 下：

```text
abstain_to_static = 0
```

这说明“oracle identity disagrees but static is near-oracle”这种关键安全边界样本还没有被构造出来。没有足够 near-boundary static fallback 样本，就很难学到可靠 abstention。

### 3.4 模型过度自信，校准很差

Eval calibration：

```text
0.50-0.75 bin: accuracy = 0.5, count = 2
>=0.75 bin:    accuracy = 0.4444444444444444, count = 18
abstention_rate = 0.0
```

这很危险。模型大部分时候信心很高，但高置信 bin 的 accuracy 低于 50%。这说明下一轮必须做 calibration / abstention threshold sweep / coverage-risk curve，而不能直接 runtime 接入。

### 3.5 负控实现需要修正

G5.8 evaluator gate 名叫：

```text
beats_random_features
beats_shuffled_labels
```

但脚本行为更接近：

```text
random_candidate baseline
deterministic shuffled candidate baseline
```

不是“训练一个 random-feature model”和“训练一个 shuffled-label model”。下一轮必须把负控实现改成真正的 train/eval controls：

```text
same train/dev split + random features + same model class
same train/dev split + shuffled labels + same model class
train-only majority expert
train-only map-agent prior
static fallback
always nonstatic candidate
oracle upper bound
```

否则 negative-control 结论的学术含义不够清楚。

### 3.6 Candidate space 太窄

当前 offline model 只在两个候选之间选：

```text
repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75
repair5g2_best_frozen_static_candidate
```

这对证明 learning-enhanced UpdateLTM 太弱。目标不是“学会何时选一个手工 expert”，而是学习 goal-aware dual-channel UpdateLTM dynamics。下一轮应该扩展 candidate lattice，并开始设计/诊断 bounded parameter policy：

```text
context -> alpha_cong / alpha_flow / rho / beta / max_flow_shield / static-abstain
```

而不是长期停留在两个候选 ID 的 selector。

---

## 4. 对“不是已经证明双通道 LTM 有效了吗？”的回答

是，已经证明了 **static / hand-designed goal-aware dual-channel flow-shield LTM 是强 baseline**。

但这不等于已经证明了 **learned UpdateLTM policy**。

现在项目处在这个状态：

```text
Level 0: hand-designed static flow-shield rule
  已经有效，是强 baseline。

Level 1: selector over hand-designed UpdateLTM candidates
  G5.8 只有弱正信号，未通过 controls。

Level 2: learned bounded dual-channel UpdateLTM parameter / residual / mixture policy
  这是项目要推进的核心论文贡献。

Level 3: graph/trace neural UpdateLTM policy with safety/fallback
  后续更强版本。
```

所以 G5.8 的失败不是“双通道 LTM 失败”，而是“浅层二分类 selector 尚未证明自己比 static/majority/controls 更有学习价值”。

下一轮必须把 Codex 从“继续小修 G6 selector”推向：

```text
goal-aware dual-channel candidate-space expansion
+
calibrated abstention / fallback
+
direct learned bounded UpdateLTM parameter policy diagnostic
```

---

## 5. 下一轮应该做什么

建议下一轮叫：

```text
Repair5G.5.9: Offline G6 Autopsy + Goal-Aware Dual-Channel Candidate/Parameter Expansion
```

目标不是马上 runtime，不是碰 reserved IDs，也不是声称 Phase5.5。

目标是回答四个问题：

```text
Q1. G5.8 offline G6 为什么输给 majority/random/shuffled controls？
Q2. 当前失败是 feature signal 不足、label noise、candidate space 太窄，还是 model/calibration 问题？
Q3. 扩展 goal-aware dual-channel UpdateLTM candidate lattice 后，oracle upper bound 是否明显增大？
Q4. 一个 calibrated abstention-aware policy 是否能在 observed dev 上：
    - beat static
    - beat additive
    - beat train-only majority/map-agent priors
    - beat true random-feature and shuffled-label trained controls
    - harmful rate <= 5-10%
```

---

# Copy/paste prompt for Codex

```text
Continue czr004 on branch phase4f5p5-stable-attention-lau after commit d78b6908c29d8778961f68aaba290e8a772b26ea repair5g: expand confidence labels and gate offline g6.

Goal:
Implement Repair5G.5.9: a rigorous autopsy of G5.8 offline G6 failure, then push the project back toward goal-aware dual-channel learned UpdateLTM dynamics. G5.8 crossed the confidence-label gate, so the next blocker is not label sufficiency. The next blocker is whether the learned policy actually beats static/majority/random/shuffled controls and whether the candidate/feature space is rich enough to support learning.

Main project objective:
Use learning-enhanced UpdateLTM to replace the coarse additive update in the LTM paper and eventually beat LaCAM*+plain additive LTM under closed-loop solver metrics, without changing LaCAM*/PIBT semantics.

Read first:
  deep-research-report.md
  phase4_6_laur_ltm_codex_execution_plan.md
  docs/aaai_quality_requirements.md
  czr004_repair5g58_targeted_confidence_expansion_offline_g6_plan.md
  outputs/reports/phase5p5_repair5g57_final_interpretation.md
  outputs/reports/phase5p5_repair5g58_protocol_overview.md
  outputs/reports/phase5p5_repair5g58_decision.md
  outputs/reports/phase5p5_repair5g58_decision_summary.json
  outputs/reports/phase5p5_repair5g58_primary_pair_confidence_expansion_summary.json
  outputs/reports/phase5p5_repair5g58_confidence_weighted_targets_summary.json
  outputs/reports/phase5p5_repair5g58_training_label_threshold_decision_summary.json
  outputs/reports/phase5p5_repair5g58_warehouse_abstention_policy_summary.json
  outputs/reports/phase5p5_repair5g58_g6_feature_matrix_summary.json
  outputs/reports/phase5p5_repair5g58_offline_safe_mixture_train_summary.json
  outputs/reports/phase5p5_repair5g58_offline_safe_mixture_eval_summary.json
  scripts/repair5g58_common.py
  scripts/train_repair5g58_offline_safe_mixture.py
  scripts/eval_repair5g58_offline_safe_mixture.py

Preserve this interpretation:
  - G5.8 decision = offline_g6_safe_mixture_failed_continue_labels_or_candidate_space.
  - G5.8 is not a direction failure.
  - G5.8 is a useful progression from "cannot train" to "trained but failed safe learned-policy controls".
  - confidence expansion passed:
      measured_confidence_contexts = 60
      primary_1000_2000_stable_contexts = 40
      training_eligible_contexts = 40
      stable_high_confidence_nonstatic_count = 21
      stable_static_or_abstain_count = 19
      no_solution_or_budget_abstain_count = 20
  - warehouse policy passed:
      no_solution_abstain = 30
      longer_budget_needed = 10
  - feature matrix passed:
      perf_safe_rows = 60
      audit_plus_perf_rows = 60
      forbidden_feature_count = 0
      cost audit features remain audit-only
  - offline training ran:
      training_rows = 40
      train_rows = 20
      dev_rows = 20
      feature_count = 25
      model = calibrated/logistic-style binary selector
      model classes are only:
        repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75
        repair5g2_best_frozen_static_candidate
  - offline eval had weak positive mean improvement:
      mean_delta_vs_static = -0.010778176605500178
      mean_delta_vs_additive = -0.11875287566100012
      oracle_regret = 0.008681862316999966
  - offline eval failed because:
      beats_majority_expert = false
      beats_random_features = false
      beats_shuffled_labels = false
      harmful_vs_static_rate_bounded = false
      harmful_vs_static_rate = 0.15
      high-confidence calibration is poor
      abstention_rate = 0.0
  - G5.8's "random features" and "shuffled labels" gates need semantic audit because eval_repair5g58 currently appears to use random/shuffled candidate controls rather than training true random-feature/shuffled-label models.
  - G5.8 counted no_solution/longer_budget examples but did not train an abstention/feasibility head.
  - abstain_to_static remained 0.
  - IDs 166..205 remain untouched.
  - phase5p5_allowed=false, phase6_allowed=false, aaai_ready=false, runtime_claim_allowed=false.
  - The project direction remains goal-aware dual-channel LTM + learned bounded UpdateLTM dynamics, not MAPF action learning, not learned restart, not priority learning.

Do not:
  - modify external/lacam2/lacam2/**
  - change PIBT, LaCAM*, candidate generation, conflict, pruning, OPEN/EXPLORED, rewrite, incumbent, or restart semantics
  - introduce action prediction
  - introduce learned restart
  - output h_i(v), action logits, priority overrides, or candidate deletion
  - claim Phase5.5 or Phase6
  - claim AAAI-ready
  - run or peek IDs 166..205
  - use final full-run outcomes as per-update labels
  - integrate learned G6 into runtime C++
  - train on unstable, unknown-confidence, or unclassified labels as gold expert labels
  - use audit-only cost_audit features in a performance-safe model
  - hide warehouse/no-solution contexts
  - present a binary selector over two hand-coded candidates as the final learning contribution

Tasks:

1. Add:
   czr004_repair5g59_offline_g6_autopsy_goal_aware_dual_channel_update_plan.md

   Update:
   docs/codex-worklog.md

2. Verify all required G5.8 artifacts. If missing, stop with:
   missing_g58_artifacts_stop

3. Write:
   outputs/reports/phase5p5_repair5g58_final_interpretation.md
   outputs/reports/phase5p5_repair5g59_protocol_overview.md

4. Implement a rigorous G5.8 offline eval autopsy:
   scripts/analyze_repair5g59_g58_offline_eval_autopsy.py

   It must produce:
   outputs/reports/phase5p5_repair5g59_g58_offline_eval_autopsy.md
   outputs/reports/phase5p5_repair5g59_g58_offline_eval_autopsy_summary.json
   outputs/tables/phase5p5_repair5g59_g58_eval_confusion_by_map_agent.csv
   outputs/tables/phase5p5_repair5g59_g58_eval_harmful_rows.csv
   outputs/tables/phase5p5_repair5g59_g58_eval_helpful_rows.csv
   outputs/tables/phase5p5_repair5g59_g58_eval_calibration_bins.csv

   Required analysis:
     - confusion matrix target vs selected
     - per-map, per-agent, per-seed breakdown
     - stable_static vs stable_high_confidence_nonstatic error types
     - harmful rows where selected_score > static_score + 0.005
     - helpful rows where selected_score < static_score - 0.005
     - static regret distribution
     - oracle gap distribution
     - selected vs oracle regret distribution
     - confidence vs accuracy bins
     - coverage-risk curve over abstention thresholds 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90
     - identify whether failure is primarily:
        model_overfit_or_calibration
        feature_signal_insufficient
        label_noise_or_budget_sensitivity
        candidate_space_too_narrow
        control_implementation_bug
        insufficient_train_dev_rows

5. Fix and rerun the offline controls semantically, without overwriting the original G5.8 result:
   scripts/train_repair5g59_control_models.py
   scripts/eval_repair5g59_control_models.py

   Required controls:
     - static flow-shield fallback
     - always nonstatic G5.8 majority candidate
     - always additive
     - train-only majority candidate
     - train-only map-agent prior
     - true random-feature model using same train/dev split and same model class
     - true shuffled-label model using same train/dev split and same model class
     - random candidate baseline, clearly named as random_candidate, not random_features
     - oracle upper bound

   Important:
     - compute feature normalization on train rows only
     - compute majority/prior baselines on train rows only
     - report any previous G5.8 naming mismatch honestly
     - do not change the original G5.8 summary; write G5.9 corrected-control summaries separately

6. Build a stronger feature audit:
   scripts/analyze_repair5g59_feature_signal_quality.py

   It must report:
     - feature variance / constant features
     - train/dev distribution shift by feature
     - map-agent leakage risk
     - label separability using simple univariate effects
     - feature ablations:
        no map dimensions
        no density/free-cell features
        no incumbent/history features
        only trace event features
        only C/F traffic-map summary features
     - whether current features are too weak to distinguish static vs nonstatic safely

   Write:
     outputs/reports/phase5p5_repair5g59_feature_signal_quality.md
     outputs/reports/phase5p5_repair5g59_feature_signal_quality_summary.json

7. Expand goal-aware dual-channel UpdateLTM candidate space, but keep semantics safe:
   scripts/create_repair5g59_goal_aware_dual_channel_candidate_lattice.py
   scripts/analyze_repair5g59_candidate_lattice.py

   Candidate lattice must remain UpdateLTM-only and bounded. It may vary:
     - alpha_cong_committed
     - alpha_cong_blocked
     - alpha_flow_progress
     - alpha_flow_wait_or_nonprogress
     - rho_cong
     - rho_flow
     - flow_shield_beta
     - max_flow_shield
     - static fallback
     - additive fallback
     - C-only / F-disabled ablations

   It must not output actions, priorities, h-values, restart choices, or candidate deletion.

   Gate candidate count to a manageable number first, e.g. <= 16 for local smoke. If more is needed, write a server plan.

   Write:
     outputs/reports/phase5p5_repair5g59_candidate_lattice_summary.json
     outputs/reports/phase5p5_repair5g59_candidate_lattice.md

8. Run targeted counterfactual probes over the expanded candidate lattice:
   scripts/run_repair5g59_goal_aware_dual_channel_counterfactuals.py
   scripts/analyze_repair5g59_goal_aware_dual_channel_counterfactuals.py

   Focus:
     - observed IDs only
     - do not run 166..205
     - primary budgets 1000 and 2000 ms
     - 250 ms stress-only
     - include later-iteration contexts if checkpoints exist
     - include it0/it1/it2 stratification if available
     - include random/maze/warehouse and 50/100 agents
     - record if local compute cannot finish

   Required gates:
     - observed_ids_only = true
     - ids_166_205_untouched = true
     - measured_contexts >= 60, preferably >= 100 if local/server feasible
     - later_iteration_measured_contexts >= 20, or explicitly explain why unavailable
     - primary_1000_2000_stable_contexts >= 40
     - oracle_beats_static_fraction reported
     - mean_oracle_gap_over_static reported
     - candidate_space_oracle_gap_vs_g58 reported
     - no_solution/longer_budget explicitly classified

   Decision if oracle upper bound does not improve:
     candidate_space_gap_expand_flow_shield_lattice

9. Create G5.9 confidence targets v3:
   scripts/create_repair5g59_confidence_targets_v3.py
   scripts/analyze_repair5g59_confidence_targets_v3.py

   Classes:
     stable_high_confidence_nonstatic
     stable_static
     abstain_to_static
     no_solution_abstain
     longer_budget_needed
     budget_sensitive_exclude
     exclude_from_training

   Requirements:
     - no_solution_abstain and longer_budget_needed must train only abstention/feasibility head, not expert-selection positives
     - budget_sensitive_exclude must not be gold expert labels
     - abstain_to_static should be actively searched for; if still 0, write a near-boundary diagnostic explaining why
     - thresholds 0.0025, 0.005, 0.010
     - threshold decision before training

10. Build an abstention-aware offline policy, not just a binary expert selector:
    scripts/train_repair5g59_abstention_aware_offline_policy.py
    scripts/eval_repair5g59_abstention_aware_offline_policy.py

    Allowed models:
      - calibrated logistic regression
      - calibrated multinomial logistic regression
      - tiny MLP <=64 hidden units

    Preferred structure:
      Head A: feasibility/abstention head
        classes:
          trainable_expert_selection
          static_fallback
          no_solution_abstain
          longer_budget_needed
          budget_sensitive_abstain

      Head B: expert-selection head, only on stable eligible contexts
        classes:
          static fallback
          expanded safe UpdateLTM candidates from the goal-aware dual-channel lattice

    Must report:
      - coverage-risk curve
      - harmful_vs_static_rate by threshold
      - mean_delta_vs_static
      - mean_delta_vs_additive
      - mean_delta_vs_train_only_majority
      - mean_delta_vs_map_agent_prior
      - mean_delta_vs_random_feature_model
      - mean_delta_vs_shuffled_label_model
      - oracle_regret
      - calibration bins
      - per-map/agent breakdown
      - no runtime claim

    Passing gate:
      - observed_dev_only = true
      - eval_rows_gt_0 = true
      - mean_delta_vs_static < 0
      - mean_delta_vs_additive < 0
      - beats train-only majority
      - beats train-only map-agent prior
      - beats true random-feature model
      - beats true shuffled-label model
      - harmful_vs_static_rate <= 0.10, preferably <= 0.05
      - calibration reported
      - abstention coverage-risk reported
      - static fallback available
      - no forbidden features
      - no IDs 166..205

11. Write direct learned bounded UpdateLTM policy design, even if not trained yet:
    outputs/reports/phase5p5_repair5g59_learned_bounded_dual_channel_update_policy_design.md
    outputs/reports/phase5p5_repair5g59_learned_bounded_dual_channel_update_policy_design_summary.json

    This should explicitly move beyond a hand-coded candidate selector:
      context / trace / C-F traffic state
        -> bounded alpha/rho/beta/max_flow_shield parameter policy
        -> UpdateLTM
        -> DirectedTrafficMap
        -> WeightedDistanceTable
        -> original LaCAM*/PIBT semantics unchanged

    Include:
      - permitted outputs
      - forbidden outputs
      - training labels needed
      - safety projection
      - static/additive fallback
      - offline-only stage gate
      - future runtime preflight requirements

12. Final decision writer:
    scripts/write_repair5g59_decision.py

    Write:
      outputs/reports/phase5p5_repair5g59_decision.md
      outputs/reports/phase5p5_repair5g59_decision_summary.json

    Decision options:
      missing_g58_artifacts_stop
      g58_eval_control_bug_fixed_continue
      feature_signal_insufficient_continue_feature_design
      candidate_space_gap_expand_flow_shield_lattice
      confidence_targets_v3_insufficient_continue_probe_design
      abstention_aware_policy_failed_continue_labels_or_features
      abstention_aware_policy_passed_continue_runtime_preflight_design
      learned_bounded_update_policy_design_ready_offline_only
      server_required_for_candidate_lattice_or_later_iteration_expansion
      stop_for_protocol_or_semantic_bug

    Always keep:
      phase5p5_allowed=false
      phase6_allowed=false
      aaai_ready=false
      runtime_claim_allowed=false

13. Validation:
    - python -m py_compile all new/modified Python scripts
    - if C++ changed, run scripts/build_phase1a_batch.ps1; avoid C++ changes unless absolutely necessary
    - pytest focused tests if available; otherwise manual fallback harness
    - reserved-ID guard rejects 166
    - JSON summaries parse
    - CSV row-count sanity checks pass
    - git diff --check
    - commit and push only G5.9-related tracked files/reports
    - leave unrelated dirty/untracked files untouched

Commit message:
  repair5g: autopsy offline g6 and expand goal-aware update search

One-sentence guiding principle:
  G5.8 proved the confidence-label gate can pass, but the binary offline selector did not beat safe controls; G5.9 must diagnose that failure, fix controls/calibration/abstention, expand the goal-aware dual-channel UpdateLTM candidate/parameter space, and move the project closer to learned bounded UpdateLTM dynamics rather than a two-candidate hand-coded selector.
```
