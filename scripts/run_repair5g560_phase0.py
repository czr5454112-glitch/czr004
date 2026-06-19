from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str], root: Path) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=root, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run G5.60 Phase 0 on the RTX5090 server without new solver replay.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--steps", type=int, default=20000)
    parser.add_argument("--fold-steps", type=int, default=4000)
    parser.add_argument("--hidden-dim", type=int, default=128)
    parser.add_argument("--seed", type=int, default=560)
    parser.add_argument("--g0-steps", type=int, default=6000)
    parser.add_argument("--g1-actor-steps", type=int, default=5000)
    parser.add_argument("--g1-critic-steps", type=int, default=3000)
    parser.add_argument("--replay-limit", type=int, default=300)
    parser.add_argument("--scenario-limit", type=int, default=None)
    parser.add_argument("--skip-pytest", action="store_true")
    args = parser.parse_args()
    py = sys.executable
    if not args.skip_pytest:
        run([py, "-m", "pytest", "tests/test_repair5g560_labelv51.py", "tests/test_repair5g560_direct_actor.py", "tests/test_repair5g559_gcst.py", "-q"], args.root)
    run([py, "scripts/audit_repair5g560_g559_truth.py", "--root", str(args.root)], args.root)
    run([py, "scripts/recover_repair5g560_labelv51.py", "--root", str(args.root)], args.root)
    scenario_cmd = [py, "scripts/validate_repair5g560_scenarios.py", "--root", str(args.root)]
    if args.scenario_limit:
        scenario_cmd.extend(["--limit", str(args.scenario_limit)])
    run(scenario_cmd, args.root)
    run([py, "scripts/analyze_repair5g560_oracle_gap.py", "--root", str(args.root)], args.root)
    run([py, "scripts/train_repair5g560_direct_actor.py", "--root", str(args.root), "--seed", str(args.seed), "--hidden-dim", str(args.hidden_dim), "--steps", str(args.g0_steps)], args.root)
    run(
        [
            py,
            "scripts/train_repair5g560_direct_actor_critic.py",
            "--root",
            str(args.root),
            "--seed",
            str(args.seed + 1),
            "--hidden-dim",
            str(args.hidden_dim),
            "--actor-steps",
            str(args.g1_actor_steps),
            "--critic-steps",
            str(args.g1_critic_steps),
        ],
        args.root,
    )
    run([py, "scripts/eval_repair5g560_direct_actor.py", "--root", str(args.root), "--device", "cpu"], args.root)
    run([py, "scripts/export_repair5g560_direct_actor.py", "--root", str(args.root)], args.root)
    run([py, "scripts/run_repair5g560_direct_actor_dev_replay.py", "--limit", str(args.replay_limit), "--overwrite"], args.root)


if __name__ == "__main__":
    main()
