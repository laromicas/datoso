[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/laromicas/datoso)
[![PyPI version](https://badge.fury.io/py/datoso.svg)](https://badge.fury.io/py/datoso)
[![Downloads](https://pepy.tech/badge/datoso)](https://pepy.tech/project/datoso)
[![License](https://img.shields.io/pypi/l/datoso.svg)](https://pypi.org/project/datoso/)
[![Python Version](https://img.shields.io/pypi/pyversions/datoso.svg)](https://pypi.org/project/datoso/)

![Datoso](/bearlogo.svg)

# Datoso

Datoso (DAT Organizer and SOrter) is a WIP Python command line tool to download and organize your Dat Roms.
As today the tool supports dat-omatic, redump, and pleasuredome dats.
It merges all the dats in a tree folder structure thought to use with Emulators rather than dats.
The dat file format must be compatible with [ROMVault](https://www.romvault.com/).

# Features

- It can download updated dats from different sources (dat-omatic, redump, and pleasuredome)
- It can process dats to generate a folder structure compatible with emulators
- It can deduplicate dats
- It can import dats from existing RomVault
- It can mark MIA roms


## Installation

Datoso requires python 3.11+.

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
pip install datoso[SEED_NAME]
# e.g.
pip install datoso[fbneo]

# or install the plugins separately
# Install datoso plugins after installing datoso
pip install datoso_seed_SEED_NAME
# e.g.
pip install datoso_seed_nointro

```
### Seeds available:
- fbneo (Final Burn Neo)
- nointro (No-Intro Datomatic)
- redump (Redump)
- pleasuredome (Pleasuredome)
- tdc (Total DOS Collection)
- vpinmame (Visual Pinball)
- whdload (WHDLoad)
- eggman (Eggman Teknoparrot, ALLs.net)
- md_enhanced (Mega Drive Enhanced) (deprecated)
- sfc_enhancedcolors (Super Famicom Enhanced Colors) (deprecated)
- sfc_msu1 (Super Famicom MSU1) (deprecated)
- sfc_speedhacks (Super Famicom Speed Hacks) (deprecated)
- translatedenglish (Translated English) (deprecated)


## Usage

``` bash
# Show help
$ datoso --help

usage: datoso [-h] [-v] {config,doctor,dat,seed,import,deduper,all} ...

Update dats from different sources.

positional arguments:
  {config,doctor,dat,seed,import,deduper,base,fbneo,nointro,pleasuredome,private,redump,translatedenglish,all}
                        sub-command help
    config              Show configuration
    doctor              Doctor installed seeds
    dat                 Changes configuration in current dats
    seed                Seed admin commands
    import              Import dats from existing romvault
    deduper             Deduplicate dats, removes duplicates from input dat existing in parent dat
    all                 Update seed all

options:
  -h, --help            show this help message and exit
  -v, --version         show version



# Seed commands
$ datoso seed [list,details]

# Seed commands
$ datoso {<seed> | all} {--fetch | --process} [--filter FILTER]
#e.g.
$ datoso redump --fetch                    # Downloads all dats from redump
$ datoso redump --process --filter IBM     # Process all dats downloaded in the step before that has IBM in its name

# Dat management
$ datoso dat -d <dat_name>                 # Finds a dat by partial name (cannot set/modify properties)
$ datoso dat -d <seed>:<dat_name>          # Finds a dat by partial name in a seed (can set/modify properties)
$ datoso dat -d <dat_name> --fields <field1> <field2> ...  # Shows only the fields specified
$ datoso dat -d <seed>:<dat_name> --fields <field1> <field2> ...  # Shows only the fields specified
$ datoso dat -d <dat_name> -on             # Finds a dat by partial name in a seed and shows the full name (for setting properties)
$ datoso dat -d <seed>:<dat_name> --set <property>=<value>   # Sets a property of a dat
$ datoso dat -d <seed>:<dat_name> --unset <property>         # Unsets a property of a dat


# Doctor
$ datoso doctor [seed]        # Validates if all requirements for all seeds are OK

# Deduper
$ datoso deduper -input <input_dat> -p <parent_dat> [-o <output_dat>]   # If output dat is not especified, input dat will be overwritten.

optional arguments:
   -h, --help            show the help message and exit, feel free to append to other commands
   -v, --verbose         verbose output
   -q, --quiet           quiet output
```

## Developing a seed

Check [datoso_seed_base](https://github.com/laromicas/datoso_seed_base)

## Posible Issues

Be careful when updating dats from datomatic, sometimes they put a
captcha, and you may be banned if the captcha fails.

## TODO (without priority)
-   Firmwares  https://gbatemp.net/download/nintendo-switch-firmware-datfile.36558/
-   Better rules update process
-   Tests
-   More dat repositories
-   Mega.nz download support (<https://pypi.org/project/mega.py/>)
-   Zippyshare download support (<https://pypi.org/project/zippyshare-downloader/>)
-   OneFichier download support (<https://pypi.org/project/pyOneFichierClient/>)
-   Templating for folder structure (opinionated, per seed, custom)
    - currently is opinionated and can be customized with static paths


## WISHLIST (without priority)

-   Support for deduplication on ClrMamePro dat structure
-   Web interface
-   Download from central repositories (an S3 or something like that to prevent overload main sites)
    -   Lambda to download dats and upload to S3
    -   Downloading from S3
-   Auto-Import MIA Lists (for redump)
-   .cue Generator for Non-Redump Dats

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
Please make sure to update tests as appropriate.

## License

[MIT](https://choosealicense.com/licenses/mit/)
