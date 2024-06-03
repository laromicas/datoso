"""Seed the database with mia."""
import json
from pathlib import Path

import requests

from datoso import ROOT_FOLDER
from datoso.configuration import config

fields = [
    'system',
    'game',
    'size',
    'crc32',
    'md5',
    'sha1',
]


def get_mia() -> dict:
    """Get MIA from the Google Sheets."""
    if not config['UPDATE_URLS']['GoogleSheetMIAUrl']:
        return []
    result = requests.get(config['UPDATE_URLS']['GoogleSheetMIAUrl'], timeout=300)
    mias_result = result.json()['values']
    mias = {}
    for i in range(1, len(mias_result)):
        mia = mias_result[i]
        row = {}
        for j, field in enumerate(fields):
            if len(mia) > j and mia[j] != '':
                row[field] = mia[j]
        key = row.get('sha1') or row.get('md5') or row.get('crc32') or f"{row.get('system')} - {row.get('game')}"
        mias[key] = row
    return mias


def import_mias() -> None:
    """Seed the database with mia."""
    # pylint: disable=protected-access
    mias = get_mia()
    with open(Path(ROOT_FOLDER,'mia.json'), 'w', encoding='utf-8') as file:
        json.dump(mias, file, indent=4)


def get_mias() -> dict:
    """Seed the database with mia."""
    # pylint: disable=protected-access
    with open(Path(ROOT_FOLDER,'mia.json'), encoding='utf-8') as file:
        return json.load(file)
