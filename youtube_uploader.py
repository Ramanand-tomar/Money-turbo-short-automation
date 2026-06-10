import os
import random
import time
import json
import httplib2
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from loguru import logger
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# Scopes needed for YouTube uploads and channel info querying
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.readonly'
]
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'


def get_web_flow(redirect_uri: str, user_id: str = "global"):
    import json
    from app.services import db
    
    # 1. Try loading from global environment variable first (Developer-side config)
    client_secret_json = os.getenv("YOUTUBE_CLIENT_SECRET_JSON")
    if client_secret_json:
        try:
            client_config = json.loads(client_secret_json)
            if 'web' in client_config:
                client_config['web']['redirect_uris'] = [redirect_uri]
            elif 'installed' in client_config:
                client_config = {
                    "web": {
                        "client_id": client_config['installed']['client_id'],
                        "client_secret": client_config['installed']['client_secret'],
                        "auth_uri": client_config['installed']['auth_uri'],
                        "token_uri": client_config['installed']['token_uri'],
                        "redirect_uris": [redirect_uri]
                    }
                }
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            flow.redirect_uri = redirect_uri
            return flow
        except Exception as parse_err:
            logger.warning(f"Failed to parse YOUTUBE_CLIENT_SECRET_JSON from environment: {parse_err}")

    # 2. Try loading from database settings next
    client_id = db.get_setting("youtube_client_id", user_id=user_id)
    client_secret = db.get_setting("youtube_client_secret", user_id=user_id)
    
    if not client_id or not client_secret:
        # 3. Fallback to client_secret.json local file
        if os.path.exists('client_secret.json'):
            with open('client_secret.json', 'r') as f:
                client_config = json.load(f)
                if 'web' in client_config:
                    client_config['web']['redirect_uris'] = [redirect_uri]
                elif 'installed' in client_config:
                    client_config = {
                        "web": {
                            "client_id": client_config['installed']['client_id'],
                            "client_secret": client_config['installed']['client_secret'],
                            "auth_uri": client_config['installed']['auth_uri'],
                            "token_uri": client_config['installed']['token_uri'],
                            "redirect_uris": [redirect_uri]
                        }
                    }
                flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
                flow.redirect_uri = redirect_uri
                return flow
        raise Exception("Missing YouTube Client ID and Client Secret in settings, environment JSON, or client_secret.json")
        
    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri]
        }
    }
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    flow.redirect_uri = redirect_uri
    return flow

def get_authenticated_service(user_id: str = "global"):
    from app.services import db
    creds = None
    
    # 1. Try loading from database first
    db_creds = db.get_youtube_credentials(user_id=user_id)
    if db_creds:
        logger.info(f"Loading YouTube OAuth credentials from database settings for user {user_id}.")
        client_id = db.get_setting("youtube_client_id", user_id=user_id)
        client_secret = db.get_setting("youtube_client_secret", user_id=user_id)
        
        # Resolve client credentials from env / local file if not present in DB settings
        if not client_id or not client_secret:
            env_json = os.getenv("YOUTUBE_CLIENT_SECRET_JSON")
            if env_json:
                try:
                    parsed = json.loads(env_json)
                    if "web" in parsed:
                        client_id = parsed["web"].get("client_id")
                        client_secret = parsed["web"].get("client_secret")
                    elif "installed" in parsed:
                        client_id = parsed["installed"].get("client_id")
                        client_secret = parsed["installed"].get("client_secret")
                except Exception:
                    pass
            
            if (not client_id or not client_secret) and os.path.exists("client_secret.json"):
                try:
                    with open("client_secret.json", "r") as f:
                        parsed = json.load(f)
                        if "web" in parsed:
                            client_id = parsed["web"].get("client_id")
                            client_secret = parsed["web"].get("client_secret")
                        elif "installed" in parsed:
                            client_id = parsed["installed"].get("client_id")
                            client_secret = parsed["installed"].get("client_secret")
                except Exception:
                    pass
        
        creds = Credentials(
            token=db_creds["access_token"],
            refresh_token=db_creds["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id or os.getenv("YOUTUBE_CLIENT_ID"),
            client_secret=client_secret or os.getenv("YOUTUBE_CLIENT_SECRET")
        )
        
        if creds.expired or not creds.valid:
            logger.info("Database credentials expired. Attempting refresh...")
            try:
                creds.refresh(Request())
                db.save_youtube_credentials(
                    channel_id=db_creds["channel_id"],
                    channel_name=db_creds["channel_name"],
                    access_token=creds.token,
                    refresh_token=creds.refresh_token,
                    token_expiry=str(creds.expiry),
                    user_id=user_id
                )
                logger.success("Refreshed credentials successfully saved back to database.")
            except Exception as ref_err:
                logger.error(f"Failed to refresh database YouTube credentials: {ref_err}")
                creds = None
 
    # 2. Fallback to local token.json if no database credentials exist
    if not creds:
        if os.path.exists('token.json'):
            logger.info("Fallback: Loading cached OAuth credentials from token.json")
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            if creds and creds.expired and creds.refresh_token:
                logger.info("Fallback credentials expired. Attempting refresh...")
                try:
                    creds.refresh(Request())
                    with open('token.json', 'w') as token:
                        token.write(creds.to_json())
                except Exception as ref_err:
                    logger.error(f"Failed to refresh local token.json: {ref_err}")
                    creds = None
 
    if not creds:
        raise Exception(f"No active YouTube channel connected for user {user_id}. Please authenticate via the Web Dashboard.")
 
    return build(API_SERVICE_NAME, API_VERSION, credentials=creds)

def initialize_upload(youtube, file_path, title, description, category="22", tags=None, privacy_status="private"):
    tags = tags or ["shorts", "motivation", "viral"]
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': category
        },
        'status': {
            'privacyStatus': privacy_status,
            'selfDeclaredMadeForKids': False
        }
    }

    # Call the API's videos.insert method to create and upload the video.
    media = MediaFileUpload(
        file_path, 
        chunksize=1024 * 1024, 
        mimetype='application/octet-stream', 
        resumable=True
    )
    
    request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=media
    )

    return resumable_upload(request)

def resumable_upload(request):
    response = None
    error = None
    retry = 0
    max_retries = 10
    
    while response is None:
        try:
            logger.info("Starting chunk upload...")
            status, response = request.next_chunk()
            if response is not None:
                if 'id' in response:
                    logger.success(f"Video uploaded successfully. Video ID: {response['id']}")
                    return response
                else:
                    raise Exception(f"The upload failed with an unexpected response: {response}")
            if status:
                logger.info(f"Upload progress: {int(status.progress() * 100)}%")
        except HttpError as e:
            if e.resp.status in [500, 502, 503, 504]:
                error = f"A retryable HTTP error occurred: {e.resp.status}"
            else:
                raise e
        except (httplib2.HttpLib2Error, IOError) as e:
            error = f"A retryable connection error occurred: {e}"

        if error:
            logger.warning(error)
            retry += 1
            if retry > max_retries:
                raise Exception("No longer retrying. Max retries exceeded.")
            sleep_seconds = random.random() * (2 ** retry)
            logger.info(f"Sleeping {sleep_seconds:.2f} seconds before retrying...")
            time.sleep(sleep_seconds)

def upload_video(file_path, title, description, tags=None, privacy_status="private", user_id: str = "global"):
    if not os.path.exists(file_path):
        logger.error(f"Video file not found at: {file_path}")
        return None
    try:
        youtube = get_authenticated_service(user_id=user_id)
        return initialize_upload(youtube, file_path, title, description, tags=tags, privacy_status=privacy_status)
    except Exception as e:
        logger.exception(f"An error occurred during YouTube upload: {e}")
        return None

if __name__ == "__main__":
    logger.info("Uploader module loaded")
