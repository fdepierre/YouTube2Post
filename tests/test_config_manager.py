"""
Config Manager Test Module
------------------------
This module contains unit tests for the ConfigManager class.
It verifies the proper functioning of configuration file reading
and error handling capabilities.
"""

import sys
import os

# Add the modules directory to the Python path for importing
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../modules')))

import unittest
from config_manager import ConfigManager, ConfigError
import json
import os

class TestConfigManager(unittest.TestCase):
    """
    Test suite for the ConfigManager class.
    
    This class tests various scenarios including:
    - Reading valid configuration parameters
    - Handling invalid parameter requests
    - Managing missing configuration files
    """

    def setUp(self):
        """
        Set up the test environment before each test.
        Creates a temporary configuration file with test data.
        """
        # Create a temporary config file for testing
        self.test_config_path = 'test_config.json'
        with open(self.test_config_path, 'w') as f:
            json.dump({'valid_parameter': 'expected_value'}, f)
        
        self.config_manager = ConfigManager(self.test_config_path)

    def tearDown(self):
        """
        Clean up the test environment after each test.
        Removes the temporary configuration file.
        """
        # Remove the temporary config file after tests
        os.remove(self.test_config_path)

    def test_read_valid_config(self):
        """
        Test that valid configuration parameters can be read correctly.
        Verifies that the expected value is returned for a known parameter.
        """
        result = self.config_manager.read_config('valid_parameter')
        self.assertEqual(result, 'expected_value')

    def test_read_invalid_config(self):
        """
        Test handling of invalid configuration parameter requests.
        Verifies that attempting to read a non-existent parameter raises
        the appropriate exception.
        """
        with self.assertRaises(ConfigError):
            self.config_manager.read_config('invalid_parameter')

    def test_file_not_found(self):
        """
        Test handling of missing configuration files.
        Verifies that attempting to read from a non-existent file raises
        the appropriate exception.
        """
        with self.assertRaises(ConfigError):
            invalid_manager = ConfigManager('non_existent.json')
            invalid_manager.read_config('any_parameter')

if __name__ == '__main__':
    unittest.main()
