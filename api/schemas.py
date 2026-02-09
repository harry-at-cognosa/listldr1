"""
Pydantic request/response models for the SQM template loader API.
"""

from pydantic import BaseModel


class SectionResponse(BaseModel):
    sequence: int
    heading: str
    section_type_id: int


class TemplateResponse(BaseModel):
    plsqt_id: int
    template_name: str
    product_line: str
    is_new: bool
    section_count: int
    blob_id: int
    sections: list[SectionResponse]


class LoadSuccessResponse(BaseModel):
    status: str = "success"
    template: TemplateResponse


class ErrorResponse(BaseModel):
    status: str = "error"
    detail: str
