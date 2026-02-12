"""
API routes for the SQM template loader.
"""

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from fastapi.responses import Response

from listldr.db import SQMDatabase
from listldr.logger import SQMLogger
from listldr.parser import extract_section_docx
from listldr.service import load_template
from api.dependencies import get_db, get_logger, get_section_types
from api.schemas import LoadSuccessResponse, TemplateResponse, SectionResponse

DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

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
    logger: SQMLogger = Depends(get_logger),
):
    """
    Upload and load a .docx sales-quote template into the database.
    """
    logger.log(f"POST /load file={file.filename} country={country} currency={currency} dry_run={dry_run}")

    # Validate file extension
    if not file.filename or not file.filename.lower().endswith(".docx"):
        detail = "File must be a .docx document"
        logger.log(f"  ERROR 400: {detail}")
        raise HTTPException(status_code=400, detail=detail)

    # Resolve country and currency
    country_id = db.lookup_country(country)
    if country_id is None:
        detail = f"Country not found: {country}"
        logger.log(f"  ERROR 400: {detail}")
        raise HTTPException(status_code=400, detail=detail)

    currency_id = db.lookup_currency(currency)
    if currency_id is None:
        detail = f"Currency not found: {currency}"
        logger.log(f"  ERROR 400: {detail}")
        raise HTTPException(status_code=400, detail=detail)

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
        logger.log(f"  ERROR 400 (ValueError): {e}")
        raise HTTPException(status_code=400, detail=str(e))

    logger.log(
        f"  OK: template={result.template_name} plsqt_id={result.plsqt_id}"
        f" blob_id={result.blob_id} sections={result.section_count} is_new={result.is_new}"
    )

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


@router.get("/{plsqt_id}/sections/{seqn}/docx")
def get_section_docx(
    plsqt_id: int,
    seqn: int,
    db: SQMDatabase = Depends(get_db),
    logger: SQMLogger = Depends(get_logger),
):
    """
    Extract a single section from a template's .docx file and return it
    as a fully formatted .docx document (clone-and-strip).
    """
    logger.log(f"GET /{plsqt_id}/sections/{seqn}/docx")

    # 1. Look up template
    template = db.get_template_by_id(plsqt_id)
    if template is None:
        detail = f"Template not found: {plsqt_id}"
        logger.log(f"  ERROR 404: {detail}")
        raise HTTPException(status_code=404, detail=detail)

    blob_id = template["current_blob_id"]
    if blob_id is None:
        detail = f"No document stored for template {plsqt_id}"
        logger.log(f"  ERROR 404: {detail}")
        raise HTTPException(status_code=404, detail=detail)

    # 2. Look up section record(s) for this seqn
    section_rows = db.get_section_info(plsqt_id, seqn)
    if not section_rows:
        detail = f"No section {seqn} for template {plsqt_id}"
        logger.log(f"  ERROR 404: {detail}")
        raise HTTPException(status_code=404, detail=detail)

    # 3. Resolve section name (use alt_name if flagged)
    row = section_rows[0]
    if row["plsqts_use_alt_name"] and row["plsqts_alt_name"]:
        section_name = row["plsqts_alt_name"]
    else:
        section_name = row["plsqtst_name"]

    # 4. Fetch blob bytes
    source_bytes = db.get_blob_bytes(blob_id)
    if source_bytes is None:
        detail = f"Blob {blob_id} not found in document_blob"
        logger.log(f"  ERROR 404: {detail}")
        raise HTTPException(status_code=404, detail=detail)

    # 5. Extract section from docx
    docx_bytes = extract_section_docx(source_bytes, seqn)
    if docx_bytes is None:
        detail = f"Section {seqn} not found in parsed document for template {plsqt_id}"
        logger.log(f"  ERROR 404: {detail}")
        raise HTTPException(
            status_code=404,
            detail=detail,
        )

    # 6. Build filename
    safe_name = section_name.replace(" ", "_")
    filename = f"plsqts_content_{plsqt_id}_{blob_id}_{seqn}_{safe_name}.docx"

    logger.log(f"  OK: {filename} ({len(docx_bytes)} bytes)")

    return Response(
        content=docx_bytes,
        media_type=DOCX_CONTENT_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Section-Count": str(template["plsqt_section_count"]),
            "X-Content-Length": str(len(docx_bytes)),
        },
    )
