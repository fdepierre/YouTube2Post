import unittest
import os
from directory_manager import DirectoryManager

class TestDirectoryManager(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = 'test_tmp'
        self.work_dir = 'test_work'
        self.manager = DirectoryManager(tmp_directory=self.tmp_dir, work_directory=self.work_dir)

    def tearDown(self):
        # Clean up test directories after tests
        for directory in [self.tmp_dir, self.work_dir]:
            if os.path.exists(directory):
                for file in os.listdir(directory):
                    file_path = os.path.join(directory, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                os.rmdir(directory)

    def test_create_directories(self):
        self.assertTrue(os.path.exists(self.tmp_dir))
        self.assertTrue(os.path.exists(self.work_dir))

    def test_clear_tmp_directory(self):
        # Create a dummy file in tmp directory
        dummy_file = os.path.join(self.tmp_dir, 'dummy.txt')
        with open(dummy_file, 'w') as f:
            f.write('dummy content')

        # Clear tmp directory and check
        self.manager.clear_tmp_directory()
        self.assertFalse(os.path.exists(dummy_file))

if __name__ == '__main__':
    unittest.main()
