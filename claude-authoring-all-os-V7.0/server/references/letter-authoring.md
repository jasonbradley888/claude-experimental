# Letter Authoring Reference

Single source of truth for letter payload structure, dynamic element detection, and two-step creation process.

**Validated 2026-01-29:** Three test letter patterns (Simple, Formal, Representation) successfully authored with dynamic elements.

---

## Letter Structure

Letters in Caseware Cloud use `statement-save` with `type: "letter"`. Structure:

1. **Document Map** — Contains one or more "areas" that organize the letter content
2. **Sections** — Content blocks within each area, all at depth 0 (flat structure)

---

## Section Types and Order

| Type | Purpose |
|------|---------|
| `area` | Main container for letter content (typically one per letter) |
| `content` | Text content section (the only section type for letters) |

**Recommended Section Order:**
1. Header/Title Area — Empty text areas for spacing
2. Recipient Address Block — Client name and address using formulas
3. Date Field — Date placeholder for letter date
4. Sender Address Block — Firm/sender address information
5. Addressee Line — "To" with input placeholder
6. Introduction — Opening paragraph with engagement context
7. Body Sections — Main content organized by topic
8. Closing — "Yours truly" and signature blocks with placeholders

---

## TWO-STEP Creation Process (CRITICAL)

For **NEW letters**, the API ignores sections on initial creation. You MUST use two calls:

### Step 1: Create the Letter

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

**Capture from response:**
- `response.id` → document ID
- `response.documentMap[0].id` → area ID

### Step 2: Add Sections (REQUIRED for content to appear)

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

**For EXISTING letters (updates):** Include the area `id` and sections save correctly in a single call.

### Common Errors

- Submitting `sections: []` (empty array) → **Blank letter** — API accepts but no content appears
- Putting sections at top level → **Wrong** — sections MUST be nested inside `documentMap[].sections`

---

## Dynamic Element Detection

Letters MUST use dynamic elements for entity data, dates, user inputs, and signatures. Detect content patterns and convert to appropriate HTML elements.

### Element Types

| Element Type | Purpose | HTML Attribute |
|--------------|---------|----------------|
| **Formula** | Pull engagement/entity data | `formula="..."` |
| **Date Placeholder** | User-selectable date | `type="date"` |
| **Input Placeholder** | User-editable text | `type="input-area"` |
| **Staff Selector** | Staff picker for signatures | `type="staff"` |

### Detection Rules (Keyword → Element Type)

| Content Pattern | Element Type | Formula/Config |
|-----------------|--------------|----------------|
| Entity Name, Company Name, Client Name | Formula | `engprop("name")` |
| Year End, Period End, Balance Sheet Date | Formula | `engprop("yearend", 0, "longDate")` |
| Firm Name, Auditor Firm | Formula | `collaborate("firmName")` |
| Legal Name | Formula | `collaborate("legalName")` |
| Address, Street, City, Province, Country, Postal Code | Formula | `collaborate("clientAddressId", "field")` |
| `[Date]`, `[Select Date]`, `[Letter Date]` | Date Placeholder | `type="date"` |
| `[Enter...]`, `[Insert...]`, `[Describe...]` | Input Placeholder | `type="input-area"` |
| Signature, Signed by, Authorized by, `[Select Staff]` | Staff Selector | `type="staff"` |
| Any other `[bracketed text]` | Input Placeholder (FALLBACK) | `type="input-area"` |

---

## Formula Reference Library

### Engagement Properties (`engprop`)

| Formula | Returns |
|---------|---------|
| `engprop("name")` | Entity/engagement name |
| `engprop("yearend", 0, "longDate")` | Year end date (formatted, e.g., "December 31, 2025") |
| `engprop("yearend", 0, "shortDate")` | Year end date (short, e.g., "12/31/2025") |

### Collaborate Functions

| Formula | Returns |
|---------|---------|
| `collaborate("firmName")` | Audit firm name |
| `collaborate("legalName")` | Client legal name |
| `collaborate("clientAddressId", "address1")` | Address line 1 |
| `collaborate("clientAddressId", "address2")` | Address line 2 |
| `collaborate("clientAddressId", "address3")` | Address line 3 |
| `collaborate("clientAddressId", "city")` | City |
| `collaborate("clientAddressId", "province")` | State/Province |
| `collaborate("clientAddressId", "country")` | Country |
| `collaborate("clientAddressId", "postalCode")` | Postal/ZIP code |

### Other Formulas

| Formula | Purpose |
|---------|---------|
| `wording("@glossaryId")` | Dynamic glossary term |
| `sentencecase(wording("@glossaryId"))` | Glossary term with sentence case |
| `procedureAnswer(checklistId.procedureId)=answerId → {(en = "Option A")}\|⊤ → {(en = "Option B")}` | Text varies based on checklist answer |

**LLM Discretion:** Other formulas may exist. If content suggests dynamic data not listed, apply best judgment following the syntax pattern.

---

## HTML Templates

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

---

## Letter Content Analysis Phase

Before authoring, analyze and generate element tree:

```xml
<letter_analysis>
  <pattern>Pattern B: Formal Letter</pattern>
  <sections>
    <section title="Entity Address">
      <element type="formula" target="engprop('name')">Entity name reference</element>
    </section>
    <section title="Date">
      <element type="date" original="[Letter Date]">Date placeholder</element>
    </section>
  </sections>
  <element_counts>
    <formulas>5</formulas>
    <date_placeholders>2</date_placeholders>
    <input_placeholders>3</input_placeholders>
    <staff_selectors>1</staff_selectors>
  </element_counts>
</letter_analysis>
```

### Letter Structure Patterns

| Pattern | Sections | Typical Elements |
|---------|----------|-----------------|
| A: Simple | Date → Body → Closing/Signature | 1 date, 1-2 inputs, 1 staff |
| B: Formal | Address → Date → Recipient → Salutation → Body → Closing → Signature | 3-5 formulas, 1-2 dates, 2-4 inputs, 1 staff |
| C: Representation | Address → Date → Introduction → Numbered Representations → Closing → Signature | 3-5 formulas, 3-5 dates, 10+ inputs, 1 staff |

---

## Mandatory Requirements

1. **Unique IDs:** Each placeholder needs a unique 22-char uuid-base64url ID
2. **Preserve Original Text:** ALWAYS preserve `[placeholder text]` in `custom-label` AND `title` attributes (non-negotiable)
3. **No Raw Brackets:** All `[bracketed text]` must be converted to elements in final HTML

---

## Pre-Submission Checklist

Before calling `statement-save`:
- [ ] `type: "letter"` is set
- [ ] `documentMap` is an array with at least one area object
- [ ] Each area has `sections` array with content objects (NOT empty `[]` on Step 2)
- [ ] Each section has `type: "content"`, `title`, `content`, and `depth: 0`
- [ ] HTML content uses `<p>` tags and escapes special characters (`&lt;`, `&gt;`, `&quot;`)
- [ ] `documentInfo` present for new letters (folder, name, number)
- [ ] All `[placeholder text]` converted to element type
- [ ] Original text preserved in `custom-label` and `title` attributes
- [ ] Entity references use `engprop()` or `collaborate()` formulas
- [ ] Date fields use `type="date"` placeholder with unique ID
- [ ] Signature has staff selector and firm name formula
- [ ] All placeholder IDs are unique 22-char format
- [ ] No raw `[bracketed text]` in final HTML

---

## Authoring Guidelines

1. **Structure**: All sections at depth 0 (flat)
2. **HTML Content**: Use `<p>`, `<ul>`, `<li>` tags
3. **Spacing**: Use `<p>&nbsp;</p>` for blank lines
4. **Placeholders**: Descriptive text in square brackets `[Like This]`
5. **Formulas**: Use engagement property formulas for dynamic data
6. **Conditional Logic**: Use procedureAnswer formulas for variable text
7. **Signature Blocks**: Include signature lines with underscores and placeholder fields

---

## Naming Conventions

- Draft letters: `[Number] - [Description] - Draft`
- Signed letters: `[Number]R - [Description] - Signed`
- Related queries: `[Number]Q - [Description] - Query`

## Common Letter Types

| Type | Example Number | Description |
|------|----------------|-------------|
| Management Representation | E-600 | Written representations from management |
| Bank Confirmation | D-110 | Confirmation requests to banks |
| AR Confirmation | D-210 | Trade receivables confirmation |
| Audit Planning | A-800 | Communications to those charged with governance |
| Engagement Letter | A-130 | Terms of engagement |
| Specialist Letter | A-700 | Letters to external audit specialists |
| Management Letter | E-610 | Post-audit management recommendations |
| Deficiency Communication | E-620 | Internal control deficiency communications |

## Folder Placement

Use `document-manager` to identify appropriate folder:
- Communication letters: Reporting > Communication and Management Representations
- Confirmation letters: Risk Response > Fieldwork > [Relevant Account Area]
- Planning letters: Planning & Risk Assessment > Overall Audit Strategy
- Engagement letters: Planning & Risk Assessment > Pre-Engagement Activities
