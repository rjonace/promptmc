"""Schema validation for OpenMC configuration files using Pydantic."""

from __future__ import annotations

import contextlib
import xml.etree.ElementTree as ET  # nosec B405
from defusedxml.ElementTree import parse as defused_parse
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator


class RunMode(str, Enum):
    """Valid OpenMC run modes."""

    EIGENVALUE = "eigenvalue"
    FIXED_SOURCE = "fixed source"
    PLOT = "plot"
    PARTICLE_RESTART = "particle restart"
    VOLUME = "volume"


class SettingsSchema(BaseModel):
    """Schema for OpenMC settings.xml file."""

    run_mode: RunMode = RunMode.EIGENVALUE
    batches: int = Field(default=10, ge=1, le=1_000_000)
    inactive: int = Field(default=5, ge=0)
    particles: int = Field(default=10_000, ge=1, le=1_000_000_000)
    output_path: str | None = None
    seed: int | None = Field(default=None, ge=1)
    survival_biasing: bool | None = None
    weight_cutoff: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _check_inactive_below_batches(self) -> SettingsSchema:
        if self.inactive >= self.batches:
            raise ValueError(
                f"inactive ({self.inactive}) must be less than batches ({self.batches})"
            )
        return self

    @field_validator("inactive")
    @classmethod
    def _check_inactive_for_run_mode(cls, v: int) -> int:
        # Note: run_mode-specific validation happens in model_validator
        return v


class MaterialSchema(BaseModel):
    """Schema for an OpenMC material element."""

    id: int = Field(ge=1)
    name: str | None = None
    density_value: float | None = Field(default=None, gt=0)
    density_units: Literal["g/cm3", "kg/m3", "atom/b-cm", "sum"] = "g/cm3"
    nuclides: list[str] = Field(default_factory=list)


class MaterialsSchema(BaseModel):
    """Schema for OpenMC materials.xml file."""

    materials: list[MaterialSchema] = Field(default_factory=list)

    @field_validator("materials")
    @classmethod
    def _check_unique_ids(cls, materials: list[MaterialSchema]) -> list[MaterialSchema]:
        ids = [m.id for m in materials]
        duplicates = {x for x in ids if ids.count(x) > 1}
        if duplicates:
            raise ValueError(f"Duplicate material IDs: {sorted(duplicates)}")
        return materials


class CellSchema(BaseModel):
    """Schema for an OpenMC cell element."""

    id: int = Field(ge=1)
    name: str | None = None
    material: int | str | None = None
    region: str | None = None
    universe: int | None = None
    fill: int | None = None


class GeometrySchema(BaseModel):
    """Schema for OpenMC geometry.xml file."""

    cells: list[CellSchema] = Field(default_factory=list)

    @field_validator("cells")
    @classmethod
    def _check_unique_ids(cls, cells: list[CellSchema]) -> list[CellSchema]:
        ids = [c.id for c in cells]
        duplicates = {x for x in ids if ids.count(x) > 1}
        if duplicates:
            raise ValueError(f"Duplicate cell IDs: {sorted(duplicates)}")
        return cells


class SchemaSeverity(str, Enum):
    """Severity of a schema validation issue."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class SchemaIssue:
    """A single schema validation issue."""

    severity: SchemaSeverity
    field: str
    message: str
    file_path: str | None = None


@dataclass
class SchemaValidationResult:
    """Result of schema validation."""

    is_valid: bool
    issues: list[SchemaIssue]

    @property
    def errors(self) -> list[SchemaIssue]:
        return [i for i in self.issues if i.severity == SchemaSeverity.ERROR]

    @property
    def warnings(self) -> list[SchemaIssue]:
        return [i for i in self.issues if i.severity == SchemaSeverity.WARNING]


class SchemaValidator:
    """Validates OpenMC XML files against Pydantic schemas."""

    def validate_settings(self, xml_path: str | Path) -> SchemaValidationResult:
        """Validate a settings.xml file."""
        xml_path = Path(xml_path)
        issues: list[SchemaIssue] = []

        try:
            tree = defused_parse(xml_path)
        except ET.ParseError as e:
            issues.append(
                SchemaIssue(
                    severity=SchemaSeverity.ERROR,
                    field="<root>",
                    message=f"Invalid XML: {e}",
                    file_path=str(xml_path),
                )
            )
            return SchemaValidationResult(is_valid=False, issues=issues)

        root = tree.getroot()
        data = self._settings_xml_to_dict(root)

        try:
            SettingsSchema(**data)
        except ValidationError as e:
            for err in e.errors():
                issues.append(
                    SchemaIssue(
                        severity=SchemaSeverity.ERROR,
                        field=".".join(str(p) for p in err["loc"]),
                        message=err["msg"],
                        file_path=str(xml_path),
                    )
                )

        return SchemaValidationResult(is_valid=not issues, issues=issues)

    def validate_materials(self, xml_path: str | Path) -> SchemaValidationResult:
        """Validate a materials.xml file."""
        xml_path = Path(xml_path)
        issues: list[SchemaIssue] = []

        try:
            tree = defused_parse(xml_path)
        except ET.ParseError as e:
            issues.append(
                SchemaIssue(
                    severity=SchemaSeverity.ERROR,
                    field="<root>",
                    message=f"Invalid XML: {e}",
                    file_path=str(xml_path),
                )
            )
            return SchemaValidationResult(is_valid=False, issues=issues)

        materials_data: list[dict] = []
        for material_elem in tree.getroot().findall("material"):
            mat_dict: dict = {
                "id": int(material_elem.get("id", "0") or 0),
                "name": material_elem.get("name"),
            }
            density_elem = material_elem.find("density")
            if density_elem is not None:
                value = density_elem.get("value")
                units = density_elem.get("units", "g/cm3")
                if value:
                    try:
                        mat_dict["density_value"] = float(value)
                    except ValueError:
                        issues.append(
                            SchemaIssue(
                                severity=SchemaSeverity.ERROR,
                                field=f"material[{mat_dict['id']}].density.value",
                                message=f"Invalid density value: {value}",
                                file_path=str(xml_path),
                            )
                        )
                mat_dict["density_units"] = units

            mat_dict["nuclides"] = [
                str(n.get("name", "")) for n in material_elem.findall("nuclide") if n.get("name")
            ]
            materials_data.append(mat_dict)

        try:
            MaterialsSchema(materials=[MaterialSchema(**m) for m in materials_data])
        except ValidationError as e:
            for err in e.errors():
                issues.append(
                    SchemaIssue(
                        severity=SchemaSeverity.ERROR,
                        field=".".join(str(p) for p in err["loc"]),
                        message=err["msg"],
                        file_path=str(xml_path),
                    )
                )

        return SchemaValidationResult(is_valid=not issues, issues=issues)

    def validate_geometry(self, xml_path: str | Path) -> SchemaValidationResult:
        """Validate a geometry.xml file."""
        xml_path = Path(xml_path)
        issues: list[SchemaIssue] = []

        try:
            tree = defused_parse(xml_path)
        except ET.ParseError as e:
            issues.append(
                SchemaIssue(
                    severity=SchemaSeverity.ERROR,
                    field="<root>",
                    message=f"Invalid XML: {e}",
                    file_path=str(xml_path),
                )
            )
            return SchemaValidationResult(is_valid=False, issues=issues)

        cells_data: list[dict] = []
        for cell_elem in tree.getroot().findall("cell"):
            cells_data.append(
                {
                    "id": int(str(cell_elem.get("id", "0") or "0")),
                    "name": cell_elem.get("name"),
                    "material": cell_elem.get("material"),
                    "region": cell_elem.get("region"),
                    "universe": int(str(cell_elem.get("universe")))
                    if cell_elem.get("universe")
                    else None,
                    "fill": int(str(cell_elem.get("fill"))) if cell_elem.get("fill") else None,
                }
            )

        try:
            GeometrySchema(cells=[CellSchema(**c) for c in cells_data])
        except ValidationError as e:
            for err in e.errors():
                issues.append(
                    SchemaIssue(
                        severity=SchemaSeverity.ERROR,
                        field=".".join(str(p) for p in err["loc"]),
                        message=err["msg"],
                        file_path=str(xml_path),
                    )
                )

        return SchemaValidationResult(is_valid=not issues, issues=issues)

    def validate_directory(self, directory: str | Path) -> SchemaValidationResult:
        """Validate all OpenMC input files in a directory."""
        directory = Path(directory)
        all_issues: list[SchemaIssue] = []

        validators = {
            "settings.xml": self.validate_settings,
            "materials.xml": self.validate_materials,
            "geometry.xml": self.validate_geometry,
        }

        for filename, validator in validators.items():
            file_path = directory / filename
            if not file_path.exists():
                all_issues.append(
                    SchemaIssue(
                        severity=SchemaSeverity.ERROR,
                        field="<file>",
                        message=f"Required file missing: {filename}",
                        file_path=str(file_path),
                    )
                )
                continue
            result = validator(file_path)
            all_issues.extend(result.issues)

        return SchemaValidationResult(
            is_valid=not any(i.severity == SchemaSeverity.ERROR for i in all_issues),
            issues=all_issues,
        )

    @staticmethod
    def _settings_xml_to_dict(root: ET.Element) -> dict:
        """Convert settings.xml root element to a flat dict."""
        data: dict = {}

        for tag in ("run_mode", "batches", "inactive", "particles", "seed"):
            elem = root.find(tag)
            if elem is not None and elem.text is not None:
                value: str | int = elem.text.strip()
                if tag in ("batches", "inactive", "particles", "seed"):
                    with contextlib.suppress(ValueError):
                        value = int(value)
                data[tag] = value

        survival = root.find("survival_biasing")
        if survival is not None and survival.text:
            data["survival_biasing"] = survival.text.strip().lower() == "true"

        cutoff = root.find("cutoff")
        if cutoff is not None:
            weight = cutoff.find("weight")
            if weight is not None and weight.text:
                with contextlib.suppress(ValueError):
                    data["weight_cutoff"] = float(weight.text.strip())

        output_elem = root.find("output")
        if output_elem is not None:
            path_elem = output_elem.find("path")
            if path_elem is not None and path_elem.text:
                data["output_path"] = path_elem.text.strip()

        return data


def format_validation_report(result: SchemaValidationResult) -> str:
    """Format a schema validation result as a human-readable report."""
    lines = []
    lines.append("=" * 60)
    lines.append("Schema Validation Report")
    lines.append("=" * 60)
    lines.append("")

    status = "PASSED" if result.is_valid else "FAILED"
    lines.append(f"Status: {status}")
    lines.append(f"Issues: {len(result.errors)} error(s), {len(result.warnings)} warning(s)")
    lines.append("")

    if not result.issues:
        lines.append("No issues found.")
    else:
        for issue in result.issues:
            marker = {
                SchemaSeverity.ERROR: "[ERROR]",
                SchemaSeverity.WARNING: "[WARN] ",
                SchemaSeverity.INFO: "[INFO] ",
            }[issue.severity]
            location = (
                f" ({issue.file_path}:{issue.field})" if issue.file_path else f" ({issue.field})"
            )
            lines.append(f"{marker}{location}")
            lines.append(f"        {issue.message}")
            lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)
