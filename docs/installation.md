# Installation Guide

This guide covers detailed installation instructions for OpenMC and PromptMC, including building OpenMC from source.

## Prerequisites

- Python 3.10 or higher (required for OpenMC Python API compatibility)
- OpenMC (built from source or executable in PATH)
- Nuclear cross-section data (for running simulations)

## Install OpenMC

OpenMC is not available via pip. Build from source:

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

## Install PromptMC

```bash
# Clone the repository
git clone https://github.com/rjonace/promptmc.git
cd promptmc

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode
pip install -e .

# Install with optional telemetry support
pip install -e ".[telemetry]"

# Install development dependencies (optional)
pip install pytest pytest-cov mypy ruff pre-commit bandit types-PyYAML types-psutil types-defusedxml
```

## Verify Installation

```bash
# Check OpenMC installation
promptmc info

# Check system info
promptmc system-info

# Run a quick validation test
promptmc validate --help
```
