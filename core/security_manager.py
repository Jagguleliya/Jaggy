import os
import json
import shutil
from pathlib import Path
from core.settings_manager import SettingsManager

class SecurityManager:
    def __init__(self, config_path='config/config.yaml'):
        self.config_path = Path(config_path)
        self.project_root = self.config_path.parent.parent
        self.settings = SettingsManager(config_path)
        
    def get_connected_accounts(self) -> list:
        accounts = []
        token_path = self.project_root / "config" / "token.json"
        if token_path.exists():
            accounts.append("YouTube")
        return accounts
        
    def revoke_youtube_oauth(self):
        token_path = self.project_root / "config" / "token.json"
        if token_path.exists():
            token_path.unlink()
            
    def get_permissions_status(self) -> dict:
        return {
            "youtube": "granted" if "YouTube" in self.get_connected_accounts() else "not_granted"
        }
        
    def get_api_key_status(self) -> dict:
        config = self.settings.get_all()
        creds = config.get("credentials", {})
        status = {}
        for platform, keys in creds.items():
            if isinstance(keys, dict):
                status[platform] = {k: self.mask_key(v) for k, v in keys.items() if isinstance(v, str)}
        return status
        
    def mask_key(self, key: str) -> str:
        if not key or len(key) < 8:
            return "****"
        return f"{key[:4]}{'*' * (len(key) - 8)}{key[-4:]}"
        
    def get_privacy_summary(self) -> dict:
        return {
            "data_locations": [
                str(self.project_root / "output"),
                str(self.project_root / "data"),
                str(self.project_root / "logs")
            ],
            "stored_locally": ["video_renders", "upload_history", "logs", "oauth_tokens"]
        }
        
    def clear_all_data(self):
        for folder in ["output", "data", "logs"]:
            path = self.project_root / folder
            if path.exists():
                shutil.rmtree(path)
                path.mkdir(exist_ok=True)
                
    def clear_cache(self):
        cache_path = self.project_root / "data" / "clip_cache"
        if cache_path.exists():
            shutil.rmtree(cache_path)
            cache_path.mkdir(exist_ok=True)
            
    def export_settings(self) -> dict:
        config = self.settings.get_all()
        if "credentials" in config:
            for platform in config["credentials"]:
                if isinstance(config["credentials"][platform], dict):
                    for k in config["credentials"][platform]:
                        config["credentials"][platform][k] = self.mask_key(config["credentials"][platform][k])
        return config
