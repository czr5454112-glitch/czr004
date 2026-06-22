# Repair5G.5.67 Gate-2 Bounded Pilot

- decision: `gate2_bounded_pilot_pass`
- generated contexts: `76`
- selected contexts: `2`
- requested agent tiers: `[2000, 3000]`
- selected budgets ms: `[8000, 20000]`
- selected map families: `{'large_maze': 1, 'large_room': 1}`
- blind split constructed: `False`
- replay planned rows: `8`
- replay exact materialization rate: `1.0`
- A5 BF16 elapsed sec: `25.7799653429538`
- A5 BF16 CUDA peak bytes: `8386809856`

This pilot intentionally does not build or access a final blind panel, does not launch 100k context generation, does not acquire million-row solver labels, and does not start a long training campaign.
