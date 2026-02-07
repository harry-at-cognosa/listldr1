# Template Migration — Comparative Analysis

Comparison of the 6 sample `.docx` templates in `templates_docx/`, cross-referenced with the database schema and existing design documents.

---

## 1. File Inventory

### CHE (source) templates — 2 files

| File | Product line | Sections |
|------|-------------|----------|
| `ECM AP 10 KERAMIK MIT WAB VIEW E.docx` | ECM | Cover + 8 numbered |
| `UBM 20 FU_FU E.docx` | UBM | Cover + 8 numbered |

### USA (target) templates — 4 files

| File | Product line | Variant | Sections |
|------|-------------|---------|----------|
| `ECM AP 10 Ceramic MIT WAB VIEW_US_FCA Muttenz_11 2025.docx` | ECM | FCA Muttenz | Cover + 10 numbered |
| `ECM AP 10 Ceramic MIT WAB VIEW_US_FOB Allendale_11 2025.docx` | ECM | FOB Allendale | Cover + 10 numbered |
| `UBM 20 FCFC_US_FCA Muttenz_11 2025.docx` | UBM | FCA Muttenz | Cover + 10 numbered |
| `UBM 20 FCFC_US_FOB Allendale_11 2025.docx` | UBM | FOB Allendale | Cover + 10 numbered |

Companion `.xlsx` files exist for each USA template (price calculation sheets, out of scope for now).

---

## 2. Page Size

| Template set | Page size |
|-------------|-----------|
| ECM — CHE | A4 |
| ECM — USA (both variants) | A4 |
| UBM — CHE | A4 |
| UBM — USA (both variants) | US Letter |

**Finding:** ECM keeps A4 in both regions. UBM changes from A4 (CHE) to US Letter (USA). This is a product-line-specific difference — the migration function must handle page-size selection per product line rather than applying a blanket rule.

---

## 3. Section Structure Comparison

### CHE templates (both ECM and UBM) — 9 sections

```
Cover Page
1 – Principal Characteristics
2 – General Technical Data
3 – Machine Execution
4 – Product Pump
5 – Motor Starter Cabinet
6 – Price Summary
7 – Options and Accessories
8 – Terms of Delivery
```

### USA templates (both ECM and UBM) — 11 sections

```
Cover Page
1  – Principal Characteristics
2  – General Technical Data
3  – Machine Execution
4  – Product Pump
5  – Motor Starter Cabinet
6  – Onsite Services                    ← NEW (not in CHE)
7  – Price Summary
8  – Options and Accessories
9  – List of Accessories                ← NEW (expanded from subsection)
10 – Terms of Delivery
```

**Key differences:**

| # | Difference | Detail |
|---|-----------|--------|
| 1 | **Onsite Services** added | USA section 6; no CHE equivalent. Has its own total price. |
| 2 | **List of Accessories** split out | CHE bundles accessories into section 7 (Options and Accessories). USA separates them: section 8 = Options and Accessories, section 9 = List of Accessories. |
| 3 | **Section renumbering** | Insertions push Price Summary from 6→7, Options from 7→8, Terms of Delivery from 8→10. |
| 4 | **Subsections added** | USA section 9 may contain subsections: 9.1 Spare Parts, 9.2 Documentation, 9.3 Alternate Product Pump. |

---

## 4. Cover Page Differences

| Element | CHE | USA |
|---------|-----|-----|
| Company name | WILLY A. BACHOFEN AG | WAB US Corp. |
| Address | Utengasse 15–17, CH-4058 Basel | (USA address) |
| Greeting | "Dear Sirs" | "Dear (Name):" |
| Contact block | Minimal | Expanded with US contact details |
| Signature block | Single | Multiple / expanded |
| Logo / branding | CHE logo image | USA logo image |
| Table of Contents | 8 entries | 10 entries |
| Section type in DB | `plsqts_type` id 18 (Cover Page - CH/EU) | `plsqts_type` id 13 (Cover Page) |

---

## 5. Section Types in Database

The `plsqts_type` table defines 17 section types. Region-specific types are highlighted:

| ID | Name | Total Price | Lineitem Prices | Region |
|----|------|:-----------:|:---------------:|--------|
| 1 | Product Pump | yes | — | shared |
| 2 | General Technical Data | — | — | shared |
| 3 | Machine Execution | yes | — | shared |
| 4 | Motor Starter Cabinet | yes | — | shared |
| **5** | **Terms of Delivery - FOB Allendale** | — | — | **USA** |
| 6 | Principal Characteristics | — | — | shared |
| 7 | Price Summary | yes | yes | shared |
| 8 | Options and Accessories | — | yes | shared |
| 9 | Onsite Services | yes | — | **USA only** |
| 10 | Grinding Mills | yes | — | shared |
| 11 | Basic Execution | — | — | shared |
| **12** | **Terms of Delivery - FCA Muttenz** | — | — | **USA** |
| **13** | **Cover Page** | — | — | **USA** |
| 14 | Options | — | yes | shared |
| 15 | List of Accessories | — | yes | shared |
| **18** | **Cover Page - CH/EU** | — | — | **CHE** |
| **19** | **Terms of Delivery (CH/EU)** | — | — | **CHE** |

**Observations:**
- Cover pages have separate types: 18 for CHE, 13 for USA.
- Terms of Delivery has three variants: 19 (CHE), 5 (USA FOB), 12 (USA FCA).
- Onsite Services (9) exists only in USA templates.
- List of Accessories (15) and Options (14) are broken out as separate types, supporting the USA split of CHE section 7.

---

## 6. Headers, Footers, and Branding

| Element | CHE | USA |
|---------|-----|-----|
| Header image | WAB AG logo | WAB US Corp. logo |
| Footer content | Swiss company info | US company info |
| Right-margin text | CHE variant | USA variant |
| Branding images embedded | CHE-specific | USA-specific |

**Requirement:** Branding image files for USA templates need to be provided as source assets. These are embedded in the docx as image relationships and cannot be derived from the CHE templates.

---

## 7. Text Differences

### Product naming (German → English)

| CHE | USA |
|-----|-----|
| KERAMIK | Ceramic |
| FU\_FU | FCFC |
| DYNO-MILL UBM 20 FU\_FU | DYNO-MILL UBM 20 FCFC |
| DYNO-MILL ECM AP 10 KERAMIK MIT WAB VIEW | DYNO-MILL ECM AP 10 Ceramic MIT WAB VIEW |

### Additional USA text

- Tax-compliance language (not present in CHE)
- Delivery disclaimers and shipping terms specific to US trade
- Extended warranty or service language in applicable sections

### Content modifications within shared sections

Several sections that exist in both CHE and USA have textual differences beyond simple name translation. The General Technical Data section, in particular, may have alternate content in the USA version (different specifications, units, or regulatory references). The extent of section-by-section text replacement rules needs to be defined.

---

## 8. FCA Muttenz vs FOB Allendale

Comparing the two USA variants (FCA vs FOB) for both ECM and UBM:

| Aspect | FCA Muttenz | FOB Allendale |
|--------|-------------|---------------|
| Section type (Terms of Delivery) | `plsqts_type` id 12 | `plsqts_type` id 5 |
| Shipping origin | Muttenz, Switzerland | Allendale, NJ, USA |
| Incoterm | FCA (Free Carrier) | FOB (Free on Board) |

**Finding:** The FCA vs FOB difference appears to be confined to the final section (Terms of Delivery). All other sections — cover page, technical content, pricing — are identical between the two variants of the same product. This means the migration function can treat FCA/FOB as a simple section-swap at the end, not a document-wide difference.

---

## 9. Pricing Infrastructure

### Conversion pair

`country_conversion_pairs` table:

| ccp\_id | from | to |
|---------|------|-----|
| 1 | CHE | USA |

### Factor types

`price_conv_factors` table:

| pcf\_id | code | description |
|---------|------|-------------|
| 1 | FX | currency conversion etc |
| 2 | MU | markup, duties, other |

### Current factor values

`pconv_factor_values` (CHE → USA, valid 2026-01-01 to 2026-12-31):

| Factor | multiplier\_1 | multiplier\_2 |
|--------|:------------:|:------------:|
| FX | 1.1000 | 1.5400 |
| MU | 1.3000 | 2.1800 |

**Open questions:**
- When is `multiplier_1` used vs `multiplier_2`? (by product category? section type? price magnitude?)
- Is the formula `CHF × FX × MU`, or `CHF × (FX + MU)`, or something else?
- Do the Excel companion files contain the authoritative calculation logic?

### Sections with pricing

| Pricing model | Section types |
|---------------|--------------|
| Single total price | Product Pump (1), Machine Execution (3), Motor Starter Cabinet (4), Onsite Services (9), Grinding Mills (10) |
| Lineitem prices | Price Summary (7), Options and Accessories (8), Options (14), List of Accessories (15) |
| Both | Price Summary (7) |

---

## 10. Template Counts in Database

The `plsq_templates` table contains 84 loaded templates. Relevant examples:

| plsqt\_id | name | country |
|-----------|------|---------|
| 21 | DYNO-MILL UBM 20 FU\_FU KERAMIK : CH/CHF | CHE |
| 24 | DYNO-MILL ECM AP 10 KERAMIK MIT WAB VIEW : CH/CHF | CHE |
| 28 | UBM 20 FU\_FU E | CHE |
| 29 | ECM AP 10 KERAMIK MIT WAB VIEW E | CHE |
| 1 | DYNO-MILL 20 FCFC\_US\_FOB Allendale : USA/USD | USA |
| 23 | DYNO-MILL ECM-AP 10 Ceramic MIT WAB VIEW : USA/USD | USA |

---

## 11. What's Needed from Outside

The following cannot be derived from the existing CHE templates or database and must be supplied:

| Item | Detail |
|------|--------|
| **USA branding images** | Logo, header image, any other embedded graphics for USA templates |
| **Alternate General Technical Data content** | USA version may differ from CHE beyond simple text substitution; full replacement text needed |
| **Section-by-section text replacement rules** | Mapping of CHE text → USA text for each section type (beyond product-name translation) |
| **Product-line specificity rules** | Which conversions are generic across a product category vs. product-line-specific |
| **Onsite Services section content** | This section has no CHE source; its content must come from an external template or reference |
| **List of Accessories split rules** | How CHE "Options and Accessories" maps to the separate USA "Options and Accessories" + "List of Accessories" sections |
| **Subsection content** | Content for USA-only subsections (9.1 Spare Parts, 9.2 Documentation, 9.3 Alternate Product Pump) |
| **Price formula** | How FX and MU factors combine, and when to use multiplier\_1 vs multiplier\_2 |
| **FCA vs FOB Terms of Delivery text** | Full text for both delivery-term variants (may already be extractable from sample USA templates) |

---

## 12. Summary of Conversion Operations by Section

| CHE section | USA section(s) | Operation |
|-------------|---------------|-----------|
| Cover Page | Cover Page | **Transform** — company, greeting, contact block, TOC, branding |
| 1 – Principal Characteristics | 1 – Principal Characteristics | **Transform** — text replacements |
| 2 – General Technical Data | 2 – General Technical Data | **Transform or Replace** — may need alternate content |
| 3 – Machine Execution | 3 – Machine Execution | **Transform** — text + price |
| 4 – Product Pump | 4 – Product Pump | **Transform** — text + price |
| 5 – Motor Starter Cabinet | 5 – Motor Starter Cabinet | **Transform** — text + price |
| *(none)* | 6 – Onsite Services | **Insert** — new section, content from external source |
| 6 – Price Summary | 7 – Price Summary | **Transform** — recalculate from upstream sections + price conversion |
| 7 – Options and Accessories | 8 – Options and Accessories | **Transform** — text + lineitem prices |
| *(split from above)* | 9 – List of Accessories | **Insert/Split** — content extracted or supplied separately |
| 8 – Terms of Delivery | 10 – Terms of Delivery | **Substitute** — replace with FCA (type 12) or FOB (type 5) variant |
