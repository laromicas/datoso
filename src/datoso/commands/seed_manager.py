""" Seed manager, list, install and remove seeds. """
import logging
import os
import sys

from datoso import __app_name__
from datoso.configuration import ROOT_FOLDER, SEEDS_FOLDER
from datoso.helpers import is_git_path, is_git_repo
from datoso.helpers.executor import Command


def read_seed_repositories():
    """ Read seed repositories from seeds.txt file. """
    with open(os.path.join(ROOT_FOLDER, 'seeds.txt'), 'r', encoding='utf-8') as seeds:
        for seed in seeds:
            seed = seed.strip().split(' ')
            yield (seed[0], ' '.join(seed[1:]) if len(seed) >= 2 else '')


def get_seed_repository(seed_needed):
    """ Get seed repository from seeds.txt file. """
    with open(os.path.join(ROOT_FOLDER, 'seeds.txt'), 'r', encoding='utf-8') as seeds:
        for seed in seeds:
            seed = seed.strip().split(' ')
            if seed[0] == seed_needed:
                return seed[1]
    return None


def seed_available():
    """ Check if seed is available. """
    for seed in read_seed_repositories():
        yield seed[0], seed[1]


def seed_developer_install(args, repository):
    """ Install seed from git repository. """
    if not is_git_path(repository) and repository.startswith('/') and not is_git_repo(repository):
        logging.error('%s is not a git repository', repository)
        sys.exit(1)
    branch = args.branch if getattr(args, 'branch', None) else 'master'
    url = repository
    path = os.path.join(SEEDS_FOLDER, args.seed)
    os.system(f'rm -rf {path}')
    Command.execute(['git', 'clone', f'{url}', args.seed], cwd=SEEDS_FOLDER)
    Command.execute(['git', 'checkout', f'{branch}'], cwd=path)


def seed_user_install(args, repository):
    """ Install seed from zip file. """
    repository = repository if repository.startswith('http') else 'https://' + repository
    repository = repository[:-4] if repository.endswith('.git') else repository
    branch = args.branch if getattr(args, 'branch', None) else 'master'
    url = os.path.join(repository, 'archive', f'{branch}.zip')
    path = os.path.join(SEEDS_FOLDER, args.seed)
    os.system(f'rm -rf {path}')
    Command.execute(['wget', f'{url}', '-O', f'{__app_name__}_{args.seed}-{branch}.zip', '-c'], cwd=SEEDS_FOLDER)
    Command.execute(['unzip', f'{__app_name__}_{args.seed}-{branch}.zip'], cwd=SEEDS_FOLDER)
    os.unlink(os.path.join(SEEDS_FOLDER, f'{__app_name__}_{args.seed}-{branch}.zip'))
    os.rename(os.path.join(SEEDS_FOLDER, f'{__app_name__}_{args.seed}-{branch}'), os.path.join(SEEDS_FOLDER, args.seed))


def seed_install(args, repository):
    """ Install seed. """
    if args.developer:
        seed_developer_install(args, repository)
    else:
        seed_user_install(args, repository)
    if args.install_dependencies:
        seed_install_dependencies(args.seed)


def seed_remove(seed):
    """ Remove seed. """
    path = os.path.join(SEEDS_FOLDER, seed)
    os.system(f'rm -rf {path}')


def seed_install_dependencies(seed):
    """ Install seed dependencies. """
    # pylint: disable=protected-access
    def install(package):
        output = io.StringIO()
        sys.stdout = sys.stderr = output
        if hasattr(pip, 'main'):
            pip.main(['install', package])
        else:
            pip._internal.main(['install', package])
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        logging.info(output.getvalue())

    if os.path.exists(os.path.join(SEEDS_FOLDER, seed, 'requirements.txt')):
        import pip
        import io
        with open(os.path.join(SEEDS_FOLDER, seed, 'requirements.txt'), 'r', encoding='utf-8') as requirements:
            for requirement in requirements:
                install(requirement)
