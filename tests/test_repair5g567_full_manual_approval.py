from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_full_launcher_requires_fresh_manual_gptpro_approval() -> None:
    script = (ROOT / "scripts/server_start_repair5g567_full.sh").read_text(encoding="utf-8")
    assert 'expected_approval="APPROVE_G567_FULL_${actual_head}"' in script
    assert '${G567_FULL_MANUAL_APPROVAL:-}' in script
    assert "g567_full_campaign_waiting_for_manual_gptpro_review" in script
    assert "fresh manual GPT-Pro approval required" in script
    assert script.index("expected_approval=") < script.index("status_short=")
    assert "echo \"expected_approval=" not in script


def test_repo_scripts_do_not_self_set_full_manual_approval() -> None:
    offenders: list[str] = []
    for path in (ROOT / "scripts").glob("*.sh"):
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "G567_FULL_MANUAL_APPROVAL=" in stripped:
                offenders.append(f"{path.name}:{stripped}")
    assert offenders == []
