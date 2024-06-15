"""Helper functions for the seed command."""
import re
import sys
from argparse import Namespace
from collections.abc import Callable

from datoso.commands.seed import Seed
from datoso.configuration import config
from datoso.configuration.configuration import get_seed_name
from datoso.helpers import Bcolors
from datoso.helpers.plugins import installed_seeds


def command_seed_parse_actions(args: Namespace) -> None:
    """Parse the actions."""
    if args.actions and len(args.actions) == 1:
            args.actions = args.actions[0].split(',')
    if args.seed != 'all':
        seed_object = Seed(name=args.seed)
        if seed_object.parse_args:
            seed_object.parse_args(args)
    if not any([getattr(args, 'fetch', False), getattr(args, 'process', False), getattr(args, 'details', False)]):
        print(f'{Bcolors.FAIL}No action specified{Bcolors.ENDC} (fetch, process, details)')
        sys.exit(1)

def command_seed_all(args: Namespace, command_seed: Callable) -> None:
    """Run the seed command for all seeds."""
    for seed in installed_seeds():
        seed_name = get_seed_name(seed)
        if (args.exclude and seed_name in args.exclude) or \
            (args.only and seed_name not in args.only):
            continue
        if config['PROCESS'].get('SeedIgnoreRegEx'):
            ignore_regex = re.compile(config['PROCESS']['SeedIgnoreRegEx'])
            if ignore_regex.match(seed_name):
                continue
        args.seed = seed_name
        command_seed(args)
