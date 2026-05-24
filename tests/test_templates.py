"""Tests for configuration templates."""

import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from promptmc.templates import (
    CriticalityTemplate,
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


def test_render_criticality_template():
    """Test rendering criticality template."""
    tmpl = CriticalityTemplate()

    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
        temp_path = Path(f.name)

    try:
        result = tmpl.render(output_path=temp_path)
        assert result == temp_path
        assert temp_path.exists()

        # Parse and verify
        tree = ET.parse(temp_path)
        root = tree.getroot()
        assert root.tag == "settings"
        run_mode = root.find("run_mode")
        assert run_mode is not None
        assert run_mode.text == "eigenvalue"
    finally:
        temp_path.unlink()


def test_render_with_overrides():
    """Test rendering with parameter overrides."""
    tmpl = CriticalityTemplate()

    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
        temp_path = Path(f.name)

    try:
        tmpl.render(
            output_path=temp_path,
            particles=50000,
            batches=200,
            inactive=20,
        )

        tree = ET.parse(temp_path)
        root = tree.getroot()
        assert root.find("particles").text == "50000"
        assert root.find("batches").text == "200"
        assert root.find("inactive").text == "20"
    finally:
        temp_path.unlink()


def test_render_fixed_source_template():
    """Test rendering fixed source template."""
    tmpl = FixedSourceTemplate()

    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
        temp_path = Path(f.name)

    try:
        tmpl.render(output_path=temp_path)
        tree = ET.parse(temp_path)
        root = tree.getroot()
        run_mode = root.find("run_mode")
        assert run_mode.text == "fixed source"
    finally:
        temp_path.unlink()


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
