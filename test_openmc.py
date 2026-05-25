import openmc
import os

openmc.config['cross_sections'] = 'cross_sections/cross_sections.xml'

# 1. Materials
print("Defining materials...")
uo2 = openmc.Material(name="UO2")
uo2.add_nuclide('U235', 0.03)
uo2.add_nuclide('U238', 0.97)
uo2.add_nuclide('O16', 2.0)
uo2.set_density('g/cm3', 10.0)

water = openmc.Material(name="Light Water")
water.add_nuclide('H1', 2.0)
water.add_nuclide('O16', 1.0)
water.set_density('g/cm3', 1.0)

materials = openmc.Materials([uo2, water])
materials.export_to_xml()

# 2. Geometry
print("Defining geometry...")
sph = openmc.Sphere(r=10.0)
inside_sph = -sph
outside_sph = +sph

fuel_cell = openmc.Cell(fill=uo2, region=inside_sph)
water_cell = openmc.Cell(fill=water, region=outside_sph)

# Add an outer bounding sphere
outer_sph = openmc.Sphere(r=20.0, boundary_type='vacuum')
water_cell.region &= -outer_sph

universe = openmc.Universe(cells=[fuel_cell, water_cell])
geometry = openmc.Geometry(universe)
geometry.export_to_xml()

# 3. Settings
print("Defining settings...")
settings = openmc.Settings()
settings.batches = 5
settings.inactive = 2
settings.particles = 100

bounds = [-10, -10, -10, 10, 10, 10]
uniform_dist = openmc.stats.Box(bounds[:3], bounds[3:])
source = openmc.IndependentSource(space=uniform_dist)
settings.source = source
settings.export_to_xml()

# 4. Run OpenMC
print("Running OpenMC...")
try:
    openmc.run()
    print("OpenMC simulation completed successfully!")
except Exception as e:
    print(f"Failed to run OpenMC: {e}")
