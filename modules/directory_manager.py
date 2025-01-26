"""
Directory Manager Module
----------------------
This module handles the creation and management of working directories for the application.
It maintains two main directories:
- A temporary directory for downloaded files and intermediate processing
- A work directory for final output files
"""

import os

class DirectoryManager:
    """
    A class to manage working directories for the application.
    
    This class handles the creation and maintenance of temporary and working
    directories. It ensures that directories exist and manages cleanup of
    temporary files.
    
    Attributes:
        tmp_directory (str): Path to temporary directory for intermediate files
        work_directory (str): Path to working directory for final output
    """

    def __init__(self, tmp_directory='tmp', work_directory='work'):
        """
        Initialize the DirectoryManager with paths for temporary and working directories.
        
        Args:
            tmp_directory (str): Path to temporary directory (default: 'tmp')
            work_directory (str): Path to working directory (default: 'work')
        """
        self.tmp_directory = tmp_directory
        self.work_directory = work_directory
        self.create_directories()

    def create_directories(self):
        """
        Create the necessary directories if they don't exist.
        Also performs cleanup of the temporary directory.
        """
        os.makedirs(self.tmp_directory, exist_ok=True)
        os.makedirs(self.work_directory, exist_ok=True)
        self.clear_tmp_directory()

    def clear_tmp_directory(self):
        """
        Remove all files from the temporary directory.
        This helps maintain a clean workspace and prevent conflicts
        between different processing runs.
        """
        for file in os.listdir(self.tmp_directory):
            file_path = os.path.join(self.tmp_directory, file)
            if os.path.isfile(file_path):
                os.remove(file_path)

    def get_tmp_directory(self):
        """
        Get the path to the temporary directory.
        
        Returns:
            str: Path to the temporary directory
        """
        return self.tmp_directory

    def get_work_directory(self):
        """
        Get the path to the working directory.
        
        Returns:
            str: Path to the working directory
        """
        return self.work_directory
