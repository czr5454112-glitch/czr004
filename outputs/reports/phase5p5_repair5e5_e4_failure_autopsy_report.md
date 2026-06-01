# Phase5.5 Repair5E.5 E4 Failure Autopsy

- diagnostic_only: `true`
- phase5p5_allowed: `false`
- phase6_allowed: `false`
- e4_cases: `60`
- false_positive_contexts: `4`
- false_negative_oracle_contexts: `19`
- random-32-32-20:100 main false-positive source: `True`
- maze/warehouse false-negative contexts: `19`

## Rule Precision/Recall Proxy

{
  "block_heavy": {
    "precision_better": 0.2,
    "selected_better_cases": 2,
    "selected_cases": 10,
    "selected_worse_cases": 2,
    "train_positive_contexts": 20
  },
  "decay_090": {
    "precision_better": 0.1,
    "selected_better_cases": 1,
    "selected_cases": 10,
    "selected_worse_cases": 2,
    "train_positive_contexts": 4
  }
}

## Margin Vs Realized Delta

{
  "buckets": {
    "0": {
      "better": 0,
      "mean_realized_delta_ratio": 0.0,
      "rows": 40,
      "worse": 0
    },
    ">0.005": {
      "better": 3,
      "mean_realized_delta_ratio": -0.002474561994000013,
      "rows": 20,
      "worse": 4
    }
  },
  "rows": 60
}

## Support Count Vs Realized Delta

{
  "buckets": {
    "0": {
      "better": 0,
      "mean_realized_delta_ratio": 0.0,
      "rows": 40,
      "worse": 0
    },
    ">0.005": {
      "better": 3,
      "mean_realized_delta_ratio": -0.002474561994000013,
      "rows": 20,
      "worse": 4
    }
  },
  "rows": 60
}
