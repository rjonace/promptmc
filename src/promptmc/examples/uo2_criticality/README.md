# UO2 Criticality Example

This example demonstrates how to run a basic UO2 and Light Water criticality simulation using `promptmc`.

## Included Files
- `geometry.xml`: A simple 10cm sphere of UO2 surrounded by 10cm of Light Water, bounded by a vacuum sphere.
- `materials.xml`: UO2 (3% enriched) and Light Water material definitions.

## Prerequisites

Before running this example, you need nuclear cross-section data for U235, U238, O16, and H1. You can download this data using the OpenMC Data Downloader.

Run this from the root of the repository:
```bash
poetry run openmc_data_downloader -l TENDL-2019 -i U235 U238 O16 H1 -d cross_sections
export OPENMC_CROSS_SECTIONS=$(pwd)/cross_sections/cross_sections.xml
```

## Running the Example

1. **Generate Settings:**
   Use `promptmc` to generate the `settings.xml` file based on the built-in `criticality` template. We will use 500 particles and 20 batches for this quick test.

   ```bash
   poetry run promptmc template criticality --output examples/uo2_criticality/settings.xml --particles 500 --batches 20
   ```

2. **Run Simulation:**
   Use `promptmc` to execute the simulation. It will automatically detect the Python API or use the `openmc` executable as a subprocess.

   ```bash
   poetry run promptmc run examples/uo2_criticality/
   ```

   > **Tip:** If you installed the optional `[telemetry]` extra, the default console exporter will dump verbose JSON telemetry to stdout alongside OpenMC output. To silence it for a one-off run:
   >
   > ```bash
   > OTEL_CONSOLE_EXPORT=false poetry run promptmc run examples/uo2_criticality/
   > ```

3. **View Results:**
   Once finished, OpenMC will print the k-effective values to your terminal and write `statepoint.20.h5` and `summary.h5` into `examples/uo2_criticality/`. You can also parse and pretty-print the results:

   ```bash
   poetry run promptmc analyze examples/uo2_criticality/
   ```
