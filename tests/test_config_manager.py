import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../modules')))


import unittest
from config_manager import ConfigManager, ConfigError
import json
import os

class TestConfigManager(unittest.TestCase):
    def setUp(self):
        # Create a temporary config file for testing
        self.test_config_path = 'test_config.json'
        with open(self.test_config_path, 'w') as f:
            json.dump({'valid_parameter': 'expected_value'}, f)
        
        self.config_manager = ConfigManager(self.test_config_path)

    def tearDown(self):
        # Remove the temporary config file after tests
        os.remove(self.test_config_path)

    def test_read_valid_config(self):
        result = self.config_manager.read_config('valid_parameter')
        self.assertEqual(result, 'expected_value')

    def test_read_invalid_config(self):
        with self.assertRaises(ConfigError):
            self.config_manager.read_config('invalid_parameter')

    def test_file_not_found(self):
        with self.assertRaises(ConfigError):
            invalid_manager = ConfigManager('non_existent.json')
            invalid_manager.read_config('any_parameter')

if __name__ == '__main__':
    unittest.main()
