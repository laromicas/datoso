"""
    Seed the database with Systems.
"""
import os
import json
import requests
from datoso.configuration import config
from datoso import ROOT_FOLDER
from datoso.database.models import System


fields = [
    'company',
    'system',
    'override',
    'extra_configs',
    'system_type',
]


def get_systems():
    """ Get systems from the Google Sheets. """
    if not config['UPDATE_URLS']['GoogleSheetUrl']:
        return []
    result = requests.get(config['UPDATE_URLS']['GoogleSheetUrl'], timeout=300)
    systems_result = result.json()['values']
    systems = []
    for i in range(1, len(systems_result)):
        system = systems_result[i]
        row = {}
        for j, field in enumerate(fields):
            if len(system) > j and system[j] != '':
                row[field] = system[j]
            elif field == 'company':
                row[field] = None
            if field in ('override', 'extra_configs') and field in row:
                try:
                    row[field] = json.loads(system[j])
                except Exception:  # pylint: disable=broad-except
                    row[field] = system[j]
        systems.append(row)
    return systems


def import_dats():
    """ Seed the database with Systems. """
    # pylint: disable=protected-access
    systems = get_systems()
    with open(os.path.join(ROOT_FOLDER,'systems.json'), 'w', encoding='utf-8') as file:
        json.dump(systems, file, indent=4)
    for system in systems:
        row = System(**system)
        row.save()
        row._DB.table.storage.flush()
