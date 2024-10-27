import unittest
import os
import sys
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../modules')))

from transcriber import Transcriber

class TestTranscriber(unittest.TestCase):
    def setUp(self):
        self.transcriber = Transcriber()

    def test_create_transcript_content(self):
        # Replace these with valid paths for testing
        audio_file = './tests/test_transcriber.mp3'
        json_file = 'sample_info.json'
        youtube_url = 'https://www.youtube.com/watch?v=v4t0E3S1N1k'

        with open(json_file, 'w') as f:
            json.dump({
                'title': 'Sample Title',
                'uploader': 'Sample Author',
                'description': 'Sample Description'
            }, f)

        full_content_file = self.transcriber.create_transcript_content(audio_file, json_file, youtube_url)
        
        self.assertTrue(os.path.exists(full_content_file))
        
        # Clean up created files
        os.remove(json_file)
        os.remove(full_content_file)

if __name__ == '__main__':
    unittest.main()
