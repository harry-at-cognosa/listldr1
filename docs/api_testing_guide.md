# SQM Template Loader API — Testing Guide

## Prerequisites

- Python virtual environment at `./venv/` with dependencies installed
- PostgreSQL running on localhost with `listmgr1` database accessible
- A `.env` file in the project root (copy from `.env.example` if missing)

### Environment Variables (`.env`)

```
LISTLDR_DB_HOST=localhost
LISTLDR_DB_PORT=5432
LISTLDR_DB_USER=postgres
LISTLDR_DB_PASSWORD=
LISTLDR_DB_NAME=listmgr1
LISTLDR_CORS_ORIGINS=http://localhost:3000
```

These are read at server startup. If your database credentials differ from the defaults, edit `.env` before starting the server.

### CORS

The API includes CORS middleware so it can be called from a browser or a Node.js backend running on a different origin.

- **Default allowed origin**: `http://localhost:3000`
- Set `LISTLDR_CORS_ORIGINS` in `.env` to override. Multiple origins can be comma-separated:
  ```
  LISTLDR_CORS_ORIGINS=http://localhost:3000,https://app.example.com
  ```
- Only `POST` requests are allowed (the only method the API uses).
- Changes to CORS origins require a server restart.

---

## Starting the Server

All commands assume you are in the project root directory (`1_listldr/`).

```bash
./venv/bin/uvicorn api.app:app --reload
```

- Default address: `http://127.0.0.1:8000`
- `--reload` watches for file changes and restarts automatically (development only)
- To use a different port: `--port 9000`
- To allow external access: `--host 0.0.0.0`

On successful startup you should see:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

Press `Ctrl+C` to stop the server.

---

## Interactive API Docs

FastAPI auto-generates interactive documentation:

- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

You can upload files and test the endpoint directly from the Swagger UI in your browser.

---

## API Endpoint

```
POST /api/v1/templates/load
Content-Type: multipart/form-data
```

### Request Fields

| Field          | Required | Description                                          |
|----------------|----------|------------------------------------------------------|
| `file`         | Yes      | The `.docx` template file                            |
| `country`      | Yes      | Country abbreviation (e.g. `CHE`, `USA`)             |
| `currency`     | Yes      | Currency symbol (e.g. `CHF`, `USD`)                  |
| `product_line` | No       | 3-char override (e.g. `ECM`); if omitted, parsed from filename |
| `dry_run`      | No       | `true` to parse/validate only, no database writes (default: `false`) |

### Response (200 — Success)

```json
{
  "status": "success",
  "template": {
    "plsqt_id": 41,
    "template_name": "ECM AP 2 E",
    "product_line": "ECM",
    "is_new": false,
    "section_count": 9,
    "blob_id": 14,
    "sections": [
      {"sequence": 0, "heading": "Cover Page", "section_type_id": 13},
      {"sequence": 1, "heading": "Principal Characteristics", "section_type_id": 6},
      ...
    ]
  }
}
```

- `is_new`: `true` if template was created, `false` if updated
- `plsqt_id` and `blob_id` are `0` in dry-run mode

### Error Responses

| Code | Meaning                                                |
|------|--------------------------------------------------------|
| 400  | Validation error (bad country, unknown product line, section mismatch, non-.docx file) |
| 422  | Malformed request (missing required field)             |
| 500  | Unexpected server error                                |

---

## Testing with curl

### Dry-run (parse and validate, no database writes)

```bash
curl -s -X POST 'http://127.0.0.1:8000/api/v1/templates/load' \
  -F 'file=@/Users/harry/1_listldr_files/inputs/che/ECM AP 2 E.docx' \
  -F 'country=CHE' \
  -F 'currency=CHF' \
  -F 'dry_run=true' | python3 -m json.tool
```

### Real upload (writes to database)

```bash
curl -s -X POST 'http://127.0.0.1:8000/api/v1/templates/load' \
  -F 'file=@/Users/harry/1_listldr_files/inputs/che/ECM AP 2 E.docx' \
  -F 'country=CHE' \
  -F 'currency=CHF' | python3 -m json.tool
```

### With explicit product line override

```bash
curl -s -X POST 'http://127.0.0.1:8000/api/v1/templates/load' \
  -F 'file=@/path/to/template.docx' \
  -F 'country=CHE' \
  -F 'currency=CHF' \
  -F 'product_line=ECM' | python3 -m json.tool
```

### Expect an error (bad country)

```bash
curl -s -X POST 'http://127.0.0.1:8000/api/v1/templates/load' \
  -F 'file=@/Users/harry/1_listldr_files/inputs/che/ECM AP 2 E.docx' \
  -F 'country=XXX' \
  -F 'currency=CHF' | python3 -m json.tool
```

Expected response:

```json
{"detail": "Country not found: XXX"}
```

### curl tips

- File paths with spaces must be inside **single quotes** in the `-F` argument: `-F 'file=@/path/with spaces/file.docx'`
- `| python3 -m json.tool` pretty-prints the JSON response (optional)
- Add `-v` for verbose output including HTTP headers

---

## Comparison with the Batch CLI

| Feature                | Batch CLI                                        | API                                     |
|------------------------|--------------------------------------------------|-----------------------------------------|
| Start command          | `python SQM_load_quote_template_docx_file_v2.0.py` | `./venv/bin/uvicorn api.app:app --reload` |
| Config source          | `conf/listldr_sqt.ini` + CLI args               | `.env` + request fields                 |
| Input                  | Directory of `.docx` files                       | Single file upload per request          |
| Dry-run                | `--noupdate`                                     | `dry_run=true` form field               |
| Audit trail user       | `SQM_loader`                                     | `SQM_api`                               |
| Transaction scope      | Per file (commit after each)                     | Per request                             |
| Output                 | Log file + console                               | JSON response                           |
| DB connection          | Single connection for entire run                  | Connection pool (1–10 connections)       |
