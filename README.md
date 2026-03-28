# 1_listldr

## Description

This is one half of the Sale Quote Manager solution.

The listmgr project was built entirely with Claude Code -- one half auto-built using LVZ's AutoForge project to support long-running, multi-agent solution construction, and the remainder assisted by Claude Code being used directly.

the project has two halfs - listmgr and listldr.  

The listmgr part was built first, after I used Claude Code directly to build a database schema.  with the table structures defined, I used autoForge (then AutoCoder) to build listmgr, the primary front end for administrative functions.  I also used this portion of the system to populate the database with some initial sales quote templates developed for two country, both across multiple product categories and lines, requiring the use of multiple countries and currencies. I also set up and defined other minor tables for pricing and currency conversionts and to manage those changes over time. 

the initial build created about 125 features over the period of about 4 hours, and included account creation and authentication and some other navigation and data access pages. the initial build included a single error -- it used sqlite3 after specifically having instruction to use postgresql -- but the second invocation of AutoForge told the agents to fix that, and not only did all the changes get made correctly but all the data was cleanly moved over and the conversion was flawless.

Multiple additional features and functions were added to the front end, and then work was paused for phase 2.

The second major build was all done with Python.  I first wrote batch programs to load about 130 sales quote template files across two countries and currrencies into the database, storing the docx files as blobs with a well-architected write-only blob table following best practices for this sort of application. [I also wrote a batch program that could be used to periodically purge old sales templates documents.] 

With the batch processes working well, I used claude code to generate a FastAPI web application that could invoke those jobs via menu items and api calls from the listmgr side of the application, and by refactoring the batch programs to use key routines (e.g. load this word doc into the doc storage and associate it with its corresponding sales quote template record), we have only one set of code doing the template level operations which is shared by the front end that lets end users operate on sigle templates and the back end that runs on say "all the Bead Mills sold in Switzerland". 

In summary, the listmgr code base provides Sales Quote Manager the primary user and admin interface to the application, while the listldr (or list loader) FasatAPI applicaiton implements some of the key business logic and implements the primary batch and periodic functions for the application.

more details about each portion are available at quotemgr-info http://files.cognosa.net/quotemgr-info/. This older has, in addition toa quick overview movie and two detailed PDFs describing the solution, also has a postgresql database that could be used with the system there to run a complete working version of that application.  While not shown in the inex.html web page in that folder, the database file can be downloaded from https://s3.us-east-1.amazonaws.com/files.cognosa.net/quotemgr-info/listmgr1_blue_260228_v1.7b.dump.zip 



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
