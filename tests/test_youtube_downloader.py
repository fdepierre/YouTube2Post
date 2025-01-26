"""
YouTube Downloader Test Module
----------------------------
This module contains unit tests for the YouTubeDownloader class.
It verifies the proper downloading of YouTube videos and extraction
of audio content for transcription purposes.
"""

import unittest
import os
from youtube_downloader import YouTubeDownloader

class TestYouTubeDownloader(unittest.TestCase):
    """
    Test suite for the YouTubeDownloader class.
    
    This class tests the downloading capabilities including:
    - Audio extraction from YouTube videos
    - Metadata JSON file creation
    - File existence verification
    
    Note: These tests require an active internet connection and
    access to YouTube's services.
    """

    def setUp(self):
        """
        Set up the test environment before each test.
        Creates a test instance of the YouTubeDownloader with a
        dedicated test directory.
        """
        self.downloader = YouTubeDownloader(tmp_directory='test_tmp')

    def tearDown(self):
        """
        Clean up the test environment after each test.
        Removes all downloaded files and the test directory.
        """
        # Clean up test directory after tests
        if os.path.exists('test_tmp'):
            for file in os.listdir('test_tmp'):
                file_path = os.path.join('test_tmp', file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            os.rmdir('test_tmp')

    def test_download_audio(self):
        """
        Test the audio download functionality.
        
        This test:
        1. Downloads audio from a sample YouTube video
        2. Verifies that both audio and metadata files are created
        3. Checks file existence in the filesystem
        
        Note: This test requires an actual YouTube URL and internet
        connectivity to run successfully.
        """
        # This test requires an actual YouTube URL to run successfully.
        youtube_url = 'https://www.youtube.com/watch?v=v4t0E3S1N1k'
        
        audio_file, json_file = self.downloader.download_audio(youtube_url)
        
        self.assertTrue(os.path.exists(audio_file))
        self.assertTrue(os.path.exists(json_file))

if __name__ == '__main__':
    unittest.main()
