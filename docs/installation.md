# Installation Guide

This guide covers PromptMC installation plus the optional OpenMC setup required for simulation execution, geometry-debug checks, and plot rendering.

## Prerequisites

- Python 3.10, 3.11, 3.12, 3.13, or 3.14
- [OpenMC](https://docs.openmc.org/en/stable/), built from source or executable in `PATH`, for running simulations
- Nuclear cross-section data for running simulations

PromptMC planning, template generation, XML validation, and schema validation work without OpenMC installed.

> **Note for macOS users:** the Python bundled with macOS (Xcode Command Line Tools) is 3.9, which is too old. If `pip install promptmc` fails with `No matching distribution found`, that is why — see [Troubleshooting](#troubleshooting). The uv method below avoids the problem entirely.

## Install PromptMC

How you install depends on which features you need:

| You want | Install method |
|---|---|
| CLI, MCP server, planning, validation | uv or pipx (isolated install) |
| Also run simulations | uv or pipx, with the `openmc` executable on `PATH` |
| Also plot rendering and geometry-debug | pip, into the same environment as OpenMC |
| Contribute to PromptMC | Poetry (editable install) |

Plot rendering and geometry-debug import OpenMC's Python API, so PromptMC must live in the same Python environment as OpenMC (typically a conda environment) for those features. Everything else works from an isolated tool install.

### Option 1: uv (recommended)

[uv](https://docs.astral.sh/uv/) installs PromptMC into its own isolated environment and puts the `promptmc` and `promptmc-mcp` commands on your `PATH`. If no suitable Python is found on your system, uv downloads one automatically.

```bash
# Install uv: https://docs.astral.sh/uv/getting-started/installation/
# e.g. on macOS: brew install uv

uv tool install promptmc                    # core
uv tool install 'promptmc[telemetry]'       # + OpenTelemetry tracing
```

To try PromptMC without installing it:

```bash
uvx promptmc plan "pin cell criticality with 50k particles"
```

### Option 2: pipx

[pipx](https://pipx.pypa.io/) gives the same isolated-install behavior using a Python already on your system (3.10+):

```bash
pipx install promptmc
pipx install 'promptmc[telemetry]'   # instead, for OpenTelemetry tracing
pipx ensurepath                      # then open a new terminal
```

### Option 3: pip into an existing environment

Use this when PromptMC must share an environment with OpenMC's Python API (required for plot rendering and geometry-debug), for example inside your conda environment:

```bash
conda activate openmc-env   # or your virtualenv
pip install promptmc
pip install 'promptmc[telemetry]'   # optional OpenTelemetry support
```

Avoid running pip against your operating system's Python or Homebrew's Python directly — modern distributions block this ([PEP 668](https://peps.python.org/pep-0668/)); use a virtual environment, or Options 1–2.

### Option 4: editable development install

```bash
git clone https://github.com/rjonace/promptmc.git
cd promptmc
poetry install --with dev --extras "telemetry"
```

The MCP server (`promptmc-mcp`) is included in every install method. To connect an AI assistant — Claude Desktop/Code, Cursor, Google Antigravity, or VS Code — see the [MCP server configuration guide](mcp.md).

## Install OpenMC

OpenMC is not available on PyPI (via pip). You can install it using Conda, Spack, Docker, or by building from source:

### Option 1: Conda (Recommended)

Conda is the easiest way to install OpenMC on Linux and macOS.

```bash
# Add the conda-forge channel
conda config --add channels conda-forge
conda config --set channel_priority strict

# Create and activate environment
conda create --name openmc-env openmc
conda activate openmc-env
```

If you are on Apple Silicon (ARM) macOS, specify the platform option:
```bash
conda create --name openmc-env --platform osx-64 openmc
```

### Option 2: Docker

With Docker running, you can run OpenMC directly:

```bash
docker run -it openmc/openmc:latest
```

### Option 3: Spack

If you use Spack for package management:

```bash
spack install py-openmc
```

### Option 4: Build from Source

If you prefer building from source:

#### macOS with Homebrew

```bash
# Install build dependencies
brew install llvm cmake xtensor hdf5 python libomp libpng

# Clone and build OpenMC
git clone --recurse-submodules https://github.com/openmc-dev/openmc.git
cd openmc
mkdir build && cd build
cmake ..
make -j4
sudo make install

# Install the Python API from the repository root
cd ..
python -m pip install .
```

#### Linux (Ubuntu/Debian)

```bash
# Install build dependencies
sudo apt update
sudo apt install g++ cmake libhdf5-dev libpng-dev

# Clone and build OpenMC
git clone --recurse-submodules https://github.com/openmc-dev/openmc.git
cd openmc
mkdir build && cd build
cmake ..
make -j4
sudo make install

# Install the Python API from the repository root
cd ..
python -m pip install .
```

### Verify Installation

```bash
openmc --version
python -c "import openmc; print(openmc.__version__)"
```

For detailed installation instructions, see https://docs.openmc.org/en/stable/quickinstall.html

## Install Nuclear Data

OpenMC requires nuclear cross-section data to run simulations. The easiest way to get this is using the `openmc_data_downloader` package:

```bash
# Install the downloader
pip install openmc-data-downloader

# Download data for specific isotopes (e.g., U-235, U-238, O-16, H-1)
openmc_data_downloader -l TENDL-2019 -i U235 U238 O16 H1 -d cross_sections

# Export the path so OpenMC can find it
export OPENMC_CROSS_SECTIONS=$(pwd)/cross_sections/cross_sections.xml
```

### Alternative: Manual Download

You can also download cross-section data directly from the [IAEA Nuclear Data Section](https://www-nds.iaea.org/endf/) or [TENDL](https://tendl.web.psi.ch/tendl_2019/tendl2019.html) and place them in a directory, then set the `OPENMC_CROSS_SECTIONS` environment variable to point to the `cross_sections.xml` file.

## Verify Installation

```bash
# Check PromptMC and OpenMC installation status
promptmc info

# Check system info
promptmc system-info

# Run a quick command check
promptmc validate --help
```

## Troubleshooting

### `No matching distribution found for promptmc`

Your Python is older than 3.10. pip reports this confusingly — the package exists, but no release supports your interpreter. This is common on macOS, where the bundled `/usr/bin/python3` (from Xcode Command Line Tools) is 3.9. Check with:

```bash
python3 --version
```

Fix: use [uv](https://docs.astral.sh/uv/) (Option 1 above), which downloads a suitable Python automatically, or install a newer Python first (e.g. `brew install python` on macOS) and invoke it by its versioned name, such as `python3.14 -m pip install promptmc`.

### `error: externally-managed-environment`

You ran pip against a Python managed by your OS or Homebrew, which blocks direct installs ([PEP 668](https://peps.python.org/pep-0668/)). Use uv or pipx (Options 1–2), or install inside a virtual environment or conda environment (Option 3).

### `command not found: promptmc` after installing

The directory holding the entry-point scripts is not on your `PATH`:

- **pipx / pip --user:** scripts land in `~/.local/bin` — run `pipx ensurepath` (or add the directory to `PATH` in your shell profile), then open a new terminal.
- **uv:** run `uv tool update-shell`, then open a new terminal.
- **conda:** make sure the environment you installed into is activated.

### Simulations fail but planning and validation work

Execution requires OpenMC, which is a separate install (see [Install OpenMC](#install-openmc)). Run `promptmc info` to see what PromptMC detects:

- Simulation runs need the `openmc` executable on `PATH` *or* the OpenMC Python API importable from PromptMC's environment.
- Plot rendering and geometry-debug need the Python API specifically — install PromptMC with pip into the same environment as OpenMC (Option 3).
- Running simulations also requires cross-section data (see [Install Nuclear Data](#install-nuclear-data)); check with `promptmc info` that `OPENMC_CROSS_SECTIONS` is set.
