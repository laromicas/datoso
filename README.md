![Datoso](/bearlogo.png)

# Datoso

Datoso is a WIP Python command line tool to download and organize your Dat Roms.
As today the tool supports dat-omatic, redump, and translated-english dats.
It merges all the dats in a tree folder structure thought to use with Emulators rather than dats.
The dat file format must be compatible with [ROMVault](https://www.romvault.com/).

## Installation

Datoso requires python 3.10+.

Use pip (recommended to use a virtual environment):

``` bash
# Optional (create a virtual environment)
python3 -m venv venv
source venv/bin/activate

# Install datoso base (doesn't do much without plugins)
pip install datoso

# Install datoso with all official plugins
pip install datoso[all]

# Install datoso with only one of the plugins
pip install datoso[fbneo]
pip install datoso[nointro]
pip install datoso[pleasuredome]
pip install datoso[redump]
pip install datoso[translatedenglish]

# Install datoso plugins after installing datoso
pip install datoso_seed_fbneo
pip install datoso_seed_nointro
pip install datoso_seed_pleasuredome
pip install datoso_seed_redump
pip install datoso_seed_translatedenglish

```

## Usage

``` bash
# Show help
$ datoso --help

# Seed commands
$ datoso seed [list,details]

# Seed commands
$ datoso [seed] {--fetch|--process} [--filter FILTER]

# Seed install
$ datoso seed install [seed] [--repository REPOSITORY] [--branch BRANCH]

# Seed remove
$ datoso seed remove [seed]

optional arguments:
   -h, --help            show the help message and exit, feel free to append to other commands
   -v, --verbose         verbose output
   -q, --quiet           quiet output
```

## How to Build

``` bash
# Install build
$ pip install build

# Build
$ python -m build
```

## Developing a seed

``` bash
# Download base
$ git clone https://

# Build
$ python -m build
```

## Posible Issues

Be careful when updating dats from datomatic, sometimes they put a
captcha, and you may be banned if the captcha fails, captcha support is
OTW.

## TODO (without priority)

-   Migrate pydantic to dataclasses
-   Migration of current datero seeds to plugins
-   Cleaning of legacy modular code
-   Better rules update process
    -   Make update rules write to database only when finished
-   Tests
-   More dat repositories
-   Mega.nz download support (<https://pypi.org/project/mega.py/>)
-   Zippyshare download support (<https://pypi.org/project/zippyshare-downloader/>)
-   Zippyshare download support (<https://pypi.org/project/pyOneFichierClient/>)
-   Configurable folder structure (instead of emulator-focused structure use dat-repositories or viceversa)
    -   Maybe with a builder, to avoid the need to change the code anytime
-   Modular design for repositories (done for seeds, repositores
    missing)
-   Better structure for the downloaders \*


*(*) Done but to be improved*
*(**) Did it Yay!!!*

## USEFUL DEVELOPMENT COMMANDS

```bash
# Find folders with more than one dat file:
$ find . -type f -iname '*.dat' -printf '%h\n'|sort|uniq -cd

# Find and delete empty folders:
$ find . -type d -empty -print -delete

# Pylint
$ pylint src --errors-only
$ pylint src --disable=all --enable=missing-function-docstring
```

## WISHLIST (without priority)

-   Dat structure for ClrMamePro or another dat manager.
-   Web interface
-   Download from central repositories (an S3 or something like that to prevent overload main sites)
    -   Lambda to download dats and upload to S3
    -   Downloading from S3
-   Auto-Import MIA Lists (for redump)
    -   Add \[MIA\] to dat roms
-   Remove MIA from dats
-   .cue Generator

*(**) Did it Yay!!!*

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
Please make sure to update tests as appropriate.

## License

[MIT](https://choosealicense.com/licenses/mit/)
