import unittest
import os
from unittest import mock
from pathlib import Path
import configparser
import sys

# Attempt to import from src. This might require PYTHONPATH to be set correctly
# for the test execution environment. If /app is the project root, /app/src should be
# on PYTHONPATH.
try:
    from src.datoso.configuration.configuration import Config, get_seed_name, config_paths, XDG_CONFIG_HOME, HOME, ROOT_FOLDER
except ModuleNotFoundError:
    # Fallback for environments where src is not directly in PYTHONPATH
    # This assumes the script is run from a context where 'src' is a sibling of 'tests'
    # or that PYTHONPATH is otherwise managed.
    # For the agent's environment, we might need to adjust sys.path if direct import fails.
    # Adding project root to path to facilitate src.datoso... imports
    project_root = Path(__file__).parent.parent.parent.parent # Assuming tests/datoso/configuration/test_configuration.py
    sys.path.insert(0, str(project_root))
    sys.path.insert(0, str(project_root / "src")) # Ensure src is on the path
    from datoso.configuration.configuration import Config, get_seed_name, config_paths, XDG_CONFIG_HOME, HOME, ROOT_FOLDER


class TestConfiguration(unittest.TestCase):

    def setUp(self):
        self.config = Config(allow_no_value=True)
        self.test_ini_content = """
[Section1]
Key1 = Value1
KeyTrue = True
KeyYes = yes
KeyOne = 1
KeyFalse = False
KeyNo = no
KeyZero = 0
KeyMixedCase = VaLuE

[Section2]
AnotherKey = AnotherValue
"""
        self.config.read_string(self.test_ini_content)
        # Clear relevant environment variables before each test
        self.env_vars_to_clear = [
            "Section1.KEY1", "Section1.NEWKEY", "Section1.KEYTRUE", "Section1.KEYFALSE",
            "SectionBoolean.ENVTRUE", "SectionBoolean.ENVYES", "SectionBoolean.ENVONE",
            "SectionBoolean.ENVFALSE", "SectionBoolean.ENVNO", "SectionBoolean.ENVZERO",
            "SectionBoolean.ENVINVALID"
        ]
        for var in self.env_vars_to_clear:
            if var in os.environ:
                del os.environ[var]


    def test_get_from_ini(self):
        self.assertEqual(self.config.get("Section1", "Key1"), "Value1")
        self.assertEqual(self.config.get("Section1", "KeyMixedCase"), "VaLuE") # Relies on optionxform = str
        self.assertEqual(self.config.get("Section2", "AnotherKey"), "AnotherValue")

    def test_get_missing_option_returns_none(self):
        self.assertIsNone(self.config.get("Section1", "MissingKey"))

    def test_get_missing_section_returns_none(self):
        self.assertIsNone(self.config.get("MissingSection", "Key1"))

    @mock.patch.dict(os.environ, {"Section1.KEY1": "EnvValue1"})
    def test_get_from_env(self):
        # Config object is created in setUp, os.environ mock needs to be active when .get is called
        self.assertEqual(self.config.get("Section1", "Key1"), "EnvValue1")

    @mock.patch.dict(os.environ, {"Section1.NEWKEY": "EnvNewValue"})
    def test_get_new_key_from_env(self):
        self.assertEqual(self.config.get("Section1", "NewKey"), "EnvNewValue")
        # Ensure it doesn't affect underlying parser if not present in ini
        # The Config.get() method returns None if the key is not in os.environ and not in the INI file.
        # It does not raise NoOptionError itself.
        # To check the underlying parser, we'd need a way to call super().get() on the instance,
        # which is not straightforward from the test.
        # Let's verify that the key is not added to the INI structure.
        self.assertNotIn("NewKey", self.config["Section1"])


    @mock.patch.dict(os.environ, {"Section1.KEY1": "EnvValueOverridesIni"})
    def test_env_overrides_ini(self):
        # Ensure INI value is what we expect first by creating a fresh config
        fresh_config = Config()
        fresh_config.read_string(self.test_ini_content)
        self.assertEqual(super(Config, fresh_config).get("Section1", "Key1"), "Value1")
        # Then test that get() prefers the environment variable
        self.assertEqual(self.config.get("Section1", "Key1"), "EnvValueOverridesIni")


    def test_getboolean_from_ini(self):
        self.assertTrue(self.config.getboolean("Section1", "KeyTrue"))
        self.assertTrue(self.config.getboolean("Section1", "KeyYes"))
        self.assertTrue(self.config.getboolean("Section1", "KeyOne"))
        self.assertFalse(self.config.getboolean("Section1", "KeyFalse"))
        self.assertFalse(self.config.getboolean("Section1", "KeyNo"))
        self.assertFalse(self.config.getboolean("Section1", "KeyZero"))

    def test_getboolean_custom_value_from_ini(self):
        # Test a value that might cause super().getboolean() to fail if not handled by our boolean()
        self.config.read_string("[SectionCustom]\nCustomBool = custom_true_value")
        # This test depends on how boolean() is implemented. Current Config.boolean only recognizes true/yes/1.
        # So, this should be False.
        self.assertFalse(self.config.getboolean("SectionCustom", "CustomBool"))


    def test_getboolean_missing_option_returns_none(self):
        self.assertIsNone(self.config.getboolean("Section1", "MissingKeyBool"))

    def test_getboolean_missing_section_returns_none(self):
        self.assertIsNone(self.config.getboolean("MissingSection", "KeyTrue"))

    @mock.patch.dict(os.environ, {"Section1.KEYTRUE": "false", "Section1.KEYFALSE": "true"})
    def test_getboolean_env_overrides_ini(self):
        self.assertFalse(self.config.getboolean("Section1", "KeyTrue")) # Was True in INI
        self.assertTrue(self.config.getboolean("Section1", "KeyFalse")) # Was False in INI

    @mock.patch.dict(os.environ, {
        "SectionBoolean.ENVTRUE": "True",
        "SectionBoolean.ENVYES": "yes",
        "SectionBoolean.ENVONE": "1",
        "SectionBoolean.ENVFALSE": "False",
        "SectionBoolean.ENVNO": "no",
        "SectionBoolean.ENVZERO": "0",
        "SectionBoolean.ENVINVALID": "notabool", # should be false
        "SectionBoolean.EMPTY": "" # should be false
    })
    def test_getboolean_from_env(self):
        self.assertTrue(self.config.getboolean("SectionBoolean", "EnvTrue"))
        self.assertTrue(self.config.getboolean("SectionBoolean", "EnvYes"))
        self.assertTrue(self.config.getboolean("SectionBoolean", "EnvOne"))
        self.assertFalse(self.config.getboolean("SectionBoolean", "EnvFalse"))
        self.assertFalse(self.config.getboolean("SectionBoolean", "EnvNo"))
        self.assertFalse(self.config.getboolean("SectionBoolean", "EnvZero"))
        self.assertFalse(self.config.getboolean("SectionBoolean", "EnvInvalid"))
        self.assertFalse(self.config.getboolean("SectionBoolean", "Empty"))


    def test_boolean_helper(self):
        cfg = Config() # Instance needed to call boolean method
        self.assertTrue(cfg.boolean("True"))
        self.assertTrue(cfg.boolean("yes"))
        self.assertTrue(cfg.boolean("1"))
        self.assertTrue(cfg.boolean(1))
        self.assertTrue(cfg.boolean(True))
        self.assertFalse(cfg.boolean("False"))
        self.assertFalse(cfg.boolean("no"))
        self.assertFalse(cfg.boolean("0"))
        self.assertFalse(cfg.boolean(0))
        self.assertFalse(cfg.boolean(False))
        self.assertFalse(cfg.boolean("anything_else"))
        self.assertFalse(cfg.boolean(None))
        self.assertFalse(cfg.boolean(123))
        self.assertFalse(cfg.boolean(""))


    def test_optionxform_is_set_to_str(self):
        # The global `config` object in the module has optionxform = str (or lambda s:s)
        # This test checks an instance.
        # By default, configparser.ConfigParser.optionxform is 'str.lower'.
        # The 'Config' class itself doesn't set optionxform in its __init__.
        # It is set on the global 'config' instance in the module.
        # So, a raw Config() instance will have default behavior.
        default_cfg = configparser.ConfigParser()
        self.assertEqual(default_cfg.optionxform("MixedCaseKey"), "mixedcasekey")

        # Our Config class does not override __init__ to change optionxform
        # So instances of it behave like normal ConfigParser unless optionxform is set explicitly
        my_cfg = Config()
        self.assertEqual(my_cfg.optionxform("MixedCaseKey"), "mixedcasekey") # Default behavior

        # The global 'config' object in configuration.py has it set.
        # We can't easily test the global 'config' object's optionxform directly here
        # without importing it and testing its state, which is more of an integration test.
        # For a unit test of the class, we'd check if the class's __init__ sets it. It doesn't.
        # However, the prompt implies testing the module's configuration features,
        # and `config.optionxform = lambda option: option` is a feature.
        # Let's test an instance where it's set, like the global one.
        
        self.config.optionxform = str # Replicates `lambda option: option` for this purpose
        self.config.read_string("[Section]\nMixedCaseKey = Value")
        self.assertEqual(self.config.get("Section", "MixedCaseKey"), "Value")
        # If optionxform was default (lower), "MixedCaseKey" would not be found by super().get()
        # but our get() uses the original key, so this test needs refinement.

        # Let's test the effect of optionxform on super().get()
        cfg_sensitive = Config()
        cfg_sensitive.optionxform = str # Make keys case-sensitive
        cfg_sensitive.read_string("[Section]\nMixedCaseKey = Value1")
        self.assertEqual(super(Config, cfg_sensitive).get("Section", "MixedCaseKey"), "Value1")
        with self.assertRaises(configparser.NoOptionError):
            super(Config, cfg_sensitive).get("Section", "mixedcasekey")

        cfg_insensitive = Config()
        cfg_insensitive.optionxform = str.lower # Default, make keys case-insensitive
        cfg_insensitive.read_string("[Section]\nMixedCaseKey = Value2")
        self.assertEqual(super(Config, cfg_insensitive).get("Section", "mixedcasekey"), "Value2")
        self.assertEqual(super(Config, cfg_insensitive).get("Section", "MixedCaseKey"), "Value2")


    def test_get_seed_name(self):
        self.assertEqual(get_seed_name("datoso_seed_testseed"), "testseed")
        self.assertEqual(get_seed_name("another_prefix_testseed"), "another_prefix_testseed") # No replacement
        self.assertEqual(get_seed_name("datoso_seed_"), "") # Empty seed name
        # __app_name__ is 'datoso' in the module, this test assumes it's mocked or consistent
        # For this test, we can use the imported __app_name__ if available or mock it.
        # The import `from datoso.configuration.configuration import get_seed_name` means
        # that get_seed_name uses __app_name__ from its own module scope.
        with mock.patch('datoso.configuration.configuration.__app_name__', "myapp"):
             self.assertEqual(get_seed_name("myapp_seed_another"), "another")

    def test_get_with_fallback(self):
        self.assertEqual(self.config.get("Section1", "Key1", fallback="DefaultValue"), "Value1")
        self.assertEqual(self.config.get("Section1", "MissingKey", fallback="DefaultValue"), "DefaultValue")
        self.assertIsNone(self.config.get("Section1", "MissingKey")) # Ensure None if no fallback

    @mock.patch.dict(os.environ, {"Section1.MISSINGKEY_WITH_FALLBACK": "EnvValue"})
    def test_get_with_fallback_and_env(self):
        # Env variable should take precedence over fallback
        self.assertEqual(self.config.get("Section1", "MissingKey_With_Fallback", fallback="DefaultValue"), "EnvValue")
        # If INI key exists, env var still wins, fallback ignored
        self.assertEqual(self.config.get("Section1", "Key1", fallback="DefaultValue"), "Value1") # from INI
        with mock.patch.dict(os.environ, {"Section1.KEY1": "EnvKey1"}):
            self.assertEqual(self.config.get("Section1", "Key1", fallback="DefaultValue"), "EnvKey1") # from Env


    def test_getboolean_with_fallback(self):
        # Fallback in getboolean is tricky because super().getboolean has specific fallback handling.
        # Our Config.getboolean calls self.boolean(super().get(...))
        # So, the fallback should be passed to super().get().
        self.assertTrue(self.config.getboolean("Section1", "KeyTrue", fallback="False")) # Existing, fallback ignored
        self.assertFalse(self.config.getboolean("Section1", "MissingBool", fallback="False"))
        self.assertTrue(self.config.getboolean("Section1", "MissingBool", fallback="True"))
        self.assertIsNone(self.config.getboolean("Section1", "MissingBool")) # No fallback, should be None

    @mock.patch.dict(os.environ, {"Section1.MISSINGBOOL_WITH_FALLBACK": "true"})
    def test_getboolean_with_fallback_and_env(self):
        self.assertTrue(self.config.getboolean("Section1", "MissingBool_With_Fallback", fallback="false"))


    def test_read_string_malformed_ini(self):
        malformed_ini_content = """
[SectionOnlyKey
Key1 = Value1
"""
        with self.assertRaises(configparser.ParsingError):
            self.config.read_string(malformed_ini_content)

    def test_read_file_non_existent(self):
        # ConfigParser.read() on a non-existent file should not raise error, just return empty list.
        # Create a temporary Config instance for this test to avoid affecting self.config
        temp_config = Config()
        result = temp_config.read("non_existent_file.ini")
        self.assertEqual(result, [])
        self.assertIsNone(temp_config.get("AnySection", "AnyKey"))


# class TestGlobalConfigInitialization(unittest.TestCase):
#     pass
# Commenting out TestGlobalConfigInitialization as it requires more complex setup (module reloading)
# to reliably test module-level initialization logic with mocks.
# Focus for now is on the Config class and get_seed_name function.

if __name__ == '__main__':
    # This setup allows running the test file directly, ensuring src is discoverable.
    # It's a common pattern when tests are outside the main package.
    project_root_for_runner = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(project_root_for_runner))
    sys.path.insert(0, str(project_root_for_runner / "src"))
    unittest.main()
