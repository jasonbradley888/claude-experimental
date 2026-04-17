# Document Type Identification

Identify the document type to route to the correct authoring phase.

## Before Starting

Load references as needed:
- `load_reference('hierarchy-rules')` — marker definitions
- `load_reference('document-type-detection')` — weighted scoring algorithm

## Decision Tree

```
START
  |
  +--> [D0]-[D4] depth markers with [R], [C]?  -> CHECKLIST
  +--> Question sets with response columns?     -> QUERY
  +--> Letter format (To/From/Date/Re)?         -> LETTER
  +--> Financial statement structure?            -> FINANCIAL STATEMENT (not implemented)
  +--> Procedural language (Verify/Confirm)?     -> CHECKLIST
  +--> Request language (Please provide/Attach)? -> QUERY
  +--> Formal correspondence (Dear/Sincerely)?   -> LETTER
  +--> DEFAULT                                   -> CHECKLIST
```

### Detection Layers (applied in order)

| Layer | Signal | Example |
|-------|--------|---------|
| 1. Structure markers | `[D0]`-`[D4]`, `[R]`, `[C]`, `[G]` | Checklist |
| 1. Structure markers | `[Question Set]`, `[Question]` | Query |
| 1. Structure markers | Date/To/From/Re header | Letter |
| 2. Content patterns | "Verify", "Confirm", "Review", "Assess" | Checklist |
| 2. Content patterns | "Please provide", "Attach documentation" | Query |
| 2. Content patterns | Formal salutation, closing, signature | Letter |
| 2. Content patterns | Balance sheet, income statement | Financial Statement |
| 3. Filename | `*checklist*`, `*procedure*`, `*audit*` | Checklist |
| 3. Filename | `*query*`, `*request*`, `*pbc*` | Query |
| 3. Filename | `*letter*`, `*correspondence*` | Letter |

---

## Output Format

| File | Detected Type | Confidence | Routing |
|------|---------------|------------|---------|
| `file.md` | Checklist | High/Medium/Low | -> `load_reference('checklist-authoring')` |
| `file.md` | Query | High/Medium/Low | -> `load_reference('query-authoring')` |
| `file.md` | Letter | High/Medium/Low | -> `load_reference('letter-authoring')` |
| `file.md` | Financial Statement | High/Medium/Low | -> Not implemented |

**Confidence:** High = markers + content + filename align | Medium = partial alignment | Low = ambiguous, defaulting

## Detailed Scoring

If the quick decision tree above is inconclusive, apply the weighted scoring algorithm from `load_reference('document-type-detection')`. This scores the document against letter, query, and checklist indicator patterns with specific weights, then normalizes and checks for ambiguity.

---

## Routing

After detection, load the appropriate reference:

| Type | Reference Prompt |
|------|-----------------|
| Checklist | `load_reference('checklist-authoring')` |
| Query | `load_reference('query-authoring')` |
| Letter | `load_reference('letter-authoring')` |
| Financial Statement | Notify user — not yet supported |
