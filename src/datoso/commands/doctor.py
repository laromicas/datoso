"""Check if all dependencies are installed."""
from pydoc import locate
from shutil import which

from packaging.version import parse

from datoso import __app_name__
from datoso.helpers import Bcolors
from datoso.helpers.plugins import installed_seeds


def check_seed(seed: str) -> bool:
    """Check if seed is installed."""
    return f'{__app_name__}_seed_{seed}' in installed_seeds()


def check_version(detected: str, required: str, expression: str) -> bool:
    """Check if version of required package is correct."""
    detected = parse(detected)
    required = parse(required)
    match expression:
        case '>':
            return detected > required
        case '<':
            return detected < required
        case '>=':
            return detected >= required
        case '<=':
            return detected <= required
        case '==':
            return detected == required
        case _:
            return detected == required


def check_module_attributes(seed: str, module: object) -> None:
    """Check if all needed files are present."""
    reqs = {
        '__prefix__': 'Prefix for identification of dats',
        '__description__': 'Description of module',
        'fetch.fetch': 'Function to fetch data',
        'rules.get_rules': 'Rules for the rules engine',
        'actions.get_actions': 'Actions to take for dats',
        }
    for attribute, desc in reqs.items():
        if not hasattr(module, attribute):
            located = locate(seed+'.'+attribute)
            if located is None:
                print(f'{Bcolors.FAIL} - {Bcolors.BOLD}{seed}.{attribute}{Bcolors.ENDC} not found ({desc})')


def check_executable(executable: str) -> bool:
    """Check if executable is installed."""
    return which(executable) is not None or which(executable + '.exe') is not None


def check_module(seed: str, module: object, *, repair: bool=False) -> None:  # noqa: ARG001
    """Check if all dependencies are installed."""
    # TODO(laromicas): Add repair functionality
    if not module:
        module = locate(seed)
    check_module_attributes(seed, module)
    requirements = getattr(module, '__requirements__', None)
    if requirements and 'executables' in requirements:
        for executable in requirements['executables']:
            if not check_executable(executable):
                seed_name = seed.replace(f'{__app_name__}_seed_', '')
                print(f'{seed_name} - {Bcolors.FAIL}{executable}{Bcolors.ENDC} not found.')
