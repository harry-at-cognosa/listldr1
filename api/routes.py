"""
API routes for the SQM template loader.
"""

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException

from listldr.db import SQMDatabase
from listldr.service import load_template
from api.dependencies import get_db, get_section_types
from api.schemas import LoadSuccessResponse, TemplateResponse, SectionResponse

router = APIRouter(prefix="/api/v1/templates", tags=["templates"])


@router.post("/load", response_model=LoadSuccessResponse)
async def load_template_endpoint(
    file: UploadFile = File(...),
    country: str = Form(...),
    currency: str = Form(...),
    product_line: str | None = Form(None),
    dry_run: bool = Form(False),
    db: SQMDatabase = Depends(get_db),
    section_types: list[tuple[int, str]] = Depends(get_section_types),
):
    """
    Upload and load a .docx sales-quote template into the database.
    """
    # Validate file extension
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="File must be a .docx document")

    # Resolve country and currency
    country_id = db.lookup_country(country)
    if country_id is None:
        raise HTTPException(status_code=400, detail=f"Country not found: {country}")

    currency_id = db.lookup_currency(currency)
    if currency_id is None:
        raise HTTPException(status_code=400, detail=f"Currency not found: {currency}")

    # Read file bytes
    file_bytes = await file.read()

    try:
        result = load_template(
            file_bytes=file_bytes,
            filename=file.filename,
            db=db,
            country_id=country_id,
            currency_id=currency_id,
            section_types=section_types,
            product_line_override=product_line,
            update_user="SQM_api",
            dry_run=dry_run,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return LoadSuccessResponse(
        template=TemplateResponse(
            plsqt_id=result.plsqt_id,
            template_name=result.template_name,
            product_line=result.product_line_abbr,
            is_new=result.is_new,
            section_count=result.section_count,
            blob_id=result.blob_id,
            sections=[
                SectionResponse(
                    sequence=s.sequence,
                    heading=s.heading,
                    section_type_id=s.section_type_id,
                )
                for s in result.sections
            ],
        )
    )
