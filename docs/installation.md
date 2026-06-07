# Installation Guide

This guide covers PromptMC installation plus the optional OpenMC setup required for simulation execution, geometry-debug checks, and plot rendering.

## Prerequisites

- Python 3.10, 3.11, 3.12, or 3.13
- OpenMC, built from source or executable in `PATH`, for running simulations
- Nuclear cross-section data for running simulations

PromptMC planning, template generation, XML validation, and schema validation work without OpenMC installed.

## Install PromptMC

```bash
pip install promptmc              # CLI, MCP server, and Gemini planner
pip install promptmc[telemetry]   # optional OpenTelemetry support
```

For editable development:

```bash
git clone https://github.com/rjonace/promptmc.git
cd promptmc
poetry install --with dev --extras "telemetry"
```

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
