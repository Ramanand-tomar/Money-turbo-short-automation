import glob
import os
import pathlib
import shutil
from typing import Union

from fastapi import BackgroundTasks, Depends, Path, Query, Request, UploadFile, Response
from fastapi.params import File
from fastapi.responses import FileResponse, StreamingResponse, RedirectResponse, JSONResponse
from loguru import logger

from app.config import config
from app.controllers import base
from app.controllers.manager.base_manager import TaskQueueFullError
from app.controllers.manager.memory_manager import InMemoryTaskManager
from app.controllers.manager.redis_manager import RedisTaskManager
from app.controllers.v1.base import new_router
from app.models.exception import HttpException
from app.models.schema import (
    AudioRequest,
    BgmRetrieveResponse,
    BgmUploadResponse,
    SubtitleRequest,
    TaskDeletionResponse,
    TaskQueryRequest,
    TaskQueryResponse,
    TaskResponse,
    TaskVideoRequest,
    VideoMaterialUploadResponse,
    VideoMaterialRetrieveResponse,
    ScriptScoreRequest
)
from app.services import state as sm
from app.services import task as tm
from app.services import llm
from app.utils import file_security, utils

# Import the shared SlowAPI limiter instance from asgi
try:
    from app.asgi import limiter
except ImportError:
    # Fallback: create a no-op limiter if asgi hasn't initialised yet
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    limiter = Limiter(key_func=get_remote_address)

# 认证依赖项
# router = new_router(dependencies=[Depends(base.verify_token)])
router = new_router()

_enable_redis = config.app.get("enable_redis", False)
_redis_host = config.app.get("redis_host", "localhost")
_redis_port = config.app.get("redis_port", 6379)
_redis_db = config.app.get("redis_db", 0)
_redis_password = config.app.get("redis_password", None)

from app.services import db
_max_concurrent_tasks = int(db.get_setting("max_concurrent_tasks") or config.app.get("max_concurrent_tasks", 5))
_max_queued_tasks = int(db.get_setting("max_queued_tasks") or config.app.get("max_queued_tasks", 100))

redis_url = f"redis://:{_redis_password}@{_redis_host}:{_redis_port}/{_redis_db}"
# 根据配置选择合适的任务管理器
if _enable_redis:
    task_manager = RedisTaskManager(
        max_concurrent_tasks=_max_concurrent_tasks,
        redis_url=redis_url,
        max_queued_tasks=_max_queued_tasks,
    )
else:
    task_manager = InMemoryTaskManager(
        max_concurrent_tasks=_max_concurrent_tasks,
        max_queued_tasks=_max_queued_tasks,
    )


def _sanitize_upload_filename(filename: str, request_id: str) -> str:
    # 浏览器或客户端有时会附带目录信息，甚至可能夹带 ../ 这类穿越片段。
    # 这里只保留纯文件名，避免上传接口把文件写到目标目录之外。
    normalized_name = (filename or "").replace("\\", "/").split("/")[-1].strip()
    if not normalized_name or normalized_name in {".", ".."}:
        raise HttpException(
            task_id=request_id,
            status_code=400,
            message=f"{request_id}: invalid filename",
        )
    return normalized_name


def _resolve_path_within_directory(base_dir: str, unsafe_path: str, request_id: str) -> str:
    try:
        return file_security.resolve_path_within_directory(base_dir, unsafe_path)
    except ValueError as exc:
        logger.warning(
            f"reject unsafe file path, request_id: {request_id}, path: {unsafe_path}, "
            f"error: {str(exc)}"
        )
        raise HttpException(
            task_id=request_id,
            status_code=404 if str(exc) == "file does not exist" else 403,
            message=f"{request_id}: invalid file path",
        )

def _task_file_to_uri(file: str, endpoint: str, task_dir: str, request_id: str) -> str:
    if not isinstance(file, str):
        return file

    if file.startswith(("http://", "https://")):
        return file

    # Standardize separator
    normalized_file = file.replace("\\", "/")
    
    # Try resolving relative path based on possible roots
    storage_tasks_root = os.path.join(utils.root_dir(), "storage", "tasks").replace("\\", "/")
    output_root = os.path.join(utils.root_dir(), "output").replace("\\", "/")
    
    if normalized_file.startswith(storage_tasks_root):
        relative_path = os.path.relpath(file, storage_tasks_root).replace("\\", "/")
    elif normalized_file.startswith(output_root):
        relative_path = os.path.relpath(file, output_root).replace("\\", "/")
    else:
        try:
            resolved_path = file_security.resolve_path_within_directory(task_dir, file)
            relative_path = os.path.relpath(resolved_path, task_dir).replace("\\", "/")
        except ValueError:
            return file

    uri_path = f"api/v1/stream/{relative_path}"
    if endpoint:
        return f"{endpoint.rstrip('/')}/{uri_path}"
    return f"/{uri_path}"

def _get_user_id(request: Request) -> str:
    # Read from request.state.user_id, which ClerkAuthMiddleware always sets
    # for protected routes. Do NOT fall back to query params — that would allow
    # any caller to spoof their identity by appending ?user_id=<victim>.
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        # Should only reach here on exempt/public routes (health, ping).
        # Log a warning so we can catch misconfigured middleware early.
        logger.warning(
            f"request.state.user_id is missing for path '{request.url.path}'. "
            "Falling back to 'global'. Verify ClerkAuthMiddleware is active for this route."
        )
        user_id = "global"

    # Temp hook to log user_id to file
    try:
        temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))), "storage")
        os.makedirs(temp_dir, exist_ok=True)
        temp_file = os.path.join(temp_dir, "last_user_id.txt")
        with open(temp_file, "a") as tf:
            tf.write(user_id + "\n")
    except Exception:
        pass

    # Intercept and Sync YouTube credentials from client-side headers to NeonDB/SQLite
    yt_access_token = request.headers.get("X-YouTube-Access-Token")
    yt_refresh_token = request.headers.get("X-YouTube-Refresh-Token")
    yt_channel_name = request.headers.get("X-YouTube-Channel-Name")
    yt_channel_id = request.headers.get("X-YouTube-Channel-Id")
    
    if yt_access_token and yt_refresh_token and yt_channel_name and yt_channel_id:
        try:
            from app.services import db
            import urllib.parse
            clean_channel_name = urllib.parse.unquote(yt_channel_name.strip())
            db.save_youtube_credentials(
                channel_id=yt_channel_id.strip(),
                channel_name=clean_channel_name,
                access_token=yt_access_token.strip(),
                refresh_token=yt_refresh_token.strip(),
                token_expiry="",
                user_id=user_id
            )
            logger.info(f"Synchronized YouTube credentials from request headers for user {user_id}: {clean_channel_name}")
        except Exception as err:
            logger.warning(f"Failed to auto-sync YouTube credentials from request headers: {err}")

    return user_id

def _verify_task_and_get_path(request: Request, file_path: str, request_id: str) -> str:
    # Split the file path by /
    parts = [p for p in file_path.replace("\\", "/").split("/") if p]
    if len(parts) >= 2:
        if len(parts) >= 3:
            # Format: {user_id}/{task_id}/{filename...}
            file_user_id = parts[0]
            task_id = parts[1]
            filename = "/".join(parts[2:])
        else:
            # Format: {task_id}/{filename} (legacy or global)
            file_user_id = None
            task_id = parts[0]
            filename = parts[1]
    else:
        raise HttpException(
            task_id="",
            status_code=400,
            message="Invalid file path structure",
        )

    # Retrieve task from state to check owner
    task = sm.state.get_task(task_id)
    if not task:
        raise HttpException(
            task_id=task_id,
            status_code=404,
            message=f"{request_id}: task not found",
        )

    # Enforce task ownership verification
    request_user_id = _get_user_id(request)
    task_owner = task.get("user_id", "global")
    if task_owner != request_user_id and request_user_id != "global":
        raise HttpException(
            task_id=task_id,
            status_code=403,
            message=f"{request_id}: access denied",
        )

    # Build potential base directories to resolve path securely:
    new_base = os.path.join(utils.root_dir(), "storage", "tasks", task_owner, task_id)
    if os.path.exists(os.path.join(new_base, filename)):
        return _resolve_path_within_directory(new_base, filename, request_id)

    old_base = os.path.join(utils.root_dir(), "output", task_id)
    if os.path.exists(os.path.join(old_base, filename)):
        return _resolve_path_within_directory(old_base, filename, request_id)

    global_base = os.path.join(utils.root_dir(), "storage", "tasks", "global", task_id)
    if os.path.exists(os.path.join(global_base, filename)):
        return _resolve_path_within_directory(global_base, filename, request_id)

    raise HttpException(
        task_id=task_id,
        status_code=404,
        message=f"{request_id}: file not found on server",
    )



# ---------------------------------------------------------------------------
# Health Check Endpoint
# ---------------------------------------------------------------------------
@router.get("/health", summary="Health check — DB, Redis, LLM")
def health_check(request: Request):
    """
    Returns platform health status.
    Checks: database connectivity, Redis (if enabled), LLM provider configuration.
    """
    from app.services import db

    health = {
        "status": "ok",
        "db": "ok",
        "redis": "disabled",
        "llm": "unconfigured",
        "version": config.project_version,
    }
    status_code = 200

    # DB check
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        health["db"] = "ok"
    except Exception as e:
        health["db"] = f"error: {str(e)[:80]}"
        health["status"] = "degraded"
        status_code = 503

    # Redis check (only when enabled)
    if _enable_redis:
        try:
            import redis
            r = redis.from_url(redis_url, socket_connect_timeout=2)
            r.ping()
            health["redis"] = "ok"
        except Exception as e:
            health["redis"] = f"error: {str(e)[:80]}"
            health["status"] = "degraded"
            status_code = 503
    else:
        health["redis"] = "disabled"

    # LLM provider check (just confirm a key/model is configured)
    try:
        llm_provider = db.get_setting("llm_provider", user_id="global") or config.app.get("llm_provider", "")
        api_key = db.get_setting("openai_api_key", user_id="global") or config.app.get("openai_api_key", "")
        if llm_provider or api_key:
            health["llm"] = f"configured ({llm_provider or 'openai-compatible'})"
        else:
            health["llm"] = "unconfigured"
    except Exception as e:
        health["llm"] = f"error: {str(e)[:80]}"

    return JSONResponse(status_code=status_code, content=health)


@router.post("/videos", response_model=TaskResponse, summary="Generate a short video")
@limiter.limit("10/minute")
def create_video(
    background_tasks: BackgroundTasks, request: Request, body: TaskVideoRequest, response: Response
):
    return create_task(request, body, stop_at="video", response=response)


@router.post("/subtitle", response_model=TaskResponse, summary="Generate subtitle only")
@limiter.limit("30/minute")
def create_subtitle(
    background_tasks: BackgroundTasks, request: Request, body: SubtitleRequest, response: Response
):
    return create_task(request, body, stop_at="subtitle", response=response)


@router.post("/audio", response_model=TaskResponse, summary="Generate audio only")
@limiter.limit("30/minute")
def create_audio(
    background_tasks: BackgroundTasks, request: Request, body: AudioRequest, response: Response
):
    return create_task(request, body, stop_at="audio", response=response)


def create_task(
    request: Request,
    body: Union[TaskVideoRequest, SubtitleRequest, AudioRequest],
    stop_at: str,
    response: Response,
):
    task_id = utils.get_uuid()
    request_id = base.get_task_id(request)
    user_id = _get_user_id(request)

    # 1. Keyword Blocklist Check
    blocklist_str = db.get_platform_config("keyword_blocklist", "")
    keywords = [k.strip().lower() for k in blocklist_str.split(",") if k.strip()]
    subject = getattr(body, "video_subject", None)
    if subject and isinstance(subject, str):
        subject_lower = subject.lower()
        for kw in keywords:
            if kw in subject_lower:
                raise HttpException(
                    task_id="",
                    status_code=400,
                    message=f"Video subject contains blocked keyword: {kw}"
                )

    # 2. Daily Quota Check
    from datetime import datetime, timezone, timedelta
    now_utc = datetime.now(timezone.utc)
    next_midnight = (now_utc + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    reset_str = next_midnight.strftime("%Y-%m-%dT%H:%M:%SZ")

    user_info = db.get_user(user_id)
    if not user_info:
        quota_limit = 5
    else:
        quota_limit = user_info.get("quota_videos_per_day", 5)

    usage_today = db.get_usage_today(user_id)
    if usage_today >= quota_limit:
        return JSONResponse(
            status_code=429,
            headers={
                "X-Quota-Limit": str(quota_limit),
                "X-Quota-Remaining": "0",
                "X-Quota-Reset": reset_str
            },
            content={
                "status": 429,
                "message": "Daily video generation quota exceeded"
            }
        )

    try:
        task = {
            "task_id": task_id,
            "request_id": request_id,
            "params": body.model_dump(),
            "user_id": user_id,
        }
        sm.state.update_task(task_id, user_id=user_id)
        task_manager.add_task(tm.start, task_id=task_id, params=body, stop_at=stop_at, user_id=user_id)
        
        # Populate success headers
        response.headers["X-Quota-Limit"] = str(quota_limit)
        response.headers["X-Quota-Remaining"] = str(max(0, quota_limit - usage_today - 1))
        response.headers["X-Quota-Reset"] = reset_str

        # Log usage
        db.log_usage(user_id, task_id, f"create_{stop_at}")

        logger.success(f"Task created for user {user_id}: {utils.to_json(task)}")
        return utils.get_response(200, task)
    except TaskQueueFullError as e:
        sm.state.delete_task(task_id)
        logger.warning(
            f"reject task because queue is full, request_id: {request_id}, task_id: {task_id}"
        )
        raise HttpException(
            task_id=task_id, status_code=429, message=f"{request_id}: {str(e)}"
        )
    except ValueError as e:
        raise HttpException(
            task_id=task_id, status_code=400, message=f"{request_id}: {str(e)}"
        )


@router.get("/tasks", response_model=TaskQueryResponse, summary="Get all tasks")
def get_all_tasks(request: Request, page: int = Query(1, ge=1), page_size: int = Query(10, ge=1)):
    user_id = _get_user_id(request)
    tasks, total = sm.state.get_all_tasks(page, page_size, user_id=user_id)

    response = {
        "tasks": tasks,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
    return utils.get_response(200, response)


@router.get(
    "/tasks/{task_id}", response_model=TaskQueryResponse, summary="Query task status"
)
def get_task(
    request: Request,
    task_id: str = Path(..., description="Task ID"),
    query: TaskQueryRequest = Depends(),
):
    user_id = _get_user_id(request)
    request_id = base.get_task_id(request)
    endpoint = config.app.get("endpoint", "").rstrip("/")
    task = sm.state.get_task(task_id)
    if task:
        # Check task owner
        if task.get("user_id", "global") != user_id and user_id != "global":
            raise HttpException(
                task_id=task_id, status_code=403, message=f"{request_id}: access denied"
            )
        task_dir = utils.task_dir()
        response_task = dict(task)

        if "videos" in task:
            response_task["videos"] = [
                _task_file_to_uri(v, endpoint, task_dir, request_id)
                for v in task["videos"]
            ]
        if "combined_videos" in task:
            response_task["combined_videos"] = [
                _task_file_to_uri(v, endpoint, task_dir, request_id)
                for v in task["combined_videos"]
            ]
        return utils.get_response(200, response_task)

    raise HttpException(
        task_id=task_id, status_code=404, message=f"{request_id}: task not found"
    )


@router.delete(
    "/tasks/{task_id}",
    response_model=TaskDeletionResponse,
    summary="Delete a generated short video task",
)
def delete_video(request: Request, task_id: str = Path(..., description="Task ID")):
    user_id = _get_user_id(request)
    request_id = base.get_task_id(request)
    task = sm.state.get_task(task_id)
    if task:
        # Check task owner
        task_owner = task.get("user_id", "global")
        if task_owner != user_id and user_id != "global":
            raise HttpException(
                task_id=task_id, status_code=403, message=f"{request_id}: access denied"
            )

        # Resolve the correct per-user task directory, with legacy fallback.
        # New layout: storage/tasks/{user_id}/{task_id}/
        # Legacy layout: output/{task_id}/
        task_path_found = None
        candidate_new = os.path.join(utils.root_dir(), "storage", "tasks", task_owner, task_id)
        candidate_global = os.path.join(utils.root_dir(), "storage", "tasks", "global", task_id)
        candidate_legacy = os.path.join(utils.root_dir(), "output", task_id)

        for candidate in (candidate_new, candidate_global, candidate_legacy):
            if os.path.exists(candidate):
                task_path_found = candidate
                break

        if task_path_found:
            try:
                shutil.rmtree(task_path_found)
                logger.info(f"Removed task directory: {task_path_found}")
            except Exception as rmtree_err:
                logger.warning(f"Could not completely remove task directory {task_path_found}: {rmtree_err}")
        else:
            logger.warning(f"No on-disk directory found for task {task_id} (owner={task_owner}); skipping rmtree.")

        sm.state.delete_task(task_id)
        logger.success(f"video deleted: {utils.to_json(task)}")
        return utils.get_response(200)

    raise HttpException(
        task_id=task_id, status_code=404, message=f"{request_id}: task not found"
    )


@router.post(
    "/tasks/{task_id}/stop",
    summary="Stop/Pause a running pipeline task",
)
def stop_task(request: Request, task_id: str = Path(..., description="Task ID")):
    user_id = _get_user_id(request)
    request_id = base.get_task_id(request)
    task = sm.state.get_task(task_id)
    if task:
        # Check task owner
        if task.get("user_id", "global") != user_id and user_id != "global":
            raise HttpException(
                task_id=task_id, status_code=403, message=f"{request_id}: access denied"
            )
        sm.state.update_task(task_id, state=3)
        logger.info(f"Task {task_id} has been paused/stopped by user {user_id}.")
        return utils.get_response(200, {"message": "Task stopped successfully"})

    raise HttpException(
        task_id=task_id, status_code=404, message=f"{request_id}: task not found"
    )


@router.get(
    "/musics", response_model=BgmRetrieveResponse, summary="Retrieve local BGM files"
)
def get_bgm_list(request: Request):
    suffix = "*.mp3"
    song_dir = utils.song_dir()
    files = glob.glob(os.path.join(song_dir, suffix))
    bgm_list = []
    for file in files:
        filename = os.path.basename(file)
        bgm_list.append(
            {
                "name": filename,
                "size": os.path.getsize(file),
                # 只返回文件名，避免把服务器绝对路径暴露给调用方。
                # 服务端后续会把该文件名解析回 songs 白名单目录。
                "file": filename,
            }
        )
    response = {"files": bgm_list}
    return utils.get_response(200, response)


@router.post(
    "/musics",
    response_model=BgmUploadResponse,
    summary="Upload the BGM file to the songs directory",
)
def upload_bgm_file(request: Request, file: UploadFile = File(...)):
    request_id = base.get_task_id(request)
    safe_filename = _sanitize_upload_filename(file.filename, request_id)
    # check file ext
    if safe_filename.lower().endswith("mp3"):
        song_dir = utils.song_dir()
        save_path = os.path.join(song_dir, safe_filename)
        # save file
        with open(save_path, "wb+") as buffer:
            # If the file already exists, it will be overwritten
            file.file.seek(0)
            buffer.write(file.file.read())
        response = {"file": safe_filename}
        return utils.get_response(200, response)

    raise HttpException(
        "", status_code=400, message=f"{request_id}: Only *.mp3 files can be uploaded"
    )


@router.get(
    "/video_materials", response_model=VideoMaterialRetrieveResponse, summary="Retrieve local video materials"
)
def get_video_materials_list(request: Request):
    allowed_suffixes = ("mp4", "mov", "avi", "flv", "mkv", "jpg", "jpeg", "png")
    local_videos_dir = utils.storage_dir("local_videos", create=True)
    files = []
    for suffix in allowed_suffixes:
        files.extend(glob.glob(os.path.join(local_videos_dir, f"*.{suffix}")))
    # 文件系统枚举顺序不稳定，直接返回会导致“顺序拼接”在不同机器或不同
    # 时刻表现不一致。这里统一按文件名排序，至少保证服务端返回顺序可预测。
    files.sort(key=lambda file_path: os.path.basename(file_path).lower())
    video_materials_list = []
    for file in files:
        filename = os.path.basename(file)
        video_materials_list.append(
            {
                "name": filename,
                "size": os.path.getsize(file),
                # 与 BGM 一样，只返回文件名；创建任务时再在 local_videos
                # 白名单目录内解析，避免 API 泄露宿主机绝对路径。
                "file": filename,
            }
        )
    response = {"files": video_materials_list}
    return utils.get_response(200, response)


@router.post(
    "/video_materials",
    response_model=VideoMaterialUploadResponse,
    summary="Upload the video material file to the local videos directory",
)
def upload_video_material_file(request: Request, file: UploadFile = File(...)):
    request_id = base.get_task_id(request)
    safe_filename = _sanitize_upload_filename(file.filename, request_id)
    # check file ext
    allowed_suffixes = ("mp4", "mov", "avi", "flv", "mkv", "jpg", "jpeg", "png")
    normalized_filename = safe_filename.lower()
    # 统一按小写扩展名校验，兼容 .MOV 这类大写后缀文件。
    if normalized_filename.endswith(allowed_suffixes):
        local_videos_dir = utils.storage_dir("local_videos", create=True)
        save_path = os.path.join(local_videos_dir, safe_filename)
        # save file
        with open(save_path, "wb+") as buffer:
            # If the file already exists, it will be overwritten
            file.file.seek(0)
            buffer.write(file.file.read())
        response = {"file": safe_filename}
        return utils.get_response(200, response)

    raise HttpException(
        "", status_code=400, message=f"{request_id}: Only files with extensions {', '.join(allowed_suffixes)} can be uploaded"
    )


@router.get("/stream/{file_path:path}")
async def stream_video(request: Request, file_path: str):
    request_id = base.get_task_id(request)
    video_path = _verify_task_and_get_path(request, file_path, request_id)
    range_header = request.headers.get("Range")
    video_size = os.path.getsize(video_path)
    start, end = 0, video_size - 1

    length = video_size
    if range_header:
        range_ = range_header.split("bytes=")[1]
        start, end = [int(part) if part else None for part in range_.split("-")]
        if start is None:
            start = video_size - end
            end = video_size - 1
        if end is None:
            end = video_size - 1
        length = end - start + 1

    def file_iterator(file_path, offset=0, bytes_to_read=None):
        with open(file_path, "rb") as f:
            f.seek(offset, os.SEEK_SET)
            remaining = bytes_to_read or video_size
            while remaining > 0:
                bytes_to_read = min(4096, remaining)
                data = f.read(bytes_to_read)
                if not data:
                    break
                remaining -= len(data)
                yield data

    response = StreamingResponse(
        file_iterator(video_path, start, length), media_type="video/mp4"
    )
    response.headers["Content-Range"] = f"bytes {start}-{end}/{video_size}"
    response.headers["Accept-Ranges"] = "bytes"
    response.headers["Content-Length"] = str(length)
    response.status_code = 206  # Partial Content

    return response


@router.get("/download/{file_path:path}")
async def download_video(request: Request, file_path: str):
    """
    download video
    :param request: Request request
    :param file_path: video file path, eg: /cd1727ed-3473-42a2-a7da-4faafafec72b/final-1.mp4
    :return: video file
    """
    request_id = base.get_task_id(request)
    video_path = _verify_task_and_get_path(request, file_path, request_id)
    file_path_obj = pathlib.Path(video_path)
    filename = file_path_obj.stem
    extension = file_path_obj.suffix
    headers = {"Content-Disposition": f"attachment; filename={filename}{extension}"}
    return FileResponse(
        path=video_path,
        headers=headers,
        filename=f"{filename}{extension}",
        media_type=f"video/{extension[1:]}",
    )


@router.get("/settings", summary="Retrieve platform settings and active configurations")
def get_settings(request: Request):
    user_id = _get_user_id(request)
    from app.services import db
    user_info = db.get_user(user_id)
    quota_limit = user_info.get("quota_videos_per_day", 5) if user_info else 5
    usage_today = db.get_usage_today(user_id)

    return utils.get_response(200, {
        "gemini_api_key_configured": bool(db.get_setting("gemini_api_key", user_id=user_id)),
        "gemini_api_key_2_configured": bool(db.get_setting("gemini_api_key_2", user_id=user_id)),
        "gemini_api_key_3_configured": bool(db.get_setting("gemini_api_key_3", user_id=user_id)),
        "gemini_api_key_4_configured": bool(db.get_setting("gemini_api_key_4", user_id=user_id)),
        "gemini_api_key_5_configured": bool(db.get_setting("gemini_api_key_5", user_id=user_id)),
        "pexels_api_key_configured": bool(db.get_setting("pexels_api_key", user_id=user_id)),
        "azure_speech_key_configured": bool(db.get_setting("azure_speech_key", user_id=user_id)),
        "azure_speech_region": db.get_setting("azure_speech_region", user_id=user_id) or "",
        "sarvam_api_key_configured": bool(db.get_setting("sarvam_api_key", user_id=user_id)),
        "youtube_client_id_configured": bool(db.get_setting("youtube_client_id", user_id=user_id)),
        "cloudinary_url_configured": bool(db.get_setting("cloudinary_url", user_id=user_id)),
        "max_concurrent_tasks": int(db.get_setting("max_concurrent_tasks", user_id=user_id) or config.app.get("max_concurrent_tasks", 5)),
        "max_queued_tasks": int(db.get_setting("max_queued_tasks", user_id=user_id) or config.app.get("max_queued_tasks", 100)),
        "quota_videos_per_day": quota_limit,
        "usage_today": usage_today,
    })


@router.post("/settings", summary="Update platform settings dynamically in NeonDB")
def save_settings(request: Request, body: dict):
    user_id = _get_user_id(request)
    from app.services import db
    for key, val in body.items():
        if val is not None:
            is_placeholder = str(val).strip() in ["••••••••••••••••", ""]
            if is_placeholder:
                continue
            db.save_setting(key, str(val), user_id=user_id)

            if key == "max_concurrent_tasks":
                try:
                    task_manager.update_limits(max_concurrent=int(val), max_queued=task_manager.max_queued_tasks)
                except Exception as e:
                    logger.warning(f"Failed to update task manager concurrent limits: {e}")
            elif key == "max_queued_tasks":
                try:
                    task_manager.update_limits(max_concurrent=task_manager.max_concurrent_tasks, max_queued=int(val))
                except Exception as e:
                    logger.warning(f"Failed to update task manager queue limits: {e}")
            
            # Update global config for local run fallback
            if user_id == "global":
                if key == "gemini_api_key":
                    config.app["gemini_api_key"] = str(val)
                elif key == "gemini_api_key_2":
                    config.app["gemini_api_key_2"] = str(val)
                elif key == "gemini_api_key_3":
                    config.app["gemini_api_key_3"] = str(val)
                elif key == "gemini_api_key_4":
                    config.app["gemini_api_key_4"] = str(val)
                elif key == "gemini_api_key_5":
                    config.app["gemini_api_key_5"] = str(val)
                elif key == "pexels_api_key":
                    config.app["pexels_api_key"] = str(val)
                elif key == "azure_speech_key":
                    config.azure["speech_key"] = str(val)
                elif key == "azure_speech_region":
                    config.azure["speech_region"] = str(val)
                elif key == "sarvam_api_key":
                    config.app["sarvam_api_key"] = str(val)

    logger.success(f"SaaS dashboard settings saved dynamically for user {user_id}.")
    return utils.get_response(200, {"message": "Settings saved successfully"})


@router.get("/youtube/status", summary="Get YouTube integration status from NeonDB credentials")
def get_youtube_status(request: Request):
    user_id = _get_user_id(request)
    from app.services import db
    client_secret_exists = bool(db.get_setting("youtube_client_id", user_id=user_id)) or os.path.exists("client_secret.json") or bool(os.getenv("YOUTUBE_CLIENT_SECRET_JSON"))
    youtube_creds = db.get_youtube_credentials(user_id=user_id)
    
    return utils.get_response(200, {
        "client_secret_exists": client_secret_exists,
        "token_exists": youtube_creds is not None or (user_id == "global" and os.path.exists("token.json")),
        "channel_connected": youtube_creds is not None or (user_id == "global" and os.path.exists("token.json")),
        "channel_name": youtube_creds["channel_name"] if youtube_creds else "Connected via token.json" if (user_id == "global" and os.path.exists("token.json")) else ""
    })


@router.get("/youtube/connect", summary="Get browser-friendly Google OAuth link for YouTube channel connection")
def connect_youtube_oauth(request: Request, user_id: str = Query("global")):
    from youtube_uploader import get_web_flow
    redirect_uri = str(request.url_for("youtube_oauth_callback"))
    if "onrender.com" in redirect_uri:
        redirect_uri = redirect_uri.replace("http://", "https://")
    try:
        flow = get_web_flow(redirect_uri, user_id=user_id)
        flow.autogenerate_code_verifier = False
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
            state=user_id
        )
        return utils.get_response(200, {"auth_url": auth_url})
    except Exception as e:
        logger.error(f"Failed to generate OAuth auth url for user {user_id}: {e}")
        raise HttpException("", status_code=400, message=f"OAuth setup error: {str(e)}")


@router.get("/youtube/oauth-callback", summary="Receive Google OAuth authorization code and save channel tokens")
def youtube_oauth_callback(request: Request, code: str = Query(...), state: str = Query("global")):
    from youtube_uploader import get_web_flow, SCOPES, API_SERVICE_NAME, API_VERSION
    from googleapiclient.discovery import build
    from app.services import db
    
    redirect_uri = str(request.url_for("youtube_oauth_callback"))
    if "onrender.com" in redirect_uri:
        redirect_uri = redirect_uri.replace("http://", "https://")
    try:
        flow = get_web_flow(redirect_uri, user_id=state)
        flow.autogenerate_code_verifier = False
        flow.fetch_token(code=code)
        creds = flow.credentials
        
        youtube = build(API_SERVICE_NAME, API_VERSION, credentials=creds)
        channels_response = youtube.channels().list(part="snippet", mine=True).execute()
        
        if not channels_response or "items" not in channels_response or not channels_response["items"]:
            raise Exception("No active YouTube channels found for the authenticated Google account.")
            
        channel = channels_response["items"][0]
        channel_id = channel["id"]
        channel_name = channel["snippet"]["title"]
        
        db.save_youtube_credentials(
            channel_id=channel_id,
            channel_name=channel_name,
            access_token=creds.token,
            refresh_token=creds.refresh_token,
            token_expiry=str(creds.expiry),
            user_id=state
        )
        logger.success(f"Successfully connected YouTube channel for user {state}: {channel_name} (ID: {channel_id})")
        
        import urllib.parse
        encoded_channel_name = urllib.parse.quote(channel_name)
        
        base_url = str(request.base_url).rstrip("/")
        if "onrender.com" in base_url:
            base_url = base_url.replace("http://", "https://")
        elif "127.0.0.1" in base_url or "localhost" in base_url:
            base_url = "http://localhost:5173"
            
        return RedirectResponse(
            f"{base_url}/?tab=youtube"
            f"&user_id={state}"
            f"&youtube_access_token={creds.token}"
            f"&youtube_refresh_token={creds.refresh_token}"
            f"&youtube_channel_name={encoded_channel_name}"
            f"&youtube_channel_id={channel_id}"
        )
    except Exception as e:
        logger.error(f"YouTube callback processing error: {e}")
        import urllib.parse
        encoded_err = urllib.parse.quote(str(e))
        
        base_url = str(request.base_url).rstrip("/")
        if "onrender.com" in base_url:
            base_url = base_url.replace("http://", "https://")
        elif "127.0.0.1" in base_url or "localhost" in base_url:
            base_url = "http://localhost:5173"
            
        return RedirectResponse(f"{base_url}/?tab=youtube&error={encoded_err}")


@router.post("/youtube/connect", summary="Fallback post link to trigger old auth flow")
def connect_youtube(background_tasks: BackgroundTasks):
    return utils.get_response(200, {"message": "Please connect YouTube from the channel integration settings."})


@router.post("/automation/trigger", summary="Trigger daily automation script")
def trigger_automation(background_tasks: BackgroundTasks):
    import subprocess
    import sys
    def run_script():
        interpreter = sys.executable or ".venv/Scripts/python.exe"
        subprocess.run([interpreter, "automation.py"])
    background_tasks.add_task(run_script)
    return utils.get_response(200, {"message": "Automation triggered in background"})


@router.post("/youtube/upload-secret", summary="Upload client_secret.json directly")
def upload_client_secret(request: Request, file: UploadFile = File(...)):
    user_id = _get_user_id(request)
    request_id = base.get_task_id(request)
    safe_filename = _sanitize_upload_filename(file.filename, request_id)
    if safe_filename.lower().endswith(".json") or safe_filename.lower().endswith("json"):
        save_path = "client_secret.json"
        with open(save_path, "wb+") as buffer:
            file.file.seek(0)
            buffer.write(file.file.read())
        
        try:
            import json
            file.file.seek(0)
            data = json.loads(file.file.read().decode('utf-8'))
            client_id = None
            client_secret = None
            if "web" in data:
                client_id = data["web"].get("client_id")
                client_secret = data["web"].get("client_secret")
            elif "installed" in data:
                client_id = data["installed"].get("client_id")
                client_secret = data["installed"].get("client_secret")
            
            if client_id and client_secret:
                from app.services import db
                db.save_setting("youtube_client_id", client_id, user_id=user_id)
                db.save_setting("youtube_client_secret", client_secret, user_id=user_id)
        except Exception as parse_err:
            logger.warning(f"Uploaded JSON could not be parsed for db insertion: {parse_err}")

        logger.success(f"client_secret.json uploaded and saved successfully for user {user_id}.")
        return utils.get_response(200, {"message": "client_secret.json uploaded successfully"})
    
    raise HttpException(
        "", status_code=400, message=f"{request_id}: Only *.json files can be uploaded"
    )


@router.post("/youtube/upload-task/{task_id}", summary="Upload a completed video task to YouTube")
def upload_task_to_youtube(request: Request, task_id: str, background_tasks: BackgroundTasks):
    user_id = _get_user_id(request)
    task = sm.state.get_task(task_id)
    if not task:
        raise HttpException("", status_code=404, message="Task not found")
        
    if task.get("user_id", "global") != user_id and user_id != "global":
        raise HttpException("", status_code=403, message="Access denied")
        
    tasks_dir = utils.task_dir()
    video_path = os.path.join(tasks_dir, task_id, "final-1.mp4")
    if not os.path.exists(video_path):
        import glob
        mp4_files = glob.glob(os.path.join(tasks_dir, task_id, "*.mp4"))
        if mp4_files:
            video_path = mp4_files[0]
        else:
            raise HttpException("", status_code=400, message="Compiled video file not found for this task")
            
    params = task.get("params") or {}
    title = params.get("video_subject")
    if not title:
        # Fallback 1: Parse first keyword from terms
        terms_str = task.get("terms")
        if terms_str:
            try:
                import json
                try:
                    parsed = json.loads(terms_str)
                    if isinstance(parsed, list) and parsed:
                        title = parsed[0]
                except Exception:
                    pass
                if not title:
                    clean_terms = terms_str.strip('{}').replace('"', '')
                    terms_list = [t.strip() for t in clean_terms.split(',') if t.strip()]
                    if terms_list:
                        title = terms_list[0]
            except Exception:
                pass
        
        # Fallback 2: Parse first few words of the script
        if not title:
            script = task.get("script")
            if script:
                import re
                first_sentence = re.split(r'[.!?]', script)[0].strip()
                words = first_sentence.split()
                if len(words) > 6:
                    title = " ".join(words[:6]) + "..."
                else:
                    title = first_sentence

        if not title:
            title = "Compiled Short Video"

    description = f"#shorts #motivation #viral\nGenerated via Turbo Studio\nSubject: {title}"
    
    def run_upload():
        try:
            from youtube_uploader import upload_video
            logger.info(f"Starting manual YouTube upload for task {task_id}, user {user_id}, path: {video_path}")
            upload_video(
                file_path=video_path,
                title=title,
                description=description,
                tags=["shorts", "motivation", "viral"],
                privacy_status="public",
                user_id=user_id
            )
            sm.state.update_task(task_id, youtube_uploaded=1, user_id=user_id)
            logger.info(f"Manual YouTube upload successfully completed and database state updated for task {task_id}")
        except Exception as e:
            logger.error(f"Manual YouTube upload error for task {task_id}: {e}")
            
    background_tasks.add_task(run_upload)
    return utils.get_response(200, {"message": "YouTube upload started in background"})


@router.get("/voice/preview", summary="Generate a quick voice preview stream")
async def preview_voice(request: Request, voice: str = Query(..., description="Voice name")):
    user_id = _get_user_id(request)
    import edge_tts
    from fastapi.responses import StreamingResponse
    import io
    
    # Determine the preview text based on language
    preview_text = "नमस्कार, यह आपके चुने हुए आवाज का एक पूर्वावलोकन है।"
    if not voice.lower().startswith("hi-") and not voice.lower().startswith("sarvam:"):
        preview_text = "Hello, this is a quick preview of your selected narrator voice."
        
    # Check if it is a Google Gemini voice
    from app.services.voice import is_gemini_voice, gemini_tts
    if is_gemini_voice(voice):
        try:
            from app.utils import utils
            import uuid
            temp_dir = utils.storage_dir("temp", create=True)
            preview_file = os.path.join(temp_dir, f"preview-gemini-{uuid.uuid4()}.mp3")
            
            parts = voice.split(":")
            voice_name = parts[1].split("-")[0] if len(parts) >= 2 else "Zephyr"
            
            sub_maker = gemini_tts(
                text=preview_text,
                voice_name=voice_name,
                voice_rate=1.0,
                voice_file=preview_file,
                user_id=user_id
            )
            if sub_maker and os.path.exists(preview_file):
                with open(preview_file, "rb") as f:
                    audio_bytes = f.read()
                try:
                    os.remove(preview_file)
                except Exception:
                    pass
                return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/mp3")
            else:
                logger.warning("Gemini voice preview synthesis failed")
        except Exception as e:
            logger.warning(f"Failed to generate Gemini voice preview: {e}")

    # Check if it is a Sarvam voice
    from app.services.voice import is_sarvam_voice, sarvam_tts
    if is_sarvam_voice(voice):
        try:
            from app.utils import utils
            import uuid
            temp_dir = utils.storage_dir("temp", create=True)
            preview_file = os.path.join(temp_dir, f"preview-sarvam-{uuid.uuid4()}.mp3")
            
            parts = voice.split(":")
            voice_name = parts[1].split("-")[0] if len(parts) >= 2 else "shubh"
            
            sub_maker = sarvam_tts(
                text=preview_text,
                voice_name=voice_name,
                voice_rate=1.0,
                voice_file=preview_file,
                user_id=user_id
            )
            if sub_maker and os.path.exists(preview_file):
                with open(preview_file, "rb") as f:
                    audio_bytes = f.read()
                try:
                    os.remove(preview_file)
                except Exception:
                    pass
                return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/mp3")
            else:
                logger.warning("Sarvam voice preview synthesis failed")
        except Exception as e:
            logger.warning(f"Failed to generate Sarvam voice preview: {e}")
        
    # Check if official Azure Speech config is set up
    from app.services import db
    speech_key = db.get_setting("azure_speech_key", user_id=user_id) or config.azure.get("speech_key", "")
    service_region = db.get_setting("azure_speech_region", user_id=user_id) or config.azure.get("speech_region", "")
    if speech_key and service_region:
        try:
            import azure.cognitiveservices.speech as speechsdk
            from app.services.voice import parse_voice_name
            actual_voice_name = parse_voice_name(voice)
            if actual_voice_name.endswith("-V2"):
                actual_voice_name = actual_voice_name.replace("-V2", "").strip()
                
            speech_config = speechsdk.SpeechConfig(
                subscription=speech_key, region=service_region
            )
            speech_config.speech_synthesis_voice_name = actual_voice_name
            speech_config.set_speech_synthesis_output_format(
                speechsdk.SpeechSynthesisOutputFormat.Audio48Khz192KBitRateMonoMp3
            )
            # Synthesize directly to memory stream
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=speech_config, audio_config=None
            )
            result = synthesizer.speak_text_async(preview_text).get()
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                logger.info(f"Generated voice preview via Azure Speech SDK for {actual_voice_name} for user {user_id}")
                return StreamingResponse(
                    io.BytesIO(result.audio_data), media_type="audio/mp3"
                )
            else:
                logger.warning(f"Azure voice preview synthesis canceled or failed, falling back to edge-tts")
        except Exception as azure_err:
            logger.warning(f"Failed to generate preview via Azure SDK: {azure_err}, falling back to edge-tts")

    # Map input voice names to actual valid edge-tts names
    voice_map = {
        "en-US-AndrewNeural": "en-US-AndrewMultilingualNeural",
        "en-US-EmmaNeural": "en-US-EmmaMultilingualNeural",
        "en-US-AvaNeural": "en-US-AvaMultilingualNeural",
        "en-US-BrianNeural": "en-US-BrianMultilingualNeural",
        "hi-IN-KavyanjaliNeural": "hi-IN-SwaraNeural",
        "hi-IN-AnanyaNeural": "hi-IN-SwaraNeural",
        "hi-IN-NiharikaNeural": "hi-IN-SwaraNeural",
        "hi-IN-KavyaNeural": "hi-IN-SwaraNeural",
        "hi-IN-AartiNeural": "hi-IN-SwaraNeural",
        "hi-IN-AaravNeural": "hi-IN-MadhurNeural",
        "hi-IN-KunalNeural": "hi-IN-MadhurNeural",
        "hi-IN-RehaanNeural": "hi-IN-MadhurNeural",
        "hi-IN-ArjunNeural": "hi-IN-MadhurNeural"
    }
    actual_voice = voice_map.get(voice, voice)
    
    if not actual_voice.startswith("hi-"):
        preview_text = "Hello, this is a quick preview of your selected narrator voice."
        
    try:
        communicate = edge_tts.Communicate(preview_text, actual_voice)
        audio_data = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk.get("data"):
                audio_data.write(chunk["data"])
        audio_data.seek(0)
        return StreamingResponse(audio_data, media_type="audio/mp3")
    except Exception as e:
        logger.error(f"Voice preview generation error: {e}")
        raise HttpException("", status_code=500, message=f"Failed to generate preview: {str(e)}")

@router.post("/scripts/score", summary="Score a video script for virality potential")
def score_video_script(request: Request, body: ScriptScoreRequest):
    user_id = _get_user_id(request)
    scores = llm.score_script_virality(body.script, user_id=user_id)
    # Save the score to the database (without a task_id, since it's just a prediction/draft)
    db.save_viral_score(script=body.script, platform=body.platform, scores=scores, task_id=None)
    return utils.get_response(200, scores)

@router.get("/trends", summary="Fetch trending topics from YouTube or Google Trends")
def get_trending_topics(
    request: Request,
    platform: str = Query("google", description="google or youtube"),
    category: str = Query("all", description="all, motivation, finance, health, tech, entertainment")
):
    from app.services import trend_service
    user_id = _get_user_id(request)
    trends = trend_service.get_trends(platform=platform, category=category, user_id=user_id)
    response = {"trends": trends}
    return utils.get_response(200, response)


# --- TIKTOK PUBLISHING ENDPOINTS ---
@router.get("/tiktok/status", summary="Get TikTok integration status")
def get_tiktok_status(request: Request):
    user_id = _get_user_id(request)
    from app.services import db
    tiktok_creds = db.get_platform_oauth(user_id=user_id, platform="tiktok")
    return utils.get_response(200, {
        "channel_connected": tiktok_creds is not None,
        "channel_name": tiktok_creds["channel_name"] if tiktok_creds else ""
    })

@router.get("/tiktok/connect", summary="Get TikTok OAuth redirection URL")
def connect_tiktok(request: Request):
    user_id = _get_user_id(request)
    import tiktok_uploader
    auth_url = tiktok_uploader.get_auth_url(user_id=user_id)
    return utils.get_response(200, {"auth_url": auth_url})

@router.get("/tiktok/oauth-callback", summary="Receive TikTok authorization code")
def tiktok_oauth_callback(code: str = Query(...), state: str = Query("global")):
    import tiktok_uploader
    try:
        tiktok_uploader.exchange_code(code=code, user_id=state)
        return RedirectResponse(f"http://localhost:5173/?tab=publish&user_id={state}&tiktok_connected=true")
    except Exception as e:
        logger.error(f"TikTok OAuth callback failed: {e}")
        import urllib.parse
        encoded_err = urllib.parse.quote(str(e))
        return RedirectResponse(f"http://localhost:5173/?tab=publish&error={encoded_err}")

@router.post("/tiktok/disconnect", summary="Disconnect TikTok account")
def disconnect_tiktok(request: Request):
    user_id = _get_user_id(request)
    from app.services import db
    db.delete_platform_oauth(user_id=user_id, platform="tiktok")
    return utils.get_response(200, {"message": "TikTok account disconnected successfully"})

@router.post("/tiktok/upload-task/{task_id}", summary="Upload video task to TikTok")
def upload_task_to_tiktok(request: Request, task_id: str, background_tasks: BackgroundTasks):
    user_id = _get_user_id(request)
    task = sm.state.get_task(task_id)
    if not task:
        raise HttpException("", status_code=404, message="Task not found")
        
    if task.get("user_id", "global") != user_id and user_id != "global":
        raise HttpException("", status_code=403, message="Access denied")
        
    try:
        from scheduler_service import get_task_video_path, generate_viral_caption_via_llm
        video_path = get_task_video_path(task_id)
        params = task.get("params") or {}
        video_subject = params.get("video_subject") or "SaaS Auto Short"
        script = task.get("script")
        caption = generate_viral_caption_via_llm(video_subject, script, user_id)
    except Exception as e:
        raise HttpException("", status_code=400, message=str(e))
        
    def run_upload():
        try:
            import tiktok_uploader
            logger.info(f"Starting TikTok upload for task {task_id}, user {user_id}, path: {video_path}")
            tiktok_uploader.upload_video(
                user_id=user_id,
                file_path=video_path,
                caption=caption
            )
            from app.services import db
            db.log_usage(user_id, task_id, "tiktok_publish")
        except Exception as e:
            logger.error(f"TikTok upload failed for task {task_id}: {e}")
            
    background_tasks.add_task(run_upload)
    return utils.get_response(200, {"message": "TikTok upload started in background"})


# --- INSTAGRAM PUBLISHING ENDPOINTS ---
@router.get("/instagram/status", summary="Get Instagram integration status")
def get_instagram_status(request: Request):
    user_id = _get_user_id(request)
    from app.services import db
    instagram_creds = db.get_platform_oauth(user_id=user_id, platform="instagram")
    return utils.get_response(200, {
        "channel_connected": instagram_creds is not None,
        "channel_name": instagram_creds["channel_name"] if instagram_creds else ""
    })

@router.get("/instagram/connect", summary="Get Instagram OAuth redirection URL")
def connect_instagram(request: Request):
    user_id = _get_user_id(request)
    import instagram_uploader
    auth_url = instagram_uploader.get_auth_url(user_id=user_id)
    return utils.get_response(200, {"auth_url": auth_url})

@router.get("/instagram/oauth-callback", summary="Receive Instagram/Facebook authorization code")
def instagram_oauth_callback(code: str = Query(...), state: str = Query("global")):
    import instagram_uploader
    try:
        instagram_uploader.exchange_code(code=code, user_id=state)
        return RedirectResponse(f"http://localhost:5173/?tab=publish&user_id={state}&instagram_connected=true")
    except Exception as e:
        logger.error(f"Instagram OAuth callback failed: {e}")
        import urllib.parse
        encoded_err = urllib.parse.quote(str(e))
        return RedirectResponse(f"http://localhost:5173/?tab=publish&error={encoded_err}")

@router.post("/instagram/disconnect", summary="Disconnect Instagram account")
def disconnect_instagram(request: Request):
    user_id = _get_user_id(request)
    from app.services import db
    db.delete_platform_oauth(user_id=user_id, platform="instagram")
    return utils.get_response(200, {"message": "Instagram account disconnected successfully"})

@router.post("/instagram/upload-task/{task_id}", summary="Upload video task as Instagram Reel")
def upload_task_to_instagram(request: Request, task_id: str, background_tasks: BackgroundTasks):
    user_id = _get_user_id(request)
    task = sm.state.get_task(task_id)
    if not task:
        raise HttpException("", status_code=404, message="Task not found")
        
    if task.get("user_id", "global") != user_id and user_id != "global":
        raise HttpException("", status_code=403, message="Access denied")
        
    try:
        from scheduler_service import get_task_video_path, generate_viral_caption_via_llm
        video_path = get_task_video_path(task_id)
        params = task.get("params") or {}
        video_subject = params.get("video_subject") or "SaaS Auto Short"
        script = task.get("script")
        caption = generate_viral_caption_via_llm(video_subject, script, user_id)
    except Exception as e:
        raise HttpException("", status_code=400, message=str(e))
        
    def run_upload():
        try:
            import instagram_uploader
            logger.info(f"Starting Instagram Reels upload for task {task_id}, user {user_id}, path: {video_path}")
            instagram_uploader.upload_video(
                user_id=user_id,
                file_path=video_path,
                caption=caption
            )
            from app.services import db
            db.log_usage(user_id, task_id, "instagram_publish")
        except Exception as e:
            logger.error(f"Instagram Reels upload failed for task {task_id}: {e}")
            
    background_tasks.add_task(run_upload)
    return utils.get_response(200, {"message": "Instagram Reels upload started in background"})


# --- SMART SCHEDULING ENDPOINTS ---
from pydantic import BaseModel
class SchedulePostRequest(BaseModel):
    task_id: str
    platform: str
    scheduled_at: str

@router.post("/schedule", summary="Schedule a task for platform publishing")
def schedule_publishing(request: Request, body: SchedulePostRequest):
    user_id = _get_user_id(request)
    from app.services import db
    
    task = sm.state.get_task(body.task_id)
    if not task:
        raise HttpException("", status_code=404, message="Task not found")
    if task.get("user_id", "global") != user_id and user_id != "global":
        raise HttpException("", status_code=403, message="Access denied")
        
    post_id = db.create_scheduled_post(
        task_id=body.task_id,
        user_id=user_id,
        platform=body.platform,
        scheduled_at=body.scheduled_at
    )
    if not post_id:
        raise HttpException("", status_code=500, message="Failed to write scheduled post to database")
        
    logger.success(f"Task {body.task_id} scheduled for {body.platform} at {body.scheduled_at} (Post ID: {post_id})")
    return utils.get_response(200, {"message": "Task scheduled successfully", "post_id": post_id})

@router.get("/schedule", summary="List scheduled posts for the user")
def list_scheduled_posts(request: Request):
    user_id = _get_user_id(request)
    from app.services import db
    posts = db.get_scheduled_posts(user_id=user_id)
    
    enriched_posts = []
    for post in posts:
        task_id = post["task_id"]
        task = sm.state.get_task(task_id)
        video_subject = "Auto Short Video"
        if task:
            params = task.get("params") or {}
            video_subject = params.get("video_subject") or "Auto Short Video"
        post["video_subject"] = video_subject
        enriched_posts.append(post)
        
    return utils.get_response(200, {"posts": enriched_posts})

@router.post("/schedule/cancel/{post_id}", summary="Cancel a scheduled post")
def cancel_publishing_post(request: Request, post_id: int):
    user_id = _get_user_id(request)
    from app.services import db
    success = db.cancel_scheduled_post(post_id=post_id, user_id=user_id)
    if not success:
        raise HttpException("", status_code=400, message="Failed to cancel scheduled post. Please verify ownership and ID.")
        
    return utils.get_response(200, {"message": "Scheduled post cancelled successfully"})