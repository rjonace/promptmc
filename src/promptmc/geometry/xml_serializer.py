"""Dual-mode XML serializer/deserializer for CSG geometries and materials."""

from __future__ import annotations

import xml.etree.ElementTree as ET  # nosec B405
from pathlib import Path
from typing import Any

from defusedxml.ElementTree import parse as defused_parse
from pydantic import TypeAdapter

from promptmc._typing import PathLike
from promptmc.geometry.materials import Material, MaterialsModel
from promptmc.geometry.primitives import (
    Cell,
    Complement,
    GeometryModel,
    HalfSpace,
    Intersection,
    Region,
    Surface,
    Union_,
    Universe,
)

_SURFACE_ADAPTER: TypeAdapter[Surface] = TypeAdapter(Surface)

# Guarded openmc import
try:
    import openmc as _openmc

    openmc: Any = _openmc
    _OPENMC_AVAILABLE = hasattr(openmc, "Geometry")
except ImportError:
    _OPENMC_AVAILABLE = False


def _to_openmc_surface(s: Surface) -> Any:
    """Map a promptmc Surface model to an openmc.Surface object."""
    if not _OPENMC_AVAILABLE:
        raise RuntimeError("OpenMC package is not available.")

    if s.kind == "x-plane":
        return openmc.XPlane(
            x0=s.x0, boundary_type=s.boundary_type, surface_id=s.id
        )
    if s.kind == "y-plane":
        return openmc.YPlane(
            y0=s.y0, boundary_type=s.boundary_type, surface_id=s.id
        )
    if s.kind == "z-plane":
        return openmc.ZPlane(
            z0=s.z0, boundary_type=s.boundary_type, surface_id=s.id
        )
    if s.kind == "plane":
        return openmc.Plane(
            a=s.a,
            b=s.b,
            c=s.c,
            d=s.d,
            boundary_type=s.boundary_type,
            surface_id=s.id,
        )
    if s.kind == "sphere":
        return openmc.Sphere(
            x0=s.x0,
            y0=s.y0,
            z0=s.z0,
            r=s.r,
            boundary_type=s.boundary_type,
            surface_id=s.id,
        )
    if s.kind == "x-cylinder":
        return openmc.XCylinder(
            y0=s.y0,
            z0=s.z0,
            r=s.r,
            boundary_type=s.boundary_type,
            surface_id=s.id,
        )
    if s.kind == "y-cylinder":
        return openmc.YCylinder(
            x0=s.x0,
            z0=s.z0,
            r=s.r,
            boundary_type=s.boundary_type,
            surface_id=s.id,
        )
    if s.kind == "z-cylinder":
        return openmc.ZCylinder(
            x0=s.x0,
            y0=s.y0,
            r=s.r,
            boundary_type=s.boundary_type,
            surface_id=s.id,
        )
    raise ValueError(f"Unknown surface kind: {s.kind}")


def _to_openmc_region(r: Region, surf_map: dict[int, Any]) -> Any:
    """Map a promptmc Region model to an openmc.Region object."""
    if r.kind == "halfspace":
        s = surf_map[r.surface_id]
        return -s if r.side == "-" else +s
    if r.kind == "intersection":
        return openmc.Intersection(
            [_to_openmc_region(n, surf_map) for n in r.nodes]
        )
    if r.kind == "union":
        return openmc.Union([_to_openmc_region(n, surf_map) for n in r.nodes])
    if r.kind == "complement":
        return ~_to_openmc_region(r.node, surf_map)
    raise ValueError(f"Unknown region kind: {r.kind}")


def _to_openmc_material(m: Material) -> Any:
    """Map a promptmc Material model to an openmc.Material object."""
    if not _OPENMC_AVAILABLE:
        raise RuntimeError("OpenMC package is not available.")

    mat = openmc.Material(material_id=m.id, name=m.name)
    mat.set_density("g/cm3", m.density_g_per_cc)
    for n in m.nuclides:
        mat.add_nuclide(n.name, n.fraction, percent_type="wo")
    return mat


def to_openmc_geometry(model: GeometryModel) -> Any:
    """Convert promptmc GeometryModel to openmc.Geometry."""
    if not _OPENMC_AVAILABLE:
        raise RuntimeError("OpenMC package is not available.")

    surf_map = {}
    for s in model.surfaces:
        if s.id is not None:
            surf_map[s.id] = _to_openmc_surface(s)

    openmc_cells = []
    for c in model.root_universe.cells:
        region = _to_openmc_region(c.region, surf_map)
        cell = openmc.Cell(cell_id=c.id, name=c.name, region=region)
        if c.fill_material_id is not None:
            cell.fill = openmc.Material(material_id=c.fill_material_id)
        elif c.fill_universe_id is not None:
            cell.fill = openmc.Universe(universe_id=c.fill_universe_id)
        openmc_cells.append(cell)

    univ = openmc.Universe(
        universe_id=model.root_universe.id, cells=openmc_cells
    )
    return openmc.Geometry(univ)


# Fallback XML serialization logic
def _region_to_string(r: Region) -> str:
    """Convert Region tree into standard OpenMC region expression string."""
    if r.kind == "halfspace":
        return f"{r.side}{r.surface_id}"
    if r.kind == "intersection":
        parts = []
        for n in r.nodes:
            s = _region_to_string(n)
            if n.kind == "union":
                s = f"({s})"
            parts.append(s)
        return " ".join(parts)
    if r.kind == "union":
        parts = []
        for n in r.nodes:
            s = _region_to_string(n)
            if n.kind == "intersection":
                s = f"({s})"
            parts.append(s)
        return " | ".join(parts)
    if r.kind == "complement":
        s = _region_to_string(r.node)
        if r.node.kind in ("intersection", "union"):
            s = f"({s})"
        return f"~{s}"
    raise ValueError(f"Unknown region kind: {r.kind}")


def _geometry_model_to_dict(model: GeometryModel) -> dict[str, Any]:
    """Convert GeometryModel to intermediate dictionary matching OpenMC XML tags."""
    surfaces_list = []
    for s in model.surfaces:
        coeffs_str = ""
        if s.kind == "x-plane":
            coeffs_str = str(s.x0)
        elif s.kind == "y-plane":
            coeffs_str = str(s.y0)
        elif s.kind == "z-plane":
            coeffs_str = str(s.z0)
        elif s.kind == "plane":
            coeffs_str = f"{s.a} {s.b} {s.c} {s.d}"
        elif s.kind == "sphere":
            coeffs_str = f"{s.x0} {s.y0} {s.z0} {s.r}"
        elif s.kind in ("x-cylinder", "y-cylinder", "z-cylinder"):
            if s.kind == "x-cylinder":
                coeffs_str = f"{s.y0} {s.z0} {s.r}"
            elif s.kind == "y-cylinder":
                coeffs_str = f"{s.x0} {s.z0} {s.r}"
            else:
                coeffs_str = f"{s.x0} {s.y0} {s.r}"

        s_dict: dict[str, Any] = {
            "@id": str(s.id),
            "@type": s.kind,
            "@coeffs": coeffs_str,
        }
        if s.name:
            s_dict["@name"] = s.name
        if s.boundary_type != "transmission":
            s_dict["@boundary"] = s.boundary_type
        surfaces_list.append(s_dict)

    cells_list = []
    for c in model.root_universe.cells:
        c_dict: dict[str, Any] = {
            "@id": str(c.id),
            "@region": _region_to_string(c.region),
        }
        if c.name:
            c_dict["@name"] = c.name
        if c.fill_material_id is not None:
            c_dict["@material"] = str(c.fill_material_id)
        elif c.fill_universe_id is not None:
            c_dict["@fill"] = str(c.fill_universe_id)
        else:
            c_dict["@material"] = "void"
        cells_list.append(c_dict)

    return {
        "surface": surfaces_list,
        "cell": cells_list,
    }


def _materials_model_to_dict(model: MaterialsModel) -> dict[str, Any]:
    """Convert MaterialsModel to intermediate dictionary matching OpenMC XML tags."""
    materials_list = []
    for m in model.materials:
        m_dict: dict[str, Any] = {
            "@id": str(m.id),
        }
        if m.name:
            m_dict["@name"] = m.name
        m_dict["density"] = {
            "@value": str(m.density_g_per_cc),
            "@units": "g/cm3",
        }
        m_dict["nuclide"] = [
            {
                "@name": n.name,
                "@wo": str(n.fraction),
            }
            for n in m.nuclides
        ]
        materials_list.append(m_dict)
    return {
        "material": materials_list,
    }


def _dict_to_xml(d: dict[str, Any], root_tag: str) -> ET.Element:
    """Helper to convert structured dictionary to safe ET.Element."""
    root = ET.Element(root_tag)

    def _build(parent: ET.Element, key: str, value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                _build(parent, key, item)
        elif isinstance(value, dict):
            elem = ET.SubElement(parent, key)
            for k, v in value.items():
                if k.startswith("@"):
                    elem.set(k[1:], str(v))
                else:
                    _build(elem, k, v)
        else:
            elem = ET.SubElement(parent, key)
            elem.text = str(value)

    for k, v in d.items():
        if k.startswith("@"):
            root.set(k[1:], str(v))
        else:
            _build(root, k, v)
    return root


def serialize_geometry(model: GeometryModel, path: PathLike) -> None:
    """Serialize GeometryModel to XML (uses OpenMC if available, falls back to raw XML write)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if _OPENMC_AVAILABLE:
        geom = to_openmc_geometry(model)
        geom.export_to_xml(str(path))
    else:
        d = _geometry_model_to_dict(model)
        root = _dict_to_xml(d, "geometry")
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        tree.write(path, encoding="utf-8", xml_declaration=True)


def serialize_materials(model: MaterialsModel, path: PathLike) -> None:
    """Serialize MaterialsModel to XML (uses OpenMC if available, falls back to raw XML write)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if _OPENMC_AVAILABLE:
        mats = openmc.Materials()
        for m in model.materials:
            mats.append(_to_openmc_material(m))
        mats.export_to_xml(str(path))
    else:
        d = _materials_model_to_dict(model)
        root = _dict_to_xml(d, "materials")
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        tree.write(path, encoding="utf-8", xml_declaration=True)


# ---------------------------------------------------------------------------
# Deserialization: OpenMC XML -> promptmc models
# ---------------------------------------------------------------------------

# Ordered coefficient fields per surface type (reverse of _geometry_model_to_dict).
_SURFACE_COEFF_FIELDS: dict[str, tuple[str, ...]] = {
    "x-plane": ("x0",),
    "y-plane": ("y0",),
    "z-plane": ("z0",),
    "plane": ("a", "b", "c", "d"),
    "sphere": ("x0", "y0", "z0", "r"),
    "x-cylinder": ("y0", "z0", "r"),
    "y-cylinder": ("x0", "z0", "r"),
    "z-cylinder": ("x0", "y0", "r"),
}


def _opt_int(value: str | None) -> int | None:
    """Parse an optional integer attribute, treating empty as absent."""
    return int(value) if value else None


def _tokenize_region(expr: str) -> list[str]:
    """Split an OpenMC region expression into tokens.

    Tokens are halfspaces (``-1``, ``+2``, ``3``) and the operators
    ``(``, ``)``, ``|`` (union) and ``~`` (complement). Whitespace between
    operands denotes intersection.
    """
    tokens: list[str] = []
    i = 0
    n = len(expr)
    while i < n:
        c = expr[i]
        if c.isspace():
            i += 1
        elif c in "()|~":
            tokens.append(c)
            i += 1
        elif c in "+-" or c.isdigit():
            j = i + 1 if c in "+-" else i
            start = j
            while j < n and expr[j].isdigit():
                j += 1
            if j == start:
                raise ValueError(f"Unsupported region syntax: {expr!r}")
            tokens.append(expr[i:j])
            i = j
        else:
            raise ValueError(
                f"Unsupported region syntax near {c!r} in {expr!r}"
            )
    return tokens


class _RegionParser:
    """Recursive-descent parser for OpenMC region expressions.

    Grammar (precedence low -> high)::

        union        := intersection ('|' intersection)*
        intersection := unary (unary)*          # space-separated
        unary        := '~' unary | '(' union ')' | halfspace
        halfspace    := ['+'|'-'] integer
    """

    def __init__(self, tokens: list[str]) -> None:
        self._tokens = tokens
        self._pos = 0

    def parse(self) -> Region:
        if not self._tokens:
            raise ValueError("Empty region expression")
        region = self._union()
        if self._pos != len(self._tokens):
            raise ValueError(
                f"Unexpected trailing tokens in region: "
                f"{self._tokens[self._pos:]!r}"
            )
        return region

    def _peek(self) -> str | None:
        return (
            self._tokens[self._pos] if self._pos < len(self._tokens) else None
        )

    def _advance(self) -> str:
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def _union(self) -> Region:
        nodes = [self._intersection()]
        while self._peek() == "|":
            self._advance()
            nodes.append(self._intersection())
        if len(nodes) == 1:
            return nodes[0]
        return Union_(nodes=nodes)

    def _intersection(self) -> Region:
        nodes = [self._unary()]
        while self._peek() is not None and self._peek() not in ("|", ")"):
            nodes.append(self._unary())
        if len(nodes) == 1:
            return nodes[0]
        return Intersection(nodes=nodes)

    def _unary(self) -> Region:
        tok = self._peek()
        if tok is None:
            raise ValueError("Unexpected end of region expression")
        if tok == "~":
            self._advance()
            return Complement(node=self._unary())
        if tok == "(":
            self._advance()
            region = self._union()
            if self._peek() != ")":
                raise ValueError("Unbalanced parentheses in region expression")
            self._advance()
            return region
        if tok in ("|", ")"):
            raise ValueError(f"Unexpected token {tok!r} in region expression")
        return self._halfspace(self._advance())

    @staticmethod
    def _halfspace(token: str) -> HalfSpace:
        if token[0] in "+-":
            side = token[0]
            number = token[1:]
        else:
            side = "+"
            number = token
        try:
            surface_id = int(number)
        except ValueError as exc:
            raise ValueError(f"Unsupported region syntax: {token!r}") from exc
        return HalfSpace(surface_id=surface_id, side=side)  # type: ignore[arg-type]


def parse_region_string(expr: str) -> Region:
    """Parse an OpenMC region expression into a Region tree.

    Supports halfspaces, space-separated intersections, ``|`` unions,
    ``~`` complements and parentheses. Raises ``ValueError`` with a clear
    message for unsupported syntax.
    """
    return _RegionParser(_tokenize_region(expr)).parse()


def _surface_from_element(elem: ET.Element) -> Surface:
    """Build a Surface model from an OpenMC ``<surface>`` element."""
    stype = elem.get("type")
    if stype not in _SURFACE_COEFF_FIELDS:
        raise ValueError(f"Unsupported surface type: {stype!r}")

    fields = _SURFACE_COEFF_FIELDS[stype]
    raw_coeffs = (elem.get("coeffs") or "").split()
    if len(raw_coeffs) != len(fields):
        raise ValueError(
            f"Surface {elem.get('id')} of type {stype!r} expects "
            f"{len(fields)} coefficient(s), got {len(raw_coeffs)}"
        )
    try:
        coeffs = {
            name: float(value)
            for name, value in zip(fields, raw_coeffs, strict=False)
        }
    except ValueError as exc:
        raise ValueError(
            f"Invalid surface coefficients for surface {elem.get('id')}: "
            f"{elem.get('coeffs')!r}"
        ) from exc

    data: dict[str, Any] = {
        "kind": stype,
        "id": _opt_int(elem.get("id")),
        "name": elem.get("name") or "",
        "boundary_type": elem.get("boundary", "transmission"),
        **coeffs,
    }
    return _SURFACE_ADAPTER.validate_python(data)


def _cell_from_element(elem: ET.Element) -> Cell:
    """Build a Cell model from an OpenMC ``<cell>`` element."""
    cell_id = _opt_int(elem.get("id"))

    region_str = elem.get("region")
    if not region_str:
        raise ValueError(f"Cell {cell_id} is missing a region expression")

    material = elem.get("material")
    fill_material_id = (
        int(material) if material is not None and material != "void" else None
    )
    fill_universe_id = _opt_int(elem.get("fill"))

    return Cell(
        id=cell_id,
        name=elem.get("name") or "",
        region=parse_region_string(region_str),
        fill_material_id=fill_material_id,
        fill_universe_id=fill_universe_id,
    )


def parse_geometry_xml(path: PathLike) -> GeometryModel:
    """Parse an OpenMC ``geometry.xml`` file into a GeometryModel.

    Uses ``defusedxml`` for parsing. Raises ``ValueError`` for unsupported
    constructs and ``pydantic.ValidationError`` when the resulting model
    fails CSG validation (unique IDs, surface references, boundedness).
    """
    tree = defused_parse(str(Path(path)))
    root = tree.getroot()
    if root is None:
        raise ValueError("geometry XML has no root element")

    surfaces = [_surface_from_element(e) for e in root.findall("surface")]
    cells = [_cell_from_element(e) for e in root.findall("cell")]
    return GeometryModel(
        surfaces=surfaces,
        root_universe=Universe(cells=cells),
    )


def parse_materials_xml(path: PathLike) -> MaterialsModel:
    """Parse an OpenMC ``materials.xml`` file into a MaterialsModel.

    Uses ``defusedxml`` for parsing. Raises ``ValueError`` for malformed
    numeric fields and ``pydantic.ValidationError`` when materials fail
    validation (positive density, nuclide names/fractions, unique IDs).
    """
    tree = defused_parse(str(Path(path)))
    root = tree.getroot()
    if root is None:
        raise ValueError("materials XML has no root element")

    materials: list[dict[str, Any]] = []
    for material_elem in root.findall("material"):
        mat: dict[str, Any] = {
            "id": _opt_int(material_elem.get("id")),
            "name": material_elem.get("name") or "",
        }

        density_elem = material_elem.find("density")
        if density_elem is not None and density_elem.get("value"):
            mat["density_g_per_cc"] = float(density_elem.get("value", ""))

        nuclides: list[dict[str, Any]] = []
        for nuclide_elem in material_elem.findall("nuclide"):
            nuclide: dict[str, Any] = {"name": nuclide_elem.get("name") or ""}
            fraction = (
                nuclide_elem.get("wo")
                or nuclide_elem.get("ao")
                or nuclide_elem.get("fraction")
            )
            if fraction is not None:
                nuclide["fraction"] = float(fraction)
            nuclides.append(nuclide)
        mat["nuclides"] = nuclides
        materials.append(mat)

    return MaterialsModel.model_validate({"materials": materials})
