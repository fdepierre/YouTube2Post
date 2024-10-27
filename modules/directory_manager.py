import os

class DirectoryManager:
    def __init__(self, tmp_directory='tmp', work_directory='work'):
        self.tmp_directory = tmp_directory
        self.work_directory = work_directory
        self.create_directories()

    def create_directories(self):
        os.makedirs(self.tmp_directory, exist_ok=True)
        os.makedirs(self.work_directory, exist_ok=True)
        self.clear_tmp_directory()

    def clear_tmp_directory(self):
        for file in os.listdir(self.tmp_directory):
            file_path = os.path.join(self.tmp_directory, file)
            if os.path.isfile(file_path):
                os.remove(file_path)

    def get_tmp_directory(self):
        return self.tmp_directory

    def get_work_directory(self):
        return self.work_directory
