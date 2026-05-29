# Repair5 GPTPro Review Manifest - 2026-05-29

This package is for external review of the Phase4F Repair5 attention-native LAUR work. It is evidence for diagnosis and iteration, not a Phase5.5 or Phase6 promotion claim.

## Current Gate State

- Layered diagnostic summary: `outputs/reports/phase4f_repair5_layered_gate_summary.json`
- Layered diagnostic report: `outputs/reports/phase4f_repair5_layered_gate_report.md`
- Evaluated summaries: `27`
- Development pass: `0`
- Promotion-candidate pass: `0`
- Strict seed-gate pass: `0`
- Phase5.5 allowed by this evidence: `False`
- Phase6 allowed by this evidence: `False`

## Included In Git

- Repair5 attention-native label/model/train/eval/test code:
  - `src/czr004_teacher/attention_native_labels_laur.py`
  - `src/czr004_teacher/attention_native_schema_laur.py`
  - `src/czr004_teacher/attention_native_union_laur.py`
  - `src/models/laur_attention_native.py`
  - `src/train/losses_laur_attention_native.py`
  - `src/train/train_laur_attention_native.py`
  - `src/eval/eval_laur_attention_native.py`
  - `src/eval/eval_laur_anti_escape.py`
  - `src/eval/eval_laur_repair5_final_gate.py`
  - `src/eval/eval_laur_repair5_layered_gate.py`
  - `tests/test_phase4f_attention_native_labels.py`
  - `tests/test_phase4f_attention_native_eval.py`
- Repair5 configs and remote runner scripts:
  - `configs/phase4/generated_repair5*/`
  - `configs/phase4/laur_ltm_full_repair5*.yaml`
  - `configs/phase4/laur_ltm_repair5_expand5000_scenario_manifest.jsonl`
  - `run_repair5_expand5000*.sh`
- Planning and worklog documents:
  - `phase4_6_laur_ltm_codex_execution_plan.md`
  - `phase4f_repair5_attention_native_labels_codex_plan.md`
  - `deep-research-report.md`
  - `docs/codex-worklog.md`
- Repair5 evidence:
  - `outputs/reports/phase4f_repair5*`
  - `outputs/reports/phase4_laur_ltm_full_repair5*`
  - `outputs/reports/phase4_laur_repair5_expand5000*`
  - `outputs/tables/phase4f_repair5*.csv`
  - compact expand5000 checkpoint/probe JSONL files
  - compressed attention-native expand5000 label datasets

## New Data Pulled From Server

| artifact | bytes | sha256 |
|---|---:|---|
| `artifacts/teacher/laur/full_repair5_expand5000/checkpoints/phase4_laur_checkpoints_full_repair5_expand5000.jsonl` | `18360479` | `6c1956b2daef8dfcb91cff9df07f13e3ef7aca656955852bd989072450a45288` |
| `artifacts/teacher/laur/full_repair5_expand5000/probes/phase4_laur_probe_full_repair5_expand5000.jsonl` | `49191041` | `9495e2a823319034518e95f856de11e1ea1d1bcb00aae40fc69ff529fedaad34` |
| `artifacts/teacher/laur/full_repair5_attention_native_expand5000_rawtrace/update_labels/phase4_laur_attention_native_expand5000_rawtrace_dataset.jsonl.zst` | `13185817` | `2b9d5a7aafea85a5347efaf574ecc58489b4939400cb602040fc03f880ed36bb` |
| `artifacts/teacher/laur/full_repair5_attention_native_expand5000_rawtrace_hightoken/update_labels/phase4_laur_attention_native_expand5000_rawtrace_hightoken_dataset.jsonl.zst` | `22890136` | `889907079b8b8fa9f04c0abec2b98f2675bd265719e9143e267f604f04a6e2d1` |

The two compressed attention-native datasets have `sample_count=4956`, `train=4194`, `validation=762`, `use_nonadditive=3274`, `defer_ltm=1682`, and `high_margin_nonadditive_opportunity_count=2325` according to their label-audit reports.

## Local Only

The raw trace requested by the user has been pulled back locally, but it is intentionally not committed as a normal GitHub blob because it is 5.7GB.

| artifact | bytes | sha256 |
|---|---:|---|
| `artifacts/teacher/laur/full_repair5_expand5000/traces/phase4_laur_trace_full_repair5_expand5000.jsonl.zst` | `6077128911` | `340442990519875112c0696141b281ebcfaa1ff75da3890d516edb41b4b2b2fc` |

The `.gitignore` now protects this trace path and the uncompressed attention-native JSONL label files. The compressed label datasets above are small enough to commit and review directly.

## Review Notes

- Repair5 primary label remains attention-native: risk-adjusted utility, pairwise dominance, safe non-additive opportunity, `defer_ltm`, and anti-escape masks.
- Repair3/Phase5C MLP remains only a conservative baseline and compatibility/fallback reference.
- No gate was lowered for runtime or paper claims.
- Negative results are preserved: the current layered diagnostic has no development, candidate, or strict seed pass.
