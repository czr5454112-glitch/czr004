"""Repair5G.5.60 stage state file helpers."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .schemas_v51 import ROUND

ROOT = Path(__file__).resolve().parents[2]
STATE_JSON = Path(f"outputs/reports/{ROUND}_state.json")


def resolve(path: str | Path, root: Path = ROOT) -> Path:
    p = Path(path)
    return p if p.is_absolute() else root / p


def current_commit(root: Path = ROOT) -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    except Exception:
        return "unknown"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_state(root: Path = ROOT) -> dict[str, Any]:
    path = resolve(STATE_JSON, root)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "round": ROUND,
        "schema_version": "repair5g560_state_v1",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "source_commit": current_commit(root),
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
        "stages": {},
    }


def record_stage(
    stage: str,
    status: str,
    gate_result: bool,
    producer_command: str,
    artifacts: list[str] | None = None,
    metrics: dict[str, Any] | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    state = load_state(root)
    state["updated_at"] = now_iso()
    state["source_commit"] = current_commit(root)
    state["stages"][stage] = {
        "status": status,
        "gate_result": bool(gate_result),
        "producer_command": producer_command,
        "source_commit": state["source_commit"],
        "updated_at": now_iso(),
        "artifacts": artifacts or [],
        "metrics": metrics or {},
    }
    path = resolve(STATE_JSON, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    return state
