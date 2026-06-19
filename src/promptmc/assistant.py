"""Natural-language assistant for OpenMC configuration planning."""

from __future__ import annotations

import json
import os
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, Field

from promptmc.templates import TemplateType, get_template

DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"

SUPPORTED_TEMPLATE_TYPES = {
    TemplateType.CRITICALITY,
    TemplateType.FIXED_SOURCE,
    TemplateType.SHIELDING,
    TemplateType.REACTOR_PIN,
    TemplateType.DEPLETION,
}


@dataclass
class NaturalLanguagePlan:
    """A simulation plan derived from natural language input."""

    prompt: str
    template_type: TemplateType
    particles: int
    batches: int
    inactive: int
    confidence: float
    summary: str
    rationale: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    source: str = "local"

    def command(self, output_path: str | Path = "settings.xml") -> str:
        """Generate the CLI command to execute this plan."""
        parts = [
            "promptmc",
            "template",
            self.template_type.value,
            "--output",
            str(output_path),
            "--particles",
            str(self.particles),
            "--batches",
            str(self.batches),
        ]
        if self.inactive:
            parts.extend(["--inactive", str(self.inactive)])
        return shlex.join(parts)

    def render(self, output_path: str | Path) -> Path:
        """Render the plan to an XML settings file."""
        template = get_template(self.template_type)
        return template.render(
            output_path=output_path,
            particles=self.particles,
            batches=self.batches,
            inactive=self.inactive,
        )


T = TypeVar("T", bound=BaseModel)


class GeminiPlanResponse(BaseModel):
    """Pydantic schema for the Gemini structured output plan."""

    template_type: str = Field(
        description="One of 'criticality', 'fixed_source', 'shielding', or 'reactor_pin'"
    )
    particles: int = Field(
        description="Number of particles to simulate, must be a positive integer"
    )
    batches: int = Field(
        description="Number of batches to simulate, must be a positive integer"
    )
    inactive: int = Field(
        description="Number of inactive batches to simulate (must be 0 for fixed_source and shielding)"
    )
    confidence: float = Field(
        description="Confidence score between 0.0 and 1.0"
    )
    summary: str = Field(description="A short summary of the plan")
    rationale: list[str] = Field(
        default_factory=list, description="Reasoning behind the chosen plan"
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Any warnings or potential issues detected",
    )
    next_steps: list[str] = Field(
        default_factory=list, description="Next steps for the user to follow"
    )


class GeminiClient:
    """A thin client wrapper for Google Gemini API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key: str | None = api_key or os.getenv("GEMINI_API_KEY")
        self.model: str = (
            model or os.getenv("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL
        )

    @property
    def configured(self) -> bool:
        """Whether the client has an API key configured."""
        return bool(self.api_key)

    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[T],
    ) -> T:
        """Call Gemini to generate structured output conforming to the response_schema."""
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is not set. "
                "Set this variable to use the Gemini LLM planner, "
                "or omit the --llm flag to use the default local planner."
            )

        # Lazy import: import google-genai ONLY inside the seam that makes the call
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.api_key)

        try:
            response = client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    temperature=0.1,
                ),
            )
        except Exception as e:
            raise RuntimeError(f"Gemini API request failed: {e}") from e

        if not response.text:
            raise RuntimeError("Gemini returned an empty response")

        try:
            return response_schema.model_validate_json(response.text)
        except Exception as e:
            raise RuntimeError(
                f"Failed to parse Gemini response as {response_schema.__name__}: {e}. "
                f"Raw response: {response.text}"
            ) from e


class NaturalLanguageAssistant:
    """Translates natural language into OpenMC simulation plans."""

    def __init__(self, llm_client: GeminiClient | None = None) -> None:
        self.llm_client = llm_client or GeminiClient()

    def plan(
        self,
        prompt: str,
        use_llm: bool = False,
        model: str | None = None,
    ) -> NaturalLanguagePlan:
        """Generate a simulation plan from a prompt."""
        local_plan = self._local_plan(prompt)
        if not use_llm:
            return local_plan

        client = self.llm_client
        if model:
            client = GeminiClient(model=model)

        if not client.configured:
            raise ValueError(
                "GEMINI_API_KEY environment variable is not set. "
                "Set this variable to use the Gemini LLM planner, "
                "or omit the --llm flag to use the default local planner."
            )

        return self._llm_plan(prompt, local_plan, client)

    def _local_plan(self, prompt: str) -> NaturalLanguagePlan:
        normalized = prompt.lower()
        template_type, confidence, rationale = self._infer_template(normalized)
        template = get_template(template_type)
        particles = self._extract_labeled_count(
            normalized,
            (
                "particles",
                "particle",
                "histories",
                "history",
                "neutrons",
                "photons",
            ),
            template.metadata.default_particles,
        )
        batches = self._extract_labeled_count(
            normalized,
            ("batches", "batch", "cycles", "cycle"),
            template.metadata.default_batches,
        )
        inactive = self._extract_labeled_count(
            normalized,
            ("inactive", "skip", "skipped"),
            template.metadata.default_inactive,
        )

        warnings: list[str] = []
        if template_type == TemplateType.DEPLETION:
            warnings.append(
                "The depletion template provides the eigenvalue"
                " transport settings only. Configure the burnup"
                " schedule (timesteps, power, and depletion chain)"
                " via OpenMC's Python depletion API."
            )
        if (
            template_type in {TemplateType.FIXED_SOURCE, TemplateType.SHIELDING}
            and inactive
        ):
            inactive = 0
            warnings.append(
                "Inactive batches are not used for"
                " fixed-source-style calculations."
            )

        next_steps = [
            "Generate settings.xml from the recommended template.",
            "Add or verify materials.xml and geometry.xml for the physical model.",
            "Run schema validation before launching OpenMC.",
        ]
        summary = self._summary(template_type, particles, batches, inactive)

        return NaturalLanguagePlan(
            prompt=prompt,
            template_type=template_type,
            particles=particles,
            batches=batches,
            inactive=inactive,
            confidence=confidence,
            summary=summary,
            rationale=rationale,
            warnings=warnings,
            next_steps=next_steps,
            source="local",
        )

    def _llm_plan(
        self,
        prompt: str,
        fallback: NaturalLanguagePlan,
        client: GeminiClient,
    ) -> NaturalLanguagePlan:
        system_prompt = (
            "You translate OpenMC simulation requests into a simulation plan JSON object. "
            "Valid template_type values are 'criticality', 'fixed_source', 'shielding', 'reactor_pin', and 'depletion'. "
            "Use positive integers for particles and batches. "
            "Use inactive=0 for fixed_source and shielding."
        )
        user_prompt = json.dumps(
            {
                "request": prompt,
                "fallback_plan": {
                    "template_type": fallback.template_type.value,
                    "particles": fallback.particles,
                    "batches": fallback.batches,
                    "inactive": fallback.inactive,
                },
            }
        )

        plan_response = client.generate_structured(
            system_prompt, user_prompt, GeminiPlanResponse
        )

        try:
            template_type = TemplateType(plan_response.template_type)
        except ValueError:
            template_type = fallback.template_type

        if template_type not in SUPPORTED_TEMPLATE_TYPES:
            template_type = fallback.template_type

        return NaturalLanguagePlan(
            prompt=prompt,
            template_type=template_type,
            particles=max(1, plan_response.particles),
            batches=max(1, plan_response.batches),
            inactive=max(0, plan_response.inactive),
            confidence=max(0.0, min(1.0, plan_response.confidence)),
            summary=plan_response.summary,
            rationale=plan_response.rationale,
            warnings=plan_response.warnings,
            next_steps=plan_response.next_steps,
            source="llm",
        )

    KEYWORD_TEMPLATES: dict[TemplateType, tuple[list[re.Pattern[str]], str]] = {
        TemplateType.SHIELDING: (
            [
                re.compile(rf"\b{kw}\b", re.IGNORECASE)
                for kw in (
                    "shield",
                    "shielding",
                    "dose",
                    "attenuation",
                    "concrete",
                    "lead",
                    "barrier",
                )
            ],
            "Shielding/dose keywords suggest a shielding calculation.",
        ),
        TemplateType.REACTOR_PIN: (
            [
                re.compile(rf"\b{kw}\b", re.IGNORECASE)
                for kw in (
                    "pin",
                    "pin-cell",
                    "pincell",
                    "fuel rod",
                    "fuel pellet",
                    "cladding",
                )
            ],
            "Pin-cell keywords suggest the reactor pin template.",
        ),
        TemplateType.DEPLETION: (
            [
                re.compile(rf"\b{kw}\b", re.IGNORECASE)
                for kw in (
                    "depletion",
                    "deplete",
                    "burnup",
                    "burn-up",
                )
            ],
            "Depletion/burnup keywords suggest the depletion template.",
        ),
        TemplateType.FIXED_SOURCE: (
            [
                re.compile(rf"\b{kw}\b", re.IGNORECASE)
                for kw in (
                    "fixed source",
                    "source",
                    "beam",
                    "dosimetry",
                    "14 mev",
                    "photon",
                    "gamma",
                )
            ],
            "Source/dosimetry keywords suggest a fixed-source calculation.",
        ),
        TemplateType.CRITICALITY: (
            [
                re.compile(rf"\b{kw}\b", re.IGNORECASE)
                for kw in (
                    "criticality",
                    "keff",
                    "k-effective",
                    "eigenvalue",
                    "reactor",
                    "multiplication",
                )
            ],
            "Criticality/eigenvalue keywords suggest a criticality calculation.",
        ),
    }

    def _infer_template(
        self, normalized: str
    ) -> tuple[TemplateType, float, list[str]]:
        matches: list[tuple[int, TemplateType, str]] = []
        for template_type, (patterns, reason) in self.KEYWORD_TEMPLATES.items():
            score = sum(1 for p in patterns if p.search(normalized))
            if score:
                matches.append((score, template_type, reason))

        if not matches:
            return (
                TemplateType.CRITICALITY,
                0.45,
                [
                    "No strong domain keywords were found, so criticality was chosen as a safe default."
                ],
            )

        score, template_type, reason = sorted(
            matches, key=lambda item: item[0], reverse=True
        )[0]
        confidence = min(0.95, 0.55 + 0.1 * score)
        return template_type, confidence, [reason]

    def _extract_labeled_count(
        self,
        normalized: str,
        labels: tuple[str, ...],
        default: int,
    ) -> int:
        label_group = "|".join(re.escape(label) for label in labels)
        after_pattern = re.compile(  # noqa: E501
            rf"(?:{label_group})\D{{0,24}}(?P<number>\d[\d,]*(?:\.\d+)?(?:e[+-]?\d+)?)(?P<suffix>\s*(?:k|m|thousand|million))?",
            re.IGNORECASE,
        )
        before_pattern = re.compile(  # noqa: E501
            rf"(?P<number>\d[\d,]*(?:\.\d+)?(?:e[+-]?\d+)?)(?P<suffix>\s*(?:k|m|thousand|million))?\s+(?:{label_group})",
            re.IGNORECASE,
        )
        for pattern in (before_pattern, after_pattern):
            match = pattern.search(normalized)
            if match:
                return max(
                    1,
                    self._parse_number(
                        match.group("number"), match.group("suffix") or ""
                    ),
                )
        return default

    @staticmethod
    def _parse_number(number: str, suffix: str) -> int:
        value = float(number.replace(",", ""))
        suffix = suffix.strip().lower()
        if suffix in {"k", "thousand"}:
            value *= 1_000
        elif suffix in {"m", "million"}:
            value *= 1_000_000
        return int(value)

    @staticmethod
    def _summary(
        template_type: TemplateType,
        particles: int,
        batches: int,
        inactive: int,
    ) -> str:
        if inactive:
            return (
                f"Use the {template_type.value} template with {particles:,} "
                f"particles, {batches} batches, and {inactive} inactive batches."
            )
        return (
            f"Use the {template_type.value} template with {particles:,} "
            f"particles and {batches} batches."
        )

    @staticmethod
    def _string_list(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value]
        if value is None:
            return []
        return [str(value)]
