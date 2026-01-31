# Template Transformation Workflow - Technical Design Document

## Overview

This document describes the technical architecture for a system that transforms Swiss quote templates into US regional variants. The workflow involves parsing Word documents into reusable sections, allowing section-level editing, and reassembling sections into new templates.

### Business Context

- **Source**: Swiss quote templates (Word .docx files) with pricing in CHF/EUR
- **Target**: US quote templates with USD pricing and minor text modifications
- **Volume**: 100+ templates across product categories and configurations
- **Users**: Small team (2-5 people) managing template library

### Key Requirements

1. Parse Swiss templates into discrete, numbered sections
2. Store sections for reuse across multiple templates
3. Allow users to edit sections in Microsoft Word
4. Reassemble sections into complete templates
5. Apply regional transformations (currency, pricing formulas, terminology)

---

## Document Structure Analysis

### Swiss Template Structure

Swiss templates follow a consistent structure with clearly defined section boundaries:

```
Document Body
├── Cover Page (header table, logo, intro letter, table of contents)
├── Section 1 – Principal Characteristics (1-row header table + content)
├── Section 2 – General Technical Data (1-row header table + content)
├── Section 3 – Machine Execution (1-row header table + subsections)
├── Section 4 – Product Pump (1-row header table + content)
├── Section 5 – Motor Starter Cabinet (1-row header table + content)
├── Section 6 – Price Summary (1-row header table + content)
├── Section 7 – Options and Accessories (1-row header table + content)
├── Section 8 – Terms of Delivery (1-row header table + content)
└── Footer (company info, signature block)
```

### Section Header Pattern

Each section begins with a **single-row table** containing the section number and title:

```
┌─────────────────────────────────────┐
│ 4 – Product Pump FZ 1300            │
└─────────────────────────────────────┘
```

The header pattern is: `{number} – {title}` where:
- `{number}` is a single integer (1-10)
- `–` is an en-dash (U+2013) or hyphen
- `{title}` is the section name

This pattern enables reliable programmatic identification of section boundaries.

### Element Types

Word documents contain two primary element types in the body:

| Element | Description | In Templates |
|---------|-------------|--------------|
| **Paragraph** | Text content with styling | Intro text, subsection headers, notes |
| **Table** | Tabular data with cells | Section headers, specifications, pricing |

A typical section contains:
- 1 table (header banner)
- 1-3 tables (content: specs, options, pricing)
- 0-3 paragraphs (notes, subsection labels)

---

## Technology Stack

### Python Libraries

| Library | Purpose | Version |
|---------|---------|---------|
| `python-docx` | Read/write Word documents, access paragraphs and tables | ≥1.1.0 |
| `docxcompose` | Merge multiple documents while preserving formatting | ≥1.4.0 |
| `SQLAlchemy` | Database ORM for template/section metadata | ≥2.0.0 |
| `psycopg2-binary` | PostgreSQL database driver | ≥2.9.9 |
| `alembic` | Database migrations | ≥1.13.0 |
| `Flask` | Web UI for template management | ≥3.0.0 |

### Installation

```bash
pip install python-docx docxcompose sqlalchemy psycopg2-binary alembic flask
```

---

## Core Operations

### 1. Reading a Document

```python
from docx import Document

# Load a Word document
doc = Document('/path/to/template.docx')

# Access basic properties
print(f"Paragraphs: {len(doc.paragraphs)}")
print(f"Tables: {len(doc.tables)}")
```

### 2. Accessing Document Elements in Order

The document body contains paragraphs and tables interleaved. To process them in document order:

```python
from docx import Document
from docx.oxml.ns import qn

doc = Document('/path/to/template.docx')
body = doc.element.body

para_idx = 0
table_idx = 0

for child in body:
    tag = child.tag.split('}')[-1]  # Get element type

    if tag == 'p':  # Paragraph
        para = doc.paragraphs[para_idx]
        print(f"Paragraph: {para.text[:50]}")
        para_idx += 1

    elif tag == 'tbl':  # Table
        table = doc.tables[table_idx]
        first_cell = table.rows[0].cells[0].text
        print(f"Table ({len(table.rows)} rows): {first_cell[:50]}")
        table_idx += 1
```

### 3. Finding Section Boundaries

```python
import re
from docx import Document
from docx.oxml.ns import qn

def find_section_boundaries(doc_path: str) -> list[dict]:
    """
    Identify where each numbered section starts in the document.

    Returns list of dicts with keys: num, title, element_index
    """
    doc = Document(doc_path)
    section_pattern = re.compile(r'^(\d+)\s*[–\-]\s*(.+)')
    sections = []

    body = doc.element.body

    for idx, child in enumerate(body):
        tag = child.tag.split('}')[-1]

        # Get text from paragraph or first table cell
        if tag == 'p':
            text = ''.join(t.text or '' for t in child.findall('.//' + qn('w:t')))
        elif tag == 'tbl':
            first_cell = child.findall('.//' + qn('w:tc'))[0]
            text = ''.join(t.text or '' for t in first_cell.findall('.//' + qn('w:t')))
        else:
            continue

        text = text.strip()
        match = section_pattern.match(text)

        if match and '.' not in match.group(1):  # Exclude subsections like 3.1
            sections.append({
                'num': int(match.group(1)),
                'title': match.group(2).strip(),
                'element_index': idx
            })

    return sections
```

**Example output:**
```python
[
    {'num': 1, 'title': 'Principal Characteristics', 'element_index': 16},
    {'num': 2, 'title': 'General Technical Data', 'element_index': 20},
    {'num': 3, 'title': 'Machine Execution', 'element_index': 40},
    {'num': 4, 'title': 'Product Pump FZ 1300', 'element_index': 67},
    # ...
]
```

### 4. Extracting a Section to a Separate File

```python
from docx import Document
from copy import deepcopy

def extract_section(doc_path: str, section_num: int, output_path: str):
    """
    Extract a single section from a template to its own .docx file.

    The extracted file contains all elements from the section header
    to (but not including) the next section header.
    """
    doc = Document(doc_path)
    sections = find_section_boundaries(doc_path)

    # Find start index for this section
    start_idx = None
    for s in sections:
        if s['num'] == section_num:
            start_idx = s['element_index']
            break

    if start_idx is None:
        raise ValueError(f"Section {section_num} not found")

    # Find end index (start of next section)
    end_idx = None
    for s in sections:
        if s['num'] > section_num:
            end_idx = s['element_index']
            break

    # If no next section, use end of document (minus footer)
    if end_idx is None:
        end_idx = len(list(doc.element.body)) - 5

    # Create new document with section content
    new_doc = Document()
    new_body = new_doc.element.body

    # Remove default empty paragraph
    for child in list(new_body):
        new_body.remove(child)

    # Copy elements from source
    body = doc.element.body
    for idx, child in enumerate(body):
        if start_idx <= idx < end_idx:
            new_body.append(deepcopy(child))

    new_doc.save(output_path)
    print(f"Extracted section {section_num} ({end_idx - start_idx} elements)")
```

### 5. Replacing a Section in a Document

```python
from docx import Document
from copy import deepcopy

def replace_section(doc_path: str, section_num: int,
                    replacement_path: str, output_path: str):
    """
    Replace a section in a document with content from another file.

    Args:
        doc_path: Original template
        section_num: Section to replace (e.g., 4)
        replacement_path: .docx file containing new section content
        output_path: Where to save the modified template
    """
    doc = Document(doc_path)
    replacement = Document(replacement_path)

    sections = find_section_boundaries(doc_path)

    # Find section boundaries
    start_idx = None
    end_idx = None

    for s in sections:
        if s['num'] == section_num:
            start_idx = s['element_index']
        elif s['num'] > section_num and start_idx is not None and end_idx is None:
            end_idx = s['element_index']

    if start_idx is None:
        raise ValueError(f"Section {section_num} not found")
    if end_idx is None:
        end_idx = len(list(doc.element.body)) - 5

    body = doc.element.body

    # Remove old section elements
    elements_to_remove = list(body)[start_idx:end_idx]
    for elem in elements_to_remove:
        body.remove(elem)

    # Find insertion point
    body_children = list(body)
    insert_before = body_children[start_idx] if start_idx < len(body_children) else None

    # Insert replacement content
    for elem in replacement.element.body:
        new_elem = deepcopy(elem)
        if insert_before is not None:
            insert_before.addprevious(new_elem)
        else:
            body.append(new_elem)

    doc.save(output_path)
```

### 6. Assembling a Document from Sections (Alternative Approach)

Using `docxcompose` to build a document from separate section files:

```python
from docx import Document
from docxcompose.composer import Composer

def assemble_template(cover_page_path: str, section_paths: list[str],
                      output_path: str):
    """
    Assemble a complete template from a cover page and section files.

    The cover page provides the master formatting (headers, footers,
    watermarks, styles). Sections are appended in order.
    """
    # Start with cover page as the base
    master = Document(cover_page_path)
    composer = Composer(master)

    # Append each section
    for section_path in section_paths:
        section_doc = Document(section_path)
        composer.append(section_doc)

    composer.save(output_path)
```

---

## Workflow Design

### Phase 1: Import Swiss Template

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Swiss .docx    │────▶│  Parse Sections  │────▶│  Section Files  │
│  (source)       │     │  (extract)       │     │  (.docx each)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
                                                 ┌─────────────────┐
                                                 │  Database       │
                                                 │  (metadata +    │
                                                 │   file paths)   │
                                                 └─────────────────┘
```

**Steps:**
1. User uploads Swiss template .docx
2. System parses document structure, identifies sections
3. Each section is extracted to a separate .docx file
4. Metadata (section number, title, source template, file path) stored in database

### Phase 2: Edit Sections

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Section File   │────▶│  User Edits in   │────▶│  Updated        │
│  (.docx)        │     │  Microsoft Word  │     │  Section File   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
                                                 ┌─────────────────┐
                                                 │  Re-upload to   │
                                                 │  Platform       │
                                                 └─────────────────┘
```

**Steps:**
1. User downloads section file from platform
2. User edits in Microsoft Word (change pump model, update prices, etc.)
3. User saves and re-uploads to platform
4. System stores new version, updates metadata

### Phase 3: Assemble US Template

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Cover Page     │     │                  │     │                  │
│  (US branding)  │────▶│                  │     │                  │
├─────────────────┤     │   Assemble       │────▶│   US Template    │
│  Section 1      │────▶│   Document       │     │   (.docx)        │
├─────────────────┤     │                  │     │                  │
│  Section 2      │────▶│                  │     │                  │
├─────────────────┤     └──────────────────┘     └─────────────────┘
│  ...            │
└─────────────────┘
```

**Steps:**
1. User selects which sections to include
2. User selects cover page template (contains US branding, formatting)
3. System assembles sections in order using `replace_section()` or `docxcompose`
4. Output is a complete US template ready for use

---

## Data Model

### Proposed Database Schema

```sql
-- Product categories (e.g., "Mills", "Mixers")
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT
);

-- Product lines within categories
CREATE TABLE product_lines (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES categories(id),
    name VARCHAR(100) NOT NULL,
    description TEXT
);

-- Section types (e.g., "Principal Characteristics", "Product Pump")
CREATE TABLE section_types (
    id SERIAL PRIMARY KEY,
    number INTEGER NOT NULL,  -- Standard section number (1-10)
    name VARCHAR(200) NOT NULL,
    description TEXT
);

-- Actual section content files
CREATE TABLE sections (
    id SERIAL PRIMARY KEY,
    section_type_id INTEGER REFERENCES section_types(id),
    product_line_id INTEGER REFERENCES product_lines(id),

    name VARCHAR(200) NOT NULL,  -- e.g., "Product Pump FZ 1300"
    file_path VARCHAR(500) NOT NULL,  -- Path to .docx file

    region VARCHAR(10) NOT NULL,  -- 'CH' or 'US'
    currency VARCHAR(3),  -- 'CHF', 'EUR', 'USD'

    source_section_id INTEGER REFERENCES sections(id),  -- If cloned from another

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Complete templates (assemblies of sections)
CREATE TABLE templates (
    id SERIAL PRIMARY KEY,
    product_line_id INTEGER REFERENCES product_lines(id),

    name VARCHAR(200) NOT NULL,
    file_path VARCHAR(500),  -- Path to assembled .docx (if generated)

    region VARCHAR(10) NOT NULL,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Junction table: which sections are in which template
CREATE TABLE template_sections (
    template_id INTEGER REFERENCES templates(id),
    section_id INTEGER REFERENCES sections(id),
    position INTEGER NOT NULL,  -- Order in document
    PRIMARY KEY (template_id, section_id)
);
```

### File Storage Strategy

**Recommended: Filesystem with database references**

```
/storage/
├── swiss/
│   ├── templates/
│   │   └── UBM_20_FU_FU_E.docx
│   └── sections/
│       ├── section_1_principal_characteristics.docx
│       ├── section_2_general_technical_data.docx
│       └── ...
├── us/
│   ├── templates/
│   │   └── UBM_20_FCFC_US.docx
│   └── sections/
│       ├── section_4_product_pump_vz300.docx
│       ├── section_4_product_pump_fz1300.docx
│       └── ...
└── cover_pages/
    ├── us_cover_page.docx
    └── swiss_cover_page.docx
```

**Why filesystem over database BYTEA:**
- Files directly editable in Word without export step
- Easier backup/sync with cloud storage
- No database bloat
- Simpler debugging (can inspect files directly)

---

## User Interface Concepts

### Web UI Pages

1. **Template Browser**
   - List all templates by category/product line
   - Filter by region (Swiss/US)
   - Actions: View, Edit Sections, Generate US Version

2. **Section Library**
   - List all sections by type
   - Filter by product line, region
   - Actions: Download, Clone, Replace

3. **Template Builder**
   - Select cover page
   - Drag/drop sections into order
   - Preview section list
   - Generate assembled document

4. **Import Wizard**
   - Upload Swiss template
   - Auto-detect sections
   - Review/confirm section boundaries
   - Save to library

---

## Example: Complete Workflow

### Importing a Swiss Template

```python
# 1. Parse the Swiss template
source = '/uploads/UBM_20_FU_FU_E.docx'
sections = find_section_boundaries(source)

# 2. Extract each section
for s in sections:
    output = f"/storage/swiss/sections/section_{s['num']}_{slugify(s['title'])}.docx"
    extract_section(source, s['num'], output)

    # 3. Save metadata to database
    db.execute("""
        INSERT INTO sections (section_type_id, name, file_path, region)
        VALUES (%s, %s, %s, 'CH')
    """, [s['num'], s['title'], output])
```

### Creating a US Variant

```python
# 1. User clones Swiss section for US
swiss_section = db.query("SELECT * FROM sections WHERE id = %s", [swiss_id])

# 2. Copy file
us_path = swiss_section.file_path.replace('/swiss/', '/us/')
shutil.copy(swiss_section.file_path, us_path)

# 3. Create database record
db.execute("""
    INSERT INTO sections (section_type_id, name, file_path, region, source_section_id)
    VALUES (%s, %s, %s, 'US', %s)
""", [swiss_section.section_type_id, swiss_section.name + ' (US)', us_path, swiss_id])

# 4. User downloads, edits in Word, re-uploads
# (handled by web UI file upload)
```

### Assembling a US Template

```python
# 1. Get selected sections in order
section_ids = [101, 102, 103, 104, 105, 106, 107, 108]  # User selection
sections = db.query("SELECT file_path FROM sections WHERE id IN %s", [section_ids])

# 2. Get cover page
cover_page = '/storage/cover_pages/us_cover_page.docx'

# 3. Assemble
assemble_template(
    cover_page_path=cover_page,
    section_paths=[s.file_path for s in sections],
    output_path='/storage/us/templates/UBM_20_FCFC_US_generated.docx'
)
```

---

## Validation Performed

The following tests were run against actual Swiss and US templates:

### Swiss Template Analysis
- **File**: `UBM 20 FU_FU E.docx`
- **Structure**: 79 paragraphs, 32 tables
- **Sections found**: 8 (all with clean single-row header tables)
- **Extraction test**: All 8 sections extracted successfully
- **Round-trip test**: Replace section 4, document identical (79 paragraphs, 32 tables)

### US Template Analysis
- **File**: `UBM 20 FCFC_US_FOB Allendale_11 2025.docx`
- **Structure**: 91 paragraphs, 32 tables
- **Issues found**: Sections 2 and 3 headers not cleanly separated (human error during manual conversion)
- **Sections 4-10**: Clean structure, extraction/replacement works

### Conclusion

Swiss templates have consistent, parseable structure suitable for automated processing. US templates created manually may have structural inconsistencies. The recommended workflow is **Swiss → Parse → Edit → Assemble** rather than modifying existing US templates.

---

## Next Steps

1. **Build database schema** - Create PostgreSQL tables for templates, sections, metadata
2. **Build import service** - Parse Swiss templates, extract sections, store files
3. **Build web UI** - Flask app for browsing, editing, assembling templates
4. **Build assembly service** - Generate US templates from selected sections
5. **Add price transformation** - Apply currency conversion formulas during assembly
6. **Testing** - Validate with full template library

---

## Appendix: File Locations

Proof-of-concept code created during design:

| File | Purpose |
|------|---------|
| `poc_docxcompose.py` | Document assembly examples |
| `poc_section_swap.py` | Section extraction and replacement |
| `outputs/swiss/section_*.docx` | Extracted Swiss sections |
| `outputs/swiss/modified_swiss.docx` | Round-trip test output |

