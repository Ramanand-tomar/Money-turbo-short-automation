import contextvars
import os
import sys

from loguru import logger

from app.config import config
from app.utils import utils

# ---------------------------------------------------------------------------
# Context variable to carry the correlation / request ID across async tasks.
# CorrelationIdMiddleware sets this via logger.contextualize(request_id=...).
# ---------------------------------------------------------------------------
_request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)


def __init_logger():
    _lvl = config.log_level
    root_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    )

    def format_record(record):
        # Convert absolute path to project-relative for cleaner output
        file_path = record["file"].path
        relative_path = os.path.relpath(file_path, root_dir)
        record["file"].path = f"./{relative_path}"

        # Correlation / request-ID (populated by CorrelationIdMiddleware via
        # logger.contextualize; falls back to "-" when outside a request)
        req_id = record["extra"].get("request_id", "-")
        short_req_id = req_id[:8] if req_id and req_id != "-" else "-"

        _format = (
            "<green>{time:%Y-%m-%d %H:%M:%S}</> | "
            + "<level>{level:<8}</> | "
            + f"<cyan>[{short_req_id}]</> "
            + '"{file.path}:{line}":<blue> {function}</> '
            + "- <level>{message}</>"
            + "\n"
        )
        return _format

    logger.remove()

    logger.add(
        sys.stdout,
        level=_lvl,
        format=format_record,
        colorize=True,
    )


__init_logger()
