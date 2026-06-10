from fastapi import Body, Depends, Request, Query, Path
from pydantic import BaseModel
from typing import Optional

from app.controllers.v1.base import new_router
from app.models.exception import HttpException
from app.services import db
from app.utils import utils

class UserUpdateRequest(BaseModel):
    role: Optional[str] = None
    plan: Optional[str] = None
    quota_videos_per_day: Optional[int] = None
    quota_videos_per_month: Optional[int] = None
    is_active: Optional[bool] = None
    email: Optional[str] = None

class ConfigSaveRequest(BaseModel):
    key: str
    value: str

def verify_admin(request: Request):
    role = getattr(request.state, "role", None)
    if role != "admin":
        raise HttpException(
            task_id="",
            status_code=403,
            message="Forbidden: Administrator access required"
        )

# Create router secured with verify_admin
router = new_router(dependencies=[Depends(verify_admin)])

@router.get("/admin/stats", summary="Get platform statistics")
def get_stats(request: Request):
    stats = db.get_admin_stats()
    return utils.get_response(200, stats)

@router.get("/admin/users", summary="Get paginated list of users")
def get_users(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1),
    search: str = Query("", description="Search by user ID or email")
):
    users, total = db.get_users_list(page=page, page_size=page_size, search=search)
    return utils.get_response(200, {
        "users": users,
        "total": total,
        "page": page,
        "page_size": page_size
    })

@router.patch("/admin/users/{user_id}", summary="Update user attributes")
def update_user(
    request: Request,
    user_id: str = Path(..., description="User ID"),
    body: UserUpdateRequest = Body(...),
):
    user = db.get_user(user_id)
    if not user:
        raise HttpException(task_id="", status_code=404, message="User not found")

    # Use `is not None` so that explicit False / 0 values are not filtered out
    update_data = {k: v for k, v in body.model_dump().items() if v is not None}
    if update_data:
        db.update_user(user_id, **update_data)

    return utils.get_response(200, message="User updated successfully")

@router.get("/admin/tasks", summary="Get all platform tasks (admin view)")
def get_tasks(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1)
):
    tasks, total = db.get_all_tasks_admin(page=page, page_size=page_size)
    return utils.get_response(200, {
        "tasks": tasks,
        "total": total,
        "page": page,
        "page_size": page_size
    })

@router.get("/admin/config", summary="Get platform configurations")
def get_config(
    request: Request,
    key: str = Query(None, description="Configuration key. If not specified, returns all config fields.")
):
    if key:
        val = db.get_platform_config(key)
        return utils.get_response(200, {"key": key, "value": val})
    else:
        # fetch all from platform_config
        conn = db.get_connection()
        cursor = conn.cursor()
        if db.IS_POSTGRES:
            cursor.execute("SELECT key, value FROM platform_config")
        else:
            cursor.execute("SELECT key, value FROM platform_config")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        conn.close()
        
        config_dict = {}
        for row in rows:
            if hasattr(row, 'keys'):
                r_dict = dict(row)
            else:
                r_dict = dict(zip(columns, row))
            config_dict[r_dict["key"]] = r_dict["value"]
            
        return utils.get_response(200, config_dict)

@router.post("/admin/config", summary="Save platform configuration")
def save_config(
    request: Request,
    body: ConfigSaveRequest
):
    success = db.save_platform_config(body.key, body.value)
    if success:
        return utils.get_response(200, message="Configuration saved successfully")
    raise HttpException(task_id="", status_code=500, message="Failed to save platform configuration")
