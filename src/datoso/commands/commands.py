import configparser
import json
import logging
import os
import re
import sys
from pathlib import Path
from venv import logger

from tabulate import tabulate

from datoso import ROOT_FOLDER, __app_name__
from datoso.commands.doctor import check_module, check_seed
from datoso.commands.seed import Seed
from datoso.configuration import config
from datoso.configuration.configuration import get_seed_name
from datoso.database.models.datfile import Dat
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
            database = Dat(seed=seed, new_file=dat_name, **dat.dict())
            database.save()
            database.flush()


def command_dat(args):
    """Make changes in dat config"""

    def print_dats(dats, fields = None):
        """Print dats"""
        output = []
        fields = fields if fields else ['seed', 'name', 'status']
        for field in ['seed', 'name']:
            if field not in fields:
                fields.append(field)
        for dat in dats:
            new_dat = { k:dat[k] for k in fields if dat.get(k) }
            if 'status' in fields:
                new_dat['status'] = dat.get('status', 'enabled') or 'enabled'
            output.append(new_dat)
        if getattr(args, 'only_names', False):
            for dat in output:
                print(f"{dat['seed']}:{dat['name']}")
            return
        print(tabulate(output, headers='keys', tablefmt='psql'))

    from tinydb import Query

    query = Query()
    if args.dat_name:
        splitted = args.dat_name.split(':')
        expected_dat_array_len = 2
        if len(splitted) != expected_dat_array_len:
            print(f'{Bcolors.WARNING}Invalid dat name, must be in format "seed:name"{Bcolors.ENDC}')
            print(f'Showing results for filter: {Bcolors.OKCYAN}name~={args.dat_name}{Bcolors.ENDC}')
            print('--------------------------------------------------------------')
            name = args.dat_name
            result = Dat.search(query.name.matches(r'^.*' + name + r'.*', flags=re.IGNORECASE))
            if args.fields:
                print_dats(result, fields=args.fields)
            elif args.details:
                print_dats(result, fields=['name', 'modifier', 'company', 'system', 'seed', 'date',
                                           'path', 'system_type', 'automerge', 'parent'])
            else:
                print_dats(result)
            return
        seed, name = splitted
        dat = Dat(seed=seed, name=name)
        result = dat.get_one()
        if not result:
            print(f'{Bcolors.FAIL}Dat not found{Bcolors.ENDC}')
            sys.exit(1)
        if args.set:
            if '=' not in args.set:
                print(f'{Bcolors.FAIL}Invalid set command, must be in format "variable=value"{Bcolors.ENDC}')
                sys.exit(1)
            key, value = args.set.split('=') if '=' in args.set else (args.set, 'True')
            if value.isdigit():
                value = int(value)
            if value.lower() == 'true':
                value = True
            if value.lower() in ('none', 'null'):
                value = None
            dat.update({key: value}, doc_ids=[result.doc_id])
            dat.flush()
            print(f'{Bcolors.OKGREEN}Dat {Bcolors.OKCYAN}{seed}:{name}{Bcolors.OKGREEN} ' \
                  f'{key} set to {Bcolors.OKBLUE}{value}{Bcolors.ENDC}')
            sys.exit(0)
        if args.unset:
            key = args.unset
            value = None
            dat.update({key: value}, doc_ids=[result.doc_id])
            dat.flush()
            print(f'{Bcolors.OKGREEN}Dat {Bcolors.OKCYAN}{seed}:{name}{Bcolors.OKGREEN} ' \
                  f'{key} set to {Bcolors.OKBLUE}{value}{Bcolors.ENDC}')
            sys.exit(0)
        if args.delete:
            dat.remove(doc_ids=[result.doc_id])
            dat.flush()
            print(f'{Bcolors.OKGREEN}Dat {Bcolors.OKCYAN}{seed}:{name}{Bcolors.OKGREEN} removed{Bcolors.ENDC}')
            sys.exit(0)
        if args.mark_mias:
            from datoso.mias.mia import mark_mias
            mark_mias(dat_file=result['new_file'])
            print(f'{Bcolors.OKGREEN}Set Dats {Bcolors.OKCYAN}{seed}:{name}{Bcolors.OKGREEN} marked MIAs{Bcolors.ENDC}')
            sys.exit(0)
        if args.fields:
            print_dats(result, fields=args.fields)
        elif args.details:
            print_dats([result], fields=['name', 'modifier', 'company', 'system', 'seed', 'date', 'path', 'system_type', 'full_name', 'automerge', 'parent'])
        else:
            print_dats([result])
    elif args.all:
        # Show all dats
        print_dats(dat.all())

    elif args.find:
        # Find dats TODO: finish
        print(f'Showing results for filter: {Bcolors.OKCYAN}{args.find}{Bcolors.ENDC}')
        print('--------------------------------------------------------------')
        name, value = args.find.split('=')
        from tinydb import where
        result = Dat.search(where(name) == value)
        print_dats(result)


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
    def parse_actions(args):
        if args.actions and len(args.actions) == 1:
                args.actions = args.actions[0].split(',')
        if args.seed != 'all':
            seed_object = Seed(name=args.seed)
            if seed_object.parse_args:
                seed_object.parse_args(args)
        if not any([getattr(args, 'fetch', False), getattr(args, 'process', False), getattr(args, 'details', False)]):
            print(f'{Bcolors.FAIL}No action specified{Bcolors.ENDC} (fetch, process, details)')
            sys.exit(1)
    parse_actions(args)
    if args.seed == 'all':
        for seed in installed_seeds():
            seed_name = get_seed_name(seed)
            if args.exclude and seed_name in args.exclude:
                continue
            if args.only and seed_name not in args.only:
                continue
            if config['PROCESS'].get('SeedIgnoreRegEx'):
                ignore_regex = re.compile(config['PROCESS']['SeedIgnoreRegEx'])
                if ignore_regex.match(seed_name):
                    continue
            args.seed = seed_name
            command_seed(args)
        sys.exit(0)
    seed = Seed(name=args.seed)
    if getattr(args, 'details', False):
        command_seed_details(args)
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
    config_file = Path('~/datosorc').expanduser() if args.directory == '~' else Path.cwd() / '.datosorc'
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
        print(f'{Bcolors.OKGREEN}Global config {Bcolors.OKCYAN}{myconfig[0]}.{myconfig[1]}{Bcolors.OKGREEN} set to {Bcolors.OKBLUE}{args.set[1]}{Bcolors.ENDC}')
    else:
        print(f'{Bcolors.OKGREEN}Local Config {Bcolors.OKCYAN}{myconfig[0]}.{myconfig[1]}{Bcolors.OKGREEN} set to {Bcolors.OKBLUE}{args.set[1]}{Bcolors.ENDC}')


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
    log_path = FileUtils.parse_folder(config.get('PATHS','DatosoPath', fallback='~/.datoso'))
    logfile = log_path / config['LOG'].get('LogFile', 'datoso.log')
    os.system(f'cat {logfile}')
