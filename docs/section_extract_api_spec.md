# Section Extract API — Specification

## Summary

A new API endpoint that extracts a single section from a stored sales-quote template's `.docx` file and returns it as a fully formatted `.docx` document preserving the original rich content (tables, fonts, images, borders, styles, etc.).

## Endpoint

```
GET /api/v1/templates/{plsqt_id}/sections/{seqn}/docx
```

## Parameters

| Parameter  | Type | Description |
|------------|------|-------------|
| `plsqt_id` | int  | Template ID (`plsq_templates.plsqt_id`) |
| `seqn`     | int  | Section sequence number (`plsqt_sections.plsqts_seqn`, 0–12). Section 0 is the cover page. |

## Processing Steps

1. **Look up the template** — fetch `plsq_templates` row by `plsqt_id`. Fail 404 if not found.
2. **Get the blob reference** — read `current_blob_id` from the template. Fail 404 if NULL (no document stored).
3. **Fetch the stored section record(s)** — query `plsqt_sections` for this template where `plsqts_seqn = seqn`, joined to `plsqts_type`. Fail 404 if no matching row.
4. **Resolve the section name** — for each matching section record:
   - If `plsqts_use_alt_name` is true, use `plsqts_alt_name`
   - Otherwise, use `plsqtst_name` from the joined `plsqts_type` row
   - If multiple rows share the same `seqn`, combine them (use the first section's name for the filename)
5. **Fetch the .docx bytes** from `document_blob` by `blob_id`.
6. **Parse the .docx** using `parse_docx_sections()` to identify section boundaries (the XML elements — paragraphs and tables — belonging to each section).
7. **Match** — find the parsed section whose sequence equals `seqn`. Proceed as long as the requested section is found; do not fail if the overall structure has minor mismatches with the DB records.
8. **Build a section-only `.docx`** using the **clone-and-strip** approach:
   - Clone the entire source `.docx` in memory (preserving headers, footers, page layout, margins, styles, fonts, numbering, theme, images, and all relationship parts)
   - Remove all body elements that do **not** belong to the requested section
   - The result is the original document's full container with only one section's content in the body
9. **Return** the `.docx` as a streaming file download.

## Response (200 — Success)

```
Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
Content-Disposition: attachment; filename="plsqts_content_41_14_4_Product_Pump.docx"
```

Headers:
- `X-Section-Count`: total number of sections in this template (from DB)
- `X-Content-Length`: size in bytes of the returned `.docx`

### Filename format

```
plsqts_content_{plsqt_id}_{blob_id}_{seqn}_{section_name}.docx
```

Where `section_name` has spaces replaced with underscores.

## Error Responses

| Code | Condition |
|------|-----------|
| 404  | Template not found |
| 404  | No document blob for this template (`current_blob_id` is NULL) |
| 404  | No section with `plsqts_seqn = seqn` for this template |
| 404  | Requested section not found in the parsed document |
| 500  | Unexpected error |

## Design Decisions

| Question | Decision |
|----------|----------|
| Extraction approach | **Clone-and-strip** — clone the full source `.docx`, then remove all body elements except the requested section. This preserves headers, footers, page layout, margins, styles, fonts, tables, images, and all formatting from the original document. |
| Duplicate sequence numbers | **Combine** — if multiple `plsqt_sections` rows share the same `plsqts_seqn`, their content is combined into a single document. |
| Validation strictness | **Lenient** — as long as the requested `seqn` is found in the parsed document, proceed. Do not fail if the overall document structure has minor mismatches with DB records. |
| Cover page (seqn=0) | **Yes** — section 0 (cover page) is extractable. |

## Implementation Notes

### Clone-and-strip approach

The extraction works by cloning the full `.docx` byte-for-byte, opening the clone with python-docx, then removing body elements that don't belong to the requested section. This preserves everything in the original document package:

- **Headers and footers** — retained as-is (they are document-section properties, not body content)
- **Page layout** — margins, orientation, page size
- **Styles, fonts, theme** — the full `styles.xml`, `numbering.xml`, and theme parts stay intact
- **Embedded images** — all image relationship parts remain in the package (unused ones add a small amount to file size but cause no problems)
- **Tables** — full formatting including borders, shading, merged cells, column widths
- **Margin annotations / text boxes** — if attached to elements within the section, they're preserved

The parser's existing element tracking identifies which body-level XML elements (paragraphs and tables) belong to each section. The strip step simply removes all other body elements, leaving the document container intact.
