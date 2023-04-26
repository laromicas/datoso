""" Fetch and Process Commands for Seeds """
import os
import re
from datoso.helpers.plugins import get_seed
from datoso.helpers import Bcolors, FileUtils
from datoso.configuration import config
from datoso.helpers.executor import Command
from datoso.actions.processor import Processor

class Seed:
    """ Seed class """
    name = None
    path = None
    actions = {}
    # working_path = os.path.abspath(os.path.join(os.getcwd(), config.get('PATHS', 'WorkingPath')))
    status_to_show = ['Updated', 'Created', 'Error', 'Disabled', 'Deduped']

    def __init__(self, **kwargs) -> None:
        self.__dict__.update(kwargs)
        actions = get_seed(self.name, 'actions')
        if actions:
            self.actions = actions.get_actions()


    def fetch(self):
        """ Fetch seed """
        fetch = get_seed(self.name, 'fetch')
        fetch.fetch()


    def format_actions(self, actions, data: dict = {}):
        """ Format actions. """
        for action in actions:
            for action_name, action_value in action.items():
                if isinstance(action_value, str):
                    action[action_name] = action_value.format(**data)
        return actions


    def process_dats(self, fltr=None):
        """ Process dats."""
        def delete_line(line):
            # pylint: disable=expression-not-assigned
            [print('\b \b', end='') for x in range(0, len(line))]
            print(' ' * (len(line)), end='')
            print('\r', end='')
        dat_origin = os.path.join(FileUtils.parse_folder(config['PATHS'].get('DownloadPath', 'tmp')), self.name, 'dats')
        line = ''
        for path, actions in self.actions.items():
            new_path = path.format(dat_origin=dat_origin)
            actions = self.format_actions(actions, data={'dat_destination': config['PATHS'].get('DatPath', 'DatRoot')})
            for file in os.listdir(new_path) if os.path.isdir(new_path) else []:
                if config['PROCESS'].get('DatIgnoreRegEx'):
                    ignore_regex = re.compile(config['PROCESS']['DatIgnoreRegEx'])
                    if ignore_regex.match(file):
                        continue

                if (not file.endswith(('.dat', '.xml')) \
                    and not os.path.isdir(os.path.join(new_path,file))) \
                    or (fltr and fltr not in file):
                    continue

                if not config.getboolean('COMMAND', 'Quiet', fallback=False):
                    delete_line(line)
                    line = f'Processing {Bcolors.OKCYAN}{file}{Bcolors.ENDC}'
                    print(line, end=' ', flush=True)
                procesor = Processor(seed=self.name, file=f'{new_path}/{file}', actions=actions)
                output = [x for x in procesor.process() if (x in self.status_to_show or Command.verbose)]
                if 'Deleted' in output and 'Ignored' in output:
                    output.append('Disabled')
                if not config.getboolean('COMMAND', 'Quiet', fallback=False):
                    # [print('\b \b', end='') for x in range(0, len(line))]
                    delete_line(line)
                    line = f'Processed {Bcolors.OKCYAN}{file}{Bcolors.ENDC}'
                    print(line, end=' ', flush=True)

                if output and not config.getboolean('COMMAND', 'Quiet', fallback=False):
                    line += str(output)+' '
                    print(output, end=' ', flush=True)
                if output or config.getboolean('COMMAND', 'Verbose', fallback=False):
                    line = ''
                    print(line)
        delete_line(line)
        print(f'{Bcolors.OKBLUE}Finished processing {Bcolors.OKGREEN}{self.name}{Bcolors.ENDC}')
