"""
Configuration Manager Module
--------------------------
This module handles the reading and management of configuration settings from a JSON file.
It provides a simple interface to access configuration parameters and handles common
error cases such as missing files or parameters.
"""

import json

class ConfigError(Exception):
    """Custom exception class for configuration-related errors."""
    pass

class ConfigManager:
    """
    A class to manage configuration settings from a JSON file.
    
    This class provides methods to read and validate configuration parameters
    from a JSON configuration file. It includes error handling for common
    configuration issues.
    
    Attributes:
        config_file_path (str): Path to the JSON configuration file
    """

    def __init__(self, config_file_path='config.json'):
        """
        Initialize the ConfigManager with a path to the config file.
        
        Args:
            config_file_path (str): Path to the JSON configuration file
                                  (default: 'config.json')
        """
        self.config_file_path = config_file_path

    def read_config(self, parameter):
        """
        Read a specific parameter from the configuration file.
        
        Args:
            parameter (str): Name of the configuration parameter to read
            
        Returns:
            The value of the requested parameter
            
        Raises:
            ConfigError: If the config file is not found or the parameter
                        doesn't exist in the configuration
        """
        try:
            with open(self.config_file_path, 'r') as config_file:
                config = json.load(config_file)
        except FileNotFoundError:
            raise ConfigError(f"Config file '{self.config_file_path}' not found.")
        
        if parameter not in config:
            raise ConfigError(f"Parameter '{parameter}' not found in configuration.")
        
        return config[parameter]
