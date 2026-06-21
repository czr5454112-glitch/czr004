#!/usr/bin/env bash
set -u

cd /root/czr004 || exit 1

WATCH_LOG="${WATCH_LOG:-outputs/logs/phase5p5_repair5g565_overnight_watchdog.log}"
ALERT_LOG="${ALERT_LOG:-outputs/reports/phase5p5_repair5g565_overnight_alert.txt}"
MAIN_LOG="${MAIN_LOG:-outputs/logs/phase5p5_repair5g565_tmux_resume_after_mem.log}"
MAIN_SESSION="${MAIN_SESSION:-g565}"
WATCH_INTERVAL_SECONDS="${WATCH_INTERVAL_SECONDS:-600}"
MAIN_RUNNER="${MAIN_RUNNER:-/root/czr004/outputs/logs/run_g565_resume_after_mem.sh}"
RESTART_STATE="${RESTART_STATE:-outputs/logs/phase5p5_repair5g565_watchdog_restart_count.txt}"
MAX_RESTARTS="${MAX_RESTARTS:-2}"

mkdir -p "$(dirname "$WATCH_LOG")" "$(dirname "$ALERT_LOG")"
touch "$WATCH_LOG" "$ALERT_LOG"

decision_done() {
  [ -f outputs/reports/phase5p5_repair5g565_decision_summary.json ] ||
    [ -f outputs/reports/phase5p5_repair5g565_final_decision.json ]
}

active_g565_processes() {
  ps -eo pid,etime,pcpu,pmem,stat,args |
    grep -E 'run_repair5g565|train_repair5g565|phase5p5_repair5g565|phase1a_batch|run_g565_resume_after_mem' |
    grep -v -E 'grep|watch_repair5g565_overnight|phase5p5_repair5g565_overnight_watchdog' || true
}

restart_count() {
  if [ -f "$RESTART_STATE" ]; then
    tr -dc '0-9' < "$RESTART_STATE"
  else
    printf '0'
  fi
}

record_restart_count() {
  printf '%s\n' "$1" > "$RESTART_STATE"
}

maybe_restart_main() {
  if decision_done; then
    echo "watchdog_restart=skipped_decision_done"
    return
  fi
  if tmux has-session -t "$MAIN_SESSION" 2>/dev/null; then
    echo "watchdog_restart=skipped_main_tmux_alive"
    return
  fi
  if active_g565_processes | grep -q .; then
    echo "watchdog_restart=skipped_g565_process_still_alive"
    return
  fi
  if [ ! -x "$MAIN_RUNNER" ]; then
    echo "$(date -Is) main tmux missing but runner is not executable: $MAIN_RUNNER" >> "$ALERT_LOG"
    echo "watchdog_restart=blocked_runner_not_executable"
    return
  fi

  count="$(restart_count)"
  if [ "${count:-0}" -ge "$MAX_RESTARTS" ]; then
    echo "$(date -Is) main tmux missing; restart limit reached ($count/$MAX_RESTARTS)" >> "$ALERT_LOG"
    echo "watchdog_restart=blocked_restart_limit count=$count"
    return
  fi

  next=$((count + 1))
  echo "$(date -Is) main tmux missing before decision; restarting $MAIN_SESSION ($next/$MAX_RESTARTS)" >> "$ALERT_LOG"
  record_restart_count "$next"
  tmux new-session -d -s "$MAIN_SESSION" "/bin/bash $MAIN_RUNNER"
  echo "watchdog_restart=started count=$next"
}

while true; do
  {
    echo "===== $(date -Is) ====="
    if tmux has-session -t "$MAIN_SESSION" 2>/dev/null; then
      echo "main_tmux=alive"
    else
      echo "main_tmux=missing"
      maybe_restart_main
    fi

    echo "processes:"
    active_g565_processes

    echo "gpu:"
    nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu,power.draw --format=csv,noheader 2>/dev/null || true

    echo "disk:"
    df -h /root/czr004 /root/shared-nvme 2>/dev/null || true

    echo "progress:"
    python - <<'PY'
import json
from collections import Counter
from pathlib import Path

log = Path("outputs/logs/phase5p5_repair5g565_tmux_resume_after_mem.log")
scaling = []
decisions = []
commands = []
errors = []
if log.exists():
    for line in log.read_text(errors="replace").splitlines():
        low = line.lower()
        if '"event": "scaling"' in line:
            try:
                scaling.append(json.loads(line))
            except Exception:
                pass
        if '"decision"' in line:
            decisions.append(line)
        if "staged_scaling_command" in line:
            commands.append(line)
        if any(tok in low for tok in ["traceback", "exception", "error", "blocked", "no_rows", "killed", "cuda out of memory", "outofmemory"]):
            errors.append(line)
print({
    "scaling_events": len(scaling),
    "by_size": dict(Counter(row.get("size") for row in scaling)),
    "last": scaling[-1] if scaling else None,
    "commands": len(commands),
    "decisions_tail": decisions[-3:],
    "errors_tail": errors[-3:],
})
PY

    echo "tail:"
    tail -n 8 "$MAIN_LOG" 2>/dev/null || true
  } >> "$WATCH_LOG" 2>&1
  sleep "$WATCH_INTERVAL_SECONDS"
done
