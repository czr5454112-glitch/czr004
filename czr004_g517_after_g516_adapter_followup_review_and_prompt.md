# czr004 G5.16 复盘与 G5.17 深度推进 Prompt

生成日期：2026-06-08  
基准提交：`2834f02 repair5g: add pessimistic safety-bound ranker diagnostics`  
建议下一轮：`Repair5G.5.17 Adapter-Recognized Targeted Repair Lattice Probe + Candidate-Space Reassessment`

---

## 0. 一句话结论

G5.16 不是坏结果，也不是 `goal_aware_dual_channel_ltm` 方向失败。它暴露的是一个很具体的工程 blocker：

```text
G5.16 已经设计出 10 个 targeted update-only repair candidates，
但这些 repair5g516_* candidate names 当前没有被 cpp/tools/phase1a_batch.cpp 的 repair5g_method_spec 识别，
所以 solver probe 被正确跳过。
```

因此 G5.16 的 final decision：

```text
targeted_repair_lattice_requires_adapter_followup
```

是正确的 stop，而不是实验方向失败。

与此同时，G5.16 的 table-only pessimistic safety-bound ranker 也给出重要负结果：

```text
balanced_bound:
  false_positive_count = 0
  harmful_vs_static_rate = 0
  coverage = 0
  missed_helpful_count = 52
```

这说明当前安全门控可以把 harmful false positives 压到 0，但代价是完全退回 static，错过了几乎所有有价值机会。下一步不能只继续调 threshold；必须让 targeted repair candidates 真正可执行，拿到新的 counterfactual evidence，再判断 lattice 是否能同时降低 risk 和保留 opportunity。

---

## 1. G5.16 到底好在哪里？

### 1.1 它完成了 G5.15 后最该做的 error-driven pipeline

G5.16 按计划做了：

```text
G5.15 artifacts verify
-> error bank
-> targeted repair lattice design
-> local targeted probe plan
-> adapter recognition gate
-> table-only augmented v6
-> pessimistic safety-bound ranker
-> error autopsy / safety update
-> final decision
```

这不是 prompt-only，也不是空跑。

### 1.2 Error bank 是有价值的

G5.16 error bank 把当前问题分解成可操作类别：

```text
harmful_false_positive = 3
missed_helpful_fallback = 39
high_uncertainty = 37
static_near_oracle = 8
oracle_gap_high = 20
candidate_disagreement = 21
```

这说明当前 blocker 不是“没有信号”，而是信号太难安全利用。尤其是 missed helpful 和 high uncertainty 很多，证明单纯保守 fallback 会浪费大量 oracle opportunity。

### 1.3 Targeted repair lattice 方向是对的

G5.16 设计了 10 个 update-only repair candidates，覆盖四个 families：

```text
safer_slow_decay
wait_neighborhood
commit_neighborhood
conservative_static_boundary
```

它们正好对应 G5.15/G5.16 的错误模式：

```text
harmful false positives:
  slow_decay 太强，shield beta / cap / decay 需要收敛

missed helpful fallbacks:
  wait-heavy 或 commit-heavy contexts 可能需要更精细 candidate

static-near-oracle:
  需要 minimal nonstatic boundary candidates 来学习 abstention boundary
```

这比继续在旧 14-candidate lattice 上调 ranker 更接近项目目标。

---

## 2. G5.16 为什么没有过？

### 2.1 主失败：C++ adapter 不认识 repair5g516_* names

G5.16 target lattice summary 明确显示：

```text
new_candidate_count = 10
executable_candidate_count = 0
current_cpp_adapter_recognizes_all = false
decision = targeted_repair_lattice_requires_adapter_followup
```

所以 local targeted probe plan 虽然满足：

```text
target_contexts = 20
candidate_count = 24
budgets = 1000, 2000
estimated_rows = 960
max_workers = 1
ids_166_205_untouched = true
```

但 `candidate_methods_executable=false`，probe 必须跳过。这是正确行为，不能硬跑。

### 2.2 次失败：pessimistic ranker 太保守

G5.16 的 `balanced_bound` primary policy 是：

```text
coverage = 0.0
fallback_rate = 1.0
false_positive_count = 0
harmful_vs_static_rate = 0.0
mean_delta_vs_static = 0.0
missed_helpful_count = 52
```

这说明 pessimistic bound 现在是安全但没有收益。它没有学成“安全地选择参数”，只是学会了“全部 abstain”。

### 2.3 Table-only v6 没有新 evidence

因为 targeted probe 没跑，`augmented_candidate_targets` 还是 840 rows，仅来自 existing v5，没有新增 repair candidates 的 outcomes。也就是说，v6 只能在旧 candidate outcomes 上做更保守的 gate，不可能证明新 repair lattice 能解决问题。

---

## 3. 方向有没有问题？

没有。

项目核心目标仍然是：

```text
用 learning-enhanced UpdateLTM 替换 LTM 论文中的粗糙 additive update，
最终在 closed-loop solver metrics 上超过 plain additive LTM，
且不改 LaCAM*/PIBT 搜索语义。
```

到目前为止的证据链是：

```text
G5.11:
  14-candidate bounded dual-channel lattice oracle 强过 additive/static。

G5.12:
  candidate-level regret/ranking target 能训练出低 harmful offline ranker。

G5.13:
  hard controls 发现 G5.12 主要是 safe-gated slow_decay/simple prior。

G5.14:
  rich trace features 恢复成功，但 context-only rich features 不够。

G5.15:
  rich × candidate interactions 和 pairwise ranking 更安全，但 RAU 没赢 v4。

G5.16:
  error-driven safety bound 可消灭 false positives，但过度保守；
  targeted repair lattice 设计出来了，但还没被 C++ adapter 执行验证。
```

所以当前不是“学习增强 UpdateLTM 失败”，而是推进到下一个必须解决的工程/实验关口：

```text
让 targeted repair lattice 变成 executable candidate space，
再用 same-context counterfactual probe 检查它是否真的改善 error-bank oracle/risk tradeoff。
```

---

## 4. G5.17 应该做什么？

G5.17 不应该再只做 table-only ranker。下一轮要做一个更长、更深、更接近项目目标的执行包：

```text
Repair5G.5.17:
  Adapter-Recognized Targeted Repair Lattice Probe
  + Candidate-Space Oracle Reassessment
  + Controlled Ranker Refit
  + Safety Boundary Update
```

核心是先让 G5.16 targeted candidates 可执行，然后在 observed-ID/error-bank 上跑 small local probe。

---

## 5. 给 Codex 的完整执行 Prompt

下面这段可直接发给 Codex。

```text
Continue czr004 on branch phase4f5p5-stable-attention-lau after commit 2834f02 repair5g: add pessimistic safety-bound ranker diagnostics.

Implement Repair5G.5.17: adapter-recognized targeted repair lattice probe + candidate-space reassessment + controlled ranker refit.

This must be a real execution round, not a prompt-only commit.

Main interpretation to preserve:
- G5.16 is not a direction failure.
- G5.16 correctly stopped because the 10 targeted `repair5g516_*` candidate names were not recognized by the current C++ adapter.
- G5.16 table diagnostics showed pessimistic bounds can eliminate false positives but are too conservative: balanced_bound coverage=0, false_positive_count=0, missed_helpful_count=52.
- The next useful step is to make the targeted repair candidate lattice executable in the project-owned adapter and run a small observed-ID local counterfactual probe.
- Runtime / Phase5.5 / Phase6 / AAAI claims remain closed.

Project objective:
Use learning-enhanced UpdateLTM to replace the coarse additive update in the LTM paper and eventually beat LaCAM*+plain additive LTM under closed-loop solver metrics, without changing LaCAM*/PIBT semantics.

Hard constraints:
- Do not modify `external/lacam2/lacam2/**`.
- Do not change PIBT, LaCAM*, candidate generation, conflicts, pruning, OPEN/EXPLORED, rewrite, incumbent, or restart semantics.
- Do not introduce action prediction, priority prediction, learned restart, h-values, candidate deletion, MAPF action logits, or learned solver control.
- Do not run or inspect IDs `166..205`.
- Do not claim runtime learned policy, Phase5.5, Phase6, or AAAI-ready.
- Default to local PC execution.
- Use `--max-workers 1` for any solver/probe command.
- Use isolated G5.17 output paths. Do not append multiple workers into a shared JSONL.
- Leave unrelated dirty/untracked files untouched.
- Commit only G5.17 files.

Read first:
  outputs/reports/phase5p5_repair5g516_decision.md
  outputs/reports/phase5p5_repair5g516_decision_summary.json
  outputs/reports/phase5p5_repair5g516_error_bank_summary.json
  outputs/reports/phase5p5_repair5g516_targeted_repair_lattice_summary.json
  outputs/reports/phase5p5_repair5g516_local_targeted_probe_plan_summary.json
  outputs/reports/phase5p5_repair5g516_targeted_probe_run_summary.json
  outputs/reports/phase5p5_repair5g516_pessimistic_rankers_summary.json
  outputs/tables/phase5p5_repair5g516_targeted_repair_lattice.csv
  outputs/tables/phase5p5_repair5g516_local_targeted_probe_plan.csv
  cpp/tools/phase1a_batch.cpp
  scripts/run_repair5g510_goal_aware_dual_channel_lattice_counterfactuals.py
  scripts/create_repair5g516_targeted_repair_lattice.py
  scripts/plan_repair5g516_local_targeted_probe.py

Stage 0 — write plan and worklog:
1. Add:
   `czr004_repair5g517_adapter_recognized_targeted_lattice_probe_plan.md`
   and update `docs/codex-worklog.md`.
2. Write:
   `outputs/reports/phase5p5_repair5g516_final_interpretation.md`
   explaining that G5.16 stopped at adapter-recognition gate, not due to LAU/LTM direction failure.

Stage 1 — adapter recognition, minimal and audited:
3. Add project-owned adapter recognition for the exact 10 `repair5g516_*` candidates in `cpp/tools/phase1a_batch.cpp`.
   Use the existing `repair5g_method_spec` / `set_g510_lattice(...)` pattern already used for `repair5g59_*`.
   Do not modify any external solver code.
   Do not modify LaCAM*/PIBT semantics.
   Do not touch candidate generation, conflict logic, OPEN/EXPLORED, pruning, rewrite, incumbent, or restart.
4. Add a clear comment block marking this as:
   `Repair5G.5.17 targeted update-parameter adapter recognition only`.
5. Candidate mappings must exactly match `outputs/tables/phase5p5_repair5g516_targeted_repair_lattice.csv`:

   repair5g516_slow_decay_safer_beta025_cap050:
     alpha_cong_committed=1.25, alpha_cong_blocked=1.25,
     alpha_flow_progress=1.00, alpha_flow_wait_or_nonprogress=0.75,
     rho_cong=0.92, rho_flow=1.00, flow_shield_beta=0.25, max_flow_shield=0.50, c_only=false

   repair5g516_slow_decay_safer_beta020_cap045:
     alpha_cong_committed=1.20, alpha_cong_blocked=1.20,
     alpha_flow_progress=1.00, alpha_flow_wait_or_nonprogress=0.75,
     rho_cong=0.90, rho_flow=1.00, flow_shield_beta=0.20, max_flow_shield=0.45, c_only=false

   repair5g516_slow_decay_safer_beta015_cap040:
     alpha_cong_committed=1.15, alpha_cong_blocked=1.15,
     alpha_flow_progress=1.00, alpha_flow_wait_or_nonprogress=0.75,
     rho_cong=0.88, rho_flow=1.00, flow_shield_beta=0.15, max_flow_shield=0.40, c_only=false

   repair5g516_wait_aggressive_low_cap:
     alpha_cong_committed=1.00, alpha_cong_blocked=1.00,
     alpha_flow_progress=1.05, alpha_flow_wait_or_nonprogress=1.25,
     rho_cong=0.95, rho_flow=0.95, flow_shield_beta=0.20, max_flow_shield=0.50, c_only=false

   repair5g516_wait_conservative_mid_cap:
     alpha_cong_committed=1.00, alpha_cong_blocked=1.00,
     alpha_flow_progress=1.00, alpha_flow_wait_or_nonprogress=1.05,
     rho_cong=0.95, rho_flow=0.98, flow_shield_beta=0.18, max_flow_shield=0.45, c_only=false

   repair5g516_wait_aggressive_fast_flow_decay:
     alpha_cong_committed=1.00, alpha_cong_blocked=1.00,
     alpha_flow_progress=1.10, alpha_flow_wait_or_nonprogress=1.30,
     rho_cong=0.95, rho_flow=0.90, flow_shield_beta=0.18, max_flow_shield=0.45, c_only=false

   repair5g516_commit_heavy_low_beta:
     alpha_cong_committed=1.45, alpha_cong_blocked=0.90,
     alpha_flow_progress=1.10, alpha_flow_wait_or_nonprogress=0.80,
     rho_cong=0.95, rho_flow=1.00, flow_shield_beta=0.18, max_flow_shield=0.45, c_only=false

   repair5g516_commit_heavy_static_guard:
     alpha_cong_committed=1.35, alpha_cong_blocked=0.90,
     alpha_flow_progress=1.05, alpha_flow_wait_or_nonprogress=0.75,
     rho_cong=0.92, rho_flow=0.98, flow_shield_beta=0.15, max_flow_shield=0.35, c_only=false

   repair5g516_static_boundary_light_flow:
     alpha_cong_committed=1.00, alpha_cong_blocked=1.00,
     alpha_flow_progress=1.00, alpha_flow_wait_or_nonprogress=0.90,
     rho_cong=0.95, rho_flow=1.00, flow_shield_beta=0.10, max_flow_shield=0.25, c_only=false

   repair5g516_static_boundary_c_only:
     alpha_cong_committed=1.05, alpha_cong_blocked=1.05,
     alpha_flow_progress=1.00, alpha_flow_wait_or_nonprogress=0.75,
     rho_cong=0.95, rho_flow=1.00, flow_shield_beta=0.00, max_flow_shield=0.00, c_only=true

6. Add script:
   `scripts/verify_repair5g517_adapter_recognition.py`
   It must:
   - parse `cpp/tools/phase1a_batch.cpp`,
   - verify every `repair5g516_*` candidate appears in adapter recognition,
   - verify every candidate in the G5.16 lattice CSV has an exact parameter tuple mapping recorded in a summary,
   - report `adapter_recognition_passed_continue_local_probe` only if all 10 are recognized.
7. If adapter recognition fails or build fails, stop with:
   `adapter_recognition_failed_no_solver_run`
   and do not run solver.

Stage 2 — build and lightweight adapter smoke:
8. If C++ changed, run the project build for `phase1a_batch`.
9. Add:
   `scripts/run_repair5g517_adapter_smoke.py`
   This should run a minimal observed-ID smoke over one safe context and all 10 repair candidates, or use the existing counterfactual runner with a tiny context limit, to prove:
   - candidate_recognized=true for all repair candidates,
   - updateparams fingerprint exists,
   - no external/lacam2 files modified,
   - IDs 166..205 untouched.
10. If smoke fails, stop with:
    `adapter_smoke_failed_no_targeted_probe`.

Stage 3 — local targeted probe, only after adapter gate:
11. Reuse or extend G5.16 plan to run:
    - target contexts: <=20, selected from error bank;
    - candidates: existing 14 + new 10 = 24;
    - budgets: 1000 and 2000 only;
    - max_workers=1;
    - observed IDs only;
    - no IDs 166..205;
    - local output paths under `outputs/logs/phase5p5_repair5g517_*`.
12. Expected scale:
    `20 contexts x 24 candidates x 2 budgets = 960 probe rows`.
13. Write:
    `outputs/reports/phase5p5_repair5g517_targeted_probe_integrity.md`
    `outputs/reports/phase5p5_repair5g517_targeted_probe_integrity_summary.json`
    with gates:
    - probe_ran=true
    - rows_eq_960 or exact documented equivalent
    - contexts_eq_target_count
    - candidates_eq_24
    - repair_candidates_eq_10
    - candidate_recognized_all=true
    - duplicate_context_candidate_budget_rows_eq_0
    - ids_166_205_untouched=true
    - observed_ids_only=true

Stage 4 — candidate-space reassessment:
14. Add:
    `scripts/analyze_repair5g517_targeted_lattice_oracle.py`
15. Compare on targeted contexts:
    - old 14-candidate oracle
    - new 24-candidate oracle
    - static
    - additive
    - fixed slow_decay_high_shield
    - G5.15/G5.16 table policies where comparable
16. Required outputs:
    `outputs/reports/phase5p5_repair5g517_targeted_lattice_oracle.md`
    `outputs/reports/phase5p5_repair5g517_targeted_lattice_oracle_summary.json`
    `outputs/tables/phase5p5_repair5g517_targeted_lattice_oracle_by_context.csv`
    `outputs/tables/phase5p5_repair5g517_targeted_candidate_distribution.csv`
17. Gates:
    - new_repair_candidate_win_count > 0 OR explicitly report no candidate-space gain;
    - mean_new_oracle_gap_vs_old_oracle < 0 for pass;
    - harmful_false_positive_target_contexts_improved > 0 for pass;
    - static_boundary_contexts_no_worse reported;
    - additive remains weak reported.
18. If there is no oracle/candidate-space gain, stop with:
    `targeted_repair_lattice_no_oracle_gain_continue_lattice_design`
    and do not pretend a learned policy can improve.

Stage 5 — conditional full 60-context primary local expansion:
19. If and only if Stage 4 passes candidate-space gate, run a full primary-bank local expansion:
    - 60 contexts
    - 24 candidates
    - budgets 1000 and 2000 only
    - max_workers=1
    - expected 2880 probe rows
20. This is still local PC scale; do not use server unless the run exceeds local capacity.
21. Write full-bank integrity and oracle summaries:
    `phase5p5_repair5g517_full_primary_24cand_integrity_summary.json`
    `phase5p5_repair5g517_full_primary_24cand_oracle_summary.json`
22. If full expansion is not run, write why.

Stage 6 — ranker refit only after new outcomes exist:
23. If targeted or full new outcomes exist, build:
    `phase5p5_repair5g517_candidate_regret_targets.csv`
    `phase5p5_repair5g517_candidate_feature_matrix_v7.csv`
24. Include:
    - old 14 candidates;
    - repair 10 candidates where measured;
    - rich trace features;
    - rich x candidate interactions;
    - error-bank category features;
    - candidate family flags;
    - no oracle/probe/outcome/target leakage in `feature_*`.
25. Train/evaluate:
    - pairwise_context_ranker_v7
    - two_stage_safety_ranker_v7
    - pessimistic_bound_ranker_v7
    - family-aware candidate gate
    - static-first abstention gate
26. Use:
    - seed OOF
    - leave-one-map-agent-group-out
    - fixed 146..150 train / 151..155 dev
    - bootstrap CIs
    - calibration buckets
    - false-positive autopsy
    - missed-opportunity autopsy
27. Required controls:
    - static_flow_shield
    - additive_ltm
    - fixed slow_decay_high_shield
    - best old policy from G5.15/G5.16
    - safe train-only map-agent gate
    - candidate-param-only
    - no-repair-candidate ablation
    - repair-family-only ablation
    - shuffled repair interactions
    - random feature
    - shuffled label
    - oracle upper bound
28. Policy success gates:
    - harmful_vs_static_rate <= 0.033
    - false_positive_count <= G5.15 and <= G5.16 no-bound ablation
    - missed_helpful_count decreases vs G5.16 balanced_bound by a meaningful amount
    - RAU lambda 0.05 and 0.10 beats G5.15 pairwise and G5.16 best table policy
    - beats safe_slow_decay_train_gate
    - beats safe_train_only_map_agent_gate on RAU lambda 0.10
    - calibration reported
    - no IDs 166..205
    - runtime_claim_allowed=false
29. Even if all offline gates pass, do not claim runtime policy. Decision may be:
    `targeted_repair_v7_offline_passed_continue_safety_package`
    but Phase5.5 remains closed.

Stage 7 — safety package update:
30. Update:
    `outputs/reports/phase5p5_repair5g517_static_abstention_safety_update.md`
    `outputs/reports/phase5p5_repair5g517_static_abstention_safety_update_summary.json`
31. Must report:
    - static-near-oracle contexts
    - static wins
    - no-solution/infeasible coverage
    - budget-sensitive coverage
    - OOD-like holdout coverage
    - high uncertainty contexts
    - harmful false positives
    - abstention reasons
32. Runtime / Phase5.5 remains closed unless a later safety package covers no-solution, budget-sensitive, OOD, static, and abstention cases.

Stage 8 — final decision:
33. Write:
    `outputs/reports/phase5p5_repair5g517_decision.md`
    `outputs/reports/phase5p5_repair5g517_decision_summary.json`
34. Decision options:
    - `adapter_recognition_failed_no_solver_run`
    - `adapter_smoke_failed_no_targeted_probe`
    - `targeted_probe_integrity_failed`
    - `targeted_repair_lattice_no_oracle_gain_continue_lattice_design`
    - `targeted_repair_lattice_oracle_improved_continue_full_primary`
    - `full_primary_24cand_oracle_failed_continue_lattice_design`
    - `full_primary_24cand_oracle_improved_continue_ranker`
    - `targeted_repair_v7_ranker_failed_continue_feature_design`
    - `targeted_repair_v7_offline_passed_continue_safety_package`
    - `server_required_for_expanded_lattice_or_more_contexts`
    - `stop_for_semantic_or_protocol_bug`

Validation:
- `python -m py_compile` for all new/modified Python scripts.
- If C++ changed, build phase1a_batch.
- Adapter recognition verification.
- Adapter smoke.
- JSON summaries parse.
- CSV row-count sanity.
- reserved-ID guard rejects 166.
- candidate_recognized_all true before any probe result is accepted.
- leakage scanner reports forbidden_feature_count=0 for feature matrices.
- grouped context sanity.
- git diff --check.
- Commit and push only G5.17-related changes.

Commit message:
  repair5g: execute targeted repair lattice adapter probe
```

---

## 6. 为什么 G5.17 这样安排？

因为 G5.16 已经证明：

```text
只做更保守的 safety bound = 0 false positives, 0 coverage。
只做 table-only feature design = 没有新 candidate evidence。
新 repair candidates 没进 C++ adapter = 没法验证 lattice 是否真的更好。
```

所以 G5.17 的第一关键不是再训练模型，而是：

```text
让 repair candidates 可执行；
跑一个小规模 local same-context counterfactual；
验证 candidate-space 是否真的改善。
```

如果 10 个 repair candidates 连 oracle 都不能改善，就说明这批 lattice repair 设计不够好，应继续 lattice design。  
如果 oracle 改善，再训练 learned ranker 才有意义。

---

## 7. 本地/服务器分工

G5.17 仍应本地优先：

```text
adapter recognition: local
build/smoke: local
20-context targeted probe, 960 rows: local
conditional 60-context primary 24-candidate run, 2880 rows: local if machine can handle it
server: only for much larger context bank / larger candidate lattice / more budgets / later closed-loop smoke
```

继续默认：

```text
max_workers = 1
isolated output paths
no shared concurrent JSONL append
```

---

## 8. Claim boundary

Allowed after G5.17 if successful:

```text
targeted repair candidate-space diagnostic improved on observed IDs
candidate-level offline ranker improved on observed IDs
local PC sufficient for current scale
```

Still not allowed:

```text
runtime learned policy validated
Phase5.5 allowed
Phase6 allowed
AAAI-ready
closed-loop learned policy claim
fresh ID claim
```
