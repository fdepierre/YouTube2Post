"""
Directory Manager Test Module
---------------------------
This module contains unit tests for the DirectoryManager class.
It verifies the proper creation, management, and cleanup of
temporary and working directories.
"""

import unittest
import os
from directory_manager import DirectoryManager

class TestDirectoryManager(unittest.TestCase):
    """
    Test suite for the DirectoryManager class.
    
    This class tests various directory management operations including:
    - Creation of temporary and working directories
    - Cleanup of temporary files
    - Directory existence verification
    """

    def setUp(self):
        """
        Set up the test environment before each test.
        Creates test instances of temporary and working directories.
        """
        self.tmp_dir = 'test_tmp'
        self.work_dir = 'test_work'
        self.manager = DirectoryManager(tmp_directory=self.tmp_dir, work_directory=self.work_dir)

    def tearDown(self):
        """
        Clean up the test environment after each test.
        Removes all test directories and their contents.
        """
        # Clean up test directories after tests
        for directory in [self.tmp_dir, self.work_dir]:
            if os.path.exists(directory):
                for file in os.listdir(directory):
                    file_path = os.path.join(directory, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                os.rmdir(directory)

    def test_create_directories(self):
        """
        Test the creation of directories.
        Verifies that both temporary and working directories are
        created and exist in the filesystem.
        """
        self.assertTrue(os.path.exists(self.tmp_dir))
        self.assertTrue(os.path.exists(self.work_dir))

    def test_clear_tmp_directory(self):
        """
        Test the cleanup of temporary directory.
        Creates a test file and verifies that it is properly removed
        when the cleanup method is called.
        """
        # Create a dummy file in tmp directory
        dummy_file = os.path.join(self.tmp_dir, 'dummy.txt')
        with open(dummy_file, 'w') as f:
            f.write('dummy content')

        # Clear tmp directory and check
        self.manager.clear_tmp_directory()
        self.assertFalse(os.path.exists(dummy_file))

if __name__ == '__main__':
    unittest.main()
