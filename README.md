# DataFilesManager

Managing data from heavy csv files.

## Getting Started

1. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure the environment:

   ```bash
   cp .env.example .env
   ```

4. Place CSV files in `data/csv/`.

5. Start the development server:

   ```bash
   uvicorn app.main:app --reload
   ```

6. Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.
