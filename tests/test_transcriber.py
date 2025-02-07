import unittest
import os
import sys
from unittest.mock import patch, MagicMock

# Add the modules directory to the Python path for importing
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../modules')))

from transcriber import Transcriber

class TestTranscriber(unittest.TestCase):
    def setUp(self):
        self.transcriber = Transcriber(work_directory='.')
        self.test_audio = os.path.join(os.path.dirname(__file__), 'test_transcriber.mp3')
        self.expected_words = ['grow', 'weed', 'English', 'minute', 'quickly']

    def test_transcribe_audio_content(self):
        """Test that the transcription contains expected key words"""
        # Read the existing transcript
        transcript_file = os.path.join(os.path.dirname(__file__), 'test_transcriber.mp3.txt')
        
        # Read the transcript
        with open(transcript_file, 'r', encoding='utf-8') as f:
            transcript_text = f.read().lower()
        
        # Check for the presence of expected words
        found_words = []
        for word in self.expected_words:
            if word.lower() in transcript_text:
                found_words.append(word)
        
        # Assert that all expected words are found
        self.assertEqual(
            len(found_words), 
            len(self.expected_words), 
            f"Expected to find all words {self.expected_words}, but only found {found_words}"
        )

if __name__ == '__main__':
    unittest.main()
