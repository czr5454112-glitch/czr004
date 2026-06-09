# Phase5.5 Repair5E.3 Leakage and Ablation Audit

- diagnostic-only: `true`
- phase5p5_allowed: `false`
- phase6_allowed: `false`
- leakage_detected: `False`
- eval paths reused in train/support metadata: `False`
- support/eval instance overlap count: `0`
- support generated after eval logs: `False`
- exact map/agent recovery table used: `True`

## Ablation Checks

{
  "disabled_stats": {
    "better": 0,
    "equal": 60,
    "mean_delta_ratio_vs_ltm": 0.0,
    "rows": 60,
    "worse": 0
  },
  "guarded_stats": {
    "better": 7,
    "equal": 41,
    "mean_delta_ratio_vs_ltm": 0.001572602467666669,
    "rows": 60,
    "worse": 12
  },
  "recovery_disabled_parity_exact": true,
  "shuffled_stats": {
    "better": 0,
    "equal": 60,
    "mean_delta_ratio_vs_ltm": 0.0,
    "rows": 60,
    "worse": 0
  },
  "shuffled_support_not_better_than_guarded": false
}

## Rule Support By Context

| map | agents | rule | support | better/equal/worse | source |
|---|---:|---|---:|---:|---|
| maze-32-32-4 | 100.0 | block_light | 3 | 3/0/0 | repair5e_caseb_oracle_static_support |
| random-32-32-20 | 50.0 | block_light | 3 | 0/3/0 | repair5e_caseb_oracle_static_support |
| random-32-32-20 | 100.0 | decay_095 | 3 | 3/0/0 | repair5e_caseb_oracle_static_support |
| warehouse-10-20-10-2-1 | 50.0 | block_light | 3 | 0/3/0 | repair5e_caseb_oracle_static_support |
| warehouse-10-20-10-2-1 | 100.0 | block_light | 3 | 0/3/0 | repair5e_caseb_oracle_static_support |
