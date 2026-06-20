# UO2 Criticality Example (subcritical water-reflected sphere)

This example demonstrates the `promptmc` workflow (generate settings, validate,
run, analyze) on a small UO2 and light-water model using OpenMC's criticality
(eigenvalue) mode.

> **Expected result: k-effective ≈ 0.44 (subcritical).** This is the correct
> answer for this geometry, not a broken run. A 10 cm sphere of 3%-enriched UO2
> with a thin water reflector is far below critical: low-enriched UO2 only
> approaches criticality when it is thermally moderated (for example, thin fuel
> pins interspersed with water, as in a reactor lattice), not as a solid
> undermoderated lump. The example is here to exercise the toolchain, not to
> reproduce a critical configuration. Validated near-critical and critical
> benchmarks (Godiva, Jezebel, the PWR pin) ship in the reference geometry
> library; see the [roadmap](https://github.com/rjonace/promptmc/blob/main/ROADMAP.md).

## Included Files

- `geometry.xml`: a 10 cm sphere of UO2, surrounded by a 10 cm light-water
  reflector, bounded by a vacuum sphere at 20 cm.
- `materials.xml`: UO2 (3% enriched, 10 g/cm³) and light water (1 g/cm³).
- `settings.xml`: criticality (eigenvalue) settings, 500 particles over 20
  batches (10 inactive). Regenerate it with the step below or edit it directly.
- `statepoint.20.h5`, `summary.h5`: results from a prior run, so `analyze`
  works out of the box without cross-section data. Re-running overwrites them.

## Prerequisites

To run (rather than just validate or analyze) you need nuclear cross-section
data for U235, U238, O16, and H1. Download it with the OpenMC Data Downloader,
from the root of the repository:

```bash
poetry run openmc_data_downloader -l TENDL-2019 -i U235 U238 O16 H1 -d cross_sections
export OPENMC_CROSS_SECTIONS=$(pwd)/cross_sections/cross_sections.xml
```

`promptmc doctor` reports whether OpenMC, this data, and the rest of the
environment are set up correctly.

## Running the Example

1. **Generate settings:**
   Generate `settings.xml` from the built-in `criticality` template. We use 500
   particles and 20 batches for a quick test. The emitted file carries a
   provenance header (PromptMC version, timestamp, and the exact command).

   ```bash
   poetry run promptmc template criticality --output src/promptmc/examples/uo2_criticality/settings.xml --particles 500 --batches 20
   ```

2. **Run the simulation:**
   `promptmc` auto-detects the Python API or falls back to the `openmc`
   executable as a subprocess.

   ```bash
   poetry run promptmc run src/promptmc/examples/uo2_criticality/
   ```

   > **Tip:** If you installed the optional `[telemetry]` extra, the default
   > console exporter dumps verbose JSON telemetry to stdout alongside OpenMC
   > output. To silence it for a one-off run:
   >
   > ```bash
   > OTEL_CONSOLE_EXPORT=false poetry run promptmc run src/promptmc/examples/uo2_criticality/
   > ```

3. **View results:**
   OpenMC prints the k-effective values and writes `statepoint.20.h5` and
   `summary.h5` into the example directory. Parse and pretty-print them with:

   ```bash
   poetry run promptmc analyze src/promptmc/examples/uo2_criticality/
   ```

   You should see a k-effective near 0.44 (with a wide uncertainty band at only
   500 particles). Increase `--particles` for a tighter estimate.
