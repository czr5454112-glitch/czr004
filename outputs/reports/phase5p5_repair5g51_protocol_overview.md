# Phase5.5 Repair5G.5.1 Protocol Overview

- scope: observed-ID runtime selector failure autopsy and safe bridge only
- observed smoke IDs: `126..165`
- fresh learned-runtime holdout: `166..205`, still blocked unless corrected selector passes smoke and is frozen
- allowed runtime output: bounded UpdateParams candidate id only
- forbidden outputs: actions, restarts, priorities, h-values, candidate deletion
- AAAI status: `aaai_ready=false`
- phase status: `phase5p5_allowed=false`, `phase6_allowed=false`
