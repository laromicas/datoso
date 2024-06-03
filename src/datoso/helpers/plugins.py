"""List all installed seeds."""
from enum import Enum
from pydoc import locate
from types import ModuleType

from datoso import __app_name__


class PluginType(Enum):
    """Plugin type Enum."""

    SEED = 'seed'
    PLUGIN = 'plugin'

def get(plugin: str, module: str, plugin_type: str) -> ModuleType:
    """Get a plugin."""
    if module:
        return locate(f'{__app_name__}_{plugin_type}_{plugin}.{module}')
    return locate(f'{__app_name__}_{plugin_type}_{plugin}')

def installed(plugin_type: str) -> dict:
    """List all installed plugins."""
    import pkgutil
    return {
        name: __import__(name)
        for finder, name, ispkg
        in pkgutil.iter_modules()
        if name.startswith(f'{__app_name__}_{plugin_type}_')
    }

def description(plugin: str, plugin_type: str) -> str:
    """Get the description of a plugin."""
    plugin = plugin if isinstance(plugin, ModuleType) else locate(f'{__app_name__}_{plugin_type}_{plugin}')
    return plugin.__description__

def get_seed(seed: str, module: str | None=None) -> ModuleType:
    """Get a seed."""
    return get(seed, module, PluginType.SEED.value)

def installed_seeds() -> dict:
    """List all installed seeds."""
    return installed(PluginType.SEED.value)

def seed_description(seed: str) -> str:
    """Get the description of a seed."""
    return description(seed, PluginType.SEED.value)

def get_plugin(plugin: str, module: str | None=None) -> ModuleType:
    """Get a plugin."""
    return get(plugin, module, PluginType.PLUGIN.value)

def installed_plugins() -> dict:
    """List all installed plugins."""
    return installed(PluginType.PLUGIN.value)

def plugin_description(plugin: str) -> str:
    """Get the description of a plugin."""
    return description(plugin, PluginType.PLUGIN.value)
