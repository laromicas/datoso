"""Unknown seed, detects version and type of dat already in DatRoot."""
import logging
import re
from typing import Any

from datoso.repositories.dat_file import DatFile, DatFileTypes


def detect_from_rules(dat: DatFile, rules: list) -> tuple[str, DatFile]:
    """Detect the seed for a dat file."""
    for rule_details in rules:
        if rule_details.get('type', False) in [e.value for e in DatFileTypes] \
            and not isinstance(dat, DatFileTypes(rule_details['type']).cls):
            continue
        found = True
        for rule in rule_details['rules']:
            if not comparator(dat.header.get(rule['key']), rule['value'], rule.get('operator', 'eq')):
                found = False
                break
        if found:
            return rule_details['seed'], rule_details['_class']
    return None, None

def detect_seed(dat_file: str, rules: list) -> tuple[str, DatFile]:
    """Detect the seed for a dat file."""
    try:
        dat = DatFile.from_file(file=dat_file)
        seed, _class = detect_from_rules(dat, rules)
        if _class:
            return seed, _class
    except Exception:
        logging.exception('Error detecting seed type')
        raise
    msg = f'Unknown seed type {dat_file}'
    raise LookupError(msg)

def comparator(key: Any, value: Any, operator: str = 'eq') -> bool:  # noqa: C901, PLR0911, PLR0912, ANN401
    """Return a boolean based on the comparison of the key and value."""
    match operator:
        case 'eq' | 'equals' | '==':
            return key == value
        case 'ne' | 'not_equals' | '!=':
            return key != value
        case 'gt' | 'greater_than' | '>':
            return key > value
        case 'lt' | 'less_than' | '<':
            return key < value
        case 'ge' | 'greater_than_or_equals' | '>=':
            return key >= value
        case 'le' | 'less_than_or_equals' | '<=':
            return key <= value
        case 'in' | 'is_contained_in' | 'has':
            return key in value if value else False
        case 'ni' | 'not_in' | 'is_not_contained_in' | 'hasnt' | 'has_not':
            return key not in value if value else True
        case 're' | 'regex' | 'matches' | 'match' | 'matches_regex' | 'match_regex':
            return re.search(value, key)
        case 'nr' | 'not_regex' | 'not_matches' | 'not_match' | 'not_matches_regex' | 'not_match_regex':
            return not re.search(value, key)
        case 'sw' | 'starts_with':
            return key.startswith(value) if key else False
        case 'ew' | 'ends_with':
            return key.endswith(value) if key else False
        case 'ns' | 'not_starts_with':
            return not key.startswith(value) if key else True
        case 'ne' | 'not_ends_with':
            return not key.endswith(value) if key else True
        case 'co' | 'contains':
            return value in key if key else False
        case 'nc' | 'not_contains':
            return value not in key if key else True
        case 'ex' | 'exists':
            return bool(key)
        case 'nx' | 'not_exists' | 'not_exist' | 'not_exits' | 'not_exits':
            return not bool(key)
        case 'bt' | 'between' | 'in_range' | 'in_between':
            return value[0] <= key <= value[1] if value else False
        case 'nb' | 'not_between' | 'not_in_range' | 'not_in_between':
            return not (value[0] <= key <= value[1]) if value else True
        case 'is':
            return key is value
        case 'isnt' | 'is_not':
            return key is not value
    return False
