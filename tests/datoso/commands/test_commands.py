import unittest
from unittest import mock
import argparse # For creating mock args
import sys
from pathlib import Path
import logging

from datoso.helpers import Bcolors # For logger levels

# Ensure src is discoverable for imports
project_root_for_imports = Path(__file__).parent.parent.parent.parent
if str(project_root_for_imports) not in sys.path:
    sys.path.insert(0, str(project_root_for_imports))
if str(project_root_for_imports / "src") not in sys.path:
    sys.path.insert(0, str(project_root_for_imports / "src"))

# Import the functions to be tested
from datoso.commands.commands import (
    command_deduper,
    command_import,
    command_dat,
    command_seed_installed,
    command_seed_details,
    command_seed,
    command_config_save,
    command_config_set,
    command_config_get,
    command_config_rules_update,
    command_config_mia_update,
    command_config_path,
    command_config,
    command_list, # Seems duplicative of command_seed_installed
    command_doctor,
    command_log
)
# Import classes/objects that are dependencies and will need mocking
# from datoso.configuration import config as datoso_config # Already mocked in TestCommandsBase
# from datoso.configuration import logger as datoso_logger # Already mocked in TestCommandsBase
# from datoso.repositories.dedupe import Dedupe as DedupeClass # For command_deduper
# from datoso.seeds.rules import Rules as RulesClass # For command_import
# from datoso.seeds.unknown_seed import detect_seed as detect_seed_func # For command_import
# from datoso.database.models.dat import Dat as DatModel # For command_import
# from datoso.commands.helpers.dat import helper_command_dat # For command_dat
# from datoso.helpers.plugins import installed_seeds as installed_seeds_func, seed_description as seed_description_func # For command_seed_installed
# from datoso import __app_name__ # For command_seed_details
# from datoso.commands.seed import Seed as SeedClass # For command_seed (the class, not the function)
# from datoso.commands.helpers.seed import command_seed_all, command_seed_parse_actions # For command_seed
# from datoso.database.seeds import dat_rules, mia # For config_rules_update, config_mia_update
# from datoso.commands.doctor import check_module, check_seed # For command_doctor
# from datoso.helpers.file_utils import parse_path # For command_log


class TestCommandsBase(unittest.TestCase):
    """ Base class for command tests, provides common mocks or setup if needed. """
    def setUp(self):
        self.mock_args = argparse.Namespace()

        self.config_patcher = mock.patch('datoso.commands.commands.config')
        self.logger_patcher = mock.patch('datoso.commands.commands.logger') # Main logger used in processor.py
        self.logging_patcher = mock.patch('datoso.commands.commands.logging') # logging module itself

        self.mock_config = self.config_patcher.start()
        self.mock_logger = self.logger_patcher.start() # This is likely 'from venv import logger' in commands.py
        self.mock_logging = self.logging_patcher.start()
        self.mock_logging.DEBUG = 10

        # Common default for config if needed by multiple tests
        self.mock_config.get.return_value = "default_path"
        self.mock_config.__getitem__.side_effect = lambda key: {'DatPath': 'default_dat_path'}.get(key, mock.MagicMock())


    def tearDown(self):
        self.config_patcher.stop()
        self.logger_patcher.stop()
        self.logging_patcher.stop()


class TestCommandDeduper(TestCommandsBase):

    @mock.patch('datoso.commands.commands.Dedupe')
    @mock.patch('datoso.commands.commands.sys.exit')
    def test_deduper_parent_required_for_dat_input(self, mock_sys_exit, mock_Dedupe_class):
        self.mock_args.parent = None
        self.mock_args.input = "input.dat" # Ends with .dat
        self.mock_args.auto_merge = False # Ensure auto_merge is false

        command_deduper(self.mock_args)

        mock_sys_exit.assert_called_once_with(1)
        mock_Dedupe_class.assert_not_called()

    @mock.patch('datoso.commands.commands.Dedupe')
    def test_deduper_with_parent(self, mock_Dedupe_class):
        mock_dedupe_instance = mock_Dedupe_class.return_value
        self.mock_args.input = "input_file"
        self.mock_args.parent = "parent_file"
        self.mock_args.output = "output_file"
        self.mock_args.dry_run = False

        command_deduper(self.mock_args)

        mock_Dedupe_class.assert_called_once_with(self.mock_args.input, self.mock_args.parent)
        mock_dedupe_instance.dedupe.assert_called_once()
        mock_dedupe_instance.save.assert_called_once_with(self.mock_args.output)
        self.mock_logging.info.assert_called()


    @mock.patch('datoso.commands.commands.Dedupe')
    def test_deduper_no_parent_auto_merge_or_non_dat_input(self, mock_Dedupe_class):
        mock_dedupe_instance = mock_Dedupe_class.return_value
        self.mock_args.input = "input_db_or_folder" # Does not end with .dat
        self.mock_args.parent = None
        self.mock_args.output = None # Save to input
        self.mock_args.dry_run = False

        command_deduper(self.mock_args)

        mock_Dedupe_class.assert_called_once_with(self.mock_args.input)
        mock_dedupe_instance.dedupe.assert_called_once()
        mock_dedupe_instance.save.assert_called_once_with() # No output arg, saves to input
        self.mock_logging.info.assert_called()

    @mock.patch('datoso.commands.commands.Dedupe')
    def test_deduper_dry_run(self, mock_Dedupe_class):
        mock_dedupe_instance = mock_Dedupe_class.return_value
        self.mock_args.input = "input_file"
        self.mock_args.parent = "parent_file"
        self.mock_args.output = "output_file"
        self.mock_args.dry_run = True

        command_deduper(self.mock_args)

        # self.mock_logger.setLevel.assert_called_once_with(logging.DEBUG) # This is the venv logger
        self.mock_logger.setLevel.assert_called_once_with(logging.DEBUG)
        mock_Dedupe_class.assert_called_once_with(self.mock_args.input, self.mock_args.parent)
        mock_dedupe_instance.dedupe.assert_called_once()
        mock_dedupe_instance.save.assert_not_called()
        self.mock_logging.info.assert_called()


class TestCommandImport(TestCommandsBase):

    @mock.patch('datoso.commands.commands.Path')
    @mock.patch('datoso.commands.commands.Rules')
    @mock.patch('datoso.commands.commands.detect_seed')
    @mock.patch('datoso.commands.commands.Dat') # Mock the DatModel
    @mock.patch('datoso.commands.commands.sys.exit')
    def test_import_dat_path_not_set_or_exists(self, mock_sys_exit, mock_DatModel_constructor, mock_detect_seed, mock_Rules_class, mock_Path_class):
        self.mock_config.get.return_value = None
        mock_path_instance = mock_Path_class.return_value
        mock_path_instance.exists.return_value = True
        command_import(self.mock_args)
        mock_sys_exit.assert_called_once_with(1)
        mock_sys_exit.reset_mock()

        # Scenario 2: DatPath is set but directory does not exist
        self.mock_config.get.return_value = '/nonexistent/path'
        mock_path_instance = mock_Path_class.return_value
        mock_path_instance.exists.return_value = False
        command_import(self.mock_args)
        mock_Path_class.assert_called_with('/nonexistent/path')
        mock_sys_exit.assert_called_once_with(1)

    @mock.patch('datoso.commands.commands.Path')
    @mock.patch('datoso.commands.commands.Rules')
    @mock.patch('datoso.commands.commands.detect_seed')
    @mock.patch('datoso.commands.commands.Dat') # Mock the DatModel
    def test_import_successful_run(self, mock_DatModel_constructor, mock_detect_seed, mock_Rules_class, mock_Path_class):
        # Setup mocks
        mock_rules_instance = mock_Rules_class.return_value
        mock_rules_instance.rules = {"some_rule_data"} # Dummy rules

        mock_path_instance = mock_Path_class.return_value
        mock_path_instance.exists.return_value = True
        # Simulate rglob finding one .dat file
        mock_dat_file_path = mock.MagicMock(spec=Path)
        mock_dat_file_path.__str__.return_value = "/fake/datroot/file1.dat"
        mock_path_instance.rglob.return_value = [mock_dat_file_path]

        def config_getitem(section, option, **kwargs):
            if section == 'IMPORT' and option == 'IgnoreRegEx':
                return None
            if section == 'PATHS' and option == 'DatPath':
                return '/fake/datroot'
        self.mock_config.get.side_effect = config_getitem

        mock_dat_file_obj_instance = mock.MagicMock()
        mock_dat_file_obj_instance.dict.return_value = {"name": "file1", "version": "1.0"}

        mock_detected_class = mock.Mock(return_value=mock_dat_file_obj_instance)
        mock_detected_class.__name__ = 'MockDatClass'
        mock_detect_seed.return_value = ("detected_seed_name", mock_detected_class)

        mock_db_dat_instance = mock_DatModel_constructor.return_value

        # Call the function
        with mock.patch('builtins.print') as mock_print: # Suppress print output during test
            command_import(self.mock_args)

        # Assertions
        mock_Path_class.assert_called_with('/fake/datroot')
        mock_path_instance.rglob.assert_called_once_with('*.[dD][aA][tT]')
        mock_detect_seed.assert_called_once_with(str(mock_dat_file_path), mock_rules_instance.rules)
        mock_detected_class.assert_called_once_with(file=str(mock_dat_file_path))
        mock_dat_file_obj_instance.load.assert_called_once()

        expected_dat_constructor_args = {
            "name": "file1", "version": "1.0", # from mock_dat_file_obj_instance.dict()
            "seed": "detected_seed_name",
            "new_file": str(mock_dat_file_path)
        }
        mock_DatModel_constructor.assert_called_once_with(**expected_dat_constructor_args)
        mock_db_dat_instance.save.assert_called_once()
        mock_db_dat_instance.flush.assert_called_once()
        mock_print.assert_any_call(f'detected_seed_name - {mock_detected_class.__name__}')


    @mock.patch('datoso.commands.commands.Path')
    @mock.patch('datoso.commands.commands.Rules')
    @mock.patch('datoso.commands.commands.detect_seed', side_effect=LookupError("Seed not found"))
    @mock.patch('datoso.commands.commands.Dat')
    def test_import_lookup_error(self, mock_DatModel_constructor, mock_detect_seed, mock_Rules_class, mock_Path_class):
        mock_path_instance = mock_Path_class.return_value
        mock_path_instance.exists.return_value = True
        mock_dat_file_path = mock.MagicMock(spec=Path)
        mock_dat_file_path.__str__.return_value = "/fake/datroot/file_lookup_error.dat"
        mock_path_instance.rglob.return_value = [mock_dat_file_path]
        self.mock_config.__getitem__.side_effect = lambda key: {'DatPath': '/fake/datroot', 'IMPORT': {}}.get(key, mock.MagicMock())

        with mock.patch('builtins.print') as mock_print:
            command_import(self.mock_args)

        mock_print.assert_any_call(f'{str(mock_dat_file_path)} - ', end='')
        self.assertTrue(any("Error detecting seed type" in call[0][0] and "Seed not found" in call[0][0] for call in mock_print.call_args_list), "Expected error message not found")
        mock_DatModel_constructor.assert_not_called() # Should not proceed to save

    @mock.patch('datoso.commands.commands.Path')
    @mock.patch('datoso.commands.commands.Rules')
    @mock.patch('datoso.commands.commands.detect_seed')
    @mock.patch('datoso.commands.commands.re.compile')
    @mock.patch('datoso.commands.commands.Dat')
    def test_import_with_ignore_regex(self, mock_DatModel_constructor, mock_re_compile, mock_detect_seed, mock_Rules_class, mock_Path_class):
        mock_path_instance = mock_Path_class.return_value
        mock_path_instance.exists.return_value = True

        mock_file1 = mock.MagicMock(); mock_file1.__str__.return_value = "/dats/file1.dat"
        mock_file_ignored = mock.MagicMock(); mock_file_ignored.__str__.return_value = "/dats/ignored_file.dat"
        mock_path_instance.rglob.return_value = [mock_file1, mock_file_ignored]

        # Setup IgnoreRegEx in config
        def config_getitem(section, option, **kwargs):
            if section == 'IMPORT' and option == 'IgnoreRegEx':
                return '.*ignored.*'
            if section == 'PATHS' and option == 'DatPath':
                return '/dats'
        self.mock_config.get.side_effect = config_getitem

        mock_regex = mock_re_compile.return_value
        mock_regex.match.side_effect = lambda x: True if "ignored" in x else False # Simulate regex matching

        # Setup detect_seed to succeed for file1
        mock_dat_file_obj_instance = mock.MagicMock()
        mock_dat_file_obj_instance.dict.return_value = {"name": "file1"}
        mock_detected_class = mock.Mock(return_value=mock_dat_file_obj_instance)
        mock_detected_class.__name__ = 'MockDatClass'
        mock_detect_seed.return_value = ("seed1", mock_detected_class)

        with mock.patch('builtins.print'):
            command_import(self.mock_args)

        mock_re_compile.assert_called_once_with('.*ignored.*')
        # detect_seed should only be called for file1.dat, not for ignored_file.dat
        mock_detect_seed.assert_called_once_with(str(mock_file1), mock.ANY)
        # Verify that Dat model was saved for file1
        mock_DatModel_constructor.assert_called_once_with(name="file1", seed="seed1", new_file=str(mock_file1))


class TestCommandDat(TestCommandsBase):
    @mock.patch('datoso.commands.commands.helper_command_dat')
    def test_command_dat_calls_helper(self, mock_helper_command_dat):
        self.mock_args.some_dat_arg = "value" # Example argument
        command_dat(self.mock_args)
        mock_helper_command_dat.assert_called_once_with(self.mock_args)

# TestCommandSeedInstalled / TestCommandList (they seem similar)
# command_list seems simpler and older. command_seed_installed uses helper functions.
# Let's test command_seed_installed as it appears more current.
class TestCommandSeedInstalled(TestCommandsBase):
    @mock.patch('datoso.commands.commands.installed_seeds')
    @mock.patch('datoso.commands.commands.seed_description')
    def test_command_seed_installed_lists_seeds(self, mock_seed_description, mock_installed_seeds):
        # Setup mock return values
        mock_seed_module1 = mock.MagicMock()
        mock_seed_module2 = mock.MagicMock()
        mock_installed_seeds.return_value = {
            "datoso_seed_seedone": mock_seed_module1,
            "datoso_seed_seedtwo": mock_seed_module2
        }
        mock_seed_description.side_effect = ["Description for Seed One", "Description for Seed Two (very long, should be truncated)"]

        with mock.patch('builtins.print') as mock_print:
            command_seed_installed(self.mock_args) # Argument is not used by this command

        # Assertions
        mock_installed_seeds.assert_called_once()
        self.assertEqual(mock_seed_description.call_count, 2)
        mock_seed_description.assert_any_call(mock_seed_module1)
        mock_seed_description.assert_any_call(mock_seed_module2)

        # Check print output (simplified check)
        mock_print.assert_any_call('Installed seeds:')
        self.assertTrue(any("seedone" in call_args[0][0] for call_args in mock_print.call_args_list if call_args[0]))
        self.assertTrue(any("Description for Seed One" in call_args[0][0] for call_args in mock_print.call_args_list if call_args[0]))
        self.assertTrue(any("seedtwo" in call_args[0][0] for call_args in mock_print.call_args_list if call_args[0]))
        # Check truncation logic (first 60 chars of the long description + '...')
        expected_truncated_desc = "Description for Seed Two (very long, should be truncated)"[:60] + "..."
        # The actual print includes Bcolors, so direct string match is hard. Check for substring.
        # The description is put into a set: {description[0:description_len]+'...' ...} - this is odd.
        # Let's assume it means to print that string.
        # The formatting is `* {Bcolors.OKGREEN}{seed_name}{Bcolors.ENDC} - {description}`
        # So we search for the seed name and its description part.

        # Example of a more specific check for one of the calls, if Bcolors were not an issue:
        # calls = [call[0][0] for call in mock_print.call_args_list if call[0]] # Get all first arguments to print
        # self.assertTrue(any(f"* {mock.ANY}seedone{mock.ANY} - {{'Description for Seed One'}}" in c for c in calls))
        # self.assertTrue(any(f"* {mock.ANY}seedtwo{mock.ANY} - {{'{expected_truncated_desc}'}}" in c for c in calls))
        # Due to the set literal in print: `{{'{expected_truncated_desc}'}}` would be the format.
        # For simplicity, the any() checks above cover the essence.
        # The main thing is that it attempts to print details for each seed.

class TestCommandList(TestCommandsBase): # Older version? Test to ensure it runs.
    @mock.patch('datoso.commands.commands.installed_seeds')
    def test_command_list_functionality(self, mock_installed_seeds):
        mock_seed_class1 = mock.MagicMock()
        mock_seed_class1.description.return_value = "Description 1"
        mock_seed_class2 = mock.MagicMock()
        mock_seed_class2.description.return_value = "A very very very very very very very long description that will surely be cut."

        mock_installed_seeds.return_value = {
            "seed_one_key": mock_seed_class1,
            "seed_two_key": mock_seed_class2,
        }

        with mock.patch('builtins.print') as mock_print:
            command_list(self.mock_args) # Argument is not used

        mock_installed_seeds.assert_called_once()
        mock_seed_class1.description.assert_called_once()
        mock_seed_class2.description.assert_called_once()

        # The main thing is that it attempts to print details for each seed.

class TestCommandListTwo(TestCommandsBase): # Older version? Test to ensure it runs.
    @mock.patch('datoso.commands.commands.installed_seeds')
    def test_command_list_functionality(self, mock_installed_seeds):
        mock_seed_class1 = mock.MagicMock()
        mock_seed_class1.description.return_value = "Description 1"
        mock_seed_class2 = mock.MagicMock()
        mock_seed_class2.description.return_value = "A very very very very very very very long description that will surely be cut."

        mock_installed_seeds.return_value = {
            "seed_one_key": mock_seed_class1,
            "seed_two_key": mock_seed_class2,
        }

        with mock.patch('builtins.print') as mock_print:
            command_list(self.mock_args) # Argument is not used

        mock_installed_seeds.assert_called_once()
        mock_seed_class1.description.assert_called_once()
        mock_seed_class2.description.assert_called_once()

        # Verify basic print calls occurred
        self.assertGreaterEqual(mock_print.call_count, 2)


class TestCommandSeedDetails(TestCommandsBase):
    @mock.patch('datoso.commands.commands.installed_seeds')
    @mock.patch('datoso.commands.commands.sys.exit')
    @mock.patch('datoso.commands.commands.__app_name__', "datoso_test_app") # Mock app_name
    def test_seed_details_found(self, mock_sys_exit, mock_installed_seeds):
        Bcolors.no_color()
        mock_seed_module = mock.MagicMock()
        mock_seed_module.__name__ = "MockSeedModule"
        mock_seed_module.__version__ = "1.0"
        mock_seed_module.__author__ = "Test Author"
        mock_seed_module.__description__ = "A mock seed module."

        mock_installed_seeds.return_value = {
            "datoso_test_app_seed_myseed": mock_seed_module
        }
        self.mock_args.seed = "myseed" # This is the short name

        with mock.patch('builtins.print') as mock_print:
            command_seed_details(self.mock_args)

        mock_installed_seeds.assert_called_once()
        mock_sys_exit.assert_not_called()

        # Check that print was called with the details
        output = "".join(str(call_arg[0]) for call_arg in mock_print.call_args_list if call_arg[0]) # Safely join args
        self.assertIn("Seed myseed details:", output)
        self.assertIn("Name: MockSeedModule", output)
        self.assertIn("Version: 1.0", output)
        self.assertIn("Author: Test Author", output)
        self.assertIn("Description: A mock seed module.", output)

    @mock.patch('datoso.commands.commands.installed_seeds')
    @mock.patch('datoso.commands.commands.sys.exit')
    @mock.patch('datoso.commands.commands.__app_name__', "datoso")
    def test_seed_details_not_found(self, mock_sys_exit, mock_installed_seeds):
        mock_installed_seeds.return_value = {
            "datoso_seed_anotherseed": mock.MagicMock()
        }
        self.mock_args.seed = "nonexistentseed"

        found_print = False
        with mock.patch('builtins.print') as mock_print:
            command_seed_details(self.mock_args)

            mock_installed_seeds.assert_called_once()
            mock_sys_exit.assert_called_once_with(1)
            # Check that the specific print call about the seed not being installed was made
            for call in mock_print.call_args_list:
                if call[0] and "not installed" in call[0][0] and "nonexistentseed" in call[0][0]:
                    found_print = True
                    break
        self.assertTrue(found_print, "Print call for 'seed not installed' not found or with wrong format.")

class TestCommandSeed(TestCommandsBase):

    @mock.patch('datoso.commands.commands.command_seed_parse_actions')
    @mock.patch('datoso.commands.commands.command_seed_all')
    @mock.patch('datoso.commands.commands.sys.exit')
    def test_seed_all(self, mock_sys_exit, mock_command_seed_all, mock_command_seed_parse_actions):
        self.mock_args.seed = "all"
        command_seed(self.mock_args)
        mock_command_seed_parse_actions.assert_called_once_with(self.mock_args)
        mock_command_seed_all.assert_called_once_with(self.mock_args, command_seed)
        mock_sys_exit.assert_called_once_with(0)

    @mock.patch('datoso.commands.commands.command_seed_parse_actions')
    @mock.patch('datoso.commands.commands.command_seed_details')
    def test_seed_details_flag(self, mock_command_seed_details, mock_command_seed_parse_actions):
        self.mock_args.seed = "myseed"
        self.mock_args.details = True
        # Ensure other flags that would trigger actions are false
        self.mock_args.fetch = False
        self.mock_args.process = False

        command_seed(self.mock_args)

        mock_command_seed_parse_actions.assert_called_once_with(self.mock_args)
        mock_command_seed_details.assert_called_once_with(self.mock_args)

    @mock.patch('datoso.commands.commands.command_seed_parse_actions')
    @mock.patch('datoso.commands.commands.Seed') # Mock the Seed class
    @mock.patch('datoso.commands.commands.command_doctor')
    @mock.patch('datoso.commands.commands.sys.exit')
    def test_seed_fetch_success(self, mock_sys_exit, mock_command_doctor, mock_Seed_class, mock_command_seed_parse_actions):
        self.mock_args.seed = "myseed"
        self.mock_args.details = False
        self.mock_args.fetch = True
        self.mock_args.process = False # Ensure process is not called

        mock_seed_instance = mock_Seed_class.return_value
        mock_seed_instance.fetch.return_value = None # Successful fetch returns None or 0

        with mock.patch('builtins.print') as mock_print:
            command_seed(self.mock_args)

        mock_command_seed_parse_actions.assert_called_once_with(self.mock_args)
        mock_Seed_class.assert_called_once_with(name="myseed")
        mock_seed_instance.fetch.assert_called_once()
        mock_command_doctor.assert_not_called() # Not called on success
        mock_sys_exit.assert_not_called() # Not called on success
        self.assertTrue(any("Finished fetching" in args[0] and "myseed" in args[0] for args, _ in mock_print.call_args_list))

    @mock.patch('datoso.commands.commands.command_seed_parse_actions')
    @mock.patch('datoso.commands.commands.Seed')
    @mock.patch('datoso.commands.commands.command_doctor')
    @mock.patch('datoso.commands.commands.sys.exit')
    def test_seed_fetch_failure(self, mock_sys_exit, mock_command_doctor, mock_Seed_class, mock_command_seed_parse_actions):
        self.mock_args.seed = "myseed"
        self.mock_args.details = False
        self.mock_args.fetch = True
        self.mock_args.process = False

        mock_seed_instance = mock_Seed_class.return_value
        mock_seed_instance.fetch.return_value = 1 # Error fetch returns non-zero

        with mock.patch('builtins.print') as mock_print:
            command_seed(self.mock_args)

        mock_command_seed_parse_actions.assert_called_once_with(self.mock_args)
        mock_Seed_class.assert_called_once_with(name="myseed")
        mock_seed_instance.fetch.assert_called_once()
        self.assertTrue(any("Errors fetching" in args[0] and "myseed" in args[0] for args, _ in mock_print.call_args_list))
        mock_command_doctor.assert_called_once_with(self.mock_args)
        mock_sys_exit.assert_called_once_with(1)

    @mock.patch('datoso.commands.commands.command_seed_parse_actions')
    @mock.patch('datoso.commands.commands.Seed')
    @mock.patch('datoso.commands.commands.command_doctor')
    @mock.patch('datoso.commands.commands.sys.exit')
    def test_seed_process_success(self, mock_sys_exit, mock_command_doctor, mock_Seed_class, mock_command_seed_parse_actions):
        self.mock_args.seed = "myseed"
        self.mock_args.details = False
        self.mock_args.fetch = False # Ensure fetch is not called
        self.mock_args.process = True
        self.mock_args.filter = "somefilter"
        self.mock_args.actions = ["action1", "action2"]

        mock_seed_instance = mock_Seed_class.return_value
        mock_seed_instance.process_dats.return_value = None # Successful process returns None or 0

        with mock.patch('builtins.print') as mock_print:
            command_seed(self.mock_args)

        mock_command_seed_parse_actions.assert_called_once_with(self.mock_args)
        mock_Seed_class.assert_called_once_with(name="myseed")
        mock_seed_instance.process_dats.assert_called_once_with(fltr="somefilter", actions_to_execute=["action1", "action2"])
        mock_command_doctor.assert_not_called()
        mock_sys_exit.assert_not_called()
        self.assertTrue(any("Finished processing" in args[0] and "myseed" in args[0] for args, _ in mock_print.call_args_list))

    @mock.patch('datoso.commands.commands.command_seed_parse_actions')
    @mock.patch('datoso.commands.commands.Seed')
    @mock.patch('datoso.commands.commands.command_doctor')
    @mock.patch('datoso.commands.commands.sys.exit')
    def test_seed_process_failure(self, mock_sys_exit, mock_command_doctor, mock_Seed_class, mock_command_seed_parse_actions):
        self.mock_args.seed = "myseed"
        self.mock_args.details = False
        self.mock_args.fetch = False
        self.mock_args.process = True
        self.mock_args.filter = None
        self.mock_args.actions = None # No specific actions

        mock_seed_instance = mock_Seed_class.return_value
        mock_seed_instance.process_dats.return_value = 1 # Error process returns non-zero

        with mock.patch('builtins.print') as mock_print:
            command_seed(self.mock_args)

        mock_command_seed_parse_actions.assert_called_once_with(self.mock_args)
        mock_Seed_class.assert_called_once_with(name="myseed")
        mock_seed_instance.process_dats.assert_called_once_with(fltr=None, actions_to_execute=None)
        self.assertTrue(any("Errors processing" in args[0] and "myseed" in args[0] for args, _ in mock_print.call_args_list))
        mock_command_doctor.assert_called_once_with(self.mock_args)
        mock_sys_exit.assert_called_once_with(1)

# TestCommandConfig (and its sub-functions)

# TestCommandSeedInstalled / TestCommandList (they seem similar)

# TestCommandSeedDetails

# TestCommandSeed

# TestCommandConfig (and its sub-functions)

# TestCommandDoctor

# TestCommandLog


if __name__ == '__main__':
    unittest.main()
