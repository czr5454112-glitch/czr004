# Related Work Notes

This file is a lightweight reading and positioning log. It is not the final related-work section.

## Current Positioning

The project should be described as learning-enhanced traffic guidance for LaCAM*, not as end-to-end learned MAPF.

## Required Discussion Buckets

- LTM: direct upstream. NTM must show closed-loop solver benefit beyond pure teacher fitting.
- Local guidance for LaCAM-style methods: related because they alter guidance, different because this project uses PIBT trace-derived directed traffic maps.
- Guidance graph optimization / online guidance graph optimization: related because they learn or optimize graph guidance, different task loop and evaluation setting.
- Learned heuristics or edge costs in other search frameworks: related at the representation level, but not the same integration point.

## Writing Rule

Do not add extra solver families to the experimental baseline just because they are discussed here. Related work can be discussed without becoming a required main-table baseline.
