release 1.1.0
- Extracted FileUtils to a separate module (breaking change)
- Production Stable (forgot to change this a long time ago)
- Updated dependencies
- Now datoso means DAT Organizer and SOrter
- Updated mia and systems
- Several fixes to dedupe and automerge
- Request helper

release 1.0.1
- Updated systems.json
- Bump internetarchive library

release 1.0.0 (breaking change)
- Changed logo
- Bumped needed python version to 3.11
- Refactored processor
- Enhanced dats import detector
- A lot of refactoring and code cleanup

release 0.3.13
- Added MIAs for redump!!!
- Some code refactor.

release 0.3.12
- Updated systems.json

release 0.3.11
- Updated systems.json
- Override actions (In progress)
- Config wrapper allows to get configuration from environment variable
- Dockerfile and compose.yaml (In progress)

release 0.3.10
- Some fixes for clrmame dat reader
- Some changes to directory handling to work better with windowsW

release 0.3.9
- Created custom urljoin multi os safe.

release 0.3.8
- Fixed pydantic version to v1 as v2 is incompatible
- Some dedupe fixes

release 0.3.7
- Updated Systems
- Added details to dat

relsease 0.3.6
- Fix bug when date day is 20

relsease 0.3.5
- New option to configure downloader
  - urllib
  - wget
  - curl
  - aria2c
- Little bug fix

release 0.3.4
- Better fuzzy dates handling

release 0.3.3
- Fixed regression

release 0.3.2
- Patched (ugly) to prevent deleting when newer found
- Added showprogress that can be shared with plugins

release 0.3.1
- Added command log
- Added action filter when process
- Enhancing Detecting file through header
- Updated Libraries

release 0.3.0
- Added log on error and continue
- Left alpha and now is beta.


release 0.2.9
- Prevents updating when newer dat is already processed.

release 0.2.8.1
- Fixed regresion

release 0.2.8
- Support for non-standard "datafile" key in dats XMLs
- Enhanced outputs

release 0.2.7
- Fixed regression

release 0.2.6
- Dat deletion from command line

release 0.2.5
- Added non-faling move to FileUtils

release 0.2.4
- Fixed regresion

release 0.2.3
- Standarized minimum version of all dependencies
- Fixed a bug where internetarchive seeds where not being processed
- Minimum recommended version

release 0.2.2
Skipped

release 0.2.1
- Autoinitialize database on first run
- Seeds are now plugins
- Removed seed installator/manager
- Added factory support for actions
- Internetarchive is now a plugin
- Cleaned up the code
- Reorganized the code
- Dat import of current datdir
- Added some File and folder helpers
- Datoso now has a logo (To be changed)


release 0.2.0
- Added --developer to install with git repository instead of zip release
- Cleaned up the code a bit
- Reorganized the code a bit
- Started to add current dat imports
- Added ruff as linter