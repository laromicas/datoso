""" Rules class. """
import json
import os
from datoso.configuration import SEEDS_FOLDER
from datoso.commands.seed_manager import seed_available


class Rules:
    """ Rules class. """
    _rules = []

    def __init__(self):
        for seed in seed_available():
            rules_file = os.path.join(SEEDS_FOLDER, seed[0], 'rules.json')
            # yield rules_file
            if os.path.exists(rules_file):
                with open(rules_file, 'r', encoding='utf-8') as file:
                    Rules._rules.extend(json.load(file))
        self._rules.sort(key=lambda x: x['priority'], reverse=True)

    @property
    def rules(self):
        """ Return the rules. """
        return self._rules
