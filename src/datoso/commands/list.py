"""List all installed seeds."""
import os
from datoso.configuration import SEEDS_FOLDER

def installed_seeds():
    """ List all installed seeds. """
    for seed in os.listdir(SEEDS_FOLDER):
        if not os.path.isdir(os.path.join(SEEDS_FOLDER, seed)) or seed.startswith('__'):
            continue
        name = seed
        description = seed_description(seed)
        yield (name, description)

def seed_description(seed):
    """ Get seed description. """
    description = ''
    if os.path.isfile(os.path.join(SEEDS_FOLDER, seed, 'description.txt')):
        with open(os.path.join(SEEDS_FOLDER, seed, 'description.txt'), 'r', encoding='utf-8') as desc:
            description = desc.readline().strip()
    return description
