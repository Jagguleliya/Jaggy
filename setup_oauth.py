import os
import argparse
import yaml
import logging
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.readonly',
    'https://www.googleapis.com/auth/youtube.force-ssl',
    'https://www.googleapis.com/auth/yt-analytics.readonly'
]

def load_config(config_path: str = 'config/config.yaml') -> dict:
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Could not load config: {e}")
    return {}

def setup_oauth(config_path: str = 'config/config.yaml', verify_only: bool = False):
    config = load_config(config_path)
    
    platforms = config.get('platforms', {})
    youtube_config = platforms.get('youtube', {})
    
    client_secrets_file = youtube_config.get('client_secrets', 'config/client_secrets.json')
    token_file = youtube_config.get('token_file', 'config/token.json')
    
    creds = None
    if os.path.exists(token_file):
        try:
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
            logger.info("Loaded existing credentials from token file.")
        except Exception as e:
            logger.warning(f"Error loading token.json: {e}")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired credentials...")
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                creds = None
        
        if not creds and not verify_only:
            if not os.path.exists(client_secrets_file):
                logger.error(f"client_secrets file not found at {client_secrets_file}. Please download it from Google Cloud Console.")
                return
            
            logger.info("Initiating OAuth flow. A browser window will open.")
            try:
                flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
                creds = flow.run_local_server(port=0)
                
                os.makedirs(os.path.dirname(token_file) or '.', exist_ok=True)
                with open(token_file, 'w') as token:
                    token.write(creds.to_json())
                logger.info(f"OAuth successful! Token saved to {token_file}")
            except Exception as e:
                logger.error(f"Failed during OAuth flow: {e}")
                return
        elif verify_only and not creds:
            logger.error("No valid credentials to verify. Run without --verify first.")
            return

    if creds and creds.valid:
        try:
            youtube = build('youtube', 'v3', credentials=creds)
            request = youtube.channels().list(
                part="snippet,statistics",
                mine=True
            )
            response = request.execute()
            if response.get('items'):
                channel_info = response['items'][0]
                channel_title = channel_info['snippet']['title']
                logger.info(f"Successfully authenticated as YouTube Channel: {channel_title}")
            else:
                logger.warning("Authenticated, but no channel found for this user.")
        except Exception as e:
            logger.error(f"Verification failed. The token might be invalid or lacking permissions. Error: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Setup YouTube OAuth for Shorts Bot")
    parser.add_argument('--config', default='config/config.yaml', help="Path to config.yaml")
    parser.add_argument('--verify', action='store_true', help="Only verify existing token")
    args = parser.parse_args()
    
    setup_oauth(config_path=args.config, verify_only=args.verify)
