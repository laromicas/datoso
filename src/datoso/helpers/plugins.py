"""List all installed seeds."""
from enum import Enum
from pydoc import locate
from types import ModuleType
from datoso import __app_name__

class PluginType(Enum):
    SEED = 'seed'
    PLUGIN = 'plugin'

def get(plugin, module, plugin_type):
    if module:
        return locate(f'{__app_name__}_{plugin_type}_{plugin}.{module}')
    return locate(f'{__app_name__}_{plugin_type}_{plugin}')

def installed(plugin_type):
    import importlib
    import pkgutil
    return {
        name: importlib.import_module(name)
        for finder, name, ispkg
        in pkgutil.iter_modules()
        if name.startswith(f'{__app_name__}_{plugin_type}_')
    }

def description(plugin, plugin_type):
    plugin = plugin if isinstance(plugin, ModuleType) else locate(f'{__app_name__}_{plugin_type}_{plugin}')
    return plugin.__description__

def get_seed(seed, module=None):
    return get(seed, module, PluginType.SEED.value)

def installed_seeds():
    return installed(PluginType.SEED.value)

def seed_description(seed):
    return description(seed, PluginType.SEED.value)

def get_plugin(plugin, module=None):
    return get(plugin, module, PluginType.PLUGIN.value)

def installed_plugins():
    return installed(PluginType.PLUGIN.value)

def plugin_description(plugin):
    return description(plugin, PluginType.PLUGIN.value)
