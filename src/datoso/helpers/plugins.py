"""List all installed seeds."""
from pydoc import locate
from datoso import __app_name__

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
    plugin = locate(f'{__app_name__}_{plugin_type}_{plugin}')
    return plugin.__description__

def get_seed(seed, module):
    return get(seed, module, 'seed')

def installed_seeds():
    return installed('seed')

def seed_description(seed):
    return description(seed, 'seed')

def get_plugin(plugin, module):
    return get(plugin, module, 'plugin')

def installed_plugins():
    return installed('plugin')

def plugin_description(plugin):
    return description(plugin, 'plugin')