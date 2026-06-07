"""Materials schema and validation definitions."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator, model_validator

NUCLIDE_REGEX = re.compile(r"^[A-Za-z][A-Za-z0-9-]*$")


class NuclideSpec(BaseModel):
    """Specifies a nuclide and its weight/atom fraction."""

    name: str
    fraction: float = Field(gt=0)

    @field_validator("name")
    @classmethod
    def validate_nuclide_name(cls, v: str) -> str:
        """Validate nuclide name structure (e.g. U235, H-1, O16)."""
        if not NUCLIDE_REGEX.match(v):
            raise ValueError(
                f"Nuclide name must be alphanumeric with optional dashes, got: '{v}'"
            )
        return v


class Material(BaseModel):
    """A material definition composed of nuclides/elements and a density."""

    id: int | None = None
    name: str = ""
    density_g_per_cc: float = Field(gt=0)
    nuclides: list[NuclideSpec]


class MaterialsModel(BaseModel):
    """A collection of materials."""

    materials: list[Material]

    @model_validator(mode="after")
    def validate_materials(self) -> MaterialsModel:
        """Ensure all material IDs are unique."""
        mat_ids = set()
        for m in self.materials:
            if m.id is not None:
                if m.id in mat_ids:
                    raise ValueError(f"Duplicate material ID: {m.id}")
                mat_ids.add(m.id)
        return self
