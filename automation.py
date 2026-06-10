import os
import sys
import json
import re

# Force add current directory to python path so imports resolve cleanly
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from loguru import logger
from app.models.schema import VideoParams
from app.services.task import start
from app.services.llm import _generate_response
from app.utils import utils
import youtube_uploader

# Automation Configuration
VIRAL_SUBJECTS_COUNT = 5
PRIVACY_STATUS = "public"  # "public" for standard uploads, "private" or "unlisted" for testing
DEFAULT_VOICE = "en-US-AndrewNeural"
DEFAULT_FONT = "UTM Kabel KT.ttf"

def generate_viral_topics(count=5):
    logger.info("Generating viral motivational subjects using Gemini...")
    prompt = f"""
    Generate {count} highly engaging, extremely viral short video subjects for motivational and self-improvement YouTube Shorts.
    Each subject should be a short, highly-clickable curiosity hook (e.g. "Why Silent People Are Dangerous", "The 1% Rule You Never Heard Of").
    Keep subjects under 50 characters and in English.
    You must return only a raw JSON list of strings. Do not include markdown blocks, code formatting, or other text.
    Example output format:
    ["Subject 1", "Subject 2", "Subject 3", "Subject 4", "Subject 5"]
    """
    
    response = _generate_response(prompt)
    
    try:
        # Strip potential markdown formatting if returned by the LLM
        cleaned_response = response.strip()
        if cleaned_response.startswith("```"):
            lines = cleaned_response.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned_response = "\n".join(lines).strip()
            
        subjects = json.loads(cleaned_response)
        if isinstance(subjects, list) and len(subjects) > 0:
            logger.success(f"Successfully generated {len(subjects)} subjects: {subjects}")
            return subjects[:count]
    except Exception as e:
        logger.warning(f"Failed to parse LLM response as JSON: {e}. Falling back to default list.")
        
    # Standard high-performing fallback list
    fallback_subjects = [
        "The Power of the 1% Rule",
        "Why Silent People are Dangerous",
        "How to Build Unshakeable Self-Discipline",
        "Stop Wasting Your Morning Routine",
        "The Secrets of Mental Toughness"
    ]
    return fallback_subjects[:count]

def run_daily_automation():
    logger.info("Starting Daily Motivational Video Automation Pipeline...")
    
    # 1. Generate viral topics
    topics = generate_viral_topics(VIRAL_SUBJECTS_COUNT)
    
    success_count = 0
    
    for idx, topic in enumerate(topics):
        logger.info(f"\n========================================\n"
                    f"PROCESSING VIDEO {idx+1}/{len(topics)}: '{topic}'\n"
                    f"========================================")
        
        task_id = utils.get_uuid()
        
        # Configure video parameters
        params = VideoParams(
            video_subject=topic,
            video_aspect="9:16",
            video_clip_duration=3,
            video_source="pexels",
            voice_name=DEFAULT_VOICE,
            font_name=DEFAULT_FONT,
            text_fore_color="#FFD700",  # Gold/Yellow text
            stroke_color="#000000",      # Black outline
            bgm_type="random",
            bgm_volume=0.15,
            voice_volume=1.0,
            subtitle_enabled=True,
            video_language="en",
            video_script_prompt="Create a highly engaging, emotional and punchy motivational transcript. Emphasize keywords. Keep sentences very short."
        )
        
        try:
            # 2. Generate video
            logger.info(f"Generating video for topic: {topic}")
            result = start(task_id, params, stop_at="video", enable_auto_upload=False)
            
            if not result or "videos" not in result or not result["videos"]:
                logger.error(f"Video generation failed for: {topic}")
                continue
                
            video_path = result["videos"][0]
            logger.success(f"Video compiled successfully at: {video_path}")
            
            # 3. Upload to YouTube
            title = f"{topic} | Mindset Motivation #shorts #motivation #viral"
            if len(title) > 100:
                title = title[:95] + "..."
                
            description = (
                f"Boost your daily mindset with this quick motivation short!\n\n"
                f"Topic: {topic}\n"
                f"Subscribe for daily self-improvement insights and build unshakeable discipline.\n\n"
                f"#motivation #mindset #shorts #discipline #viral #success"
            )
            
            tags = ["shorts", "motivation", "viral", "inspiration", "mindset", "success", "discipline"]
            
            logger.info(f"Uploading video to YouTube: '{title}'...")
            upload_result = youtube_uploader.upload_video(
                file_path=video_path,
                title=title,
                description=description,
                tags=tags,
                privacy_status=PRIVACY_STATUS
            )
            
            if upload_result:
                logger.success(f"Video '{topic}' successfully uploaded to YouTube!")
                success_count += 1
            else:
                logger.error(f"YouTube upload failed for: {topic}")
                
        except Exception as e:
            logger.exception(f"Exception occurred while processing video '{topic}': {e}")
            
    logger.info(f"Pipeline complete! Successfully generated and uploaded {success_count}/{len(topics)} videos.")

if __name__ == "__main__":
    run_daily_automation()
