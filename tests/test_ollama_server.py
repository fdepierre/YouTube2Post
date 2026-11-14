import os
import unittest
from unittest.mock import MagicMock, patch

from modules import ollama_manager as om
from modules import ui


class TestServerLocation(unittest.TestCase):
    def test_remote(self):
        self.assertEqual(om.server_location('http://192.168.1.20:11434'),
                         'on another computer (192.168.1.20)')

    def test_wsl_with_ollama_on_windows(self):
        with patch.object(om, 'environment', return_value='wsl'), \
             patch.object(om, 'process_running', return_value=False):
            self.assertIn('Windows host', om.server_location('http://127.0.0.1:11434'))

    def test_wsl_with_ollama_inside(self):
        with patch.object(om, 'environment', return_value='wsl'), \
             patch.object(om, 'process_running', return_value=True):
            self.assertEqual(om.server_location('http://localhost:11434'), 'inside WSL')

    def test_local(self):
        with patch.object(om, 'environment', return_value='windows'):
            self.assertEqual(om.server_location('http://localhost:11434'), 'on this computer')


class TestVerboseChatDetails(unittest.TestCase):
    def _chat(self, chunks):
        lines = []
        with patch.object(om, 'Client') as client_cls, \
             patch.object(ui, 'verbose', True), \
             patch.object(ui, 'detail', side_effect=lines.append), \
             patch.object(om, 'gpu_status', return_value={
                 'name': 'RTX', 'memory.total': 6144.0, 'memory.used': 1024.0}), \
             patch.object(om, 'server_location', return_value='on this computer'):
            client = client_cls.return_value
            client._client.base_url = 'http://127.0.0.1:11434'
            client._client.get.return_value.json.return_value = {'version': '0.40.15'}
            client.show.return_value = MagicMock(modelinfo={}, capabilities=['thinking'])
            client.ps.return_value.models = []
            client.chat.side_effect = lambda **kw: iter(chunks)
            manager = om.OllamaManager(model='m')
            transcript = os.path.join(os.path.dirname(__file__), 'test_chat.txt')
            with patch('builtins.input', side_effect=['q', 'exit']), patch('builtins.print'):
                manager.interactive_chat(transcript)
        return '\n'.join(lines)

    def test_server_api_and_hardware(self):
        text = self._chat([{'message': {'content': 'ok'}}])
        self.assertIn('Ollama server 0.40.15 at http://127.0.0.1:11434, running on this computer', text)
        self.assertIn('think=false', text)
        self.assertIn('RTX, 5.0 of 6.0 GB GPU memory free', text)
        self.assertIn('No model in Ollama memory yet', text)
        self.assertIn('no reasoning received', text)

    def test_reasoning_is_reported(self):
        text = self._chat([{'message': {'content': '', 'thinking': 'hmm...'}},
                           {'message': {'content': 'ok'}}])
        self.assertIn('Thinking: 6 characters of reasoning received', text)


if __name__ == '__main__':
    unittest.main()
