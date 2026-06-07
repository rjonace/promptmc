"""Benchmark geometries registry."""

from __future__ import annotations

from promptmc.benchmarks import godiva, pwr_pin
from promptmc.benchmarks._types import Benchmark

ALL_BENCHMARKS: dict[str, Benchmark] = {
    "godiva": godiva,
    "pwr_pin": pwr_pin,
}

__all__ = ["Benchmark", "ALL_BENCHMARKS"]
