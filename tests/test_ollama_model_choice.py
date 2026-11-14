import unittest
from unittest.mock import MagicMock, patch

from modules import ollama_manager as om


def _manager(installed, running):
    with patch.object(om, 'Client') as client_cls:
        manager = om.OllamaManager()
    client = client_cls.return_value
    client.list.return_value = MagicMock(models=[MagicMock(model=m) for m in installed])
    client.ps.return_value = MagicMock(models=[MagicMock(model=m) for m in running])
    return manager


class TestChooseModel(unittest.TestCase):
    def test_no_model_running_is_not_an_error(self):
        # the reported bug: 'No Ollama model is running' at start-up
        manager = _manager(['qwen3.5:4b'], [])
        self.assertEqual(manager.choose_model(), 'qwen3.5:4b')

    def test_the_running_model_is_used(self):
        manager = _manager(['qwen3.5:4b', 'gemma4:26b'], ['gemma4:26b'])
        self.assertEqual(manager.choose_model(), 'gemma4:26b')

    def test_several_installed_none_running_asks_enter_takes_newest(self):
        manager = _manager(['qwen3.5:4b', 'gemma4:26b'], [])
        with patch('builtins.input', return_value='') as ask, patch('builtins.print'):
            self.assertEqual(manager.choose_model(), 'qwen3.5:4b')
        ask.assert_called_once()

    def test_ask_lets_user_pick_any_installed_model(self):
        manager = _manager(['qwen3.5:4b', 'gemma4:26b', 'llama3.2:latest'], ['qwen3.5:4b'])
        with patch('builtins.input', side_effect=['9', 'x', '3']), patch('builtins.print'):
            self.assertEqual(manager.choose_model(ask=True), 'llama3.2:latest')

    def test_nothing_installed(self):
        manager = _manager([], [])
        with self.assertRaisesRegex(Exception, 'ollama pull'):
            manager.choose_model()

    def test_cancel(self):
        manager = _manager(['a:1', 'b:1'], [])
        with patch('builtins.input', side_effect=EOFError), patch('builtins.print'):
            with self.assertRaisesRegex(Exception, 'No model selected'):
                manager.choose_model()


if __name__ == '__main__':
    unittest.main()
