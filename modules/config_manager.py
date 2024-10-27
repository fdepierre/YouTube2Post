import json

class ConfigError(Exception):
    pass

class ConfigManager:
    def __init__(self, config_file_path='config.json'):
        self.config_file_path = config_file_path

    def read_config(self, parameter):
        try:
            with open(self.config_file_path, 'r') as config_file:
                config = json.load(config_file)
        except FileNotFoundError:
            raise ConfigError(f"Config file '{self.config_file_path}' not found.")
        
        if parameter not in config:
            raise ConfigError(f"Parameter '{parameter}' not found in configuration.")
        
        return config[parameter]

