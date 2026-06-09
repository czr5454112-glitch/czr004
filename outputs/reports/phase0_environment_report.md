# Phase0 Environment Report

Date: 2026-05-20  
Environment: `czr004`

## Summary

Phase0 environment setup is complete enough to start Phase1 planning. The conda environment is installed for C++/metrics work, the LaCAM* upstream submodule is locked, the upstream library build/tests pass on Windows through a documented build-only compatibility header, and GPU PyTorch is verified in the same `czr004` environment.

## Verified Commands

```text
python: 3.11.15
cmake: 4.3.2
ninja: 1.13.2
git: 2.54.0.windows.1
```

## Verified Python Imports

```text
numpy 2.4.6
pandas 3.0.3
scipy 1.17.1
pyyaml 6.0.3
networkx 3.6.1
matplotlib 3.10.9
statsmodels 0.14.6
pytest 9.0.3
pybind11 3.0.3
```

## PyTorch / CUDA Status

Initial PyTorch installation failed on Windows because the conda package cache path was too long while extracting `pytorch-2.10.0`. Retrying with a short package cache initially installed packages:

```powershell
$env:CONDA_PKGS_DIRS='C:\tmp\conda_pkgs'
conda install -n czr004 -c pytorch -c conda-forge --override-channels pytorch torchvision torchaudio cpuonly -y
```

That path was abandoned. A later conda CUDA attempt installed `pytorch-cuda=12.4` but selected `conda-forge` CPU builds for `pytorch`/`libtorch`, leaving `torch.version.cuda=None`.

Accepted fix:

```powershell
conda remove -n czr004 pytorch torchvision torchaudio libtorch -y
& "$env:USERPROFILE\.conda\envs\czr004\python.exe" -m pip install --index-url https://download.pytorch.org/whl/cu124 torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1
& "$env:USERPROFILE\.conda\envs\czr004\python.exe" -m pip install --force-reinstall pillow==10.4.0
```

Verified result:

```text
torch 2.5.1+cu124
torchvision 0.20.1+cu124
torchaudio 2.5.1+cu124
torch cuda 12.4
cuda available True
device count 1
device NVIDIA GeForce RTX 4070 Laptop GPU
tensor cuda:0 1048576.0
```

## C++ Toolchain

Installed `cxx-compiler` for MSVC activation. MinGW was also installed during troubleshooting, but the accepted Phase0 build uses MSVC + Ninja.

## Upstream Status

Selected upstream:

```text
https://github.com/Kei18/lacam2
```

Recorded submodule:

```text
61a4c40ce91ce18c06eb2fe070aa9f1951eecb8d external/lacam2 (v0.1-13-g61a4c40)
```

Recursive submodules:

```text
scripts: 09a158196e513252cfb468ad46e33568787c1e92
argparse: e9ae471ea46a0f3dcd2bbbd26fa3d14433ec7884
googletest: 5376968f6948923e2411081fd9372e71a59d8e77
```

## Build And Smoke

Build:

```text
external/lacam2/build-czr004-msvc-compat
```

Compatibility header:

```text
cpp/compat/lacam2_windows_compat.hpp
```

Validation:

```text
build-czr004-msvc-compat\test_all.exe
7 tests from 6 test suites ran.
7 passed.
```

CLI caveat: the upstream `main.exe` timed out locally even with a small loop instance. The argparse short-flag clash between `-v/--version` and `-v/--verbose` is a known risk, but the timeout was also observed without relying on `-v`; treat the CLI root cause as unproven. Phase1 should use `scripts/phase0_smoke.ps1`, `build/phase0-smoke/phase0_smoke.exe`, or a project-owned adapter CLI instead of upstream `main.exe`.

## Project Smoke Binary

Built from `cpp/tools/phase0_smoke.cpp`:

```text
build/phase0-smoke/phase0_smoke.exe
```

Example:

```powershell
Set-Location C:\PROGRAMING\czr004\external\lacam2
C:\PROGRAMING\czr004\build\phase0-smoke\phase0_smoke.exe
```

Observed result on loop-3:

```text
phase0_smoke ok steps=12 sum_of_loss=15
```

## Final Verification Commands

```powershell
& "$env:USERPROFILE\.conda\envs\czr004\python.exe" -c "import torch, torchvision, torchaudio; print(torch.__version__, torch.version.cuda, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
powershell -ExecutionPolicy Bypass -File scripts\phase0_smoke.ps1
```
