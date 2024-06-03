"""Rules class."""
from pydoc import locate

from datoso.helpers.plugins import installed_seeds


class Rules:
    """Rules class."""

    _rules: list | None

    def __init__(self) -> None:
        """Initialize Rules."""
        self._rules = []
        for seed in installed_seeds():
            rules = locate(f'{seed}.rules')
            self._rules.extend(rules.get_rules())
        self._rules.sort(key=lambda x: x['priority'], reverse=True)

    @property
    def rules(self) -> list:
        """Return the rules."""
        return self._rules
