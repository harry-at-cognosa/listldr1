# Template Migration — Request Summary

## Goal

Build a migration function that takes a CHE (Swiss) sales quote template `.docx` file for a specific product and converts it into a USA variant for the same product. The conversion is country-to-country (CHE → USA), implying a currency change from CHF to USD.

---

## Scope

**Phase 1 (current):** Text and format conversion — understand and implement the structural, textual, and formatting differences between Swiss and US templates.

**Phase 2 (later):** Price conversion — apply currency exchange and markup factors from `pconv_factor_values` / `price_conv_factors` to transform CHF amounts to USD.

The `.xlsx` price-sheet companions shipping alongside the USA templates are excluded from scope for now.

---

## Conversion Details

### 1. Document-Level Format Changes

| Aspect | CHE | USA |
|--------|-----|-----|
| Page size | A4 (may vary by product line) | US Letter or A4 (product-dependent) |
| Header | CHE branding / logo | USA branding / logo |
| Footer | CHE company info | USA company info |
| Right-margin vertical text | CHE variant | USA variant |
| Branding images | WAB AG assets | WAB US Corp. assets |

### 2. Cover Page Changes

- Company name: WILLY A. BACHOFEN AG → WAB US Corp.
- Greeting: "Dear Sirs" → "Dear (Name):"
- Address / contact block updated for USA office
- Signature block additions
- Table of Contents reflects expanded USA section list

### 3. Section-Level Text Conversion

- Product names translate from German to English (e.g. KERAMIK → Ceramic, FU\_FU → FCFC)
- Location references change (Switzerland → USA)
- Additional tax-compliance and delivery-disclaimer text in USA versions
- Some sections gain subsections that don't exist in the CHE source (e.g. 9.1 Spare Parts, 9.2 Documentation, 9.3 Alternate Product Pump)
- Entirely new sections may be inserted (e.g. Onsite Services)

### 4. Section-Level Price Conversion (Phase 2)

Two types of pricing sections:

- **Single price line** — one description + currency code + amount
- **Multiple price lines** — several line items, each with currency code + amount; some flagged "not included in total price"

Special section type **Price Summary** aggregates prices from specific prior sections (Machine Execution, Basic Execution, Product Pump, Motor Starter Cabinet) when present.

Price conversion uses factors stored in the database:

| Factor | Code | Description |
|--------|------|-------------|
| FX | `pconv_factor_values.pfc_multiplier_1/2` | Currency exchange |
| MU | `pconv_factor_values.pfc_multiplier_1/2` | Markup, duties, other |

Current 2026 values (CHE → USA): FX = 1.10 / 1.54, MU = 1.30 / 2.18.

### 5. Two USA Delivery-Term Variants

Each USA template exists in two forms, differing primarily in the Terms of Delivery section:

| Variant | DB section type | Shipping origin |
|---------|-----------------|-----------------|
| FCA Muttenz | `plsqts_type` id 12 | Switzerland |
| FOB Allendale | `plsqts_type` id 5 | USA |

### 6. Product-Line Specificity

It is not yet determined whether conversions are generic across all product lines in a product category or need to be specified per product line. Three product lines are in scope for initial analysis:

- **UBM** (e.g. UBM 20)
- **ECM** (e.g. ECM AP 10)
- **KD**

The fact that USA templates are grouped separately by product line within each delivery-term variant suggests at least some conversions may be product-line-specific.

---

## Sample Files Provided

Located in `templates_docx/`:

| File | Country | Product | Variant |
|------|---------|---------|---------|
| `ECM AP 10 KERAMIK MIT WAB VIEW E.docx` | CHE | ECM AP 10 | — |
| `UBM 20 FU_FU E.docx` | CHE | UBM 20 | — |
| `ECM AP 10 Ceramic MIT WAB VIEW_US_FCA Muttenz_11 2025.docx` | USA | ECM AP 10 | FCA Muttenz |
| `ECM AP 10 Ceramic MIT WAB VIEW_US_FOB Allendale_11 2025.docx` | USA | ECM AP 10 | FOB Allendale |
| `UBM 20 FCFC_US_FCA Muttenz_11 2025.docx` | USA | UBM 20 | FCA Muttenz |
| `UBM 20 FCFC_US_FOB Allendale_11 2025.docx` | USA | UBM 20 | FOB Allendale |

---

## Conversion Approach

Process each section of the source CHE template individually:

1. **Carry forward** — section exists in both CHE and USA, apply text/price transformations
2. **Substitute** — section is replaced by a region-specific equivalent (e.g. Terms of Delivery)
3. **Insert** — section exists only in the USA variant and must be added (e.g. Onsite Services)
4. **Omit** — section exists only in the CHE variant (none identified so far)

The migration function should accept:
- Input: CHE template (docx file or template ID)
- Parameters: target country, delivery-term variant (FCA / FOB)
- Output: USA template (docx file and/or database record)
