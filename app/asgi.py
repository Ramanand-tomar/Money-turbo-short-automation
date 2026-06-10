"""Application implementation - ASGI."""

import os
import uuid

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message

from app.config import config
from app.models.exception import HttpException
from app.router import root_api_router
from app.utils import utils
from app.middleware.auth import ClerkAuthMiddleware


# ---------------------------------------------------------------------------
# Sentry initialisation (no-op when SENTRY_DSN is not set)
# ---------------------------------------------------------------------------
_sentry_dsn = os.getenv("SENTRY_DSN", "")
if _sentry_dsn:
    sentry_sdk.init(
        dsn=_sentry_dsn,
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        environment=os.getenv("ENVIRONMENT", "production"),
        send_default_pii=False,
    )
    logger.info("Sentry SDK initialised.")
else:
    logger.info("SENTRY_DSN not set — Sentry error tracking disabled.")


# ---------------------------------------------------------------------------
# SlowAPI rate-limiter (shared instance, injected into FastAPI state)
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


# ---------------------------------------------------------------------------
# Correlation-ID middleware
# ---------------------------------------------------------------------------
class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Attaches a UUID correlation ID to every request.
    - Reads X-Request-ID from the incoming request; generates one if absent.
    - Stores it on request.state.correlation_id for use in endpoint code.
    - Adds it to the response as X-Request-ID.
    """

    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.correlation_id = correlation_id

        # Make the correlation ID available to loguru via a context-var shim
        with logger.contextualize(request_id=correlation_id):
            response = await call_next(request)

        response.headers["X-Request-ID"] = correlation_id
        return response


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------
def exception_handler(request: Request, e: HttpException):
    return JSONResponse(
        status_code=e.status_code,
        content=utils.get_response(e.status_code, e.data, e.message),
    )


def validation_exception_handler(request: Request, e: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content=utils.get_response(
            status=400, data=e.errors(), message="field required"
        ),
    )


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------
def get_application() -> FastAPI:
    """Initialize FastAPI application.

    Returns:
       FastAPI: Application object instance.

    """
    instance = FastAPI(
        title=config.project_name,
        description=config.project_description,
        version=config.project_version,
        debug=False,
    )

    # Attach the limiter to the app state so endpoint decorators can find it
    instance.state.limiter = limiter
    instance.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    instance.add_exception_handler(HttpException, exception_handler)
    instance.add_exception_handler(RequestValidationError, validation_exception_handler)
    instance.include_router(root_api_router)
    return instance


app = get_application()

# ---------------------------------------------------------------------------
# Middleware stack (applied in reverse registration order by Starlette)
# ---------------------------------------------------------------------------

# 1. CORS — configures allowed origins via env var CORS_ALLOWED_ORIGINS
cors_allowed_origins_str = os.getenv("CORS_ALLOWED_ORIGINS", "")
if cors_allowed_origins_str:
    origins = [o.strip() for o in cors_allowed_origins_str.split(",") if o.strip()]
    allow_origin_regex = None
else:
    origins = []
    allow_origin_regex = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# 2. Rate limiting
app.add_middleware(SlowAPIMiddleware)

# 3. Correlation ID (applied after auth so correlation_id is available to all layers)
app.add_middleware(CorrelationIdMiddleware)

# 4. Clerk Auth
app.add_middleware(ClerkAuthMiddleware)

# ---------------------------------------------------------------------------
# Static file mounts
# ---------------------------------------------------------------------------
# NOTE: The /tasks static mount is intentionally omitted.
# All video file serving is handled by the authenticated /api/v1/stream/{path}
# endpoint (in video.py) which enforces per-user ownership checks before
# returning files. Serving storage/tasks/ as a public static directory would
# bypass those ownership checks.

public_dir = utils.public_dir()
app.mount("/", StaticFiles(directory=public_dir, html=True), name="")


# ---------------------------------------------------------------------------
# Startup / Shutdown lifecycle hooks
# ---------------------------------------------------------------------------
@app.on_event("shutdown")
def shutdown_event():
    logger.info("shutdown event")
    try:
        import scheduler_service
        scheduler_service.shutdown_scheduler()
    except Exception as e:
        logger.error(f"Error shutting down scheduler: {e}")


@app.on_event("startup")
def startup_event():
    logger.info("startup event")
    try:
        import scheduler_service
        scheduler_service.start_scheduler()
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
