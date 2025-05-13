"""Hashes index module."""


class HashesIndex:
    """Index of hashes."""

    valid_hashes: list
    sha256: dict
    sha1: dict
    md5: dict
    crc: dict
    sizes: dict

    def __init__(self) -> None:
        """Initialize the index."""
        self.sha256 = {}
        self.sha1 = {}
        self.md5 = {}
        self.crc = {}
        self.sizes = {}
        self.valid_hashes = ['sha256', 'sha1', 'md5', 'crc']

    def add_rom(self, rom: dict) -> None:
        """Add a rom to the index."""
        for rom_hash in self.valid_hashes:
            if rom_hash in rom:
                if rom_hash not in self.__dict__:
                    self.__dict__[rom_hash] = {}
                self.__dict__[rom_hash][rom[rom_hash]] = rom

    def has_rom(self, rom: dict, rom_hash: str | None=None) -> bool:
        """Check if a rom exists in the index."""
        if rom_hash:
            return rom_hash in rom and rom_hash in self.__dict__ \
                and rom[rom_hash] in self.__dict__[rom_hash] \
                and rom['size'] == self.__dict__[rom_hash][rom[rom_hash]]['size']
        return any((rom_hash in rom and rom_hash in self.__dict__ \
                    and rom[rom_hash] in self.__dict__[rom_hash] \
                    and rom['size'] == self.__dict__[rom_hash][rom[rom_hash]]['size']) \
                    for rom_hash in self.valid_hashes)

    def get_sha256s(self) -> list:
        """Get the sha256s."""
        return self.sha256.keys()

    def get_sha1s(self) -> list:
        """Get the sha1s."""
        return self.sha1.keys()

    def get_md5s(self) -> list:
        """Get the md5s."""
        return self.md5.keys()

    def get_crcs(self) -> list:
        """Get the crcs."""
        return self.crc.keys()
