# DataFilesManager — Implementation Plan

This document tracks the implementation plan stage by stage. Only the current stage is fully specified; future stages are added here as they are approved.

---

## Approved stack

| Layer | Choice | Notes |
|-------|--------|-------|
| Web framework | FastAPI | Local dev via `uvicorn` |
| UI | Jinja2 templates + HTMX | No separate frontend build |
| CSV engine | DuckDB | Used from Stage 2 onward |
| Local DB | SQLite | Used from Stage 4 onward |
| Config | `.env` + `pydantic-settings` | CSV folder path and settings |

## Project layout

```
DataFilesManager/
├── data/
│   └── csv/              # dedicated CSV folder (user places files here)
├── app/
│   ├── main.py           # FastAPI entry point
│   ├── config.py         # settings (CSV_DATA_DIR, etc.)
│   ├── routes/
│   │   └── files.py           # Stage 1–3: list, detail, and browse routes
│   ├── services/
│   │   ├── file_discovery.py  # Stage 1: scan CSV folder
│   │   ├── formatting.py      # Shared formatting helpers
│   │   ├── path_utils.py      # Stage 2: safe filename → path resolution
│   │   ├── csv_inspection.py  # Stage 2: metadata + sample rows via DuckDB
│   │   └── csv_pagination.py  # Stage 3: paginated row reads via DuckDB
│   └── templates/
│       ├── base.html          # shared layout
│       ├── index.html         # Stage 1: file list page
│       ├── file_detail.html   # Stage 2: file metadata + sample preview
│       └── file_browse.html   # Stage 3: paginated content viewer
├── db/                   # SQLite storage (Stage 4; folder created early)
├── PLAN.md               # this file
├── requirements.txt
├── .env.example
└── README.md
```

## Cross-cutting decisions

| ID | Decision | Value |
|----|----------|-------|
| C1 | CSV folder location | `data/csv/` inside project; overridable via `.env` |
| C2 | Supported formats | `.csv` only |
| C3 | Encoding | UTF-8 default; fallback to `latin-1` with a visible warning (Stage 2) |
| C4 | Git ignores | `data/csv/*.csv`, `db/*.db`, `.env` |
| C5 | Path safety | User-supplied filenames resolved inside `CSV_DATA_DIR` only (Stage 2) |

---

## Stage 1 — List CSV files from dedicated folder

**Status:** Implemented

**Goal:** Run the app locally and see all CSV files in the configured folder.

### Sub-tasks

#### 1.1 — Project bootstrap

Create the foundational project files and dependencies.

**Files to create:**

| File | Purpose |
|------|---------|
| `requirements.txt` | Pin runtime dependencies |
| `.env.example` | Document required environment variables |
| `app/main.py` | FastAPI app instance, template engine, route registration |
| `app/config.py` | `Settings` class reading `CSV_DATA_DIR` from `.env` |
| `app/__init__.py` | Package marker |
| `data/csv/.gitkeep` | Ensure folder exists in repo |
| `db/.gitkeep` | Ensure folder exists for future SQLite use |

**Dependencies (requirements.txt):**

```
fastapi
uvicorn[standard]
jinja2
python-multipart
pydantic-settings
python-dotenv
```

> DuckDB and SQLite driver are deferred to later stages.

**Environment variables (.env.example):**

```
CSV_DATA_DIR=data/csv
```

**app/config.py behavior:**

- Load settings from `.env` via `pydantic-settings`
- Default `CSV_DATA_DIR` to `data/csv` (relative to project root)
- Resolve to absolute path at runtime
- Expose a `get_settings()` helper (cached singleton)

**app/main.py behavior:**

- Create FastAPI app
- Mount Jinja2 templates from `app/templates/`
- Register `files` router
- Root route redirects or renders file list (via router)

---

#### 1.2 — Config service validation

Validate that the CSV data directory exists and is readable before scanning.

**Logic (in `file_discovery.py` or `config.py`):**

- On startup or first request, check `CSV_DATA_DIR` exists
- If missing: return a clear error state (do not crash the app)
- If not readable: return permission error message

---

#### 1.3 — File discovery service

**File:** `app/services/file_discovery.py`

**Function:** `list_csv_files(data_dir: Path) -> list[FileInfo]`

**FileInfo fields:**

| Field | Type | Source |
|-------|------|--------|
| `name` | str | Filename only (e.g. `sales.csv`) |
| `size_bytes` | int | `os.path.getsize()` |
| `size_human` | str | Formatted (e.g. `1.2 MB`) |
| `modified_at` | datetime | `os.path.getmtime()` |

**Rules:**

- Scan only `*.csv` files (case-insensitive: `.csv`, `.CSV`)
- Ignore subdirectories (flat folder only for Stage 1)
- Ignore hidden files (names starting with `.`)
- Sort by `modified_at` descending (newest first)
- Return empty list if folder is empty (not an error)

---

#### 1.4 — Routes and list UI

**File:** `app/routes/files.py`

**Endpoints:**

| Method | Path | Response |
|--------|------|----------|
| `GET` | `/` | HTML file list page |

**Template:** `app/templates/index.html`

**UI requirements:**

- Page title: "Data Files Manager"
- Table columns: File name, Size, Last modified
- Each row is a file entry (clickable link deferred to Stage 2 — display name only for now)
- Empty state message: *"No CSV files found. Place `.csv` files in the `data/csv/` folder."*
- Error state: show message if folder missing or unreadable
- Show resolved CSV folder path in the page footer or header (helps debugging)

**Template:** `app/templates/base.html`

- Minimal clean layout (no CSS framework required; simple inline or `<style>` block)
- Header with app name
- `{% block content %}` for child templates

---

#### 1.5 — Error handling

| Condition | Behavior |
|-----------|----------|
| `CSV_DATA_DIR` does not exist | Show warning banner; empty file list |
| Folder not readable | Show error banner with permission message |
| No CSV files in folder | Show empty state (not an error) |
| Unexpected scan error | Log error; show generic message to user |

**Security note for Stage 1:**

- No user-supplied file paths yet
- Filename display only (no file content read)

---

### Acceptance criteria

- [ ] App starts locally with `uvicorn app.main:app --reload`
- [ ] CSV files placed in `data/csv/` appear on the home page
- [ ] Non-CSV files in the folder are ignored
- [ ] Empty folder shows a helpful empty-state message
- [ ] Missing folder shows a clear warning (app does not crash)
- [ ] File list shows name, human-readable size, and last modified date
- [ ] Files are sorted newest-first

---

### Commands (run by user)

```bash
# 1. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env

# 4. (Optional) Add a test CSV for verification
echo "id,name\n1,Alice\n2,Bob" > data/csv/sample.csv

# 5. Start the development server
uvicorn app.main:app --reload

# 6. Open in browser
open http://127.0.0.1:8000
```

---

### Git / .gitignore updates

Add to `.gitignore` (if not already present):

```
data/csv/*.csv
db/*.db
.env
```

Keep `data/csv/.gitkeep` and `db/.gitkeep` tracked.

---

### README updates (after implementation)

Add a short "Getting Started" section covering:

1. Virtual env setup
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env`
4. Place CSV files in `data/csv/`
5. Run `uvicorn app.main:app --reload`
6. Open `http://127.0.0.1:8000`

---

## Stage 2 — File metadata and sample preview

**Status:** Implemented

**Goal:** Select a CSV file from the list and view its metadata (size, row count, columns, types) plus a 10-row sample preview.

**Builds on:** Stage 1 file list, `CSV_DATA_DIR` config, existing templates and error-banner patterns.

### Design decisions (proposed defaults)

| Topic | Decision | Rationale |
|-------|----------|-----------|
| CSV engine | DuckDB `read_csv_auto` | Approved stack; reads CSVs efficiently without loading full file into app memory |
| Row count | Full-file `COUNT(*)` via DuckDB | Accurate (handles quoted newlines); may take seconds on very large files |
| Type inference | Sample first 10,000 rows | Fast on large files; UI notes types are *"inferred from sample"* |
| Sample rows | First 10 data rows | Matches original spec |
| Encoding | UTF-8 first; fallback to `latin-1` | Matches cross-cutting decision C3; show warning if fallback used |
| Loading UX | Synchronous request with *"Analyzing…"* page state | Simple for local tool; async/HTMX polling deferred unless needed |
| Invalid filename | HTTP 404 | No path traversal; no leaking of folder contents |

---

### Sub-tasks

#### 2.1 — Add DuckDB dependency

**File:** `requirements.txt`

Add:

```
duckdb
```

**Command (run by user after approval):**

```bash
pip install duckdb
```

---

#### 2.2 — Safe file path resolution

**File:** `app/services/path_utils.py`

**Function:** `resolve_csv_file(data_dir: Path, filename: str) -> Path`

**Rules:**

- Reject empty filenames
- Reject filenames containing `/`, `\`, or `..`
- Reject filenames not ending in `.csv` (case-insensitive)
- Resolve `data_dir / filename` and verify the result is still inside `data_dir` (use `.resolve()` + `is_relative_to()`)
- Verify the file exists and is a regular file
- Raise a dedicated exception (e.g. `FileNotFoundError` or custom `CsvFileNotFoundError`) for the route to map to 404

**Reuse:** Called by both the detail route and `csv_inspection` service.

---

#### 2.3 — CSV inspection service

**File:** `app/services/csv_inspection.py`

**Dataclasses:**

| Class | Fields |
|-------|--------|
| `ColumnInfo` | `name: str`, `dtype: str` |
| `FileMetadata` | `name: str`, `path: Path`, `size_bytes: int`, `size_human: str`, `row_count: int`, `columns: list[ColumnInfo]`, `encoding: str`, `encoding_warning: str \| None`, `inferred_from_sample: bool` |
| `SamplePreview` | `columns: list[str]`, `rows: list[list[str]]` (max 10 rows; cell values as display strings) |

**Function:** `inspect_csv(file_path: Path, *, sample_size: int = 10_000) -> FileMetadata`

**Behavior:**

1. Read `size_bytes` / `size_human` via `stat()` (reuse `_format_size` — extract to shared helper or import from `file_discovery`)
2. Open an in-memory DuckDB connection
3. Attempt read with UTF-8 encoding
4. On encoding failure, retry with `latin-1` and set `encoding_warning`
5. Query row count: `SELECT COUNT(*) FROM read_csv_auto(?, sample_size=?)`
6. Query schema: `DESCRIBE SELECT * FROM read_csv_auto(?, sample_size=?)` → map DuckDB types to display labels (e.g. `VARCHAR` → `string`, `BIGINT` → `integer`, `DOUBLE` → `float`, `BOOLEAN` → `boolean`, `DATE` → `date`, `TIMESTAMP` → `datetime`)
7. Set `inferred_from_sample=True` when file has more rows than `sample_size` (or always `True` with note — see open question below)

**Function:** `get_sample_rows(file_path: Path, *, limit: int = 10, sample_size: int = 10_000) -> SamplePreview`

**Behavior:**

- `SELECT * FROM read_csv_auto(?, sample_size=?) LIMIT 10`
- Convert all cell values to strings for template rendering (`None` → empty string or `"null"` — pick `""` for cleaner display)
- Return column names + row matrix

**Error handling:**

- DuckDB parse errors → raise `CsvInspectionError` with user-friendly message
- Empty file or header-only file → return `row_count=0`, empty columns/rows with clear metadata (not a crash)

---

#### 2.4 — Config extension (optional settings)

**File:** `app/config.py`

Add optional setting:

| Setting | Default | Purpose |
|---------|---------|---------|
| `csv_type_inference_sample_size` | `10000` | Rows DuckDB samples for type inference |

**File:** `.env.example`

```
CSV_TYPE_INFERENCE_SAMPLE_SIZE=10000
```

---

#### 2.5 — File detail route

**File:** `app/routes/files.py`

**New endpoint:**

| Method | Path | Response |
|--------|------|----------|
| `GET` | `/files/{filename}` | HTML file detail page |

**Route behavior:**

1. Resolve safe path via `resolve_csv_file()` → 404 if invalid
2. Call `inspect_csv()` and `get_sample_rows()`
3. On `CsvInspectionError` → render detail page with error banner (not a 500)
4. Pass metadata + sample to `file_detail.html`

**Stage 1 update in same file:**

- No changes to `GET /` logic beyond linking filenames in the template

---

#### 2.6 — File detail UI

**File:** `app/templates/file_detail.html`

**Sections:**

1. **Breadcrumb / back link** — `← Back to file list` linking to `/`
2. **Summary cards** (or definition list) showing:
   - File name
   - File size (human-readable)
   - Row count (formatted with thousands separator)
   - Encoding (+ warning banner if fallback was used)
3. **Schema table** — columns: `Column name`, `Type`
   - Footnote if `inferred_from_sample`: *"Types inferred from first N rows"*
4. **Sample preview table** — first 10 rows, all columns
   - Horizontal scroll if many columns
5. **Error banner** — malformed/unreadable CSV message when inspection fails

**File:** `app/templates/index.html` (update)

- Wrap filename in `<a href="/files/{{ file.name }}">` (URL-encode filename if needed — use `urlencode` filter or `path` helper)

**File:** `app/templates/base.html` (minor update)

- Add styles for summary cards, schema table, sample table, breadcrumb link
- Reuse existing `.banner`, `table`, `.empty-state` patterns

---

#### 2.7 — Error handling

| Condition | Behavior |
|-----------|----------|
| Filename contains `..` or path separators | HTTP 404 |
| File not in `CSV_DATA_DIR` | HTTP 404 |
| File does not exist | HTTP 404 |
| Non-`.csv` extension | HTTP 404 |
| DuckDB cannot parse CSV | Error banner on detail page with message |
| Empty CSV file | Show zero rows, empty schema/sample with explanatory text |
| Encoding fallback used | Warning banner: *"UTF-8 decode failed; read as latin-1"* |
| Unexpected error | Log exception; generic error banner (no stack trace to user) |

**Security:**

- Never pass user input directly as a filesystem path
- Only the basename is accepted; always resolved under `CSV_DATA_DIR`

---

### Acceptance criteria

- [ ] Clicking a filename on the home page opens `/files/{filename}`
- [ ] Detail page shows file size, row count, column names, and column types
- [ ] Detail page shows a 10-row sample with values
- [ ] Types note indicates they were inferred from a sample (when applicable)
- [ ] Invalid or non-existent filenames return 404
- [ ] Malformed CSV shows a clear error (app does not crash)
- [ ] Large CSV (e.g. 100 MB+) completes inspection without loading entire file into Python memory
- [ ] `← Back to file list` returns to home page
- [ ] Non-CSV files remain inaccessible via URL manipulation

---

### Commands (run by user)

```bash
# 1. Install new dependency (with venv active)
pip install duckdb

# 2. Restart the dev server
uvicorn app.main:app --reload

# 3. Open a file detail page
open http://127.0.0.1:8000/files/sample.csv
```

---

### Open questions (confirm before implementation)

| # | Question | Recommendation |
|---|----------|----------------|
| Q1 | Row count on very large files may take several seconds — acceptable for Stage 2? | Yes; show file name immediately, add *"Analyzing…"* note in template title area or a simple loading message before heavy query completes |
| Q2 | Always show *"inferred from sample"* note, or only when `row_count > sample_size`? | Only when file exceeds sample size |
| Q3 | `null` values in sample — display as empty cell or literal `"null"`? | Empty cell |
| Q4 | Delimiter auto-detection via DuckDB default — OK for Stage 2? | Yes (DuckDB handles `,`, `;`, tabs in many cases) |

---

## Stage 3 — Paginated full content viewer

**Status:** Implemented

**Goal:** Browse the full contents of a selected CSV file page by page, without loading the entire file into memory.

**Builds on:** Stage 2 file detail page, `path_utils`, DuckDB `read_csv_auto`, encoding fallback (C3), and existing table/banner UI patterns.

### Design decisions (proposed defaults)

| Topic | Decision | Rationale |
|-------|----------|-----------|
| Browse URL | `GET /files/{filename}/browse?page=1&page_size=50` | RESTful, bookmarkable, consistent with existing `/files/{filename}` route |
| Pagination query | DuckDB `LIMIT` + `OFFSET` on `read_csv_auto` | Matches approved stack; only fetches the rows needed for the current page |
| Default page size | `50` | Balanced for wide tables and screen space |
| Page size options | `25`, `50`, `100` | Matches original spec; validated server-side |
| Total row count | Reuse `inspect_csv()` row count on browse page load | Accurate count already implemented in Stage 2; avoids new counting logic |
| Encoding | Reuse existing UTF-8 → `latin-1` fallback | Consistent reads across detail and browse views |
| Navigation UX | Full page reload via query params | Consistent with Stages 1–2; HTMX partial updates deferred |
| Page controls | Previous / Next + page indicator | Simple and sufficient for v1 |
| Row numbers | Show absolute row number as first column | Helps orient user within large files |
| Table header | Sticky header on vertical scroll | Improves readability for wide/long pages |
| Sortable columns | Deferred | Out of scope for Stage 3 v1 |
| Invalid `page` | Clamp to valid range (`1` … `total_pages`) | Better UX than error page when user bookmarks an out-of-range page |
| Invalid `page_size` | Fall back to default (`50`) | Ignore unsupported values silently |

**Known limitation:** DuckDB `OFFSET` on CSV files may scan skipped rows, so very deep pages (e.g. page 10,000) can be slower. Acceptable for Stage 3 local use; can optimize later (e.g. cached DuckDB table).

---

### Sub-tasks

#### 3.1 — Shared CSV read helpers (light refactor)

**File:** `app/services/csv_inspection.py` (update)

Extract reusable internals so pagination does not duplicate encoding logic:

| Helper | Purpose |
|--------|---------|
| `_resolve_encoding(...)` | Already exists — keep as shared internal |
| `_format_cell(...)` | Already exists — reuse for paginated rows |
| `get_csv_read_context(file_path, sample_size)` *(new, optional)* | Returns resolved `encoding` + `encoding_warning` in one DuckDB connection |

**Goal:** `csv_pagination.py` reuses the same encoding fallback behavior as Stage 2 without copy-paste.

> Full inspection/pagination merge (single DuckDB connection) remains a future optimization — not required for Stage 3.

---

#### 3.2 — Pagination service

**File:** `app/services/csv_pagination.py`

**Dataclass:** `PaginatedRows`

| Field | Type | Description |
|-------|------|-------------|
| `columns` | `list[str]` | Column headers |
| `rows` | `list[list[str]]` | Cell values as display strings (same rules as Stage 2 sample) |
| `page` | `int` | Current page (1-based) |
| `page_size` | `int` | Rows per page |
| `total_rows` | `int` | Total data rows in file |
| `total_pages` | `int` | `ceil(total_rows / page_size)`, minimum `1` when `total_rows == 0` |
| `start_row` | `int` | Absolute index of first row on page (1-based; `0` when empty) |
| `end_row` | `int` | Absolute index of last row on page (`0` when empty) |
| `encoding` | `str` | Encoding used for read |
| `encoding_warning` | `str \| None` | Set when `latin-1` fallback is used |

**Function:** `get_paginated_rows(file_path: Path, *, page: int, page_size: int, sample_size: int, total_rows: int | None = None) -> PaginatedRows`

**Behavior:**

1. Validate and normalize `page` and `page_size`
2. If `total_rows` not provided, obtain via `inspect_csv()` (or a lighter count helper)
3. Compute `offset = (page - 1) * page_size`
4. Open DuckDB connection; resolve encoding (reuse Stage 2 helper)
5. Query:

   ```sql
   SELECT *
   FROM read_csv_auto(?, sample_size=?, encoding=?)
   LIMIT ? OFFSET ?
   ```

6. Format cells with `_format_cell`
7. Compute `start_row`, `end_row`, `total_pages`
8. Return `PaginatedRows`

**Edge cases:**

| Case | Behavior |
|------|----------|
| Empty file | `total_rows=0`, empty table, `total_pages=1`, empty-state message |
| `page` beyond last page | Clamp to last page |
| `page` < 1 | Clamp to `1` |
| `page_size` not in allowed set | Use default `50` |
| Parse error | Raise `CsvInspectionError` (reuse existing exception) |

---

#### 3.3 — Config extension

**File:** `app/config.py`

| Setting | Default | Purpose |
|---------|---------|---------|
| `csv_default_page_size` | `50` | Default rows per page |
| `csv_page_size_options` | `[25, 50, 100]` | Allowed page sizes (can be a constant in code instead of env) |

**File:** `.env.example` (optional)

```
CSV_DEFAULT_PAGE_SIZE=50
```

---

#### 3.4 — Browse route

**File:** `app/routes/files.py`

**New endpoint:**

| Method | Path | Response |
|--------|------|----------|
| `GET` | `/files/{filename}/browse` | HTML paginated content page |

**Query parameters:**

| Param | Type | Default | Rules |
|-------|------|---------|-------|
| `page` | int | `1` | Clamp to valid range |
| `page_size` | int | `50` | Must be one of `25`, `50`, `100` |

**Route behavior:**

1. Resolve safe path via `resolve_csv_file()` → 404 if invalid
2. Parse and validate `page` / `page_size` query params
3. Call `get_paginated_rows()` (pass `settings.csv_type_inference_sample_size`)
4. On `CsvInspectionError` → render browse page with error banner
5. Pass pagination data to `file_browse.html`

---

#### 3.5 — Browse UI

**File:** `app/templates/file_browse.html`

**Sections:**

1. **Breadcrumb** — `← Back to file details` → `/files/{filename}`
2. **Page title** — filename + "Browse rows"
3. **Encoding warning banner** — if `latin-1` fallback used
4. **Pagination summary** — e.g. *"Rows 51–100 of 12,345"* and *"Page 2 of 247"*
5. **Page size selector** — `<select>` or button group for 25 / 50 / 100 (submits via GET, resets to page 1 on change)
6. **Data table** — sticky header, horizontal scroll for many columns
   - First column: row number (`start_row` + loop index)
   - Remaining columns: CSV values
7. **Pagination controls** — `← Previous` | `Next →` (disabled when at first/last page)
8. **Empty state** — when file has no rows
9. **Error banner** — when CSV cannot be read

**File:** `app/templates/file_detail.html` (update)

- Add action link below sample preview: **"Browse all rows →"** linking to `/files/{filename}/browse`

**File:** `app/templates/base.html` (update)

- Add styles for pagination bar, page-size selector, disabled nav buttons, sticky `thead`, row-number column

---

#### 3.6 — Query param helpers

**File:** `app/routes/files.py` or `app/services/csv_pagination.py`

**Functions:**

| Function | Purpose |
|----------|---------|
| `normalize_page(page: int, total_pages: int) -> int` | Clamp page to `1 … total_pages` |
| `normalize_page_size(page_size: int, allowed: list[int], default: int) -> int` | Return valid page size |

Keeps validation logic out of the template and route body.

---

#### 3.7 — Error handling

| Condition | Behavior |
|-----------|----------|
| Invalid / missing filename | HTTP 404 |
| `page=0` or negative | Clamp to `1` |
| `page` > `total_pages` | Clamp to `total_pages` |
| `page_size=999` | Fall back to default `50` |
| Empty CSV | Empty-state message; pagination shows *"Rows 0 of 0"* |
| DuckDB parse error | Error banner on browse page (no 500) |
| Encoding fallback | Warning banner (same message as Stage 2) |
| Unexpected error | Log exception; generic error banner |

**Security:**

- Reuse `resolve_csv_file()` — no new path traversal surface
- Query params affect only `LIMIT`/`OFFSET` integers, not file paths

---

### Acceptance criteria

- [ ] File detail page links to browse view ("Browse all rows")
- [ ] Browse page shows CSV content paginated (default 50 rows per page)
- [ ] User can switch page size between 25, 50, and 100
- [ ] Previous / Next navigation works and disables at boundaries
- [ ] Page indicator shows current page, total pages, and row range
- [ ] Row numbers are visible in the first column
- [ ] Table header stays visible on vertical scroll (sticky)
- [ ] Empty file shows a clear empty state
- [ ] Invalid filenames return 404
- [ ] Malformed CSV shows an error banner (app does not crash)
- [ ] Browsing a large file does not load the entire file into Python memory
- [ ] `← Back to file details` returns to the Stage 2 detail page

---

### Commands (run by user)

```bash
# 1. Restart the dev server (no new dependencies expected)
uvicorn app.main:app --reload

# 2. Open a file detail page, then click "Browse all rows"
open http://127.0.0.1:8000/files/sample.csv

# 3. Or go directly to browse view
open "http://127.0.0.1:8000/files/sample.csv/browse?page=1&page_size=50"
```

---

### Open questions (confirm before implementation)

| # | Question | Recommendation |
|---|----------|----------------|
| Q1 | Default page size of 50 OK? | Yes |
| Q2 | Prev/Next only for v1, or include jump-to-page input? | Prev/Next only for v1 |
| Q3 | Full page reload OK, or use HTMX for in-place table swap? | Full page reload (consistent with Stages 1–2) |
| Q4 | Show row number column? | Yes |
| Q5 | On browse page load, call `inspect_csv()` for `total_rows` (accurate but may be slow on first load)? | Yes for v1; caching optimization deferred |
| Q6 | Include First/Last page buttons in addition to Prev/Next? | Optional nice-to-have; Prev/Next sufficient for v1 |

---

## Future stages (placeholder)

The following stages are approved at a high level but not yet detailed in this file. They will be added here before each implementation phase.

| Stage | Goal | Status |
|-------|------|--------|
| 2 | File metadata and 10-row sample preview | Implemented |
| 3 | Paginated full content viewer | Implemented |
| 4 | Column manipulation and SQLite import | Pending detail |
