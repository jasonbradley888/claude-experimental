# Query Authoring Reference

Single source of truth for query payload structure and authoring rules.

---

## Query Structure

- **depth 0:** Question sets (section headers) — use `type: "questionSet"`
- **depth 1:** Questions within each question set — use `type: "question"`

---

## General Rules

- Set `id: null` for new queries and new questions
- Each question has two response columns:
  - Column 1: `type: "text"` with placeholder
  - Column 2: `type: "files"` with `fileDestination: {}`
- Include `hidden: false` and `hideCondition: null` on all question sets and questions
- Include client-facing instructions
- Use related document number with "Q" suffix
- Place queries in the same folder as related documents
- The `reasoning` object is NOT required for authoring agent submissions

---

## Question Set Structure (depth 0)

```json
{
  "id": null,
  "depth": 0,
  "type": "questionSet",
  "title": "Section Title",
  "hidden": false,
  "hideCondition": null
}
```

---

## Question Structure (depth 1)

```json
{
  "id": null,
  "depth": 1,
  "type": "question",
  "title": "Question Title",
  "text": "<p>Question text in HTML format.</p>",
  "rows": [{
    "columns": [
      {"type": "text", "placeholder": "Enter response here"},
      {"type": "files", "placeholder": "", "fileDestination": {}}
    ]
  }],
  "hidden": false,
  "hideCondition": null
}
```

---

## Query Save Parameters

When using `query-save`, always include:
- `id`: `null` for new queries; existing ID when updating
- `documentInfo`: folder ID, name, and number (new queries only; omit when updating)
- `instructions`: Client-facing instructions explaining the query purpose
- `purpose`: Internal description
- `purposeSummary`: Short title for the suggestion set
- `questions`: Array of question sets and questions

---

## Complete Payload Example

```json
{
  "id": null,
  "documentInfo": {
    "folder": "abc123def456ghi789",
    "name": "Revenue Process Information Request",
    "number": "B-100Q"
  },
  "instructions": "Please provide the following information to assist with our audit procedures. For each item, enter your response in the text field and upload any supporting documents.",
  "purpose": "Gather client information for revenue cycle audit procedures",
  "purposeSummary": "Revenue Process Query",
  "questions": [
    {
      "id": null,
      "depth": 0,
      "type": "questionSet",
      "title": "Process Overview",
      "hidden": false,
      "hideCondition": null
    },
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
    },
    {
      "id": null,
      "depth": 0,
      "type": "questionSet",
      "title": "Supporting Documentation",
      "hidden": false,
      "hideCondition": null
    },
    {
      "id": null,
      "depth": 1,
      "type": "question",
      "title": "Additional Information",
      "text": "<p>Please provide any additional information or documents relevant to the revenue process.</p>",
      "rows": [{
        "columns": [
          {"type": "text", "placeholder": "Enter additional information"},
          {"type": "files", "placeholder": "", "fileDestination": {}}
        ]
      }],
      "hidden": false,
      "hideCondition": null
    }
  ]
}
```

---

## Minimal Template

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

---

## Folder Placement

Use `document-manager` to identify the appropriate folder based on where related documents are located.
