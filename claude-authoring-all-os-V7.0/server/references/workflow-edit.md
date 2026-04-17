# Workflow: Edit Existing Documents

Edit existing checklists, queries, and letters in Caseware Cloud. Retrieves the current document, identifies changes, builds a sparse update payload, and submits.

---

## When to Use

- User asks to modify, update, or edit an existing document
- User wants to add, remove, or change procedures/questions/sections
- User wants to fix errors in a previously authored document

---

## Steps

### 1. Locate the Document

```
Call document-manager with includeHidden: true to find the document by name or number.
```

Capture the document ID from the response.

### 2. Retrieve Current Content

| Document Type | Tool | What You Get |
|--------------|------|-------------|
| Checklist | `checklist-get` | All procedures with IDs, response types, depths |
| Query | `query-get` | All questions/questionSets with IDs |
| Letter | `statement-get` | All sections with IDs, area ID, document map |

### 3. Identify Changes

Compare the current content against the requested changes. Categorize each item:

| Category | Has `id`? | Has `_delete`? | What Happens |
|----------|-----------|---------------|-------------|
| **Modify** | Yes | No | Sparse update — only changed fields sent |
| **Add** | No | No | Full item — all fields required (same as create) |
| **Delete** | Yes | Yes | Soft-delete — sets `hidden: true` |
| **Unchanged** | — | — | Omit from outline entirely |

### 4. Build Update Outline

Build the outline with `mode: "update"` and the document ID.

**Checklist update outline:**
```json
{
  "document_type": "checklist",
  "mode": "update",
  "document_id": "captured-doc-id-22chars",
  "items": [
    {"id": "existingProcId", "text": "Updated procedure text"},
    {"id": "procToDelete123456789", "_delete": true},
    {"depth": 2, "type": "procedure", "text": "Brand new procedure", "response": "choice"}
  ]
}
```

**Query update outline:**
```json
{
  "document_type": "query",
  "mode": "update",
  "document_id": "captured-doc-id-22chars",
  "items": [
    {"id": "existingQuestionId", "title": "Updated question title"},
    {"depth": 1, "type": "question", "text": "New question", "title": "New Q"}
  ]
}
```

**Letter update outline:**
```json
{
  "document_type": "letter",
  "mode": "update",
  "document_id": "captured-doc-id-22chars",
  "area_id": "captured-area-id-22ch",
  "area_title": "Letter Title",
  "sections": [
    {"id": "existingSectionId", "content": "Updated content with [Entity Name]"},
    {"title": "New Section", "content": "New content"}
  ]
}
```

### 5. Build Payload

```
Call build_payload(outline) — the tool detects mode: "update" and produces a sparse payload.
```

### 6. Submit

| Document Type | Submit Via |
|--------------|-----------|
| Checklist | `checklist-save` |
| Query | `query-save` |
| Letter | `statement-save` (single call — no two-step needed for updates) |

### 7. Verify

Call the corresponding `-get` tool to verify the changes were applied correctly.

---

## Update Rules

| Rule | Details |
|------|---------|
| Items WITH `id` | Sparse update — only send `id` + changed fields. API preserves unchanged fields. |
| Items WITHOUT `id` | New item — all fields required (depth, type, text, response for procedures). |
| Items with `_delete: true` | Must have `id`. Sets `hidden: true` (soft-delete — API doesn't support hard deletes). |
| No `documentInfo` | Updates never include `documentInfo` — it's only for new documents. |
| No chunking | Updates are submitted as a single payload (typically small). |
| No `includeConclusion` | Conclusion already exists on the document. |
| Letter updates | Single call (no two-step). Requires `area_id` from `statement-get`. |
| Optional top-level fields | `purpose`, `purpose_summary`, `guidance` are included only if provided. |

---

## Example: Edit a Checklist

```
User: "Update the Revenue Testing Checklist — change procedure 3 to a text response and add a new procedure about related party transactions."

1. document-manager → find "Revenue Testing Checklist" → capture docId
2. checklist-get(docId) → retrieve all procedures with IDs
3. Identify: procedure 3 needs response change, plus one new procedure
4. Build outline:
   {
     "document_type": "checklist",
     "mode": "update",
     "document_id": "docId",
     "items": [
       {"id": "proc3Id", "response": "text"},
       {"depth": 2, "type": "procedure", "text": "Are there related party transactions?", "response": "choice"}
     ]
   }
5. build_payload(outline) → sparse update payload
6. checklist-save(payload) → submit
7. checklist-get(docId) → verify changes
```
