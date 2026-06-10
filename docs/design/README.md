# Design documents

One design document per minor release. Shipped releases are documented
as built (including decisions that changed along the way); planned
releases are forward-looking designs, open for review and iteration —
file an issue or PR if you see a problem with one.

[`ROADMAP.md`](../../ROADMAP.md) stays the authoritative "what ships
when"; `AGENTS.md` §5.3 holds the per-release acceptance criteria.
These documents carry the layer between the two: the architecture, the
key decisions, and the testing strategy for each release.

| Release | Design doc | Status |
|---|---|---|
| v0.1 | [CLI initial release](v0.1-cli.md) | Shipped |
| v0.2 | [MCP server](v0.2-mcp-server.md) | Shipped |
| v0.3 | [CSG schema + serialization](v0.3-csg-schema.md) | Shipped |
| v0.4 | [Reference geometry library](v0.4-reference-library.md) | Planned |
| v0.5 | [Geometry composition + inspection](v0.5-composition-inspection.md) | Planned |
| v0.6 | [Physics safety gate](v0.6-physics-gate.md) | Planned |
| v0.7 | [Component library](v0.7-component-library.md) | Planned |
| v0.8 | [Constrained generation](v0.8-constrained-generation.md) | Planned |
| v0.9 | [Observability, provenance + audit](v0.9-observability-provenance.md) | Planned |

When implementation diverges from a planned design, update the design
doc in the same PR — these documents describe the system, not a wish.
