import os
import requests
from loguru import logger
from app.services import db
import time
from moviepy import VideoFileClip

def get_instagram_client_credentials(user_id="global"):
    client_id = db.get_setting("instagram_client_id", user_id=user_id) or os.getenv("INSTAGRAM_CLIENT_ID", "")
    client_secret = db.get_setting("instagram_client_secret", user_id=user_id) or os.getenv("INSTAGRAM_CLIENT_SECRET", "")
    return client_id.strip(), client_secret.strip()

def get_auth_url(user_id="global") -> str:
    client_id, _ = get_instagram_client_credentials(user_id)
    if not client_id:
        client_id = "dummy_instagram_client_id"
    redirect_uri = "http://127.0.0.1:8085/api/v1/instagram/oauth-callback"
    scope = "instagram_basic,instagram_content_publish,pages_show_list,pages_read_engagement"
    return f"https://www.facebook.com/v18.0/dialog/oauth?client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}&state={user_id}"

def exchange_code(code: str, user_id="global") -> dict:
    client_id, client_secret = get_instagram_client_credentials(user_id)
    redirect_uri = "http://127.0.0.1:8085/api/v1/instagram/oauth-callback"
    
    if not client_id or client_id == "dummy_instagram_client_id":
        logger.warning("Using mock Instagram credentials, simulating token exchange.")
        fake_token = {
            "access_token": "mock_instagram_access_token_12345",
            "expires_in": 5184000,
            "instagram_business_account_id": "mock_ig_user_id_12345",
            "username": "mock_instagram_creator"
        }
        db.save_platform_oauth(
            user_id=user_id,
            platform="instagram",
            access_token=fake_token["access_token"],
            refresh_token="",
            token_expiry=str(int(time.time()) + fake_token["expires_in"]),
            channel_id=fake_token["instagram_business_account_id"],
            channel_name=fake_token["username"]
        )
        return fake_token

    try:
        url = "https://graph.facebook.com/v18.0/oauth/access_token"
        params = {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "code": code
        }
        res = requests.get(url, params=params, timeout=30)
        res.raise_for_status()
        res_data = res.json()
        short_token = res_data.get("access_token")
        
        long_url = "https://graph.facebook.com/v18.0/oauth/access_token"
        long_params = {
            "grant_type": "fb_exchange_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "fb_exchange_token": short_token
        }
        long_res = requests.get(long_url, params=long_params, timeout=30)
        long_res.raise_for_status()
        long_data = long_res.json()
        long_token = long_data.get("access_token")
        expires_in = long_data.get("expires_in", 5184000)
        
        pages_url = "https://graph.facebook.com/v18.0/me/accounts"
        pages_params = {"access_token": long_token}
        pages_res = requests.get(pages_url, params=pages_params, timeout=20)
        pages_res.raise_for_status()
        pages_data = pages_res.json().get("data", [])
        
        if not pages_data:
            raise Exception("No Facebook Pages associated with the authenticated user.")

        ig_business_id = None
        ig_username = "Instagram Creator"
        
        for page in pages_data:
            page_id = page.get("id")
            page_url = f"https://graph.facebook.com/v18.0/{page_id}"
            page_params = {
                "fields": "instagram_business_account",
                "access_token": long_token
            }
            p_res = requests.get(page_url, params=page_params, timeout=15)
            if p_res.status_code == 200:
                p_data = p_res.json()
                ig_acc = p_data.get("instagram_business_account")
                if ig_acc:
                    ig_business_id = ig_acc.get("id")
                    break
                    
        if not ig_business_id:
            raise Exception("Could not find an Instagram Business Account linked to your Facebook Pages. Please link one in Facebook Page settings.")

        try:
            ig_url = f"https://graph.facebook.com/v18.0/{ig_business_id}"
            ig_params = {
                "fields": "username,name",
                "access_token": long_token
            }
            ig_res = requests.get(ig_url, params=ig_params, timeout=15)
            if ig_res.status_code == 200:
                ig_data = ig_res.json()
                ig_username = ig_data.get("username") or ig_data.get("name") or "Instagram Creator"
        except Exception as ig_err:
            logger.warning(f"Failed to query IG username details: {ig_err}")

        token_expiry = str(int(time.time()) + int(expires_in))
        db.save_platform_oauth(
            user_id=user_id,
            platform="instagram",
            access_token=long_token,
            refresh_token="",
            token_expiry=token_expiry,
            channel_id=ig_business_id,
            channel_name=ig_username
        )
        return {
            "access_token": long_token,
            "expires_in": expires_in,
            "instagram_business_account_id": ig_business_id,
            "username": ig_username
        }
    except Exception as e:
        logger.error(f"Instagram Graph code exchange failed: {e}")
        raise e

def upload_video(user_id: str, file_path: str, caption: str) -> dict:
    if not os.path.exists(file_path):
        raise Exception(f"Video file not found at path: {file_path}")

    try:
        clip = VideoFileClip(file_path)
        w, h = clip.size
        clip.close()
        aspect = w / h
        logger.info(f"Validating aspect ratio of {file_path}: size is {w}x{h}, aspect ratio is {aspect:.4f}")
        if not (0.50 <= aspect <= 0.63):
            raise Exception(f"Invalid video aspect ratio: {w}x{h} ({aspect:.4f}). Instagram Reels must be strictly vertical (~9:16 aspect ratio).")
    except Exception as aspect_err:
        logger.error(f"Video aspect ratio validation failed: {aspect_err}")
        raise aspect_err

    oauth_info = db.get_platform_oauth(user_id, "instagram")
    if not oauth_info:
        raise Exception(f"No Instagram connected account found for user {user_id}.")

    access_token = oauth_info["access_token"]
    ig_user_id = oauth_info["channel_id"]

    if access_token == "mock_instagram_access_token_12345":
        logger.info("Instagram upload simulator: Successful mock Reels upload.")
        return {"success": True, "media_id": "mock_media_id_12345"}

    video_url = None
    try:
        c_url = db.get_setting("cloudinary_url", user_id=user_id) or os.getenv("CLOUDINARY_URL")
        if not c_url:
            raise Exception("Cloudinary storage is required to upload files to Instagram. Please configure CLOUDINARY_URL in settings.")
        
        import cloudinary
        import cloudinary.uploader
        cloudinary.config(cloudinary_url=c_url)
        
        logger.info(f"Uploading local file {file_path} to Cloudinary to generate public URL...")
        upload_result = cloudinary.uploader.upload_large(
            file_path,
            resource_type="video",
            folder="instagram_reels"
        )
        video_url = upload_result.get("secure_url")
        logger.info(f"Cloudinary upload completed successfully. Public URL: {video_url}")
    except Exception as cloud_err:
        logger.error(f"Cloudinary upload failed: {cloud_err}")
        raise Exception(f"Failed to fetch public video URL for Instagram Graph API: {str(cloud_err)}")

    try:
        media_url = f"https://graph.facebook.com/v18.0/{ig_user_id}/media"
        headers = {"Authorization": f"Bearer {access_token}"}
        body = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption[:2200],
            "share_to_feed": True
        }
        
        logger.info("Instagram upload Step 3: Initiating container upload...")
        res = requests.post(media_url, headers=headers, json=body, timeout=30)
        res.raise_for_status()
        creation_id = res.json().get("id")
        
        if not creation_id:
            raise Exception(f"Instagram container creation failed: {res.json()}")

        status_url = f"https://graph.facebook.com/v18.0/{creation_id}"
        params = {"fields": "status_code"}
        
        logger.info(f"Instagram upload Step 4: Polling processing status for container {creation_id}...")
        for i in range(12):
            time.sleep(5)
            status_res = requests.get(status_url, headers=headers, params=params, timeout=15)
            if status_res.status_code == 200:
                status_code = status_res.json().get("status_code")
                logger.info(f"Poll check {i+1}: Container status is '{status_code}'")
                if status_code == "FINISHED":
                    break
                elif status_code in ["EXPIRED", "ERROR"]:
                    raise Exception(f"Instagram video processing failed with status '{status_code}': {status_res.json()}")
            else:
                logger.warning(f"Poll check {i+1}: status check HTTP code is {status_res.status_code}")
        else:
            raise Exception("Instagram Reels video processing timed out on Facebook servers.")

        pub_url = f"https://graph.facebook.com/v18.0/{ig_user_id}/media_publish"
        pub_body = {"creation_id": creation_id}
        
        logger.info("Instagram upload Step 5: Publishing container live as Instagram Reel...")
        pub_res = requests.post(pub_url, headers=headers, json=pub_body, timeout=30)
        pub_res.raise_for_status()
        media_id = pub_res.json().get("id")
        
        logger.success(f"Instagram Reel published successfully! Media ID: {media_id}")
        return {"success": True, "media_id": media_id}
    except Exception as e:
        logger.error(f"Instagram Graph Reels publishing failed: {e}")
        raise e
