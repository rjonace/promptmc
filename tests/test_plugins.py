"""Tests for plugin system."""

from __future__ import annotations

import pytest
from openmc_wrapper.plugins import (
    HookEvent,
    HookPlugin,
    Plugin,
    PluginMetadata,
    PluginRegistry,
    PluginType,
    PostProcessorPlugin,
    hook,
)


class _DummyPlugin(Plugin):
    """A minimal plugin for testing."""

    def __init__(self, name: str = "dummy"):
        self._metadata = PluginMetadata(
            name=name,
            version="1.0.0",
            plugin_type=PluginType.HOOK,
            description="Test plugin",
        )
        self.initialized = False
        self.shutdown_called = False

    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata

    def initialize(self) -> None:
        self.initialized = True

    def shutdown(self) -> None:
        self.shutdown_called = True


class _DummyHookPlugin(HookPlugin):
    """A hook plugin for testing."""

    def __init__(self, events: list[HookEvent], name: str = "hook-plugin"):
        self._events = events
        self._metadata = PluginMetadata(
            name=name,
            version="1.0.0",
            plugin_type=PluginType.HOOK,
        )
        self.received_events: list = []

    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata

    def supported_events(self):
        return self._events

    def handle(self, event: HookEvent, context: dict) -> None:
        self.received_events.append((event, context))


class _DummyPostProcessor(PostProcessorPlugin):
    """A post-processor plugin for testing."""

    def __init__(self, name: str = "post-proc"):
        self._metadata = PluginMetadata(
            name=name,
            version="1.0.0",
            plugin_type=PluginType.POST_PROCESSOR,
        )

    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata

    def process(self, output_path: str, results: dict) -> dict:
        return {**results, "post_processed": True}


def test_plugin_registry_register():
    """Test registering a plugin."""
    registry = PluginRegistry()
    plugin = _DummyPlugin()

    registry.register(plugin)
    assert plugin.initialized
    assert registry.get("dummy") is plugin


def test_plugin_registry_duplicate_name():
    """Test that registering duplicate names raises."""
    registry = PluginRegistry()
    registry.register(_DummyPlugin())

    with pytest.raises(ValueError):
        registry.register(_DummyPlugin())


def test_plugin_registry_unregister():
    """Test unregistering a plugin."""
    registry = PluginRegistry()
    plugin = _DummyPlugin()
    registry.register(plugin)

    registry.unregister("dummy")
    assert plugin.shutdown_called
    assert registry.get("dummy") is None


def test_plugin_registry_unregister_unknown():
    """Test unregistering a non-existent plugin doesn't raise."""
    registry = PluginRegistry()
    registry.unregister("nonexistent")  # Should not raise


def test_plugin_registry_list():
    """Test listing plugins."""
    registry = PluginRegistry()
    registry.register(_DummyPlugin("a"))
    registry.register(_DummyPlugin("b"))

    metas = registry.list_plugins()
    assert len(metas) == 2
    names = [m.name for m in metas]
    assert "a" in names
    assert "b" in names


def test_hook_plugin_registration():
    """Test registering a hook plugin and firing events."""
    registry = PluginRegistry()
    hook_plugin = _DummyHookPlugin([HookEvent.BEFORE_RUN, HookEvent.AFTER_RUN])

    registry.register(hook_plugin)
    registry.fire_hook(HookEvent.BEFORE_RUN, {"sim_id": "test"})

    assert len(hook_plugin.received_events) == 1
    assert hook_plugin.received_events[0][0] == HookEvent.BEFORE_RUN
    assert hook_plugin.received_events[0][1]["sim_id"] == "test"


def test_hook_plugin_only_subscribed_events():
    """Test that hooks only receive subscribed events."""
    registry = PluginRegistry()
    hook_plugin = _DummyHookPlugin([HookEvent.BEFORE_RUN])

    registry.register(hook_plugin)
    registry.fire_hook(HookEvent.AFTER_RUN, {})

    assert len(hook_plugin.received_events) == 0


def test_failing_hook_does_not_break():
    """Test that a failing hook does not break others."""

    class _BadHook(HookPlugin):
        @property
        def metadata(self):
            return PluginMetadata(name="bad", version="1.0", plugin_type=PluginType.HOOK)

        def supported_events(self):
            return [HookEvent.BEFORE_RUN]

        def handle(self, event, context):
            raise RuntimeError("bad hook")

    registry = PluginRegistry()
    good_hook = _DummyHookPlugin([HookEvent.BEFORE_RUN], name="good")
    bad_hook = _BadHook()

    registry.register(bad_hook)
    registry.register(good_hook)

    # Should not raise even though bad_hook raises
    registry.fire_hook(HookEvent.BEFORE_RUN, {})
    assert len(good_hook.received_events) == 1


def test_post_processor_plugin():
    """Test post-processor plugin."""
    registry = PluginRegistry()
    plugin = _DummyPostProcessor()
    registry.register(plugin)

    results = registry.run_post_processors("/tmp", {"original": True})
    assert results["original"] is True
    assert results["post_processed"] is True


def test_failing_post_processor_does_not_break():
    """Test that a failing post-processor doesn't break others."""

    class _BadPostProc(PostProcessorPlugin):
        @property
        def metadata(self):
            return PluginMetadata(
                name="bad-proc",
                version="1.0",
                plugin_type=PluginType.POST_PROCESSOR,
            )

        def process(self, output_path, results):
            raise RuntimeError("bad")

    registry = PluginRegistry()
    registry.register(_BadPostProc())
    registry.register(_DummyPostProcessor())

    # Should not raise
    results = registry.run_post_processors("/tmp", {})
    assert "post_processed" in results


def test_global_plugin_registry():
    """Test global plugin registry singleton."""
    from openmc_wrapper.plugins import get_plugin_registry

    registry1 = get_plugin_registry()
    registry2 = get_plugin_registry()
    assert registry1 is registry2


def test_hook_decorator():
    """Test hook decorator."""

    @hook(HookEvent.BEFORE_RUN)
    def my_handler(event, context):
        return None

    assert my_handler._hook_event == HookEvent.BEFORE_RUN
