import unittest
import os
import sys

# Add parent directory to path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from modules.ollama_manager import OllamaManager

class TestOllamaManager(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures before all tests."""
        # Initialize OllamaManager without specifying a model
        cls.ollama_manager = OllamaManager()
        
        # Get running models and use the first one for testing if available
        try:
            running_models = cls.ollama_manager.list_running_models()
            if running_models:
                cls.model = running_models[0]
                cls.ollama_manager.model = cls.model
            else:
                # If no running models, we'll skip tests that require a model
                cls.model = None
        except Exception:
            cls.model = None

    def test_01_check_ollama_running(self):
        """Test if Ollama service is running."""
        try:
            result = self.ollama_manager.check_ollama_running()
            self.assertTrue(result, "Ollama service should be running")
        except Exception as e:
            self.fail(f"Ollama service check failed: {str(e)}")

    def test_02_list_available_models(self):
        """Test listing available models."""
        try:
            available_models = self.ollama_manager.list_available_models()
            self.assertIsNotNone(available_models)
            self.assertTrue(len(available_models) > 0, "Should have at least one model available")
        except Exception as e:
            self.fail(f"Failed to list available models: {str(e)}")

    def test_03_list_running_models(self):
        """Test listing running models."""
        try:
            running_models = self.ollama_manager.list_running_models()
            self.assertIsNotNone(running_models)
            # We don't assert that a specific model is running, just that we can get the list
        except Exception as e:
            self.fail(f"Failed to list running models: {str(e)}")
            
    def test_04_select_model_non_interactive(self):
        """Test selecting a model in non-interactive mode."""
        if not self.model:  # Skip if no running models
            self.skipTest("No running models available for testing")
            
        try:
            selected_model = self.ollama_manager.select_model(use_running=True, non_interactive=True)
            self.assertIsNotNone(selected_model)
            self.assertTrue(isinstance(selected_model, str))
        except Exception as e:
            self.fail(f"Failed to select model in non-interactive mode: {str(e)}")

if __name__ == '__main__':
    unittest.main()
