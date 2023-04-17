"""
    Seed the database with repositories.
"""
from datoso.database.models import Seed

repositories = [
    {
        "name": "No-Intro",
        "short_name": "nointro",
        "description": "No-Intro is a collection of DATs aimed for video game preservation especialized in cartridge-based and digital systems.",
        "url": "https://wiki.no-intro.org/index.php",
        "icon": "https://www.no-intro.org/favicon.ico",
        "update_script": "lib/nointro/update.py",
        "type": "system"
    },
    {
        "name": "Redump",
        "short_name": "redump",
        "description": "Redump.org is a disc preservation database and internet community dedicated to collecting precise and accurate information about every video game ever released on optical media of any system.",
        "url": "http://redump.org/",
        "icon": "http://redump.org/favicon.ico",
        "update_script": "lib/redump/update",
        "type": "system"
    },
    {
        "name": "Translated-English",
        "short_name": "t_en",
        "description": "Translated-English is a collection of DATs aimed for video game translations.",
        "url": "http://archive.org/En-ROMs/",
        "icon": "http://archive.org/favicon.ico",
        "update_script": "lib/t_en/update",
        "type": "system"
    },
]


def _import_():
    """ Seed the database with repositories. """
    for repository in repositories:
        repo = Seed(**repository)
        repo.save()
