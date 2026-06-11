import math
import os.path
import re
from os import path

from loguru import logger

from app.config import config
from app.models import const
from app.models.schema import VideoConcatMode, VideoParams
from app.services import llm, material, subtitle, video, voice, upload_post
from app.services import state as sm
from app.utils import utils


def generate_script(task_id, params, user_id="global"):
    logger.info("\n\n## generating video script")
    video_script = params.video_script.strip()
    if not video_script:
        video_script = llm.generate_script(
            video_subject=params.video_subject,
            language=params.video_language,
            paragraph_number=params.paragraph_number,
            video_script_prompt=params.video_script_prompt,
            custom_system_prompt=params.custom_system_prompt,
            video_duration=getattr(params, "video_duration", 30),
            user_id=user_id,
            prompt_mode=getattr(params, "prompt_mode", "viral_shorts"),
            target_platform=getattr(params, "target_platform", "youtube_shorts"),
            emotional_tone=getattr(params, "emotional_tone", "inspiring"),
            trend_context=getattr(params, "trend_context", ""),
        )
    else:
        logger.debug(f"video script: \n{video_script}")

    if not video_script:
        sm.state.update_task(task_id, state=const.TASK_STATE_FAILED)
        logger.error("failed to generate video script.")
        return None

    if getattr(params, "emoji_subtitles", False) and "Error: " not in video_script:
        video_script = llm.inject_emojis_into_script(video_script, user_id=user_id)
        params.video_script = video_script


    # Auto-score in the background (non-blocking)
    import threading
    def run_autoscore():
        try:
            from app.services import db
            scores = llm.score_script_virality(video_script, user_id=user_id)
            platform = getattr(params, "target_platform", "youtube_shorts")
            db.save_viral_score(script=video_script, platform=platform, scores=scores, task_id=task_id)
            logger.info(f"Auto-scored generated script for task {task_id}")
        except Exception as score_err:
            logger.error(f"Failed to auto-score generated script for task {task_id}: {score_err}")

    threading.Thread(target=run_autoscore, daemon=True).start()

    return video_script


def generate_terms(task_id, params, video_script, user_id="global"):
    logger.info("\n\n## generating video terms")
    video_terms = params.video_terms
    if not video_terms:
        video_terms = llm.generate_terms(
            video_subject=params.video_subject, video_script=video_script, amount=5, user_id=user_id
        )
    else:
        if isinstance(video_terms, str):
            video_terms = [term.strip() for term in re.split(r"[,，]", video_terms)]
        elif isinstance(video_terms, list):
            video_terms = [term.strip() for term in video_terms]
        else:
            raise ValueError("video_terms must be a string or a list of strings.")

        logger.debug(f"video terms: {utils.to_json(video_terms)}")

    if not video_terms:
        sm.state.update_task(task_id, state=const.TASK_STATE_FAILED)
        logger.error("failed to generate video terms.")
        return None

    return video_terms


def save_script_data(task_id, video_script, video_terms, params, user_id="global"):
    script_file = path.join(utils.task_dir(task_id, user_id), "script.json")
    script_data = {
        "script": video_script,
        "search_terms": video_terms,
        "params": params,
    }

    with open(script_file, "w", encoding="utf-8") as f:
        f.write(utils.to_json(script_data))


def generate_audio(task_id, params, video_script, user_id="global"):
    '''
    Generate audio for the video script.
    If a custom audio file is provided, it will be used directly.
    There will be no subtitle maker object returned in this case.
    Otherwise, TTS will be used to generate the audio.
    Returns:
        - audio_file: path to the generated or provided audio file
        - audio_duration: duration of the audio in seconds
        - sub_maker: subtitle maker object if TTS is used, None otherwise
    '''
    logger.info("\n\n## generating audio")
    # /audio 和 /subtitle 请求模型不包含 custom_audio_file，
    # 这里统一做兼容读取，避免直调接口时抛属性错误。
    custom_audio_file = getattr(params, "custom_audio_file", None)
    if not custom_audio_file or not os.path.exists(custom_audio_file):
        if custom_audio_file:
            logger.warning(
                f"custom audio file not found: {custom_audio_file}, using TTS to generate audio."
            )
        else:
            logger.info("no custom audio file provided, using TTS to generate audio.")
        audio_file = path.join(utils.task_dir(task_id, user_id), "audio.mp3")
        sub_maker = voice.tts(
            text=video_script,
            voice_name=voice.parse_voice_name(params.voice_name),
            voice_rate=params.voice_rate,
            voice_file=audio_file,
            user_id=user_id,
        )
        if sub_maker is None:
            sm.state.update_task(task_id, state=const.TASK_STATE_FAILED)
            logger.error(
                """failed to generate audio:
1. check if the language of the voice matches the language of the video script.
2. check if the network is available. If you are in China, it is recommended to use a VPN and enable the global traffic mode.
            """.strip()
            )
            return None, None, None
        audio_duration = math.ceil(voice.get_audio_duration(sub_maker))
        if audio_duration == 0:
            sm.state.update_task(task_id, state=const.TASK_STATE_FAILED)
            logger.error("failed to get audio duration.")
            return None, None, None
        return audio_file, audio_duration, sub_maker
    else:
        logger.info(f"using custom audio file: {custom_audio_file}")
        audio_duration = voice.get_audio_duration(custom_audio_file)
        if audio_duration == 0:
            sm.state.update_task(task_id, state=const.TASK_STATE_FAILED)
            logger.error("failed to get audio duration from custom audio file.")
            return None, None, None
        return custom_audio_file, audio_duration, None

def generate_subtitle(task_id, params, video_script, sub_maker, audio_file, user_id="global"):
    '''
    Generate subtitle for the video script.
    If subtitle generation is disabled or no subtitle maker is provided, it will return an empty string.
    Otherwise, it will generate the subtitle using the specified provider.
    Returns:
        - subtitle_path: path to the generated subtitle file
    '''
    logger.info("\n\n## generating subtitle")
    if not params.subtitle_enabled or sub_maker is None:
        return ""

    subtitle_path = path.join(utils.task_dir(task_id, user_id), "subtitle.srt")
    subtitle_provider = config.app.get("subtitle_provider", "edge").strip().lower()
    logger.info(f"\n\n## generating subtitle, provider: {subtitle_provider}")

    subtitle_fallback = False
    if subtitle_provider == "edge":
        voice.create_subtitle(
            text=video_script, sub_maker=sub_maker, subtitle_file=subtitle_path
        )
        if not os.path.exists(subtitle_path):
            subtitle_fallback = True
            logger.warning("subtitle file not found, fallback to whisper")

    if subtitle_provider == "whisper" or subtitle_fallback:
        subtitle.create(audio_file=audio_file, subtitle_file=subtitle_path)
        logger.info("\n\n## correcting subtitle")
        subtitle.correct(subtitle_file=subtitle_path, video_script=video_script)

    subtitle_lines = subtitle.file_to_subtitles(subtitle_path)
    if not subtitle_lines:
        logger.warning(f"subtitle file is invalid: {subtitle_path}")
        return ""

    return subtitle_path


def get_video_materials(task_id, params, video_terms, audio_duration, user_id="global"):
    if params.video_source == "local":
        logger.info("\n\n## preprocess local materials")
        materials = video.preprocess_video(
            materials=params.video_materials, clip_duration=params.video_clip_duration
        )
        if not materials:
            sm.state.update_task(task_id, state=const.TASK_STATE_FAILED)
            logger.error(
                "no valid materials found, please check the materials and try again."
            )
            return None
        return [material_info.url for material_info in materials]
    else:
        logger.info(f"\n\n## downloading videos from {params.video_source}")
        downloaded_videos = material.download_videos(
            task_id=task_id,
            search_terms=video_terms,
            source=params.video_source,
            video_aspect=params.video_aspect,
            video_contact_mode=params.video_concat_mode,
            audio_duration=audio_duration * params.video_count,
            max_clip_duration=params.video_clip_duration,
            user_id=user_id,
        )
        if not downloaded_videos:
            sm.state.update_task(task_id, state=const.TASK_STATE_FAILED)
            logger.error(
                "failed to download videos, maybe the network is not available. if you are in China, please use a VPN."
            )
            return None
        return downloaded_videos


def generate_final_videos(
    task_id, params, downloaded_videos, audio_file, subtitle_path, user_id="global"
):
    final_video_paths = []
    combined_video_paths = []
    video_concat_mode = (
        params.video_concat_mode if params.video_count == 1 else VideoConcatMode.random
    )
    video_transition_mode = params.video_transition_mode

    _progress = 50
    for i in range(params.video_count):
        index = i + 1
        combined_video_path = path.join(
            utils.task_dir(task_id, user_id), f"combined-{index}.mp4"
        )
        logger.info(f"\n\n## combining video: {index} => {combined_video_path}")
        video.combine_videos(
            combined_video_path=combined_video_path,
            video_paths=downloaded_videos,
            audio_file=audio_file,
            video_aspect=params.video_aspect,
            video_concat_mode=video_concat_mode,
            video_transition_mode=video_transition_mode,
            max_clip_duration=params.video_clip_duration,
            threads=params.n_threads,
            ken_burns=getattr(params, "ken_burns", True),
            beat_sync=getattr(params, "beat_sync", False),
        )

        _progress += 50 / params.video_count / 2
        sm.state.update_task(task_id, progress=_progress)

        final_video_path = path.join(utils.task_dir(task_id, user_id), f"final-{index}.mp4")

        logger.info(f"\n\n## generating video: {index} => {final_video_path}")
        video.generate_video(
            video_path=combined_video_path,
            audio_path=audio_file,
            subtitle_path=subtitle_path,
            output_file=final_video_path,
            params=params,
        )

        _progress += 50 / params.video_count / 2
        sm.state.update_task(task_id, progress=_progress)

        final_video_paths.append(final_video_path)
        combined_video_paths.append(combined_video_path)

    return final_video_paths, combined_video_paths


def start(task_id, params: VideoParams, stop_at: str = "video", enable_auto_upload: bool = True, user_id: str = "global"):
    logger.info(f"start task: {task_id} for user {user_id}, stop_at: {stop_at}")
    sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=5, status_message="Initializing video generation pipeline...", user_id=user_id)

    def check_stop_status():
        task = sm.state.get_task(task_id)
        if task and task.get("state") == 3:
            raise RuntimeError("Task execution paused/stopped by user.")

    try:
        check_stop_status()
        
        # 1. Generate script
        logger.info("Step 1: Generating video script...")
        sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, status_message="Generating video script...", user_id=user_id)
        video_script = generate_script(task_id, params, user_id=user_id)
        if not video_script or "Error: " in video_script:
            raise Exception("Failed to generate video script or encountered LLM error.")
        
        check_stop_status()
        sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=15, script=video_script, status_message="Video script generated.", user_id=user_id)

        if stop_at == "script":
            sm.state.update_task(
                task_id, state=const.TASK_STATE_COMPLETE, progress=100, script=video_script, user_id=user_id
            )
            return {"script": video_script}

        check_stop_status()
        
        # 2. Generate terms
        logger.info("Step 2: Generating search terms...")
        sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, status_message="Generating visual materials search terms...", user_id=user_id)
        video_terms = ""
        if params.video_source != "local":
            video_terms = generate_terms(task_id, params, video_script, user_id=user_id)
            if not video_terms:
                raise Exception("Failed to generate search terms from script.")
        
        check_stop_status()
        save_script_data(task_id, video_script, video_terms, params, user_id=user_id)
        sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=30, terms=video_terms, status_message="Search terms generated.", user_id=user_id)

        if stop_at == "terms":
            sm.state.update_task(
                task_id, state=const.TASK_STATE_COMPLETE, progress=100, script=video_script, terms=video_terms, user_id=user_id
            )
            return {"script": video_script, "terms": video_terms}

        check_stop_status()
        
        # 3. Generate audio
        logger.info("Step 3: Generating voiceover audio...")
        sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, status_message="Synthesizing voiceover audio...", user_id=user_id)
        audio_file, audio_duration, sub_maker = generate_audio(
            task_id, params, video_script, user_id=user_id
        )
        if not audio_file:
            raise Exception("Failed to generate TTS audio narration.")

        check_stop_status()
        sm.state.update_task(
            task_id, 
            state=const.TASK_STATE_PROCESSING, 
            progress=45, 
            audio_file=audio_file, 
            audio_duration=audio_duration,
            status_message="Voiceover audio generated.",
            user_id=user_id
        )

        if stop_at == "audio":
            sm.state.update_task(
                task_id,
                state=const.TASK_STATE_COMPLETE,
                progress=100,
                audio_file=audio_file,
                audio_duration=audio_duration,
                user_id=user_id
            )
            return {"audio_file": audio_file, "audio_duration": audio_duration}

        check_stop_status()
        
        # 4. Generate subtitle
        logger.info("Step 4: Creating subtitles...")
        sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, status_message="Generating subtitles alignment...", user_id=user_id)
        subtitle_path = generate_subtitle(
            task_id, params, video_script, sub_maker, audio_file, user_id=user_id
        )
        
        check_stop_status()
        sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=60, subtitle_path=subtitle_path, status_message="Subtitles generated.", user_id=user_id)

        if stop_at == "subtitle":
            sm.state.update_task(
                task_id,
                state=const.TASK_STATE_COMPLETE,
                progress=100,
                subtitle_path=subtitle_path,
                user_id=user_id
            )
            return {"subtitle_path": subtitle_path}

        check_stop_status()
        
        # 5. Get video materials
        logger.info("Step 5: Fetching video materials...")
        sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, status_message="Downloading visual stock clips from Pexels...", user_id=user_id)
        downloaded_videos = get_video_materials(
            task_id, params, video_terms, audio_duration, user_id=user_id
        )
        if not downloaded_videos:
            raise Exception("Failed to acquire video background materials.")

        check_stop_status()
        sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=75, materials=downloaded_videos, status_message="Visual stock clips downloaded.", user_id=user_id)

        if stop_at == "materials":
            sm.state.update_task(
                task_id,
                state=const.TASK_STATE_COMPLETE,
                progress=100,
                materials=downloaded_videos,
                user_id=user_id
            )
            return {"materials": downloaded_videos}

        check_stop_status()
        
        # 6. Generate final videos
        logger.info("Step 6: Processing video transitions & rendering...")
        if type(params.video_concat_mode) is str:
            params.video_concat_mode = VideoConcatMode(params.video_concat_mode)

        sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, status_message="Stitching final video & rendering subtitles via FFmpeg...", user_id=user_id)
        final_video_paths, combined_video_paths = generate_final_videos(
            task_id, params, downloaded_videos, audio_file, subtitle_path, user_id=user_id
        )

        if not final_video_paths:
            raise Exception("Failed to render and stitch final compiled video.")

        check_stop_status()
        sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=90, videos=final_video_paths, combined_videos=combined_video_paths, status_message="Video rendering finished.", user_id=user_id)
        logger.success(f"Task {task_id} generated final local video files successfully.")

        check_stop_status()
        
        # 7. Cloudinary cloud uploading
        logger.info("Step 7: Uploading generated video to Cloudinary...")
        from app.services.cloudinary_service import upload_to_cloudinary
        cloudinary_url = ""
        cloudinary_public_id = ""
        try:
            sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, status_message="Uploading generated video to Cloud CDN...", user_id=user_id)
            cloudinary_res = upload_to_cloudinary(final_video_paths[0], user_id=user_id)
            if cloudinary_res:
                cloudinary_url = cloudinary_res.get("url", "")
                cloudinary_public_id = cloudinary_res.get("public_id", "")
        except Exception as cloud_err:
            logger.warning(f"Non-fatal error uploading to Cloudinary: {cloud_err}")
            
        check_stop_status()
        sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=95, cloudinary_url=cloudinary_url, status_message="Cloud CDN upload finished.", user_id=user_id)

        check_stop_status()
        
        # 8. Auto-upload to connected YouTube channel
        logger.info("Step 8: Checking YouTube publishing status...")
        from app.services import db
        youtube_creds = db.get_youtube_credentials(user_id=user_id)
        
        youtube_uploaded_status = 0
        sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, status_message="Uploading/publishing video directly to YouTube channel...", user_id=user_id)
        if enable_auto_upload and youtube_creds:
            logger.info("Auto-upload is enabled and connected channel found. Initializing YouTube upload...")
            try:
                from youtube_uploader import upload_video
                title = params.video_subject or "Compiled Short Video"
                description = f"#shorts #motivation #viral\nGenerated via Turbo Studio SaaS\nSubject: {title}"
                upload_video(
                    file_path=final_video_paths[0],
                    title=title,
                    description=description,
                    tags=["shorts", "motivation", "viral"],
                    privacy_status="public",
                    user_id=user_id,
                )
                logger.info(f"✅ Auto-uploaded directly to YouTube: {final_video_paths[0]}")
                youtube_uploaded_status = 1
                
                # Cleanup Storage (Cloudinary and Local)
                logger.info("Cleaning up file storage after successful YouTube upload...")
                if cloudinary_public_id:
                    from app.services.cloudinary_service import delete_from_cloudinary
                    delete_from_cloudinary(cloudinary_public_id, user_id=user_id)
                    cloudinary_url = "" # Cleared after deletion
                
                import shutil
                task_dir_path = utils.task_dir(task_id, user_id)
                if os.path.exists(task_dir_path):
                    shutil.rmtree(task_dir_path, ignore_errors=True)
                    logger.info(f"Local file storage removed: {task_dir_path}")

            except Exception as yt_err:
                logger.error(f"⚠️ YouTube auto-publishing failed: {yt_err}")

        # Final complete step
        kwargs = {
            "videos": final_video_paths,
            "combined_videos": combined_video_paths,
            "script": video_script,
            "terms": video_terms,
            "audio_file": audio_file,
            "audio_duration": audio_duration,
            "subtitle_path": subtitle_path,
            "materials": downloaded_videos,
            "cloudinary_url": cloudinary_url,
            "cross_post_results": None,
            "youtube_uploaded": youtube_uploaded_status,
        }
        sm.state.update_task(
            task_id, state=const.TASK_STATE_COMPLETE, progress=100, status_message="SaaS Video Pipeline completed successfully!", user_id=user_id, **kwargs
        )
        
        # Send successful run report email
        try:
            from app.services.email_service import send_pipeline_email
            send_pipeline_email(
                task_id=task_id,
                state=const.TASK_STATE_COMPLETE,
                progress=100,
                subject=params.video_subject,
                status_msg="SaaS Video Pipeline completed successfully!",
                cdn_url=cloudinary_url,
                user_id=user_id
            )
        except Exception as mail_err:
            logger.error(f"Failed to send success email notification: {mail_err}")

        return kwargs

    except Exception as e:
        # Check if the task was explicitly stopped/paused by the user
        task = sm.state.get_task(task_id)
        if task and task.get("state") == 3:
            logger.info(f"Task {task_id} execution aborted cleanly because it was stopped/paused by user.")
            return None

        logger.error(f"Task {task_id} failed in start pipeline: {e}")
        sm.state.update_task(
            task_id,
            state=const.TASK_STATE_FAILED,
            error_message=str(e),
            status_message=f"Pipeline error: {str(e)}",
            user_id=user_id
        )

        # Send failure email notification
        try:
            from app.services.email_service import send_pipeline_email
            subject_val = getattr(params, "video_subject", "")
            send_pipeline_email(
                task_id=task_id,
                state=const.TASK_STATE_FAILED,
                progress=0,
                subject=subject_val,
                status_msg=f"Pipeline error: {str(e)}",
                error_msg=str(e),
                user_id=user_id
            )
        except Exception as mail_err:
            logger.error(f"Failed to send failure email notification: {mail_err}")

        return None



if __name__ == "__main__":
    task_id = "task_id"
    params = VideoParams(
        video_subject="金钱的作用",
        voice_name="zh-CN-XiaoyiNeural-Female",
        voice_rate=1.0,
    )
    start(task_id, params, stop_at="video")