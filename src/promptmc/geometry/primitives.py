"""CSG geometry primitives and model definition."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

BoundaryType = Literal[
    "transmission", "vacuum", "reflective", "periodic", "white"
]


class _SurfaceBase(BaseModel):
    id: int | None = None
    name: str = ""
    boundary_type: BoundaryType = "transmission"


class XPlane(_SurfaceBase):
    """An infinite plane perpendicular to the x-axis."""

    kind: Literal["x-plane"] = "x-plane"
    x0: float


class YPlane(_SurfaceBase):
    """An infinite plane perpendicular to the y-axis."""

    kind: Literal["y-plane"] = "y-plane"
    y0: float


class ZPlane(_SurfaceBase):
    """An infinite plane perpendicular to the z-axis."""

    kind: Literal["z-plane"] = "z-plane"
    z0: float


class Plane(_SurfaceBase):
    """An arbitrary 3D plane ax + by + cz = d."""

    kind: Literal["plane"] = "plane"
    a: float
    b: float
    c: float
    d: float


class Sphere(_SurfaceBase):
    """A sphere centered at (x0, y0, z0) with radius r."""

    kind: Literal["sphere"] = "sphere"
    x0: float = 0.0
    y0: float = 0.0
    z0: float = 0.0
    r: float = Field(gt=0)


class XCylinder(_SurfaceBase):
    """An infinite cylinder aligned with the x-axis."""

    kind: Literal["x-cylinder"] = "x-cylinder"
    y0: float = 0.0
    z0: float = 0.0
    r: float = Field(gt=0)


class YCylinder(_SurfaceBase):
    """An infinite cylinder aligned with the y-axis."""

    kind: Literal["y-cylinder"] = "y-cylinder"
    x0: float = 0.0
    z0: float = 0.0
    r: float = Field(gt=0)


class ZCylinder(_SurfaceBase):
    """An infinite cylinder aligned with the z-axis."""

    kind: Literal["z-cylinder"] = "z-cylinder"
    x0: float = 0.0
    y0: float = 0.0
    r: float = Field(gt=0)


Surface = Annotated[
    XPlane
    | YPlane
    | ZPlane
    | Plane
    | Sphere
    | XCylinder
    | YCylinder
    | ZCylinder,
    Field(discriminator="kind"),
]


class HalfSpace(BaseModel):
    """A halfspace defined by a surface and side (+ or -)."""

    kind: Literal["halfspace"] = "halfspace"
    surface_id: int
    side: Literal["+", "-"]


class Intersection(BaseModel):
    """An intersection of multiple regions (AND)."""

    kind: Literal["intersection"] = "intersection"
    nodes: list[Region]


class Union_(BaseModel):
    """A union of multiple regions (OR)."""

    kind: Literal["union"] = "union"
    nodes: list[Region]


class Complement(BaseModel):
    """A complement of a region (NOT)."""

    kind: Literal["complement"] = "complement"
    node: Region


Region = Annotated[
    HalfSpace | Intersection | Union_ | Complement,
    Field(discriminator="kind"),
]

# Rebuild models to resolve the forward references in Region
Intersection.model_rebuild()
Union_.model_rebuild()
Complement.model_rebuild()


class Cell(BaseModel):
    """A bounded region filled with a material or universe."""

    id: int | None = None
    name: str = ""
    region: Region
    fill_material_id: int | None = None
    fill_universe_id: int | None = None


Cell.model_rebuild()


class Universe(BaseModel):
    """A collection of cells."""

    id: int | None = None
    cells: list[Cell]


class GeometryModel(BaseModel):
    """A complete CSG geometry description."""

    surfaces: list[Surface]
    root_universe: Universe

    @model_validator(mode="after")
    def validate_geometry(self) -> GeometryModel:
        """Validate CSG structure (unique IDs, correct references, boundedness)."""
        # Unique surface IDs
        surf_ids = set()
        for s in self.surfaces:
            if s.id is not None:
                if s.id in surf_ids:
                    raise ValueError(f"Duplicate surface ID: {s.id}")
                surf_ids.add(s.id)

        # Unique cell IDs
        cell_ids = set()
        for cell in self.root_universe.cells:
            if cell.id is not None:
                if cell.id in cell_ids:
                    raise ValueError(f"Duplicate cell ID: {cell.id}")
                cell_ids.add(cell.id)

        # Verify that all half-spaces reference a valid surface ID
        known_surf_ids = {s.id for s in self.surfaces if s.id is not None}

        def check_region(r: Region) -> None:
            if r.kind == "halfspace":
                if r.surface_id not in known_surf_ids:
                    raise ValueError(
                        f"Dangling surface reference: surface {r.surface_id} does not exist"
                    )
            elif r.kind in ("intersection", "union"):
                for node in r.nodes:
                    check_region(node)
            elif r.kind == "complement":
                check_region(r.node)

        if not self.root_universe.cells:
            raise ValueError("Root universe must have at least one cell")

        for cell in self.root_universe.cells:
            check_region(cell.region)

        # Bounded geometry: at least one surface has non-transmission boundary
        has_outer = any(
            s.boundary_type != "transmission" for s in self.surfaces
        )
        if not has_outer:
            raise ValueError(
                "Geometry must be bounded (at least one surface boundary must not be 'transmission')"
            )

        return self
