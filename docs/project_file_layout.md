# SQM Template Loader — Project File Layout

```
1_listldr/
├── listldr/                    # shared library package
│   ├── __init__.py
│   ├── config.py               # DBConfig from env / INI
│   ├── db.py                   # SQMDatabase, DBConfig
│   ├── logger.py               # SQMLogger
│   ├── models.py               # TemplateLoadResult, SectionInfo
│   ├── parser.py               # parse_docx_sections, extract_section_docx, TOC
│   ├── service.py              # load_template() — shared core logic
│   └── text_utils.py           # longest_common_substring
├── api/                        # FastAPI application
│   ├── __init__.py
│   ├── app.py                  # app, lifespan, CORS, pool
│   ├── dependencies.py         # get_db, get_section_types
│   ├── routes.py               # POST /load, GET /sections/{seqn}/docx
│   └── schemas.py              # Pydantic response models
├── cli/                        # batch entry points
│   ├── __init__.py
│   ├── archive_blobs.py        # blob cleanup program
│   └── batch_load.py           # template batch loader
├── conf/
│   └── listldr_sqt.ini         # batch/archive config
├── docs/
│   ├── api_testing_guide.md    # API + CLI + archive usage
│   ├── blob_archive_design.md  # archive program design
│   ├── project_file_layout.md  # this file
│   └── ...                     # specs, comparisons, etc.
├── SQM_load_quote_template_docx_file_v2.0.py  # shim → cli.batch_load
├── .env.example                # API env vars template
├── requirements.txt            # FastAPI, psycopg2, python-docx, etc.
├── alembic/                    # database migrations
├── sql_files/                  # ad-hoc SQL scripts
├── templates_docx/             # reference .docx templates
├── templates_xlsx/             # reference .xlsx templates
├── inputs/                     # batch loader input files
├── outputs/                    # generated output files
├── log/                        # batch loader log files
└── reports/                    # generated reports
```

## Entry Points

| What | Command |
|------|---------|
| Batch loader | `python SQM_load_quote_template_docx_file_v2.0.py [options]` |
| Blob archive | `python cli/archive_blobs.py YYMMDD [options]` |
| FastAPI server | `./venv/bin/uvicorn api.app:app --reload` |

## Key Documentation

- [API Testing Guide](api_testing_guide.md) — server setup, curl examples, CORS config
- [Section Extract Service](section_extract_service.md) — GET endpoint for extracting formatted sections
- [Blob Archive Design](blob_archive_design.md) — how blob storage and cleanup work
