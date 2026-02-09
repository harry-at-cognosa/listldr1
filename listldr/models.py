"""
Result models for the SQM template loader service layer.
"""

from dataclasses import dataclass


@dataclass
class SectionInfo:
    """Summary of a loaded section."""
    sequence: int
    heading: str
    section_type_id: int


@dataclass
class TemplateLoadResult:
    """Result of a successful template load operation."""
    plsqt_id: int
    template_name: str
    product_line_abbr: str
    section_count: int
    is_new: bool
    blob_id: int
    sections: list[SectionInfo]
