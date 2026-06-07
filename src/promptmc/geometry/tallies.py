"""Tallies schema and validation definitions."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

FilterType = Literal["energy", "material", "cell", "universe"]
ScoreType = Literal[
    "flux",
    "fission",
    "absorption",
    "scatter",
    "total",
    "nu-fission",
]


class TallyFilter(BaseModel):
    """A filter restricting a tally's scope."""

    type: FilterType
    bins: list[Any]


class Tally(BaseModel):
    """Defines a simulation tally scoring specific metrics."""

    id: int | None = None
    name: str = ""
    filters: list[TallyFilter] = Field(default_factory=list)
    scores: list[str] = Field(default_factory=list)


class TalliesModel(BaseModel):
    """A collection of tallies."""

    tallies: list[Tally]

    @model_validator(mode="after")
    def validate_tallies(self) -> TalliesModel:
        """Ensure all tally IDs are unique."""
        tally_ids = set()
        for t in self.tallies:
            if t.id is not None:
                if t.id in tally_ids:
                    raise ValueError(f"Duplicate tally ID: {t.id}")
                tally_ids.add(t.id)
        return self
