import logging
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.services.file_discovery import (
    DirectoryStatus,
    check_data_directory,
    list_csv_files,
)

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


@router.get("/", response_class=HTMLResponse)
async def list_files(request: Request) -> HTMLResponse:
    settings = get_settings()
    data_dir = settings.csv_data_path
    dir_check = check_data_directory(data_dir)

    files = []
    scan_error = None

    if dir_check.status == DirectoryStatus.OK:
        try:
            files = list_csv_files(data_dir)
        except OSError:
            logger.exception("Failed to scan CSV folder: %s", data_dir)
            scan_error = "Unable to read CSV files. Please check folder permissions."

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "files": files,
            "data_dir": str(data_dir),
            "dir_check": dir_check,
            "scan_error": scan_error,
        },
    )
