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
│   │   └── files.py      # Stage 1: file list routes
│   ├── services/
│   │   └── file_discovery.py  # Stage 1: scan CSV folder
│   └── templates/
│       ├── base.html     # shared layout
│       └── index.html    # Stage 1: file list page
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
| C3 | Encoding | UTF-8 default (relevant from Stage 2) |
| C4 | Git ignores | `data/csv/*.csv`, `db/*.db`, `.env` |

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

## Future stages (placeholder)

The following stages are approved at a high level but not yet detailed in this file. They will be added here before each implementation phase.

| Stage | Goal | Status |
|-------|------|--------|
| 2 | File metadata and 10-row sample preview | Pending detail |
| 3 | Paginated full content viewer | Pending detail |
| 4 | Column manipulation and SQLite import | Pending detail |
