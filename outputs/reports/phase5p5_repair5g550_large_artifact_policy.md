# G5.50 Large Artifact Policy

- Do not commit generated tables larger than 50 MB.
- Full raw plans/results are written under ignored `outputs/logs/`.
- Committed tables are summaries, previews, manifests, and compact diagnostics.
- Decision label: `large_artifact_commit_blocked_or_redirected_to_logs` applies when any raw artifact exceeds 50 MB.
