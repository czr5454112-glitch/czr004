#!/usr/bin/env bash
set -u -o pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

STAGE_ROOT="${G567_STAGE_ROOT:-/root/shared-nvme/g567_gate3b_bounded_pilot}"
REPORT_DIR="${STAGE_ROOT}/reports"
LOG_DIR="${STAGE_ROOT}/logs"
mkdir -p "${REPORT_DIR}" "${LOG_DIR}"

RC_PATH="${REPORT_DIR}/phase5p5_repair5g567_gate3b_bounded_pilot_runner.rc"
FINAL_SUMMARY="${REPORT_DIR}/phase5p5_repair5g567_gate3b_bounded_pilot_runner_final_summary.json"
RUNNING_MARKER="${REPORT_DIR}/phase5p5_repair5g567_gate3b_bounded_pilot_runner.running.json"
PREVIOUS_FINAL_SUMMARY="${REPORT_DIR}/phase5p5_repair5g567_gate3b_bounded_pilot_runner_previous_final_summary.json"
PREVIOUS_RC_PATH="${REPORT_DIR}/phase5p5_repair5g567_gate3b_bounded_pilot_runner.previous.rc"
STDOUT_LOG="${LOG_DIR}/phase5p5_repair5g567_gate3b_bounded_pilot_runner.stdout.log"
STDERR_LOG="${LOG_DIR}/phase5p5_repair5g567_gate3b_bounded_pilot_runner.stderr.log"
RUNNER_FINALIZED=0
RUNNER_STARTED_UNIX="$(python -c 'import time; print(time.time())')"
RUNNER_SHELL_PID="$$"
RUNNER_BASHPID="${BASHPID:-$$}"
RUNNER_PARENT_PID="${PPID:-}"
RUNNER_PGID="$(ps -o pgid= -p "$$" 2>/dev/null | tr -d ' ' || true)"
RUNNER_SID="$(ps -o sid= -p "$$" 2>/dev/null | tr -d ' ' || true)"
RUNNER_CGROUP="$(tr '\n' ';' < "/proc/$$/cgroup" 2>/dev/null || true)"
PYTHON_PID=""
HEARTBEAT_PID=""
PYTHON_TREE_TERMINATED=0

tmux_server_pid() {
  if command -v tmux >/dev/null 2>&1 && [[ -n "${TMUX:-}" ]]; then
    tmux display-message -p '#{pid}' 2>/dev/null || true
  fi
}

write_json_atomic() {
  local target="$1"
  local tmp="${target}.tmp.$$"
  python - "$tmp" "$2" "$3" "$4" "$5" \
    "${RUNNER_SHELL_PID}" "${RUNNER_BASHPID}" "${RUNNER_PARENT_PID}" "${RUNNER_PGID}" "${RUNNER_SID}" \
    "${PYTHON_PID:-}" "${HEARTBEAT_PID:-}" "${RUNNER_STARTED_UNIX}" "${RUNNER_CGROUP}" "$(tmux_server_pid)" <<'PY'
import json
import os
import sys
import time

(
    path,
    phase,
    rc,
    reason,
    expected_head,
    runner_shell_pid,
    runner_bashpid,
    runner_parent_pid,
    runner_pgid,
    runner_sid,
    python_pid,
    heartbeat_pid,
    started_unix,
    runner_cgroup,
    tmux_pid,
) = sys.argv[1:16]
payload = {
    "schema_version": "phase5p5_repair5g567_gate3b_runner_final_summary_v2",
    "phase": phase,
    "rc": int(rc),
    "reason": reason,
    "expected_head": expected_head,
    "head": os.popen("git rev-parse HEAD 2>/dev/null").read().strip(),
    "status_short": os.popen("git status --short 2>/dev/null").read(),
    "stage_root": os.environ.get("G567_STAGE_ROOT", ""),
    "stdout_log": os.environ.get("G567_RUNNER_STDOUT_LOG", ""),
    "stderr_log": os.environ.get("G567_RUNNER_STDERR_LOG", ""),
    "runner_shell_pid": runner_shell_pid,
    "runner_bashpid": runner_bashpid,
    "runner_parent_pid": runner_parent_pid,
    "runner_pgid": runner_pgid,
    "runner_sid": runner_sid,
    "runner_cgroup": runner_cgroup,
    "python_orchestrator_pid": python_pid,
    "heartbeat_pid": heartbeat_pid,
    "tmux_server_pid": tmux_pid,
    "tmux_session_name": os.environ.get("G567_TMUX_SESSION_NAME", ""),
    "tmux": os.environ.get("TMUX", ""),
    "started_unix": float(started_unix or 0.0),
    "completed_unix": time.time(),
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
  mv -f "$tmp" "$target"
}

write_running_marker() {
  local phase="$1"
  local python_pid="${2:-}"
  local tmp="${RUNNING_MARKER}.tmp.$$"
  python - "$tmp" "$phase" "${G567_EXPECTED_HEAD:-}" \
    "${RUNNER_SHELL_PID}" "${RUNNER_BASHPID}" "${RUNNER_PARENT_PID}" "${RUNNER_PGID}" "${RUNNER_SID}" \
    "${python_pid}" "${HEARTBEAT_PID:-}" "${RUNNER_STARTED_UNIX}" "${RUNNER_CGROUP}" "$(tmux_server_pid)" <<'PY'
import csv
import json
import os
import signal
import sys
import time
from pathlib import Path


def pid_alive(raw: str) -> bool:
    try:
        pid = int(str(raw).strip())
    except ValueError:
        return False
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def proc_cgroup(raw: str) -> str:
    try:
        pid = int(str(raw).strip())
    except ValueError:
        return ""
    try:
        return Path(f"/proc/{pid}/cgroup").read_text(encoding="utf-8").replace("\n", ";")
    except OSError:
        return ""


def memory_snapshot() -> dict[str, object]:
    out = {
        "cgroup_path": "",
        "cgroup_memory_current_bytes": "",
        "cgroup_memory_peak_bytes": "",
        "cgroup_memory_max_bytes": "",
        "cgroup_memory_events": {},
    }
    try:
        lines = Path("/proc/self/cgroup").read_text(encoding="utf-8").splitlines()
    except OSError:
        return out
    cgroup_path = ""
    for line in lines:
        parts = line.split(":", 2)
        if len(parts) == 3 and (parts[1] == "" or "memory" in parts[1].split(",")):
            cgroup_path = parts[2].strip()
            if parts[1] == "":
                break
    if not cgroup_path:
        return out
    cdir = Path("/sys/fs/cgroup") / cgroup_path.lstrip("/")
    if not cdir.exists():
        cdir = Path("/sys/fs/cgroup")
    out["cgroup_path"] = cgroup_path
    for name, key in [
        ("memory.current", "cgroup_memory_current_bytes"),
        ("memory.peak", "cgroup_memory_peak_bytes"),
        ("memory.max", "cgroup_memory_max_bytes"),
    ]:
        try:
            text = (cdir / name).read_text(encoding="utf-8").strip()
            out[key] = text if text == "max" else int(text)
        except (OSError, ValueError):
            out[key] = ""
    events = {}
    try:
        for line in (cdir / "memory.events").read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) == 2:
                events[parts[0]] = int(parts[1])
    except (OSError, ValueError):
        events = {}
    out["cgroup_memory_events"] = events
    return out


def csv_rows(path: Path) -> int:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            return max(0, sum(1 for _ in csv.reader(handle)) - 1)
    except OSError:
        return 0


(
    path,
    phase,
    expected_head,
    runner_shell_pid,
    runner_bashpid,
    runner_parent_pid,
    runner_pgid,
    runner_sid,
    python_pid,
    heartbeat_pid,
    started_unix,
    runner_cgroup,
    tmux_pid,
) = sys.argv[1:14]
stage_root = Path(os.environ.get("G567_STAGE_ROOT", ""))
result_counts = {}
for csv_path in sorted((stage_root / "tables").glob("*_results.csv")):
    result_counts[csv_path.name] = csv_rows(csv_path)
completed_solver_rows = max(result_counts.values(), default=0)
payload = {
    "schema_version": "phase5p5_repair5g567_gate3b_runner_running_v2",
    "phase": phase,
    "expected_head": expected_head,
    "head": os.popen("git rev-parse HEAD 2>/dev/null").read().strip(),
    "stage_root": str(stage_root),
    "runner_shell_pid": runner_shell_pid,
    "runner_bashpid": runner_bashpid,
    "runner_parent_pid": runner_parent_pid,
    "runner_pgid": runner_pgid,
    "runner_sid": runner_sid,
    "runner_cgroup": runner_cgroup,
    "runner_shell_pid_alive": pid_alive(runner_shell_pid),
    "python_orchestrator_pid": python_pid,
    "python_orchestrator_pid_alive": pid_alive(python_pid),
    "python_orchestrator_cgroup": proc_cgroup(python_pid),
    "heartbeat_pid": heartbeat_pid,
    "heartbeat_pid_alive": pid_alive(heartbeat_pid),
    "tmux_server_pid": tmux_pid,
    "tmux_session_name": os.environ.get("G567_TMUX_SESSION_NAME", ""),
    "tmux": os.environ.get("TMUX", ""),
    "started_unix": float(started_unix or 0.0),
    "heartbeat_unix": time.time(),
    "completed_solver_rows": completed_solver_rows,
    "result_csv_rows_by_file": result_counts,
    "disk_free_bytes_stage_root": "",
    **memory_snapshot(),
    "forbidden_actions": {
        "full_100k_generation_launched": False,
        "million_row_solver_acquisition_launched": False,
        "forty_eight_hour_training_launched": False,
        "final_blind_panel_constructed_or_accessed": False,
        "final_blind_solver_replay_launched": False,
    },
}
try:
    payload["disk_free_bytes_stage_root"] = os.statvfs(stage_root).f_bavail * os.statvfs(stage_root).f_frsize
except OSError:
    payload["disk_free_bytes_stage_root"] = ""
with open(path, "w", encoding="utf-8", newline="\n") as handle:
    json.dump(payload, handle, indent=2, sort_keys=True)
    handle.write("\n")
PY
  mv -f "$tmp" "${RUNNING_MARKER}"
}

heartbeat_loop() {
  local interval="${G567_RUNNER_HEARTBEAT_INTERVAL_SEC:-30}"
  while true; do
    write_running_marker "running" "${PYTHON_PID:-}"
    sleep "${interval}"
  done
}

terminate_python_tree() {
  if [[ "${PYTHON_TREE_TERMINATED}" == "1" ]]; then
    return 0
  fi
  PYTHON_TREE_TERMINATED=1
  if [[ -z "${PYTHON_PID:-}" ]]; then
    return 0
  fi
  if ! kill -0 "${PYTHON_PID}" >/dev/null 2>&1; then
    return 0
  fi
  local child child_pgid
  while read -r child; do
    [[ -n "${child}" ]] || continue
    child_pgid="$(ps -o pgid= -p "${child}" 2>/dev/null | tr -d ' ' || true)"
    if [[ -n "${child_pgid}" && "${child_pgid}" != "$(ps -o pgid= -p "$$" 2>/dev/null | tr -d ' ' || true)" ]]; then
      kill -TERM "-${child_pgid}" >/dev/null 2>&1 || true
    else
      kill -TERM "${child}" >/dev/null 2>&1 || true
    fi
  done < <(pgrep -P "${PYTHON_PID}" 2>/dev/null || true)
  kill -TERM "${PYTHON_PID}" >/dev/null 2>&1 || true
  for _ in $(seq 1 10); do
    if ! kill -0 "${PYTHON_PID}" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  while read -r child; do
    [[ -n "${child}" ]] || continue
    child_pgid="$(ps -o pgid= -p "${child}" 2>/dev/null | tr -d ' ' || true)"
    if [[ -n "${child_pgid}" && "${child_pgid}" != "$(ps -o pgid= -p "$$" 2>/dev/null | tr -d ' ' || true)" ]]; then
      kill -KILL "-${child_pgid}" >/dev/null 2>&1 || true
    else
      kill -KILL "${child}" >/dev/null 2>&1 || true
    fi
  done < <(pgrep -P "${PYTHON_PID}" 2>/dev/null || true)
  kill -KILL "${PYTHON_PID}" >/dev/null 2>&1 || true
}

finalize() {
  local rc="$1"
  local reason="$2"
  if [[ "${RUNNER_FINALIZED}" == "1" ]]; then
    return 0
  fi
  RUNNER_FINALIZED=1
  set +e
  if [[ "${reason}" != "python_gate3b_exited" ]]; then
    terminate_python_tree
  fi
  if [[ -n "${HEARTBEAT_PID:-}" ]]; then
    kill "${HEARTBEAT_PID}" >/dev/null 2>&1 || true
    wait "${HEARTBEAT_PID}" >/dev/null 2>&1 || true
  fi
  write_running_marker "finalizing" "${PYTHON_PID:-}"
  cp -f "${RUNNING_MARKER}" "${RUNNING_MARKER%.json}.last.json" 2>/dev/null || true
  printf '%s\n' "$rc" > "${RC_PATH}.tmp.$$"
  mv -f "${RC_PATH}.tmp.$$" "${RC_PATH}"
  write_json_atomic "${FINAL_SUMMARY}" "gate3b_bounded_pilot" "$rc" "$reason" "${G567_EXPECTED_HEAD:-}"
  rm -f "${RUNNING_MARKER}"
}

on_exit() {
  local rc="$?"
  if [[ "${RUNNER_FINALIZED}" != "1" ]]; then
    finalize "$rc" "runner_exit_trap"
  fi
}

on_term() {
  finalize 143 "runner_received_signal"
  exit 143
}

trap on_exit EXIT
trap on_term TERM INT HUP

export G567_STAGE_ROOT="${STAGE_ROOT}"
export G567_RUNNER_STDOUT_LOG="${STDOUT_LOG}"
export G567_RUNNER_STDERR_LOG="${STDERR_LOG}"

if [[ -z "${G567_EXPECTED_HEAD:-}" ]]; then
  finalize 2 "missing_G567_EXPECTED_HEAD_fail_closed"
  exit 2
fi

if [[ -f "${FINAL_SUMMARY}" ]]; then
  mv -f "${FINAL_SUMMARY}" "${PREVIOUS_FINAL_SUMMARY}"
fi
if [[ -f "${RC_PATH}" ]]; then
  mv -f "${RC_PATH}" "${PREVIOUS_RC_PATH}"
fi

if [[ -f "${RUNNING_MARKER}" && ! -f "${FINAL_SUMMARY}" ]]; then
  write_json_atomic "${REPORT_DIR}/phase5p5_repair5g567_gate3b_bounded_pilot_runner_stale_previous.json" "gate3b_bounded_pilot" 124 "stale_previous_runner_marker_without_final_summary" "${G567_EXPECTED_HEAD}"
fi

write_running_marker "starting" ""

launch_unix="$(python -c 'import time; print(time.time())')"
printf '\n{"event":"gate3b_runner_launch","expected_head":"%s","stage_root":"%s","runner_shell_pid":"%s","unix":%s}\n' \
  "${G567_EXPECTED_HEAD}" "${STAGE_ROOT}" "${RUNNER_SHELL_PID}" "${launch_unix}" >> "${STDOUT_LOG}"
printf '\n{"event":"gate3b_runner_launch","expected_head":"%s","stage_root":"%s","runner_shell_pid":"%s","unix":%s}\n' \
  "${G567_EXPECTED_HEAD}" "${STAGE_ROOT}" "${RUNNER_SHELL_PID}" "${launch_unix}" >> "${STDERR_LOG}"

set +e
overwrite_args=()
if [[ "${G567_GATE3B_OVERWRITE:-0}" == "1" ]]; then
  overwrite_args+=(--overwrite)
fi
if [[ "${G567_GATE3B_SPLIT_SELECTION_ONLY:-0}" == "1" ]]; then
  overwrite_args+=(--split-selection-only)
fi
if [[ "${G567_GATE3B_SKIP_CANDIDATE_POOL_FILE_HASH_CHECK:-0}" == "1" ]]; then
  overwrite_args+=(--skip-candidate-pool-file-hash-check)
fi
python scripts/run_repair5g567_gate3b_bounded_pilot.py \
  --stage-root "${STAGE_ROOT}" \
  --expected-head "${G567_EXPECTED_HEAD}" \
  --context-pool "${G567_GATE3B_CONTEXT_POOL:-8000}" \
  --label-train-contexts "${G567_GATE3B_LABEL_TRAIN_CONTEXTS:-2000}" \
  --calibration-contexts "${G567_GATE3B_CALIBRATION_CONTEXTS:-500}" \
  --development-contexts "${G567_GATE3B_DEVELOPMENT_CONTEXTS:-500}" \
  --label-replay-solver-rows "${G567_GATE3B_LABEL_REPLAY_SOLVER_ROWS:-60000}" \
  --label-official-scenario-fraction-min "${G567_GATE3B_LABEL_OFFICIAL_SCENARIO_FRACTION_MIN:-0.20}" \
  --calibration-official-scenario-fraction-min "${G567_GATE3B_CALIBRATION_OFFICIAL_SCENARIO_FRACTION_MIN:-0.30}" \
  --development-official-scenario-fraction-min "${G567_GATE3B_DEVELOPMENT_OFFICIAL_SCENARIO_FRACTION_MIN:-0.30}" \
  --parent-concentration-cap-fraction "${G567_GATE3B_PARENT_CONCENTRATION_CAP_FRACTION:-0.15}" \
  --family-concentration-cap-fraction "${G567_GATE3B_FAMILY_CONCENTRATION_CAP_FRACTION:-0.30}" \
  --split-selection-milp-time-limit-sec "${G567_GATE3B_SPLIT_SELECTION_MILP_TIME_LIMIT_SEC:-120}" \
  --candidate-pool-source-commit "${G567_GATE3B_CANDIDATE_POOL_SOURCE_COMMIT:-}" \
  --max-workers "${G567_GATE3B_MAX_WORKERS:-8}" \
  --materialize-workers "${G567_GATE3B_MATERIALIZE_WORKERS:-8}" \
  --materialize-progress-interval-sec "${G567_GATE3B_MATERIALIZE_PROGRESS_INTERVAL_SEC:-30}" \
  --batch-size "${G567_GATE3B_BATCH_SIZE:-4}" \
  --inference-token-budget "${G567_GATE3B_INFERENCE_TOKEN_BUDGET:-6000}" \
  --inference-progress-interval-sec "${G567_GATE3B_INFERENCE_PROGRESS_INTERVAL_SEC:-30}" \
  --binary "${G567_SOLVER_BINARY:-build/phase1a-batch/phase1a_batch}" \
  --min-gpu-active-hours "${G567_GATE3B_MIN_GPU_ACTIVE_HOURS:-2.0}" \
  --max-gpu-active-hours "${G567_GATE3B_MAX_GPU_ACTIVE_HOURS:-4.0}" \
  "${overwrite_args[@]}" \
  "$@" > >(tee -a "${STDOUT_LOG}") 2> >(tee -a "${STDERR_LOG}" >&2) &
PYTHON_PID="$!"
write_running_marker "python_launched" "${PYTHON_PID}"
heartbeat_loop &
HEARTBEAT_PID="$!"
write_running_marker "running" "${PYTHON_PID}"
wait "${PYTHON_PID}"
rc=$?
set -e

finalize "$rc" "python_gate3b_exited"
exit "$rc"
