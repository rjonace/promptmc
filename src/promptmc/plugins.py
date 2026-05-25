"""Plugin system for extending PromptMC functionality.

Plugins can provide:
- Custom configuration templates
- Result post-processors
- Pre/post simulation hooks
- Custom CLI commands

Plugins are discovered via Python entry points under the
``promptmc.plugins`` group, or registered programmatically.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class PluginType(str, Enum):
    """Categories of plugins."""

    TEMPLATE = "template"
    POST_PROCESSOR = "post_processor"
    HOOK = "hook"
    CLI_COMMAND = "cli_command"


class HookEvent(str, Enum):
    """Lifecycle events that hooks can subscribe to."""

    BEFORE_VALIDATE = "before_validate"
    AFTER_VALIDATE = "after_validate"
    BEFORE_RUN = "before_run"
    AFTER_RUN = "after_run"
    BEFORE_BATCH = "before_batch"
    AFTER_BATCH = "after_batch"
    ON_ERROR = "on_error"


@dataclass
class PluginMetadata:
    """Metadata describing a plugin."""

    name: str
    version: str
    plugin_type: PluginType
    description: str = ""
    author: str = ""


class Plugin(ABC):
    """Base class for all plugins."""

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""

    def initialize(self) -> None:  # noqa: B027 – intentional no-op default
        """Initialize the plugin. Called when registered."""

    def shutdown(self) -> None:  # noqa: B027 – intentional no-op default
        """Shutdown the plugin. Called when unregistered or on app exit."""


class PostProcessorPlugin(Plugin):
    """Plugin that processes simulation results."""

    @abstractmethod
    def process(self, output_path: str, results: dict) -> dict:
        """Process simulation results.

        Args:
            output_path: Path to simulation output directory.
            results: Existing results dict (may be modified).

        Returns:
            Processed results dict.
        """


class HookPlugin(Plugin):
    """Plugin that hooks into simulation lifecycle events."""

    @abstractmethod
    def supported_events(self) -> Iterable[HookEvent]:
        """Return the events this hook supports."""

    @abstractmethod
    def handle(self, event: HookEvent, context: dict) -> None:
        """Handle a lifecycle event.

        Args:
            event: The event being fired.
            context: Event-specific context data.
        """


@dataclass
class PluginRegistry:
    """Registry for managing plugins."""

    _plugins: dict[str, Plugin] = field(default_factory=dict)
    _hooks_by_event: dict[HookEvent, list[HookPlugin]] = field(
        default_factory=dict
    )
    _post_processors: list[PostProcessorPlugin] = field(default_factory=list)

    def register(self, plugin: Plugin) -> None:
        """Register a plugin.

        Raises:
            ValueError: If a plugin with the same name is already registered.
        """
        name = plugin.metadata.name
        if name in self._plugins:
            raise ValueError(f"Plugin '{name}' is already registered")

        try:
            plugin.initialize()
        except Exception as e:
            logger.exception("Plugin %s failed to initialize: %s", name, e)
            raise

        self._plugins[name] = plugin

        if isinstance(plugin, HookPlugin):
            for event in plugin.supported_events():
                self._hooks_by_event.setdefault(event, []).append(plugin)

        if isinstance(plugin, PostProcessorPlugin):
            self._post_processors.append(plugin)

        logger.info(
            "Registered plugin: %s (%s)",
            name,
            plugin.metadata.plugin_type.value,
        )

    def unregister(self, name: str) -> None:
        """Unregister a plugin by name."""
        plugin = self._plugins.pop(name, None)
        if plugin is None:
            return

        try:
            plugin.shutdown()
        except Exception:
            logger.exception("Plugin %s failed to shutdown", name)

        # Remove from event registry
        for event_plugins in self._hooks_by_event.values():
            if plugin in event_plugins:
                event_plugins.remove(plugin)

        if plugin in self._post_processors:
            self._post_processors.remove(plugin)

    def get(self, name: str) -> Plugin | None:
        """Get a registered plugin by name."""
        return self._plugins.get(name)

    def list_plugins(self) -> list[PluginMetadata]:
        """List all registered plugins."""
        return [p.metadata for p in self._plugins.values()]

    def fire_hook(self, event: HookEvent, context: dict | None = None) -> None:
        """Fire a lifecycle event to all subscribed hooks.

        Errors in individual hooks are logged but do not propagate.
        """
        ctx = context or {}
        hooks = self._hooks_by_event.get(event, [])
        for hook in hooks:
            try:
                hook.handle(event, ctx)
            except Exception:
                logger.exception(
                    "Hook %s failed for event %s",
                    hook.metadata.name,
                    event.value,
                )

    def run_post_processors(self, output_path: str, results: dict) -> dict:
        """Run all registered post-processors against the results."""
        current = results
        for processor in self._post_processors:
            try:
                current = processor.process(output_path, current)
            except Exception:
                logger.exception(
                    "Post-processor %s failed", processor.metadata.name
                )
        return current

    def discover_entry_points(self, group: str = "promptmc.plugins") -> int:
        """Discover and load plugins via Python entry points.

        Returns:
            Number of plugins loaded.
        """
        loaded = 0
        try:
            from importlib.metadata import entry_points

            try:
                eps: Any = entry_points(group=group)
            except TypeError:
                # Python 3.9 returns a dict-like
                eps_dict: Any = entry_points()
                eps = eps_dict.get(group, [])

            for ep in eps:
                try:
                    plugin_class: Any = ep.load()
                    plugin: Plugin = plugin_class()
                    self.register(plugin)
                    loaded += 1
                except Exception:
                    logger.exception("Failed to load plugin %s", ep.name)
        except Exception:
            logger.exception("Plugin entry point discovery failed")
        return loaded


# Global registry
_registry = PluginRegistry()


def get_plugin_registry() -> PluginRegistry:
    """Get the global plugin registry."""
    return _registry


def register_plugin(plugin: Plugin) -> None:
    """Register a plugin in the global registry."""
    _registry.register(plugin)


def hook(
    event: HookEvent,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to mark a function as a hook handler.

    Example:
        >>> @hook(HookEvent.AFTER_RUN)
        ... def my_handler(event, context):
        ...     print(f"Run finished: {context}")
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        func._hook_event = event  # type: ignore[attr-defined]
        return func

    return decorator
