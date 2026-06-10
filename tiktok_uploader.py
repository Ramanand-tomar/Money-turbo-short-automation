import os
import requests
from loguru import logger
from app.services import db
import time

def get_tiktok_client_credentials(user_id="global"):
    client_key = db.get_setting("tiktok_client_key", user_id=user_id) or os.getenv("TIKTOK_CLIENT_KEY", "")
    client_secret = db.get_setting("tiktok_client_secret", user_id=user_id) or os.getenv("TIKTOK_CLIENT_SECRET", "")
    return client_key.strip(), client_secret.strip()

def get_auth_url(user_id="global") -> str:
    client_key, _ = get_tiktok_client_credentials(user_id)
    if not client_key:
        client_key = "dummy_client_key"
    redirect_uri = "http://127.0.0.1:8085/api/v1/tiktok/oauth-callback"
    scope = "user.info.profile,video.upload,video.publish"
    return f"https://www.tiktok.com/v2/auth/authorize/?client_key={client_key}&scope={scope}&response_type=code&redirect_uri={redirect_uri}&state={user_id}"

def exchange_code(code: str, user_id="global") -> dict:
    client_key, client_secret = get_tiktok_client_credentials(user_id)
    redirect_uri = "http://127.0.0.1:8085/api/v1/tiktok/oauth-callback"
    
    if not client_key or client_key == "dummy_client_key":
        logger.warning("Using mock TikTok credentials, simulating token exchange.")
        fake_token = {
            "access_token": "mock_access_token_12345",
            "refresh_token": "mock_refresh_token_12345",
            "expires_in": 86400,
            "open_id": "mock_open_id_12345",
            "display_name": "Mock TikTok Account"
        }
        db.save_platform_oauth(
            user_id=user_id,
            platform="tiktok",
            access_token=fake_token["access_token"],
            refresh_token=fake_token["refresh_token"],
            token_expiry=str(int(time.time()) + fake_token["expires_in"]),
            channel_id=fake_token["open_id"],
            channel_name=fake_token["display_name"]
        )
        return fake_token

    try:
        url = "https://open.tiktokapis.com/v2/oauth/token/"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "client_key": client_key,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri
        }
        response = requests.post(url, headers=headers, data=data, timeout=30)
        response.raise_for_status()
        res_data = response.json()
        
        access_token = res_data.get("access_token")
        refresh_token = res_data.get("refresh_token")
        expires_in = res_data.get("expires_in", 86400)
        open_id = res_data.get("open_id", "")
        
        if not access_token:
            raise Exception(f"Failed to retrieve access token from TikTok: {res_data}")

        display_name = "TikTok Account"
        try:
            profile_url = "https://open.tiktokapis.com/v2/user/info/"
            profile_headers = {"Authorization": f"Bearer {access_token}"}
            profile_res = requests.get(profile_url, headers=profile_headers, timeout=20)
            profile_res.raise_for_status()
            p_data = profile_res.json()
            user_data = p_data.get("data", {}).get("user", {})
            display_name = user_data.get("display_name") or user_data.get("username") or "TikTok Account"
        except Exception as profile_err:
            logger.warning(f"Failed to fetch TikTok user profile info: {profile_err}")
            
        token_expiry = str(int(time.time()) + int(expires_in))
        db.save_platform_oauth(
            user_id=user_id,
            platform="tiktok",
            access_token=access_token,
            refresh_token=refresh_token,
            token_expiry=token_expiry,
            channel_id=open_id,
            channel_name=display_name
        )
        return res_data
    except Exception as e:
        logger.error(f"TikTok code exchange error: {e}")
        raise e

def refresh_token_if_needed(user_id="global") -> str:
    oauth_info = db.get_platform_oauth(user_id, "tiktok")
    if not oauth_info:
        raise Exception(f"No TikTok credentials found in database for user {user_id}.")
        
    access_token = oauth_info["access_token"]
    refresh_token = oauth_info["refresh_token"]
    expiry = oauth_info["token_expiry"]
    channel_id = oauth_info["channel_id"]
    channel_name = oauth_info["channel_name"]
    
    if access_token == "mock_access_token_12345":
        return access_token

    current_time = int(time.time())
    if expiry and int(expiry) - current_time > 300:
        return access_token

    client_key, client_secret = get_tiktok_client_credentials(user_id)
    if not client_key or not refresh_token:
        return access_token

    logger.info(f"TikTok access token expired. Attempting token refresh for user {user_id}...")
    try:
        url = "https://open.tiktokapis.com/v2/oauth/token/"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "client_key": client_key,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        res = requests.post(url, headers=headers, data=data, timeout=30)
        res.raise_for_status()
        res_data = res.json()
        
        new_access_token = res_data.get("access_token")
        new_refresh_token = res_data.get("refresh_token") or refresh_token
        expires_in = res_data.get("expires_in", 86400)
        
        if new_access_token:
            new_expiry = str(current_time + int(expires_in))
            db.save_platform_oauth(
                user_id=user_id,
                platform="tiktok",
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                token_expiry=new_expiry,
                channel_id=channel_id,
                channel_name=channel_name
            )
            logger.success("TikTok access token successfully refreshed.")
            return new_access_token
    except Exception as e:
        logger.error(f"Failed to refresh TikTok token: {e}")
        
    return access_token

def upload_video(user_id: str, file_path: str, caption: str) -> dict:
    if not os.path.exists(file_path):
        raise Exception(f"Video file not found at path: {file_path}")
        
    access_token = refresh_token_if_needed(user_id)
    
    if access_token == "mock_access_token_12345":
        logger.info("TikTok upload simulator: Successful mock upload.")
        return {"success": True, "publish_id": "mock_publish_id_12345"}

    file_size = os.path.getsize(file_path)
    
    try:
        init_url = "https://open.tiktokapis.com/v2/post/publish/video/init/"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        body = {
            "post_info": {
                "title": caption[:2200],
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "video_cover_timestamp_ms": 0
            },
            "source_info": {
                "source_type": "FILE_UPLOAD",
                "video_size": file_size,
                "chunk_size": file_size,
                "total_chunk_count": 1
            }
        }
        
        logger.info(f"TikTok upload Step 1: Initializing video upload (size: {file_size} bytes)")
        response = requests.post(init_url, headers=headers, json=body, timeout=30)
        response.raise_for_status()
        res_data = response.json()
        
        data = res_data.get("data", {})
        upload_url = data.get("upload_url")
        publish_id = data.get("publish_id")
        
        if not upload_url:
            raise Exception(f"TikTok initialization failed to return upload_url: {res_data}")

        logger.info("TikTok upload Step 2: Streaming video bytes to TikTok servers...")
        with open(file_path, "rb") as f:
            put_headers = {
                "Content-Type": "video/mp4",
                "Content-Length": str(file_size),
                "Content-Range": f"bytes 0-{file_size - 1}/{file_size}"
            }
            put_res = requests.put(upload_url, headers=put_headers, data=f, timeout=300)
            put_res.raise_for_status()

        logger.success("TikTok video upload completed successfully.")
        return {"success": True, "publish_id": publish_id}
    except Exception as e:
        logger.error(f"TikTok video upload pipeline failed: {e}")
        raise e
