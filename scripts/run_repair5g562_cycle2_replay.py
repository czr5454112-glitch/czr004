from run_repair5g562_replay_truth import main


if __name__ == "__main__":
    raise SystemExit(
        main(
            [
                "--phase",
                "cycle2",
                "--contexts",
                "800",
                "--preferred-split",
                "any",
                "--variants",
                "A1,A2,A4",
                *(__import__("sys").argv[1:]),
            ]
        )
    )
