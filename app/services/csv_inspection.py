import duckdb
from dataclasses import dataclass
from pathlib import Path

from app.services.formatting import format_size

DUCKDB_TYPE_LABELS = {
    "BOOLEAN": "boolean",
    "TINYINT": "integer",
    "SMALLINT": "integer",
    "INTEGER": "integer",
    "BIGINT": "integer",
    "UTINYINT": "integer",
    "USMALLINT": "integer",
    "UINTEGER": "integer",
    "UBIGINT": "integer",
    "HUGEINT": "integer",
    "FLOAT": "float",
    "DOUBLE": "float",
    "DECIMAL": "float",
    "VARCHAR": "string",
    "BLOB": "binary",
    "DATE": "date",
    "TIME": "time",
    "TIMESTAMP": "datetime",
    "TIMESTAMP WITH TIME ZONE": "datetime",
    "INTERVAL": "interval",
    "UUID": "uuid",
}


class CsvInspectionError(Exception):
    pass


@dataclass
class ColumnInfo:
    name: str
    dtype: str


@dataclass
class FileMetadata:
    name: str
    path: Path
    size_bytes: int
    size_human: str
    row_count: int
    columns: list[ColumnInfo]
    encoding: str
    encoding_warning: str | None
    inferred_from_sample: bool
    sample_size: int


@dataclass
class SamplePreview:
    columns: list[str]
    rows: list[list[str]]


@dataclass
class CsvReadContext:
    encoding: str
    encoding_warning: str | None


def _display_type(duckdb_type: str) -> str:
    normalized = duckdb_type.upper()
    return DUCKDB_TYPE_LABELS.get(normalized, duckdb_type.lower())


def _format_cell(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _empty_metadata(file_path: Path, sample_size: int) -> FileMetadata:
    stat = file_path.stat()
    return FileMetadata(
        name=file_path.name,
        path=file_path,
        size_bytes=stat.st_size,
        size_human=format_size(stat.st_size),
        row_count=0,
        columns=[],
        encoding="UTF-8",
        encoding_warning=None,
        inferred_from_sample=False,
        sample_size=sample_size,
    )


def _resolve_encoding(
    conn: duckdb.DuckDBPyConnection,
    file_path: Path,
    sample_size: int,
) -> tuple[str, str | None]:
    encodings = (
        ("UTF-8", None),
        ("latin-1", "UTF-8 decode failed; read as latin-1"),
    )

    last_error: duckdb.Error | None = None

    for encoding, warning in encodings:
        try:
            conn.execute(
                """
                SELECT COUNT(*)
                FROM read_csv_auto(?, sample_size=?, encoding=?)
                """,
                [str(file_path), sample_size, encoding],
            )
            return encoding, warning
        except duckdb.Error as exc:
            last_error = exc
            continue

    raise CsvInspectionError(
        f"Unable to read CSV file: {last_error}"
    ) from last_error


def get_csv_read_context(
    file_path: Path,
    *,
    sample_size: int = 10_000,
) -> CsvReadContext:
    if file_path.stat().st_size == 0:
        return CsvReadContext(encoding="UTF-8", encoding_warning=None)

    conn = duckdb.connect()

    try:
        encoding, encoding_warning = _resolve_encoding(conn, file_path, sample_size)
        return CsvReadContext(
            encoding=encoding,
            encoding_warning=encoding_warning,
        )
    finally:
        conn.close()


def inspect_csv(file_path: Path, *, sample_size: int = 10_000) -> FileMetadata:
    stat = file_path.stat()

    if stat.st_size == 0:
        return _empty_metadata(file_path, sample_size)

    conn = duckdb.connect()

    try:
        encoding, encoding_warning = _resolve_encoding(conn, file_path, sample_size)

        row_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM read_csv_auto(?, sample_size=?, encoding=?)
            """,
            [str(file_path), sample_size, encoding],
        ).fetchone()[0]

        describe_rows = conn.execute(
            """
            DESCRIBE
            SELECT *
            FROM read_csv_auto(?, sample_size=?, encoding=?)
            """,
            [str(file_path), sample_size, encoding],
        ).fetchall()

        columns = [
            ColumnInfo(name=row[0], dtype=_display_type(row[1]))
            for row in describe_rows
        ]

        return FileMetadata(
            name=file_path.name,
            path=file_path,
            size_bytes=stat.st_size,
            size_human=format_size(stat.st_size),
            row_count=row_count,
            columns=columns,
            encoding=encoding,
            encoding_warning=encoding_warning,
            inferred_from_sample=row_count > sample_size,
            sample_size=sample_size,
        )
    except CsvInspectionError:
        raise
    except duckdb.Error as exc:
        raise CsvInspectionError(f"Unable to parse CSV file: {exc}") from exc
    finally:
        conn.close()


def get_sample_rows(
    file_path: Path,
    *,
    limit: int = 10,
    sample_size: int = 10_000,
) -> SamplePreview:
    if file_path.stat().st_size == 0:
        return SamplePreview(columns=[], rows=[])

    conn = duckdb.connect()

    try:
        encoding, _ = _resolve_encoding(conn, file_path, sample_size)

        relation = conn.execute(
            """
            SELECT *
            FROM read_csv_auto(?, sample_size=?, encoding=?)
            LIMIT ?
            """,
            [str(file_path), sample_size, encoding, limit],
        )
        columns = [col[0] for col in relation.description]
        rows = [
            [_format_cell(value) for value in row]
            for row in relation.fetchall()
        ]

        return SamplePreview(columns=columns, rows=rows)
    except CsvInspectionError:
        raise
    except duckdb.Error as exc:
        raise CsvInspectionError(f"Unable to read sample rows: {exc}") from exc
    finally:
        conn.close()
