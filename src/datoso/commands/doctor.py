"""Check if all dependencies are installed"""

import os
import re
import subprocess
import sys
from shutil import which
import pkg_resources
from datoso import __app_name__
from datoso.commands.list import installed_seeds
from datoso.configuration import SEEDS_FOLDER
from datoso.helpers import Bcolors

ignore_packages = ['pyOpenSSL', 'PySocks']


# def check_seed(seed):
#     """ Check if seed is installed """
#     return os.path.isdir(os.path.join(SEEDS_FOLDER, seed))

def check_seed(seed):
    """ Check if seed is installed """
    return f'{__app_name__}_seed_{seed}' in installed_seeds()


def check_version(detected, required, expression):
    """ Check if version of required package is correct """
    detected = pkg_resources.parse_version(detected)
    required = pkg_resources.parse_version(required)
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

def required_packages(seed, installed_pkgs):
    """ Check if all required packages are installed """
    fixable = []
    not_fixable = []
    if os.path.isfile(os.path.join(SEEDS_FOLDER, seed, 'requirements.txt')):
        with open(os.path.join(SEEDS_FOLDER, seed, 'requirements.txt'), 'r', encoding='utf-8') as req:
            for line in req:
                line = line.strip()
                if line.startswith('#') or line == '':
                    continue
                line0 = re.split('[>=<]', line)
                line0 = [x for x in line0 if x]
                if line0[0] in ignore_packages:
                    continue
                if line0[0] not in installed_pkgs:
                    fixable.append(line)
                    continue
                if len(line0) > 1:
                    expression = ''.join(re.findall('[>=<]', line))
                    # line0[1] = expression
                    if not check_version(detected=installed_pkgs[line0[0]], required=line0[1], expression=expression):
                        not_fixable.append((line, installed_pkgs[line0[0]]))
    return fixable, not_fixable

def install(package):
    """ Install package """
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def check_main_executables():
    """ Check if all main executables are installed """
    req_executables = {
        'wget': 'wget',
        'unzip': 'unzip',
        '7z': 'p7zip',
        'geckodriver': 'geckodriver',
        'aria2c': 'aria2',
    }
    for exe, pkg in req_executables.items():
        if which(exe) is None and which(exe + '.exe') is None:
            print(f'{Bcolors.FAIL}  - {Bcolors.BOLD}{exe}{Bcolors.ENDC} not found (install {pkg})')


def check_needed_files(seed):
    """ Check if all needed files are present """
    req_files = {
        '__init__.py': 'Namespace initialization file',
        'fetch': 'Fetch script',
        'actions.json': 'json with actions to execute to process the data',
        'rules.json': 'json with rules to detect the datafile seed',
        }
    for file, desc in req_files.items():
        if not os.path.isfile(os.path.join(SEEDS_FOLDER, seed, file)):
            print(f'{Bcolors.FAIL}  - {Bcolors.BOLD}{file}{Bcolors.ENDC} not found ({desc})')


def check_dependencies(seed, repair=False):
    """ Check if all dependencies are installed """
    installed_pkgs = {pkg.key: pkg.version for pkg in pkg_resources.working_set} #pylint: disable=not-an-iterable
    print(f'* {Bcolors.OKCYAN}{seed}{Bcolors.ENDC}')
    # check_installed_packages(seed, installed_pkgs)
    fixable, not_fixable = required_packages(seed, installed_pkgs)
    if not_fixable:
        print(f'{Bcolors.FAIL}  - Not fixable requirements:{Bcolors.ENDC}')
        for line in not_fixable:
            print(f'    - {line[0]} (detected {line[1]})')
    if fixable:
        print(f'{Bcolors.WARNING}  - Requirements not found:{Bcolors.ENDC}')
        for line in fixable:
            print(f'    - {line}')
        if repair:
            print(f'{Bcolors.OKGREEN}  - Installing requirements:{Bcolors.ENDC}')
            for line in fixable:
                print(f'    - {line}')
                install(line)
    if not fixable and not not_fixable:
        print(f'{Bcolors.OKGREEN}  - All requirements installed{Bcolors.ENDC}')
    check_needed_files(seed)
