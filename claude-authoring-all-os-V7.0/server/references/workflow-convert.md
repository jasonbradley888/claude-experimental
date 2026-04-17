# Read and Analyse Source Documents

Read source document content and analyse structure to produce a procedure outline for `build_payload`.

## Core Rules

- Never change original document wording; only convert format
- Go directly from reading content to producing a procedure outline — no intermediate markdown step
- Remove bullet indicators (a., b., 1., etc.) — Caseware auto-numbers
- Execute continuously without pausing for confirmation

---

## Steps

**Step 1:** Identify files to process (.docx, .xlsx, .pptx, .pdf, .md).

**Step 2:** Read file content:

| Format | Method |
|--------|--------|
| `.docx`, `.xlsx`, `.pptx` | Use `convert_document` tool to extract text content |
| `.pdf` | Read natively (Claude reads PDFs directly) |
| `.md` | Read directly |

**Step 3:** Analyse structure and produce procedure outline:

1. Detect document type per `load_reference('document-type-detection')`
2. Analyse document structure — identify hierarchy levels, sections, procedures
3. Determine response types for each procedure (Priority 1-4 rules from `load_reference('checklist-authoring')`)
4. Apply type-specific rules:
   - **Checklists**: Every procedure needs a response type (conclusions are auto-generated)
   - **Queries**: Question sets at depth 0, questions at depth 1 with dual columns
   - **Letters**: Flat structure at depth 0, detect dynamic elements and formula placeholders
5. Produce a procedure outline JSON (see `load_reference('outline-format')` for schema)

**Step 4:** Present outline summary (do NOT call `build_payload` — that happens in the author step):

| File | Type | Items | Groups | Procedures |
|------|------|-------|--------|------------|
| ... | ... | ... | ... | ... |

> **Important:** This workflow produces the procedure outline only. Do not call `build_payload` or submit to Caseware Cloud. The author workflow handles payload building and submission.
