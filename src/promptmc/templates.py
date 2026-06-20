"""Configuration templates for OpenMC simulations."""

from __future__ import annotations

import xml.etree.ElementTree as ET  # nosec B405
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from promptmc._typing import PathLike
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
        """Render template to output path.

        Args:
            output_path: Where to write the rendered template
            particles: Override default particles
            batches: Override default batches
            inactive: Override default inactive batches
            **kwargs: Additional template parameters

        Returns:
            Path to rendered file
        """
        output_path = Path(output_path)
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

        return write_xml_with_provenance(root, output_path)

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
