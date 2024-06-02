import configparser
import json
import logging
import os
import re
import sys
from pathlib import Path
from venv import logger

from datoso import ROOT_FOLDER, __app_name__
from datoso.commands.doctor import check_module, check_seed
from datoso.commands.seed import Seed
from datoso.configuration import config
from datoso.database.models.dat import Dat
from datoso.helpers import Bcolors, FileUtils
from datoso.helpers.plugins import installed_seeds, seed_description
from datoso.repositories.dedupe import Dedupe
from datoso.seeds.rules import Rules
from datoso.seeds.unknown_seed import detect_seed


def command_deduper(args) -> None:
    """Deduplicate dats, removes duplicates from input dat existing in parent dat"""
    if not args.parent and args.input.endswith(('.dat', '.xml')):
        print('Parent dat is required when input is a dat file')
        sys.exit(1)
    if args.dry_run:
        logger.setLevel(logging.DEBUG)
    merged = Dedupe(args.input, args.parent)
    merged.dedupe()
    if args.output and not args.dry_run:
        merged.save(args.output)
    elif not args.dry_run:
        merged.save()
    logging.info('%s File saved to %s %s',
                 Bcolors.OKBLUE,
                 args.output if args.output else args.input,
                 Bcolors.ENDC,
                 )


def command_import(_) -> None:
    """Make changes in dat config"""
    dat_root_path = config['PATHS']['DatPath']

    if not dat_root_path or not Path(dat_root_path).exists():
        print(f'{Bcolors.FAIL}Dat root path not set or does not exist{Bcolors.ENDC}')
        sys.exit(1)

    rules = Rules().rules

    dats = { str(x):None for x in Path(dat_root_path).rglob('*.[dD][aA][tT]') }

    if config['IMPORT'].get('IgnoreRegEx'):
        ignore_regex = re.compile(config['IMPORT']['IgnoreRegEx'])
        dats = [ dat for dat in dats if not ignore_regex.match(dat) ]

    fromhere = ''
    found = False
    for dat_name in dats:
        if fromhere in (dat_name, ''):
            found = True
        if not found:
            continue
        print(f'{dat_name} - ', end='')
        seed, _class = detect_seed(dat_name, rules)
        print(f'{seed} - {_class.__name__ if _class else None}')
        if _class:
            dat = _class(file=dat_name)
            dat.load()
            database = Dat(**{**dat.dict(), 'seed': seed, 'new_file': dat_name})
            database.save()
            database.flush()


def command_dat(args):
    """Make changes in dat config"""
    from datoso.commands.helpers.dat import helper_command_dat
    helper_command_dat(args)


def command_seed_installed(_) -> None:
    """List available seeds"""
    print('Installed seeds:')
    description_len = 60
    for seed, seed_module in installed_seeds().items():
        description = seed_description(seed_module)
        description = {description[0:description_len]+'...' if len(description) > description_len else description}
        seed_name = seed[12:]
        print(f'* {Bcolors.OKGREEN}{seed_name}{Bcolors.ENDC} - {description}')


def command_seed_details(args) -> None:
    module = None
    for seed, seed_module in installed_seeds().items():
        if seed == f'{__app_name__}_seed_{args.seed}':
            module = seed_module
            break
    if not module:
        print(f'Seed {Bcolors.FAIL}{args.seed}{Bcolors.ENDC} not installed')
        sys.exit(1)
    print(f'Seed {Bcolors.OKGREEN}{args.seed}{Bcolors.ENDC} details:')
    print(f'  * Name: {module.__name__}')
    print(f'  * Version: {module.__version__}')
    print(f'  * Author: {module.__author__}')
    print(f'  * Description: {module.__description__}')


def command_seed(args) -> None:
    """Commands with the seed (must be installed)"""
    from datoso.commands.helpers.seed import command_seed_all, command_seed_parse_actions
    command_seed_parse_actions(args)
    if args.seed == 'all':
        command_seed_all(args, command_seed)
        sys.exit(0)
    if getattr(args, 'details', False):
        command_seed_details(args)
    else:
        seed = Seed(name=args.seed)
        if getattr(args, 'fetch', False):
            message = f'{Bcolors.OKCYAN}Fetching seed {Bcolors.OKGREEN}{args.seed}{Bcolors.ENDC}'
            print('='*(len(message)-14))
            print(message)
            print('='*(len(message)-14))
            if seed.fetch():
                print(f'Errors fetching {Bcolors.FAIL}{args.seed}{Bcolors.ENDC}')
                print('Please enable logs for more information or use -v parameter')
                command_doctor(args)
                sys.exit(1)
            print(f'{Bcolors.OKBLUE}Finished fetching {Bcolors.OKGREEN}{args.seed}{Bcolors.ENDC}')
        if getattr(args, 'process', False):
            message = f'{Bcolors.OKCYAN}Processing seed {Bcolors.OKGREEN}{args.seed}{Bcolors.ENDC}'
            print('='*(len(message)-14))
            print(message)
            print('='*(len(message)-14))
            if seed.process_dats(fltr=getattr(args, 'filter', None), actions_to_execute=args.actions):
                print(f'Errors processing {Bcolors.FAIL}{args.seed}{Bcolors.ENDC}')
                print('Please enable logs for more information or use -v parameter')
                command_doctor(args)
                sys.exit(1)
            print(f'{Bcolors.OKBLUE}Finished processing {Bcolors.OKGREEN}{args.seed}{Bcolors.ENDC}')


def command_config_save(args) -> None:
    """Save config to file"""
    config_file = Path('~/.config/datoso/datoso.config').expanduser() \
        if args.directory == '~' \
        else Path.cwd() / '.datosorc'
    with open(config_file, 'w', encoding='utf-8') as file:
        config.write(file)
    print(f'Config saved to {Bcolors.OKGREEN}{config_file}{Bcolors.ENDC}')


def command_config_set(args) -> None:
    """Set config value, if global is set, it will be set in datoso.ini file"""
    myconfig = args.set[0].split('.')
    expected_config_array_len = 2
    if len(myconfig) != expected_config_array_len:
        print(f'{Bcolors.FAIL}Invalid config key, must be in <SECTION>.<Option> format. {Bcolors.ENDC}')
        sys.exit(1)
    if myconfig[1] not in config[myconfig[0]]:
        print(f'{Bcolors.FAIL}Invalid config option. {Bcolors.ENDC}')
        sys.exit(1)

    newconfig = configparser.ConfigParser(comment_prefixes='/', allow_no_value=True)
    newconfig.optionxform = lambda option: option
    if getattr(args, 'global', False):
        file = Path(ROOT_FOLDER) / 'datoso.ini'
    else:
        file = Path.cwd() / '.datosorc'
        if not Path.is_file(file):
            file = Path('~/datosorc').expanduser()
    newconfig.read(file)
    if not newconfig.has_section(myconfig[0]):
        newconfig.add_section(myconfig[0])
    newconfig[myconfig[0]][myconfig[1]] = args.set[1]
    with open(file, 'w', encoding='utf-8') as file:
        newconfig.write(file)
    if getattr(args, 'global', False):
        print(f'{Bcolors.OKGREEN}Global config {Bcolors.OKCYAN}{myconfig[0]}.{myconfig[1]}{Bcolors.OKGREEN}' \
            f' set to {Bcolors.OKBLUE}{args.set[1]}{Bcolors.ENDC}')
    else:
        print(f'{Bcolors.OKGREEN}Local Config {Bcolors.OKCYAN}{myconfig[0]}.{myconfig[1]}{Bcolors.OKGREEN}' \
            f' set to {Bcolors.OKBLUE}{args.set[1]}{Bcolors.ENDC}')


def command_config_get(args) -> None:
    """Get active config value"""
    myconfig = args.get.split('.')
    expected_config_array_len = 2
    if len(myconfig) != expected_config_array_len:
        print(myconfig)
        print(f'{Bcolors.FAIL}Invalid config key, must be in <SECTION>.<Option> format. {Bcolors.ENDC}')
        sys.exit(1)
    if myconfig[1] not in config[myconfig[0]]:
        print(f'{Bcolors.FAIL}Invalid config option. {Bcolors.ENDC}')
        sys.exit(1)
    print(config[myconfig[0]][myconfig[1]])


def command_config_rules_update(args) -> None:
    """Update rules from google sheet"""
    from datoso.database.seeds import dat_rules
    print('Updating rules')
    try:
        dat_rules.import_dats()
        print('Rules updated')
    except Exception as exc:
        print(f'{Bcolors.FAIL}Error updating rules{Bcolors.ENDC}')
        print(exc)
        print('Please enable logs for more information or use -v parameter')
        command_doctor(args)


def command_config_mia_update(args) -> None:
    """Update rules from google sheet"""
    from datoso.database.seeds import mia
    print('Updating MIA')
    try:
        mia.import_mias()
        print('MIA updated')
    except Exception as exc:
        print(f'{Bcolors.FAIL}Error updating MIA{Bcolors.ENDC}')
        print(exc)
        print('Please enable logs for more information or use -v parameter')
        command_doctor(args)


def command_config(args) -> None:
    """Config commands"""
    if args.save:
        command_config_save(args)
    elif args.set:
        command_config_set(args)
    elif args.get:
        command_config_get(args)
    elif args.rules_update:
        command_config_rules_update(args)
    elif args.mia_update:
        command_config_mia_update(args)
    else:
        config_dict = {s:dict(config.items(s)) for s in config.sections()}
        print(json.dumps(config_dict, indent=4))


def command_list(_):
    """List installed seeds"""
    description_len = 60
    for seed, seed_class in installed_seeds().items():
        description = seed_class.description()
        print(f'* {Bcolors.OKCYAN}{seed}{Bcolors.ENDC} - ' \
              f'{description[0:description_len] if len(description) > description_len else description}...')

def command_doctor(args):
    """Doctor installed seeds"""
    if getattr(args, 'seed', False):
        seed = check_seed(args.seed)
        if not seed:
            print(f'Module Seed {Bcolors.FAIL}  - {Bcolors.BOLD}{args.seed}{Bcolors.ENDC} not found')
            sys.exit(1)
        seed = seed if args.seed.startswith('datoso_seed_') else f'datoso_seed_{args.seed}'
        seeds = {seed: None}
    else:
        seeds = installed_seeds()
    for seed, module in seeds.items():
        print(f'Checking seed {Bcolors.OKCYAN}{seed}{Bcolors.ENDC}')
        check_module(seed, module, args.repair)

def command_log(_):
    log_path = FileUtils.parse_path(config.get('PATHS','DatosoPath', fallback='~/.datoso'))
    logfile = log_path / config['LOG'].get('LogFile', 'datoso.log')
    os.system(f'cat {logfile}') # noqa: S605
