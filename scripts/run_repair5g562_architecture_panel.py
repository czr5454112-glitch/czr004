from run_repair5g562_replay_truth import main


if __name__ == "__main__":
    raise SystemExit(
        main(
            [
                "--phase",
                "cycle1",
                "--contexts",
                "200",
                "--preferred-split",
                "validation,heldout",
                "--variants",
                "C0,A0,A1,A2,A4",
                *(__import__("sys").argv[1:]),
            ]
        )
    )
