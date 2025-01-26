"""
Transcriber Test Module
----------------------
This module contains unit tests for the Transcriber class.
It verifies the proper functioning of audio transcription and
transcript content formatting capabilities.
"""

import unittest
import os
import sys
import json
import tempfile
from unittest.mock import patch, MagicMock
import shutil

# Add the modules directory to the Python path for importing
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../modules')))

from transcriber import Transcriber

class TestTranscriber(unittest.TestCase):
    """
    Test suite for the Transcriber class.
    
    This class tests various transcription operations including:
    - Audio file transcription
    - Transcript content formatting
    - Metadata integration
    - File handling and cleanup
    
    The tests use mocking to simulate the behavior of the
    underlying transcription model.
    """

    def setUp(self):
        """
        Set up the test environment before each test.
        Creates temporary directories and initializes test data.
        """
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        self.transcriber = Transcriber(work_directory=self.test_dir)
        self.audio_file = os.path.join(os.path.dirname(__file__), 'test_transcriber.mp3')
        self.sample_transcript = "This is a sample transcript text."
        
    def tearDown(self):
        """
        Clean up the test environment after each test.
        Removes all temporary files and directories.
        """
        # Clean up all test files
        shutil.rmtree(self.test_dir)

    @patch('whisper.load_model')
    def test_transcribe_audio(self, mock_load_model):
        """
        Test the audio transcription functionality.
        
        This test:
        1. Mocks the Whisper model to simulate transcription
        2. Verifies the transcription process
        3. Checks the output file content
        4. Validates model initialization parameters
        
        Args:
            mock_load_model: Mock object for the Whisper model loader
        """
        # Mock whisper model
        mock_model = MagicMock()
        mock_model.to = MagicMock(return_value=mock_model)
        mock_model.transcribe.return_value = {'text': self.sample_transcript}
        mock_load_model.return_value = mock_model

        # Test transcription
        transcript_file = self.transcriber.transcribe_audio(self.audio_file)
        
        self.assertTrue(os.path.exists(transcript_file))
        with open(transcript_file, 'r') as f:
            content = f.read()
        self.assertEqual(content, self.sample_transcript)
        
        # Verify model was loaded with correct parameters
        mock_load_model.assert_called_once_with('base')

    def test_create_transcript_content(self):
        """
        Test the transcript content creation functionality.
        
        This test verifies:
        1. Proper handling of metadata from JSON
        2. Correct formatting of the final transcript
        3. Integration of video information with transcript
        4. File creation and content validation
        """
        # Create test JSON file
        json_data = {
            'title': 'Test Video Title',
            'uploader': 'Test Author',
            'description': 'Test Description'
        }
        json_file = os.path.join(self.test_dir, 'info.json')
        with open(json_file, 'w') as f:
            json.dump(json_data, f)
            
        # Create test audio file and transcribe
        with patch.object(self.transcriber, 'transcribe_audio') as mock_transcribe:
            mock_transcribe.return_value = os.path.join(self.test_dir, 'transcript.txt')
            with open(mock_transcribe.return_value, 'w') as f:
                f.write(self.sample_transcript)
                
            # Test transcript content creation
            youtube_url = 'https://www.youtube.com/watch?v=test'
            result_file = self.transcriber.create_transcript_content(
                self.audio_file, json_file, youtube_url
            )
            
            # Verify result
            self.assertTrue(os.path.exists(result_file))
            with open(result_file, 'r') as f:
                content = f.read()
                
            # Check all required elements are in the content
            self.assertIn('Test Video Title', content)
            self.assertIn('Test Author', content)
            self.assertIn('Test Description', content)
            self.assertIn(self.sample_transcript, content)
            self.assertIn(youtube_url, content)

    def test_create_transcript_content_with_special_chars(self):
        """
        Test handling of special characters in title.
        
        This test verifies that the filename is properly sanitized
        when special characters are present in the title.
        """
        # Test handling of special characters in title
        json_data = {
            'title': 'Test!@#$%^&* Video:;Title',
            'uploader': 'Test Author',
            'description': 'Test Description'
        }
        json_file = os.path.join(self.test_dir, 'info.json')
        with open(json_file, 'w') as f:
            json.dump(json_data, f)

        with patch.object(self.transcriber, 'transcribe_audio') as mock_transcribe:
            mock_transcribe.return_value = os.path.join(self.test_dir, 'transcript.txt')
            with open(mock_transcribe.return_value, 'w') as f:
                f.write(self.sample_transcript)

            content_file = self.transcriber.create_transcript_content(
                self.audio_file, json_file, 'https://youtube.com/test'
            )

            # Verify filename only contains safe characters
            filename = os.path.basename(content_file)
            self.assertTrue(all(c.isalnum() or c in '_-' for c in filename.replace('_transcript.txt', '')))

    def test_missing_json_fields(self):
        """
        Test handling of missing fields in JSON.
        
        This test verifies that default values are used when
        required fields are missing from the JSON metadata.
        """
        # Test handling of missing fields in JSON
        json_data = {}  # Empty JSON
        json_file = os.path.join(self.test_dir, 'info.json')
        with open(json_file, 'w') as f:
            json.dump(json_data, f)

        with patch.object(self.transcriber, 'transcribe_audio') as mock_transcribe:
            mock_transcribe.return_value = os.path.join(self.test_dir, 'transcript.txt')
            with open(mock_transcribe.return_value, 'w') as f:
                f.write(self.sample_transcript)

            content_file = self.transcriber.create_transcript_content(
                self.audio_file, json_file, 'https://youtube.com/test'
            )

            with open(content_file, 'r') as f:
                content = f.read()
            
            # Verify default values are used
            self.assertIn('Unknown Title', content)
            self.assertIn('Unknown Author', content)
            self.assertIn('No Description', content)

if __name__ == '__main__':
    unittest.main()
