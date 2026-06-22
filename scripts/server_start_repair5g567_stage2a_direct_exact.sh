#!/usr/bin/env bash
set -u -o pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

STAGE_ROOT="${G567_STAGE_ROOT:-/root/shared-nvme/g567_stage2a_direct_exact}"
REPORT_DIR="${STAGE_ROOT}/reports"
LOG_DIR="${STAGE_ROOT}/logs"
mkdir -p "${REPORT_DIR}" "${LOG_DIR}"

RC_PATH="${REPORT_DIR}/phase5p5_repair5g567_stage2a_diagnostic_a5_runner.rc"
FINAL_SUMMARY="${REPORT_DIR}/phase5p5_repair5g567_stage2a_diagnostic_a5_runner_final_summary.json"
RUNNING_MARKER="${REPORT_DIR}/phase5p5_repair5g567_stage2a_diagnostic_a5_runner.running.json"
STDOUT_LOG="${LOG_DIR}/phase5p5_repair5g567_stage2a_diagnostic_a5_runner.stdout.log"
STDERR_LOG="${LOG_DIR}/phase5p5_repair5g567_stage2a_diagnostic_a5_runner.stderr.log"

write_json_atomic() {
  local target="$1"
  local tmp="${target}.tmp.$$"
  python - "$tmp" "$2" "$3" "$4" "$5" <<'PY'
import json
import os
import sys
import time

path, phase, rc, reason, expected_head = sys.argv[1:6]
payload = {
    "schema_version": "phase5p5_repair5g567_stage2a_runner_final_summary_v1",
    "phase": phase,
    "rc": int(rc),
    "reason": reason,
    "expected_head": expected_head,
    "head": os.popen("git rev-parse HEAD 2>/dev/null").read().strip(),
    "status_short": os.popen("git status --short 2>/dev/null").read(),
    "stage_root": os.environ.get("G567_STAGE_ROOT", ""),
    "stdout_log": os.environ.get("G567_RUNNER_STDOUT_LOG", ""),
    "stderr_log": os.environ.get("G567_RUNNER_STDERR_LOG", ""),
    "completed_unix": time.time(),
    "forbidden_actions": {
        "gate3b_launched": False,
        "full_100k_generation_launched": False,
        "million_row_solver_acquisition_launched": False,
        "forty_eight_hour_training_launched": False,
        "final_blind_panel_constructed_or_accessed": False,
    },
}
with open(path, "w", encoding="utf-8", newline="\n") as handle:
    json.dump(payload, handle, indent=2, sort_keys=True)
    handle.write("\n")
PY
  mv -f "$tmp" "$target"
}

finalize() {
  local rc="$1"
  local reason="$2"
  printf '%s\n' "$rc" > "${RC_PATH}.tmp.$$"
  mv -f "${RC_PATH}.tmp.$$" "${RC_PATH}"
  write_json_atomic "${FINAL_SUMMARY}" "stage2a_diagnostic_a5" "$rc" "$reason" "${G567_EXPECTED_HEAD:-}"
  rm -f "${RUNNING_MARKER}"
}

on_term() {
  finalize 143 "runner_received_signal"
  exit 143
}

trap on_term TERM INT HUP

export G567_STAGE_ROOT="${STAGE_ROOT}"
export G567_RUNNER_STDOUT_LOG="${STDOUT_LOG}"
export G567_RUNNER_STDERR_LOG="${STDERR_LOG}"

if [[ -z "${G567_EXPECTED_HEAD:-}" ]]; then
  finalize 2 "missing_G567_EXPECTED_HEAD_fail_closed"
  exit 2
fi

if [[ -f "${RUNNING_MARKER}" && ! -f "${FINAL_SUMMARY}" ]]; then
  write_json_atomic "${REPORT_DIR}/phase5p5_repair5g567_stage2a_diagnostic_a5_runner_stale_previous.json" "stage2a_diagnostic_a5" 124 "stale_previous_runner_marker_without_final_summary" "${G567_EXPECTED_HEAD}"
fi

python - "$RUNNING_MARKER" "${G567_EXPECTED_HEAD}" <<'PY'
import json
import os
import sys
import time

path, expected_head = sys.argv[1:3]
payload = {
    "schema_version": "phase5p5_repair5g567_stage2a_runner_running_v1",
    "pid": os.getpid(),
    "started_unix": time.time(),
    "expected_head": expected_head,
    "head": os.popen("git rev-parse HEAD 2>/dev/null").read().strip(),
}
with open(path, "w", encoding="utf-8", newline="\n") as handle:
    json.dump(payload, handle, indent=2, sort_keys=True)
    handle.write("\n")
PY

set +e
python scripts/run_repair5g567_stage2a_train_diagnostic_a5.py \
  --stage-root "${STAGE_ROOT}" \
  --expected-head "${G567_EXPECTED_HEAD}" \
  --contexts "${G567_STAGE2A_CONTEXTS:-64}" \
  --context-pool "${G567_STAGE2A_CONTEXT_POOL:-2048}" \
  --train-agent-tiers "${G567_STAGE2A_TRAIN_AGENT_TIERS:-32,64,128,256}" \
  --max-workers "${G567_STAGE2A_MAX_WORKERS:-1}" \
  --binary "${G567_SOLVER_BINARY:-build/phase1a-batch/phase1a_batch}" \
  --overwrite \
  "$@" > >(tee -a "${STDOUT_LOG}") 2> >(tee -a "${STDERR_LOG}" >&2)
rc=$?
set -e

finalize "$rc" "python_stage2a_exited"
exit "$rc"
