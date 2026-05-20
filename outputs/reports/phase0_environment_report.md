# Phase0 Environment Report

Date: 2026-05-20  
Environment: `czr004`

## Summary

The Phase0 base environment is installed and verified. PyTorch is intentionally excluded from the base environment after repeated Windows conda extraction failures. Model dependencies will be handled later in Phase4.

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

## PyTorch Deferral

`conda env update` repeatedly failed while extracting `pytorch-2.10.0-cpu_openblas_py311h7dd4006_3.conda`, with a missing long-path test file under the package cache. Since Phase0 only needs C++ build tools and metrics dependencies, PyTorch was removed from `environment.yml` and deferred to Phase4.

## Upstream Clone Status

`git submodule add https://github.com/Kei18/lacam2.git external/lacam2` failed with:

```text
Could not resolve host: github.com
```

No `.gitmodules` file or partial `external/lacam2` checkout remains after the failed attempt.
