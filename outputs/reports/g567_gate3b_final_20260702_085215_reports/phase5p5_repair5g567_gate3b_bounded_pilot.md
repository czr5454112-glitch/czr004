# Repair5G.5.67 Gate-3B Bounded Pilot

- decision: `gate3b_research_signal_failed`
- source HEAD: `4b786766da4625b315c281c1b89e7ffd6cbfa591`
- label train contexts: `2000`
- calibration contexts: `500`
- development contexts: `500`
- total solver rows: `63027`
- scientific-valid solver rows: `63003`
- hard-timeout rate: `0.0003807891855871293`
- hard-timeout rows excluded from scientific labels: `24`
- unexcluded hard-timeout rows: `0`
- crash rate: `0.0`
- label public fraction: `0.5`
- calibration public fraction: `0.7`
- development public fraction: `0.7`
- official scenario proportion: `0.35833333333333334`
- Label-v5.4 safe/positive/harmful: `52503` / `3447` / `8906`
- critic decision: `g567_distributional_critic_not_calibrated`
- critic used for actor training: `False`
- actor GPU-active hours: `4.0000057585581414`
- actor seed count: `2`
- primary actor decision: `g567_one_primary_actor_selected`
- research signal: `gate3b_research_signal_failed`
- full campaign launched: `False`
- final blind accessed: `False`

Gate-3B is a bounded pilot only. It does not authorize the full campaign or final blind replay.
