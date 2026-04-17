# Payload Schemas Reference

Consolidated JSON schemas for checklist, query, and letter payloads submitted via MCP.

> **These schemas are produced by the `build_payload` tool.** When authoring, use the Procedure Outline format (`load_reference('outline-format')`) and call `build_payload(outline)` — the tool generates these full payloads with all boilerplate, validation, and chunking. Refer to these schemas only if you need to understand the raw payload structure.

---

## 1. Checklist (`checklist-save`)

### Top-Level Payload

```json
{
  "id": null,
  "documentInfo": {
    "folder": "uuid-base64url",
    "name": "Checklist Name",
    "number": "DOC-XXX"
  },
  "guidance": "Guidance text from [G] markers",
  "includeConclusion": true,
  "conclusionTitle": "Conclusion",
  "procedures": [...],
  "purpose": "Description of why checklist is being created",
  "purposeSummary": "Short title for suggestion set"
}
```

> **ID fields:** For new documents (with `documentInfo`), omit all `id` fields on procedures, rows, columns, and choices — the server auto-generates them. For updates (using a captured document ID), omit `id` on new procedures being appended.

> **Group nodes must NOT have `rows`:** The MCP rejects group-type nodes that include a `rows` array. Groups and headings are structural containers only — never attach response rows to them. The `build_payload` tool enforces this automatically.

> **Choice objects must NOT have `id`:** Choice objects must be `{ "text": "Yes" }` only. Including an `id` field (e.g., `{ "id": "...", "text": "Yes" }`) causes `UnableToCreateSubObject` errors. The `build_payload` tool strips any stray choice IDs automatically.

> **Summary:** NEVER populate the `summary` field on procedures. Omit it entirely or pass `""`. Never generate summary text.

> **notePlaceholder:** Always use `"Response and Comments"` on every procedure with `includeNote: true`.

> **"Not Applicable" option:** All picklist and multi-picklist responses MUST include `"Not Applicable"` as the final choice (use the full text, not "N/A").

### Procedure: CHOICE Response (Yes/No/N/A)

```json
{
  "depth": 2,
  "type": "procedure",
  "text": "Has management approved the financial statements?",
  "hidden": false,
  "hideCondition": null,
  "includeNote": true,
  "notePlaceholder": "Response and comments",
  "includeSignOffs": true,
  "guidance": null,
  "authoritativeReferences": [],
  "rows": [{
    "columns": [{
      "type": "choice",
      "placeholder": "",
      "includeOtherChoice": false,
      "inlineChoices": true,
      "choices": [
        { "text": "Yes" },
        { "text": "No" },
        { "text": "Not Applicable" }
      ]
    }]
  }]
}
```

> **`inlineChoices`:** Set `true` when choices ≤ 3 AND max choice text length ≤ 20 characters (renders as radio buttons). Set `false` for more choices or longer text (renders as dropdown).

> **`notePlaceholder` vs column `placeholder`:** `notePlaceholder` is placeholder text for the note/comment section attached to the procedure. `placeholder` (on column) is placeholder text inside the response input field itself. When source data has a "Response Placeholder", map it to the column `placeholder`, not to `notePlaceholder`.

> **`hideCondition`:** Condition expression string controlling procedure visibility. Default `null` (always visible). Format: `"[DocNumber] [ProcedureText] = [Value]"`.

> **`authoritativeReferences`:** Array of `{ "reference": "AS 2201.39" }` objects. Cap at 5 per procedure. Split multi-line sources on `\n`.

### Procedure: TEXT Response (Free-Form Entry)

```json
{
  "depth": 1,
  "type": "procedure",
  "text": "Describe the client's business and primary revenue streams",
  "hidden": false,
  "includeNote": false,
  "includeSignOffs": true,
  "rows": [{
    "columns": [{
      "type": "text",
      "placeholder": "Enter description here"
    }]
  }]
}
```

### Procedure: PICKLIST Response (Multiple Options)

```json
{
  "depth": 2,
  "type": "procedure",
  "text": "What is the assessed level of inherent risk?",
  "hidden": false,
  "includeNote": true,
  "notePlaceholder": "Response and comments",
  "includeSignOffs": true,
  "rows": [{
    "columns": [{
      "type": "choice",
      "placeholder": "",
      "includeOtherChoice": false,
      "inlineChoices": true,
      "choices": [
        { "text": "Low" },
        { "text": "Moderate" },
        { "text": "High" },
        { "text": "Not Applicable" }
      ]
    }]
  }]
}
```

### GROUP (depth 0, no response)

```json
{
  "depth": 0,
  "type": "group",
  "text": "Revenue Recognition",
  "hidden": false,
  "includeNote": true,
  "includeSignOffs": true,
  "notePlaceholder": "Response and comments"
}
```

### HEADING (depth 1, no response)

```json
{
  "depth": 1,
  "type": "heading",
  "text": "Understanding the Process",
  "hidden": false,
  "includeNote": true,
  "includeSignOffs": true,
  "notePlaceholder": "Response and comments"
}
```

### CONCLUSION

> **Do NOT add conclusion items to the procedures array.** Set `"includeConclusion": true` on the top-level payload — the API generates the real conclusion widget automatically. Explicit conclusion items in the procedures array render as groups, not actual conclusions. The `build_payload` tool strips any conclusion items from the outline automatically.

### Chunking Pattern (>50 Procedures)

> **Reference only.** `build_payload` handles chunking automatically. These patterns describe what the tool does internally — do NOT chunk manually.

1. **<=50 procedures:** Single `checklist-save` call with `id: null`
2. **>50 procedures:** Split at `[D0]` group boundaries (max 20 per chunk)
   - **First chunk:** `id: null` -> capture returned document ID
   - **Subsequent chunks:** Use captured ID
   - **Conclusion:** Auto-generated via `includeConclusion: true` — do NOT include conclusion items in any chunk
   - **Sequential submission required:** Wait for each response before sending next
   - Never split mid-group
   - Use 15 per chunk if procedures have long guidance text (>500 chars)
3. **Truncation detection:** After each `checklist-save`, compare submitted procedure count to response procedure count. If they differ, HARD FAIL with `PAYLOAD_TRUNCATED`.

### Update Mode (Editing Existing Checklists)

For updates, pass the existing document ID and only the changed/new/deleted procedures. No `documentInfo`, no chunking, no `includeConclusion`.

```json
{
  "id": "existingDocumentId22ch",
  "procedures": [
    {"id": "existingProcId22chars", "text": "Updated procedure text"},
    {"id": "procToSoftDelete22char", "hidden": true},
    {
      "depth": 2, "type": "procedure", "text": "New procedure",
      "rows": [{"columns": [{"type": "choice", "choices": [{"text": "Yes"}, {"text": "No"}, {"text": "Not Applicable"}]}]}],
      "includeNote": true, "notePlaceholder": "Response and Comments", "includeSignOffs": true
    }
  ]
}
```

> **Sparse updates:** Items with `id` only need the `id` field plus changed fields — the API preserves all unchanged fields. Items without `id` are new and need the full procedure structure. Soft-delete uses `"hidden": true`.

---

## 2. Query (`query-save`)

### Top-Level Payload

```json
{
  "id": null,
  "documentInfo": {
    "folder": "uuid-base64url",
    "name": "Revenue Process Information Request",
    "number": "B-100Q"
  },
  "instructions": "Please provide the following information...",
  "purpose": "Gather client information for revenue cycle audit procedures",
  "purposeSummary": "Revenue Process Query",
  "questions": [...]
}
```

### QuestionSet (depth 0)

```json
{
  "id": null,
  "depth": 0,
  "type": "questionSet",
  "title": "Process Overview",
  "hidden": false,
  "hideCondition": null
}
```

### Question (depth 1, dual-column)

```json
{
  "id": null,
  "depth": 1,
  "type": "question",
  "title": "Revenue Recognition Policy",
  "text": "<p>Please describe your revenue recognition policy and provide supporting documentation.</p>",
  "rows": [{
    "columns": [
      {"type": "text", "placeholder": "Describe revenue recognition policy"},
      {"type": "files", "placeholder": "", "fileDestination": {}}
    ]
  }],
  "hidden": false,
  "hideCondition": null
}
```

### Minimal Template

```json
{
  "id": null,
  "documentInfo": {
    "folder": "[FOLDER_ID]",
    "name": "[QUERY_NAME]",
    "number": "[DOC_NUMBER]Q"
  },
  "instructions": "[CLIENT_INSTRUCTIONS]",
  "purpose": "[INTERNAL_PURPOSE]",
  "purposeSummary": "[SHORT_TITLE]",
  "questions": [
    {
      "id": null, "depth": 0, "type": "questionSet",
      "title": "[SECTION_TITLE]", "hidden": false, "hideCondition": null
    },
    {
      "id": null, "depth": 1, "type": "question",
      "title": "[QUESTION_TITLE]",
      "text": "<p>[QUESTION_TEXT]</p>",
      "rows": [{"columns": [
        {"type": "text", "placeholder": "[PLACEHOLDER]"},
        {"type": "files", "placeholder": "", "fileDestination": {}}
      ]}],
      "hidden": false, "hideCondition": null
    }
  ]
}
```

### Query Rules

- Use related document number with "Q" suffix (e.g., "B-100Q")
- Each question has two columns: text input + file upload
- Include `hidden: false` and `hideCondition: null` on all items
- Place queries in same folder as related documents
- First retrieve an existing query of the same type as format reference

### Update Mode (Editing Existing Queries)

```json
{
  "id": "existingDocumentId22ch",
  "questions": [
    {"id": "existingQuestId22chars", "title": "Updated question title"},
    {"id": "questToSoftDelete22ch", "hidden": true},
    {
      "depth": 1, "type": "question", "title": "New Question",
      "text": "<p>New question text</p>",
      "rows": [{"columns": [
        {"type": "text", "placeholder": "Enter response"},
        {"type": "files", "placeholder": "", "fileDestination": {}}
      ]}],
      "hidden": false, "hideCondition": null
    }
  ]
}
```

---

## 3. Letter (`statement-save`)

### Two-Step Creation (CRITICAL)

For **new letters**, the API ignores sections on initial creation. You MUST use two calls.

**Step 1: Create the Letter**

```json
{
  "id": null,
  "type": "letter",
  "documentInfo": {
    "folder": "folderId",
    "name": "Letter Name - Draft",
    "number": "DOC-XXX"
  },
  "purpose": "Description of why the letter is being created",
  "purposeSummary": "Short title for the suggestion set",
  "documentMap": [{
    "type": "area",
    "title": "Letter Title",
    "sections": []
  }]
}
```

Capture from response: `response.id` (document ID) and `response.documentMap[0].id` (area ID).

**Step 2: Add Sections**

```json
{
  "id": "docIdFromStep1",
  "type": "letter",
  "documentMap": [{
    "id": "areaIdFromStep1",
    "type": "area",
    "title": "Letter Title",
    "excludeFromTableOfContents": false,
    "dontNumberInTableOfContents": false,
    "hidden": false,
    "sections": [
      {
        "type": "content",
        "title": "Section Name",
        "content": "<p>HTML content here</p>",
        "depth": 0,
        "excludeFromTableOfContents": false,
        "dontNumberInTableOfContents": false,
        "hidden": false
      }
    ]
  }]
}
```

### Dynamic Element HTML Templates

**Formula:**
```html
<span formula="engprop(&quot;name&quot;)" class="formula">Entity Name</span>
```

**Date Placeholder:**
```html
<span placeholder="uniqueId22chars" type="date" user="null" contenteditable="false" custom-label="[Original Text]" title="[Original Text]" class="placeholder unselected"><span>[Original Text]</span><span class="caret hidden-print">&nbsp;</span></span>
```

**Input Placeholder:**
```html
<span placeholder="uniqueId22chars" contenteditable="false" type="input-area" title="[Original Text]" custom-label="[Original Text]" class="placeholder unselected">[Original Text]</span>
```

**Staff Selector:**
```html
<span placeholder="uniqueId22chars" type="staff" user="undefined" contenteditable="false" custom-label="" class="placeholder unselected"><span>Select Staff</span><span class="caret hidden-print">&nbsp;</span></span>
```

### Formula Reference

| Formula | Returns |
|---------|---------|
| `engprop("name")` | Entity/engagement name |
| `engprop("yearend", 0, "longDate")` | Year end (e.g., "December 31, 2025") |
| `engprop("yearend", 0, "shortDate")` | Year end (e.g., "12/31/2025") |
| `collaborate("firmName")` | Audit firm name |
| `collaborate("legalName")` | Client legal name |
| `collaborate("clientAddressId", "address1")` | Address line 1 |
| `collaborate("clientAddressId", "address2")` | Address line 2 |
| `collaborate("clientAddressId", "address3")` | Address line 3 |
| `collaborate("clientAddressId", "city")` | City |
| `collaborate("clientAddressId", "province")` | State/Province |
| `collaborate("clientAddressId", "country")` | Country |
| `collaborate("clientAddressId", "postalCode")` | Postal/ZIP code |
| `wording("@glossaryId")` | Dynamic glossary term |

### Detection Rules (Content Pattern -> Element Type)

| Content Pattern | Element Type | Formula/Config |
|-----------------|--------------|----------------|
| Entity Name, Company Name, Client Name | Formula | `engprop("name")` |
| Year End, Period End, Balance Sheet Date | Formula | `engprop("yearend", 0, "longDate")` |
| Firm Name, Auditor Firm | Formula | `collaborate("firmName")` |
| Legal Name | Formula | `collaborate("legalName")` |
| Address fields | Formula | `collaborate("clientAddressId", "field")` |
| `[Date]`, `[Select Date]`, `[Letter Date]` | Date Placeholder | `type="date"` |
| `[Enter...]`, `[Insert...]`, `[Describe...]` | Input Placeholder | `type="input-area"` |
| Signature, Signed by, `[Select Staff]` | Staff Selector | `type="staff"` |
| Any other `[bracketed text]` | Input Placeholder (fallback) | `type="input-area"` |

### Letter Rules

- All sections at depth 0 (flat structure)
- HTML content uses `<p>`, `<ul>`, `<li>` tags; use `<p>&nbsp;</p>` for spacing
- Each placeholder needs a unique 22-char uuid-base64url ID
- Preserve `[placeholder text]` in `custom-label` AND `title` attributes
- All `[bracketed text]` must be converted to elements in final HTML
- Naming: Draft = `[Number] - [Description] - Draft`, Signed = `[Number]R - [Description] - Signed`

### Section Order

1. Header/Title Area
2. Recipient Address Block (client name/address using formulas)
3. Date Field (date placeholder)
4. Sender Address Block (firm/sender info)
5. Addressee Line
6. Introduction (opening paragraph)
7. Body Sections (main content)
8. Closing (signature blocks with staff selectors)

### Letter Structure Patterns

| Pattern | Sections | Typical Elements |
|---------|----------|-----------------|
| A: Simple | Date -> Body -> Closing/Signature | 1 date, 1-2 inputs, 1 staff |
| B: Formal | Address -> Date -> Recipient -> Body -> Closing -> Signature | 3-5 formulas, 1-2 dates, 2-4 inputs, 1 staff |
| C: Representation | Address -> Date -> Intro -> Numbered Representations -> Closing -> Signature | 3-5 formulas, 3-5 dates, 10+ inputs, 1 staff |

### Folder Placement

- Communication letters: Reporting > Communication and Management Representations
- Confirmation letters: Risk Response > Fieldwork > [Relevant Account Area]
- Planning letters: Planning & Risk Assessment > Overall Audit Strategy
- Engagement letters: Planning & Risk Assessment > Pre-Engagement Activities

### Update Mode (Editing Existing Letters)

Letter updates are single-call (no two-step needed — document already exists). Requires `area_id` from `statement-get`.

```json
{
  "id": "existingDocumentId22ch",
  "type": "letter",
  "documentMap": [{
    "id": "existingAreaId22chars",
    "type": "area",
    "title": "Letter Title",
    "sections": [
      {"id": "existingSectionId22ch", "content": "<p>Updated HTML content</p>"},
      {"id": "sectToSoftDelete22chs", "hidden": true},
      {
        "type": "content", "title": "New Section",
        "content": "<p>New section content</p>",
        "depth": 0, "hidden": false
      }
    ]
  }]
}
```

> **Single call:** Unlike create mode, letter updates do not need the two-step pattern. The document and area already exist — just submit sections with their IDs.
