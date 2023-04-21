""" Rules class. """
from pydoc import locate
from datoso.helpers.plugins import installed_seeds

class Rules:
    """ Rules class. """
    _rules = []

    def __init__(self):
        for seed, _ in installed_seeds().items():
            rules = locate(f'{seed}.rules')
            self._rules.extend(rules.get_rules())
        self._rules.sort(key=lambda x: x['priority'], reverse=True)

    @property
    def rules(self):
        """ Return the rules. """
        return self._rules
