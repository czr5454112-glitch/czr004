from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from repair5g5_common import run_command_with_hard_timeout  # noqa: E402
from repair5g549_common import enrich_or_placeholder  # noqa: E402


def test_process_hard_timeout_records_timeout_provenance() -> None:
    started = time.perf_counter()
    result = run_command_with_hard_timeout(
        [sys.executable, "-c", "import time; print('started', flush=True); time.sleep(30)"],
        cwd=ROOT,
        process_hard_timeout_sec=0.25,
        timeout_term_grace_sec=0.10,
    )
    elapsed = time.perf_counter() - started
    assert elapsed < 5.0
    assert result.returncode != 0
    assert result.stdout.strip() == "started"
    assert result.provenance["process_hard_timeout_exceeded"] is True
    assert result.provenance["process_timeout_reason"] in {
        "process_hard_timeout_sec_exceeded",
        "process_already_exited_after_timeout",
    }
    assert result.provenance["process_timeout_sigterm_sent"] is True
    assert result.provenance["process_timeout_sigterm_unix"]
    assert result.provenance["child_process_group_killed"] is True
    assert result.provenance["child_process_group_kill_method"] in {"sigterm", "terminate", "sigkill", "kill"}
    assert result.provenance["process_partial_stdout_preserved"] is True
    assert result.provenance["process_partial_stdout_chars"] >= len("started")
    assert "process hard timeout exceeded" in result.stderr


def test_timeout_provenance_is_preserved_on_no_probe_placeholder() -> None:
    rows = enrich_or_placeholder(
        [],
        [
            {
                "context_id": "ctx-1",
                "role": "generated_theta::unit",
                "candidate_id": "candidate-1",
                "materialized_method": "candidate-1",
                "sampling_policy": "unit",
            }
        ],
        ("map-unit", 32, 7, 1000, "budget1000_ltm3"),
        row_prefix="unit",
        execution_mode="unit_real_solver_row",
        command_row={
            "returncode": -15,
            "returncode_classification": "process_hard_timeout",
            "process_hard_timeout_sec": 0.25,
            "process_hard_timeout_exceeded": True,
            "process_timeout_provenance": "subprocess_popen_posix_start_new_session_process_group",
            "process_timeout_reason": "process_hard_timeout_sec_exceeded",
            "process_timeout_sigterm_unix": 123.0,
            "child_process_group_killed": True,
            "child_process_group_kill_method": "sigterm",
            "process_partial_stdout_preserved": True,
            "process_partial_stdout_chars": 7,
        },
    )
    assert rows[0]["no_probe_reason"] == "process_hard_timeout_exceeded"
    assert rows[0]["process_hard_timeout_exceeded"] is True
    assert rows[0]["returncode_classification"] == "process_hard_timeout"
    assert rows[0]["solution_found"] == ""
    assert rows[0]["probe_feasible"] == ""
    assert rows[0]["candidate_recognized"] is False
    assert rows[0]["infrastructure_timeout"] is True
    assert rows[0]["scientific_result_valid"] is False
    assert rows[0]["excluded_from_scientific_labels"] is True
    assert rows[0]["fulltheta_fingerprint_match"] is False
    assert rows[0]["process_timeout_sigterm_unix"] == 123.0
    assert rows[0]["child_process_group_killed"] is True
    assert rows[0]["child_process_group_kill_method"] == "sigterm"
    assert rows[0]["process_partial_stdout_preserved"] is True
    assert rows[0]["process_partial_stdout_chars"] == 7


@pytest.mark.skipif(os.name != "posix", reason="Linux process-group semantics only")
def test_process_hard_timeout_uses_posix_process_group(tmp_path: Path) -> None:
    child_pid_path = tmp_path / "child.pid"
    script = tmp_path / "spawn_child.py"
    script.write_text(
        "\n".join(
            [
                "import pathlib",
                "import subprocess",
                "import time",
                f"pid_path = pathlib.Path({str(child_pid_path)!r})",
                "child = subprocess.Popen(['sleep', '30'])",
                "pid_path.write_text(str(child.pid), encoding='utf-8')",
                "time.sleep(30)",
            ]
        ),
        encoding="utf-8",
    )
    result = run_command_with_hard_timeout(
        [sys.executable, str(script)],
        cwd=ROOT,
        process_hard_timeout_sec=0.25,
        timeout_term_grace_sec=0.10,
    )
    assert result.provenance["process_hard_timeout_exceeded"] is True
    assert result.provenance["process_group_id"]
    assert result.provenance["process_group_termination_attempted"] is True
    assert result.provenance["child_process_group_killed"] is True
    assert result.provenance["child_process_group_kill_method"] in {"sigterm", "sigkill"}
    child_pid = int(child_pid_path.read_text(encoding="utf-8"))
    for _ in range(30):
        status = subprocess.run(["ps", "-o", "stat=", "-p", str(child_pid)], text=True, capture_output=True, check=False)
        if status.returncode != 0 or "Z" in status.stdout:
            break
        time.sleep(0.10)
    else:
        raise AssertionError("child process from timed-out process group is still running")
