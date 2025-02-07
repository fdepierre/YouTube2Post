import unittest
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../modules')))

from ollama_manager import OllamaManager

class TestOllamaManager(unittest.TestCase):
    def setUp(self):
        self.chat_manager = OllamaManager('llama2')
        self.test_dir = tempfile.mkdtemp()
        self.transcript_file = os.path.join(self.test_dir, 'test_transcript.txt')
        with open(self.transcript_file, 'w') as f:
            f.write('Test transcript content')

    def tearDown(self):
        # Clean up test files
        if os.path.exists(self.transcript_file):
            os.remove(self.transcript_file)
        if os.path.exists(self.test_dir):
            os.rmdir(self.test_dir)

    @patch('ollama.chat')
    def test_check_ollama_running_success(self, mock_chat):
        # Mock successful response
        mock_chat.return_value = {'message': {'content': 'Hello'}}
        self.assertTrue(self.chat_manager.check_ollama_running())

    @patch('ollama.chat')
    def test_check_ollama_running_failure(self, mock_chat):
        # Mock failed response
        mock_chat.side_effect = Exception('Connection failed')
        self.assertFalse(self.chat_manager.check_ollama_running())

    @patch('builtins.input')
    @patch('builtins.print')
    @patch('ollama.chat')
    def test_interactive_chat_single_response(self, mock_chat, mock_print, mock_input):
        # Set up mock responses
        mock_chat.side_effect = [
            {'message': {'content': 'Hello'}},  # For service check
            {'message': {'content': 'AI response'}}  # For user question
        ]
        
        # Mock user input to exit after one message
        mock_input.side_effect = ['test question', 'exit']
        
        # Run interactive chat
        self.chat_manager.interactive_chat(self.transcript_file)
        
        # Verify responses were printed
        mock_print.assert_any_call('Assistant:', 'AI response')
        mock_print.assert_any_call('Assistant: Goodbye!')
        
        # Verify chat was called at least twice (check and response)
        self.assertEqual(mock_chat.call_count, 2)


