# Repair5G.5.66 Bug Log

This log records implementation or experiment issues found while completing the
G5.66 valid-tail three-tier direct-actor run. Each entry is kept factual so the
final report can distinguish fixed bugs from remaining blockers.

## 2026-06-22 Local Implementation Review

- Fixed: `src/gcst/three_tier_baselines.py` initially emitted baseline registry
  rows without a `candidate_id`. The solver counterfactual registry is keyed by
  candidate ID, so Tier B/Tier C rows could have been present in the human
  registry but not resolvable by the solver.
- Fixed: `scripts/run_repair5g566_strict_pipeline.py` initially populated the
  static-flow plan `expected_updateparams_fingerprint` with raw theta columns
  instead of the solver-facing UpdateParams fingerprint. The audit compared the
  returned fingerprint against theta columns, but the plan/report fingerprint
  itself needed to be exact.
- Fixed: the first G5.66 generator spec had only 10 declared map families, so
  the Phase 1 minimum target of 16 families was impossible no matter how many
  contexts were generated.
- Fixed: the first frozen split assigned roles by cycling sorted physical map
  hashes. Because context counts per hash are uneven, this could leave the blind
  set below the hard 1,000-context requirement at a 6,000-context target. The
  split now assigns whole physical-map hashes greedily toward context-count
  targets while preserving hash grouping.
- Fixed: the first pipeline draft inferred development and blind actors directly
  from prior G5.65 checkpoints after building Label-v5.3. That skipped the
  required G5.66 direct-actor training stage. The pipeline now trains G5.66
  C0/A0/A1/A2/A3/A4 checkpoints from Label-v5.3 candidates before development
  replay and blind checkpoint selection.
- Fixed: local 1-context integration smoke exposed that actor training returned
  only rich-actor checkpoints. A scalar-control-only smoke trained successfully
  but was reported as missing checkpoints, and the scientific development set
  also needs one scalar control. Selection now returns the best scalar control
  plus up to three rich actors.
- Fixed: the first strict pipeline wrote only a training-only distributional
  outcome ensemble summary placeholder. The plan requires a real physical-map
  cross-fitted critic before actor training. The pipeline now trains a bootstrap
  ridge OOF distributional critic, writes prediction/model-audit artifacts, and
  fail-closes if the critic is not calibrated.
- Fixed: the first actor training target used Label-v5.3 safe/positive rows
  directly without consuming conservative critic estimates. Actor target
  averaging now uses the critic's OOF regression-risk upper bounds, gain lower
  bounds, harmful-quality tail, and epistemic uncertainty as training-only
  weights while keeping exported actor checkpoints critic-free.
- Fixed: the first remote tmux launch failed before experiment execution because
  `/root/czr004` was not a complete git checkout and lacked
  `scripts/generate_repair5g561_valid_scenario_bank.py`. The deployment step now
  uploads the required Python source directories for the strict pipeline instead
  of only the new top-level G5.66 files.
- Open/non-blocking: the 5090 run directory `/root/czr004` is still not a git
  checkout, so the existing replay helper emits repeated `fatal: not a git
  repository` stderr lines while populating provenance fields. The solver rows
  still execute and the G5.66 audit checks candidate recognition, fingerprint,
  scenario hash, and identity retention; this is log noise/provenance metadata
  loss, not a replay-result blocker.

## 2026-06-22 Remote Run and Packaging Review

- Confirmed: the full RTX5090 tmux run exited with code 0. Blind replay
  materialized exactly: 1,000 contexts, 6,000 executed rows, 2,000 actor
  candidate rows, exact materialization 1.0, candidate recognition 1.0,
  scenario-hash match 1.0, and identity retention 1.0.
- Result, not a code bug: G5.66 did not pass Tier A, Tier B, or Tier C gates.
  Tier A median relative improvement versus additive LTM was 13.22%, but there
  were 12 success regressions. Tier B median relative improvement versus
  static-flow was 4.69%, but there were 30 success regressions. Tier C had 21
  success gains versus 23 regressions versus g556 and q95 harmful delta 0.263
  above the 0.05 margin. The actor has central-tendency value but is not
  tail-safe enough for promotion.
- Fixed packaging issue: three field-group-response CSVs exceeded GitHub's
  normal 100 MB object limit after being pulled back from the server. The raw
  files are kept locally, ignored by path, and matching `.csv.gz` archives are
  generated for commit so the useful data can be pushed without violating the
  remote object limit.
- Fixed: `phase5p5_repair5g566_artifact_manifest.json` was written before the
  final decision summary received its post-run fields (`elapsed_sec`,
  component decisions). That made the manifest hash for
  `phase5p5_repair5g566_final_decision_summary.json` stale even though the run
  itself completed correctly. The pipeline now refreshes the artifact manifest
  after the final summary rewrite, and the local manifest has been regenerated.
