# Upstream Baseline Selection

Date: 2026-05-20

## Selected Upstream

Primary upstream for Phase0 and Phase1:

- Repository: `https://github.com/Kei18/lacam2`
- Role: LaCAM* baseline and LTM implementation base.
- Rationale: the IJCAI-23 LaCAM* paper states that code is available from `https://kei18.github.io/lacam2/`, and the public repository is titled `Improving LaCAM for Scalable Eventually Optimal Multi-Agent Pathfinding (IJCAI-23)`.

Reference links:

- GitHub: https://github.com/Kei18/lacam2
- IJCAI paper page: https://www.ijcai.org/proceedings/2023/28

## Not Yet Recorded

- Exact commit hash after clone.
- Submodule status after clone.
- Local build command result.
- Single-instance smoke result.

## 2026-05-20 Clone Attempt

Command:

```powershell
git submodule add https://github.com/Kei18/lacam2.git external/lacam2
```

Result:

```text
Could not resolve host: github.com
```

No partial submodule state remained: `.gitmodules` was not created and `external/lacam2` does not exist.

## Phase0 Rule

No solver code should be changed until the upstream commit hash and baseline smoke command are recorded here.
