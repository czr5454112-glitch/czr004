# Phase5.5 Repair5E.5 Cross-Fold Utility Tables

- diagnostic_only: `true`
- phase5p5_allowed: `false`
- phase6_allowed: `false`
- wide_rows: `2100`
- long_rows: `16800`
- positive_labels_only_random_map: `False`
- positive_label_maps: `['maze-32-32-4', 'random-32-32-20']`

## Stable Positives By Rule

{
  "block_heavy": 960,
  "block_light": 320,
  "decay_090": 160,
  "decay_095": 160,
  "wait_heavy": 640,
  "wait_light": 160
}

## False-Positive Risk By Rule

{
  "block_heavy": 0.42095238095238097,
  "block_light": 0.45904761904761904,
  "commit_heavy": 0.5276190476190477,
  "decay_090": 0.49714285714285716,
  "decay_095": 0.5047619047619047,
  "wait_heavy": 0.3580952380952381,
  "wait_light": 0.4895238095238095
}

## Margin Histogram

{
  "(0,0.001]": 0,
  "(0.001,0.002]": 0,
  "(0.002,0.005]": 40,
  "0": 1616,
  ">0.005": 444
}
