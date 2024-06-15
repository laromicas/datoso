"""Unknown seed, detects version and type of dat already in DatRoot."""
import logging
import re
from typing import Any

from datoso.helpers import FileHeaders
from datoso.repositories.dat_file import ClrMameProDatFile, DatFile, DOSCenterDatFile, XMLDatFile


def detect_from_rules(dat: DatFile, rules: list) -> tuple[str, DatFile]:
    """Detect the seed for a dat file."""
    for rule_details in rules:
        found = True
        for rule in rule_details['rules']:
            if not comparator(dat.header.get(rule['key']), rule['value'], rule.get('operator', 'eq')):
                found = False
                break
        if found:
            return rule_details['seed'], rule_details['_class']
    return None, None

def detect_xml(dat_file: str, rules: list) -> tuple[str, XMLDatFile]:
    """Detect the seed for a XML dat file."""
    dat = XMLDatFile(file=dat_file)
    return detect_from_rules(dat, rules)

def detect_clrmame(dat_file: str, rules: list) -> tuple[str, ClrMameProDatFile]:
    """Detect the seed for a ClrMamePro dat file."""
    dat = ClrMameProDatFile(file=dat_file)
    return detect_from_rules(dat, rules)

def detect_doscenter(dat_file: str, rules: list) -> tuple[str, DOSCenterDatFile]:
    """Detect the seed for a ClrMamePro dat file."""
    dat = DOSCenterDatFile(file=dat_file)
    return detect_from_rules(dat, rules)

def detect_seed(dat_file: str, rules: list) -> tuple[str, DatFile]:
    """Detect the seed for a dat file."""
    # Read first 5 chars of file to determine type
    with open(dat_file, encoding='utf-8', errors='ignore') as file:
        file_header = file.read(10).encode('ascii', errors='ignore')[:5].decode()
    try:
        if file_header == FileHeaders.XML.value:
            return detect_xml(dat_file, rules)
        if file_header == FileHeaders.CLRMAMEPRO.value:
            return detect_clrmame(dat_file, rules)
        if file_header == FileHeaders.DOSCENTER.value:
            return detect_doscenter(dat_file, rules)
    except Exception:
        logging.exception('Error detecting seed type')
        raise
    msg = f'Unknown seed type {dat_file} {file_header}'
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
