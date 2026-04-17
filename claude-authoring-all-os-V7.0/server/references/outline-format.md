# Procedure Outline Format

Reference for the `build_payload` tool. Instead of building full JSON payloads manually, output a lightweight **procedure outline** and call `build_payload` — it handles all boilerplate, validation, and chunking.

---

## Checklist Outline

```json
{
  "document_type": "checklist",
  "name": "Revenue Testing Checklist",
  "number": "B-100",
  "folder_id": "abc123...",
  "purpose": "Create revenue testing checklist",
  "purpose_summary": "Revenue Testing",
  "guidance": "Optional top-level guidance",
  "default_response": "choice:Yes|No|Not Applicable",
  "items": [
    {"depth": 0, "type": "group", "text": "Revenue Recognition"},
    {"depth": 1, "type": "heading", "text": "Verify policies"},
    {"depth": 2, "type": "procedure", "text": "Has the policy been reviewed?"},
    {"depth": 2, "type": "procedure", "text": "Describe the revenue process.",
     "response": "text"},
    {"depth": 2, "type": "procedure", "text": "Calculate the total revenue.",
     "response": "number"},
    {"depth": 2, "type": "procedure", "text": "What date was the review completed?",
     "response": "date"}
  ]
}
```

> **Conclusions:** Do NOT include conclusion items. `build_payload` handles this automatically via `includeConclusion: true`.

### Checklist Settings (default_response)

Set `default_response` at the top level to apply a default response type to any procedure that does not specify an explicit `response` field. This simplifies outlines where most procedures share the same response type.

- Procedures/conclusions with an explicit `response` are never overridden
- The default is expanded before validation, so validation passes normally
- Metadata includes `default_response_applied` count
- Also works in update mode (applied to new items without `id`)

### Automatic Text Processing

`build_payload` automatically applies these transformations to procedure and conclusion text:

1. **Numbering stripping** — leading indicators like `1.`, `a)`, `ii.`, `(1)`, bullets are removed (Caseware auto-numbers)
2. **Dynamic element detection** — formulas (`engprop()`, `collaborate()`, `wording()`) and known placeholders (`[Date]`, `[Select Staff]`, `[Enter...]`) are converted to Caseware HTML. Generic `[bracketed text]` is NOT converted in checklists (only in letters).
3. **Left-align wrapping** — text is wrapped in `<p style="text-align: left;">` for consistent rendering. Already-HTML text is not double-wrapped. Groups and headings are not wrapped.

### Response String Notation

| Notation | Meaning | Builder Output |
|----------|---------|----------------|
| `"choice:Yes,No,Not Applicable"` | Picklist with specific options | Choice column with `inlineChoices` calculated |
| `"choice:Low,Moderate,High,Not Applicable"` | Custom picklist | Choice column (dropdown if >3 or long text) |
| `"choice"` | Default Yes/No/Not Applicable | Same as `"choice:Yes,No,Not Applicable"` |
| `"text"` | Free text entry | Text column, `includeNote: false` |
| `"text:Describe the process"` | Text with custom placeholder | Text column with specified placeholder |
| `"number"` | Numeric input | Number column |
| `"date"` | Date picker | Date column |

**Rules applied by the builder:**
- "Not Applicable" auto-appended if missing from choice lists
- `inlineChoices: true` only when ≤3 choices AND max text ≤20 chars
- `includeNote: false` for text responses (avoids duplicate input)
- `includeNote: true` with `notePlaceholder: "Response and Comments"` for all others
- `includeSignOffs: true` on all items
- Choices use `{"text": "Yes"}` (never `{"label": "Yes"}`)

### Optional Fields Per Item

| Field | Type | Purpose |
|-------|------|---------|
| `guidance` | string | Populates the guidance field on the procedure |
| `authoritative_references` | string[] | Up to 5 references (e.g., `["AS 2201.39", "ISA 315"]`) |
| `hide_condition` | string | Condition expression for visibility |
| `hidden` | boolean | Default: `false` |
| `placeholder` | string | Maps to column placeholder for text/choice inputs |

---

## Query Outline

```json
{
  "document_type": "query",
  "name": "Revenue Info Request",
  "number": "B-100Q",
  "folder_id": "abc123...",
  "purpose": "Gather client information for revenue cycle",
  "purpose_summary": "Revenue Process Query",
  "instructions": "Please provide the following information and supporting documents.",
  "items": [
    {"depth": 0, "type": "questionSet", "text": "Process Overview"},
    {"depth": 1, "type": "question", "text": "Describe your revenue recognition policy.",
     "title": "Revenue Recognition Policy",
     "placeholder": "Describe policy and key judgments"}
  ]
}
```

**Builder handles:**
- Wrapping question text in `<p>` tags
- Adding dual columns: text input + file upload
- Setting `hidden: false` and `hideCondition: null`

---

## Letter Outline

```json
{
  "document_type": "letter",
  "name": "E-600 - Management Reps - Draft",
  "number": "E-600",
  "folder_id": "abc123...",
  "purpose": "Create management representation letter",
  "purpose_summary": "Management Representations",
  "area_title": "Management Representations",
  "sections": [
    {"title": "Date", "content": "[Letter Date]"},
    {"title": "Addressee", "content": "To [Auditor Name]"},
    {"title": "Body", "content": "We confirm that the financial statements of [Entity Name] for the year ended [Year End]..."},
    {"title": "Closing", "content": "Yours truly,\n\n[Select Staff]"}
  ]
}
```

**Builder handles:**
- Two-step creation (step 1: create doc, step 2: add sections)
- Dynamic element detection and HTML conversion:
  - `[Letter Date]` → date placeholder
  - `[Entity Name]` → `engprop("name")` formula
  - `[Year End]` → `engprop("yearend", 0, "longDate")` formula
  - `[Select Staff]` → staff selector
  - `[Enter...]`, `[Insert...]` → input-area placeholders
  - Other `[bracketed text]` → input-area placeholder (fallback)
- Unique 22-char placeholder IDs
- HTML wrapping in `<p>` tags

---

## Calling `build_payload`

### Step 1: Build the outline

After converting and analysing the source document, output the outline JSON with your structure decisions (depth, type, response type).

### Step 2: Call `build_payload`

```
build_payload(outline)
```

### Step 3: Handle the result

Check `validation.valid` — if false, fix errors and retry.
Follow `submission_instructions` in the result — it is the single source of truth
for how many API calls to make and what to pass.

---

## Update Mode (Editing Existing Documents)

To edit an existing document, add `"mode": "update"` and `"document_id"` to the outline. The builder produces a sparse payload — only changed fields are sent.

### Update Outline: Checklist

```json
{
  "document_type": "checklist",
  "mode": "update",
  "document_id": "existing-doc-id-22chars",
  "items": [
    {"id": "existingProcId-22chars", "text": "Updated procedure text"},
    {"id": "procToSoftDelete22char", "_delete": true},
    {"depth": 2, "type": "procedure", "text": "New procedure", "response": "choice"}
  ]
}
```

### Update Outline: Query

```json
{
  "document_type": "query",
  "mode": "update",
  "document_id": "existing-doc-id-22chars",
  "items": [
    {"id": "existingQuestId22chars", "title": "Updated question title"},
    {"depth": 1, "type": "question", "text": "New question", "title": "New Q"}
  ]
}
```

### Update Outline: Letter

```json
{
  "document_type": "letter",
  "mode": "update",
  "document_id": "existing-doc-id-22chars",
  "area_id": "existing-area-id-22ch",
  "area_title": "Letter Title",
  "sections": [
    {"id": "existingSectionId22ch", "content": "Updated content"},
    {"title": "New Section", "content": "New content"}
  ]
}
```

### Update Item Rules

| Item Pattern | What to Include | What Happens |
|-------------|----------------|-------------|
| `{"id": "...", "text": "new"}` | `id` + only changed fields | Sparse update — API preserves unchanged fields |
| `{"depth": 2, "type": "procedure", ...}` | All fields (no `id`) | New item appended to document |
| `{"id": "...", "_delete": true}` | `id` + `_delete` flag | Soft-delete — sets `hidden: true` |

### Update Result

All update modes return a single `payload` (not chunked):

```json
{
  "payload": {...},
  "validation": {"valid": true, "errors": [], "warnings": []},
  "metadata": {"mode": "update", "modified_procedures": 1, "added_procedures": 1, "deleted_procedures": 0}
}
```

Submit the `payload` via the appropriate `-save` tool. Letter updates are single-call (no two-step needed).

---

## What the Builder Handles vs What You Decide

| Your Decision (Outline) | Builder Handles (Code) |
|--------------------------|----------------------|
| What depth? (0-4) | Depth validation (no jumps >1, max 4) |
| What type? (group/heading/procedure) | Type-at-depth validation |
| What response type? (Priority 1-4) | Full `rows`/`columns`/`choices` JSON |
| Guidance text | `includeNote`, `notePlaceholder` boilerplate |
| Document name/number | `documentInfo` structure |
| — | `inlineChoices` calculation |
| — | "Not Applicable" auto-append |
| — | Chunking at D0 boundaries |
| — | Letter two-step creation |
| — | Dynamic element HTML |
| — | Placeholder ID generation |
