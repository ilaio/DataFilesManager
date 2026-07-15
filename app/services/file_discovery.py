import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

from app.services.formatting import format_size


class DirectoryStatus(str, Enum):
    OK = "ok"
    NOT_FOUND = "not_found"
    NOT_READABLE = "not_readable"


@dataclass
class FileInfo:
    name: str
    size_bytes: int
    size_human: str
    modified_at: datetime


@dataclass
class DirectoryCheck:
    status: DirectoryStatus
    message: str | None = None



def check_data_directory(data_dir: Path) -> DirectoryCheck:
    if not data_dir.exists():
        return DirectoryCheck(
            status=DirectoryStatus.NOT_FOUND,
            message=f"CSV folder does not exist: {data_dir}",
        )

    if not data_dir.is_dir():
        return DirectoryCheck(
            status=DirectoryStatus.NOT_FOUND,
            message=f"CSV path is not a directory: {data_dir}",
        )

    if not os.access(data_dir, os.R_OK):
        return DirectoryCheck(
            status=DirectoryStatus.NOT_READABLE,
            message=f"CSV folder is not readable: {data_dir}",
        )

    return DirectoryCheck(status=DirectoryStatus.OK)


def list_csv_files(data_dir: Path) -> list[FileInfo]:
    files: list[FileInfo] = []

    for entry in data_dir.iterdir():
        if not entry.is_file():
            continue
        if entry.name.startswith("."):
            continue
        if entry.suffix.lower() != ".csv":
            continue

        stat = entry.stat()
        files.append(
            FileInfo(
                name=entry.name,
                size_bytes=stat.st_size,
                size_human=format_size(stat.st_size),
                modified_at=datetime.fromtimestamp(stat.st_mtime),
            )
        )

    files.sort(key=lambda file_info: file_info.modified_at, reverse=True)
    return files
