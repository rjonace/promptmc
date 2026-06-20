"""Schema validation for OpenMC configuration files using Pydantic."""

from __future__ import annotations

import contextlib
import xml.etree.ElementTree as ET  # nosec B405
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from defusedxml.ElementTree import parse as defused_parse
from pydantic import (
    BaseModel,
    Field,
    ValidationError,
    model_validator,
)

from promptmc._typing import PathLike
from promptmc.geometry.xml_serializer import (
    parse_geometry_xml,
    parse_materials_xml,
)


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
        """All issues with ERROR severity."""
        return [i for i in self.issues if i.severity == SchemaSeverity.ERROR]

    @property
    def warnings(self) -> list[SchemaIssue]:
        """All issues with WARNING severity."""
        return [i for i in self.issues if i.severity == SchemaSeverity.WARNING]


class SchemaValidator:
    """Validates OpenMC XML files against Pydantic schemas."""

    def validate_settings(self, xml_path: PathLike) -> SchemaValidationResult:
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
        if root is None:
            issues.append(
                SchemaIssue(
                    severity=SchemaSeverity.ERROR,
                    field="<root>",
                    message="XML document has no root element",
                    file_path=str(xml_path),
                )
            )
            return SchemaValidationResult(is_valid=False, issues=issues)

        data = self._settings_xml_to_dict(root)

        self._run_pydantic(SettingsSchema, data, issues, xml_path)

        return SchemaValidationResult(is_valid=not issues, issues=issues)

    def validate_materials(self, xml_path: PathLike) -> SchemaValidationResult:
        """Validate a materials.xml file against the ``MaterialsModel``."""
        return self._validate_with_parser(parse_materials_xml, xml_path)

    def validate_geometry(self, xml_path: PathLike) -> SchemaValidationResult:
        """Validate a geometry.xml file against the ``GeometryModel``.

        Delegates to ``parse_geometry_xml``, so this enforces the full CSG
        contract (unique IDs, no dangling surface references, boundedness),
        which is strictly more than the previous flat cell-ID check.
        """
        return self._validate_with_parser(parse_geometry_xml, xml_path)

    def _validate_with_parser(
        self,
        parser: Callable[[PathLike], object],
        xml_path: PathLike,
    ) -> SchemaValidationResult:
        """Run an XML-to-model parser and convert failures to issues."""
        xml_path = Path(xml_path)
        issues: list[SchemaIssue] = []

        try:
            parser(xml_path)
        except ET.ParseError as e:
            issues.append(
                SchemaIssue(
                    severity=SchemaSeverity.ERROR,
                    field="<root>",
                    message=f"Invalid XML: {e}",
                    file_path=str(xml_path),
                )
            )
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
        except ValueError as e:
            issues.append(
                SchemaIssue(
                    severity=SchemaSeverity.ERROR,
                    field="<root>",
                    message=str(e),
                    file_path=str(xml_path),
                )
            )

        return SchemaValidationResult(is_valid=not issues, issues=issues)

    def _run_pydantic(
        self,
        schema_cls: type,
        kwargs: dict[str, Any],
        issues: list[SchemaIssue],
        xml_path: PathLike,
    ) -> None:
        """Run Pydantic validation and append any issues."""
        try:
            schema_cls(**kwargs)
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

    def validate_directory(self, directory: PathLike) -> SchemaValidationResult:
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
            is_valid=not any(
                i.severity == SchemaSeverity.ERROR for i in all_issues
            ),
            issues=all_issues,
        )

    @staticmethod
    def _settings_xml_to_dict(root: ET.Element) -> dict[str, Any]:
        """Convert settings.xml root element to a flat dict."""
        data: dict[str, Any] = {}

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
    lines.append(
        f"Issues: {len(result.errors)} error(s), {len(result.warnings)} warning(s)"
    )
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
                f" ({issue.file_path}:{issue.field})"
                if issue.file_path
                else f" ({issue.field})"
            )
            lines.append(f"{marker}{location}")
            lines.append(f"        {issue.message}")
            lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)
