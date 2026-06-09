# czr004 Repair5G.5.12 方向判断与 Codex 推进 Prompt

生成日期：2026-06-07
基准提交：`4a2b75d repair5g: reingest full g511 lattice run`
分支：`phase4f5p5-stable-attention-lau`
状态：完成版，用于启动 G5.12；不包含 Phase5.5、Phase6、runtime learned policy 或 AAAI-ready claim。

依据文件：
- `outputs/reports/phase5p5_repair5g511_full_lattice_integrity_summary.json`
- `outputs/reports/phase5p5_repair5g511_lattice_oracle_gap_full_summary.json`
- `outputs/reports/phase5p5_repair5g511_confidence_targets_v5_summary.json`
- `outputs/reports/phase5p5_repair5g511_decision_summary.json`

## 0. 一句话结论

G5.11 是一个**明确的好结果**：完整 60-context / 14-candidate / 4-budget lattice counterfactual 已经跑通，候选空间 oracle upper bound 明确优于 G5.8、static 和 additive。它失败的不是 `goal_aware_dual_channel_ltm` 方向，而是 **confidence target 仍然沿用“context -> 单一 oracle class”的旧 selector 标签设计**，导致 safe label coverage gate 没过。

下一步不应该继续扩大同一个 context-level selector，也不应该立刻 runtime；应该做 G5.12：

```text
context-level oracle-class target
  -> candidate-level regret / ranking / harmful-risk targets
  -> learned bounded dual-channel parameter scoring policy
  -> static fallback when predicted improvement/risk is not safe
```

这一步才真正接近项目主目标：学习增强 `UpdateLTM`，替换 LTM 论文里的粗糙 additive update。

---

## 1. G5.11 结果到底怎么样？

### 1.1 完整性是强通过

G5.11 采纳的是干净服务器运行：

```text
server accepted run: max-workers = 1
solver tasks: 240 / 240
lattice probe rows: 3360
measured contexts: 60
candidate count: 14
primary 1000/2000 contexts: 60
duplicate context/candidate/budget rows: 0
seed range: 146..155
ids 166..205 untouched: true
```

这说明 G5.10 的 executable lattice adapter 不只是 smoke，而是已经能支撑完整 observed-ID bank 的 same-context counterfactual run。

### 1.2 候选空间 gate 是强通过

核心结果：

```text
decision = full_lattice_candidate_space_passed_continue_targets
candidate_space_oracle_gap_vs_g58 = -0.028445334327249994
candidate_space_oracle_gap_vs_g510_smoke = -0.013364706402250015
mean_oracle_gap_over_static = -0.035097435576500004
mean_oracle_gap_over_additive = -0.12287598200416668
oracle_beats_static_fraction = 0.8666666666666667
oracle_beats_additive_fraction = 1.0
primary_1000_2000_stable_contexts = 60
stress_250_disagreement_rate = 0.0
bonus_500_agreement_rate = 1.0
```

这很关键。它说明 14-candidate bounded dual-channel UpdateLTM parameter lattice 的 oracle upper bound 不只是小样本偶然，而是在完整 60 contexts 上稳定优于 G5.8 的狭窄 candidate space，并且相对 additive 的 gap 非常大。

### 1.3 最好单候选也有意义

完整分布里：

```text
best_single_candidate = repair5g59_slow_decay_high_shield
per-candidate oracle wins:
  slow_decay_high_shield = 23
  low_beta_high_cap = 8
  wait_conservative = 7
  block_heavy_flow_guard = 6
  high_beta_cap_safe = 5
  static_flow_shield = 5
  commit_heavy_flow_guard = 4
  others smaller
```

这说明 full-run 不是一个候选偶然垄断所有 map/agent；但 `slow_decay_high_shield` 明显成为强 candidate。下一轮应把它当作 strong static parameter baseline，而不是只当 oracle lattice 的一个离散项。

---

## 2. 为什么 final decision 还是 failed？

G5.11 final decision 是：

```text
confidence_targets_v5_failed_continue_label_design
```

失败点不是 candidate-space，而是 target gate：

```text
label_counts:
  stable_high_confidence_parameter_candidate = 52
  stable_static = 8

stable_static_or_abstain = 8 < 10
no_solution_or_budget_abstain_count = 0
head_b_training_rows = 60
```

也就是说，完整 lattice 已经让 52 / 60 个 context 都有稳定非 static 参数候选可赢，只有 8 个 stable static，没有 no-solution / longer-budget / budget-abstain。这对“候选空间是否有潜力”是好事，但对旧版 safe-mixture label gate 是坏事，因为旧 gate 期待至少一些 abstention / static / budget-sensitive 样本。

因此 G5.11 的失败原因是：

```text
1. 旧 target 设计仍是 context-level oracle-class classification；
2. 它把每个 context 压成一个 target_candidate_id；
3. 它要求 static/abstain/no-solution 覆盖；
4. 但 full lattice 结果恰好显示大多数 context 都有可赢的非 static bounded parameter candidate；
5. 所以 gate 因 safe label balance 不足而阻断 feature v3 / policy training。
```

这不是方向失败。恰恰相反，方向强了：bounded dual-channel parameter lattice 让 oracle upper bound 大幅提高。

---

## 3. 方向有没有问题？

没有。现在更能确定：`goal_aware_dual_channel_ltm` 是正确主线。

之前 G5.8/G5.9 已经证明 narrow selector 不够：

```text
G5.8:
  static vs one nonstatic candidate 的 selector 有弱正信号，但不过 controls。

G5.9:
  修正 controls 后确认旧 selector 打不过 train-only majority / map-agent prior / random-feature model。
  同时建立了 14-candidate bounded dual-channel parameter lattice。

G5.10:
  lattice adapter 可执行，本地 2-context smoke 正向。

G5.11:
  full 60-context lattice oracle upper bound 强通过。
```

这条链条说明：

```text
不要继续押注 two-class selector；
应该转向 learned bounded dual-channel UpdateLTM parameter policy。
```

真正的问题是：我们现在还没有学会**如何从 context 预测哪个参数候选安全有效**。G5.11 已经证明“可用参数空间存在”，还没有证明“模型能安全选择参数”。

---

## 4. 旧 target 设计为什么不够？

当前 v5 target 是这样分类的：

```text
if primary 1000/2000 missing:
  exclude
elif no feasible:
  no_solution_abstain
elif 1000 infeasible and 2000 feasible:
  longer_budget_needed
elif primary oracle unstable and static near oracle:
  abstain_to_static
elif stable oracle == static:
  stable_static
elif stable nonstatic beats static by margin:
  stable_high_confidence_parameter_candidate
else:
  stable_static
```

这对早期 selector 是合理的，但现在 lattice full run 后已经太粗。因为每个 context 实际上有 14 个候选、4 个预算、candidate-level score、harmful/helpful 信息。把它压成一个 context-level oracle class，会丢掉大量训练信号。

更好的 target 应该是 candidate-level：

```text
for each context and candidate:
  delta_vs_static_1000
  delta_vs_static_2000
  mean_delta_vs_static_primary
  oracle_regret
  harmful_vs_static
  helpful_vs_static
  stable_candidate_score
  candidate_parameter_vector
```

这样 60 contexts 可以变成至少：

```text
60 contexts x 14 candidates = 840 candidate-level primary examples
```

如果按 1000/2000 分开，还有 1680 primary-budget examples。这样模型可以学的是：

```text
f(context_features, candidate_parameter_features) -> predicted utility / risk
```

而不是：

```text
f(context_features) -> one candidate id
```

这更接近“学习双通道 LTM 参数”。

---

## 5. 下一步应该做什么？

下一步建议做 **Repair5G.5.12: Lattice Regret/Ranking Target Redesign + Local-PC Candidate-Level Policy Gate**。

核心任务：

```text
把 G5.11 full lattice results 从 context-level oracle labels
改造成 candidate-level regret / ranking / harmful-risk labels。
```

然后训练/评估：

```text
input:
  runtime-safe context features
  + candidate parameter vector
  + candidate family indicators

target:
  mean_delta_vs_static_primary
  harmful_vs_static
  oracle_regret / rank

policy:
  score all 14 bounded candidates
  choose predicted best only if predicted improvement > margin and predicted harmful risk < threshold
  otherwise fallback static
```

### 5.1 为什么这比继续扩大 context-level labels 更好？

因为现在缺的不是 nonstatic positive，nonstatic positive 已经太多了：

```text
stable_high_confidence_parameter_candidate = 52
stable_static = 8
```

继续盲目找 static contexts 会很慢，而且可能偏离“学习参数”的主线。更好的做法是利用每个 context 内部的 14 个候选对比，构造 hard negatives：

```text
同一个 context:
  oracle candidate = good positive
  harmful candidates = hard negative
  near-static candidates = fallback / neutral
  static candidate = safe baseline
```

这天然给 safety learning 提供大量负例，不需要等待 no-solution contexts。

### 5.2 还要不要 no-solution / abstention？

要，但不要让它阻断 candidate-level policy 的离线诊断。

建议分成两个 gate：

```text
Gate A: candidate-level parameter ranking / risk policy
  可以在 G5.11 full lattice data 上训练诊断；
  不需要 no-solution 才能做 offline ranking。

Gate B: runtime-safe abstention / deployment readiness
  必须有 no-solution / budget-sensitive / OOD / static-near-oracle coverage；
  没有这些不能 runtime claim。
```

这样既不破坏安全纪律，也不会因为 no-solution 为 0 而阻断对参数学习本身的研究。

### 5.3 本地 PC 是否够？

这次 G5.11 说明完整 3360-row 规模并不大。正式服务器用 `--max-workers 1` 都能跑完 240 / 240 solver tasks，所以后续 **同等规模或更小规模** 的 G5.12 本地 PC 应该可以承担，尤其是：

```text
只做 re-analysis / target redesign / candidate-level model training：
  本地足够。

少量新增 targeted contexts / rerun：
  本地也可以先跑。

扩大到更多 contexts、更多 candidate lattice、more budgets：
  再上服务器。
```

需要注意的是，G5.11 的并发 4 发生共享 JSONL 污染风险。以后本地或服务器都应该：

```text
默认 max-workers=1
或每个 worker 单独 JSONL，最后 merge + dedupe
不要多个 solver 进程并发 append 同一个 JSONL。
```

---

## 6. G5.12 Codex Prompt

下面这段可直接发给 Codex。

```text
Continue czr004 on branch phase4f5p5-stable-attention-lau after commit 4a2b75d repair5g: reingest full g511 lattice run.

Implement Repair5G.5.12: redesign targets from context-level oracle class labels to candidate-level regret/ranking/harmful-risk labels over the full G5.11 executable goal-aware dual-channel UpdateLTM lattice.

Preserve interpretation:
- G5.11 is a strong positive candidate-space result, not a direction failure.
- Full clean run completed 240/240 solver tasks with max-workers=1, 3360 lattice probe rows, 60 contexts, 14 candidates, 4 budgets, and IDs 166..205 untouched.
- Integrity passed.
- Candidate-space gate passed:
  candidate_space_oracle_gap_vs_g58=-0.028445334327249994,
  mean_oracle_gap_over_static=-0.035097435576500004,
  mean_oracle_gap_over_additive=-0.12287598200416668,
  oracle_beats_static_fraction=0.8666666666666667,
  oracle_beats_additive_fraction=1.0,
  primary_1000_2000_stable_contexts=60,
  stress_250_disagreement_rate=0.0,
  bonus_500_agreement_rate=1.0.
- Best single candidate is repair5g59_slow_decay_high_shield, but oracle wins are distributed across several parameter candidates.
- G5.11 stopped because context-level confidence targets v5 had 52 stable_high_confidence_parameter_candidate and only 8 stable_static, no no_solution/longer-budget/abstain coverage.
- This is a label design blocker, not a parameter-lattice blocker.
- The next step is not another two-class selector and not runtime integration.
- The next step is candidate-level parameter ranking/regret/risk learning.

Main project objective:
Use learning-enhanced UpdateLTM to replace the coarse additive update in the LTM paper and eventually beat LaCAM*+plain additive LTM under closed-loop solver metrics, without changing LaCAM*/PIBT semantics.

Hard constraints:
- Do not modify external/lacam2/lacam2/**.
- Do not change PIBT, LaCAM*, candidate generation, conflicts, pruning, OPEN/EXPLORED, rewrite, incumbent, or restart semantics.
- Do not introduce action prediction, priority prediction, learned restart, h-values, candidate deletion, or MAPF action logits.
- Do not run or peek IDs 166..205.
- Do not claim Phase5.5, Phase6, runtime learned policy, or AAAI-ready.
- Do not train or evaluate on final full-run outcomes as per-update labels outside the same-context counterfactual UpdateLTM probe protocol.
- Leave unrelated dirty/untracked files untouched.
- For this round, prefer local PC execution; only write a server plan if the task expands beyond the current 60-context / 14-candidate scale.

Read first:
  deep-research-report.md
  phase4_6_laur_ltm_codex_execution_plan.md
  docs/aaai_quality_requirements.md
  czr004_repair5g511_full_server_lattice_reingest_plan.md
  outputs/reports/phase5p5_repair5g511_full_lattice_integrity_summary.json
  outputs/reports/phase5p5_repair5g511_lattice_oracle_gap_full_summary.json
  outputs/reports/phase5p5_repair5g511_confidence_targets_v5_summary.json
  outputs/reports/phase5p5_repair5g511_decision_summary.json
  outputs/tables/phase5p5_repair5g511_full_lattice_counterfactual_results.csv
  outputs/tables/phase5p5_repair5g511_lattice_oracle_by_context.csv
  outputs/tables/phase5p5_repair5g511_lattice_candidate_distribution.csv
  outputs/tables/phase5p5_repair5g511_lattice_by_map_agent.csv
  outputs/tables/phase5p5_repair5g511_confidence_targets_v5.csv

Tasks:

1. Add:
   czr004_repair5g512_lattice_regret_ranking_target_redesign_plan.md
   and update docs/codex-worklog.md.

2. Verify G5.11 artifacts. If missing, stop with:
   missing_g511_artifacts_stop.

3. Write:
   outputs/reports/phase5p5_repair5g511_final_interpretation.md
   outputs/reports/phase5p5_repair5g512_protocol_overview.md

4. Implement candidate-level target construction:
   scripts/create_repair5g512_candidate_regret_targets.py
   scripts/analyze_repair5g512_candidate_regret_targets.py

   Build rows at candidate-level, not context-level:
     one row per context x candidate, aggregated over primary 1000/2000 budgets.

   Required fields:
     context_id
     normalized_context_key
     map
     agents
     seed
     iteration
     candidate_id
     candidate parameter columns:
       alpha_cong_committed
       alpha_cong_blocked
       alpha_flow_progress
       alpha_flow_wait_or_nonprogress
       rho_cong
       rho_flow
       flow_shield_beta
       max_flow_shield
       static_fallback
       additive_fallback
       c_only_f_disabled
     score_1000
     score_2000
     static_score_1000
     static_score_2000
     additive_score_1000
     additive_score_2000
     delta_vs_static_1000
     delta_vs_static_2000
     mean_delta_vs_static_primary
     mean_delta_vs_additive_primary
     oracle_regret_primary
     rank_primary
     helpful_vs_static
     harmful_vs_static
     near_static_neutral
     oracle_candidate_for_context
     target_weight
     observed_ids_only
     ids_166_205_untouched

   Label classes:
     helpful_parameter_candidate
     harmful_parameter_candidate
     neutral_parameter_candidate
     static_fallback_candidate
     additive_bad_baseline
     c_only_ablation_candidate

   Gates:
     candidate_level_rows >= 840
     contexts == 60
     candidates == 14
     helpful_count > 0
     harmful_count > 0
     neutral_or_static_count > 0
     additive_bad_count > 0
     ids_166_205_untouched = true
     observed_ids_only = true

5. Analyze the target-design failure from G5.11:
   scripts/analyze_repair5g512_context_vs_candidate_target_gap.py

   Compare:
     context-level v5 labels:
       52 nonstatic / 8 static / 0 abstain
   versus:
     candidate-level regret labels:
       helpful / harmful / neutral / static / additive-bad distribution.

   Write:
     outputs/reports/phase5p5_repair5g512_target_redesign_decision.md
     outputs/reports/phase5p5_repair5g512_target_redesign_decision_summary.json

   Required interpretation:
     G5.11 failed because context-level oracle class labels are too coarse for a parameter lattice.
     Candidate-level regret/ranking is the right target for learned bounded UpdateLTM parameter policy.

6. Build feature matrix v3 for candidate-level policy:
   scripts/create_repair5g512_candidate_feature_matrix_v3.py
   scripts/analyze_repair5g512_candidate_feature_signal_v3.py

   Input features:
     A. Runtime-safe context features from G5.10/G5.11:
        event counts, progress ratios, wait/block counts, map/agent/density fields, iteration fields.
     B. Candidate parameter features:
        alpha/rho/beta/max_shield and family flags.
     C. Interaction features:
        candidate params x context congestion/progress/wait summary.
     D. Optional audit-only features:
        cost/span/probe/oracle fields must remain audit-only and excluded from performance-safe models.

   Do not include:
     future outcome
     probe result
     oracle score
     target label
     final full-run outcome
     actions
     priorities
     restart
     h-values
     candidate deletion

   Gates:
     perf_safe_candidate_rows >= 840
     forbidden_feature_count = 0
     candidate_param_features_present = true
     interaction_features_present = true
     train/dev split observed-only and seed-based
     audit-only features excluded from perf-safe model.

7. Train offline candidate-level models only if target and feature gates pass:
   scripts/train_repair5g512_candidate_regret_ranker.py
   scripts/eval_repair5g512_candidate_regret_ranker.py

   Allowed model types:
     calibrated linear regression / logistic ranking
     pairwise ranking model
     tiny MLP <=64 hidden units
     monotone-safe fallback wrapper if simple to implement

   The model should score each candidate for a context:
     predicted_delta_vs_static
     predicted_harmful_risk
     predicted_oracle_regret or rank score

   Policy:
     score all 14 candidate parameter rows for a context.
     select predicted best candidate only if:
       predicted improvement over static <= -margin
       predicted harmful risk <= threshold
       confidence / margin sufficient
     otherwise fallback to static_flow_shield.

   Baselines:
     static_flow_shield
     additive_ltm
     best_single_train_candidate
     slow_decay_high_shield fixed
     train-only majority candidate
     train-only map-agent prior
     random candidate
     true random-feature model
     true shuffled-label model
     oracle upper bound

   Eval gates:
     mean_delta_vs_static < 0
     mean_delta_vs_additive < 0
     beats_best_single_train_candidate OR clearly reports why not
     beats_train_only_map_agent_prior
     beats_true_random_feature_model
     beats_true_shuffled_label_model
     harmful_vs_static_rate <= 0.10, preferably <= 0.05
     coverage/risk curve reported
     calibration reported
     no IDs 166..205
     runtime_claim_allowed=false

8. Static/abstention coverage should be separated from candidate-ranking progress:
   - Do not let no_solution_or_budget_abstain_count=0 block offline candidate-level ranking diagnostics.
   - But keep runtime/Phase5.5 closed unless a later safety package includes static, abstention, no-solution, budget-sensitive, and OOD coverage.
   - Write this explicitly in the decision.

9. Optional local-PC targeted augmentation, only if quick:
   scripts/run_repair5g512_static_boundary_probe_local.py

   Search observed IDs only, excluding 166..205, for static-near-oracle or static-wins contexts.
   Prefer:
     later-iteration contexts from existing observed IDs,
     warehouse/maze hard cases,
     contexts where G5.11 static_flow_shield was oracle or near oracle.
   Keep local scale modest.
   Avoid full server unless expanding beyond current lattice/context size.

10. Write final:
    outputs/reports/phase5p5_repair5g512_decision.md
    outputs/reports/phase5p5_repair5g512_decision_summary.json

Decision options:
  missing_g511_artifacts_stop
  candidate_regret_targets_failed
  candidate_regret_targets_passed_continue_feature_v3
  feature_v3_failed_continue_feature_design
  candidate_ranker_training_gate_failed
  candidate_ranker_failed_continue_features_or_lattice
  candidate_ranker_passed_continue_static_abstention_safety_package
  static_boundary_augmentation_needed
  local_pc_sufficient_continue_local
  server_required_for_expanded_lattice_or_more_contexts
  stop_for_protocol_or_semantic_bug

Validation:
  python -m py_compile all new/modified Python scripts
  JSON summaries parse
  CSV row-count sanity
  reserved-ID guard rejects 166
  git diff --check
  If C++ changed, run scripts/build_phase1a_batch.ps1
  Leave unrelated dirty/untracked files untouched
  Commit and push only G5.12-related tracked files/reports

Commit message:
  repair5g: redesign lattice targets as regret ranking
```

---

## 7. Final interpretation for the project

G5.11 是项目路线中的重要正结果：

```text
粗糙 additive LTM:
  full lattice oracle beats additive in 100% of contexts.

static flow-shield:
  strong baseline, but full lattice oracle beats static in 86.67% contexts.

goal-aware dual-channel parameter lattice:
  oracle upper bound strongly improves over G5.8 and static/additive.

learning problem:
  not solved yet, because old target design is too coarse and too class-imbalanced.
```

所以 G5.12 不应再问“selector 有没有用”，而应问：

```text
Can we learn to score bounded dual-channel UpdateLTM parameter candidates by predicted regret/risk from runtime-safe context features?
```

这才是从 selector 真正转向 learned dual-channel LTM parameter policy 的关键一步。

---

## 8. 发布检查

这份 G5.12 handoff 的边界如下：

```text
claim_allowed:
  G5.11 full lattice candidate-space result is positive.
  G5.11 target failure is a label-design blocker, not a parameter-lattice blocker.
  G5.12 should redesign labels at candidate-level regret/ranking/risk granularity.

claim_not_allowed:
  phase5p5_allowed = false
  phase6_allowed = false
  aaai_ready = false
  runtime_claim_allowed = false
  learned_runtime_policy_validated = false

implementation_boundary:
  do not modify external/lacam2/lacam2/**
  do not change PIBT or LaCAM* search semantics
  do not run or inspect IDs 166..205
  keep static/abstention deployment safety separate from offline candidate-ranking diagnostics
```

Commit scope should remain this completed prompt/analysis file unless the next Codex run actually implements the G5.12 scripts and reports.
