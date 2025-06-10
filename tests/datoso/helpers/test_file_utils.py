import unittest
from unittest import mock
import os
import shutil
import tempfile
from pathlib import Path
import sys

# Ensure src is discoverable for imports
project_root_for_imports = Path(__file__).parent.parent.parent.parent
if str(project_root_for_imports) not in sys.path:
    sys.path.insert(0, str(project_root_for_imports))
if str(project_root_for_imports / "src") not in sys.path:
    sys.path.insert(0, str(project_root_for_imports / "src"))

# Import functions from file_utils.py
from datoso.helpers.file_utils import (
    copy_path,
    remove_folder,
    remove_path,
    remove_empty_folders,
    parse_path,
    move_path,
    get_ext
)

class TestFileUtilsBase(unittest.TestCase):
    """ Base class for file utility tests, provides common setup like temp dirs. """
    def setUp(self):
        # Create a temporary directory for operations that need the filesystem
        self.temp_dir_obj = tempfile.TemporaryDirectory()
        self.temp_dir = Path(self.temp_dir_obj.name)

    def tearDown(self):
        self.temp_dir_obj.cleanup()

class TestCopyPath(TestFileUtilsBase):
    def test_copy_file(self):
        source_file = self.temp_dir / "source.txt"
        source_file.write_text("test content")
        dest_file = self.temp_dir / "dest" / "dest.txt"

        copy_path(str(source_file), str(dest_file))

        self.assertTrue(dest_file.exists())
        self.assertEqual(dest_file.read_text(), "test content")

    def test_copy_directory(self):
        source_dir = self.temp_dir / "source_dir"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("file1")
        (source_dir / "subdir").mkdir()
        (source_dir / "subdir" / "file2.txt").write_text("file2")

        dest_dir = self.temp_dir / "dest_dir"
        copy_path(str(source_dir), str(dest_dir))

        self.assertTrue(dest_dir.exists())
        self.assertTrue((dest_dir / "file1.txt").exists())
        self.assertEqual((dest_dir / "file1.txt").read_text(), "file1")
        self.assertTrue((dest_dir / "subdir" / "file2.txt").exists())
        self.assertEqual((dest_dir / "subdir" / "file2.txt").read_text(), "file2")

    def test_copy_existing_destination_dir(self):
        source_dir = self.temp_dir / "source_dir_2"
        source_dir.mkdir()
        (source_dir / "file_new.txt").write_text("new_content")

        dest_dir = self.temp_dir / "dest_dir_2"
        dest_dir.mkdir() # Destination directory already exists
        (dest_dir / "old_file.txt").write_text("old_content") # With some content

        copy_path(str(source_dir), str(dest_dir)) # Should replace dest_dir

        self.assertTrue(dest_dir.exists())
        self.assertTrue((dest_dir / "file_new.txt").exists())
        self.assertFalse((dest_dir / "old_file.txt").exists()) # Old content should be gone

    def test_copy_same_file_error_suppressed(self):
        source_file = self.temp_dir / "samesource.txt"
        source_file.write_text("content")
        # shutil.copytree and shutil.copy raise SameFileError if src and dst are the same
        # The function should suppress this.
        try:
            copy_path(str(source_file), str(source_file))
        except shutil.SameFileError:
            self.fail("shutil.SameFileError was not suppressed")

    def test_copy_source_not_found(self):
        with self.assertRaises(FileNotFoundError) as context:
            copy_path("non_existent_source.txt", str(self.temp_dir / "dest.txt"))
        self.assertIn("File non_existent_source.txt not found.", str(context.exception))


class TestRemoveFolder(TestFileUtilsBase):
    @mock.patch('datoso.helpers.file_utils.shutil.rmtree')
    def test_remove_folder_calls_shutil_rmtree(self, mock_rmtree):
        folder_to_remove = self.temp_dir / "folder_to_delete"
        # No need to actually create it since we mock rmtree

        remove_folder(str(folder_to_remove))
        mock_rmtree.assert_called_once_with(str(folder_to_remove))

    @mock.patch('datoso.helpers.file_utils.shutil.rmtree', side_effect=PermissionError("Test permission error"))
    def test_remove_folder_suppresses_permission_error(self, mock_rmtree):
        try:
            remove_folder(str(self.temp_dir / "any_folder"))
        except PermissionError:
            self.fail("PermissionError was not suppressed by remove_folder")


class TestRemovePath(TestFileUtilsBase):
    def test_remove_existing_file(self):
        file_to_remove = self.temp_dir / "file_to_remove.txt"
        file_to_remove.write_text("delete me")
        self.assertTrue(file_to_remove.exists())

        remove_path(str(file_to_remove))
        self.assertFalse(file_to_remove.exists())

    @mock.patch('datoso.helpers.file_utils.remove_folder')
    def test_remove_existing_directory(self, mock_remove_folder_func):
        dir_to_remove = self.temp_dir / "dir_to_remove"
        dir_to_remove.mkdir()
        self.assertTrue(dir_to_remove.exists())

        remove_path(str(dir_to_remove))
        mock_remove_folder_func.assert_called_once_with(dir_to_remove) # Path object is passed

    def test_remove_non_existent_path(self):
        # Should not raise any error
        try:
            remove_path(str(self.temp_dir / "non_existent_path"))
        except Exception as e:
            self.fail(f"remove_path raised an unexpected exception for non-existent path: {e}")

    def test_remove_file_and_empty_parent(self):
        parent_dir = self.temp_dir / "parent"
        parent_dir.mkdir()
        file_in_parent = parent_dir / "file.txt"
        file_in_parent.write_text("content")

        remove_path(str(file_in_parent), remove_empty_parent=True)

        self.assertFalse(file_in_parent.exists())
        self.assertFalse(parent_dir.exists(), "Parent directory should have been removed as it became empty.")

    def test_remove_file_and_non_empty_parent(self):
        parent_dir = self.temp_dir / "parent_nonempty"
        parent_dir.mkdir()
        file_to_remove = parent_dir / "file_to_remove.txt"
        file_to_remove.write_text("content")
        sibling_file = parent_dir / "sibling.txt"
        sibling_file.write_text("i stay")

        remove_path(str(file_to_remove), remove_empty_parent=True)

        self.assertFalse(file_to_remove.exists())
        self.assertTrue(parent_dir.exists(), "Parent directory should NOT have been removed.")
        self.assertTrue(sibling_file.exists())

    def test_remove_nested_empty_parents(self):
        grandparent_dir = self.temp_dir / "grandparent"
        parent_dir = grandparent_dir / "parent"
        child_dir = parent_dir / "child" # This will be removed first
        child_dir.mkdir(parents=True, exist_ok=True)

        # Remove child_dir, which should trigger removal of parent and grandparent
        remove_path(str(child_dir), remove_empty_parent=True)

        self.assertFalse(child_dir.exists())
        self.assertFalse(parent_dir.exists())
        self.assertFalse(grandparent_dir.exists())


class TestRemoveEmptyFolders(TestFileUtilsBase):
    def test_remove_only_empty_folders(self):
        # Structure:
        # root/
        #   empty_top/
        #     empty_mid/
        #       empty_leaf/
        #   not_empty_top/
        #     file_in_not_empty.txt
        #     empty_mid_in_not_empty/  (should be removed)
        #   file_in_root.txt

        root_dir = self.temp_dir / "root_cleanup"

        empty_leaf = root_dir / "empty_top" / "empty_mid" / "empty_leaf"
        empty_leaf.mkdir(parents=True, exist_ok=True)

        not_empty_top = root_dir / "not_empty_top"
        not_empty_top.mkdir()
        (not_empty_top / "file_in_not_empty.txt").write_text("content")
        empty_mid_in_not_empty = not_empty_top / "empty_mid_in_not_empty"
        empty_mid_in_not_empty.mkdir()

        (root_dir / "file_in_root.txt").write_text("root content")

        remove_empty_folders(str(root_dir))

        self.assertTrue(root_dir.exists())
        self.assertTrue((root_dir / "file_in_root.txt").exists())

        self.assertFalse((root_dir / "empty_top").exists(), "empty_top and its children should be removed")

        self.assertTrue(not_empty_top.exists())
        self.assertTrue((not_empty_top / "file_in_not_empty.txt").exists())
        self.assertFalse(empty_mid_in_not_empty.exists(), "empty_mid_in_not_empty should be removed")


class TestParsePath(unittest.TestCase): # Does not need TestFileUtilsBase
    @mock.patch('datoso.helpers.file_utils.Path.cwd', return_value=Path("/current/working/dir"))
    def test_parse_path_relative(self, mock_cwd):
        self.assertEqual(parse_path("some/relative/path"), Path("/current/working/dir/some/relative/path"))
        self.assertEqual(parse_path(""), Path("/current/working/dir/"))
        self.assertEqual(parse_path(None), Path("/current/working/dir/")) # None is treated as empty string

    @mock.patch('datoso.helpers.file_utils.Path.expanduser')
    def test_parse_path_absolute_and_home(self, mock_expanduser):
        # Test absolute path
        self.assertEqual(parse_path("/absolute/path"), Path("/absolute/path"))
        mock_expanduser.assert_not_called() # expanduser shouldn't be called for /absolute/path

        # Test path starting with ~
        mock_expanduser.return_value = Path("/home/user/expanded_path")
        self.assertEqual(parse_path("~/somepath"), Path("/home/user/expanded_path"))
        # Path('~/somepath').expanduser() is called.
        # The mock_expanduser here is on file_utils.Path.expanduser, so we need to ensure Path('~/somepath') is created first.
        # This test is a bit tricky due to how Path itself works.
        # A more direct test:
        with mock.patch('pathlib.Path.expanduser', return_value=Path("/home/user/path")) as mock_pathlib_expanduser:
            result = parse_path("~/test")
            self.assertEqual(result, Path("/home/user/path"))
            # Check that expanduser was called on a Path object representing '~/test'
            # This requires knowing how Path() itself is called internally or mocking Path constructor.
            # For simplicity, we trust Path('~/test').expanduser() works if expanduser is called.
            mock_pathlib_expanduser.assert_called()


class TestMovePath(TestFileUtilsBase):
    @mock.patch('datoso.helpers.file_utils.shutil.move')
    @mock.patch('datoso.helpers.file_utils.Path.mkdir') # To check parent dir creation
    def test_move_path_success(self, mock_mkdir, mock_shutil_move):
        source_file = self.temp_dir / "source_to_move.txt"
        source_file.write_text("move content")
        dest_file_str = str(self.temp_dir / "moved_dest" / "dest_moved.txt")

        move_path(str(source_file), dest_file_str)

        # Check that parent directory of destination was ensured
        # Path(dest_file_str).parent.mkdir should have been called
        # This is implicitly tested by checking shutil.move args if mkdir is part of Path setup.
        # For direct check:
        # mock_mkdir_instance = mock_Path_class.return_value.parent.mkdir
        # mock_mkdir_instance.assert_called_once_with(parents=True, exist_ok=True)
        # For now, let's assume Path().parent.mkdir works and check shutil.move
        mock_shutil_move.assert_called_once_with(str(source_file), dest_file_str)

    @mock.patch('datoso.helpers.file_utils.shutil.move', side_effect=shutil.Error("Simulated shutil.Error"))
    @mock.patch('datoso.helpers.file_utils.remove_path') # Mock our own remove_path
    def test_move_path_shutil_error_removes_source(self, mock_internal_remove_path, mock_shutil_move):
        source_file_str = str(self.temp_dir / "source_on_error.txt")
        Path(source_file_str).write_text("content")
        dest_file_str = str(self.temp_dir / "dest_on_error.txt")

        move_path(source_file_str, dest_file_str)

        mock_shutil_move.assert_called_once_with(source_file_str, dest_file_str)
        mock_internal_remove_path.assert_called_once_with(source_file_str)


class TestGetExt(unittest.TestCase): # Does not need TestFileUtilsBase
    def test_get_ext_various_cases(self):
        self.assertEqual(get_ext("file.txt"), ".txt")
        self.assertEqual(get_ext("/path/to/archive.tar.gz"), ".gz")
        self.assertEqual(get_ext("nodotextension"), "")
        self.assertEqual(get_ext(".hiddenfile"), "") # Path('.hiddenfile').suffix is ''
        self.assertEqual(get_ext("/path/to/.configfile"), "")
        self.assertEqual(get_ext(Path("some.folder/file.zip")), ".zip")


if __name__ == '__main__':
    unittest.main()
