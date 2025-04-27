import yaml

class Config:
    def __init__(self, config_path):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
    
    def get(self, section, key, default=None):
        return self.config.get(section, {}).get(key, default)

    def get(self, key, default=None):
        return self.config.get(key, default)