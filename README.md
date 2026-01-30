# 1_listldr

## Description

[Project description here]

## Project Structure

```
1_listldr/
├── 1_listldr_lib/     # Shared library modules
├── alembic/           # Database migrations (Alembic)
│   └── versions/      # Migration version files
├── conf/              # Configuration files
│   └── config.ini     # Main configuration
├── docs/              # Documentation
├── inputs/            # Data inputs
├── log/               # Log file outputs
├── outputs/           # Data outputs
├── reports/           # Report outputs
├── sql_files/         # SQL files
├── static/            # Static assets (Flask)
├── templates/         # Flask templates
├── templates_docx/    # Word document templates
├── templates_xlsx/    # Excel templates
├── alembic.ini        # Alembic configuration
├── CHANGELOG.md       # Version changelog
├── README.md          # This file
└── requirements.txt   # Python dependencies
```

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure `conf/config.ini` with your settings.

4. Initialize the database with Alembic:
   ```bash
   alembic upgrade head
   ```

## Usage

[Usage instructions here]

## Flask App

To run the Flask app locally:
```bash
flask run
```

## Database Migrations

Create a new migration:
```bash
alembic revision --autogenerate -m "description"
```

Apply migrations:
```bash
alembic upgrade head
```
