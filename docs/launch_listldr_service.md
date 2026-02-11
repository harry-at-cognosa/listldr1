# Launching the listldr FastAPI Service

Step-by-step instructions for running the listldr API service on macOS for local development and testing.

## Prerequisites

- Python 3.12 (the existing `venv/` was built with 3.12)
- PostgreSQL running locally with the `listmgr1` database accessible
- The project cloned to `/Users/harry/1_listldr`

## Step 1: Open a terminal and cd to the project root

The uvicorn command must be run from the **project root** (not `api/`), because the app import path is `api.app:app` and the `listldr` package is resolved relative to the project root.

```bash
cd /Users/harry/1_listldr
```

## Step 2: Activate the virtual environment

> **Note:** The activation command below is specific to this M1 Mac where the project lives at `/Users/harry/1_listldr`.

The project already has a `venv/` directory (Python 3.12). Activate it so that all installed packages are available:

```bash
source /Users/harry/1_listldr/venv/bin/activate
```

You should see `(venv)` in your terminal prompt.

### If packages are missing or venv doesn't exist

```bash
python3 -m venv /Users/harry/1_listldr/venv
source /Users/harry/1_listldr/venv/bin/activate
pip install -r requirements.txt
```

## Step 3: Create your `.env` file

The FastAPI app uses `python-dotenv` to load environment variables from a `.env` file **in the project root**. A template is provided in `.env.example`. Copy it and fill in your values:

```bash
cp .env.example .env
```

Then edit `.env` with your actual database credentials:

```ini
# Database connection for the FastAPI service
LISTLDR_DB_HOST=localhost
LISTLDR_DB_PORT=5432
LISTLDR_DB_USER=postgres
LISTLDR_DB_PASSWORD=your_actual_password_here
LISTLDR_DB_NAME=listmgr1

# CORS: comma-separated origins allowed to call the API
# This must include the origin of your Express/Node.js frontend
LISTLDR_CORS_ORIGINS=http://localhost:3000
```

### Notes on each variable

| Variable | Purpose | Default if omitted |
|---|---|---|
| `LISTLDR_DB_HOST` | PostgreSQL hostname | `localhost` |
| `LISTLDR_DB_PORT` | PostgreSQL port | `5432` |
| `LISTLDR_DB_USER` | Database user | `postgres` |
| `LISTLDR_DB_PASSWORD` | Database password | *(empty string)* |
| `LISTLDR_DB_NAME` | Database name | `listmgr1` |
| `LISTLDR_CORS_ORIGINS` | Allowed CORS origins (comma-separated) | `http://localhost:3000` |

### CORS origin

Since your Node.js Express frontend runs on the same machine, `http://localhost:3000` is likely correct (assuming Express serves the frontend on port 3000). If your Express app uses a different port, update this value. Multiple origins can be comma-separated:

```ini
LISTLDR_CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Security

The `.env` file is already listed in `.gitignore`, so it will not be committed to the repo. Never commit real credentials.

## Step 4: Verify PostgreSQL is reachable

Before launching the service, confirm you can connect to the database with the credentials you put in `.env`:

```bash
psql -h localhost -p 5432 -U postgres -d listmgr1 -c "SELECT 1"
```

If this fails, fix your PostgreSQL setup or credentials before proceeding. The FastAPI app will fail at startup if it cannot connect — it creates a connection pool and pre-fetches section types during initialization.

## Step 5: Launch the service

From the project root, with the venv activated:

```bash
uvicorn api.app:app --reload --host 127.0.0.1 --port 8000
```

### What each flag does

| Flag | Purpose |
|---|---|
| `api.app:app` | Python import path: module `api.app`, variable `app` |
| `--reload` | Auto-restart on code changes (development only) |
| `--host 127.0.0.1` | Listen on localhost only (safe for local dev) |
| `--port 8000` | The port the API listens on (default 8000) |

### What happens at startup

1. `load_dotenv()` reads your `.env` file
2. The lifespan handler creates a **psycopg2 connection pool** (1-10 connections) to PostgreSQL
3. It **pre-fetches all section types** from `plsqts_type` and caches them in `app.state`
4. CORS middleware is configured using `LISTLDR_CORS_ORIGINS`

If startup succeeds you will see:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using StatReload
```

## Step 6: Verify the service is running

Open a browser or use curl:

```bash
curl http://127.0.0.1:8000/docs
```

FastAPI auto-generates interactive API docs at `/docs` (Swagger UI) and `/redoc` (ReDoc). These are useful for testing the endpoints manually.

## Available API Endpoints

Once running, the service exposes two endpoints:

### POST `/api/v1/templates/load`

Upload a `.docx` template file for parsing and storage.

- **Content-Type:** `multipart/form-data`
- **Form fields:** `file` (the .docx), `country`, `currency`, `product_line` (optional), `dry_run` (optional, default false)
- **Returns:** JSON with template ID, name, sections, blob ID

**Testing via Swagger UI (easiest for file uploads):**

Since the POST endpoint requires a file upload, you cannot test it from a browser URL bar. The simplest way is to use the built-in Swagger UI:

1. Open `http://127.0.0.1:8000/docs` in your browser
2. Click on the **POST /api/v1/templates/load** endpoint to expand it
3. Click the **"Try it out"** button
4. Click **"Choose File"** to select your `.docx` file
5. Fill in `country` (e.g. `USA`), `currency` (e.g. `USD`), and set `dry_run` to `true` for a safe test
6. Click **"Execute"**
7. The response will appear below with the template ID, sections found, and blob ID

**Testing via curl:**

Example curl (upload a file with dry_run to test without writing to the DB):

```bash
curl -X POST http://127.0.0.1:8000/api/v1/templates/load \
  -F "file=@/path/to/your/template.docx" \
  -F "country=USA" \
  -F "currency=USD" \
  -F "dry_run=true"
```

Example for Switzerland (with actual DB write):

```bash
curl -X POST http://127.0.0.1:8000/api/v1/templates/load \
  -F "file=@/path/to/your/template.docx" \
  -F "country=CHE" \
  -F "currency=CHF" \
  -F "dry_run=false"
```

### GET `/api/v1/templates/{plsqt_id}/sections/{seqn}/docx`

Extract a single section from a stored template as a `.docx` download.

- **Path params:** `plsqt_id` (template ID), `seqn` (section sequence number)
- **Returns:** `.docx` file as binary download

**In a browser** — just navigate to the URL directly (e.g. section 4 of template 40):

```
http://127.0.0.1:8000/api/v1/templates/40/sections/4/docx
```

**Download via curl** (saves the file using the server-provided filename):

```bash
curl -O -J http://127.0.0.1:8000/api/v1/templates/40/sections/4/docx
```

**Check response headers only** (no download):

```bash
curl -I http://127.0.0.1:8000/api/v1/templates/40/sections/4/docx
```

## Stopping the Service

Press `Ctrl+C` in the terminal. The lifespan shutdown handler will close all pooled database connections.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `ModuleNotFoundError: No module named 'listldr'` | You are not in the project root, or the venv is not activated |
| `ModuleNotFoundError: No module named 'fastapi'` | Run `pip install -r requirements.txt` inside the activated venv |
| Connection refused / psycopg2 error at startup | PostgreSQL is not running, or `.env` credentials are wrong |
| CORS errors from the browser | `LISTLDR_CORS_ORIGINS` does not include the frontend's origin |
| Port 8000 already in use | Another process is using port 8000; use `--port 8001` or kill the other process |
