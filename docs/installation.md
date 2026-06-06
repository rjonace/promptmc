# Installation Guide

This guide covers PromptMC installation plus the optional OpenMC setup required for simulation execution, geometry-debug checks, and plot rendering.

## Prerequisites

- Python 3.10, 3.11, 3.12, or 3.13
- OpenMC, built from source or executable in `PATH`, for running simulations
- Nuclear cross-section data for running simulations

PromptMC planning, template generation, XML validation, and schema validation work without OpenMC installed.

## Install PromptMC

```bash
pip install promptmc
pip install promptmc[mcp]         # optional MCP server
pip install promptmc[telemetry]   # optional OpenTelemetry support
```

For editable development:

```bash
git clone https://github.com/rjonace/promptmc.git
cd promptmc
poetry install --with dev --extras "telemetry mcp"
```

## Install OpenMC

OpenMC is not available via pip. Build from source when you need execution, plotting, or geometry-debug workflows:

### macOS with Homebrew

```bash
# Install build dependencies
brew install cmake hdf5

# Clone and build OpenMC
git clone https://github.com/openmc-dev/openmc.git
cd openmc
mkdir build && cd build
cmake ..
make -j4
sudo make install
```

### Linux (Ubuntu/Debian)

```bash
# Install build dependencies
sudo apt-get update
sudo apt-get install build-essential cmake libhdf5-dev

# Clone and build OpenMC
git clone https://github.com/openmc-dev/openmc.git
cd openmc
mkdir build && cd build
cmake ..
make -j4
sudo make install
```

### Verify Installation

```bash
openmc --version
python -c "import openmc; print(openmc.__version__)"
```

For detailed installation instructions, see https://docs.openmc.org/en/stable/quickstart.html

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
