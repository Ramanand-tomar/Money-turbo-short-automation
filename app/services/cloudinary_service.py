import os
from loguru import logger
from app.services import db

def upload_to_cloudinary(file_path: str, resource_type: str = "video", user_id: str = "global") -> str:
    """
    Upload a local file to Cloudinary and return its secure URL.
    Fetches settings dynamically from NeonDB/SQLite scoped to user_id.
    """
    if not os.path.exists(file_path):
        logger.error(f"Local file does not exist for Cloudinary upload: {file_path}")
        return ""

    # Try parsing CLOUDINARY_URL first
    cloudinary_url = db.get_setting("cloudinary_url", user_id=user_id) or os.getenv("CLOUDINARY_URL")
    
    cloud_name = None
    api_key = None
    api_secret = None

    if cloudinary_url and cloudinary_url.startswith("cloudinary://"):
        try:
            # Format: cloudinary://api_key:api_secret@cloud_name
            content = cloudinary_url[13:]
            if "@" in content:
                keys, cloud = content.split("@", 1)
                if ":" in keys:
                    k, s = keys.split(":", 1)
                    api_key = k
                    api_secret = s
                    cloud_name = cloud
        except Exception as parse_err:
            logger.warning(f"Failed to parse CLOUDINARY_URL: {parse_err}")

    # Fallback to individual settings/env vars if not set by CLOUDINARY_URL
    if not cloud_name:
        cloud_name = db.get_setting("cloudinary_cloud_name", user_id=user_id) or os.getenv("CLOUDINARY_CLOUD_NAME") or ""
    if not api_key:
        api_key = db.get_setting("cloudinary_api_key", user_id=user_id) or os.getenv("CLOUDINARY_API_KEY") or ""
    if not api_secret:
        api_secret = db.get_setting("cloudinary_api_secret", user_id=user_id) or os.getenv("CLOUDINARY_API_SECRET") or ""

    if not all([cloud_name, api_key, api_secret]):
        logger.warning(
            "Cloudinary credentials are not configured globally or in settings. "
            "Skipping cloud upload; returning local path."
        )
        return ""

    try:
        import cloudinary
        import cloudinary.uploader

        # Dynamically configure Cloudinary
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True
        )

        logger.info(f"Uploading {file_path} to Cloudinary ({resource_type})...")
        upload_result = cloudinary.uploader.upload(
            file_path,
            resource_type=resource_type,
            folder="money-printer-turbo"
        )
        secure_url = upload_result.get("secure_url")
        if secure_url:
            logger.success(f"Cloudinary upload completed successfully: {secure_url}")
            return secure_url
        else:
            logger.error("Cloudinary upload failed: no secure_url returned")
            return ""

    except Exception as e:
        logger.exception(f"Error during Cloudinary upload: {e}")
        return ""
