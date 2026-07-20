import math
from dataclasses import dataclass
from pathlib import Path

import duckdb

from app.services.csv_inspection import (
    CsvInspectionError,
    _format_cell,
    _resolve_encoding,
    inspect_csv,
)

PAGE_SIZE_OPTIONS = [25, 50, 100]
DEFAULT_PAGE_SIZE = 50


@dataclass
class PaginatedRows:
    columns: list[str]
    rows: list[list[str]]
    page: int
    page_size: int
    total_rows: int
    total_pages: int
    start_row: int
    end_row: int
    encoding: str
    encoding_warning: str | None


def normalize_page_size(
    page_size: int,
    allowed: list[int],
    default: int,
) -> int:
    if page_size in allowed:
        return page_size
    return default


def normalize_page(page: int, total_pages: int) -> int:
    if total_pages < 1:
        total_pages = 1
    if page < 1:
        return 1
    if page > total_pages:
        return total_pages
    return page


def _compute_total_pages(total_rows: int, page_size: int) -> int:
    if total_rows == 0:
        return 1
    return math.ceil(total_rows / page_size)


def get_paginated_rows(
    file_path: Path,
    *,
    page: int,
    page_size: int,
    sample_size: int,
    total_rows: int | None = None,
    encoding: str | None = None,
    encoding_warning: str | None = None,
    allowed_page_sizes: list[int] | None = None,
    default_page_size: int = DEFAULT_PAGE_SIZE,
) -> PaginatedRows:
    allowed = allowed_page_sizes or PAGE_SIZE_OPTIONS
    normalized_page_size = normalize_page_size(page_size, allowed, default_page_size)

    if total_rows is None:
        metadata = inspect_csv(file_path, sample_size=sample_size)
        total_rows = metadata.row_count
        encoding = metadata.encoding
        encoding_warning = metadata.encoding_warning

    total_pages = _compute_total_pages(total_rows, normalized_page_size)
    normalized_page = normalize_page(page, total_pages)

    if total_rows == 0 or file_path.stat().st_size == 0:
        return PaginatedRows(
            columns=[],
            rows=[],
            page=1,
            page_size=normalized_page_size,
            total_rows=0,
            total_pages=1,
            start_row=0,
            end_row=0,
            encoding=encoding or "UTF-8",
            encoding_warning=encoding_warning,
        )

    offset = (normalized_page - 1) * normalized_page_size
    start_row = offset + 1
    end_row = min(offset + normalized_page_size, total_rows)

    conn = duckdb.connect()

    try:
        if encoding is None:
            encoding, encoding_warning = _resolve_encoding(
                conn, file_path, sample_size
            )

        relation = conn.execute(
            """
            SELECT *
            FROM read_csv_auto(?, sample_size=?, encoding=?)
            LIMIT ? OFFSET ?
            """,
            [
                str(file_path),
                sample_size,
                encoding,
                normalized_page_size,
                offset,
            ],
        )
        columns = [col[0] for col in relation.description]
        rows = [
            [_format_cell(value) for value in row]
            for row in relation.fetchall()
        ]

        return PaginatedRows(
            columns=columns,
            rows=rows,
            page=normalized_page,
            page_size=normalized_page_size,
            total_rows=total_rows,
            total_pages=total_pages,
            start_row=start_row,
            end_row=end_row,
            encoding=encoding,
            encoding_warning=encoding_warning,
        )
    except CsvInspectionError:
        raise
    except duckdb.Error as exc:
        raise CsvInspectionError(f"Unable to read CSV page: {exc}") from exc
    finally:
        conn.close()
