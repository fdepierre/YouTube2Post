import unittest
import json
import os
from modules.ollama_manager import OllamaManager

class TestOllamaManager(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures before all tests."""
        # Read the model name from config
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
        with open(config_path, 'r') as f:
            config = json.load(f)
        cls.model = config['model']
        cls.ollama_manager = OllamaManager(cls.model)

    def test_01_check_ollama_running(self):
        """Test if Ollama service is running and model is available."""
        result = self.ollama_manager.check_ollama_running()
        self.assertTrue(result, "Ollama service should be running and model should be available")

    def test_02_list_available_models(self):
        """Test listing available models."""
        models = self.ollama_manager.list_available_models()
        self.assertIsNotNone(models)
        self.assertTrue(len(models.models) > 0, "Should have at least one model available")
        
        # Check if our configured model is in the list
        model_names = [model.model.split(':')[0] for model in models.models]
        self.assertIn(self.model, model_names, f"Configured model {self.model} should be in available models")

    def test_03_list_running_models(self):
        """Test listing running models."""
        running_models = self.ollama_manager.list_running_models()
        self.assertIsNotNone(running_models)
        
        # After running check_ollama_running, our model should be in the running models
        model_names = [model.model.split(':')[0] for model in running_models.models]
        self.assertIn(self.model, model_names, f"Model {self.model} should be running after previous tests")

if __name__ == '__main__':
    unittest.main()
