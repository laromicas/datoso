"""Dat classes to parse different types of dat files."""
import logging
import os
import shlex
from collections.abc import Callable, Generator
from enum import Enum
from hashlib import md5
from pathlib import Path
from typing import Any

import xmltodict

from datoso.configuration import config
from datoso.database.models.dat import System
from datoso.repositories.hashes_index import HashesIndex


class FileHeaders(Enum):
    """File headers Enum."""

    XML = '<?xml'
    CLRMAMEPRO = 'clrma'
    DOSCENTER = 'DOSCe'

class DatFile:
    """Base class for dat files. Abstract class."""

    name: str = None
    file: str = None
    full_name: str = None
    seed: str = None

    # calculated values
    modifier: str = None
    system_type: str = None
    company: str = None
    system: str = None
    prefix: str = None
    suffix: str = None
    suffixes: list = None
    date = None
    path: str = None
    version: str = None

    header: dict = None
    games: list = None

    def __init__(self, **kwargs: Any) -> None:  # noqa: ANN401
        """Initialize the dat file."""
        self.__dict__.update(kwargs)
        if not self.name and not self.file:
            msg = 'No file specified'
            raise ValueError(msg)
        if not self.name:
            self.load()

    # @abstractmethod
    def load(self) -> None:
        """Abstract ** Load the dat file."""

    # @abstractmethod
    def initial_parse(self) -> None:
        """Parse the dat file."""

    # @abstractmethod
    def get_date(self) -> str:
        """Get the date from the dat file."""

    # @abstractmethod
    def to_csv(self) -> Generator[str, None, None]:
        """Convert the dat file to CSV."""
        raise NotImplementedError('This method should be implemented in the subclass.')

    def close(self) -> None:
        """Close the dat file if needed."""

    def get_version(self) -> str:
        """Get the version from the dat file."""
        return getattr(self, 'version', None)

    def get_modifier(self) -> str:
        """Get the modifier ej. 'Source Code', 'etc'."""
        return getattr(self, 'modifier', None)

    def get_company(self) -> str:
        """Get the company name."""
        return getattr(self, 'company', None)

    def get_system(self) -> str:
        """Get the system name."""
        return getattr(self, 'system', None)

    def get_system_type(self) -> str:
        """Get the system type."""
        return getattr(self, 'system_type', None)

    def get_prefix(self) -> str:
        """Get the prefix for the path."""
        return getattr(self, 'prefix', None)

    def get_suffix(self) -> str:
        """Get the suffix for the path."""
        return getattr(self, 'suffix', None)

    def get_path(self) -> str:
        """Get the path for the dat file."""
        suffixes = self.get_suffix()
        if not isinstance(suffixes, list):
            suffixes = [suffixes]
        self.path = os.path.join(*[x for x in [self.get_prefix(), self.get_company(), self.get_system(), # noqa: PTH118
                                               *suffixes] if x])
        return self.path

    def get_rom_shas(self) -> None:
        """Get the shas for the roms and creates an index."""

    def dedupe(self) -> None:
        """Dedupe the dat file."""

    def merge_with(self, parent: 'DatFile') -> None:
        """Merge the dat file with the parent."""

    def dict(self) -> dict:
        """Return a dictionary with the dat file information."""
        self.initial_parse()
        return {
            'name': self.name,
            'file': self.file,
            'full_name': self.full_name,
            'seed': self.seed,
            'version': self.get_version(),
            'date': self.get_date(),
            'modifier': self.get_modifier(),
            'company': self.get_company(),
            'system': self.get_system(),
            'system_type': self.get_system_type(),
            'path': self.get_path(),
        }

    @staticmethod
    def from_file(file: str | Path | None) -> 'DatFile':
        """Create a class dynamically."""
        try:
            dat_file = DatFile.class_from_file(dat_file=file)
            return dat_file(file=file) if dat_file else None
        except Exception:
            logging.exception('Error detecting seed type')
            raise

    @staticmethod
    def class_from_file(dat_file: str | Path | None) -> 'DatFile':
        """Create a class dynamically."""
        with open(dat_file, encoding='utf-8', errors='ignore') as file:
            file_header = file.read(10).encode('ascii', errors='ignore')[:5].decode()
        if file_header == FileHeaders.XML.value:
            # Check if it's a DB Export format (no header element)
            if DatFile._is_xml_db_export(dat_file):
                return XMLDBExportDatFile
            return XMLDatFile
        if file_header == FileHeaders.CLRMAMEPRO.value:
            return ClrMameProDatFile
        if file_header == FileHeaders.DOSCENTER.value:
            return DOSCenterDatFile
        return None

    @staticmethod
    def _is_xml_db_export(dat_file: str | Path) -> bool:
        """Check if XML file is DB Export format (has no header element)."""
        with open(dat_file, encoding='utf-8', errors='ignore') as file:
            # Read first few lines to check for header element
            for _ in range(50):  # Check first 50 lines
                line = file.readline()
                if not line:
                    break
                if '<header>' in line or '<header ' in line:
                    return False  # Has header, not DB Export
                if '<game' in line:
                    return True  # Found game before header, it's DB Export
        return False  # Default to regular XML

class XMLDatFile(DatFile):
    """XML dat file."""

    shas = None
    main_key = 'datafile'
    game_key = 'game'
    header: dict = None
    merged_roms: list = None
    merge_options = 'dedupe' # dedupe, merge

    def load(self, *, load_games: bool = False) -> None:
        """Load the data from a XML file."""
        with open(self.file, encoding='utf-8-sig') as fild:
            # Load the entire file or just header based on load_games flag
            xml_content = fild.read() if load_games else self._read_header_only(fild)

            self.data = xmltodict.parse(xml_content)
            self.detect_main_key()
            self.header = self.data[self.main_key].get('header', {})
            if self.header:
                self.name = self.header.get('name')
                self.full_name = self.header.get('description')
                self.date = self.header.get('date')
                self.homepage = self.header['homepage'] if 'homepage' in self.header and self.header['homepage'] \
                    and 'insert' not in self.header['homepage'] else None
                self.url = self.header['url'] if 'url' in self.header and self.header['url'] \
                    and 'insert' not in self.header['url'] else None
                self.author = self.header['author'] if 'author' in self.header and self.header['author'] \
                    and 'insert' not in self.header['author'] else None
                self.email = self.header['email'] if 'email' in self.header and self.header['email'] \
                    and 'insert' not in self.header['email'] else None
            else:
                self.name = self.data[self.main_key].get('@name')
                self.full_name = self.data[self.main_key].get('@description')
            if load_games:
                self.detect_game_key()

    def _read_header_only(self, file_obj: Any) -> str:  # noqa: ANN401
        """Read only the header portion of the XML file for memory efficiency."""
        lines = []
        header_closed = False
        main_tag = None

        for line in file_obj:
            lines.append(line)

            # Capture the main tag name (e.g., "datafile", "logiqx", etc.)
            stripped = line.strip()
            if main_tag is None and '<' in line and not stripped.startswith('<?') and not stripped.startswith('<!'):
                # Extract tag name from opening tag
                tag_start = line.find('<') + 1
                tag_end = line.find('>', tag_start)
                if tag_end > tag_start:
                    tag_name = line[tag_start:tag_end].split()[0].strip()
                    if tag_name and not tag_name.startswith('/'):
                        main_tag = tag_name

            # Check if we've reached the end of the header
            if '</header>' in line:
                header_closed = True
                break

        # Add closing tag for the main element
        if header_closed and main_tag:
            lines.append(f'</{main_tag}>\n')

        return ''.join(lines)

    def save(self) -> None:
        """Save the data to a XML file."""
        with open(self.file, 'w', encoding='utf-8') as fild:
            fild.write(xmltodict.unparse(self.data, pretty=True))

    def detect_main_key(self) -> str:
        """Detect the main key for the dat file."""
        self.main_key = next(iter(self.data))

    def detect_game_key(self) -> str:
        """Get the game key."""
        for key in self.data[self.main_key]:
            if key != 'header' and not key.startswith('@'):
                self.game_key = key
                break

    def parse_rom(self, rom: dict) -> dict:
        """Standarize the rom."""
        parsed_rom = {}
        for key in rom:
            if key.startswith('@'):
                parsed_rom[key[1:]] = rom[key]
            else:
                parsed_rom[key] = rom[key]
        return parsed_rom

    def add_rom(self, rom: dict) -> None:
        """Add a rom to the dat file."""
        self.shas.add_rom(self.parse_rom(rom))

    def mark_mia(self, rom: dict, mias: dict) -> None:
        """Mark the mias in the dat file."""
        key = rom.get('@sha1') or rom.get('@md5') or rom.get('@crc32') or f"{self.get_system()} - {rom.get('name')}"
        return key in mias

    def mark_mias(self, mias: dict) -> None:
        """Mark the mias in the dat file."""
        mark_all_roms_in_set = config.getboolean('PROCESS', 'MarkAllRomsInSet', fallback=False)
        if not isinstance(self.data[self.main_key][self.game_key], list):
            self.data[self.main_key][self.game_key] = [self.data[self.main_key][self.game_key]]
        for game in self.data[self.main_key][self.game_key]:
            if 'rom' not in game:
                continue
            if not isinstance(game['rom'], list):
                miad = self.mark_mia(game['rom'], mias)
                if miad:
                    game['rom']['@mia'] = 'yes'
            else:
                miad = False
                for rom in game['rom']:
                    miad = self.mark_mia(rom, mias)
                    if miad:
                        rom['@mia'] = 'yes'
                if miad and mark_all_roms_in_set:
                    for rom in game['rom']:
                        rom['@mia'] = 'yes'
                    break

    def _iter_games(self, container: dict) -> Generator[dict, None, None]:
        """Recursively yield game dicts from a container that may hold 'game' and/or 'dir' entries.

        A container is a dict that may contain a 'game' key (one game or a list of games) and/or
        a 'dir' key (one sub-container or a list of sub-containers) which may recursively contain
        more 'game'/'dir' entries. This allows dat files with nested <dir> elements to be walked
        the same way as flat ones.
        """
        if 'game' in container:
            games = container['game']
            if not isinstance(games, list):
                games = [games]
            yield from games
        if 'dir' in container:
            dirs = container['dir']
            if not isinstance(dirs, list):
                dirs = [dirs]
            for sub_dir in dirs:
                yield from self._iter_games(sub_dir)

    def _dedupe_game(
        self,
        game: dict,
        has_rom: Callable[[dict], bool],
        on_keep: Callable[[dict], None] | None,
    ) -> dict | None:
        """Filter duplicate roms out of a single game, returning None if no roms remain."""
        roms = game['rom'] if isinstance(game['rom'], list) else [game['rom']]
        new_roms = []
        for rom in roms:
            if has_rom(self.parse_rom(rom)):
                self.merged_roms.append(self.parse_rom(rom))
            else:
                if on_keep:
                    on_keep(rom)
                new_roms.append(rom)
        if not new_roms:
            return None
        new_game = {key: value for key, value in game.items() if key != 'rom'}
        new_game['rom'] = new_roms
        return new_game

    def _dedupe_games(
        self,
        container: dict,
        has_rom: Callable[[dict], bool],
        on_keep: Callable[[dict], None] | None = None,
    ) -> None:
        """Recursively filter out duplicate roms from a container, dropping empty games/dirs.

        `container` is a dict that may hold 'game' and/or 'dir' entries (see `_iter_games`).
        Games are kept in place wherever they appear in the tree; a game is dropped entirely if
        all of its roms are duplicates, and a 'dir' is dropped if it ends up with no games and no
        sub-dirs left.

        has_rom: given a parsed rom, return True if it's a duplicate that should be removed.
        on_keep: optional callback invoked with the raw rom dict for every rom that is kept.
        """
        if 'game' in container:
            games = container['game']
            if not isinstance(games, list):
                games = [games]
            new_games = [
                new_game
                for game in games if 'rom' in game
                for new_game in (self._dedupe_game(game, has_rom, on_keep),)
                if new_game is not None
            ]
            if new_games:
                container['game'] = new_games
            else:
                container.pop('game', None)

        if 'dir' in container:
            dirs = container['dir']
            if not isinstance(dirs, list):
                dirs = [dirs]
            new_dirs = []
            for sub_dir in dirs:
                self._dedupe_games(sub_dir, has_rom, on_keep)
                if 'game' in sub_dir or 'dir' in sub_dir:
                    new_dirs.append(sub_dir)
            if new_dirs:
                container['dir'] = new_dirs
            else:
                container.pop('dir', None)

    def get_rom_shas(self) -> None:
        """Get the shas for the roms and creates an index."""
        self.shas = HashesIndex()

        for game in self._iter_games(self.data[self.main_key]):
            if 'rom' not in game:
                continue
            if not isinstance(game['rom'], list):
                self.add_rom(game['rom'])
            else:
                for rom in game['rom']:
                    self.add_rom(rom)

    def merge_with(self, parent: DatFile) -> None:
        """Merge the dat file with the parent."""
        if not self.merged_roms:
            self.merged_roms = []
        parent.get_rom_shas()
        self._dedupe_games(self.data[self.main_key], has_rom=parent.shas.has_rom)

    def dedupe(self) -> None:
        """Dedupe the dat file."""
        self.shas = HashesIndex()
        if not self.merged_roms:
            self.merged_roms = []
        self._dedupe_games(self.data[self.main_key], has_rom=self.shas.has_rom, on_keep=self.add_rom)

    def get_name(self) -> str:
        """Get the name of the dat file."""
        if not self.name:
            self.load()
        return self.name

    def overrides(self) -> System:
        """Override data for some systems."""
        find_system = System(company=self.get_company(), system=self.get_system())
        find_system.load()
        if getattr(find_system, 'system_type', None):
            self.system_type = find_system.system_type
            if getattr(find_system, 'override', None):
                self.__dict__.update({k: v for k, v in find_system.override.items() if v})
        return find_system

    def extra_configs(self, find_system: System) -> None:
        """Extra configs for some systems."""
        extra_configs = getattr(find_system, 'extra_configs', None)
        if extra_configs:
            if extra_configs.get('empty_suffix', None) and not self.suffix:
                self.suffix = extra_configs['empty_suffix'].get(self.seed, None)
            if extra_configs.get('additional_suffix', None):
                self.suffix = str(Path(self.suffix) / extra_configs['additional_suffix'].get(self.seed, None))
            if extra_configs.get('if_suffix', None):
                for key, value in extra_configs['if_suffix'].items():
                    if value and self.suffixes and key in self.suffixes:
                        self.__dict__.update(value)

    def get_date(self) -> str:
        """Get the date from the dat file."""
        return self.date

    def to_csv(self) -> str:
        """Convert the dat file to a CSV file."""
        if not self.data[self.main_key][self.game_key]:
            self.load()
        if not self.data[self.main_key][self.game_key]:
            raise ValueError('No games found in the dat file')
        for game in self.data[self.main_key][self.game_key]:
            if 'rom' in game:
                roms = game['rom'] if isinstance(game['rom'], list) else [game['rom']]
                for rom in roms:
                    extensions_to_remove = ['.iso', '.cue', '.bin', '.chd', '.rvz']
                    clean_rom_name = rom.get('@name', '')
                    for ext in extensions_to_remove:
                        clean_rom_name = clean_rom_name.removesuffix(ext)

                    sha = rom.get('@sha1', '')
                    md5 = rom.get('@md5', '')
                    crc = rom.get('@crc', '')
                    yield f'"{clean_rom_name}"\t"{sha}"\t"{md5}"\t"{crc}"\n'


class XMLDBExportDatFile(XMLDatFile):
    """XML DB Export dat file - XML format without header element."""

    def load(self, *, load_games: bool = False) -> None:
        """Load the data from a XML DB Export file (no header element)."""
        with open(self.file, encoding='utf-8') as fild:
            # Load the entire file or just first game based on load_games flag
            xml_content = fild.read() if load_games else self._read_first_game_only(fild)

            self.data = xmltodict.parse(xml_content)
            self.detect_main_key()
            # DB Export format has no header element
            self.header = {}

            # Set placeholder values for missing header fields
            self.name = self.data[self.main_key].get('@name', 'DB Export')
            self.full_name = self.data[self.main_key].get('@description', 'Database Export')
            self.date = None  # Placeholder - to be determined later from filename or metadata
            self.homepage = None
            self.url = None
            self.author = None
            self.email = None

            if load_games:
                self.detect_game_key()

    def _read_first_game_only(self, file_obj: Any) -> str:  # noqa: ANN401
        """Read only the first game for structure detection in DB Export format."""
        lines = []
        main_tag = None
        game_count = 0
        max_games_to_read = 1

        for line in file_obj:
            lines.append(line)

            # Capture the main tag name (e.g., "datafile")
            stripped = line.strip()
            if main_tag is None and '<' in line and not stripped.startswith('<?') and not stripped.startswith('<!'):
                # Extract tag name from opening tag
                tag_start = line.find('<') + 1
                tag_end = line.find('>', tag_start)
                if tag_end > tag_start:
                    tag_name = line[tag_start:tag_end].split()[0].strip()
                    if tag_name and not tag_name.startswith('/'):
                        main_tag = tag_name

            # Count game tags to stop after first game
            if main_tag and '<game' in line and not line.strip().startswith('<!'):
                game_count += 1
            if game_count >= max_games_to_read and '</game>' in line:
                # We've read enough to parse the structure
                break

        # Add closing tag for the main element
        if game_count > 0 and main_tag:
            lines.append(f'</{main_tag}>\n')

        return ''.join(lines)


class ClrMameProDatFile(DatFile):
    """ClrMamePro dat file."""

    header: dict = None
    games: list = None
    main_key = 'clrmamepro'
    game_key = 'game'

    def get_next_block(self, data: str) -> tuple[str, str]:
        """Get the next block of data."""
        parenthesis = 0
        start = 0
        end = 0
        within_string = False
        for i, char in enumerate(data):
            if char == '"':
                within_string = not within_string
            if not within_string:
                if char == '(':
                    if parenthesis == 0:
                        start = i + 1
                    parenthesis += 1
                if char == ')':
                    parenthesis -= 1
            if parenthesis == 0 and start >= 1:
                end = i
                break
        return data[start:end], data[end + 1:] if end < len(data) else None

    def read_block(self, data: str) -> dict:
        """Read a block of data from a ClrMame dat and parses it."""
        dictionary = {}
        for unstripped_line in iter(data.splitlines()):
            line = unstripped_line.strip()
            if line:
                if line.startswith('rom'):
                    line = line[6:-2]
                    rom = {'@name': None, '@crc': None, '@md5': None, '@sha1': None}
                    try:
                        data = shlex.split(line)
                    except ValueError:
                        data = line.split(' ')
                    for i in range(0, len(data), 2):
                        rom[f'@{data[i]}'] = data[i+1]
                    dictionary['rom'] = dictionary.get('rom', [])
                    dictionary['rom'].append(rom)
                else:
                    try:
                        key, value = shlex.split(line)
                    except ValueError as exc:
                        msg = f'Error parsing line: {line} from: {self.file}'
                        raise ValueError(msg) from exc
                    dictionary[key] = value

        return dictionary

    def load(self, *, load_games: bool = False) -> None:
        """Load the data from a ClrMamePro file."""
        self.games = []
        self.main_key = 'datafile'
        with open(self.file, encoding='utf-8', errors='ignore') as file:
            data = file.read()

            block, next_block = self.get_next_block(data)
            self.header = self.read_block(block)
            self.header = {k.lower(): v for k, v in self.header.items()}

            if load_games:
                while next_block:
                    block, next_block = self.get_next_block(next_block)
                    self.games.append(self.read_block(block))

        self.data = {
            self.main_key: {
                'header':  self.header,
                'game': self.games,
            },
        }
        self.name = self.header['name']
        self.full_name = self.header['description']

    def get_rom_shas(self) -> None:
        """Get the shas for the roms and creates an index."""
        self.shas = HashesIndex()

        for game in self.games:
            if 'rom' not in game:
                continue
            if not isinstance(game['rom'], list):
                self.add_rom(game['rom'])
            else:
                for rom in game['rom']:
                    self.add_rom(rom)

    def merge_with(self, parent: DatFile) -> None:
        """Merge the dat file with the parent."""
        print('Not yet implemented')
        return
        if not self.merged_roms:
            self.merged_roms = []
        parent.get_rom_shas()
        new_games = []
        for game in self.data[self.main_key][self.game_key]:
            if 'rom' not in game:
                continue
            new_game = {}
            for key in game:
                if key != 'rom':
                    new_game[key] = game[key]
            if not isinstance(game['rom'], list):
                if parent.shas.has_rom(self.parse_rom(game['rom'])):
                    self.merged_roms.append(self.parse_rom(game['rom']))
                else:
                    new_game['rom'] = game['rom']
            else:
                new_roms = []
                for rom in game['rom']:
                    if not parent.shas.has_rom(self.parse_rom(rom)):
                        new_roms.append(rom)
                    else:
                        self.merged_roms.append(self.parse_rom(rom))
                new_game['rom'] = new_roms
            new_games.append(new_game)
        self.data[self.main_key][self.game_key] = new_games

    def add_rom(self, rom: dict) -> None:
        """Add a rom to the dat file."""
        self.shas.add_rom(self.parse_rom(rom))

    def parse_rom(self, rom: dict) -> dict:
        """Standarize the rom."""
        parsed_rom = {}
        for key in rom:
            if key.startswith('@'):
                parsed_rom[key[1:]] = rom[key]
            else:
                parsed_rom[key] = rom[key]
        return parsed_rom

class DOSCenterDatFile(ClrMameProDatFile):
    """DOSCenter dat file."""

    def read_block(self, data: str) -> dict:
        """Read a block of data from a DOSCenter dat and parses it."""
        dictionary = {}
        for unstripped_line in iter(data.splitlines()):
            line = unstripped_line.strip()
            if line:
                if line.startswith('rom'):
                    line = line[6:-2]
                    rom = {'@name': None, '@crc': None, '@md5': None, '@sha1': None}
                    try:
                        data = shlex.split(line)
                    except ValueError:
                        data = line.split(' ')
                    for i in range(0, len(data), 2):
                        rom[f'@{data[i]}'] = data[i+1]
                    dictionary['rom'] = dictionary.get('rom', [])
                    dictionary['rom'].append(rom)
                else:
                    try:
                        key = None
                        if ':' in line:
                            key, value = line.split(':', 1)
                        if not key or "'" in key or '"' in key:
                            key, value = shlex.split(line)
                    except ValueError:
                        split = ' '.split(line)
                        key, value = split[0], ' '.join(split[1:])
                    dictionary[key] = value
        return dictionary


class ZipMultiDatFile(DatFile):
    """Base class for dat files."""

    def get_header(self) -> dict:
        """Get the header from the dat file."""
        return { 'name': Path(self.file).name, 'description': self.file }

    def load(self, *, load_games: bool = False) -> None:  # noqa: ARG002
        """Load the data from a ClrMamePro file."""
        self.main_key = 'datafile'
        self.games = []
        self.header = self.get_header()

        self.data = {
            self.main_key: {
                'header':  self.header,
                'game': self.games,
            },
        }
        self.name = self.header['name']
        self.full_name = self.header['description']


class DirMultiDatFile(DatFile):
    """Base class for dat files."""

    def get_header(self) -> dict:
        """Get the header from the dat file."""
        return { 'name': self.name, 'description': self.file }

    def load(self, *, load_games: bool = False) -> None:  # noqa: ARG002
        """Load the data from a ClrMamePro file."""
        self.main_key = 'datafile'
        self.games = []
        for file in os.listdir(self.file):
            if file.endswith(('.xml', '.dat')):
                self.games.append({ 'rom': { '@name': file } })

        self.name = Path(self.file).name

        self.header = self.get_header()

        self.data = {
            self.main_key: {
                'header':  self.header,
                'game': self.games,
            },
        }
        self.name = self.header['name']
        self.full_name = self.header['description']


class DatFileTypes(Enum):
    """Dat file types Enum."""

    XML = 'xml', XMLDatFile
    CLRMAMEPRO = 'clrmamepro', ClrMameProDatFile
    DOSCENTER = 'doscenter', DOSCenterDatFile
    ZIP_MULTI = 'zip_multi', ZipMultiDatFile
    DIR_MULTI = 'dir_multi', DirMultiDatFile
    UNKNOWN = 'unknown', DatFile

    def __new__(cls, *args: str, **_: str) -> 'DatFileTypes':
        """Create a new instance of DatFileTypes."""
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    def __init__(self, _: str, cls: str | None = None) -> None:
        """Initialize the DatFileTypes."""
        self._cls = cls

    def __str__(self) -> str:
        """Return the string representation of the DatFileTypes."""
        return self.value

    def __repr__(self) -> str:
        """Return the string representation of the DatFileTypes."""
        return f'DatFileTypes.{self.value.upper()}'
    @property
    def cls(self) -> type[DatFile]:
        """Return the class associated with the DatFileTypes."""
        return self._cls
