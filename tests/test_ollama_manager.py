"""Tests against the real Ollama service: skipped when it is not running."""

import unittest
from unittest.mock import patch

from modules.ollama_manager import OllamaManager


class TestOllamaManager(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ollama_manager = OllamaManager()
        if not cls.ollama_manager.check_ollama_running():
            raise unittest.SkipTest("Ollama is not running")

    def test_list_available_models(self):
        models = self.ollama_manager.list_available_models()
        self.assertIsInstance(models, list)
        if not models:
            self.skipTest("No Ollama model installed")

    def test_list_running_models(self):
        self.assertIsInstance(self.ollama_manager.list_running_models(), list)

    def test_choose_model_default(self):
        """Enter (the default choice) returns an installed model."""
        if not self.ollama_manager.list_available_models():
            self.skipTest("No Ollama model installed")
        with patch('builtins.input', return_value=''), patch('builtins.print'):
            selected_model = self.ollama_manager.choose_model()
        self.assertIn(selected_model, self.ollama_manager.list_available_models())


if __name__ == '__main__':
    unittest.main()
