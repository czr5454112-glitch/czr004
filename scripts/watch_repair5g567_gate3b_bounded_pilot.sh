#!/usr/bin/env bash
set -u -o pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

STAGE_ROOT="${G567_STAGE_ROOT:-/root/shared-nvme/g567_gate3b_bounded_pilot}"
REPORT_DIR="${STAGE_ROOT}/reports"
LOG_DIR="${STAGE_ROOT}/logs"
RUNNING_MARKER="${REPORT_DIR}/phase5p5_repair5g567_gate3b_bounded_pilot_runner.running.json"
RC_PATH="${REPORT_DIR}/phase5p5_repair5g567_gate3b_bounded_pilot_runner.rc"
FINAL_SUMMARY="${REPORT_DIR}/phase5p5_repair5g567_gate3b_bounded_pilot_runner_final_summary.json"
WATCHDOG_LOG="${LOG_DIR}/phase5p5_repair5g567_gate3b_bounded_pilot_watchdog.log"
WATCHDOG_MARKER="${REPORT_DIR}/phase5p5_repair5g567_gate3b_bounded_pilot_watchdog.running.json"
INTERVAL="${G567_GATE3B_WATCHDOG_INTERVAL_SEC:-30}"
MISS_LIMIT="${G567_GATE3B_WATCHDOG_MISS_LIMIT:-2}"
mkdir -p "${REPORT_DIR}" "${LOG_DIR}"

write_watchdog_marker() {
  local phase="$1"
  local missing_count="$2"
  local tmp="${WATCHDOG_MARKER}.tmp.$$"
  python - "$tmp" "$phase" "$missing_count" "$$" <<'PY'
import json
import os
import sys
import time

path, phase, missing_count, pid = sys.argv[1:5]
payload = {
    "schema_version": "phase5p5_repair5g567_gate3b_watchdog_running_v1",
    "phase": phase,
    "watchdog_pid": pid,
    "stage_root": os.environ.get("G567_STAGE_ROOT", ""),
    "heartbeat_unix": time.time(),
    "missing_count": int(missing_count),
}
with open(path, "w", encoding="utf-8", newline="\n") as handle:
    json.dump(payload, handle, indent=2, sort_keys=True)
    handle.write("\n")
PY
  mv -f "$tmp" "$WATCHDOG_MARKER"
}

write_external_missing_summary() {
  local reason="$1"
  local tmp="${FINAL_SUMMARY}.tmp.watchdog.$$"
  python - "$tmp" "$reason" "$$" "$RUNNING_MARKER" <<'PY'
import json
import os
import sys
import time
from pathlib import Path

path, reason, watchdog_pid, marker_path = sys.argv[1:5]
marker = {}
try:
    marker = json.loads(Path(marker_path).read_text(encoding="utf-8"))
except Exception:
    marker = {}
payload = {
    "schema_version": "phase5p5_repair5g567_gate3b_runner_final_summary_v2",
    "phase": "gate3b_bounded_pilot",
    "rc": 137,
    "reason": reason,
    "watchdog_pid": watchdog_pid,
    "watchdog_detected_unix": time.time(),
    "stage_root": os.environ.get("G567_STAGE_ROOT", ""),
    "expected_head": marker.get("expected_head", os.environ.get("G567_EXPECTED_HEAD", "")),
    "head": os.popen("git rev-parse HEAD 2>/dev/null").read().strip(),
    "runner_marker_at_detection": marker,
    "forbidden_actions": {
        "full_100k_generation_launched": False,
        "million_row_solver_acquisition_launched": False,
        "forty_eight_hour_training_launched": False,
        "final_blind_panel_constructed_or_accessed": False,
        "final_blind_solver_replay_launched": False,
    },
}
with open(path, "w", encoding="utf-8", newline="\n") as handle:
    json.dump(payload, handle, indent=2, sort_keys=True)
    handle.write("\n")
PY
  if [[ ! -f "${FINAL_SUMMARY}" ]]; then
    mv -f "$tmp" "$FINAL_SUMMARY"
    printf '137\n' > "${RC_PATH}.tmp.watchdog.$$"
    mv -f "${RC_PATH}.tmp.watchdog.$$" "${RC_PATH}"
  else
    rm -f "$tmp"
  fi
}

runner_missing_decision() {
  python - "$RUNNING_MARKER" <<'PY'
import json
import os
import sys
from pathlib import Path


def alive(value):
    try:
        pid = int(str(value).strip())
    except ValueError:
        return False
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


path = Path(sys.argv[1])
if not path.exists():
    print("marker_missing")
    raise SystemExit(0)
try:
    marker = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    print("marker_unreadable")
    raise SystemExit(0)
runner_alive = alive(marker.get("runner_shell_pid", ""))
python_alive = alive(marker.get("python_orchestrator_pid", ""))
if runner_alive or python_alive:
    print("alive")
else:
    print("missing")
PY
}

missing_count=0
printf '%s watchdog_start stage_root=%s pid=%s\n' "$(date -Is)" "$STAGE_ROOT" "$$" >> "$WATCHDOG_LOG"
while true; do
  if [[ -f "${FINAL_SUMMARY}" ]]; then
    write_watchdog_marker "final_summary_present" "$missing_count"
    printf '%s watchdog_exit final_summary_present\n' "$(date -Is)" >> "$WATCHDOG_LOG"
    exit 0
  fi
  decision="$(runner_missing_decision)"
  if [[ "$decision" == "missing" ]]; then
    missing_count=$((missing_count + 1))
    printf '%s watchdog_runner_missing count=%s\n' "$(date -Is)" "$missing_count" >> "$WATCHDOG_LOG"
    if (( missing_count >= MISS_LIMIT )); then
      write_watchdog_marker "external_runner_missing" "$missing_count"
      write_external_missing_summary "external_watchdog_detected_runner_process_tree_missing"
      printf '%s watchdog_wrote_external_missing_summary\n' "$(date -Is)" >> "$WATCHDOG_LOG"
      exit 0
    fi
  else
    missing_count=0
    printf '%s watchdog_decision=%s\n' "$(date -Is)" "$decision" >> "$WATCHDOG_LOG"
    write_watchdog_marker "$decision" "$missing_count"
  fi
  sleep "$INTERVAL"
done
