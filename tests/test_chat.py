import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../modules')))

import unittest

from unittest.mock import patch
from chatbot import Chatbot

class TestChatbot(unittest.TestCase):
    @patch('ollama.chat')
    def test_check_ollama_running(self, mock_chat):
        mock_chat.return_value = {'message': {'content': 'Hello'}}
        
        chatbot = Chatbot(model='llama3.2')
        
        self.assertTrue(chatbot.check_ollama_running())

if __name__ == '__main__':
    unittest.main()
