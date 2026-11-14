"""
Directory Manager Module
------------------------
Creates the two directories of the application:
- the temporary directory, for the downloaded audio and its metadata, emptied
  at each run;
- the work directory, for the transcripts.
"""

import os

# The project directory: the temporary directory must not contain it
_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _contains(directory, path):
    """True if path is directory or inside it."""
    try:
        return os.path.commonpath([directory, path]) == directory
    except ValueError:  # Windows: on different drives
        return False


class DirectoryManager:
    """
    Create the temporary and work directories, and empty the temporary one.

    Attributes:
        tmp_directory (str): Directory for downloaded files (emptied at each run)
        work_directory (str): Directory for the transcripts
    """

    def __init__(self, tmp_directory='tmp', work_directory='work'):
        self.tmp_directory = tmp_directory
        self.work_directory = work_directory
        self._check_tmp_directory()
        self.create_directories()

    def _check_tmp_directory(self):
        """
        Refuse a temporary directory whose emptying would delete other files:
        the work directory, the home directory, a drive root, or a directory
        holding the program (e.g. a wrong value in config.json).
        """
        tmp = os.path.realpath(self.tmp_directory)
        forbidden = {
            os.path.realpath(self.work_directory): 'the work directory',
            os.path.realpath(os.path.expanduser('~')): 'the home directory',
        }
        reason = forbidden.get(tmp)
        if not reason and os.path.dirname(tmp) == tmp:
            reason = 'a drive root'
        if not reason and _contains(tmp, _PROJECT_DIR):
            reason = 'the directory of the program'
        if reason:
            raise ValueError(f"The temporary directory {self.tmp_directory} is {reason}: "
                             "its files would be deleted. Choose another tmp_directory "
                             "in config.json.")

    def create_directories(self):
        """Create the directories if needed, and empty the temporary one."""
        os.makedirs(self.tmp_directory, exist_ok=True)
        os.makedirs(self.work_directory, exist_ok=True)
        self.clear_tmp_directory()

    def clear_tmp_directory(self):
        """Delete the files of the temporary directory (left by the previous run)."""
        for file in os.listdir(self.tmp_directory):
            file_path = os.path.join(self.tmp_directory, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
