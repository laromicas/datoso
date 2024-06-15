"""Seed the database with Systems."""
import json
from pathlib import Path

import requests

from datoso import ROOT_FOLDER
from datoso.configuration import config
from datoso.database.models import System

fields = [
    'company',
    'system',
    'override',
    'extra_configs',
    'system_type',
]


def get_systems() -> list:
    """Get systems from the Google Sheets."""
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
                except Exception:  # noqa: BLE001
                    row[field] = system[j]
        systems.append(row)
    return systems


def import_dats() -> None:
    """Seed the database with Systems."""
    systems = get_systems()
    with open(Path(ROOT_FOLDER,'systems.json'), 'w', encoding='utf-8') as file:
        json.dump(systems, file, indent=4)
    System.truncate()
    for system in systems:
        row = System.from_dict(system)
        row.save()
        row.flush()


def init() -> None:
    """Seed the database with Systems."""
    with open(Path(ROOT_FOLDER,'systems.json'), encoding='utf-8') as file:
        systems = json.load(file)
    for system in systems:
        row = System.from_dict(system)
        row.save()
        row.flush()


def detect_first_run() -> None:
    """Detect if this is the first run."""
    if not System.all():
        init()
