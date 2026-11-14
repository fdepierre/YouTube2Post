"""Real YouTube download: needs an Internet connection."""

import os
import tempfile
import unittest
import unittest.mock

from modules.youtube_downloader import YouTubeDownloader


class TestYouTubeDownloader(unittest.TestCase):
    def test_download_audio(self):
        with tempfile.TemporaryDirectory() as tmp, unittest.mock.patch('builtins.print'):
            downloader = YouTubeDownloader(tmp_directory=tmp)
            audio_file, json_file = downloader.download_audio('https://www.youtube.com/watch?v=v4t0E3S1N1k')
            self.assertTrue(os.path.exists(audio_file))
            self.assertTrue(os.path.exists(json_file))


if __name__ == '__main__':
    unittest.main()
