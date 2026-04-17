# Document Type Detection Reference

Weighted scoring algorithm for classifying source documents as **checklist**, **query**, or **letter**. Use this when the quick decision tree (markers, headers, filename) is inconclusive.

---

## Quick Decision Tree (Try First)

```
START
  |
  +-> [D0]-[D4] depth markers with [R], [C]?        -> CHECKLIST
  +-> Question sets with response columns?           -> QUERY
  +-> Letter format (To/From/Date/Re, salutation)?   -> LETTER
  +-> Procedural language (Verify/Confirm/Review)?    -> CHECKLIST
  +-> Request language (Please provide/Attach)?       -> QUERY
  +-> Formal correspondence (Dear/Sincerely)?         -> LETTER
  +-> DEFAULT                                         -> CHECKLIST
```

If the quick decision tree gives a clear answer, use it. Only proceed to weighted scoring when the document has mixed signals or no strong markers.

---

## Weighted Scoring Algorithm

Score the document against three categories. Each matched pattern adds its weight to the category total.

### Letter Indicators (21 patterns)

| Pattern (regex, case-insensitive) | Indicator Name | Score |
|-----------------------------------|---------------|-------|
| `\bdear\s+` | salutation_found | 0.20 |
| `\bsincerely\b` | closing_sincerely | 0.15 |
| `\byours\s+(truly\|faithfully)\b` | closing_yours | 0.15 |
| `\bkind\s+regards\b` | closing_regards | 0.10 |
| `\bengagement\s+letter\b` | engagement_letter_title | 0.25 |
| `\bwe\s+(are\s+pleased\|confirm)\b` | letter_opening | 0.10 |
| `\bplease\s+sign\s+and\s+return\b` | signature_request | 0.15 |
| `\btext\s+area\s*[-–]\s*` | text_area_section | 0.10 |
| `\bin\s+connection\s+with\s+your\b` | representation_opening | 0.20 |
| `\bwe\s+make\s+the\s+following\s+representations?\b` | representation_statement | 0.25 |
| `\bto\s+the\s+best\s+of\s+our\s+knowledge\s+and\s+belief\b` | knowledge_belief | 0.20 |
| `\bwe\s+acknowledge\s+that\b` | acknowledgment_statement | 0.15 |
| `\bwe\s+have\s+(disclosed\|provided\|made\s+available)\b` | disclosure_statement | 0.15 |
| `\bwe\s+are\s+responsible\s+for\b` | responsibility_statement | 0.15 |
| `\battached\s+hereto\b` | attachment_reference | 0.10 |
| `\bexhibit\s+[a-z]\b` | exhibit_reference | 0.10 |
| `^[A-Z][A-Za-z\s,\.]+\n\[?address\]?` | addressee_block | 0.15 |
| `\battestation\s+engagement\b` | attestation_engagement | 0.20 |
| `\bcompliance\s+(with\|attestation)\b` | compliance_reference | 0.15 |
| `\bmanagement\s*('s)?\s+representation\b` | management_rep_title | 0.25 |
| `\bwritten\s+representations?\b` | written_representation | 0.15 |

**Bonus:** If >10 footnote back-references (`[[N]](#footnote-N)` pattern), add indicator `many_footnote_refs` with score 0.15.

### Query Indicators (8 patterns)

| Pattern (regex, case-insensitive) | Indicator Name | Score |
|-----------------------------------|---------------|-------|
| `\b(please\s+provide\|kindly\s+provide)\b` | client_request_language | 0.20 |
| `\binformation\s+request\b` | information_request | 0.25 |
| `\bupload\s+(the\s+)?following\b` | file_upload_request | 0.20 |
| `\bprovide\s+(a\s+)?copy\b` | document_request | 0.15 |
| `\bquestion(s)?\s*:` | question_format | 0.15 |
| `\bclient\s+response\b` | client_response | 0.20 |
| `\bsupporting\s+documentation\b` | supporting_docs | 0.15 |
| `\bplease\s+(describe\|explain\|list)\b` | query_verbs | 0.15 |

### Checklist Indicators (13 patterns)

| Pattern (regex, case-insensitive) | Indicator Name | Score |
|-----------------------------------|---------------|-------|
| `\bprocedure\s*(number\|#)?\b` | procedure_column | 0.20 |
| `\byes\s*/\s*no\s*/\s*(n/?a\|not\s+applicable)\b` | yes_no_response | 0.25 |
| `^\s*isa\s+\d{3}\s*$` (multiline) | isa_column_header | 0.15 |
| `\bresponse\s*(type\|option)?\b` | response_column | 0.10 |
| `\bstep\s*\d+` | step_numbering | 0.15 |
| `\btask\s*\d+` | task_numbering | 0.10 |
| `\bwork\s*paper\s*ref` | workpaper_reference | 0.15 |
| `\bprepared\s*by.*reviewed\s*by` | audit_signoff | 0.20 |
| `\bassertions?\s*:?\s*(existence\|completeness\|accuracy\|valuation\|rights\|obligations\|presentation)` | audit_assertions | 0.20 |
| `\b(complete\|completed\|done)\s*[checkbox symbols]` | checkbox_response | 0.20 |
| `\bconclusion\s*(and\|&)?\s*sign-?off` | conclusion_signoff | 0.20 |
| `\boverall\s+conclusion` | overall_conclusion | 0.15 |
| `\bcontrol\s+(testing\|evaluation\|deficienc)` | control_testing | 0.15 |

---

## Structural Analysis (Additional Signals)

Count these structural features and add bonus scores:

| Condition | Indicator | Category | Bonus |
|-----------|-----------|----------|-------|
| Numbered items (`^\s*\d{1,3}\.\s+`) > 20 AND lettered items (`^\s*[a-z]\.\s+`) > 10 | many_numbered_lettered_items | Checklist | +0.20 |
| Prose paragraphs (lines >100 chars, not tables/headers/lists) > 10 AND numbered items < prose paragraphs | prose_heavy | Letter | +0.15 |

---

## Scoring Algorithm

1. **Sum scores** for each category (letter, checklist, query)
2. **Normalize** each category: `category_confidence = category_score / total_score`
3. **Ambiguity check**: Sort raw scores descending. If `second_highest / highest > 0.7`, classify as **ambiguous** — flag for manual review with the message: `"Mixed signals: letter={L:.2f}, checklist={C:.2f}, query={Q:.2f}"`
4. **Confidence threshold**: The winning category's normalized confidence must be >= **0.70** to assign a type. Below that, classify as **unknown**.
5. **Confidence cap**: Never report confidence above **0.95** (even if normalized score is higher).

### Decision Summary

```
total = letter_score + checklist_score + query_score

if total == 0:
    type = "unknown", confidence = 0.0

sorted_scores = [highest, second, lowest]
if second / highest > 0.7:
    type = "ambiguous", requires_manual_review = true

best_type = category with highest raw score
best_confidence = best_score / total
if best_confidence >= 0.70:
    type = best_type, confidence = min(best_confidence, 0.95)
else:
    type = "unknown"
```

---

## Usage Notes

- Run the quick decision tree first. Only use weighted scoring for ambiguous cases.
- When scoring, scan the full document text (case-insensitive) against all patterns.
- Report the matched indicators alongside the result for transparency.
- If the result is "ambiguous" or "unknown", default to **checklist** per the autonomous execution mandate and log the decision.
