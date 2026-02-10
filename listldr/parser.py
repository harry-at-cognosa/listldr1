# parser.py - v1.2 - 2026-02-06
# SQM DOCX Parser: extract section headings and content from Word documents
# Handles paragraphs, table-based headings, trailing table headings, and TOC-driven validation

"""
SQM DOCX Parser Module

Parse Word documents to extract section headings and content.
Handles both standalone paragraphs and text within table cells.
"""

import re
from dataclasses import dataclass
from io import BytesIO
from typing import Optional, BinaryIO
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn


@dataclass
class Section:
    """Represents a parsed section from a document."""
    sequence: int  # 0 = cover page, 1+ = numbered sections
    heading: str   # The heading text (empty for cover page)
    content: str   # Extracted plain text content


# Heading pattern: digit + separator (dash/en-dash) + title
# Must be short (<80 chars) to avoid matching body text
HEADING_PATTERN = re.compile(r'^(\d)\s*[–\-]\s*(.+)$')

# Name of the first expected section heading (configurable for future use)
FIRST_SECTION_HEADING = "Principal Characteristics"


def _get_element_text(element) -> str:
    """Extract all text from an XML element."""
    texts = element.findall('.//' + qn('w:t'))
    return ''.join(t.text or '' for t in texts)


def _is_table(element) -> bool:
    """Check if element is a table."""
    return element.tag.split('}')[-1] == 'tbl'


def _is_paragraph(element) -> bool:
    """Check if element is a paragraph."""
    return element.tag.split('}')[-1] == 'p'


def _find_heading_in_element(element) -> Optional[tuple[int, str, bool]]:
    """
    Check if an element contains a section heading.

    Section headings are recognized when:
    - For paragraphs: matches heading pattern and is short (<80 chars)
    - For tables: first or last row has exactly 1 cell with heading pattern text

    This stricter table check avoids false positives in multi-column tables
    (e.g., price summary tables with section references).

    Returns (section_num, heading_title, is_trailing) or None.
    is_trailing is True when the heading was found in the last row of a table
    (i.e. appended to the end of a preceding content table).
    """
    if _is_paragraph(element):
        text = _get_element_text(element).strip()
        if len(text) < 80:
            match = HEADING_PATTERN.match(text)
            if match:
                return int(match.group(1)), match.group(2).strip(), False

    elif _is_table(element):
        rows = element.findall('.//' + qn('w:tr'))
        if rows:
            # Check first row - must have exactly 1 cell for it to be a heading
            first_row_cells = rows[0].findall('.//' + qn('w:tc'))
            if len(first_row_cells) == 1:
                text = _get_element_text(first_row_cells[0]).strip()
                if len(text) < 80:
                    match = HEADING_PATTERN.match(text)
                    if match:
                        return int(match.group(1)), match.group(2).strip(), False

            # Check last row (if different from first) - heading may be
            # appended to the bottom of a preceding content table
            if len(rows) > 1:
                last_row_cells = rows[-1].findall('.//' + qn('w:tc'))
                if len(last_row_cells) == 1:
                    text = _get_element_text(last_row_cells[0]).strip()
                    if len(text) < 80:
                        match = HEADING_PATTERN.match(text)
                        if match:
                            return int(match.group(1)), match.group(2).strip(), True

    return None


def _extract_text_from_elements(elements: list) -> str:
    """Extract plain text from a list of XML elements."""
    lines = []
    for elem in elements:
        if _is_paragraph(elem):
            text = _get_element_text(elem).strip()
            if text:
                lines.append(text)
        elif _is_table(elem):
            # Extract text from all cells
            for cell in elem.findall('.//' + qn('w:tc')):
                text = _get_element_text(cell).strip()
                if text:
                    lines.append(text)
    return '\n'.join(lines)


def parse_docx_sections(source: str | Path | BinaryIO) -> list[Section]:
    """
    Parse a docx file and extract all sections.

    Args:
        source: File path (str or Path) or file-like object (BinaryIO).

    Returns a list of Section objects:
    - Section 0 is always the cover page (content before first heading)
    - Sections 1+ are numbered sections based on headings found

    Raises:
        ValueError: If document cannot be parsed
    """
    doc = Document(source)
    body = doc.element.body
    elements = list(body)

    sections = []
    current_elements = []
    current_heading = ""
    current_seq = 0
    found_first_heading = False

    for elem in elements:
        heading_match = _find_heading_in_element(elem)

        if heading_match:
            section_num, heading_title, is_trailing = heading_match

            if is_trailing:
                # Heading found in last row of a content table - the table
                # belongs to the current (previous) section, not the new one
                current_elements.append(elem)

            if not found_first_heading:
                # Everything before first heading is cover page
                if current_elements:
                    sections.append(Section(
                        sequence=0,
                        heading="Cover Page",
                        content=_extract_text_from_elements(current_elements)
                    ))
                found_first_heading = True
            else:
                # Save previous section
                sections.append(Section(
                    sequence=current_seq,
                    heading=current_heading,
                    content=_extract_text_from_elements(current_elements)
                ))

            # Start new section
            current_seq = section_num
            current_heading = heading_title
            current_elements = [] if is_trailing else [elem]

        else:
            current_elements.append(elem)

    # Don't forget the last section
    if found_first_heading and current_elements:
        sections.append(Section(
            sequence=current_seq,
            heading=current_heading,
            content=_extract_text_from_elements(current_elements)
        ))
    elif not found_first_heading and current_elements:
        # No headings found at all - treat entire doc as cover page
        sections.append(Section(
            sequence=0,
            heading="Cover Page",
            content=_extract_text_from_elements(current_elements)
        ))

    return sections


# Pattern for finding TOC entries anywhere in text (not just at line start).
# Matches digit + separator + title, where title runs until the next digit+separator or end.
_TOC_ENTRY_PATTERN = re.compile(r'(\d)\s*[–\-]\s*(.+?)(?=\d\s*[–\-]|$)')


def extract_toc_entries(sections: list[Section]) -> list[tuple[int, str]]:
    """
    Extract table-of-contents entries from the cover page (section 0).

    Scans cover page content for TOC entries like "3 - Machine Execution".
    Handles both newline-separated entries and entries concatenated on a
    single line (common in docx table cell extraction).

    Returns list of (section_number, title) tuples.
    """
    # Find section 0 (cover page)
    cover = None
    for sec in sections:
        if sec.sequence == 0:
            cover = sec
            break

    if cover is None:
        return []

    entries = []
    for line in cover.content.split('\n'):
        line = line.strip()
        for match in _TOC_ENTRY_PATTERN.finditer(line):
            entries.append((int(match.group(1)), match.group(2).strip()))

    return entries


def _map_elements_to_sections(body) -> dict[int, list]:
    """
    Walk body elements and build a map of section sequence -> list of XML elements.

    Uses the same heading detection and trailing-heading logic as parse_docx_sections().
    """
    elements = list(body)
    section_elements: dict[int, list] = {}
    current_elements: list = []
    current_seq = 0
    found_first_heading = False

    for elem in elements:
        heading_match = _find_heading_in_element(elem)

        if heading_match:
            section_num, _heading_title, is_trailing = heading_match

            if is_trailing:
                current_elements.append(elem)

            if not found_first_heading:
                if current_elements:
                    section_elements[0] = list(current_elements)
                found_first_heading = True
            else:
                section_elements[current_seq] = list(current_elements)

            current_seq = section_num
            current_elements = [] if is_trailing else [elem]
        else:
            current_elements.append(elem)

    # Last section
    if found_first_heading and current_elements:
        section_elements[current_seq] = list(current_elements)
    elif not found_first_heading and current_elements:
        section_elements[0] = list(current_elements)

    return section_elements


def extract_section_docx(source_bytes: bytes, target_seqn: int) -> bytes | None:
    """
    Clone a .docx and strip all body content except the target section.

    Uses the clone-and-strip approach: opens the full document (preserving
    headers, footers, page layout, styles, fonts, images), then removes
    every body element that does not belong to the requested section.

    Args:
        source_bytes: Raw bytes of the source .docx file.
        target_seqn: Section sequence number to keep (0 = cover page).

    Returns:
        Bytes of the new .docx containing only the target section,
        or None if the target section was not found in the document.
    """
    doc = Document(BytesIO(source_bytes))
    body = doc.element.body

    section_elements = _map_elements_to_sections(body)

    if target_seqn not in section_elements:
        return None

    # Build set of element ids to keep
    keep = {id(e) for e in section_elements[target_seqn]}

    # Remove all body elements not in the target section
    for elem in list(body):
        if id(elem) not in keep:
            body.remove(elem)

    output = BytesIO()
    doc.save(output)
    return output.getvalue()


# DEPRECATED: hardcoded expected sequences -- no longer used by validate_section_sequence().
# Kept for reference only. Validation now derives expected sections from the cover page TOC.
EXPECTED_SEQUENCES = {
    'ECM': [0, 1, 2, 3, 4, 5, 6, 7, 8],  # 8 numbered + cover = 9 total
    'UBM': [0, 1, 2, 3, 4, 5, 6, 7, 8],  # 8 numbered + cover = 9 total
    'KD ': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],  # 9 numbered + cover = 10 total
}


def validate_section_sequence(
    sections: list[Section],
    product_line_abbr: str
) -> tuple[bool, str]:
    """
    Validate parsed sections against the document's own cover page TOC.

    Derives the expected section list from TOC entries on the cover page,
    then compares against the actual parsed section numbers.

    The product_line_abbr parameter is kept for API compatibility but is
    no longer used internally.

    Returns (is_valid, error_message).
    If valid, error_message is empty.
    """
    if len(sections) < 2:
        return False, f"Too few sections: {len(sections)} (need at least 2)"

    # Extract TOC entries from cover page
    toc_entries = extract_toc_entries(sections)

    if not toc_entries:
        # No TOC found on cover page -- fall back to basic count check
        if len(sections) < 6:
            return False, f"No TOC found and too few sections: {len(sections)} (need at least 6)"
        return True, ""

    # Build expected sequence: section 0 (cover) + TOC section numbers
    expected = [0] + [num for num, _title in toc_entries]
    actual = [s.sequence for s in sections]

    if actual != expected:
        toc_desc = [(num, title) for num, title in toc_entries]
        found_desc = [(s.sequence, s.heading) for s in sections]
        return False, (
            f"Section sequence mismatch. "
            f"TOC promised: {expected}, Parsed: {actual}. "
            f"TOC entries: {toc_desc}, "
            f"Found headings: {found_desc}"
        )

    return True, ""
