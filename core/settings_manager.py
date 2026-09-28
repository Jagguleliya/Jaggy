import yaml
from pathlib import Path

class SettingsManager:
    def __init__(self, config_path='config/config.yaml'):
        self.config_path = Path(config_path)
        
    def _read_config(self) -> dict:
        if not self.config_path.exists():
            return {}
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    def _write_config(self, data: dict):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(data, f)
            
    def get_all(self) -> dict:
        return self._read_config()
        
    def get_section(self, section: str) -> dict:
        config = self._read_config()
        return config.get(section, {})
        
    def update_section(self, section: str, data: dict):
        config = self._read_config()
        if section not in config:
            config[section] = {}
        config[section].update(data)
        self._write_config(config)
        
    def add_channel(self, channel: str):
        config = self._read_config()
        if 'clipping' not in config:
            config['clipping'] = {}
        if 'custom_channels' not in config['clipping']:
            config['clipping']['custom_channels'] = []
        if channel not in config['clipping']['custom_channels']:
            config['clipping']['custom_channels'].append(channel)
            self._write_config(config)
            
    def remove_channel(self, channel: str):
        config = self._read_config()
        try:
            config['clipping']['custom_channels'].remove(channel)
            self._write_config(config)
        except (KeyError, ValueError):
            pass
            
    def get_channels(self) -> list:
        config = self._read_config()
        clipping = config.get('clipping', {})
        channels = clipping.get('custom_channels', [])
        if not channels:
            return clipping.get('default_viral_pool', [])
        return channels
        
    def update_schedule(self, times: list, mode: str):
        config = self._read_config()
        if 'schedule' not in config:
            config['schedule'] = {}
        config['schedule']['upload_times'] = times
        config['schedule']['mode'] = mode
        self._write_config(config)
        
    def update_platform_keys(self, platform: str, keys: dict):
        config = self._read_config()
        if 'credentials' not in config:
            config['credentials'] = {}
        if platform not in config['credentials']:
            config['credentials'][platform] = {}
        config['credentials'][platform].update(keys)
        self._write_config(config)
        
    def get_security_settings(self) -> dict:
        config = self._read_config()
        return config.get('security', {})
        
    def update_security(self, data: dict):
        self.update_section('security', data)
