# Phase5.5 Repair5E.4 Provenance Audit

- git_head_sha: `48b5c6da438376f99c207a1deebc0d3dd0efdc1a`
- git_branch: `phase4f5p5-stable-attention-lau`
- tracked_dirty_files_count: `11`
- untracked_files_count: `385`
- clean_tracked_worktree: `False`
- runtime_manifest_sha256: `515e52edc7f1bdc4ba85724381c9a83f6c11916153eb503dd6901a82bfac7a17`
- runtime_artifact_dir: `artifacts\models\laur_ltm\repair5e4_closed_loop_utility_selector`

## Tracked Dirty Files

- `M cpp/ntm/laur_ltm_runtime.cpp`
- ` M cpp/ntm/laur_ltm_runtime.hpp`
- ` M cpp/tools/phase1a_batch.cpp`
- ` M scripts/run_phase5p5_laur_diagnostic_preflight_exec.py`
- ` M src/czr004_teacher/stable_attention_dataset_laur.py`
- ` M src/czr004_teacher/stable_attention_tokens_laur.py`
- ` M src/eval/eval_laur_stable_attention.py`
- ` M src/train/train_laur_stable_attention.py`
- ` M tests/test_phase4f_stable_attention_dataset.py`
- ` M tests/test_phase4f_stable_attention_eval.py`
- ` M tests/test_repair5e_composite_preflight.py`

## Inputs

- train_support_log_paths: `['outputs\\logs\\phase5p5_repair5e4_train_support\\phase5p5_repair5e4_train_support.jsonl', 'outputs\\logs\\phase5p5_repair5e4_train_support\\phase5p5_repair5e4_train_support_commands.jsonl', 'outputs\\logs\\phase5p5_repair5e4_train_support\\phase5p5_repair5e4_train_support_laur_updates.jsonl']`
- eval_log_paths: `['outputs\\logs\\phase5p5_repair5e4_preflight\\phase5p5_repair5e4_preflight.jsonl', 'outputs\\logs\\phase5p5_repair5e4_preflight\\phase5p5_repair5e4_preflight_laur_updates.jsonl']`
- forbidden_eval_support_paths: `['outputs\\logs\\phase5p5_repair5e4_preflight\\phase5p5_repair5e4_preflight.jsonl', 'outputs\\logs\\phase5p5_repair5e4_preflight\\phase5p5_repair5e4_preflight_laur_updates.jsonl']`

## Script Hashes

{
  "scripts/audit_repair5e4_provenance.py": "d06bd91d01ff3239a62263f10acbe2efb3dc4bbf92fae0ddfa5c03ba09a14ff7",
  "scripts/audit_repair5e4_runtime_feature_stats.py": "6c2d941ebb1d8525596c26fe4d660188ca4f94ff293e5157575aae8bd5f987e7",
  "scripts/create_repair5e4_closed_loop_utility_selector_runtime.py": "3c8de802fe4c8318c693b49004f56b33111daa28c27e5eed6d7a342e936a359c",
  "scripts/create_repair5e4_closed_loop_utility_table.py": "0bcbe55a0f183d4f9c832abb8b60f91dfb2fbc9c8d4cdc093e7f566726405ebc",
  "scripts/create_repair5e4_runtime_feature_stats_from_train_support.py": "daf8fb4d94fcdb565207ca49961769ce8d76d6cec17ad483005eb283887c37bf",
  "scripts/run_phase5p5_laur_diagnostic_preflight_exec.py": "9b50b9f76eb92e3b8e73486fda91f1e039d0f1dc1c6d1ae9f580eef2304e7f87"
}
