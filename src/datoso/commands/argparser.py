"""Argument parser for datoso commands."""
from argparse import ArgumentParser

from datoso.commands.commands import (
    command_config,
    command_dat,
    command_deduper,
    command_doctor,
    command_import,
    command_log,
    command_seed,
    command_seed_details,
    command_seed_installed,
)
from datoso.commands.seed import Seed


def add_log_parser(subparser: ArgumentParser) -> None:
    """Log parser."""
    parser_log = subparser.add_parser('log', help='Show log')
    parser_log.set_defaults(func=command_log)

def add_config_parser(subparser: ArgumentParser) -> None:
    """Config parser."""
    parser_config = subparser.add_parser('config', help='Show configuration')
    parser_config.add_argument('-p', '--path', action='store_true', help='datoso config file')
    parser_config.add_argument('-s', '--save', action='store_true', help='Save configuration to .datosorc')
    parser_config.add_argument('-d', '--directory', default='~', choices=['~', '.'], help='Directory to save .datosorc')
    parser_config.set_defaults(func=command_config)
    parser_config.add_argument('-ru', '--rules-update', action='store_true',
                    help='Update system rules from GoogleSheets Url')
    parser_config.add_argument('-mu', '--mia-update', action='store_true', help='Update MIA from GoogleSheets Url')

    group_save = parser_config.add_mutually_exclusive_group()
    group_save.add_argument('--set', nargs=2, metavar=('configuration', 'value'),
                    help='Set Configuration Option separated by point with new value e.g. <PROCESS.Overwrite> <false>')
    group_save.add_argument('--get', metavar=('configuration'), help='Get value of Configuration Option.')
    where_group = parser_config.add_mutually_exclusive_group()
    where_group.add_argument('-g','--global', action='store_true',
                               help='When set, saves to global config, enabled by default')
    where_group.add_argument('-l','--local', action='store_true',
                    help='When set, saves to `.datosorc` in current directory, disabled by default')

def add_doctor_parser(subparser: ArgumentParser) -> None:
    """Doctor parser."""
    parser_doctor = subparser.add_parser('doctor', help='Doctor installed seeds')
    parser_doctor.add_argument('seed', nargs='?', help='Seed to doctor')
    parser_doctor.set_defaults(func=command_doctor)
    parser_doctor.add_argument('-r', '--repair', action='store_true', help='Try to repair seed(s)')

def add_dat_parser(subparser: ArgumentParser) -> None:
    """Dat parser."""
    parser_dat = subparser.add_parser('dat', help='Changes configuration in current dats')
    parser_dat.add_argument('command', nargs='?', help='Command to execute')

    group_dat = parser_dat.add_mutually_exclusive_group(required=True)
    group_dat.add_argument('-d', '--dat-name', help='Select dat to update/check, must be in format "seed:name"')
    group_dat.add_argument('-f', '--find',
        help='Select dats based on filter, they are "<field><operator><value>;...", valid operators are: =, !=, and ~=')
    group_dat.add_argument('-a', '--all', help='Show all dats', action='store_true')

    group_dat_action = parser_dat.add_mutually_exclusive_group(required=False)
    group_dat_action.add_argument('-dt', '--details', help='Show details of dat', action='store_true')
    group_dat_action.add_argument('-fi', '--fields', nargs='+', help='Fields to show, must be in format "fld1 fld2"',
            choices=[
                    'name', 'modifier', 'company', 'system', 'seed', 'date', 'path', 'system_type', 'full_name',
                    'automerge', 'parent', 'version', 'prefix', 'suffix', 'status', 'new_file', 'file', 'mias',
                    'static_path',
                ])
    group_dat_action.add_argument('-s', '--set', help='Manually set variable, must be in format "variable=value"')
    group_dat_action.add_argument('-u', '--unset', help='Manually unset variable')
    group_dat_action.add_argument('--delete', action='store_true', default=False, help='Delete Dat')
    group_dat_action.add_argument('--mark-mias', action='store_true', default=False, help='Mark Dat MIAs')

    parser_dat.add_argument('-on', '--only-names', action='store_true', help='Only show names')

    parser_dat.set_defaults(func=command_dat)

def add_seed_parser(subparser: ArgumentParser) -> None:
    """Seed parser."""
    parser_seed = subparser.add_parser('seed', help='Seed admin commands')
    subparser_seed = parser_seed.add_subparsers(help='sub-command help')

    parser_available = subparser_seed.add_parser('installed', help='List installed seeds')
    parser_available.set_defaults(func=command_seed_installed)

    parser_details = subparser_seed.add_parser('details', help='Show details of seed')
    parser_details.add_argument('seed', help='Seed to show details of')
    parser_details.set_defaults(func=command_seed_details)

def add_import_parser(subparser: ArgumentParser) -> None:
    """Import parser."""
    parser_import = subparser.add_parser('import', help='Import dats from existing romvault')
    parser_import.add_argument('-i', '--ignore', nargs='*', default=[], help='Ignore dats, can be used multiple times')
    parser_import.set_defaults(func=command_import)

def add_deduper_parser(subparser: ArgumentParser) -> None:
    """Deduper parser."""
    parser_deduper = subparser.add_parser('deduper',
                        help='Deduplicate dats, removes duplicates from input dat existing in parent dat')
    parser_deduper.add_argument('-i', '--input', required=True,
                        help='Input dat file e.g. "redump:psx_child" or "/mnt/roms/redump_psx_child.dat"')
    parser_merge = parser_deduper.add_mutually_exclusive_group(required=True)
    parser_merge.add_argument('-p', '--parent', default=None,
                help=('Parent dat file e.g. "redump:psx" or "/mnt/roms/redump_psx.dat" '
                    'if not set, parent is taken from input dat with prescanned dats'))
    parser_merge.add_argument('-au', '--auto-merge', action='store_true',
                help='Auto merge dats, removes duplicates from input dat')
    parser_deduper.add_argument('-o', '--output', default=None,
                help='If different from input.dat, must be a file path e.g. "/mnt/roms/redump_psx_child_deduped.dat"')
    parser_deduper.add_argument('-dr', '--dry-run', action='store_true',
                        help='Do not write output file, just show actions')

    parser_deduper.set_defaults(func=command_deduper)

def add_all_seed_parser(subparser: ArgumentParser) -> None:
    """All seed parser."""
    def parse_seed(seed_name: str, description: str, seed: Seed=None) -> None:
        parser_command = subparser.add_parser(seed_name, help=f'Seed {seed_name}, {description}')
        parser_command.set_defaults(func=command_seed, seed=seed_name)
        parser_command.add_argument('-d', '--details', action='store_true', help='Show details of seed')
        parser_command.add_argument('-f', '--fetch', action='store_true', help='Fetch seed')
        parser_command_process = parser_command.add_argument_group('process')
        parser_command_process.add_argument('-p', '--process', action='store_true', help='Process dats from seed')
        parser_command_process.add_argument('-a', '--actions', action='append', help='Action to execute')
        parser_command_process.add_argument('-fd', '--filter', help='Filter dats to process')
        if seed_name == 'all':
            parser_command.add_argument('-e', '--exclude', action='append',
                                        help='Exclude seed or seeds (only work with all)')
            parser_command.add_argument('-o', '--only', action='append', help='Only seed or seeds')
        else:
            parser_command_process.add_argument('-o', '--overwrite', action='store_true', help='Force overwrite dats')
            seed.args(parser_command)

    for seed in Seed.list_installed():
        parse_seed(seed.name, seed.description(), seed=seed)
    parse_seed('all', 'All seeds')
