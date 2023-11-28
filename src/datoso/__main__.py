"""Main entry point for datoso"""
import configparser
import json
import logging
import os
from pathlib import Path
import re
import sys
import argparse
from venv import logger
from tabulate import tabulate
from datoso.configuration.configuration import get_seed_name
from datoso.configuration.logger import enable_logging, set_verbosity
from datoso.database.models.datfile import Dat

from datoso import __version__, __app_name__, ROOT_FOLDER
from datoso.helpers import Bcolors, FileUtils
from datoso.configuration import config

from datoso.helpers.plugins import installed_seeds, seed_description
from datoso.commands.doctor import check_module, check_seed
from datoso.commands.seed import Seed
from datoso.repositories.dedupe import Dedupe
from datoso.seeds.rules import Rules
from datoso.seeds.unknown_seed import detect_seed

#---------Boilerplate to check python version ----------
if sys.version_info < (3, 10):
    print("This is a Python 3 script. Please run it with Python 3.9 or above")
    sys.exit(1)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments

    Returns:
        argparse.Namespace: An object to take the attributes.
    """
    #pylint: disable=too-many-locals,too-many-statements
    parser = argparse.ArgumentParser(description='Update dats from different sources.')
    subparser = parser.add_subparsers(help='sub-command help')

    parser.add_argument('-v', '--version', action='store_true', help='show version')

    parser_log = subparser.add_parser('log', help='Show log')
    parser_log.set_defaults(func=command_log)

    parser_config = subparser.add_parser('config', help='Show configuration')
    parser_config.add_argument('-s', '--save', action='store_true', help='Save configuration to .datosorc')
    parser_config.add_argument('-d', '--directory', default='~', choices=['~', '.'], help='Directory to save .datosorc')
    parser_config.set_defaults(func=command_config)
    parser_config.add_argument('-ru', '--rules-update', action='store_true', help='Update system rules from GoogleSheets Url')

    group_save = parser_config.add_mutually_exclusive_group()
    group_save.add_argument('--set', nargs=2, metavar=('configuration', 'value'), help='Set Configuration Option separated by point with new value e.g. <GENERAL.Overwrite> <false>')
    group_save.add_argument('--get', metavar=('configuration'), help='Get value of Configuration Option.')
    parser_config.add_argument('-g','--global', action='store_true', help='When set, saves to global config, else to `.datosorc`')

    parser_doctor = subparser.add_parser('doctor', help='Doctor installed seeds')
    parser_doctor.add_argument('seed', nargs='?', help='Seed to doctor')
    parser_doctor.set_defaults(func=command_doctor)
    parser_doctor.add_argument('-r', '--repair', action='store_true', help='Try to repair seed(s)')

    parser_dat = subparser.add_parser('dat', help='Changes configuration in current dats')
    parser_dat.add_argument('command', nargs='?', help='Command to execute')

    group_dat = parser_dat.add_mutually_exclusive_group(required=True)
    group_dat.add_argument('-d', '--dat-name', help='Select dat to update/check, must be in format "seed:name"')
    group_dat.add_argument('-f', '--find', help='Select dats based on filter, they are "<field><operator><value>;...", valid operators are: =, !=, and ~=')
    group_dat.add_argument('-a', '--all', help='Show all dats', action='store_true')

    group_dat_action = parser_dat.add_mutually_exclusive_group(required=False)
    group_dat_action.add_argument('-dt', '--details', help='Show details of dat', action='store_true')
    group_dat_action.add_argument('-s', '--set', help='Manually set variable, must be in format "variable=value"')
    group_dat_action.add_argument('--delete', action='store_true', default=False, help='Delete Dat')

    parser_dat.add_argument('-on', '--only-names', action='store_true', help='Only show names')

    parser_dat.set_defaults(func=command_dat)

    # Seed admin commands
    parser_seed = subparser.add_parser('seed', help='Seed admin commands')
    subparser_seed = parser_seed.add_subparsers(help='sub-command help')

    parser_available = subparser_seed.add_parser('installed', help='List installed seeds')
    parser_available.set_defaults(func=command_seed_installed)

    parser_details = subparser_seed.add_parser('details', help='Show details of seed')
    parser_details.add_argument('seed', help='Seed to show details of')
    parser_details.set_defaults(func=command_seed_details)

    parser_import = subparser.add_parser('import', help='Import dats from existing romvault')
    parser_import.set_defaults(func=command_import)

    parser_deduper = subparser.add_parser('deduper', help='Deduplicate dats, removes duplicates from input dat existing in parent dat')
    parser_deduper.add_argument('-i', '--input', required=True, help='Input dat file e.g. "redump:psx_child" or "/mnt/roms/redump_psx_child.dat"')
    parser_deduper.add_argument('-p', '--parent', default=None, help='Parent dat file e.g. "redump:psx" or "/mnt/roms/redump_psx.dat" if not set, parent is taken from input dat with prescanned dats')
    parser_deduper.add_argument('-o', '--output', default=None, help='If different from input.dat, must be a file path e.g. "/mnt/roms/redump_psx_child_deduped.dat"')
    parser_deduper.add_argument('-dr', '--dry-run', action='store_true', help='Do not write output file, just show actions')

    parser_deduper.set_defaults(func=command_deduper)


    # Seed commands
    for seed, _ in list(installed_seeds().items()) + [('all', 'All seeds')]:
        seed = get_seed_name(seed)
        parser_command = subparser.add_parser(seed, help=f'Update seed {seed}')
        parser_command.set_defaults(func=command_seed, seed=seed)
        parser_command.add_argument('-d', '--details', action='store_true', help='Show details of seed')
        parser_command.add_argument('-f', '--fetch', action='store_true', help='Fetch seed')
        parser_command_process = parser_command.add_argument_group('process')
        parser_command_process.add_argument('-p', '--process', action='store_true', help='Process dats from seed')
        parser_command_process.add_argument('-a', '--actions', action="append", help='Action to execute')
        parser_command_process.add_argument('-fd', '--filter', help='Filter dats to process')
        if seed == 'all':
            parser_command.add_argument('-e', '--exclude', action='append', help='Exclude seed or seeds (only work with all)')
            parser_command.add_argument('-o', '--only', action='append', help='Only seed or seeds (only work with all)')

    # Common arguments
    subparsers = [subparser, subparser_seed]
    for subpars in subparsers:
        for subpar in subpars.choices.values():
            subpar.add_argument('-v', '--verbose', action='store_true', help='verbose output')
            subpar.add_argument('-q', '--quiet', action='store_true', help='quiet output')
            subpar.add_argument('-nc', '--no-color', action='store_true', help='disable color output')
            subpar.add_argument('-l', '--logging', action='store_true', help='enable logging')

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
    args = parser.parse_args()
    initial_setup(args)
    return args


def initial_setup(args) -> None:
    """ Initial setup of datoso from command line arguments """
    if getattr(args, 'version', False):
        print(__version__)
        sys.exit()
    if getattr(args, 'no_color', False) or os.name == 'nt':
        Bcolors.no_color()
    if getattr(args, 'quiet', False):
        set_verbosity(logging.WARNING)
        config['COMMAND']['Quiet'] = 'true'
    if getattr(args, 'verbose', False):
        set_verbosity(logging.DEBUG)
        config['COMMAND']['Verbose'] = 'true'
    if getattr(args, 'logging', False):
        enable_logging()


def command_deduper(args) -> None:
    """ Deduplicate dats, removes duplicates from input dat existing in parent dat """
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
    logging.info(f'{Bcolors.OKBLUE} File saved to {args.output if args.output else args.input}{Bcolors.ENDC}')


def command_import(_) -> None:
    """ Make changes in dat config """
    dat_root_path = config['PATHS']['DatPath']

    if not dat_root_path or not Path(dat_root_path).exists():
        print(f'{Bcolors.FAIL}Dat root path not set or does not exist{Bcolors.ENDC}')
        sys.exit(1)

    rules = Rules().rules

    dats = { str(x):None for x in Path(dat_root_path).rglob("*.[dD][aA][tT]") }

    if config['IMPORT'].get('IgnoreRegEx'):
        ignore_regex = re.compile(config['IMPORT']['IgnoreRegEx'])
        dats = [ dat for dat in dats if not ignore_regex.match(dat) ]

    fromhere = ''
    found = False
    for dat_name in dats:
        if dat_name == fromhere or fromhere == '':
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
            database.close()


def command_dat(args):
    """ Make changes in dat config """

    def print_dats(dats, fields = ['seed', 'name', 'status']):
        """ Print dats """
        output = []
        for dat in dats:
            new_dat = { k:dat[k] for k in fields if k in dat and dat[k] }
            new_dat['status'] = dat['status'] if 'status' in dat else 'enabled'
            output.append(new_dat)
        if getattr(args, 'only_names', False):
            for dat in output:
                print(f"{dat['seed']}:{dat['name']}")
            return
        print(tabulate(output, headers='keys', tablefmt='psql'))

    from datoso.database import DB
    from tinydb import Query
    query = Query()
    table = DB.table('dats')
    if args.dat_name:
        splitted = args.dat_name.split(':')
        if len(splitted) != 2:
            print(f'{Bcolors.WARNING}Invalid dat name, must be in format "seed:name"{Bcolors.ENDC}')
            print(f'Showing results for filter: {Bcolors.OKCYAN}name~={args.dat_name}{Bcolors.ENDC}')
            print('--------------------------------------------------------------')
            name = args.dat_name
            result = table.search(query.name.matches(r'^.*' + name + r'.*', flags=re.IGNORECASE))

            print_dats(result)

        else:
            seed, name = splitted
            result = table.get((query.name == name) & (query.seed == seed))
            if not result:
                print(f'{Bcolors.FAIL}Dat not found{Bcolors.ENDC}')
                sys.exit(1)
            if args.set:
                key, value = args.set.split('=') if '=' in args.set else (args.set, True)
                if value.isdigit():
                    value = int(value)
                if value.lower() == 'true':
                    value = True
                table.update({key: value}, doc_ids=[result.doc_id])
                table.storage.flush()
                print(f'{Bcolors.OKGREEN}Dat {Bcolors.OKCYAN}{seed}:{name}{Bcolors.OKGREEN} {key} set to {Bcolors.OKBLUE}{value}{Bcolors.ENDC}')
                sys.exit(0)
            # if args.unset:
            #     # TODO: unset
            #     key = args.unset
            #     table.update({key: value}, doc_ids=[result.doc_id])
            #     table.storage.flush()
            #     print(f'{Bcolors.OKGREEN}Dat {Bcolors.OKCYAN}{seed}:{name}{Bcolors.OKGREEN} {key} set to {Bcolors.OKBLUE}{value}{Bcolors.ENDC}')
            #     sys.exit(0)
            if args.delete:
                table.remove(doc_ids=[result.doc_id])
                table.storage.flush()
                print(f'{Bcolors.OKGREEN}Dat {Bcolors.OKCYAN}{seed}:{name}{Bcolors.OKGREEN} removed{Bcolors.ENDC}')
                sys.exit(0)
            if args.details:
                print_dats([result], fields=["name", "modifier", "company", "system", "seed", "date", "path", "system_type", "full_name", "automerge", "parent"])
            else:
                print_dats([result])
    elif args.all:
        # Show all dats
        print_dats(table.all())

    elif args.find:
        # Find dats TODO: finish
        print(f'Showing results for filter: {Bcolors.OKCYAN}{args.find}{Bcolors.ENDC}')
        print('--------------------------------------------------------------')
        name, value = args.find.split('=')
        from tinydb import where
        result = table.search(where(name) == value)
        print_dats(result)


def command_seed_installed(_) -> None:
    """ List available seeds """
    print('Installed seeds:')
    for seed, seed_module in installed_seeds().items():
        description = seed_description(seed_module)
        description = {description[0:60]+'...' if len(description) > 60 else description}
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
    """ Commands with the seed (must be installed) """
    def parse_actions(args):
        if args.actions and len(args.actions) == 1:
                args.actions = args.actions[0].split(',')
    parse_actions(args)
    if args.seed == 'all':
        for seed, _ in installed_seeds().items():
            seed = get_seed_name(seed)
            if args.exclude and seed in args.exclude:
                continue
            if args.only and seed not in args.only:
                continue
            if config['PROCESS'].get('SeedIgnoreRegEx'):
                ignore_regex = re.compile(config['PROCESS']['SeedIgnoreRegEx'])
                if ignore_regex.match(seed):
                    continue
            args.seed = seed
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
    """ Save config to file """
    config_file = os.path.expanduser('~/.datosorc') if args.directory == '~' else os.path.join(os.getcwd(), '.datosorc')
    with open(config_file, 'w', encoding='utf-8') as file:
        config.write(file)
    print(f'Config saved to {Bcolors.OKGREEN}{config_file}{Bcolors.ENDC}')


def command_config_set(args) -> None:
    """ Set config value, if global is set, it will be set in datoso.ini file """
    myconfig = args.set[0].split('.')
    if len(myconfig) != 2:
        print(f'{Bcolors.FAIL}Invalid config key, must be in <SECTION>.<Option> format. {Bcolors.ENDC}')
        sys.exit(1)
    if myconfig[1] not in config[myconfig[0]]:
        print(f'{Bcolors.FAIL}Invalid config option. {Bcolors.ENDC}')
        sys.exit(1)

    newconfig = configparser.ConfigParser(comment_prefixes='/', allow_no_value=True)
    newconfig.optionxform = lambda option: option
    if getattr(args, 'global', False):
        file = os.path.join(ROOT_FOLDER, 'datoso.ini')
    else:
        file = os.path.join(os.getcwd(), '.datosorc')
        if not os.path.isfile(file):
            file = os.path.expanduser('~/.datosorc')
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
    """ Get active config value """
    myconfig = args.get.split('.')
    if len(myconfig) != 2:
        print(myconfig)
        print(f'{Bcolors.FAIL}Invalid config key, must be in <SECTION>.<Option> format. {Bcolors.ENDC}')
        sys.exit(1)
    if myconfig[1] not in config[myconfig[0]]:
        print(f'{Bcolors.FAIL}Invalid config option. {Bcolors.ENDC}')
        sys.exit(1)
    print(config[myconfig[0]][myconfig[1]])


def command_config_rules_update(args) -> None:
    """ Update rules from google sheet """
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


def command_config(args) -> None:
    """ Config commands """
    if args.save:
        command_config_save(args)
    elif args.set:
        command_config_set(args)
    elif args.get:
        command_config_get(args)
    elif args.rules_update:
        command_config_rules_update(args)
    else:
        config_dict = {s:dict(config.items(s)) for s in config.sections()}
        print(json.dumps(config_dict, indent=4))


def command_list(_):
    """ List installed seeds """
    for seed, seed_class in installed_seeds().items():
        description = seed_class.description()
        print(f'* {Bcolors.OKCYAN}{seed}{Bcolors.ENDC} - {description[0:60] if len(description) > 60 else description}...')

def command_doctor(args):
    """ Doctor installed seeds """
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

def command_log(args):
    log_path = FileUtils.parse_folder(config.get('PATHS','DatosoPath', fallback='~/.datoso'))
    logfile = os.path.join(log_path, config['LOG'].get('LogFile', 'datoso.log'))
    os.system(f'cat {logfile}')

def main():
    """ Main function """
    from datoso.database.seeds.dat_rules import detect_first_run
    detect_first_run()
    args = parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
