import unittest
import os
from youtube_downloader import YouTubeDownloader

class TestYouTubeDownloader(unittest.TestCase):
    def setUp(self):
        self.downloader = YouTubeDownloader(tmp_directory='test_tmp')

    def tearDown(self):
        # Clean up test directory after tests
        if os.path.exists('test_tmp'):
            for file in os.listdir('test_tmp'):
                file_path = os.path.join('test_tmp', file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            os.rmdir('test_tmp')

    def test_download_audio(self):
        # This test requires an actual YouTube URL to run successfully.
        youtube_url = 'https://www.youtube.com/watch?v=v4t0E3S1N1k'
        
        audio_file, json_file = self.downloader.download_audio(youtube_url)
        
        self.assertTrue(os.path.exists(audio_file))
        self.assertTrue(os.path.exists(json_file))

if __name__ == '__main__':
    unittest.main()
