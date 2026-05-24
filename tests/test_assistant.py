"""Tests for the natural-language OpenMC assistant."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET

from promptmc.assistant import NaturalLanguageAssistant, OpenAICompatibleLLMClient
from promptmc.templates import TemplateType


class FakeLLMClient(OpenAICompatibleLLMClient):
    @property
    def configured(self) -> bool:
        return True

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict:
        return {
            "template_type": "shielding",
            "particles": 2000000,
            "batches": 20,
            "inactive": 0,
            "confidence": 0.9,
            "summary": "LLM shielding plan",
            "rationale": ["The request asked for shielding."],
            "warnings": [],
            "next_steps": ["Generate settings.xml."],
        }


class UnconfiguredLLMClient(OpenAICompatibleLLMClient):
    @property
    def configured(self) -> bool:
        return False


def test_local_plan_shielding_request():
    assistant = NaturalLanguageAssistant()
    plan = assistant.plan("make a concrete shielding calculation with 1 million particles")

    assert plan.template_type == TemplateType.SHIELDING
    assert plan.particles == 1_000_000
    assert plan.inactive == 0
    assert plan.source == "local"
    assert "template shielding" in plan.command("settings.xml")


def test_local_plan_reactor_pin_request():
    assistant = NaturalLanguageAssistant()
    plan = assistant.plan("set up a fuel pin cell criticality run with 50k particles")

    assert plan.template_type == TemplateType.REACTOR_PIN
    assert plan.particles == 50_000
    assert plan.inactive > 0


def test_local_plan_fixed_source_request():
    assistant = NaturalLanguageAssistant()
    plan = assistant.plan("run a fixed source 14 MeV neutron beam with 25 batches")

    assert plan.template_type == TemplateType.FIXED_SOURCE
    assert plan.batches == 25
    assert plan.inactive == 0


def test_local_plan_renders_settings_xml(tmp_path):
    assistant = NaturalLanguageAssistant()
    plan = assistant.plan("criticality run with 20000 particles and 30 batches")
    output = tmp_path / "settings.xml"

    result = plan.render(output)
    root = ET.parse(result).getroot()

    assert result == output
    assert root.find("particles").text == "20000"
    assert root.find("batches").text == "30"


def test_llm_plan_uses_configured_client():
    assistant = NaturalLanguageAssistant(llm_client=FakeLLMClient(api_key="test"))
    plan = assistant.plan("I need shielding", use_llm=True)

    assert plan.source == "llm"
    assert plan.template_type == TemplateType.SHIELDING
    assert plan.particles == 2_000_000


def test_llm_plan_falls_back_without_api_key():
    assistant = NaturalLanguageAssistant(llm_client=UnconfiguredLLMClient(api_key=None))
    plan = assistant.plan("shielding calculation", use_llm=True)

    assert plan.source == "local"
    assert any("API key" in warning for warning in plan.warnings)


def test_parse_number_suffixes():
    assistant = NaturalLanguageAssistant()

    assert assistant._parse_number("1", "million") == 1_000_000
    assert assistant._parse_number("2.5", "k") == 2_500
    assert assistant._parse_number("10,000", "") == 10_000


def test_llm_client_payload_can_be_json_serialized():
    client = OpenAICompatibleLLMClient(api_key="test")
    payload = {
        "model": client.model,
        "messages": [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "user"},
        ],
    }

    assert json.loads(json.dumps(payload))["model"] == client.model
