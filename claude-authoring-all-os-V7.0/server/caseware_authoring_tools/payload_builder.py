"""Payload builder — converts lightweight procedure outlines to validated Caseware Cloud payloads.

The LLM outputs a simple procedure outline (depth, type, text, response type).
This module mechanically expands it to the full Caseware payload with all
boilerplate, validates it, and chunks it.

Public API:
    build_payload(outline) — Route to checklist/query/letter builder (create or update).
    build_checklist(outline) — Returns chunked payloads with validation.
    build_query(outline) — Returns query payload with validation.
    build_letter(outline) — Returns two-step letter payloads with validation.
    build_checklist_update(outline) — Returns sparse update payload for existing checklist.
    build_query_update(outline) — Returns sparse update payload for existing query.
    build_letter_update(outline) — Returns single-call update payload for existing letter.
"""

import base64
import html as html_mod
import re
import uuid
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_DEPTH = 4
MAX_PROCEDURES_PER_CHUNK = 20
CHUNKING_THRESHOLD = 50
INLINE_CHOICES_MAX_COUNT = 3
INLINE_CHOICES_MAX_TEXT_LEN = 20

VALID_TYPES_AT_DEPTH: dict[int, set[str]] = {
    0: {"group", "conclusion"},
    1: {"group", "heading", "procedure"},
    2: {"heading", "procedure"},
    3: {"heading", "procedure"},
    4: {"procedure"},
}

VALID_RESPONSE_KINDS = {"choice", "text", "number", "date"}


# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------


def _generate_placeholder_id() -> str:
    """Generate a 22-char uuid-base64url ID for letter placeholders."""
    raw = uuid.uuid4().bytes
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Numbering stripping
# ---------------------------------------------------------------------------

# Matches leading numbering/bullet patterns followed by whitespace:
#   1. | 1.1. | 1.1.1 | a. | B. | ii. | 1) | a) | ii) | (1) | (a) | (iii) | • | – | * | -
# NOTE: Bare single letter without dot (e.g. "A " or "I ") is NOT matched —
# too likely to be an English article or pronoun. Use "a." or "(a)" or "a)" forms.
_NUMBERING_RE = re.compile(
    r"^\s*(?:"
    r"\d+(?:\.\d+)*\.?\s+"          # 1. | 1.1. | 1.1.1
    r"|[a-zA-Z]\.\s+"               # a. | B. (dot required)
    r"|[ivxIVX]+\.\s+"              # ii. | IV.
    r"|\d+\)\s+"                    # 1) | 12)
    r"|[a-zA-Z]\)\s+"               # a) | B)
    r"|[ivxIVX]+\)\s+"              # i) | ii)
    r"|\(\d+\)\s+"                  # (1)
    r"|\([a-zA-Z]\)\s+"            # (a)
    r"|\([ivxIVX]+\)\s+"           # (iii)
    r"|[•–\u2022\u2013\u2014]\s+"  # • | – | —
    r"|[*\-]\s+"                    # * | -
    r")"
)


def _strip_numbering(text: str) -> tuple[str, bool]:
    """Strip leading numbering prefixes from procedure text.

    Returns (cleaned_text, was_stripped). Does NOT strip if the result
    would be empty or if the text doesn't match a numbering pattern.
    """
    stripped = _NUMBERING_RE.sub("", text, count=1)
    if stripped and stripped != text:
        return stripped, True
    return text, False


# ---------------------------------------------------------------------------
# Text wrapping (left-align)
# ---------------------------------------------------------------------------


def _wrap_procedure_text(text: str) -> str:
    """Wrap procedure text in a left-aligned HTML paragraph.

    Caseware Cloud renders procedure text as HTML. Wrapping in
    <p style="text-align: left;"> ensures consistent left alignment.
    If the text already starts with an HTML tag, it's returned as-is.
    """
    if not text or text.strip().startswith("<"):
        return text
    return f'<p style="text-align: left;">{text}</p>'


# ---------------------------------------------------------------------------
# ID validation
# ---------------------------------------------------------------------------

_ID_RE = re.compile(r'^[A-Za-z0-9_-]{22}$')


def _validate_id_format(id_str: str) -> bool:
    """Validate 22-char uuid-base64url ID."""
    return bool(_ID_RE.match(id_str))


def _strip_nested_ids(procedure: dict) -> dict:
    """Remove nested ``id`` fields from a procedure for new-document payloads.

    The API auto-generates IDs for procedures, rows, columns, and choices.
    Stale or invented IDs cause silent errors, so strip them on create.
    Top-level ``id`` is left untouched (caller manages it).
    """
    procedure.pop("id", None)
    for row in procedure.get("rows", []):
        row.pop("id", None)
        for col in row.get("columns", []):
            col.pop("id", None)
            for choice in col.get("choices", []):
                choice.pop("id", None)
    return procedure


def _sanitize_procedure(procedure: dict) -> dict:
    """Apply safety-net sanitization to a built procedure before submission.

    Guards against two known MCP rejection patterns:
    1. Group-type nodes with a ``rows`` array — MCP rejects them.
    2. Choice objects containing an ``id`` field — causes UnableToCreateSubObject.
    """
    # Groups must never have rows
    if procedure.get("type") == "group":
        procedure.pop("rows", None)

    # Strip id from all choice objects
    for row in procedure.get("rows", []):
        for col in row.get("columns", []):
            for choice in col.get("choices", []):
                choice.pop("id", None)

    return procedure


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def _ensure_not_applicable(choices: list[str]) -> list[str]:
    """Append 'Not Applicable' if not already present."""
    normalised = [c.lower().strip() for c in choices]
    if "not applicable" not in normalised and "n/a" not in normalised:
        choices = choices + ["Not Applicable"]
    return choices


def _calculate_inline_choices(choices: list[str]) -> bool:
    """Return True if choices should render as inline radio buttons."""
    if len(choices) > INLINE_CHOICES_MAX_COUNT:
        return False
    return all(len(c) <= INLINE_CHOICES_MAX_TEXT_LEN for c in choices)


def _parse_response(response_str: str | None) -> dict | None:
    """Parse a response string notation into full column JSON.

    Formats:
        "choice:Yes|No|Not Applicable"              → picklist column (pipe-delimited, preferred)
        "choice:Completed - no exceptions|Completed with exceptions|Not Applicable"
        "choice:Yes,No,Not Applicable"              → picklist column (comma-delimited, legacy)
        "text"                                      → free text column
        "text:Describe the process"                 → free text with placeholder
        "number"                                    → numeric column
        "date"                                      → date column
        None                                        → no response (group/heading)

    Choice delimiter: pipe ``|`` is the preferred delimiter because it allows
    choices to contain commas (e.g. "Completed, no exceptions"). Comma ``,``
    is still accepted for backward compatibility when no pipe is present.

    Returns:
        A dict with "rows", "includeNote", and optionally "notePlaceholder",
        or None if no response.
    """
    if response_str is None:
        return None

    response_str = response_str.strip()
    if not response_str:
        return None

    # Split kind from value on first colon
    if ":" in response_str:
        kind, _, value = response_str.partition(":")
        kind = kind.strip().lower()
        value = value.strip()
    else:
        kind = response_str.strip().lower()
        value = ""

    # --- choice ---
    if kind == "choice":
        if not value:
            choices = ["Yes", "No", "Not Applicable"]
        else:
            # Pipe | is the preferred delimiter — allows commas inside choice text.
            # Fall back to comma splitting for legacy outlines that predate pipe support.
            delimiter = "|" if "|" in value else ","
            choices = [c.strip() for c in value.split(delimiter) if c.strip()]
            choices = _ensure_not_applicable(choices)

        inline = _calculate_inline_choices(choices)
        return {
            "rows": [{
                "columns": [{
                    "type": "choice",
                    "placeholder": "",
                    "includeOtherChoice": False,
                    "inlineChoices": inline,
                    "choices": [{"text": c} for c in choices],
                }]
            }],
            "includeNote": True,
            "notePlaceholder": "Response and Comments",
        }

    # --- text ---
    if kind == "text":
        placeholder = value if value else "Enter response here"
        return {
            "rows": [{
                "columns": [{
                    "type": "text",
                    "placeholder": placeholder,
                }]
            }],
            "includeNote": False,
        }

    # --- number ---
    if kind == "number":
        return {
            "rows": [{
                "columns": [{
                    "type": "number",
                }]
            }],
            "includeNote": True,
            "notePlaceholder": "Response and Comments",
        }

    # --- date ---
    if kind == "date":
        return {
            "rows": [{
                "columns": [{
                    "type": "date",
                }]
            }],
            "includeNote": True,
            "notePlaceholder": "Response and Comments",
        }

    # --- unrecognised → default to text with original as placeholder ---
    return {
        "rows": [{
            "columns": [{
                "type": "text",
                "placeholder": response_str,
            }]
        }],
        "includeNote": False,
        "_warning": f"Unrecognised response type '{response_str}', defaulting to text",
    }


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_depth_sequence(items: list[dict]) -> list[str]:
    """Validate depth sequence: no jumps >1, max depth 4.

    Returns list of error strings (empty = valid).
    """
    errors: list[str] = []
    prev_depth = -1

    for i, item in enumerate(items):
        depth = item.get("depth", 0)

        if depth > MAX_DEPTH:
            errors.append(
                f"INVALID_DEPTH: Item {i} '{item.get('text', '')[:40]}' has depth {depth} "
                f"(max is {MAX_DEPTH})"
            )

        if depth < 0:
            errors.append(f"INVALID_DEPTH: Item {i} has negative depth {depth}")

        if prev_depth >= 0 and depth > prev_depth + 1:
            errors.append(
                f"INVALID_DEPTH: Item {i} '{item.get('text', '')[:40]}' jumps from "
                f"depth {prev_depth} to {depth} (max increment is 1)"
            )

        prev_depth = depth

    return errors


def _validate_types_at_depth(items: list[dict]) -> list[str]:
    """Validate that each item's type is valid for its depth.

    Returns list of error strings (empty = valid).
    """
    errors: list[str] = []

    for i, item in enumerate(items):
        depth = item.get("depth", 0)
        item_type = item.get("type", "")

        if depth > MAX_DEPTH:
            continue  # Already caught by depth validation

        valid = VALID_TYPES_AT_DEPTH.get(depth, set())
        if item_type not in valid:
            errors.append(
                f"INVALID_TYPE_AT_DEPTH: Item {i} '{item.get('text', '')[:40]}' has "
                f"type '{item_type}' at depth {depth}. Valid types: {sorted(valid)}"
            )

        # Procedures must have a response (enforced during build, not here)
        # Groups should NOT have responses
        if item_type in ("group", "heading") and item.get("response"):
            errors.append(
                f"Item {i} '{item.get('text', '')[:40]}' is type '{item_type}' "
                f"but has a response — only procedures and conclusions have responses"
            )

    return errors


def _validate_procedures_have_responses(items: list[dict]) -> list[str]:
    """Validate that all procedure-type items have a response."""
    errors: list[str] = []
    for i, item in enumerate(items):
        if item.get("type") == "procedure" and not item.get("response"):
            errors.append(
                f"MISSING_RESPONSE_TYPE: Item {i} '{item.get('text', '')[:40]}' "
                f"is a procedure but has no response"
            )
    return errors


def _validate_outline(items: list[dict]) -> dict:
    """Run all validations on outline items.

    Returns:
        {"valid": bool, "errors": [...], "warnings": [...]}
    """
    errors: list[str] = []
    warnings: list[str] = []

    errors.extend(_validate_depth_sequence(items))
    errors.extend(_validate_types_at_depth(items))
    errors.extend(_validate_procedures_have_responses(items))

    # Check conclusion items — they are optional in the outline since the API
    # generates the real conclusion via includeConclusion: true.  Any explicit
    # conclusion items will be stripped from the procedures array during build.
    conclusions = [it for it in items if it.get("type") == "conclusion"]
    if len(conclusions) > 0:
        warnings.append(
            f"Outline contains {len(conclusions)} conclusion item(s) — REMOVED. "
            f"Do NOT re-add them. The API generates the conclusion automatically "
            f"via includeConclusion: true. Explicit conclusions render as groups, not conclusions."
        )

    # Warn about items with leading numbering (will be auto-stripped during build)
    for i, item in enumerate(items):
        if item.get("type") in ("procedure", "heading", "conclusion"):
            _, was_stripped = _strip_numbering(item.get("text", ""))
            if was_stripped:
                warnings.append(
                    f"Item {i} '{item.get('text', '')[:40]}' has leading numbering "
                    f"that will be auto-stripped"
                )

    # Detect duplicate procedure texts (case-insensitive).
    # Legitimate duplicates under different groups are possible, so warn only.
    proc_texts: dict[str, list[int]] = {}
    for i, item in enumerate(items):
        if item.get("type") in ("procedure", "conclusion"):
            key = item.get("text", "").strip().lower()
            if key:
                proc_texts.setdefault(key, []).append(i)
    duplicates = {t: idxs for t, idxs in proc_texts.items() if len(idxs) > 1}
    if duplicates:
        dup_details = "; ".join(
            f"'{t[:50]}' at items {idxs}" for t, idxs in duplicates.items()
        )
        warnings.append(f"DUPLICATE_PROCEDURES: {dup_details}")

    # Detect empty branches — groups/headings with no procedure descendant
    # produce empty sections in Caseware Cloud.
    for i, item in enumerate(items):
        if item.get("type") in ("group", "heading"):
            container_depth = item.get("depth", 0)
            has_procedure_child = False
            for j in range(i + 1, len(items)):
                child = items[j]
                child_depth = child.get("depth", 0)
                if child_depth <= container_depth:
                    break  # left this container's subtree
                if child.get("type") in ("procedure", "conclusion"):
                    has_procedure_child = True
                    break
            if not has_procedure_child:
                warnings.append(
                    f"EMPTY_BRANCH: Item {i} '{item.get('type')}' "
                    f"'{item.get('text', '')[:40]}' has no procedure descendants"
                )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


def _validate_update_outline(outline: dict) -> dict:
    """Validate an update-mode outline.

    Validates:
    - document_id is present and valid 22-char ID
    - Items with 'id' have valid format
    - Items marked '_delete' have an 'id'
    - New items (no 'id') pass normal depth/type/response validation

    Returns:
        {"valid": bool, "errors": [...], "warnings": [...]}
    """
    errors: list[str] = []
    warnings: list[str] = []

    doc_id = outline.get("document_id", "")
    if not doc_id:
        errors.append("Update mode requires 'document_id'")
    elif not _validate_id_format(doc_id):
        errors.append(
            f"INVALID_ID_FORMAT: document_id '{doc_id}' is not a valid "
            f"22-char uuid-base64url ID"
        )

    items = outline.get("items", [])
    sections = outline.get("sections", [])
    all_items = items or sections

    new_items: list[dict] = []

    for i, item in enumerate(all_items):
        item_id = item.get("id")
        is_delete = item.get("_delete", False)

        if is_delete and not item_id:
            errors.append(
                f"Item {i}: '_delete' requires an 'id' field "
                f"(cannot delete an item that doesn't exist yet)"
            )
            continue

        if item_id:
            if not _validate_id_format(item_id):
                errors.append(
                    f"INVALID_ID_FORMAT: Item {i} has invalid id '{item_id}'"
                )
        else:
            # New item — collect for normal validation
            new_items.append(item)

    # Validate new items using normal checklist rules (depth/type/response)
    # Only applies to checklist items — queries and letters have different structures
    doc_type = outline.get("document_type", "").lower().strip()
    if new_items and items and doc_type == "checklist":
        new_validation = _validate_outline(new_items)
        errors.extend(new_validation["errors"])
        warnings.extend(new_validation["warnings"])

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Checklist procedure building
# ---------------------------------------------------------------------------


def _build_procedure(item: dict, include_signoffs: bool = True) -> dict:
    """Expand an outline item to a full Caseware procedure object."""
    depth = item["depth"]
    item_type = item["type"]
    text = item.get("text", "")

    # Strip leading numbering for procedures, headings, and conclusions.
    # Groups excluded — they may legitimately have numbered titles like "Section 1: Revenue".
    if item_type in ("procedure", "heading", "conclusion"):
        text, _ = _strip_numbering(text)

    # Detect dynamic elements (formulas, placeholders) in procedure/conclusion text.
    # Generic brackets are NOT converted — only known patterns (avoids false positives
    # like [ISA 315] or [Section 3.1] that are common in checklists).
    if item_type in ("procedure", "conclusion"):
        text = _detect_dynamic_elements(text, convert_generic_brackets=False)

    # Wrap procedure/conclusion text in left-aligned HTML for consistent rendering.
    # Groups and headings are structural titles — not wrapped.
    if item_type in ("procedure", "conclusion"):
        text = _wrap_procedure_text(text)

    proc: dict[str, Any] = {
        "depth": depth,
        "type": item_type,
        "text": text,
        "hidden": item.get("hidden", False),
        "hideCondition": item.get("hide_condition", None),
    }

    # Groups and headings — no response rows
    if item_type in ("group", "heading"):
        proc["includeNote"] = True
        proc["notePlaceholder"] = "Response and Comments"
        proc["includeSignOffs"] = include_signoffs
        return proc

    # Procedures and conclusions — parse response
    response_data = _parse_response(item.get("response"))

    if response_data:
        proc["rows"] = response_data["rows"]
        proc["includeNote"] = response_data["includeNote"]
        if response_data["includeNote"]:
            proc["notePlaceholder"] = response_data.get(
                "notePlaceholder", "Response and Comments"
            )
    else:
        # Conclusion without explicit response gets text response
        if item_type == "conclusion":
            proc["rows"] = [{
                "columns": [{
                    "type": "text",
                    "placeholder": "Enter overall conclusion",
                }]
            }]
            proc["includeNote"] = True
            proc["notePlaceholder"] = "Response and Comments"
        else:
            # Should not happen (validation catches this), but be safe
            proc["includeNote"] = True
            proc["notePlaceholder"] = "Response and Comments"

    proc["includeSignOffs"] = include_signoffs

    # Optional fields
    if item.get("guidance"):
        proc["guidance"] = item["guidance"]
    if item.get("authoritative_references"):
        proc["authoritativeReferences"] = [
            {"reference": ref} for ref in item["authoritative_references"][:5]
        ]
    if item.get("placeholder"):
        # Map to column placeholder if response exists
        if "rows" in proc and proc["rows"]:
            col = proc["rows"][0]["columns"][0]
            if "placeholder" in col:
                col["placeholder"] = item["placeholder"]

    # Never include summary field — API displays it as unwanted text
    proc.pop("summary", None)

    return proc


def _build_update_procedure(item: dict, include_signoffs: bool = True) -> dict:
    """Build a sparse update procedure object.

    For items WITH an 'id': only include id + changed fields.
    For items WITHOUT an 'id': delegate to _build_procedure (new item).
    For items with '_delete: true': set hidden: true (soft-delete).
    """
    item_id = item.get("id")

    # New item — no ID, full build
    if not item_id:
        return _build_procedure(item, include_signoffs)

    # Soft-delete
    if item.get("_delete", False):
        return {"id": item_id, "hidden": True}

    # Sparse update — only id + changed fields
    proc: dict[str, Any] = {"id": item_id}

    if "text" in item:
        text = item["text"]
        item_type = item.get("type", "procedure")
        if item_type in ("procedure", "heading", "conclusion"):
            text, _ = _strip_numbering(text)
        if item_type in ("procedure", "conclusion"):
            text = _detect_dynamic_elements(text, convert_generic_brackets=False)
            text = _wrap_procedure_text(text)
        proc["text"] = text

    if "depth" in item:
        proc["depth"] = item["depth"]

    if "type" in item:
        proc["type"] = item["type"]

    if "hidden" in item:
        proc["hidden"] = item["hidden"]

    if "hide_condition" in item:
        proc["hideCondition"] = item["hide_condition"]

    # Groups and headings never have response rows — skip even if outline
    # erroneously supplies a "response" field for them.
    item_type = item.get("type", "procedure")
    if "response" in item and item_type not in ("group", "heading"):
        response_data = _parse_response(item["response"])
        if response_data:
            proc["rows"] = response_data["rows"]
            proc["includeNote"] = response_data["includeNote"]
            if response_data["includeNote"]:
                proc["notePlaceholder"] = response_data.get(
                    "notePlaceholder", "Response and Comments"
                )

    if "guidance" in item:
        proc["guidance"] = item["guidance"]

    if "authoritative_references" in item:
        proc["authoritativeReferences"] = [
            {"reference": ref} for ref in item["authoritative_references"][:5]
        ]

    if "include_signoffs" in item:
        proc["includeSignOffs"] = item["include_signoffs"]

    return _sanitize_procedure(proc)


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------


def _chunk_at_groups(
    items: list[dict], max_per_chunk: int = MAX_PROCEDURES_PER_CHUNK
) -> list[list[dict]]:
    """Split items at D0 boundaries, keeping each chunk ≤ max_per_chunk.

    Rules:
    - Never split mid-group
    - A single group may exceed max_per_chunk (submitted as its own chunk)
    - Conclusion goes in the final chunk only
    """
    if not items:
        return []

    # Separate conclusion from items
    conclusion = None
    working_items = []
    for item in items:
        if item.get("type") == "conclusion":
            conclusion = item
        else:
            working_items.append(item)

    # Group items by D0 boundaries
    groups: list[list[dict]] = []
    current_group: list[dict] = []

    for item in working_items:
        if item.get("depth") == 0 and current_group:
            groups.append(current_group)
            current_group = []
        current_group.append(item)

    if current_group:
        groups.append(current_group)

    # Pack groups into chunks
    chunks: list[list[dict]] = []
    current_chunk: list[dict] = []
    current_count = 0

    for group in groups:
        group_proc_count = sum(
            1 for it in group if it.get("type") in ("procedure", "conclusion")
        )

        if current_count > 0 and current_count + group_proc_count > max_per_chunk:
            chunks.append(current_chunk)
            current_chunk = []
            current_count = 0

        current_chunk.extend(group)
        current_count += group_proc_count

    if current_chunk:
        chunks.append(current_chunk)

    # Add conclusion to the final chunk
    if conclusion and chunks:
        chunks[-1].append(conclusion)
    elif conclusion:
        chunks.append([conclusion])

    return chunks


# ---------------------------------------------------------------------------
# Checklist builder
# ---------------------------------------------------------------------------


def build_checklist(outline: dict) -> dict:
    """Build validated Caseware checklist payload(s) from an outline.

    Returns:
        {
            "payloads": [payload1, payload2, ...],  # chunked if >50 procedures
            "validation": {"valid": bool, "errors": [...], "warnings": [...]},
            "metadata": {"total_procedures": N, "chunks": N, ...}
        }
    """
    items = outline.get("items", [])

    # Apply checklist-level default response to procedures that lack one.
    # The Caseware Cloud API has no native checklist-level default, so we
    # expand it here before validation so every procedure has a response.
    default_response = outline.get("default_response")
    default_applied = 0
    if default_response:
        for item in items:
            if item.get("type") in ("procedure", "conclusion") and not item.get("response"):
                item["response"] = default_response
                default_applied += 1

    # Validate
    validation = _validate_outline(items)
    if not validation["valid"]:
        return {
            "payloads": [],
            "validation": validation,
            "metadata": {"error": "Validation failed — fix errors before submitting"},
        }

    if default_response and default_applied == 0:
        validation["warnings"].append(
            f"default_response '{default_response}' was provided but all procedures "
            f"already have explicit responses — the default was not used."
        )

    include_signoffs = outline.get("include_signoffs", True)

    # Collect warnings from response parsing
    for item in items:
        resp_data = _parse_response(item.get("response"))
        if resp_data and resp_data.get("_warning"):
            validation["warnings"].append(resp_data["_warning"])

    # Count actual procedures (not groups/headings) directly from items
    proc_count = sum(
        1 for item in items if item.get("type") in ("procedure", "conclusion")
    )

    # Content loss detection — if the caller provides an expected count from
    # the source document, hard-fail when >10% of procedures were lost during
    # outline construction.
    expected = outline.get("expected_procedure_count")
    if expected is not None and expected > 0:
        loss_pct = (expected - proc_count) / expected
        if loss_pct > 0.10:
            validation["errors"].append(
                f"CONTENT_LOSS_EXCEEDED: Expected {expected} procedures from "
                f"source document but outline contains {proc_count} "
                f"({loss_pct:.0%} loss). Fix the outline before submitting."
            )
            validation["valid"] = False
            return {
                "payloads": [],
                "validation": validation,
                "metadata": {"error": "Content loss exceeded 10% threshold"},
            }

    # Determine chunk size (use 15 for long guidance text)
    has_long_guidance = any(
        len(item.get("guidance", "")) > 500 for item in items
    )
    max_per_chunk = 15 if has_long_guidance else MAX_PROCEDURES_PER_CHUNK

    # Chunk if needed
    if proc_count > CHUNKING_THRESHOLD:
        chunks = _chunk_at_groups(items, max_per_chunk)
    else:
        chunks = [items]

    # Build payloads
    payloads: list[dict] = []
    base_payload = {
        "guidance": outline.get("guidance", ""),
        "purpose": outline.get("purpose", ""),
        "purposeSummary": outline.get("purpose_summary", ""),
    }

    for chunk_idx, chunk_items in enumerate(chunks):
        # Strip conclusion items — the API generates the real conclusion via includeConclusion: true.
        # Explicit conclusion items in the array render as groups, not actual conclusions.
        filtered_items = [it for it in chunk_items if it.get("type") != "conclusion"]
        chunk_procedures = [
            _sanitize_procedure(_strip_nested_ids(_build_procedure(it, include_signoffs)))
            for it in filtered_items
        ]
        payload = {**base_payload, "procedures": chunk_procedures}

        if chunk_idx == 0:
            # First chunk: new document — include conclusion flag so the API
            # generates the conclusion widget.  Subsequent (update) chunks must
            # NOT include these flags or they create duplicate conclusions.
            payload["id"] = None
            payload["includeConclusion"] = True
            payload["conclusionTitle"] = "Conclusion"
            payload["documentInfo"] = {
                "folder": outline.get("folder_id", ""),
                "name": outline.get("name", ""),
                "number": outline.get("number", ""),
            }
        else:
            # Subsequent chunks: use captured ID (placeholder — caller fills in)
            payload["id"] = "__CAPTURED_ID__"

        payloads.append(payload)

    # Per-payload expected procedure counts — the LLM MUST compare each
    # against the API response count and HARD FAIL on mismatch.
    expected_per_payload = [len(p["procedures"]) for p in payloads]

    metadata = {
        "total_procedures": proc_count,
        "total_items": len(items),
        "chunks": len(payloads),
        "max_per_chunk": max_per_chunk,
        "has_long_guidance": has_long_guidance,
        "expected_per_payload": expected_per_payload,
        "default_response_applied": default_applied,
    }

    # Explicit submission instructions — co-located with the data so the LLM
    # cannot miss them.  This is the authoritative guide for what to do next.
    if len(payloads) == 1:
        submission = (
            f"SUBMIT: Call checklist-save ONCE with payloads[0]. "
            f"Expected {expected_per_payload[0]} procedures in the response. "
            f"Do NOT call checklist-save again — there is only 1 payload. STOP after this single call."
        )
    else:
        steps = [
            f"  1. Call checklist-save with payloads[0] (id: null). "
            f"Capture the returned document ID. Expected {expected_per_payload[0]} procedures."
        ]
        for i in range(1, len(payloads)):
            steps.append(
                f"  {i + 1}. Replace __CAPTURED_ID__ in payloads[{i}] with the captured ID, "
                f"then call checklist-save. Expected {expected_per_payload[i]} procedures."
            )
        submission = (
            f"SUBMIT: {len(payloads)} sequential checklist-save calls:\n"
            + "\n".join(steps)
            + f"\nTotal calls: exactly {len(payloads)}. Do NOT make any additional calls."
        )

    return {
        "payloads": payloads,
        "submission_instructions": submission,
        "validation": validation,
        "metadata": metadata,
    }


def build_checklist_update(outline: dict) -> dict:
    """Build update payload for an existing checklist.

    Returns:
        {
            "payload": {...},        # Single sparse update payload
            "validation": {"valid": bool, "errors": [...], "warnings": [...]},
            "metadata": {"mode": "update", "modified_procedures": N, ...}
        }
    """
    # Apply checklist-level default response to new procedures (no id) that lack one.
    default_response = outline.get("default_response")
    default_applied = 0
    if default_response:
        for item in outline.get("items", []):
            if (
                not item.get("id")
                and item.get("type") in ("procedure", "conclusion")
                and not item.get("response")
            ):
                item["response"] = default_response
                default_applied += 1

    validation = _validate_update_outline(outline)
    if not validation["valid"]:
        return {
            "payload": {},
            "validation": validation,
            "metadata": {"error": "Validation failed — fix errors before submitting"},
        }

    items = outline.get("items", [])
    include_signoffs = outline.get("include_signoffs", True)
    document_id = outline["document_id"]

    procedures = [_build_update_procedure(it, include_signoffs) for it in items]

    # Count categories
    modified = sum(1 for it in items if it.get("id") and not it.get("_delete"))
    added = sum(1 for it in items if not it.get("id"))
    deleted = sum(1 for it in items if it.get("_delete"))

    payload = {
        "id": document_id,
        "procedures": procedures,
    }

    # Include optional top-level fields only if provided
    if "purpose" in outline:
        payload["purpose"] = outline["purpose"]
    if "purpose_summary" in outline:
        payload["purposeSummary"] = outline["purpose_summary"]
    if "guidance" in outline:
        payload["guidance"] = outline["guidance"]

    metadata = {
        "mode": "update",
        "document_id": document_id,
        "total_items": len(items),
        "modified_procedures": modified,
        "added_procedures": added,
        "deleted_procedures": deleted,
        "default_response_applied": default_applied,
    }

    return {
        "payload": payload,
        "submission_instructions": (
            f"SUBMIT: Call checklist-save ONCE with the payload (update mode). "
            f"Do NOT call checklist-save again. STOP after this single call."
        ),
        "validation": validation,
        "metadata": metadata,
    }


# ---------------------------------------------------------------------------
# Query builder
# ---------------------------------------------------------------------------


def _build_question(item: dict) -> dict:
    """Build a query question or questionSet object."""
    if item.get("type") == "questionSet":
        return {
            "depth": 0,
            "type": "questionSet",
            "title": item.get("text", ""),
            "hidden": item.get("hidden", False),
            "hideCondition": item.get("hide_condition", None),
        }

    # Question — dual column (text + file upload)
    # Strip leading numbering from question text (Caseware auto-numbers)
    text = item.get("text", "")
    text, _ = _strip_numbering(text)
    # Detect dynamic elements (formulas, placeholders) — no generic bracket conversion
    text = _detect_dynamic_elements(text, convert_generic_brackets=False)
    title = item.get("title", text)
    title, _ = _strip_numbering(title)

    placeholder = item.get("placeholder", "Enter response here")
    return {
        "depth": 1,
        "type": "question",
        "title": title,
        "text": f"<p>{text}</p>",
        "rows": [{
            "columns": [
                {"type": "text", "placeholder": placeholder},
                {"type": "files", "placeholder": "", "fileDestination": {}},
            ]
        }],
        "hidden": item.get("hidden", False),
        "hideCondition": item.get("hide_condition", None),
    }


def build_query(outline: dict) -> dict:
    """Build validated Caseware query payload from an outline.

    Returns:
        {
            "payload": {...},
            "validation": {"valid": bool, "errors": [...], "warnings": [...]},
            "metadata": {...}
        }
    """
    items = outline.get("items", [])
    errors: list[str] = []
    warnings: list[str] = []

    # Basic validation
    for i, item in enumerate(items):
        if item.get("type") not in ("questionSet", "question"):
            errors.append(
                f"Item {i}: Invalid type '{item.get('type')}' for query. "
                f"Must be 'questionSet' or 'question'."
            )

    validation = {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    if not validation["valid"]:
        return {
            "payload": {},
            "validation": validation,
            "metadata": {"error": "Validation failed"},
        }

    questions = [_strip_nested_ids(_build_question(item)) for item in items]

    payload = {
        "id": None,
        "documentInfo": {
            "folder": outline.get("folder_id", ""),
            "name": outline.get("name", ""),
            "number": outline.get("number", ""),
        },
        "instructions": outline.get("instructions", ""),
        "purpose": outline.get("purpose", ""),
        "purposeSummary": outline.get("purpose_summary", ""),
        "questions": questions,
    }

    q_count = sum(1 for q in questions if q["type"] == "question")
    metadata = {
        "total_questions": q_count,
        "total_question_sets": sum(1 for q in questions if q["type"] == "questionSet"),
    }

    return {
        "payload": payload,
        "submission_instructions": (
            f"SUBMIT: Call query-save ONCE with the payload. "
            f"Expected {q_count} questions in the response. "
            f"Do NOT call query-save again. STOP after this single call."
        ),
        "validation": validation,
        "metadata": metadata,
    }


def _build_update_question(item: dict) -> dict:
    """Build a sparse update question/questionSet object."""
    item_id = item.get("id")

    # New item — no ID, full build
    if not item_id:
        return _build_question(item)

    # Soft-delete
    if item.get("_delete", False):
        return {"id": item_id, "hidden": True}

    # Sparse update
    q: dict[str, Any] = {"id": item_id}

    if "text" in item:
        q["text"] = f"<p>{item['text']}</p>"
    if "title" in item:
        q["title"] = item["title"]
    if "type" in item:
        q["type"] = item["type"]
    if "hidden" in item:
        q["hidden"] = item["hidden"]
    if "hide_condition" in item:
        q["hideCondition"] = item["hide_condition"]

    return q


def build_query_update(outline: dict) -> dict:
    """Build update payload for an existing query.

    Returns:
        {
            "payload": {...},
            "validation": {"valid": bool, "errors": [...], "warnings": [...]},
            "metadata": {"mode": "update", ...}
        }
    """
    validation = _validate_update_outline(outline)
    if not validation["valid"]:
        return {
            "payload": {},
            "validation": validation,
            "metadata": {"error": "Validation failed"},
        }

    items = outline.get("items", [])
    document_id = outline["document_id"]

    questions = [_build_update_question(item) for item in items]

    modified = sum(1 for it in items if it.get("id") and not it.get("_delete"))
    added = sum(1 for it in items if not it.get("id"))
    deleted = sum(1 for it in items if it.get("_delete"))

    payload: dict[str, Any] = {
        "id": document_id,
        "questions": questions,
    }

    if "instructions" in outline:
        payload["instructions"] = outline["instructions"]
    if "purpose" in outline:
        payload["purpose"] = outline["purpose"]
    if "purpose_summary" in outline:
        payload["purposeSummary"] = outline["purpose_summary"]

    metadata = {
        "mode": "update",
        "document_id": document_id,
        "total_items": len(items),
        "modified_questions": modified,
        "added_questions": added,
        "deleted_questions": deleted,
    }

    return {
        "payload": payload,
        "submission_instructions": (
            f"SUBMIT: Call query-save ONCE with the payload (update mode). "
            f"Do NOT call query-save again. STOP after this single call."
        ),
        "validation": validation,
        "metadata": metadata,
    }


# ---------------------------------------------------------------------------
# Letter builder
# ---------------------------------------------------------------------------

# Dynamic element detection patterns
_FORMULA_PATTERNS: list[tuple[str, str, str]] = [
    # (regex_pattern, formula, display_text)
    (r"\bentity\s+name\b|\bcompany\s+name\b|\bclient\s+name\b", 'engprop("name")', "Entity Name"),
    (r"\byear\s*end\b|\bperiod\s*end\b|\bbalance\s+sheet\s+date\b", 'engprop("yearend", 0, "longDate")', "Year End"),
    (r"\bfirm\s+name\b|\bauditor?\s+firm\b", 'collaborate("firmName")', "Firm Name"),
    (r"\blegal\s+name\b", 'collaborate("legalName")', "Legal Name"),
]

_PLACEHOLDER_PATTERNS: list[tuple[str, str]] = [
    # (regex_pattern, placeholder_type)
    (r"\[(?:select\s+)?date\]|\[letter\s+date\]", "date"),
    (r"\[enter\b[^\]]*\]|\[insert\b[^\]]*\]|\[describe\b[^\]]*\]", "input-area"),
    (r"\bsignature\b|\bsigned\s+by\b|\bauthorized\s+by\b|\[select\s+staff\]", "staff"),
]


def _make_formula_html(formula: str, display: str) -> str:
    """Build formula span HTML."""
    escaped = formula.replace('"', "&quot;")
    return f'<span formula="{escaped}" class="formula">{display}</span>'


def _make_placeholder_html(ptype: str, label: str) -> str:
    """Build placeholder span HTML with unique ID."""
    label = html_mod.escape(label, quote=True)
    pid = _generate_placeholder_id()

    if ptype == "date":
        return (
            f'<span placeholder="{pid}" type="date" user="null" '
            f'contenteditable="false" custom-label="{label}" title="{label}" '
            f'class="placeholder unselected"><span>{label}</span>'
            f'<span class="caret hidden-print">&nbsp;</span></span>'
        )
    elif ptype == "staff":
        return (
            f'<span placeholder="{pid}" type="staff" user="undefined" '
            f'contenteditable="false" custom-label="" '
            f'class="placeholder unselected"><span>Select Staff</span>'
            f'<span class="caret hidden-print">&nbsp;</span></span>'
        )
    else:  # input-area
        return (
            f'<span placeholder="{pid}" contenteditable="false" '
            f'type="input-area" title="{label}" custom-label="{label}" '
            f'class="placeholder unselected">{label}</span>'
        )


# Matches explicit wording() formula calls in text, e.g.:
#   wording("@auditGlossary"), sentencecase(wording("@id"))
# NOTE: Only matches wording() — engprop() and collaborate() are handled by
# keyword detection in step 1. Matching all three would double-wrap keywords
# that step 1 already converted to formula HTML.
_FORMULA_SYNTAX_RE = re.compile(
    r'(?:sentencecase\s*\(\s*)?'
    r'wording\s*\([^)]*\)'
    r'(?:\s*\))?'
)


def _detect_dynamic_elements(
    text: str, convert_generic_brackets: bool = True
) -> str:
    """Detect and replace dynamic element patterns in text with HTML.

    Handles: formulas, date/input/staff placeholders, explicit formula syntax,
    and (optionally) generic [bracketed text].

    Args:
        text: The text to process.
        convert_generic_brackets: If True (default, used for letters), any
            remaining [bracketed text] is converted to input-area placeholders.
            If False (used for checklists/queries), only known formula and
            placeholder patterns are converted — generic brackets like
            [ISA 315] or [Section 3.1] are left as-is.
    """
    result = text

    # 1. Replace known formula patterns (case-insensitive)
    for pattern, formula, display in _FORMULA_PATTERNS:
        result = re.sub(
            pattern,
            _make_formula_html(formula, display),
            result,
            flags=re.IGNORECASE,
        )

    # 2. Replace known placeholder patterns
    for pattern, ptype in _PLACEHOLDER_PATTERNS:
        for match in re.finditer(pattern, result, re.IGNORECASE):
            original = match.group(0)
            label = original.strip("[]") if original.startswith("[") else original
            replacement = _make_placeholder_html(ptype, label)
            result = result.replace(original, replacement, 1)

    # 3. Wrap explicit formula syntax (wording(), engprop(), etc.) in HTML
    def _replace_formula_syntax(m: re.Match) -> str:
        formula = m.group(0)
        return _make_formula_html(formula, formula)

    result = _FORMULA_SYNTAX_RE.sub(_replace_formula_syntax, result)

    # 4. Replace remaining [bracketed text] as input-area placeholders
    #    (letters only — checklists/queries skip this to avoid false positives)
    if convert_generic_brackets:
        def _replace_bracket(m: re.Match) -> str:
            label = m.group(1)
            return _make_placeholder_html("input-area", label)

        result = re.sub(r"\[([^\]]+)\]", _replace_bracket, result)

    return result


def _build_section(section: dict) -> dict:
    """Build a letter content section with dynamic element detection."""
    content = section.get("content", "")

    # Apply dynamic element detection (letters convert all generic brackets)
    content = _detect_dynamic_elements(content, convert_generic_brackets=True)

    # Wrap in <p> tags if not already HTML
    if not content.strip().startswith("<"):
        content = f"<p>{content}</p>"

    return {
        "type": "content",
        "title": section.get("title", ""),
        "content": content,
        "depth": 0,
        "excludeFromTableOfContents": False,
        "dontNumberInTableOfContents": False,
        "hidden": section.get("hidden", False),
    }


def build_letter(outline: dict) -> dict:
    """Build validated Caseware letter payloads (two-step) from an outline.

    Returns:
        {
            "step1_payload": {...},   # Creates doc + empty area
            "step2_template": {...},  # Template for step 2 (caller fills IDs)
            "validation": {"valid": bool, "errors": [...], "warnings": [...]},
            "metadata": {...}
        }
    """
    sections = outline.get("sections", [])
    errors: list[str] = []
    warnings: list[str] = []

    if not sections:
        errors.append("Letter outline has no sections")

    validation = {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    if not validation["valid"]:
        return {
            "step1_payload": {},
            "step2_template": {},
            "validation": validation,
            "metadata": {"error": "Validation failed"},
        }

    area_title = outline.get("area_title", outline.get("name", "Letter"))

    # Step 1: Create the letter (empty sections)
    step1 = {
        "id": None,
        "type": "letter",
        "documentInfo": {
            "folder": outline.get("folder_id", ""),
            "name": outline.get("name", ""),
            "number": outline.get("number", ""),
        },
        "purpose": outline.get("purpose", ""),
        "purposeSummary": outline.get("purpose_summary", ""),
        "documentMap": [{
            "type": "area",
            "title": area_title,
            "sections": [],
        }],
    }

    # Step 2: Add sections (caller fills in docId and areaId from step 1 response)
    built_sections = [_build_section(s) for s in sections]

    step2 = {
        "id": "__DOC_ID__",
        "type": "letter",
        "documentMap": [{
            "id": "__AREA_ID__",
            "type": "area",
            "title": area_title,
            "excludeFromTableOfContents": False,
            "dontNumberInTableOfContents": False,
            "hidden": False,
            "sections": built_sections,
        }],
    }

    metadata = {
        "total_sections": len(built_sections),
        "area_title": area_title,
    }

    return {
        "step1_payload": step1,
        "step2_template": step2,
        "submission_instructions": (
            "SUBMIT: Exactly 2 statement-save calls required:\n"
            "  1. Call statement-save with step1_payload. Capture response.id (doc ID) "
            "and response.documentMap[0].id (area ID). HARD FAIL if either is null.\n"
            "  2. Replace __DOC_ID__ and __AREA_ID__ in step2_template with captured IDs. "
            "Call statement-save with the filled template.\n"
            "  3. Call statement-get to verify sections were saved.\n"
            "Total calls: exactly 2 statement-save calls. Do NOT make any additional calls."
        ),
        "validation": validation,
        "metadata": metadata,
    }


def _build_update_section(section: dict) -> dict:
    """Build a sparse update section for a letter."""
    section_id = section.get("id")

    # New section — no ID, full build
    if not section_id:
        return _build_section(section)

    # Soft-delete
    if section.get("_delete", False):
        return {"id": section_id, "hidden": True}

    # Sparse update
    s: dict[str, Any] = {"id": section_id}

    if "content" in section:
        content = _detect_dynamic_elements(section["content"], convert_generic_brackets=True)
        if not content.strip().startswith("<"):
            content = f"<p>{content}</p>"
        s["content"] = content

    if "title" in section:
        s["title"] = section["title"]
    if "hidden" in section:
        s["hidden"] = section["hidden"]

    return s


def build_letter_update(outline: dict) -> dict:
    """Build update payload for an existing letter.

    Single-call (no two-step needed for updates — document already exists).
    Requires document_id + area_id from statement-get.

    Returns:
        {
            "payload": {...},
            "validation": {"valid": bool, "errors": [...], "warnings": [...]},
            "metadata": {"mode": "update", ...}
        }
    """
    validation = _validate_update_outline(outline)

    area_id = outline.get("area_id", "")
    if not area_id:
        validation["errors"].append("Letter update requires 'area_id' from statement-get")
        validation["valid"] = False
    elif not _validate_id_format(area_id):
        validation["errors"].append(
            f"INVALID_ID_FORMAT: area_id '{area_id}' is not a valid 22-char uuid-base64url ID"
        )
        validation["valid"] = False

    if not validation["valid"]:
        return {
            "payload": {},
            "validation": validation,
            "metadata": {"error": "Validation failed"},
        }

    sections = outline.get("sections", [])
    document_id = outline["document_id"]
    area_title = outline.get("area_title", "")

    built_sections = [_build_update_section(s) for s in sections]

    modified = sum(1 for s in sections if s.get("id") and not s.get("_delete"))
    added = sum(1 for s in sections if not s.get("id"))
    deleted = sum(1 for s in sections if s.get("_delete"))

    payload: dict[str, Any] = {
        "id": document_id,
        "type": "letter",
        "documentMap": [{
            "id": area_id,
            "type": "area",
            "title": area_title,
            "sections": built_sections,
        }],
    }

    if "purpose" in outline:
        payload["purpose"] = outline["purpose"]
    if "purpose_summary" in outline:
        payload["purposeSummary"] = outline["purpose_summary"]

    metadata = {
        "mode": "update",
        "document_id": document_id,
        "area_id": area_id,
        "total_sections": len(sections),
        "modified_sections": modified,
        "added_sections": added,
        "deleted_sections": deleted,
    }

    return {
        "payload": payload,
        "submission_instructions": (
            f"SUBMIT: Call statement-save ONCE with the payload (update mode). "
            f"Do NOT call statement-save again. STOP after this single call."
        ),
        "validation": validation,
        "metadata": metadata,
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def build_payload(outline: dict) -> dict:
    """Route to the appropriate builder based on outline.document_type.

    Args:
        outline: Procedure outline with document_type, name, number, items, etc.

    Returns:
        Builder-specific result dict with payloads, validation, and metadata.
    """
    doc_type = outline.get("document_type", "").lower().strip()
    mode = outline.get("mode", "create").lower().strip()

    if mode == "update":
        if doc_type == "checklist":
            return build_checklist_update(outline)
        elif doc_type == "query":
            return build_query_update(outline)
        elif doc_type == "letter":
            return build_letter_update(outline)
        # Fall through to unknown type error below

    if doc_type == "checklist":
        return build_checklist(outline)
    elif doc_type == "query":
        return build_query(outline)
    elif doc_type == "letter":
        return build_letter(outline)
    else:
        return {
            "payloads": [],
            "validation": {
                "valid": False,
                "errors": [
                    f"Unknown document_type: '{doc_type}'. "
                    f"Must be 'checklist', 'query', or 'letter'."
                ],
                "warnings": [],
            },
            "metadata": {},
        }
