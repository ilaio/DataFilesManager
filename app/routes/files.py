import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.services.csv_inspection import CsvInspectionError, get_sample_rows, inspect_csv
from app.services.csv_pagination import PAGE_SIZE_OPTIONS, get_paginated_rows
from app.services.file_discovery import (
    DirectoryStatus,
    check_data_directory,
    list_csv_files,
)
from app.services.path_utils import CsvFileNotFoundError, resolve_csv_file

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


@router.get("/files/{filename}", response_class=HTMLResponse)
async def file_detail(request: Request, filename: str) -> HTMLResponse:
    settings = get_settings()
    data_dir = settings.csv_data_path

    try:
        file_path = resolve_csv_file(data_dir, filename)
    except CsvFileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    metadata = None
    sample = None
    inspection_error = None

    try:
        metadata = inspect_csv(
            file_path,
            sample_size=settings.csv_type_inference_sample_size,
        )
        sample = get_sample_rows(
            file_path,
            sample_size=settings.csv_type_inference_sample_size,
        )
    except CsvInspectionError as exc:
        inspection_error = str(exc)
    except Exception:
        logger.exception("Failed to inspect CSV file: %s", file_path)
        inspection_error = "Unable to analyze this CSV file."

    return templates.TemplateResponse(
        request,
        "file_detail.html",
        {
            "filename": file_path.name,
            "metadata": metadata,
            "sample": sample,
            "inspection_error": inspection_error,
        },
    )


@router.get("/files/{filename}/browse", response_class=HTMLResponse)
async def file_browse(
    request: Request,
    filename: str,
    page: int = 1,
    page_size: int | None = None,
) -> HTMLResponse:
    settings = get_settings()
    data_dir = settings.csv_data_path

    try:
        file_path = resolve_csv_file(data_dir, filename)
    except CsvFileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    resolved_page_size = (
        page_size if page_size is not None else settings.csv_default_page_size
    )

    pagination = None
    browse_error = None

    try:
        pagination = get_paginated_rows(
            file_path,
            page=page,
            page_size=resolved_page_size,
            sample_size=settings.csv_type_inference_sample_size,
            allowed_page_sizes=settings.csv_page_size_options,
            default_page_size=settings.csv_default_page_size,
        )
    except CsvInspectionError as exc:
        browse_error = str(exc)
    except Exception:
        logger.exception("Failed to browse CSV file: %s", file_path)
        browse_error = "Unable to browse this CSV file."

    return templates.TemplateResponse(
        request,
        "file_browse.html",
        {
            "filename": file_path.name,
            "pagination": pagination,
            "browse_error": browse_error,
            "page_size_options": settings.csv_page_size_options or PAGE_SIZE_OPTIONS,
        },
    )
