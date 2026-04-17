# Author to Caseware Cloud

Author converted documents to Caseware Cloud as checklists, queries, or letters.

## Prerequisites
- Caseware Cloud MCP connected (engagement URL and bearer token configured)
- Source document read and procedure outline prepared

## Critical Constraints

- All `-save` MCP operations MUST be sequential. Never invoke multiple save calls in parallel.
- **Call `build_payload` exactly ONCE per document.** If you already called `build_payload` during a convert/analyse step, use those payloads — do not call it again. Only re-call if validation failed and you fixed errors in the outline.

---

## Steps

### Step 1: For Each Document

**1.1 Pre-Save: Document Number Conflict Check (REQUIRED):**
Call `document-manager` with `includeHidden: true`. HARD FAIL if number exists.

**1.2 Build Procedure Outline** — create a procedure outline JSON with document_type, items (depth, type, text, response notation), and metadata. See `load_reference('outline-format')` for schema.

**1.3 Call `build_payload(outline)`** — the tool validates everything (depth sequences, types at depth, response completeness, duplicate detection, empty branches), builds full Caseware payloads with all boilerplate, and chunks if needed.

**1.4 Review Validation** — check `validation.valid` in the result:
- If `false`: fix errors in the outline and call `build_payload` again
- If `true`: review any `warnings` and proceed to submission

**1.5 Follow `submission_instructions`** — the `build_payload` result includes a `submission_instructions` field that tells you EXACTLY how many API calls to make and what to pass. Follow these instructions precisely. Do NOT make additional calls beyond what the instructions specify.

### Step 2: Report

| Metric | Value |
|--------|-------|
| **Files processed** | {count} |
| **Total procedures** | {count} |
| **Response type accuracy** | {percentage}% |
| **Evaluation iterations (avg)** | {number} |

**Documents Created:**

| Number | Name | Procedures |
|--------|------|------------|
| {number} | {name} | {count} |
