from pathlib import Path


class CsvFileNotFoundError(Exception):
    pass


def resolve_csv_file(data_dir: Path, filename: str) -> Path:
    if not filename:
        raise CsvFileNotFoundError("Empty filename")

    if "/" in filename or "\\" in filename or ".." in filename:
        raise CsvFileNotFoundError("Invalid filename")

    if not filename.lower().endswith(".csv"):
        raise CsvFileNotFoundError("Not a CSV file")

    resolved_dir = data_dir.resolve()
    file_path = (resolved_dir / filename).resolve()

    try:
        file_path.relative_to(resolved_dir)
    except ValueError as exc:
        raise CsvFileNotFoundError("File outside data directory") from exc

    if not file_path.is_file():
        raise CsvFileNotFoundError("File not found")

    return file_path
