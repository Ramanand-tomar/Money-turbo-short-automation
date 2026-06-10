import os
from datetime import datetime, timezone
import json
import threading
from loguru import logger
from apscheduler.schedulers.background import BackgroundScheduler
from app.services import db
import app.utils.utils as utils

scheduler = None

def get_task_video_path(task_id: str) -> str:
    """
    Resolve the video file path for a given task_id.

    Search order:
      1. storage/tasks/{user_id}/{task_id}/  — current per-user layout
      2. storage/tasks/global/{task_id}/    — tasks created before user scoping
      3. output/{task_id}/                  — legacy flat layout

    Raises an Exception if no video file is found in any location.
    """
    import glob

    # Look up the task's owner from the database so we can check the correct subdirectory.
    task_user_id = "global"
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        if db.IS_POSTGRES:
            cursor.execute("SELECT user_id FROM tasks WHERE task_id = %s LIMIT 1", (task_id,))
        else:
            cursor.execute("SELECT user_id FROM tasks WHERE task_id = ? LIMIT 1", (task_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            task_user_id = (row[0] if db.IS_POSTGRES else row["user_id"]) or "global"
    except Exception as db_err:
        logger.warning(f"Could not query user_id for task {task_id} from DB: {db_err}")

    root = utils.root_dir()
    candidate_dirs = [
        os.path.join(root, "storage", "tasks", task_user_id, task_id),
        os.path.join(root, "storage", "tasks", "global", task_id),
        os.path.join(root, "output", task_id),
    ]

    for d in candidate_dirs:
        video_path = os.path.join(d, "final-1.mp4")
        if os.path.exists(video_path):
            return video_path
        # Fall back to any .mp4 in this directory
        mp4_files = glob.glob(os.path.join(d, "*.mp4"))
        if mp4_files:
            return mp4_files[0]

    raise Exception(
        f"Compiled video file not found for task {task_id} "
        f"(user_id={task_user_id}). Searched: {candidate_dirs}"
    )


def generate_viral_caption_via_llm(video_subject: str, script: str = None, user_id: str = "global") -> str:
    try:
        from app.services import llm
        prompt = (
            f"Write a short, engaging, viral social media caption with relevant hashtags (max 3-5 hashtags) "
            f"for a video about: '{video_subject}'."
        )
        if script:
            prompt += f" Incorporate the theme of this script: '{script[:300]}'"
        prompt += " Keep it under 150 characters, punchy and clickable. Output ONLY the caption and hashtags."
        
        caption = llm.generate_script(video_subject=prompt, user_id=user_id)
        if caption and caption.strip():
            return caption.strip()
    except Exception as e:
        logger.warning(f"Failed to generate LLM caption: {e}. Falling back to default.")
    
    return f"{video_subject} #shorts #viral #motivation"

def perform_post_upload(post: dict):
    post_id = post["id"]
    task_id = post["task_id"]
    user_id = post["user_id"]
    platform = post["platform"].lower()
    
    logger.info(f"Scheduler worker starting upload for post {post_id} (Task: {task_id}, Platform: {platform}, User: {user_id})")
    
    try:
        db.update_scheduled_post(post_id, "publishing", "Upload starting in background...")
        
        conn = db.get_connection()
        cursor = conn.cursor()
        if db.IS_POSTGRES:
            cursor.execute("SELECT params, script, terms FROM tasks WHERE task_id = %s", (task_id,))
        else:
            cursor.execute("SELECT params, script, terms FROM tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise Exception(f"Task {task_id} not found in database.")
            
        if db.IS_POSTGRES:
            params_str, script, terms = row[0], row[1], row[2]
        else:
            params_str, script, terms = row["params"], row["script"], row["terms"]
            
        params = {}
        if params_str:
            try:
                params = json.loads(params_str)
            except Exception:
                pass
                
        video_path = get_task_video_path(task_id)
        video_subject = params.get("video_subject") or "SaaS Auto Short"
        caption = generate_viral_caption_via_llm(video_subject, script, user_id)
        
        if platform == "youtube" or platform == "youtube_shorts":
            from youtube_uploader import get_authenticated_service, upload_video
            youtube = get_authenticated_service(user_id=user_id)
            description = f"{caption}\n\nGenerated via Turbo Studio."
            res = upload_video(
                file_path=video_path,
                title=video_subject[:95],
                description=description,
                tags=["shorts", "motivation", "viral"],
                privacy_status="public",
                user_id=user_id
            )
            db.update_scheduled_post(post_id, "published", json.dumps({"status": "success", "platform_response": res}))
            db.log_usage(user_id, task_id, "youtube_publish")
            
            conn = db.get_connection()
            cursor = conn.cursor()
            if db.IS_POSTGRES:
                cursor.execute("UPDATE tasks SET youtube_uploaded = 1 WHERE task_id = %s", (task_id,))
            else:
                cursor.execute("UPDATE tasks SET youtube_uploaded = 1 WHERE task_id = ?", (task_id,))
            conn.commit()
            conn.close()
            
        elif platform == "tiktok":
            import tiktok_uploader
            res = tiktok_uploader.upload_video(
                user_id=user_id,
                file_path=video_path,
                caption=caption
            )
            db.update_scheduled_post(post_id, "published", json.dumps({"status": "success", "platform_response": res}))
            db.log_usage(user_id, task_id, "tiktok_publish")
            
        elif platform == "instagram" or platform == "instagram_reels":
            import instagram_uploader
            res = instagram_uploader.upload_video(
                user_id=user_id,
                file_path=video_path,
                caption=caption
            )
            db.update_scheduled_post(post_id, "published", json.dumps({"status": "success", "platform_response": res}))
            db.log_usage(user_id, task_id, "instagram_publish")
            
        else:
            raise Exception(f"Unsupported scheduling platform: {platform}")
            
        logger.success(f"Scheduler successfully published post {post_id} to {platform}.")
        
    except Exception as exc:
        logger.error(f"Scheduler failed to publish post {post_id}: {exc}")
        db.update_scheduled_post(post_id, "failed", json.dumps({"error": str(exc)}))

def check_scheduled_posts():
    try:
        due_posts = db.get_due_scheduled_posts()
        if due_posts:
            logger.info(f"Scheduler detected {len(due_posts)} due scheduled posts to publish.")
            for post in due_posts:
                t = threading.Thread(target=perform_post_upload, args=(post,), daemon=True)
                t.start()
    except Exception as e:
        logger.error(f"Error in scheduler check loop: {e}")

def start_scheduler():
    global scheduler
    if scheduler is not None:
        logger.warning("Scheduler is already running.")
        return
        
    logger.info("Initializing APScheduler BackgroundScheduler...")
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_scheduled_posts, 'interval', seconds=60, id='check_scheduled_posts_job')
    scheduler.start()
    logger.success("APScheduler started successfully. Scheduled posts monitor active.")

def shutdown_scheduler():
    global scheduler
    if scheduler is not None:
        logger.info("Shutting down APScheduler...")
        scheduler.shutdown(wait=False)
        scheduler = None
        logger.success("APScheduler shut down successfully.")
