"""Tests for configuration templates."""

import xml.etree.ElementTree as ET

import pytest
from promptmc.schema import SchemaValidator
from promptmc.templates import (
    CriticalityTemplate,
    DepletionTemplate,
    FixedSourceTemplate,
    ReactorPinTemplate,
    ShieldingTemplate,
    TemplateRegistry,
    TemplateType,
    get_template,
    list_templates,
)


def test_criticality_template_metadata():
    """Test criticality template metadata."""
    tmpl = CriticalityTemplate()
    assert tmpl.metadata.template_type == TemplateType.CRITICALITY
    assert tmpl.metadata.name == "Criticality"
    assert tmpl.metadata.default_particles == 10000


def test_fixed_source_template_metadata():
    """Test fixed source template metadata."""
    tmpl = FixedSourceTemplate()
    assert tmpl.metadata.template_type == TemplateType.FIXED_SOURCE
    assert tmpl.metadata.default_particles == 100000


def test_shielding_template_metadata():
    """Test shielding template metadata."""
    tmpl = ShieldingTemplate()
    assert tmpl.metadata.template_type == TemplateType.SHIELDING
    assert tmpl.metadata.default_particles == 1000000


def test_reactor_pin_template_metadata():
    """Test reactor pin template metadata."""
    tmpl = ReactorPinTemplate()
    assert tmpl.metadata.template_type == TemplateType.REACTOR_PIN


def test_depletion_template_metadata():
    """Test depletion template metadata."""
    tmpl = DepletionTemplate()
    assert tmpl.metadata.template_type == TemplateType.DEPLETION
    assert tmpl.metadata.name == "Depletion"


def test_render_writes_complete_deck(tmp_path):
    """render() writes settings/geometry/materials into a directory."""
    tmpl = CriticalityTemplate()
    result = tmpl.render(output_path=tmp_path / "deck")

    assert result == tmp_path / "deck"
    assert result.is_dir()
    for name in ("settings.xml", "geometry.xml", "materials.xml"):
        assert (result / name).exists()


def test_render_depletion_template(tmp_path):
    """Test rendering depletion template (eigenvalue transport settings)."""
    tmpl = DepletionTemplate()
    result = tmpl.render(output_path=tmp_path / "deck")

    root = ET.parse(result / "settings.xml").getroot()
    assert root.tag == "settings"
    assert root.find("run_mode").text == "eigenvalue"
    assert root.find("source") is not None


def test_render_criticality_template(tmp_path):
    """Test rendering criticality template."""
    tmpl = CriticalityTemplate()
    result = tmpl.render(output_path=tmp_path / "deck")

    root = ET.parse(result / "settings.xml").getroot()
    assert root.tag == "settings"
    run_mode = root.find("run_mode")
    assert run_mode is not None
    assert run_mode.text == "eigenvalue"


def test_render_with_overrides(tmp_path):
    """Test rendering with parameter overrides."""
    tmpl = CriticalityTemplate()
    result = tmpl.render(
        output_path=tmp_path / "deck",
        particles=50000,
        batches=200,
        inactive=20,
    )

    root = ET.parse(result / "settings.xml").getroot()
    assert root.find("particles").text == "50000"
    assert root.find("batches").text == "200"
    assert root.find("inactive").text == "20"


def test_render_fixed_source_template(tmp_path):
    """Test rendering fixed source template."""
    tmpl = FixedSourceTemplate()
    result = tmpl.render(output_path=tmp_path / "deck")

    root = ET.parse(result / "settings.xml").getroot()
    run_mode = root.find("run_mode")
    assert run_mode.text == "fixed source"


@pytest.mark.parametrize(
    "template_type",
    [
        TemplateType.CRITICALITY,
        TemplateType.FIXED_SOURCE,
        TemplateType.SHIELDING,
        TemplateType.REACTOR_PIN,
        TemplateType.DEPLETION,
    ],
)
def test_rendered_deck_passes_schema_validation(template_type, tmp_path):
    """Every template renders a deck that passes SchemaValidator."""
    deck = tmp_path / template_type.value
    get_template(template_type).render(output_path=deck)

    result = SchemaValidator().validate_directory(deck)

    assert result.is_valid, [issue.message for issue in result.issues]


def test_template_registry_initialization():
    """Test TemplateRegistry initialization."""
    registry = TemplateRegistry()
    templates = registry.list_templates()
    assert len(templates) >= 4


def test_template_registry_get():
    """Test getting template from registry."""
    registry = TemplateRegistry()

    tmpl = registry.get(TemplateType.CRITICALITY)
    assert tmpl is not None
    assert isinstance(tmpl, CriticalityTemplate)


def test_template_registry_get_by_string():
    """Test getting template by string identifier."""
    registry = TemplateRegistry()

    tmpl = registry.get("criticality")
    assert tmpl is not None


def test_template_registry_unknown():
    """Test getting unknown template raises KeyError."""
    registry = TemplateRegistry()

    with pytest.raises(KeyError):
        registry.get("unknown_template")


def test_global_get_template():
    """Test global get_template function."""
    tmpl = get_template(TemplateType.CRITICALITY)
    assert tmpl is not None


def test_global_list_templates():
    """Test global list_templates function."""
    templates = list_templates()
    assert len(templates) >= 4
    template_types = [t.template_type for t in templates]
    assert TemplateType.CRITICALITY in template_types
    assert TemplateType.FIXED_SOURCE in template_types
    assert TemplateType.SHIELDING in template_types
    assert TemplateType.REACTOR_PIN in template_types
