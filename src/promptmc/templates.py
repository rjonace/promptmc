"""Configuration templates for OpenMC simulations."""

from __future__ import annotations

import xml.etree.ElementTree as ET  # nosec B405
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from promptmc._typing import PathLike
from promptmc.benchmarks import godiva, pwr_pin
from promptmc.geometry.materials import Material, MaterialsModel, NuclideSpec
from promptmc.geometry.primitives import (
    Cell,
    GeometryModel,
    HalfSpace,
    Sphere,
    Universe,
)
from promptmc.geometry.xml_serializer import (
    serialize_geometry,
    serialize_materials,
)
from promptmc.provenance import write_xml_with_provenance


class TemplateType(Enum):
    """Built-in template types."""

    CRITICALITY = "criticality"
    FIXED_SOURCE = "fixed_source"
    DEPLETION = "depletion"
    SHIELDING = "shielding"
    REACTOR_PIN = "reactor_pin"


@dataclass
class TemplateMetadata:
    """Metadata for a configuration template."""

    name: str
    template_type: TemplateType
    description: str
    default_particles: int = 10000
    default_batches: int = 100
    default_inactive: int = 10
    parameters: dict[str, Any] = field(default_factory=dict)


class ConfigurationTemplate:
    """Base class for OpenMC configuration templates."""

    def __init__(self, metadata: TemplateMetadata) -> None:
        """Initialize template.

        Args:
            metadata: Template metadata
        """
        self.metadata = metadata

    def render(
        self,
        output_path: PathLike,
        particles: int | None = None,
        batches: int | None = None,
        inactive: int | None = None,
        **kwargs: Any,
    ) -> Path:
        """Render a complete OpenMC input deck into a directory.

        Writes ``settings.xml`` (with a provenance header), ``geometry.xml``,
        and ``materials.xml`` so the result is a runnable deck that passes
        ``SchemaValidator.validate_directory``.

        Args:
            output_path: Directory to write the input deck into; created if
                it does not exist.
            particles: Override default particles
            batches: Override default batches
            inactive: Override default inactive batches
            **kwargs: Additional template parameters

        Returns:
            Path to the directory containing the rendered deck.
        """
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        particles = particles or self.metadata.default_particles
        batches = batches or self.metadata.default_batches
        inactive = (
            inactive if inactive is not None else self.metadata.default_inactive
        )

        root = self._build_xml(
            particles=particles,
            batches=batches,
            inactive=inactive,
            **kwargs,
        )
        write_xml_with_provenance(root, output_dir / "settings.xml")
        serialize_geometry(
            self._build_geometry(**kwargs), output_dir / "geometry.xml"
        )
        serialize_materials(
            self._build_materials(**kwargs), output_dir / "materials.xml"
        )

        return output_dir

    def _build_geometry(self, **kwargs: Any) -> GeometryModel:
        """Build the geometry model for this template.

        The base implementation returns a minimal bounded geometry: a single
        void cell inside a vacuum sphere. Subclasses override this to emit a
        meaningful geometry.

        Args:
            **kwargs: Additional template parameters

        Returns:
            A valid ``GeometryModel``.
        """
        sphere = Sphere(id=1, name="boundary", r=10.0, boundary_type="vacuum")
        cell = Cell(id=1, name="void", region=HalfSpace(surface_id=1, side="-"))
        return GeometryModel(
            surfaces=[sphere], root_universe=Universe(id=1, cells=[cell])
        )

    def _build_materials(self, **kwargs: Any) -> MaterialsModel:
        """Build the materials model for this template.

        The base implementation returns an empty materials set (the base
        geometry is void). Subclasses override this to emit materials that
        match their geometry.

        Args:
            **kwargs: Additional template parameters

        Returns:
            A valid ``MaterialsModel``.
        """
        return MaterialsModel(materials=[])

    def _build_xml(
        self,
        particles: int,
        batches: int,
        inactive: int,
        **kwargs: Any,
    ) -> ET.Element:
        """Build the XML structure. Override in subclasses.

        Args:
            particles: Number of particles
            batches: Number of batches
            inactive: Number of inactive batches
            **kwargs: Additional parameters

        Returns:
            Root XML element
        """
        raise NotImplementedError("Subclasses must implement _build_xml")


def _shielded_sphere() -> tuple[GeometryModel, MaterialsModel]:
    """A point source inside a bounded sphere of water shielding."""
    sphere = Sphere(id=1, name="shield_outer", r=50.0, boundary_type="vacuum")
    cell = Cell(
        id=1,
        name="shield",
        region=HalfSpace(surface_id=1, side="-"),
        fill_material_id=1,
    )
    geom = GeometryModel(
        surfaces=[sphere], root_universe=Universe(id=1, cells=[cell])
    )
    water = Material(
        id=1,
        name="Water",
        density_g_per_cc=1.0,
        nuclides=[
            NuclideSpec(name="H1", fraction=0.1119),
            NuclideSpec(name="O16", fraction=0.8881),
        ],
    )
    return geom, MaterialsModel(materials=[water])


class CriticalityTemplate(ConfigurationTemplate):
    """Template for criticality (eigenvalue) calculations."""

    def __init__(self) -> None:
        metadata = TemplateMetadata(
            name="Criticality",
            template_type=TemplateType.CRITICALITY,
            description="Eigenvalue calculation for criticality analysis",
            default_particles=10000,
            default_batches=100,
            default_inactive=10,
        )
        super().__init__(metadata)

    def _build_xml(
        self,
        particles: int,
        batches: int,
        inactive: int,
        **kwargs: Any,
    ) -> ET.Element:
        root = ET.Element("settings")

        run_mode = ET.SubElement(root, "run_mode")
        run_mode.text = "eigenvalue"

        batches_elem = ET.SubElement(root, "batches")
        batches_elem.text = str(batches)

        inactive_elem = ET.SubElement(root, "inactive")
        inactive_elem.text = str(inactive)

        particles_elem = ET.SubElement(root, "particles")
        particles_elem.text = str(particles)

        # Source distribution
        source = ET.SubElement(root, "source")
        space = ET.SubElement(source, "space", type="box")
        params = ET.SubElement(space, "parameters")
        params.text = kwargs.get("source_box", "-10 -10 -10 10 10 10")

        return root

    def _build_geometry(self, **kwargs: Any) -> GeometryModel:
        return godiva.build()[0]

    def _build_materials(self, **kwargs: Any) -> MaterialsModel:
        return godiva.build()[1]


class FixedSourceTemplate(ConfigurationTemplate):
    """Template for fixed source calculations."""

    def __init__(self) -> None:
        metadata = TemplateMetadata(
            name="Fixed Source",
            template_type=TemplateType.FIXED_SOURCE,
            description="Fixed source calculation for shielding/dosimetry",
            default_particles=100000,
            default_batches=10,
            default_inactive=0,
        )
        super().__init__(metadata)

    def _build_xml(
        self,
        particles: int,
        batches: int,
        inactive: int,
        **kwargs: Any,
    ) -> ET.Element:
        root = ET.Element("settings")

        run_mode = ET.SubElement(root, "run_mode")
        run_mode.text = "fixed source"

        batches_elem = ET.SubElement(root, "batches")
        batches_elem.text = str(batches)

        particles_elem = ET.SubElement(root, "particles")
        particles_elem.text = str(particles)

        # Source distribution
        source = ET.SubElement(root, "source")
        space = ET.SubElement(source, "space", type="point")
        params = ET.SubElement(space, "parameters")
        params.text = kwargs.get("source_position", "0 0 0")

        # Energy
        energy = ET.SubElement(source, "energy", type="discrete")
        energy_params = ET.SubElement(energy, "parameters")
        energy_params.text = kwargs.get("source_energy", "14.0e6 1.0")

        return root

    def _build_geometry(self, **kwargs: Any) -> GeometryModel:
        return _shielded_sphere()[0]

    def _build_materials(self, **kwargs: Any) -> MaterialsModel:
        return _shielded_sphere()[1]


class ShieldingTemplate(ConfigurationTemplate):
    """Template for shielding calculations."""

    def __init__(self) -> None:
        metadata = TemplateMetadata(
            name="Shielding",
            template_type=TemplateType.SHIELDING,
            description="Radiation shielding analysis with variance reduction",
            default_particles=1000000,
            default_batches=10,
            default_inactive=0,
        )
        super().__init__(metadata)

    def _build_xml(
        self,
        particles: int,
        batches: int,
        inactive: int,
        **kwargs: Any,
    ) -> ET.Element:
        root = ET.Element("settings")

        run_mode = ET.SubElement(root, "run_mode")
        run_mode.text = "fixed source"

        batches_elem = ET.SubElement(root, "batches")
        batches_elem.text = str(batches)

        particles_elem = ET.SubElement(root, "particles")
        particles_elem.text = str(particles)

        # Source
        source = ET.SubElement(root, "source")
        space = ET.SubElement(source, "space", type="point")
        params = ET.SubElement(space, "parameters")
        params.text = kwargs.get("source_position", "0 0 0")

        # Variance reduction - survival biasing
        if kwargs.get("survival_biasing", True):
            survival = ET.SubElement(root, "survival_biasing")
            survival.text = "true"

        # Cutoff
        cutoff = ET.SubElement(root, "cutoff")
        weight = ET.SubElement(cutoff, "weight")
        weight.text = str(kwargs.get("weight_cutoff", 0.25))

        return root

    def _build_geometry(self, **kwargs: Any) -> GeometryModel:
        return _shielded_sphere()[0]

    def _build_materials(self, **kwargs: Any) -> MaterialsModel:
        return _shielded_sphere()[1]


class ReactorPinTemplate(ConfigurationTemplate):
    """Template for reactor pin cell calculations."""

    def __init__(self) -> None:
        metadata = TemplateMetadata(
            name="Reactor Pin",
            template_type=TemplateType.REACTOR_PIN,
            description="Single pin cell criticality calculation",
            default_particles=10000,
            default_batches=150,
            default_inactive=50,
        )
        super().__init__(metadata)

    def _build_xml(
        self,
        particles: int,
        batches: int,
        inactive: int,
        **kwargs: Any,
    ) -> ET.Element:
        root = ET.Element("settings")

        run_mode = ET.SubElement(root, "run_mode")
        run_mode.text = "eigenvalue"

        batches_elem = ET.SubElement(root, "batches")
        batches_elem.text = str(batches)

        inactive_elem = ET.SubElement(root, "inactive")
        inactive_elem.text = str(inactive)

        particles_elem = ET.SubElement(root, "particles")
        particles_elem.text = str(particles)

        # Source for pin cell
        pin_radius = kwargs.get("pin_radius", 0.39)
        pin_height = kwargs.get("pin_height", 200.0)

        source = ET.SubElement(root, "source")
        space = ET.SubElement(source, "space", type="cylindrical")
        params = ET.SubElement(space, "parameters")
        params.text = (
            f"0 0 -{pin_height / 2} 0 0 {pin_height / 2} 0 {pin_radius}"
        )

        return root

    def _build_geometry(self, **kwargs: Any) -> GeometryModel:
        return pwr_pin.build()[0]

    def _build_materials(self, **kwargs: Any) -> MaterialsModel:
        return pwr_pin.build()[1]


class DepletionTemplate(ConfigurationTemplate):
    """Template for depletion (burnup) transport settings.

    Emits the eigenvalue transport settings for a depletion calculation.
    The burnup schedule itself (timesteps, power, and depletion chain) is
    configured through OpenMC's Python depletion API, not settings.xml.
    """

    def __init__(self) -> None:
        metadata = TemplateMetadata(
            name="Depletion",
            template_type=TemplateType.DEPLETION,
            description=(
                "Eigenvalue transport settings for a depletion/burnup "
                "calculation (burnup schedule set via the OpenMC Python API)"
            ),
            default_particles=10000,
            default_batches=100,
            default_inactive=20,
        )
        super().__init__(metadata)

    def _build_xml(
        self,
        particles: int,
        batches: int,
        inactive: int,
        **kwargs: Any,
    ) -> ET.Element:
        root = ET.Element("settings")

        run_mode = ET.SubElement(root, "run_mode")
        run_mode.text = "eigenvalue"

        batches_elem = ET.SubElement(root, "batches")
        batches_elem.text = str(batches)

        inactive_elem = ET.SubElement(root, "inactive")
        inactive_elem.text = str(inactive)

        particles_elem = ET.SubElement(root, "particles")
        particles_elem.text = str(particles)

        # Source distribution
        source = ET.SubElement(root, "source")
        space = ET.SubElement(source, "space", type="box")
        params = ET.SubElement(space, "parameters")
        params.text = kwargs.get("source_box", "-10 -10 -10 10 10 10")

        return root

    def _build_geometry(self, **kwargs: Any) -> GeometryModel:
        return godiva.build()[0]

    def _build_materials(self, **kwargs: Any) -> MaterialsModel:
        return godiva.build()[1]


class TemplateRegistry:
    """Registry for configuration templates."""

    def __init__(self) -> None:
        """Initialize the registry with built-in templates."""
        self._templates: dict[str, ConfigurationTemplate] = {}
        self._register_builtin_templates()

    def _register_builtin_templates(self) -> None:
        """Register built-in templates."""
        self.register(CriticalityTemplate())
        self.register(FixedSourceTemplate())
        self.register(ShieldingTemplate())
        self.register(ReactorPinTemplate())
        self.register(DepletionTemplate())

    def register(self, template: ConfigurationTemplate) -> None:
        """Register a template.

        Args:
            template: Template to register
        """
        self._templates[template.metadata.template_type.value] = template

    def get(self, template_type: str | TemplateType) -> ConfigurationTemplate:
        """Get a template by type.

        Args:
            template_type: Template type identifier

        Returns:
            Template instance

        Raises:
            KeyError: If template not found
        """
        if isinstance(template_type, TemplateType):
            template_type = template_type.value

        if template_type not in self._templates:
            available = list(self._templates.keys())
            raise KeyError(
                f"Template '{template_type}' not found. Available: {available}"
            )

        return self._templates[template_type]

    def list_templates(self) -> list[TemplateMetadata]:
        """List all registered templates.

        Returns:
            List of template metadata
        """
        return [t.metadata for t in self._templates.values()]


# Global registry instance
_registry = TemplateRegistry()


def get_template(template_type: str | TemplateType) -> ConfigurationTemplate:
    """Get a template from the global registry.

    Args:
        template_type: Template type identifier

    Returns:
        Template instance
    """
    return _registry.get(template_type)


def list_templates() -> list[TemplateMetadata]:
    """List all available templates.

    Returns:
        List of template metadata
    """
    return _registry.list_templates()
