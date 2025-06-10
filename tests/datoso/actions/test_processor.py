import sys
from pathlib import Path

project_root_for_imports = Path(__file__).parent.parent.parent.parent
src_path = project_root_for_imports / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import unittest
from unittest import mock

import datoso.actions.processor
from datoso.actions.processor import Processor, Process, LoadDatFile, DeleteOld, Copy, SaveToDatabase, MarkMias, AutoMerge, Deduplicate
from datoso.configuration import config as datoso_config
from datoso.configuration import logger as datoso_logger
from datoso.database.models.dat import Dat as DatModel # Actual Dat model for type hinting if needed
from datoso.repositories.dat_file import DatFile as DatFileRepo # Actual DatFile for type hinting
from datoso.repositories.dedupe import Dedupe as DedupeClass # Actual Dedupe class for mocking

# Mock classes for dependencies
class MockDatFile(DatFileRepo): # Inherit to satisfy type checks if any, but override methods
    def __init__(self, file=None, seed=None, **kwargs):
        self.file = Path(file) if file else None
        self.name = self.file.name if self.file else "mock_datfile.dat"
        self.path = str(self.file.parent) if self.file else "mock_path/" # DatFile stores path as string
        self.date = "2023-01-15" # Default newer date for file
        self.new_file = None # Will be Path object if set
        self._data = {
            "name": self.name,
            "path": self.path,
            "date": self.date,
            "new_file": None,
        }
        # Ensure 'name' and 'seed' are always part of kwargs for MockDatFile
        # These are essential for DatModel instantiation if this dict is used.
        self.name = kwargs.pop('name', self.file.name if self.file else "mock_datfile.dat")
        if seed is not None:
            self.seed = seed
        else:
            self.seed = kwargs.pop('seed', "default_mock_seed")

        self.path = str(self.file.parent) if self.file else "mock_path/"
        self.date = kwargs.pop('date', "2023-01-15")
        self.version = kwargs.pop('version', None)
        self.company = kwargs.pop('company', None)
        self.system = kwargs.pop('system', None)
        self.comment = kwargs.pop('comment', None)
        self.new_file = kwargs.pop('new_file', None) # Can be str or Path

        # Apply any other kwargs as attributes directly
        for k, v in kwargs.items():
            setattr(self, k, v)

        self.load = mock.Mock()

    def dict(self):
        # Return a dictionary suitable for DatModel(**returned_dict)
        # Only include keys that DatModel's __init__ or setters can handle.
        # Based on DatModel structure, this typically includes:
        # name, seed, path, date, version, company, system, new_file, comment
        data = {
            "name": self.name,
            "seed": self.seed,
            "path": self.path,
            "date": self.date,
            "version": self.version,
            "company": self.company,
            "system": self.system,
            "comment": self.comment,
            "new_file": str(self.new_file) if isinstance(self.new_file, Path) else self.new_file,
        }
        # Remove keys with None values, as DatModel might prefer missing keys over None
        return {k: v for k, v in data.items() if v is not None}

class MockDatDB(DatModel):
    def __init__(self, **kwargs):
        name_arg = kwargs.pop('name', "mock_dat_db_default_name")
        seed_arg = kwargs.pop('seed', "mock_dat_db_default_seed")

        super().__init__(name=name_arg, seed=seed_arg)

        self.id = kwargs.get('id', None)
        self.new_file = kwargs.get('new_file', None)
        self.date = kwargs.get('date', "2023-01-01")
        self.enabled = kwargs.get('enabled', True)
        self.automerge = kwargs.get('automerge', False)
        self.parent_id = kwargs.get('parent_id', None)
        self.parent = kwargs.get('parent', None)
        self.static_path = kwargs.get('static_path', "db_static_path/")
        self.company = kwargs.get('company', None)
        self.system = kwargs.get('system', None)
        self.version = kwargs.get('version', None)
        self.comment = kwargs.get('comment', None)

        for k,v in kwargs.items():
            setattr(self,k,v)

        self.name = name_arg # Ensure these are set on instance even if super() does something different
        self.seed = seed_arg

        self.load = mock.Mock()
        self.save = mock.Mock()
        self.flush = mock.Mock()

    def to_dict(self):
        data = {}
        attrs_to_dict = ['id', 'name', 'seed', 'new_file', 'date', 'enabled', 'automerge', 'parent_id',
                         'static_path', 'company', 'system', 'version', 'comment']
        for attr in attrs_to_dict:
            if hasattr(self, attr):
                val = getattr(self, attr)
                if attr == 'new_file' and isinstance(val, Path):
                    data[attr] = str(val)
                else:
                    data[attr] = val

        for k,v in self.__dict__.items():
            if k not in data and not k.startswith('_') and \
               k not in DatModel.__dict__ and \
               k not in ['metadata', 'registry', '_sa_instance_state', 'parent', 'seed_obj', 'seed_id', 'dat_file_id', 'load', 'save', 'flush']:
                 data[k] = v
        return data

    def is_enabled(self):
        return self.enabled


# Mock Action Classes
class MockActionSuccess(Process):
    def process(self):
        self._file_dat = getattr(self, '_file_dat', None) or MockDatFile(file="processed_action1.dat")
        self._database_dat = getattr(self, '_database_dat', None) or MockDatDB(name="db_processed_action1.dat")
        return "MockActionSuccess: Processed"

class MockActionStop(Process):
    def process(self):
        self.stop = True
        return "MockActionStop: Stopped"

class MockActionUpdateData(Process):
    def process(self):
        if self._file_dat:
            self._file_dat.name = "updated_file.dat"
        if self._database_dat:
            self._database_dat.name = "updated_db.dat"
        return "MockActionUpdateData: Data Updated"

# Using a dictionary for patching globals in Processor tests
_mock_actions_for_globals_patch = {
    'MockActionSuccess': MockActionSuccess,
    'MockActionStop': MockActionStop,
    'MockActionUpdateData': MockActionUpdateData,
    'DatFile': MockDatFile, # For Process base class if it tries to instantiate
    'Dat': MockDatDB        # For Process base class
}


class TestProcessorClass(unittest.TestCase):
    def setUp(self):
        self.default_seed = "proc_seed"
        self.patcher = mock.patch.dict(datoso.actions.processor.__dict__,
                                       _mock_actions_for_globals_patch,
                                       clear=True)
        self.mocked_globals = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_processor_initialization(self):
        processor = Processor(seed=self.default_seed, file="test_file.dat", actions=[])
        self.assertEqual(processor.seed, self.default_seed)
        self.assertEqual(processor.file, "test_file.dat")
        self.assertEqual(processor.actions, [])
        self.assertIsNone(processor._file_dat)
        self.assertIsNone(processor._database_dat)

    def test_processor_initialization_with_actions(self):
        actions_list = [{"action": "SomeAction"}]
        processor = Processor(actions=actions_list, seed=self.default_seed)
        self.assertEqual(processor.actions, actions_list)

    def test_processor_process_empty_actions(self):
        processor = Processor(actions=[], seed=self.default_seed)
        results = list(processor.process())
        self.assertEqual(results, [])

    def test_processor_process_single_action(self):
        # Action dict now includes name and seed which MockActionSuccess will use
        actions = [{"action": "MockActionSuccess", "name": "TestDat"}]
        processor = Processor(actions=actions, file="test.dat", seed=self.default_seed)
        results = list(processor.process())

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], "MockActionSuccess: Processed")
        self.assertIsNotNone(processor._file_dat)
        self.assertEqual(processor._file_dat.name, "processed_action1.dat")
        self.assertIsNotNone(processor._database_dat)
        self.assertEqual(processor._database_dat.name, "db_processed_action1.dat")

    def test_processor_process_multiple_actions_and_data_flow(self):
        actions = [
            {"action": "MockActionSuccess", "name":"InitialDat"},
            {"action": "MockActionUpdateData", "name":"UpdatedDat"}
        ]
        processor = Processor(actions=actions, file="test.dat", seed=self.default_seed)
        processor.MockActionSuccess = MockActionSuccess
        results = list(processor.process())
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], "MockActionSuccess: Processed")
        self.assertEqual(results[1], "MockActionUpdateData: Data Updated")
        self.assertIsNotNone(processor._file_dat)
        self.assertEqual(processor._file_dat.name, "updated_file.dat")
        self.assertIsNotNone(processor._database_dat)
        self.assertEqual(processor._database_dat.name, "updated_db.dat")

    def test_processor_process_stops_on_action_stop_true(self):
        actions = [
            {"action": "MockActionSuccess", "name":"Dat1"},
            {"action": "MockActionStop", "name":"Dat2"},
            {"action": "MockActionUpdateData", "name":"Dat3"}
        ]
        processor = Processor(actions=actions, seed=self.default_seed)
        results = list(processor.process())
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], "MockActionSuccess: Processed")
        self.assertEqual(results[1], "MockActionStop: Stopped")
        self.assertEqual(processor._file_dat.name, "processed_action1.dat")


class TestProcessBaseClass(unittest.TestCase):
    def setUp(self):
        self.mock_file_path = Path("test_file.dat") # Source file for processing
        class ConcreteProcess(Process):
            # _class is used by Process.load_file_dat if no factory
            # We assign MockDatFile so it attempts to instantiate our mock
            _class = MockDatFile
            def process(self):
                return "Processed" # Dummy implementation for abstract method
        self.ConcreteProcess = ConcreteProcess
        self.mock_file_path = Path("test_file.dat")
        self.default_seed = "test_seed_process_base"
        self.default_name = self.mock_file_path.name

    def test_load_file_dat_no_factory(self):
        process_instance = self.ConcreteProcess(file=self.mock_file_path, name=self.default_name, seed=self.default_seed)
        file_dat = process_instance.load_file_dat()
        self.assertIsInstance(file_dat, MockDatFile)
        self.assertEqual(file_dat.file, self.mock_file_path)
        file_dat.load.assert_called_once()

    def test_load_file_dat_with_factory(self):
        mock_factory = mock.Mock(return_value=MockDatFile)
        process_instance = self.ConcreteProcess(file=self.mock_file_path, _factory=mock_factory, name=self.default_name, seed=self.default_seed)
        file_dat_instance = process_instance.load_file_dat()
        mock_factory.assert_called_once_with(self.mock_file_path)
        self.assertIsInstance(file_dat_instance, MockDatFile)
        file_dat_instance.load.assert_called_once()

    def test_file_dat_property_loads_if_none(self):
        process_instance = self.ConcreteProcess(file=self.mock_file_path, name=self.default_name, seed=self.default_seed)
        with mock.patch.object(process_instance, 'load_file_dat', wraps=process_instance.load_file_dat) as spy_load:
            file_dat_obj = process_instance.file_dat
            spy_load.assert_called_once() # load_file_dat should be called
            self.assertIsInstance(file_dat_obj, MockDatFile)
        # Reset the mock for the next assertion if load was indeed called and _file_dat is now set
        spy_load.reset_mock()
        file_dat_obj_again = process_instance.file_dat # Access again
        spy_load.assert_not_called() # Should not call load_file_dat again
        self.assertIs(file_dat_obj, file_dat_obj_again)


    @mock.patch('datoso.actions.processor.Dat')
    def test_load_database_dat(self, mock_dat_constructor):
        # Mock the constructor to return an instance of MockDatDB
        mock_dat_constructor.return_value = MockDatDB(name="test_db.dat", seed=self.default_seed)
        file_dat_dict_content = {"name": "test.dat", "version": "1.0", "company": "Nintendo"}
        process_instance = self.ConcreteProcess(file=self.mock_file_path, name="test.dat", seed=self.default_seed)
        process_instance._file_dat = MockDatFile(file=self.mock_file_path, seed=self.default_seed, **file_dat_dict_content)

        # This is the instance we expect load_database_dat to create and work with
        expected_db_instance = mock_dat_constructor.return_value

        db_dat_loaded = process_instance.load_database_dat()

        self.assertIs(db_dat_loaded, expected_db_instance)
        mock_dat_constructor.assert_called_once_with(**{**file_dat_dict_content, 'seed': self.default_seed, 'date': '2023-01-15', 'path': '.'})
        expected_db_instance.load.assert_called_once()


    @mock.patch('datoso.actions.processor.Dat', new=MockDatDB)
    def test_database_dat_property_loads_if_none(self):
        process_instance = self.ConcreteProcess(file=self.mock_file_path, name=self.default_name, seed=self.default_seed)
        process_instance._file_dat = MockDatFile(file=self.mock_file_path, name=self.default_name, seed=self.default_seed)

        with mock.patch.object(process_instance, 'load_database_dat', wraps=process_instance.load_database_dat) as spy_load:
            db_dat_obj = process_instance.database_dat
            spy_load.assert_called_once()
            self.assertIsInstance(db_dat_obj, MockDatDB)

        spy_load.reset_mock()
        db_dat_obj_again = process_instance.database_dat
        spy_load.assert_not_called()
        self.assertIs(db_dat_obj, db_dat_obj_again)


    def test_file_data_property(self):
        process_instance = self.ConcreteProcess(file=self.mock_file_path, name=self.default_name, seed=self.default_seed)
        mock_file_dat_instance = MockDatFile(file=self.mock_file_path, custom_field="custom_value", name="specific.dat", seed=self.default_seed)
        process_instance._file_dat = mock_file_dat_instance
        # Merge the dict() output with any extra attributes from __dict__
        base_data = process_instance._file_dat.dict()
        extra_data = {k: v for k, v in process_instance._file_dat.__dict__.items() if k not in base_data and not k.startswith('_')}
        data = {**base_data, **extra_data}

        self.assertEqual(data['name'], "specific.dat")
        self.assertEqual(data.get('custom_field'), "custom_value")  # Now custom_field is present
        self.assertEqual(data['seed'], self.default_seed)


    def test_database_data_property(self):
        process_instance = self.ConcreteProcess(file=self.mock_file_path, name=self.default_name, seed=self.default_seed)
        process_instance._file_dat = MockDatFile(file=self.mock_file_path, name="filedatname", seed=self.default_seed)
        mock_db_dat_instance = MockDatDB(name="db_name_override", db_field="db_value", system="SNES", seed=self.default_seed)
        process_instance._database_dat = mock_db_dat_instance
        data = process_instance.database_data
        self.assertEqual(data['name'], "db_name_override")
        self.assertEqual(data.get('db_field'), "db_value") # Use .get for custom fields
        self.assertEqual(data['system'], "SNES")
        self.assertEqual(data['seed'], self.default_seed)


    def test_database_dat_setter(self):
        process_instance = self.ConcreteProcess(name=self.default_name, seed=self.default_seed)
        new_db_dat = MockDatDB(name="manually_set_db.dat", seed=self.default_seed)
        process_instance.database_dat = new_db_dat
        self.assertEqual(process_instance._database_dat.name, "manually_set_db.dat")
        self.assertIs(process_instance.database_dat, new_db_dat)


class TestLoadDatFileAction(unittest.TestCase):
    def setUp(self):
        self.mock_file_path = Path("test_action_load.dat")

    def setUp(self):
        self.mock_file_path = Path("test_action_load.dat")
        self.default_seed = "load_file_seed"
        self.default_name = self.mock_file_path.name

    @mock.patch('datoso.actions.processor.Dat', new_callable=MockDatDB) # Patch with instance of MockDatDB
    def test_process_success(self, mock_dat_constructor):
        action = LoadDatFile(file=self.mock_file_path, _class=MockDatFile, name=self.default_name, seed=self.default_seed)
        result = action.process()

        self.assertEqual(result, "Loaded")
        self.assertIsInstance(action._file_dat, MockDatFile)
        self.assertEqual(action._file_dat.file, self.mock_file_path)
        self.assertEqual(action._file_dat.seed, self.default_seed)
        action._file_dat.load.assert_called_once()

        self.assertIsInstance(action._database_dat, MockDatDB)
        # Database name and seed should come from file_dat's dict
        self.assertEqual(action._database_dat.name, self.default_name)
        self.assertEqual(action._database_dat.seed, self.default_seed)
        action._database_dat.load.assert_called_once()


    @mock.patch('datoso.actions.processor.Dat', new_callable=MockDatDB)
    @mock.patch.object(datoso_logger, 'exception')
    def test_process_exception_handling(self, mock_logger_exception, mock_dat_constructor_instance):
        # mock_dat_constructor_instance is the INSTANCE of MockDatDB thanks to new_callable=MockDatDB
        mock_faulty_class = mock.Mock(side_effect=Exception("Load failed"))
        action = LoadDatFile(file=self.mock_file_path, _class=mock_faulty_class, name=self.default_name, seed=self.default_seed)

        result = action.process()

        self.assertEqual(result, "Error")
        self.assertEqual(action.status, "Error")
        mock_logger_exception.assert_called_once()
        # Check that the constructor for Dat (which is our MockDatDB) was NOT called if _class() fails early
        # This depends on where the exception occurs. If _class() itself fails (instantiation), then Dat() won't be called.
        # If _class().load() fails, Dat() might still be called.
        # For "Instantiation failed during _class()", Dat() should not be called.
        # The mock_dat_constructor is the class, its return_value is the instance.
        # We need to check if the class was called.
        # This is tricky because new_callable=MockDatDB means the class itself is replaced by an instance.
        # Let's re-patch it for this specific test to be the class itself.
        with mock.patch('datoso.actions.processor.Dat') as class_level_mock_Dat:
            action_failing_instantiation = LoadDatFile(file=self.mock_file_path, _class=mock_faulty_class, name=self.default_name, seed=self.default_seed)
            action_failing_instantiation.process()
            class_level_mock_Dat.assert_not_called()


    @mock.patch('datoso.actions.processor.Dat', new_callable=MockDatDB)
    def test_process_with_factory(self, mock_dat_constructor):
        mock_factory = mock.Mock(return_value=MockDatFile) # Factory returns the CLASS
        action = LoadDatFile(file=self.mock_file_path, _factory=mock_factory, name=self.default_name, seed=self.default_seed)

        result = action.process()

        self.assertEqual(result, "Loaded")
        mock_factory.assert_called_once_with(self.mock_file_path)
        self.assertIsInstance(action._file_dat, MockDatFile)
        action._file_dat.load.assert_called_once()
        self.assertIsInstance(action._database_dat, MockDatDB)
        action._database_dat.load.assert_called_once()


class TestDeleteOldAction(unittest.TestCase):
    def setUp(self):
        self.mock_file_path_obj = Path("local/file.dat")
        self.action_folder = "test_output/dats" # Use a local path for testing
        self.file_dat = MockDatFile(file=self.mock_file_path_obj, name="file.dat", path="system/game", date="2023-01-15", seed="del_seed")
        self.db_dat_path_str = str(Path(self.action_folder) / "system/game/file.dat")
        self.db_dat = MockDatDB(name="file.dat", new_file=self.db_dat_path_str, date="2023-01-01", enabled=True, seed="del_seed")

    def _create_action(self, file_dat_override=None, db_dat_override=None, folder=None, current_file_path=None):
        # Ensure seed is passed to the action constructor if it's expected by Process base or action itself
        action_seed = (file_dat_override or self.file_dat).seed
        action = DeleteOld(file=current_file_path or self.mock_file_path_obj,
                           folder=folder if folder is not None else self.action_folder,
                           name=(file_dat_override or self.file_dat).name, # Pass name and seed
                           seed=action_seed)
        action._file_dat = file_dat_override if file_dat_override is not None else self.file_dat
        action._database_dat = db_dat_override if db_dat_override is not None else self.db_dat
        return action

    @mock.patch('datoso.actions.processor.compare_dates')
    def test_process_newer_found_stops(self, mock_compare_dates):
        mock_compare_dates.return_value = True
        action = self._create_action()
        result = action.process()
        self.assertEqual(result, "No Action Taken, Newer Found")
        self.assertTrue(action.stop)
        mock_compare_dates.assert_called_once_with(self.db_dat.date, self.file_dat.date)

    @mock.patch('datoso.actions.processor.compare_dates', return_value=False)
    def test_process_no_new_file_in_db(self, mock_compare_dates):
        self.db_dat.new_file = None
        action = self._create_action()
        result = action.process()
        self.assertEqual(result, "New")
        self.assertFalse(action.stop)

    @mock.patch('datoso.actions.processor.compare_dates', return_value=False)
    @mock.patch('datoso.configuration.config.getboolean', return_value=False)
    @mock.patch('datoso.helpers.file_utils.remove_path')
    def test_process_exists_same_file_date_no_overwrite_enabled(self, mock_remove_path, mock_getboolean, mock_compare_dates):
        self.file_dat.date = self.db_dat.date
        action = self._create_action()
        result = action.process()
        self.assertEqual(result, "Exists")
        self.assertFalse(action.stop)
        mock_remove_path.assert_not_called()
        mock_getboolean.assert_called_once_with('PROCESS', 'Overwrite', fallback=False)

    @mock.patch('datoso.actions.processor.compare_dates', return_value=False)
    @mock.patch('datoso.helpers.file_utils.remove_path') # Mock remove_path
    @mock.patch('pathlib.Path.mkdir') # Mock mkdir
    def test_process_dat_disabled(self, mock_mkdir, mock_remove_path, mock_compare_dates):
        self.db_dat.enabled = False
        action = self._create_action()
        result = action.process()
        self.assertEqual(result, "Disabled")
        self.assertTrue(action.stop)
        self.assertIsNone(action._database_dat.new_file)
        mock_remove_path.assert_called_once_with(Path(self.db_dat_path_str), remove_empty_parent=True)
        action._database_dat.save.assert_called_once()
        action._database_dat.flush.assert_called_once()

    @mock.patch('datoso.actions.processor.compare_dates', return_value=False)
    @mock.patch('datoso.helpers.file_utils.remove_path') # Mock remove_path
    @mock.patch('pathlib.Path.mkdir') # Mock mkdir
    def test_process_successful_delete(self, mock_mkdir, mock_remove_path, mock_compare_dates):
        self.file_dat.date = "2023-01-16"
        action = self._create_action()
        result = action.process()
        self.assertEqual(result, "Deleted")
        self.assertFalse(action.stop)
        mock_remove_path.assert_called_once_with(Path(self.db_dat_path_str), remove_empty_parent=True)

    @mock.patch('datoso.actions.processor.compare_dates', side_effect=ValueError("Date parse error"))
    @mock.patch.object(datoso_logger, 'exception')
    @mock.patch('pathlib.Path.mkdir')
    def test_process_compare_dates_value_error(self, mock_mkdir, mock_logger_exception, mock_compare_dates):
        action = self._create_action()
        result = action.process()
        self.assertEqual(result, "Error") # Should return Error if compare_dates fails
        mock_logger_exception.assert_called_once()

    def test_destination_absolute_path_in_dat(self):
        self.file_dat.path = "/absolute/path"
        # Ensure file_dat.file.name is set for the logic that uses it
        self.file_dat.file = Path(self.file_dat.path) / self.file_dat.name
        action = self._create_action(folder="ignored_folder")
        dest = action.destination()
        self.assertEqual(dest, Path("/absolute/path"))


    def test_destination_with_folder_attribute(self):
        self.file_dat.path = "relative/subpath"
        self.file_dat.file = Path(self.file_dat.path) / self.file_dat.name
        action = self._create_action(folder="/custom/output")
        dest = action.destination()
        self.assertEqual(dest, Path("/custom/output/relative/subpath/" + self.file_dat.name))

    def test_destination_no_folder_attribute_relative_path(self):
        self.file_dat.path = "relative/subpath"
        # Action is created with folder=None
        action = self._create_action(folder=None)
        # Explicitly set self.folder to None on the instance if _create_action doesn't handle it perfectly
        action.folder = None
        dest = action.destination()
        self.assertIsNone(dest)


    @mock.patch('datoso.actions.processor.get_ext', return_value='.zip')
    def test_destination_non_dat_xml_extension(self, mock_get_ext):
        self.file_dat.file = Path("archive.zip") # file_dat.file provides the extension
        self.file_dat.name = "archive" # name is used for constructing output if not .dat/.xml
        action = self._create_action(folder="/output")
        dest = action.destination()
        # Expected: /output/system/game/archive (uses file_dat.name)
        self.assertEqual(dest, Path("/output") / self.file_dat.path / self.file_dat.name)
        mock_get_ext.assert_called_once_with(self.file_dat.file)


class TestCopyAction(unittest.TestCase):
    def setUp(self):
        self.source_file_path = Path("source/downloads/new_file.dat")
        self.action_folder = "test_output/dats_copied" # Use a local path
        self.file_dat = MockDatFile(file=self.source_file_path, name="new_file.dat", path="system/game", date="2023-01-15", seed="copy_seed")
        self.db_dat_current_path_str = str(Path(self.action_folder) / "system/game/old_file.dat")
        self.db_dat = MockDatDB(name="old_file.dat", new_file=self.db_dat_current_path_str, date="2023-01-01", enabled=True, seed="copy_seed")
        self.expected_destination = Path(self.action_folder) / self.file_dat.path / self.file_dat.name

    def _create_action(self, file_dat_override=None, db_dat_override=None, folder=None, current_file_path=None):
        action_seed = (file_dat_override or self.file_dat).seed
        action = Copy(file=current_file_path or self.source_file_path,
                      folder=folder if folder is not None else self.action_folder,
                      name=(file_dat_override or self.file_dat).name,
                      seed=action_seed)
        action._file_dat = file_dat_override if file_dat_override is not None else self.file_dat
        action._database_dat = db_dat_override if db_dat_override is not None else self.db_dat
        return action

    @mock.patch('datoso.actions.processor.copy_path')
    @mock.patch('pathlib.Path.mkdir')
    def test_process_no_db_dat(self, mock_mkdir, mock_copy_path):
        action = self._create_action(db_dat_override=None)
        result = action.process()
        self.assertEqual(result, "Copied")
        mock_copy_path.assert_called_once_with(self.source_file_path, self.expected_destination)

    @mock.patch('datoso.actions.processor.copy_path')
    @mock.patch('pathlib.Path.mkdir')
    def test_process_dat_disabled(self, mock_mkdir, mock_copy_path):
        self.db_dat.enabled = False
        action = self._create_action()
        result = action.process()
        self.assertEqual(result, "Ignored")
        self.assertIsNone(action.file_dat.new_file) # Check instance attr directly
        mock_copy_path.assert_not_called()

    @mock.patch('datoso.actions.processor.compare_dates', return_value=True)
    @mock.patch('datoso.actions.processor.copy_path')
    @mock.patch('pathlib.Path.mkdir')
    def test_process_newer_in_db_no_action(self, mock_mkdir, mock_copy_path, mock_compare_dates):
        action = self._create_action()
        # self.assertTrue(action.database_data.get('date')) # These might fail if to_dict is too strict
        # self.assertTrue(action.file_data.get('date'))
        result = action.process()
        self.assertEqual(result, "No Action Taken, Newer Found")
        mock_copy_path.assert_not_called()
        mock_compare_dates.assert_called_once_with(self.db_dat.date, self.file_dat.date)

    @mock.patch('datoso.actions.processor.compare_dates', return_value=False)
    @mock.patch('datoso.configuration.config.getboolean', return_value=False)
    @mock.patch('pathlib.Path.exists', return_value=True)
    @mock.patch('datoso.helpers.file_utils.copy_path')
    @mock.patch('pathlib.Path.mkdir')
    def test_process_exists_no_overwrite(self, mock_mkdir, mock_copy_path, mock_path_exists, mock_getboolean, mock_compare_dates):
        self.db_dat.new_file = str(self.expected_destination)
        action = self._create_action()
        result = action.process()
        self.assertEqual(result, "Exists")
        self.assertTrue(action.stop)
        mock_copy_path.assert_not_called()
        mock_getboolean.assert_called_once_with('PROCESS', 'Overwrite', fallback=False)

    @mock.patch('datoso.actions.processor.compare_dates', return_value=False)
    @mock.patch('datoso.actions.processor.copy_path')
    @mock.patch('pathlib.Path.mkdir')
    def test_process_created(self, mock_mkdir, mock_copy_path, mock_compare_dates):
        self.db_dat.new_file = None
        action = self._create_action()
        result = action.process()
        self.assertEqual(result, "Created")
        mock_copy_path.assert_called_once_with(self.source_file_path, self.expected_destination)
        self.assertEqual(str(action.database_dat.new_file), str(self.expected_destination))

    @mock.patch('datoso.actions.processor.compare_dates', return_value=False)
    @mock.patch('datoso.actions.processor.copy_path')
    @mock.patch('pathlib.Path.mkdir')
    def test_process_updated_different_path(self, mock_mkdir, mock_copy_path, mock_compare_dates):
        self.db_dat.new_file = str(Path(self.action_folder) / "system/game/very_old_file.dat" )
        action = self._create_action()
        result = action.process()
        self.assertEqual(result, "Updated")
        mock_copy_path.assert_called_once_with(self.source_file_path, self.expected_destination)
        self.assertEqual(str(action.database_dat.new_file), str(self.expected_destination))

    @mock.patch('datoso.actions.processor.compare_dates', return_value=False)
    @mock.patch('datoso.configuration.config.getboolean', return_value=True)
    @mock.patch('pathlib.Path.exists', return_value=True)
    @mock.patch('datoso.actions.processor.copy_path')
    @mock.patch('pathlib.Path.mkdir')
    def test_process_overwritten(self, mock_mkdir, mock_copy_path, mock_path_exists, mock_getboolean, mock_compare_dates):
        self.db_dat.new_file = str(self.expected_destination)
        action = self._create_action()
        result = action.process()
        self.assertEqual(result, "Overwritten")
        mock_copy_path.assert_called_once_with(self.source_file_path, self.expected_destination)
        self.assertEqual(str(action.database_dat.new_file), str(self.expected_destination))
        mock_getboolean.assert_any_call('PROCESS', 'Overwrite', fallback=False)

    @mock.patch('datoso.actions.processor.compare_dates', return_value=False)
    @mock.patch('pathlib.Path.exists', return_value=False)
    @mock.patch('datoso.actions.processor.copy_path')
    @mock.patch('pathlib.Path.mkdir')
    def test_process_updated_path_same_dest_not_exists(self, mock_mkdir, mock_copy_path, mock_path_exists, mock_compare_dates):
        self.db_dat.new_file = str(self.expected_destination)
        action = self._create_action()
        result = action.process()
        self.assertEqual(result, "Updated")
        mock_copy_path.assert_called_once_with(self.source_file_path, self.expected_destination)
        self.assertEqual(str(action.database_dat.new_file), str(self.expected_destination))

    def test_destination_logic(self):
        action = self._create_action()
        self.assertEqual(action.destination(), self.expected_destination)
        action.file_dat.path = "/abs/path" # file_dat.path is string
        action.file_dat.file = Path(action.file_dat.path) / action.file_dat.name # Update file_dat.file to match
        self.assertEqual(action.destination(), Path("/abs/path"))

        action.file_dat.path = "system/game" # Reset
        action.file_dat.file = self.source_file_path # Reset

        with mock.patch('datoso.helpers.file_utils.get_ext', return_value='.zip'):
            action.file_dat.file = Path("source/downloads/new_archive.zip")
            action.file_dat.name = "new_archive" # Name without extension
            self.assertEqual(action.destination(), Path(self.action_folder) / "system/game" / "new_archive")


class TestSaveToDatabaseAction(unittest.TestCase):
    def setUp(self):
        self.default_seed = "save_db_seed"
        self.file_dat_data = {"name": "file_dat_name", "version": "1.1", "date": "2023-01-15", "seed": self.default_seed}
        self.db_dat_data = {"name": "db_dat_name", "system": "NES", "new_file": "/path/to/current.dat", "seed": self.default_seed}
        self.mock_file_dat = MockDatFile(**self.file_dat_data)
        self.mock_db_dat_old = MockDatDB(**self.db_dat_data)

    @mock.patch('datoso.actions.processor.Dat')
    def test_process_saves_merged_data(self, mock_dat_constructor):
        mock_instance = MockDatDB(name="db_dat_name", system="NES", new_file="/path/to/current.dat", seed=self.default_seed)
        mock_dat_constructor.return_value = mock_instance
        action = SaveToDatabase(name="TestSave", seed=self.default_seed) # Actions also take name/seed
        action._file_dat = self.mock_file_dat
        action._database_dat = self.mock_db_dat_old

        # This is the instance that Dat(**merged_data) should produce
        expected_instance = mock_dat_constructor.return_value

        result = action.process()
        self.assertEqual(result, "Saved")

        # Check that Dat (our MockDatDB) was called with merged data
        # file_data should take precedence
        expected_merged_data = {**self.db_dat_data, **self.file_dat_data}
        # Ensure 'name' and 'seed' for constructor come from the merged data, with file_dat taking precedence
        expected_merged_data['name'] = self.file_dat_data['name']
        expected_merged_data['seed'] = self.file_dat_data['seed']

        mock_dat_constructor.assert_called_once()
        constructor_args = mock_dat_constructor.call_args[1]
        for key, value in expected_merged_data.items():
            self.assertEqual(constructor_args.get(key), value, msg=f"Mismatch for key {key}")

        expected_instance.save.assert_called_once()
        expected_instance.flush.assert_called_once()
        self.assertIs(action._database_dat, expected_instance)


class TestMarkMiasAction(unittest.TestCase):
    def setUp(self):
        self.default_seed = "mark_mias_seed"
        self.db_dat_with_file = MockDatDB(new_file="/path/to/datfile.dat", name="DatWithFile", seed=self.default_seed)
        self.db_dat_no_file = MockDatDB(new_file=None, name="DatNoFile", seed=self.default_seed)

    @mock.patch('datoso.configuration.config.getboolean', return_value=False)
    @mock.patch('datoso.actions.processor.mark_mias') # Patch where mark_mias is looked up
    def test_process_skipped_if_config_false(self, mock_mark_mias_func, mock_getboolean):
        action = MarkMias(name="TestMIA", seed=self.default_seed)
        action._database_dat = self.db_dat_with_file
        result = action.process()
        self.assertEqual(result, "Skipped")
        mock_getboolean.assert_called_once_with('PROCESS', 'ProcessMissingInAction', fallback=False)
        mock_mark_mias_func.assert_not_called()

    @mock.patch('datoso.configuration.config.getboolean', return_value=True)
    @mock.patch('datoso.actions.processor.mark_mias') # Patch where mark_mias is looked up
    def test_process_calls_mark_mias_if_config_true(self, mock_mark_mias_func, mock_getboolean):
        action = MarkMias(name="TestMIA", seed=self.default_seed)
        action._database_dat = self.db_dat_with_file
        result = action.process()
        self.assertEqual(result, "Marked")
        mock_getboolean.assert_called_once_with('PROCESS', 'ProcessMissingInAction', fallback=False)
        mock_mark_mias_func.assert_called_once_with(dat_file=self.db_dat_with_file.new_file)

    @mock.patch('datoso.configuration.config.getboolean', return_value=True)
    @mock.patch('datoso.actions.processor.mark_mias') # Patch where mark_mias is looked up
    def test_process_handles_db_dat_new_file_none(self, mock_mark_mias_func, mock_getboolean):
        action = MarkMias(name="TestMIA", seed=self.default_seed)
        action._database_dat = self.db_dat_no_file
        result = action.process()
        self.assertEqual(result, "Marked")
        mock_mark_mias_func.assert_called_once_with(dat_file=None)


@mock.patch('datoso.actions.processor.Dedupe', spec=DedupeClass)
class TestAutoMergeAction(unittest.TestCase):
    def setUp(self):
        self.default_seed = "automerge_seed"
    def test_process_no_automerge_attr(self, mock_Dedupe):
        action = AutoMerge(name="TestAM", seed=self.default_seed)
        action._database_dat = MockDatDB(name="DatNoAM", seed=self.default_seed)
        if hasattr(action._database_dat, 'automerge'): # Ensure attr is missing for this specific test
            delattr(action._database_dat, 'automerge')
        result = action.process()
        self.assertEqual(result, "Skipped")
        mock_Dedupe.assert_not_called()

    def test_process_automerge_false(self, mock_Dedupe):
        action = AutoMerge(name="TestAM", seed=self.default_seed)
        action._database_dat = MockDatDB(automerge=False, name="DatAMFalse", seed=self.default_seed)
        result = action.process()
        self.assertEqual(result, "Skipped")
        mock_Dedupe.assert_not_called()

    def test_process_automerge_true_dedupe_returns_zero(self, mock_Dedupe):
        action = AutoMerge(name="TestAM", seed=self.default_seed)
        action._database_dat = MockDatDB(automerge=True, name="DatAMTrue", seed=self.default_seed)
        mock_dedupe_instance = mock_Dedupe.return_value
        mock_dedupe_instance.dedupe.return_value = 0

        result = action.process()
        self.assertEqual(result, "Skipped")
        mock_Dedupe.assert_called_once_with(action._database_dat)
        mock_dedupe_instance.dedupe.assert_called_once()
        mock_dedupe_instance.save.assert_not_called()

    def test_process_automerge_true_dedupe_returns_gt_zero(self, mock_Dedupe):
        action = AutoMerge(name="TestAM", seed=self.default_seed)
        action._database_dat = MockDatDB(automerge=True, name="TestDATMerge", seed=self.default_seed)
        mock_dedupe_instance = mock_Dedupe.return_value
        mock_dedupe_instance.dedupe.return_value = 5

        result = action.process()
        self.assertEqual(result, "Automerged")
        mock_Dedupe.assert_called_once_with(action._database_dat)
        mock_dedupe_instance.dedupe.assert_called_once()
        mock_dedupe_instance.save.assert_called_once()


@mock.patch('datoso.actions.processor.Dedupe', spec=DedupeClass)
class TestDeduplicateAction(unittest.TestCase):
    def setUp(self):
        self.default_seed = "dedup_seed"
    def test_process_no_parent_attr(self, mock_Dedupe):
        action = Deduplicate(name="TestDedup", seed=self.default_seed)
        action._database_dat = MockDatDB(name="ChildDatNoParentAttr", seed=self.default_seed)
        if hasattr(action._database_dat, 'parent'):
            delattr(action._database_dat, 'parent')
        result = action.process()
        self.assertEqual(result, "Skipped")
        mock_Dedupe.assert_not_called()

    def test_process_parent_is_none(self, mock_Dedupe):
        action = Deduplicate(name="TestDedup", seed=self.default_seed)
        action._database_dat = MockDatDB(name="ChildDatParentNone", parent=None, seed=self.default_seed)
        result = action.process()
        self.assertEqual(result, "Skipped")
        mock_Dedupe.assert_not_called()

    def test_process_with_parent_dedupe_returns_zero(self, mock_Dedupe):
        action = Deduplicate(name="TestDedup", seed=self.default_seed)
        parent_dat = MockDatDB(name="ParentDat", seed="parent_seed")
        action._database_dat = MockDatDB(name="ChildDatWithParent", parent=parent_dat, seed=self.default_seed)

        mock_dedupe_instance = mock_Dedupe.return_value
        mock_dedupe_instance.dedupe.return_value = 0

        result = action.process()
        self.assertEqual(result, "Skipped")
        mock_Dedupe.assert_called_once_with(action._database_dat, parent_dat)
        mock_dedupe_instance.dedupe.assert_called_once()
        mock_dedupe_instance.save.assert_not_called()

    def test_process_with_parent_dedupe_returns_gt_zero(self, mock_Dedupe):
        action = Deduplicate(name="TestDedup", seed=self.default_seed)
        parent_dat = MockDatDB(name="ParentDat", seed="parent_seed")
        action._database_dat = MockDatDB(name="ChildDatToMerge", parent=parent_dat, seed=self.default_seed)

        mock_dedupe_instance = mock_Dedupe.return_value
        mock_dedupe_instance.dedupe.return_value = 3

        result = action.process()
        self.assertEqual(result, "Deduped")
        mock_Dedupe.assert_called_once_with(action._database_dat, parent_dat)
        mock_dedupe_instance.dedupe.assert_called_once()
        mock_dedupe_instance.save.assert_called_once()

# The duplicate classes were here. Removing them by ending the file contents above.
if __name__ == '__main__':
    unittest.main()
