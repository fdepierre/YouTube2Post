import unittest
from unittest.mock import patch, MagicMock
import os
import tempfile
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../modules')))

from chatbot import Chatbot

class TestChatbot(unittest.TestCase):
    def setUp(self):
        self.chatbot = Chatbot('llama2')
        self.test_dir = tempfile.mkdtemp()
        self.transcript_file = os.path.join(self.test_dir, 'test_transcript.txt')
        with open(self.transcript_file, 'w') as f:
            f.write("Test transcript content")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            for file in os.listdir(self.test_dir):
                os.remove(os.path.join(self.test_dir, file))
            os.rmdir(self.test_dir)

    @patch('ollama.chat')
    def test_check_ollama_running_success(self, mock_chat):
        mock_chat.return_value = {'message': {'content': 'Hello'}}
        self.assertTrue(self.chatbot.check_ollama_running())
        mock_chat.assert_called_once()

    @patch('ollama.chat')
    def test_check_ollama_running_failure_wrong_response(self, mock_chat):
        mock_chat.return_value = {'wrong_key': 'value'}
        self.assertFalse(self.chatbot.check_ollama_running())

    @patch('ollama.chat')
    def test_check_ollama_running_failure_exception(self, mock_chat):
        mock_chat.side_effect = Exception('Connection error')
        self.assertFalse(self.chatbot.check_ollama_running())

    @patch('ollama.chat')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_interactive_chat_success(self, mock_print, mock_input, mock_chat):
        # Mock ollama responses
        mock_chat.side_effect = [
            {'message': {'content': 'Hello'}},  # For check_ollama_running
            {'message': {'content': 'AI response'}}  # For the actual chat
        ]
        
        # Mock user inputs: ask a question then exit
        mock_input.side_effect = ['How are you?', 'exit']
        
        self.chatbot.interactive_chat(self.transcript_file)
        
        # Verify responses were printed
        # Note: Using args to match exactly how print is called
        mock_print.assert_any_call('Chatbot:', 'AI response')
        mock_print.assert_any_call('Chatbot: Goodbye!')
        
        # Verify chat was called at least twice (check and response)
        self.assertEqual(mock_chat.call_count, 2)

    @patch('ollama.chat')
    def test_interactive_chat_ollama_not_running(self, mock_chat):
        mock_chat.return_value = {'wrong_key': 'value'}
        
        with self.assertRaises(Exception) as context:
            self.chatbot.interactive_chat(self.transcript_file)
        
        self.assertTrue('Ollama service is not running' in str(context.exception))

    @patch('ollama.chat')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_interactive_chat_multiple_exchanges(self, mock_print, mock_input, mock_chat):
        # Mock multiple exchanges before exit
        mock_input.side_effect = ['First question', 'Second question', 'exit']
        mock_chat.side_effect = [
            {'message': {'content': 'Hello'}},  # For check_ollama_running
            {'message': {'content': 'First response'}},
            {'message': {'content': 'Second response'}}
        ]
        
        self.chatbot.interactive_chat(self.transcript_file)
        
        # Verify chat responses were printed
        mock_print.assert_any_call('Chatbot:', 'First response')
        mock_print.assert_any_call('Chatbot:', 'Second response')
        mock_print.assert_any_call('Chatbot: Goodbye!')
        
        # Verify chat was called correct number of times (check + 2 responses)
        self.assertEqual(mock_chat.call_count, 3)

if __name__ == '__main__':
    unittest.main()
