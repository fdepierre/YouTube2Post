import os
import tempfile
import unittest

from modules import directory_manager as dm
from modules.directory_manager import DirectoryManager


class TestDirectoryManager(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.TemporaryDirectory()
        self.tmp_dir = os.path.join(self.base.name, 'tmp')
        self.work_dir = os.path.join(self.base.name, 'work')
        self.manager = DirectoryManager(tmp_directory=self.tmp_dir, work_directory=self.work_dir)

    def tearDown(self):
        self.base.cleanup()

    def test_create_directories(self):
        self.assertTrue(os.path.isdir(self.tmp_dir))
        self.assertTrue(os.path.isdir(self.work_dir))

    def test_clear_tmp_directory(self):
        dummy_file = os.path.join(self.tmp_dir, 'dummy.txt')
        with open(dummy_file, 'w', encoding='utf-8') as f:
            f.write('dummy content')
        self.manager.clear_tmp_directory()
        self.assertFalse(os.path.exists(dummy_file))


class TestDangerousTmpDirectory(unittest.TestCase):
    def test_refused(self):
        with tempfile.TemporaryDirectory() as base:
            cases = [
                (base, base),                                    # same as the work directory
                (os.path.expanduser('~'), os.path.join(base, 'w')),
                (os.path.abspath(os.sep), os.path.join(base, 'w')),
                (dm._PROJECT_DIR, os.path.join(base, 'w')),       # would delete yt2post.py
            ]
            for tmp, work in cases:
                with self.assertRaises(ValueError, msg=tmp):
                    DirectoryManager(tmp_directory=tmp, work_directory=work)


if __name__ == '__main__':
    unittest.main()
