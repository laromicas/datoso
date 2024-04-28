"""Fetch and Process Commands for Seeds"""
# ruff: noqa: ERA001
import re
from pathlib import Path

from datoso import __app_name__
from datoso.actions.processor import Processor
from datoso.configuration import config
from datoso.helpers import Bcolors, FileUtils
from datoso.helpers.executor import Command
from datoso.helpers.plugins import PluginType, installed_seeds

STATUS_TO_SHOW = ['Updated', 'Created', 'Error', 'Disabled', 'Deduped', 'No Action Taken, Newer Found']

class Seed:
    """Seed class"""

    name = None
    path = None
    module = None
    actions: dict = None
    config = None

    def __init__(self, **kwargs) -> None:
        self.__dict__.update(kwargs)
        if not self.name and self.module:
            self.name = self.module.__name__.split('_')[-1]
        self.full_name = f'{__app_name__}_{PluginType.SEED.value}_{self.name}'
        if not config.has_section(self.name.upper()):
            self.init_config()

    def get_actions(self):
        """Get actions"""
        actions = self.get_module('actions')
        self.config = config[self.name.upper()] if config.has_section(self.name.upper()) else None
        configs = []
        if actions:
            self.actions = actions.get_actions()
        for path, actions in self.actions.items():
            config_path = path.replace('{dat_origin}', self.name.upper()).replace('/', '.')
            if config.has_section(config_path):
                configs.append(config[config_path])
                for actions in self.actions.values():
                    new_steps = {action['action']: action for action in actions}
                    new_actions = []
                    if override_actions := config[config_path].get('OverrideActions'):
                        override_actions = override_actions.split(',')
                        for override_action in override_actions:
                            if override_action in new_steps:
                                new_actions.append(new_steps[override_action])
                            else:
                                new_actions.append({'action': override_action})


        # if configs:
            #     for path, actions in self.actions.items():
            #         config_path = path.replace('{dat_origin}', self.name.upper()).replace('/', '.')
            #         if config.has_section(config_path):

                    # action_name =
                    # for action_name, action_value in action.items():
                    #     if isinstance(action_value, str):
                    #         action[action_name] = action_value.format(**config)

            # if self.config and self.config.get('OverrideActions'):
            #     for path, actions in self.actions.items():
            #         for action in actions:
            #             if action.get('action') == 'Copy':
            #                 action['folder'] = action.get('folder', 'ToSort')
            #                 action['destination'] = action.get('destination', 'tmp')
            #             if action.get('action') == 'LoadDatFile':
            #                 action['_class'] = action.get('_class', None)
            # if self.config and self.config.get('Actions'):
            #     self.actions = self.config.get('Actions')

    def get_module(self, submodule=None):
        """Module"""
        try:
            self.module = __import__(self.full_name) if not self.module else self.module
            if submodule:
                return __import__(f'{self.full_name}.{submodule}', fromlist=[submodule])
        except ModuleNotFoundError:
            return None
        return self.module

    def description(self):
        """Description"""
        return self.get_module().__description__

    def fetch(self):
        """Fetch seed"""
        fetch = self.get_module('fetch')
        fetch.fetch()

    def args(self, args):
        """Args"""
        try:
            get_args = self.get_module('args')
        except AttributeError:
            return None
        return get_args.seed_args(args) if get_args else None

    def parse_args(self, args):
        """Args"""
        try:
            get_args = self.get_module('args')
        except AttributeError:
            return None
        return get_args.post_parser(args) if get_args else None

    def init_config(self):
        """Initial config"""
        try:
            get_args = self.get_module('args')
        except AttributeError:
            return
        if get_args:
            get_args.init_config()

    def format_actions(self, actions, data: dict | None = None):
        """Format actions."""
        data = data if data else {}
        for action in actions:
            for action_name, action_value in action.items():
                if isinstance(action_value, str):
                    action[action_name] = action_value.format(**data)
        return actions

    def process_dats(self, fltr=None, actions_to_execute=None):
        """Process dats."""
        def delete_line(line):
            # pylint: disable=expression-not-assigned
            [print('\b \b', end='') for x in range(len(line))]
            print(' ' * (len(line)), end='')
            print('\r', end='')
        def get_prefix(name) -> str:
            seed = self.get_module()
            return seed.__prefix__ if seed else name
        tmp_path = config['PATHS'].get('DownloadPath', 'tmp')
        dat_origin = FileUtils.parse_folder(tmp_path) / get_prefix(self.name) / 'dats'
        line = ''
        self.get_actions()
        for path, actions in self.actions.items():
            new_path = Path(path.format(dat_origin=dat_origin))
            actions = self.format_actions(actions, data={'dat_destination': config['PATHS'].get('DatPath', 'DatRoot')})
            # TODO(laromicas): override actions to process from config
            if actions_to_execute:
                actions = [x for x in actions if x['action'] in actions_to_execute]
            for file in new_path.iterdir() if new_path.is_dir() else []:
                if config['PROCESS'].get('DatIgnoreRegEx'):
                    ignore_regex = re.compile(config['PROCESS']['DatIgnoreRegEx'])
                    if ignore_regex.match(str(file)):
                        continue

                if (file.suffix not in ('.dat', '.xml') \
                    and not file.is_dir()) \
                    or (fltr and fltr not in str(file)):
                    continue

                if not config.getboolean('COMMAND', 'Quiet', fallback=False):
                    delete_line(line)
                    line = f'Processing {Bcolors.OKCYAN}{file.name}{Bcolors.ENDC}'
                    print(line, end=' ', flush=True)
                procesor = Processor(seed=self.name, file=file, actions=actions)
                output = []
                for process in procesor.process():
                    if process in STATUS_TO_SHOW or Command.verbose:
                        output.append(process)
                    if process == 'Error':
                        break
                if 'Deleted' in output and 'Ignored' in output:
                    output.append('Disabled')
                if not config.getboolean('COMMAND', 'Quiet', fallback=False):
                    delete_line(line)
                    line = f'Processed {Bcolors.OKCYAN}{file.name}{Bcolors.ENDC}'
                    print(line, end=' ', flush=True)

                if output and not config.getboolean('COMMAND', 'Quiet', fallback=False):
                    line += str(output)+' '
                    print(output, end=' ', flush=True)
                if output or config.getboolean('COMMAND', 'Verbose', fallback=False):
                    line = ''
                    print(line)
        delete_line(line)

    @staticmethod
    def list_installed():
        """Installed seeds"""
        for seed in installed_seeds():
            seed = seed.replace(f'{__app_name__}_seed_', '')
            yield Seed(name=seed, module=__import__(f'{__app_name__}_{PluginType.SEED.value}_{seed}'))

    @staticmethod
    def from_name(name):
        """From name"""
        return Seed(name=name)

    @staticmethod
    def from_module(module):
        """From module"""
        return Seed(module=module)
