"""Natural-language assistant for OpenMC configuration planning."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from promptmc.templates import TemplateType, get_template

SUPPORTED_TEMPLATE_TYPES = {
    TemplateType.CRITICALITY,
    TemplateType.FIXED_SOURCE,
    TemplateType.SHIELDING,
    TemplateType.REACTOR_PIN,
}


@dataclass
class NaturalLanguagePlan:
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
        return " ".join(parts)

    def render(self, output_path: str | Path) -> Path:
        template = get_template(self.template_type)
        return template.render(
            output_path=output_path,
            particles=self.particles,
            batches=self.batches,
            inactive=self.inactive,
        )


class OpenAICompatibleLLMClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        endpoint: Optional[str] = None,
        timeout_seconds: int = 30,
    ) -> None:
        self.api_key = (
            api_key
            or os.getenv("PROMPTMC_LLM_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )
        self.model = model or os.getenv("PROMPTMC_LLM_MODEL") or "gpt-4o-mini"
        self.endpoint = endpoint or os.getenv(
            "PROMPTMC_LLM_ENDPOINT",
            "https://api.openai.com/v1/chat/completions",
        )
        self.timeout_seconds = timeout_seconds

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("LLM API key is not configured")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as e:
            raise RuntimeError(f"LLM request failed: {e}") from e

        content = data["choices"][0]["message"]["content"]
        return json.loads(content)


class NaturalLanguageAssistant:
    def __init__(self, llm_client: Optional[OpenAICompatibleLLMClient] = None) -> None:
        self.llm_client = llm_client or OpenAICompatibleLLMClient()

    def plan(
        self,
        prompt: str,
        use_llm: bool = False,
        model: Optional[str] = None,
        endpoint: Optional[str] = None,
    ) -> NaturalLanguagePlan:
        local_plan = self._local_plan(prompt)
        if not use_llm:
            return local_plan

        client = self.llm_client
        if model or endpoint:
            client = OpenAICompatibleLLMClient(model=model, endpoint=endpoint)

        if not client.configured:
            local_plan.warnings.append(
                "LLM mode requested, but no API key is configured. Set OPENAI_API_KEY or "
                "PROMPTMC_LLM_API_KEY. Returned the local planner result instead."
            )
            return local_plan

        try:
            return self._llm_plan(prompt, local_plan, client)
        except Exception as e:
            local_plan.warnings.append(f"LLM planning failed; returned local plan instead: {e}")
            return local_plan

    def _local_plan(self, prompt: str) -> NaturalLanguagePlan:
        normalized = prompt.lower()
        template_type, confidence, rationale = self._infer_template(normalized)
        template = get_template(template_type)
        particles = self._extract_labeled_count(
            normalized,
            ("particles", "particle", "histories", "history", "neutrons", "photons"),
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
        if "depletion" in normalized or "burnup" in normalized:
            warnings.append(
                "Depletion was detected, but the built-in depletion template is not "
                "implemented yet. "
                "Use the generated plan as a starting point and add depletion settings manually."
            )
        if template_type in {TemplateType.FIXED_SOURCE, TemplateType.SHIELDING} and inactive:
            inactive = 0
            warnings.append("Inactive batches are not used for fixed-source-style calculations.")

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
        client: OpenAICompatibleLLMClient,
    ) -> NaturalLanguagePlan:
        system_prompt = (
            "You translate plain-English OpenMC simulation requests into a small JSON plan. "
            "Return only JSON. Valid template_type values are criticality, fixed_source, "
            "shielding, and reactor_pin. Use positive integers for particles and batches. "
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
                "required_schema": {
                    "template_type": "criticality|fixed_source|shielding|reactor_pin",
                    "particles": "int",
                    "batches": "int",
                    "inactive": "int",
                    "confidence": "float from 0 to 1",
                    "summary": "short string",
                    "rationale": ["strings"],
                    "warnings": ["strings"],
                    "next_steps": ["strings"],
                },
            }
        )
        data = client.complete_json(system_prompt, user_prompt)
        template_type = TemplateType(str(data.get("template_type", fallback.template_type.value)))
        if template_type not in SUPPORTED_TEMPLATE_TYPES:
            template_type = fallback.template_type

        return NaturalLanguagePlan(
            prompt=prompt,
            template_type=template_type,
            particles=max(1, int(data.get("particles", fallback.particles))),
            batches=max(1, int(data.get("batches", fallback.batches))),
            inactive=max(0, int(data.get("inactive", fallback.inactive))),
            confidence=max(0.0, min(1.0, float(data.get("confidence", fallback.confidence)))),
            summary=str(data.get("summary", fallback.summary)),
            rationale=self._string_list(data.get("rationale", fallback.rationale)),
            warnings=self._string_list(data.get("warnings", fallback.warnings)),
            next_steps=self._string_list(data.get("next_steps", fallback.next_steps)),
            source="llm",
        )

    def _infer_template(self, normalized: str) -> tuple[TemplateType, float, list[str]]:
        matches: list[tuple[int, TemplateType, str]] = []
        keyword_sets = [
            (
                TemplateType.SHIELDING,
                ("shield", "shielding", "dose", "attenuation", "concrete", "lead", "barrier"),
                "Shielding/dose keywords suggest a shielding calculation.",
            ),
            (
                TemplateType.REACTOR_PIN,
                ("pin", "pin-cell", "pincell", "fuel rod", "fuel pellet", "cladding"),
                "Pin-cell keywords suggest the reactor pin template.",
            ),
            (
                TemplateType.FIXED_SOURCE,
                ("fixed source", "source", "beam", "dosimetry", "14 mev", "photon", "gamma"),
                "Source/dosimetry keywords suggest a fixed-source calculation.",
            ),
            (
                TemplateType.CRITICALITY,
                ("criticality", "keff", "k-effective", "eigenvalue", "reactor", "multiplication"),
                "Criticality/eigenvalue keywords suggest a criticality calculation.",
            ),
        ]
        for template_type, keywords, reason in keyword_sets:
            score = sum(1 for keyword in keywords if keyword in normalized)
            if score:
                matches.append((score, template_type, reason))

        if not matches:
            return (
                TemplateType.CRITICALITY,
                0.45,
                [
                    "No strong domain keywords were found, so criticality was chosen as "
                    "a safe default."
                ],
            )

        score, template_type, reason = sorted(matches, key=lambda item: item[0], reverse=True)[0]
        confidence = min(0.95, 0.55 + 0.1 * score)
        return template_type, confidence, [reason]

    def _extract_labeled_count(
        self,
        normalized: str,
        labels: tuple[str, ...],
        default: int,
    ) -> int:
        label_group = "|".join(re.escape(label) for label in labels)
        after_pattern = re.compile(
            rf"(?:{label_group})\D{{0,24}}(?P<number>\d[\d,]*(?:\.\d+)?(?:e[+-]?\d+)?)(?P<suffix>\s*(?:k|m|thousand|million))?",
            re.IGNORECASE,
        )
        before_pattern = re.compile(
            rf"(?P<number>\d[\d,]*(?:\.\d+)?(?:e[+-]?\d+)?)(?P<suffix>\s*(?:k|m|thousand|million))?\s+(?:{label_group})",
            re.IGNORECASE,
        )
        for pattern in (before_pattern, after_pattern):
            match = pattern.search(normalized)
            if match:
                return max(
                    1,
                    self._parse_number(match.group("number"), match.group("suffix") or ""),
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
                f"Use the {template_type.value} template with {particles:,} particles, "
                f"{batches} batches, and {inactive} inactive batches."
            )
        return (
            f"Use the {template_type.value} template with {particles:,} particles "
            f"and {batches} batches."
        )

    @staticmethod
    def _string_list(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value]
        if value is None:
            return []
        return [str(value)]
