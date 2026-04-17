# Full Authoring Workflow

Complete end-to-end workflow: convert, validate, and author documents to Caseware Cloud.

## Prerequisites
- Caseware Cloud MCP connected (engagement URL and bearer token configured)
- Source documents to process (Word, Excel, PDF, PowerPoint, or markdown)

## Critical Constraints

- All `-save` MCP operations MUST be sequential. Never invoke multiple save tools simultaneously.
- **Call `build_payload` exactly ONCE per document** — in Phase 3 only. Phase 2 produces the outline; Phase 3 builds the payload and submits. Never call `build_payload` during the read/analyse phase.

---

## Phase 1: Initialization

Collect user inputs:

| Input | Example |
|-------|--------|
| Document(s) | Uploaded file or path |

---

## Phase 2: Read & Analyse

### Step 2.1: Read source documents

For each file:
- `.docx`, `.xlsx`, `.pptx` — use `convert_document` tool to extract text content
- `.pdf` — read natively (Claude reads PDFs directly)
- `.md` — read directly

### Step 2.2: For each file:
1. Read content
2. Identify type (checklist/query/letter) per `load_reference('document-type-detection')`
3. Analyse structure and produce a procedure outline directly — do NOT produce intermediate depth-marked markdown:
   - Identify hierarchy levels (groups, headings, procedures)
   - Apply type-specific rules: checklists need response types (conclusions are auto-generated); queries need question set structure; letters need flat structure + dynamic elements
   - Validate: no depth jumps >1, max depth 4, types valid for depth
   - Remove bullet indicators — Caseware auto-numbers

Report discovery summary before proceeding.

---

## Phase 3: Authoring by Type

Build a procedure outline from the analysed structure, then call `build_payload(outline)` to generate validated payloads. See `load_reference('outline-format')` for the outline schema.

### Phase 3A: Checklists
Load `load_reference('checklist-authoring')` for response type detection rules (Priority 1-4). Build outline with items (depth, type, text, response notation). Call `build_payload` — it handles boilerplate, validation, and chunking. Follow the `submission_instructions` in the result exactly.

### Phase 3B: Queries
Build outline with questionSet/question items. Call `build_payload` — it handles `<p>` wrapping and dual-column structure. Follow the `submission_instructions` in the result exactly.

### Phase 3C: Letters
Build outline with sections (title + content with `[bracketed placeholders]`). Call `build_payload` — it handles dynamic element detection, HTML conversion, and two-step creation templates. Follow the `submission_instructions` in the result exactly.

### Phase 3D: Financial Statements (Not Implemented)
Notify user, suggest manual authoring, continue.

---

## Phase 4: Completion

### Summary Report

| Metric | Value |
|--------|-------|
| Files processed | X |
| Checklists authored | C |
| Queries authored | Q |
| Letters authored | L |
| Errors/warnings | N |

**WORKFLOW COMPLETE**
