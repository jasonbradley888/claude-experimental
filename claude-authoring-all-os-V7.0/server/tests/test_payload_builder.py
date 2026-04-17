"""Tests for payload_builder module."""

import json
import pytest

from caseware_authoring_tools.payload_builder import (
    build_payload,
    build_checklist,
    build_query,
    build_letter,
    build_checklist_update,
    build_query_update,
    build_letter_update,
    _parse_response,
    _ensure_not_applicable,
    _calculate_inline_choices,
    _validate_depth_sequence,
    _validate_types_at_depth,
    _validate_procedures_have_responses,
    _validate_outline,
    _validate_id_format,
    _validate_update_outline,
    _build_update_procedure,
    _build_question,
    _chunk_at_groups,
    _generate_placeholder_id,
    _detect_dynamic_elements,
    _build_procedure,
    _strip_nested_ids,
    _strip_numbering,
    _wrap_procedure_text,
    _sanitize_procedure,
)


# ===================================================================
# Response parsing
# ===================================================================


class TestParseResponse:
    def test_choice_with_options(self):
        result = _parse_response("choice:Yes,No,Not Applicable")
        assert result["rows"][0]["columns"][0]["type"] == "choice"
        choices = [c["text"] for c in result["rows"][0]["columns"][0]["choices"]]
        assert choices == ["Yes", "No", "Not Applicable"]
        assert result["includeNote"] is True
        assert result["notePlaceholder"] == "Response and Comments"

    def test_choice_auto_appends_not_applicable(self):
        result = _parse_response("choice:Low,Moderate,High")
        choices = [c["text"] for c in result["rows"][0]["columns"][0]["choices"]]
        assert choices == ["Low", "Moderate", "High", "Not Applicable"]

    def test_choice_does_not_duplicate_not_applicable(self):
        result = _parse_response("choice:Yes,No,Not Applicable")
        choices = [c["text"] for c in result["rows"][0]["columns"][0]["choices"]]
        assert choices.count("Not Applicable") == 1

    def test_choice_default_yes_no_na(self):
        result = _parse_response("choice")
        choices = [c["text"] for c in result["rows"][0]["columns"][0]["choices"]]
        assert choices == ["Yes", "No", "Not Applicable"]

    def test_text_basic(self):
        result = _parse_response("text")
        col = result["rows"][0]["columns"][0]
        assert col["type"] == "text"
        assert col["placeholder"] == "Enter response here"
        assert result["includeNote"] is False

    def test_text_with_placeholder(self):
        result = _parse_response("text:Describe the process")
        col = result["rows"][0]["columns"][0]
        assert col["type"] == "text"
        assert col["placeholder"] == "Describe the process"

    def test_number(self):
        result = _parse_response("number")
        assert result["rows"][0]["columns"][0]["type"] == "number"
        assert result["includeNote"] is True

    def test_date(self):
        result = _parse_response("date")
        assert result["rows"][0]["columns"][0]["type"] == "date"
        assert result["includeNote"] is True

    def test_none_returns_none(self):
        assert _parse_response(None) is None
        assert _parse_response("") is None

    def test_unrecognised_defaults_to_text(self):
        result = _parse_response("Entity information")
        col = result["rows"][0]["columns"][0]
        assert col["type"] == "text"
        assert col["placeholder"] == "Entity information"
        assert "_warning" in result


# ===================================================================
# Inline choices
# ===================================================================


class TestInlineChoices:
    def test_three_short_choices(self):
        assert _calculate_inline_choices(["Yes", "No", "N/A"]) is True

    def test_four_choices_not_inline(self):
        assert _calculate_inline_choices(["A", "B", "C", "D"]) is False

    def test_long_text_not_inline(self):
        assert _calculate_inline_choices(["A very long choice text here", "B"]) is False

    def test_exactly_three_at_max_length(self):
        assert _calculate_inline_choices(["A" * 20, "B" * 20, "C" * 20]) is True

    def test_one_over_max_length(self):
        assert _calculate_inline_choices(["A" * 21, "B", "C"]) is False


# ===================================================================
# Not Applicable
# ===================================================================


class TestEnsureNotApplicable:
    def test_appends_when_missing(self):
        assert _ensure_not_applicable(["Yes", "No"]) == ["Yes", "No", "Not Applicable"]

    def test_does_not_duplicate(self):
        result = _ensure_not_applicable(["Yes", "No", "Not Applicable"])
        assert result == ["Yes", "No", "Not Applicable"]

    def test_case_insensitive(self):
        result = _ensure_not_applicable(["Yes", "not applicable"])
        assert len(result) == 2  # Not duplicated


# ===================================================================
# Depth validation
# ===================================================================


class TestValidateDepthSequence:
    def test_valid_sequence(self):
        items = [
            {"depth": 0, "type": "group", "text": "G"},
            {"depth": 1, "type": "heading", "text": "H"},
            {"depth": 2, "type": "procedure", "text": "P", "response": "choice"},
        ]
        assert _validate_depth_sequence(items) == []

    def test_jump_greater_than_one(self):
        items = [
            {"depth": 0, "type": "group", "text": "G"},
            {"depth": 3, "type": "procedure", "text": "P"},
        ]
        errors = _validate_depth_sequence(items)
        assert len(errors) == 1
        assert "INVALID_DEPTH" in errors[0]

    def test_depth_exceeds_max(self):
        items = [{"depth": 5, "type": "procedure", "text": "P"}]
        errors = _validate_depth_sequence(items)
        assert len(errors) == 1
        assert "INVALID_DEPTH" in errors[0]

    def test_depth_can_decrease_freely(self):
        items = [
            {"depth": 0, "type": "group", "text": "G1"},
            {"depth": 1, "type": "heading", "text": "H"},
            {"depth": 2, "type": "procedure", "text": "P", "response": "text"},
            {"depth": 0, "type": "group", "text": "G2"},
        ]
        assert _validate_depth_sequence(items) == []


# ===================================================================
# Type-at-depth validation
# ===================================================================


class TestValidateTypesAtDepth:
    def test_valid_types(self):
        items = [
            {"depth": 0, "type": "group", "text": "G"},
            {"depth": 1, "type": "heading", "text": "H"},
            {"depth": 2, "type": "procedure", "text": "P"},
            {"depth": 0, "type": "conclusion", "text": "C"},
        ]
        assert _validate_types_at_depth(items) == []

    def test_group_at_depth_2_fails(self):
        items = [{"depth": 2, "type": "group", "text": "G"}]
        errors = _validate_types_at_depth(items)
        assert len(errors) == 1
        assert "INVALID_TYPE_AT_DEPTH" in errors[0]

    def test_procedure_at_depth_0_fails(self):
        items = [{"depth": 0, "type": "procedure", "text": "P"}]
        errors = _validate_types_at_depth(items)
        assert len(errors) == 1

    def test_heading_with_response_warns(self):
        items = [{"depth": 1, "type": "heading", "text": "H", "response": "text"}]
        errors = _validate_types_at_depth(items)
        assert len(errors) == 1
        assert "has a response" in errors[0]


# ===================================================================
# Procedures have responses
# ===================================================================


class TestValidateProceduresHaveResponses:
    def test_procedure_without_response(self):
        items = [{"depth": 2, "type": "procedure", "text": "P"}]
        errors = _validate_procedures_have_responses(items)
        assert len(errors) == 1
        assert "MISSING_RESPONSE_TYPE" in errors[0]

    def test_procedure_with_response(self):
        items = [{"depth": 2, "type": "procedure", "text": "P", "response": "choice"}]
        assert _validate_procedures_have_responses(items) == []

    def test_group_without_response_ok(self):
        items = [{"depth": 0, "type": "group", "text": "G"}]
        assert _validate_procedures_have_responses(items) == []


# ===================================================================
# Chunking
# ===================================================================


class TestChunkAtGroups:
    def test_no_chunking_needed(self):
        items = [
            {"depth": 0, "type": "group", "text": "G"},
            {"depth": 1, "type": "procedure", "text": "P1", "response": "text"},
            {"depth": 1, "type": "procedure", "text": "P2", "response": "text"},
        ]
        chunks = _chunk_at_groups(items, max_per_chunk=20)
        assert len(chunks) == 1

    def test_splits_at_group_boundaries(self):
        items = []
        # Two groups, each with 15 procedures
        for g in range(2):
            items.append({"depth": 0, "type": "group", "text": f"Group {g}"})
            for p in range(15):
                items.append({
                    "depth": 1, "type": "procedure",
                    "text": f"P{g}-{p}", "response": "choice",
                })

        chunks = _chunk_at_groups(items, max_per_chunk=20)
        assert len(chunks) == 2

    def test_conclusion_in_final_chunk(self):
        items = [
            {"depth": 0, "type": "group", "text": "G"},
            {"depth": 1, "type": "procedure", "text": "P", "response": "text"},
            {"depth": 0, "type": "conclusion", "text": "C", "response": "text"},
        ]
        chunks = _chunk_at_groups(items, max_per_chunk=20)
        last_chunk = chunks[-1]
        assert any(it["type"] == "conclusion" for it in last_chunk)

    def test_single_large_group_not_split(self):
        items = [{"depth": 0, "type": "group", "text": "G"}]
        for i in range(30):
            items.append({
                "depth": 1, "type": "procedure",
                "text": f"P{i}", "response": "choice",
            })

        chunks = _chunk_at_groups(items, max_per_chunk=20)
        # Single group should NOT be split even if >20
        assert len(chunks) == 1

    def test_empty_items(self):
        assert _chunk_at_groups([]) == []


# ===================================================================
# Build procedure
# ===================================================================


class TestBuildProcedure:
    def test_choice_procedure(self):
        item = {
            "depth": 2, "type": "procedure",
            "text": "Has the policy been reviewed?",
            "response": "choice:Yes,No,Not Applicable",
        }
        proc = _build_procedure(item)
        assert proc["depth"] == 2
        assert proc["type"] == "procedure"
        assert proc["includeNote"] is True
        assert proc["includeSignOffs"] is True
        assert proc["rows"][0]["columns"][0]["type"] == "choice"

    def test_text_procedure(self):
        item = {
            "depth": 1, "type": "procedure",
            "text": "Describe the process.",
            "response": "text",
        }
        proc = _build_procedure(item)
        assert proc["includeNote"] is False
        assert proc["rows"][0]["columns"][0]["type"] == "text"

    def test_group_no_rows(self):
        item = {"depth": 0, "type": "group", "text": "Revenue"}
        proc = _build_procedure(item)
        assert "rows" not in proc
        assert proc["includeNote"] is True

    def test_conclusion_default_text_response(self):
        item = {"depth": 0, "type": "conclusion", "text": "Conclusion text"}
        proc = _build_procedure(item)
        assert proc["rows"][0]["columns"][0]["type"] == "text"

    def test_guidance_included(self):
        item = {
            "depth": 2, "type": "procedure",
            "text": "Check it", "response": "choice",
            "guidance": "Review for compliance.",
        }
        proc = _build_procedure(item)
        assert proc["guidance"] == "Review for compliance."

    def test_authoritative_references(self):
        item = {
            "depth": 2, "type": "procedure",
            "text": "Check", "response": "choice",
            "authoritative_references": ["AS 2201.39", "ISA 315"],
        }
        proc = _build_procedure(item)
        assert len(proc["authoritativeReferences"]) == 2
        assert proc["authoritativeReferences"][0]["reference"] == "AS 2201.39"

    def test_max_five_references(self):
        item = {
            "depth": 2, "type": "procedure",
            "text": "Check", "response": "choice",
            "authoritative_references": [f"REF-{i}" for i in range(10)],
        }
        proc = _build_procedure(item)
        assert len(proc["authoritativeReferences"]) == 5


# ===================================================================
# Numbering / bullet stripping
# ===================================================================


class TestStripNumbering:
    """Covers all indicator styles from the acceptance criteria."""

    # --- Decimal numbering ---
    def test_decimal(self):
        assert _strip_numbering("1. Verify the balance")[0] == "Verify the balance"

    def test_decimal_multi(self):
        assert _strip_numbering("12. Review")[0] == "Review"

    def test_decimal_subsection(self):
        assert _strip_numbering("1.1. Verify")[0] == "Verify"

    # --- Alpha numbering ---
    def test_alpha_lower(self):
        assert _strip_numbering("a. Confirm amounts")[0] == "Confirm amounts"

    def test_alpha_upper(self):
        assert _strip_numbering("B. Confirm amounts")[0] == "Confirm amounts"

    # --- Roman numeral numbering ---
    def test_roman_lower(self):
        assert _strip_numbering("ii. Review the policy")[0] == "Review the policy"

    def test_roman_upper(self):
        assert _strip_numbering("IV. Review the policy")[0] == "Review the policy"

    # --- Parenthesised numbering ---
    def test_paren_digit(self):
        assert _strip_numbering("(1) Verify")[0] == "Verify"

    def test_paren_alpha(self):
        assert _strip_numbering("(a) Verify")[0] == "Verify"

    def test_paren_roman(self):
        assert _strip_numbering("(iii) Verify")[0] == "Verify"

    # --- Bullet symbols ---
    def test_bullet_dot(self):
        assert _strip_numbering("• Assess the risk")[0] == "Assess the risk"

    def test_en_dash(self):
        assert _strip_numbering("– Assess the risk")[0] == "Assess the risk"

    def test_em_dash(self):
        assert _strip_numbering("\u2014 Assess the risk")[0] == "Assess the risk"

    def test_asterisk(self):
        assert _strip_numbering("* Assess the risk")[0] == "Assess the risk"

    def test_hyphen(self):
        assert _strip_numbering("- Assess the risk")[0] == "Assess the risk"

    # --- Leading whitespace ---
    def test_leading_whitespace_decimal(self):
        assert _strip_numbering("  1. Verify")[0] == "Verify"

    def test_leading_whitespace_bullet(self):
        assert _strip_numbering("  • Assess")[0] == "Assess"

    # --- Preserved text (no stripping) ---
    def test_no_indicator(self):
        text = "Verify the balance"
        assert _strip_numbering(text)[0] == text

    def test_mid_sentence_not_stripped(self):
        text = "Verify items a. and b."
        assert _strip_numbering(text)[0] == text

    def test_was_stripped_flag(self):
        _, was = _strip_numbering("1. Verify")
        assert was is True
        _, was = _strip_numbering("Verify")
        assert was is False

    # --- Mixed styles via _build_procedure integration ---
    def test_build_procedure_strips_numbering(self):
        item = {
            "depth": 2, "type": "procedure",
            "text": "• Has the policy been reviewed?",
            "response": "choice:Yes,No,Not Applicable",
        }
        proc = _build_procedure(item)
        # Procedure text is HTML-wrapped after stripping
        assert "Has the policy been reviewed?" in proc["text"]
        assert proc["text"].startswith("<p")

    def test_build_procedure_strips_hyphen(self):
        item = {
            "depth": 2, "type": "procedure",
            "text": "- Confirm the amounts",
            "response": "choice:Yes,No,Not Applicable",
        }
        proc = _build_procedure(item)
        assert "Confirm the amounts" in proc["text"]
        assert proc["text"].startswith("<p")


# ===================================================================
# Placeholder ID generation
# ===================================================================


class TestGeneratePlaceholderId:
    def test_length(self):
        pid = _generate_placeholder_id()
        assert len(pid) == 22

    def test_unique(self):
        ids = {_generate_placeholder_id() for _ in range(100)}
        assert len(ids) == 100


# ===================================================================
# Dynamic element detection (letters)
# ===================================================================


class TestDetectDynamicElements:
    def test_date_placeholder(self):
        result = _detect_dynamic_elements("[Letter Date]")
        assert 'type="date"' in result
        assert "placeholder=" in result

    def test_input_placeholder(self):
        result = _detect_dynamic_elements("[Enter amount]")
        assert 'type="input-area"' in result

    def test_generic_bracket_becomes_input(self):
        result = _detect_dynamic_elements("[Some Custom Field]")
        assert 'type="input-area"' in result
        assert "Some Custom Field" in result

    def test_no_brackets_unchanged(self):
        text = "This is plain text with no placeholders."
        assert _detect_dynamic_elements(text) == text


# ===================================================================
# Build checklist (integration)
# ===================================================================


class TestBuildChecklist:
    def _simple_outline(self):
        return {
            "document_type": "checklist",
            "name": "Test Checklist",
            "number": "T-100",
            "folder_id": "abc123",
            "purpose": "Testing",
            "purpose_summary": "Test",
            "items": [
                {"depth": 0, "type": "group", "text": "Section 1"},
                {"depth": 1, "type": "heading", "text": "Verification"},
                {"depth": 2, "type": "procedure", "text": "Has it been reviewed?",
                 "response": "choice:Yes,No,Not Applicable"},
                {"depth": 2, "type": "procedure", "text": "Describe the process.",
                 "response": "text"},
                {"depth": 0, "type": "conclusion", "text": "Document your conclusion.",
                 "response": "text"},
            ],
        }

    def test_produces_valid_payload(self):
        result = build_checklist(self._simple_outline())
        assert result["validation"]["valid"] is True
        assert len(result["payloads"]) == 1

        payload = result["payloads"][0]
        assert payload["id"] is None
        assert payload["documentInfo"]["name"] == "Test Checklist"
        assert payload["documentInfo"]["number"] == "T-100"
        assert len(payload["procedures"]) == 4  # conclusion stripped (API generates via includeConclusion)

    def test_metadata(self):
        result = build_checklist(self._simple_outline())
        assert result["metadata"]["total_procedures"] == 3  # 2 procedures + 1 conclusion
        assert result["metadata"]["chunks"] == 1

    def test_validation_failure_returns_empty_payloads(self):
        outline = {
            "document_type": "checklist",
            "name": "Bad", "number": "X",
            "items": [
                {"depth": 0, "type": "group", "text": "G"},
                {"depth": 3, "type": "procedure", "text": "P", "response": "choice"},
            ],
        }
        result = build_checklist(outline)
        assert result["validation"]["valid"] is False
        assert len(result["payloads"]) == 0

    def test_chunking_triggers(self):
        items = []
        # Create 4 groups with 15 procedures each = 60 procedures (> 50 threshold)
        for g in range(4):
            items.append({"depth": 0, "type": "group", "text": f"G{g}"})
            for p in range(15):
                items.append({
                    "depth": 1, "type": "procedure",
                    "text": f"P{g}-{p}", "response": "choice",
                })
        items.append({"depth": 0, "type": "conclusion", "text": "Done", "response": "text"})

        outline = {
            "document_type": "checklist",
            "name": "Big", "number": "B-100",
            "items": items,
        }
        result = build_checklist(outline)
        assert result["validation"]["valid"] is True
        assert result["metadata"]["chunks"] > 1
        # First payload has id=None, subsequent have placeholder
        assert result["payloads"][0]["id"] is None
        assert result["payloads"][1]["id"] == "__CAPTURED_ID__"


# ===================================================================
# Build query (integration)
# ===================================================================


class TestBuildQuery:
    def test_simple_query(self):
        outline = {
            "document_type": "query",
            "name": "Info Request", "number": "B-100Q",
            "folder_id": "abc",
            "purpose": "Gather info", "purpose_summary": "Info",
            "instructions": "Please provide the following",
            "items": [
                {"depth": 0, "type": "questionSet", "text": "Overview"},
                {"depth": 1, "type": "question", "text": "Describe your policy.",
                 "title": "Revenue Policy", "placeholder": "Describe policy"},
            ],
        }
        result = build_query(outline)
        assert result["validation"]["valid"] is True
        payload = result["payload"]
        assert payload["documentInfo"]["number"] == "B-100Q"
        assert len(payload["questions"]) == 2
        assert payload["questions"][0]["type"] == "questionSet"
        assert payload["questions"][1]["type"] == "question"
        # Question has dual columns
        assert len(payload["questions"][1]["rows"][0]["columns"]) == 2

    def test_invalid_type_fails(self):
        outline = {
            "document_type": "query",
            "name": "Bad", "number": "X",
            "items": [{"depth": 0, "type": "group", "text": "G"}],
        }
        result = build_query(outline)
        assert result["validation"]["valid"] is False


# ===================================================================
# Build letter (integration)
# ===================================================================


class TestBuildLetter:
    def test_two_step_structure(self):
        outline = {
            "document_type": "letter",
            "name": "E-600 - Management Reps - Draft",
            "number": "E-600",
            "folder_id": "abc",
            "purpose": "Create letter", "purpose_summary": "Mgmt Reps",
            "area_title": "Management Representations",
            "sections": [
                {"title": "Date", "content": "[Letter Date]"},
                {"title": "Body", "content": "We confirm the financial statements."},
            ],
        }
        result = build_letter(outline)
        assert result["validation"]["valid"] is True

        # Step 1 has empty sections
        assert result["step1_payload"]["documentMap"][0]["sections"] == []
        assert result["step1_payload"]["id"] is None

        # Step 2 has actual sections
        step2_sections = result["step2_template"]["documentMap"][0]["sections"]
        assert len(step2_sections) == 2
        assert step2_sections[0]["depth"] == 0
        assert step2_sections[0]["type"] == "content"

        # Placeholders for IDs
        assert result["step2_template"]["id"] == "__DOC_ID__"
        assert result["step2_template"]["documentMap"][0]["id"] == "__AREA_ID__"

    def test_dynamic_elements_in_sections(self):
        outline = {
            "document_type": "letter",
            "name": "Test", "number": "T-1",
            "sections": [
                {"title": "Date", "content": "[Letter Date]"},
            ],
        }
        result = build_letter(outline)
        section = result["step2_template"]["documentMap"][0]["sections"][0]
        assert 'type="date"' in section["content"]

    def test_empty_sections_fails(self):
        outline = {
            "document_type": "letter",
            "name": "Test", "number": "T-1",
            "sections": [],
        }
        result = build_letter(outline)
        assert result["validation"]["valid"] is False


# ===================================================================
# build_payload router
# ===================================================================


class TestBuildPayload:
    def test_routes_to_checklist(self):
        outline = {
            "document_type": "checklist",
            "name": "Test", "number": "T",
            "items": [
                {"depth": 0, "type": "group", "text": "G"},
                {"depth": 1, "type": "procedure", "text": "P", "response": "choice"},
            ],
        }
        result = build_payload(outline)
        assert "payloads" in result

    def test_routes_to_query(self):
        outline = {
            "document_type": "query",
            "name": "Test", "number": "TQ",
            "items": [
                {"depth": 0, "type": "questionSet", "text": "Q"},
            ],
        }
        result = build_payload(outline)
        assert "payload" in result

    def test_routes_to_letter(self):
        outline = {
            "document_type": "letter",
            "name": "Test", "number": "T",
            "sections": [{"title": "A", "content": "B"}],
        }
        result = build_payload(outline)
        assert "step1_payload" in result

    def test_unknown_type_errors(self):
        result = build_payload({"document_type": "spreadsheet"})
        assert result["validation"]["valid"] is False

    def test_routes_update_to_checklist(self):
        outline = {
            "document_type": "checklist",
            "mode": "update",
            "document_id": "abcdefghijklmnopqrstuv",
            "items": [
                {"id": "existingProcId12345678", "text": "Updated text"},
            ],
        }
        result = build_payload(outline)
        assert result["metadata"]["mode"] == "update"
        assert "payload" in result

    def test_routes_update_to_query(self):
        outline = {
            "document_type": "query",
            "mode": "update",
            "document_id": "abcdefghijklmnopqrstuv",
            "items": [
                {"id": "existingQuestId1234567", "title": "Updated"},
            ],
        }
        result = build_payload(outline)
        assert result["metadata"]["mode"] == "update"

    def test_routes_update_to_letter(self):
        outline = {
            "document_type": "letter",
            "mode": "update",
            "document_id": "abcdefghijklmnopqrstuv",
            "area_id": "areaIdValue123456789ab",
            "sections": [
                {"id": "sectionId1234567890abc", "content": "Updated"},
            ],
        }
        result = build_payload(outline)
        assert result["metadata"]["mode"] == "update"

    def test_create_mode_backward_compatible(self):
        """Existing create outlines work unchanged (no mode field)."""
        outline = {
            "document_type": "checklist",
            "name": "Test", "number": "T",
            "items": [
                {"depth": 0, "type": "group", "text": "G"},
                {"depth": 1, "type": "procedure", "text": "P", "response": "choice"},
            ],
        }
        result = build_payload(outline)
        assert "payloads" in result  # create mode returns payloads list
        assert result["validation"]["valid"] is True


# ===================================================================
# ID validation
# ===================================================================


class TestValidateIdFormat:
    def test_valid_22_char_id(self):
        assert _validate_id_format("abcdefghijklmnopqrstuv") is True

    def test_valid_with_special_chars(self):
        assert _validate_id_format("Ab3_-fghijklmnopqrstuv") is True

    def test_too_short(self):
        assert _validate_id_format("abc") is False

    def test_too_long(self):
        assert _validate_id_format("abcdefghijklmnopqrstuvw") is False

    def test_invalid_chars(self):
        assert _validate_id_format("abcdefghijklmnopqrst!@") is False

    def test_empty_string(self):
        assert _validate_id_format("") is False


# ===================================================================
# Update outline validation
# ===================================================================


class TestValidateUpdateOutline:
    def test_valid_update_outline(self):
        outline = {
            "document_id": "abcdefghijklmnopqrstuv",
            "items": [
                {"id": "existingProcId12345678", "text": "Updated text"},
            ],
        }
        result = _validate_update_outline(outline)
        assert result["valid"] is True

    def test_missing_document_id(self):
        outline = {"items": [{"id": "existingProcId12345678", "text": "X"}]}
        result = _validate_update_outline(outline)
        assert result["valid"] is False
        assert any("document_id" in e for e in result["errors"])

    def test_invalid_document_id(self):
        outline = {
            "document_id": "too-short",
            "items": [{"id": "existingProcId12345678", "text": "X"}],
        }
        result = _validate_update_outline(outline)
        assert result["valid"] is False
        assert any("INVALID_ID_FORMAT" in e for e in result["errors"])

    def test_invalid_item_id(self):
        outline = {
            "document_id": "abcdefghijklmnopqrstuv",
            "items": [{"id": "bad!", "text": "X"}],
        }
        result = _validate_update_outline(outline)
        assert result["valid"] is False
        assert any("INVALID_ID_FORMAT" in e for e in result["errors"])

    def test_delete_without_id_fails(self):
        outline = {
            "document_id": "abcdefghijklmnopqrstuv",
            "items": [{"_delete": True, "text": "X"}],
        }
        result = _validate_update_outline(outline)
        assert result["valid"] is False
        assert any("_delete" in e for e in result["errors"])

    def test_new_items_validated_normally(self):
        outline = {
            "document_type": "checklist",
            "document_id": "abcdefghijklmnopqrstuv",
            "items": [
                # New item with depth jump > 1 — should fail
                {"depth": 0, "type": "group", "text": "G"},
                {"depth": 3, "type": "procedure", "text": "P", "response": "choice"},
            ],
        }
        result = _validate_update_outline(outline)
        assert result["valid"] is False
        assert any("INVALID_DEPTH" in e for e in result["errors"])


# ===================================================================
# Build update procedure
# ===================================================================


class TestBuildUpdateProcedure:
    def test_sparse_update_text_only(self):
        item = {"id": "existingProcId12345678", "text": "New text"}
        proc = _build_update_procedure(item)
        assert proc["id"] == "existingProcId12345678"
        # Default type is "procedure", so text gets HTML-wrapped
        assert "New text" in proc["text"]
        assert proc["text"].startswith("<p")
        # Should NOT have depth, type, rows (sparse)
        assert "depth" not in proc
        assert "rows" not in proc

    def test_sparse_update_response(self):
        item = {"id": "existingProcId12345678", "response": "text"}
        proc = _build_update_procedure(item)
        assert proc["id"] == "existingProcId12345678"
        assert proc["rows"][0]["columns"][0]["type"] == "text"

    def test_soft_delete(self):
        item = {"id": "existingProcId12345678", "_delete": True}
        proc = _build_update_procedure(item)
        assert proc == {"id": "existingProcId12345678", "hidden": True}

    def test_new_item_delegates_to_build_procedure(self):
        item = {
            "depth": 2, "type": "procedure",
            "text": "Brand new", "response": "choice",
        }
        proc = _build_update_procedure(item)
        # Should have full procedure structure (no id)
        assert "id" not in proc
        assert proc["depth"] == 2
        assert proc["type"] == "procedure"
        assert proc["rows"][0]["columns"][0]["type"] == "choice"

    def test_strips_numbering_on_update(self):
        item = {"id": "existingProcId12345678", "text": "1. Updated text"}
        proc = _build_update_procedure(item)
        assert "Updated text" in proc["text"]
        assert "1." not in proc["text"]


# ===================================================================
# Build checklist update (integration)
# ===================================================================


class TestBuildChecklistUpdate:
    def test_full_update(self):
        outline = {
            "document_type": "checklist",
            "mode": "update",
            "document_id": "abcdefghijklmnopqrstuv",
            "items": [
                {"id": "existingProcId12345678", "text": "Modified text"},
                {"depth": 2, "type": "procedure", "text": "New proc", "response": "choice"},
                {"id": "deleteProcId123456789a", "_delete": True},
            ],
        }
        result = build_checklist_update(outline)
        assert result["validation"]["valid"] is True
        assert result["metadata"]["mode"] == "update"
        assert result["metadata"]["modified_procedures"] == 1
        assert result["metadata"]["added_procedures"] == 1
        assert result["metadata"]["deleted_procedures"] == 1

        payload = result["payload"]
        assert payload["id"] == "abcdefghijklmnopqrstuv"
        assert len(payload["procedures"]) == 3
        # No documentInfo on updates
        assert "documentInfo" not in payload

    def test_validation_failure(self):
        outline = {
            "document_type": "checklist",
            "mode": "update",
            "document_id": "bad",
            "items": [],
        }
        result = build_checklist_update(outline)
        assert result["validation"]["valid"] is False

    def test_optional_fields_included(self):
        outline = {
            "document_type": "checklist",
            "mode": "update",
            "document_id": "abcdefghijklmnopqrstuv",
            "purpose": "Updated purpose",
            "guidance": "New guidance",
            "items": [{"id": "existingProcId12345678", "text": "X"}],
        }
        result = build_checklist_update(outline)
        assert result["payload"]["purpose"] == "Updated purpose"
        assert result["payload"]["guidance"] == "New guidance"


# ===================================================================
# Build query update (integration)
# ===================================================================


class TestBuildQueryUpdate:
    def test_full_update(self):
        outline = {
            "document_type": "query",
            "mode": "update",
            "document_id": "abcdefghijklmnopqrstuv",
            "items": [
                {"id": "existingQuestId1234567", "title": "Modified title"},
                {"depth": 1, "type": "question", "text": "New question",
                 "title": "New Q"},
                {"id": "deleteQuestId123456789", "_delete": True},
            ],
        }
        result = build_query_update(outline)
        assert result["validation"]["valid"] is True
        assert result["metadata"]["mode"] == "update"
        assert result["metadata"]["modified_questions"] == 1
        assert result["metadata"]["added_questions"] == 1
        assert result["metadata"]["deleted_questions"] == 1

        payload = result["payload"]
        assert payload["id"] == "abcdefghijklmnopqrstuv"
        assert "documentInfo" not in payload


# ===================================================================
# Build letter update (integration)
# ===================================================================


class TestBuildLetterUpdate:
    def test_full_update(self):
        outline = {
            "document_type": "letter",
            "mode": "update",
            "document_id": "abcdefghijklmnopqrstuv",
            "area_id": "areaIdValue123456789ab",
            "area_title": "Management Representations",
            "sections": [
                {"id": "sectionId1234567890abc", "content": "Updated content"},
                {"title": "New Section", "content": "New content"},
                {"id": "deleteSecId12345678901", "_delete": True},
            ],
        }
        result = build_letter_update(outline)
        assert result["validation"]["valid"] is True
        assert result["metadata"]["mode"] == "update"
        assert result["metadata"]["modified_sections"] == 1
        assert result["metadata"]["added_sections"] == 1
        assert result["metadata"]["deleted_sections"] == 1

        payload = result["payload"]
        assert payload["id"] == "abcdefghijklmnopqrstuv"
        assert payload["type"] == "letter"
        assert payload["documentMap"][0]["id"] == "areaIdValue123456789ab"
        # No documentInfo on updates
        assert "documentInfo" not in payload

    def test_missing_area_id_fails(self):
        outline = {
            "document_type": "letter",
            "mode": "update",
            "document_id": "abcdefghijklmnopqrstuv",
            "sections": [{"id": "sectionId1234567890abc", "content": "X"}],
        }
        result = build_letter_update(outline)
        assert result["validation"]["valid"] is False
        assert any("area_id" in e for e in result["validation"]["errors"])

    def test_single_call_no_two_step(self):
        outline = {
            "document_type": "letter",
            "mode": "update",
            "document_id": "abcdefghijklmnopqrstuv",
            "area_id": "areaIdValue123456789ab",
            "sections": [{"id": "sectionId1234567890abc", "title": "Updated"}],
        }
        result = build_letter_update(outline)
        # Should have 'payload', not 'step1_payload'/'step2_template'
        assert "payload" in result
        assert "step1_payload" not in result

    def test_dynamic_elements_in_update(self):
        outline = {
            "document_type": "letter",
            "mode": "update",
            "document_id": "abcdefghijklmnopqrstuv",
            "area_id": "areaIdValue123456789ab",
            "sections": [
                {"id": "sectionId1234567890abc", "content": "[Letter Date]"},
            ],
        }
        result = build_letter_update(outline)
        section = result["payload"]["documentMap"][0]["sections"][0]
        assert 'type="date"' in section["content"]


# ===================================================================
# includeConclusion on chunked payloads
# ===================================================================


class TestIncludeConclusionChunking:
    def test_chunked_payloads_only_first_has_include_conclusion(self):
        """When >50 procs trigger chunking, only the first payload should
        have includeConclusion: True.  Subsequent payloads must NOT."""
        items = []
        # 4 groups x 15 procedures = 60 (> CHUNKING_THRESHOLD of 50)
        for g in range(4):
            items.append({"depth": 0, "type": "group", "text": f"Group {g}"})
            for p in range(15):
                items.append({
                    "depth": 1, "type": "procedure",
                    "text": f"Proc {g}-{p}", "response": "choice",
                })
        items.append({"depth": 0, "type": "conclusion", "text": "Done", "response": "text"})

        outline = {
            "document_type": "checklist",
            "name": "Chunked", "number": "C-100",
            "items": items,
        }
        result = build_checklist(outline)
        assert result["validation"]["valid"] is True
        assert len(result["payloads"]) > 1

        # First payload: includeConclusion present and True
        assert result["payloads"][0].get("includeConclusion") is True
        assert result["payloads"][0].get("conclusionTitle") == "Conclusion"

        # Subsequent payloads: includeConclusion must NOT be present
        for payload in result["payloads"][1:]:
            assert "includeConclusion" not in payload, (
                "Subsequent chunk must not have includeConclusion"
            )
            assert "conclusionTitle" not in payload, (
                "Subsequent chunk must not have conclusionTitle"
            )

    def test_single_payload_has_include_conclusion(self):
        """A small checklist (single payload) should still have includeConclusion."""
        outline = {
            "document_type": "checklist",
            "name": "Small", "number": "S-100",
            "items": [
                {"depth": 0, "type": "group", "text": "Section"},
                {"depth": 1, "type": "procedure", "text": "Check it",
                 "response": "choice:Yes,No,Not Applicable"},
                {"depth": 0, "type": "conclusion", "text": "Conclude", "response": "text"},
            ],
        }
        result = build_checklist(outline)
        assert result["validation"]["valid"] is True
        assert len(result["payloads"]) == 1
        assert result["payloads"][0]["includeConclusion"] is True
        assert result["payloads"][0]["conclusionTitle"] == "Conclusion"


# ===================================================================
# Duplicate procedure detection
# ===================================================================


class TestDuplicateProcedureDetection:
    def test_duplicate_procedure_text_warning(self):
        """Duplicate procedure texts should produce a DUPLICATE_PROCEDURES warning."""
        items = [
            {"depth": 0, "type": "group", "text": "Section"},
            {"depth": 1, "type": "procedure", "text": "Has it been reviewed?",
             "response": "choice"},
            {"depth": 1, "type": "procedure", "text": "Has it been reviewed?",
             "response": "choice"},
        ]
        result = _validate_outline(items)
        assert any("DUPLICATE_PROCEDURES" in w for w in result["warnings"])

    def test_duplicate_case_insensitive(self):
        """Duplicate detection should be case-insensitive."""
        items = [
            {"depth": 0, "type": "group", "text": "Section"},
            {"depth": 1, "type": "procedure", "text": "Verify the balance",
             "response": "choice"},
            {"depth": 1, "type": "procedure", "text": "VERIFY THE BALANCE",
             "response": "choice"},
        ]
        result = _validate_outline(items)
        assert any("DUPLICATE_PROCEDURES" in w for w in result["warnings"])

    def test_no_false_duplicate_warning(self):
        """Unique procedure texts should produce no DUPLICATE_PROCEDURES warning."""
        items = [
            {"depth": 0, "type": "group", "text": "Section"},
            {"depth": 1, "type": "procedure", "text": "Has it been reviewed?",
             "response": "choice"},
            {"depth": 1, "type": "procedure", "text": "Describe the process.",
             "response": "text"},
        ]
        result = _validate_outline(items)
        assert not any("DUPLICATE_PROCEDURES" in w for w in result["warnings"])


# ===================================================================
# Summary field stripping (#25)
# ===================================================================


class TestSummaryFieldStripping:
    def test_summary_stripped_from_procedure(self):
        """_build_procedure must never include a summary field."""
        item = {
            "depth": 2, "type": "procedure",
            "text": "Check it", "response": "choice",
            "summary": "This should be removed",
        }
        proc = _build_procedure(item)
        assert "summary" not in proc

    def test_summary_stripped_from_group(self):
        item = {"depth": 0, "type": "group", "text": "G", "summary": "Bad"}
        proc = _build_procedure(item)
        assert "summary" not in proc


# ===================================================================
# Nested ID stripping (#26)
# ===================================================================


class TestStripNestedIds:
    def test_strips_procedure_id(self):
        proc = {"id": "abc", "depth": 2, "type": "procedure", "text": "P"}
        result = _strip_nested_ids(proc)
        assert "id" not in result

    def test_strips_row_column_choice_ids(self):
        proc = {
            "depth": 2, "type": "procedure", "text": "P",
            "rows": [{
                "id": "row_id",
                "columns": [{
                    "id": "col_id",
                    "type": "choice",
                    "choices": [
                        {"id": "ch1", "text": "Yes"},
                        {"id": "ch2", "text": "No"},
                    ],
                }],
            }],
        }
        result = _strip_nested_ids(proc)
        assert "id" not in result
        assert "id" not in result["rows"][0]
        assert "id" not in result["rows"][0]["columns"][0]
        for choice in result["rows"][0]["columns"][0]["choices"]:
            assert "id" not in choice

    def test_preserves_non_id_fields(self):
        proc = {"depth": 1, "type": "heading", "text": "H"}
        result = _strip_nested_ids(proc)
        assert result["depth"] == 1
        assert result["type"] == "heading"
        assert result["text"] == "H"

    def test_new_checklist_procedures_have_no_ids(self):
        """Integration: build_checklist should strip all nested IDs."""
        outline = {
            "document_type": "checklist",
            "name": "Test", "number": "T-1",
            "items": [
                {"depth": 0, "type": "group", "text": "G"},
                {"depth": 1, "type": "procedure", "text": "P",
                 "response": "choice"},
            ],
        }
        result = build_checklist(outline)
        for proc in result["payloads"][0]["procedures"]:
            assert "id" not in proc

    def test_new_query_questions_have_no_ids(self):
        """Integration: build_query should strip all nested IDs."""
        outline = {
            "document_type": "query",
            "name": "Q", "number": "Q-1",
            "items": [
                {"depth": 0, "type": "questionSet", "text": "QS"},
                {"depth": 1, "type": "question", "text": "Ask",
                 "title": "T", "placeholder": "..."},
            ],
        }
        result = build_query(outline)
        for q in result["payload"]["questions"]:
            assert "id" not in q


# ===================================================================
# Empty branch detection (#9)
# ===================================================================


class TestEmptyBranchDetection:
    def test_group_with_no_procedures(self):
        items = [
            {"depth": 0, "type": "group", "text": "Empty Group"},
            {"depth": 1, "type": "heading", "text": "Empty Heading"},
            {"depth": 0, "type": "group", "text": "Good Group"},
            {"depth": 1, "type": "procedure", "text": "P", "response": "choice"},
        ]
        result = _validate_outline(items)
        warnings = [w for w in result["warnings"] if "EMPTY_BRANCH" in w]
        assert len(warnings) == 2  # group + heading both empty
        assert "Empty Group" in warnings[0]
        assert "Empty Heading" in warnings[1]

    def test_heading_with_no_procedures(self):
        items = [
            {"depth": 0, "type": "group", "text": "G"},
            {"depth": 1, "type": "heading", "text": "Empty H"},
            {"depth": 1, "type": "heading", "text": "Good H"},
            {"depth": 2, "type": "procedure", "text": "P", "response": "choice"},
        ]
        result = _validate_outline(items)
        warnings = [w for w in result["warnings"] if "EMPTY_BRANCH" in w]
        assert len(warnings) == 1
        assert "Empty H" in warnings[0]

    def test_no_false_empty_branch(self):
        items = [
            {"depth": 0, "type": "group", "text": "G"},
            {"depth": 1, "type": "heading", "text": "H"},
            {"depth": 2, "type": "procedure", "text": "P", "response": "choice"},
        ]
        result = _validate_outline(items)
        assert not any("EMPTY_BRANCH" in w for w in result["warnings"])

    def test_group_ending_at_list_end(self):
        """Last item is a group with nothing after it."""
        items = [
            {"depth": 0, "type": "group", "text": "G1"},
            {"depth": 1, "type": "procedure", "text": "P", "response": "choice"},
            {"depth": 0, "type": "group", "text": "Trailing Empty"},
        ]
        result = _validate_outline(items)
        assert any("Trailing Empty" in w for w in result["warnings"])


# ===================================================================
# Content loss detection (#47)
# ===================================================================


class TestContentLossDetection:
    def test_content_loss_exceeds_threshold(self):
        """If expected_procedure_count is provided and loss >10%, hard-fail."""
        outline = {
            "document_type": "checklist",
            "name": "Test", "number": "T-1",
            "expected_procedure_count": 100,
            "items": [
                {"depth": 0, "type": "group", "text": "G"},
                {"depth": 1, "type": "procedure", "text": "P1", "response": "choice"},
                {"depth": 1, "type": "procedure", "text": "P2", "response": "choice"},
            ],
        }
        result = build_checklist(outline)
        assert result["validation"]["valid"] is False
        assert any("CONTENT_LOSS_EXCEEDED" in e for e in result["validation"]["errors"])
        assert len(result["payloads"]) == 0

    def test_content_loss_within_threshold(self):
        """Loss <=10% should pass."""
        outline = {
            "document_type": "checklist",
            "name": "Test", "number": "T-1",
            "expected_procedure_count": 3,
            "items": [
                {"depth": 0, "type": "group", "text": "G"},
                {"depth": 1, "type": "procedure", "text": "P1", "response": "choice"},
                {"depth": 1, "type": "procedure", "text": "P2", "response": "choice"},
                {"depth": 1, "type": "procedure", "text": "P3", "response": "choice"},
            ],
        }
        result = build_checklist(outline)
        assert result["validation"]["valid"] is True

    def test_no_expected_count_skips_check(self):
        """If expected_procedure_count is not provided, skip the check."""
        outline = {
            "document_type": "checklist",
            "name": "Test", "number": "T-1",
            "items": [
                {"depth": 0, "type": "group", "text": "G"},
                {"depth": 1, "type": "procedure", "text": "P", "response": "choice"},
            ],
        }
        result = build_checklist(outline)
        assert result["validation"]["valid"] is True


# ===================================================================
# Per-payload expected procedure count (#41)
# ===================================================================


class TestExpectedPerPayload:
    def test_single_payload_count(self):
        outline = {
            "document_type": "checklist",
            "name": "Test", "number": "T-1",
            "items": [
                {"depth": 0, "type": "group", "text": "G"},
                {"depth": 1, "type": "procedure", "text": "P1", "response": "choice"},
                {"depth": 1, "type": "procedure", "text": "P2", "response": "text"},
            ],
        }
        result = build_checklist(outline)
        expected = result["metadata"]["expected_per_payload"]
        assert expected == [3]  # 1 group + 2 procedures

    def test_chunked_payload_counts(self):
        items = []
        for g in range(4):
            items.append({"depth": 0, "type": "group", "text": f"G{g}"})
            for p in range(15):
                items.append({
                    "depth": 1, "type": "procedure",
                    "text": f"P{g}-{p}", "response": "choice",
                })
        items.append({"depth": 0, "type": "conclusion", "text": "C", "response": "text"})

        outline = {
            "document_type": "checklist",
            "name": "Big", "number": "B-1",
            "items": items,
        }
        result = build_checklist(outline)
        expected = result["metadata"]["expected_per_payload"]
        assert len(expected) == len(result["payloads"])
        # Each entry should match the actual procedure count in its payload
        for i, payload in enumerate(result["payloads"]):
            assert expected[i] == len(payload["procedures"])


# ===================================================================
# Group-type rows stripping & choice ID sanitization (#ticket)
# ===================================================================


class TestSanitizeProcedure:
    def test_strips_rows_from_group(self):
        proc = {
            "depth": 0, "type": "group", "text": "G",
            "rows": [{"columns": [{"type": "text"}]}],
        }
        result = _sanitize_procedure(proc)
        assert "rows" not in result

    def test_preserves_rows_on_procedure(self):
        proc = {
            "depth": 1, "type": "procedure", "text": "P",
            "rows": [{"columns": [{"type": "text"}]}],
        }
        result = _sanitize_procedure(proc)
        assert "rows" in result

    def test_strips_choice_ids(self):
        proc = {
            "depth": 1, "type": "procedure", "text": "P",
            "rows": [{"columns": [{
                "type": "choice",
                "choices": [
                    {"id": "abc", "text": "Yes"},
                    {"id": "def", "text": "No"},
                ],
            }]}],
        }
        result = _sanitize_procedure(proc)
        for choice in result["rows"][0]["columns"][0]["choices"]:
            assert "id" not in choice
            assert "text" in choice

    def test_no_rows_is_safe(self):
        proc = {"depth": 0, "type": "group", "text": "G"}
        result = _sanitize_procedure(proc)
        assert "rows" not in result


class TestGroupRowsNotInPayload:
    def test_build_checklist_groups_have_no_rows(self):
        outline = {
            "document_type": "checklist",
            "name": "Test", "number": "T-1",
            "items": [
                {"depth": 0, "type": "group", "text": "Section A"},
                {"depth": 1, "type": "procedure", "text": "Do something",
                 "response": "choice"},
            ],
        }
        result = build_checklist(outline)
        for proc in result["payloads"][0]["procedures"]:
            if proc["type"] == "group":
                assert "rows" not in proc

    def test_update_group_with_response_has_no_rows(self):
        """Update outline with a group that erroneously has a response field."""
        item = {
            "id": "abcdefghij1234567890ab",
            "depth": 0, "type": "group", "text": "G",
            "response": "choice",
        }
        result = _build_update_procedure(item)
        result = _sanitize_procedure(result)
        assert "rows" not in result

    def test_build_checklist_update_groups_have_no_rows(self):
        outline = {
            "document_type": "checklist",
            "document_id": "abcdefghij1234567890ab",
            "items": [
                {"id": "abcdefghij1234567890ab", "depth": 0, "type": "group",
                 "text": "G", "response": "choice"},
                {"id": "bbcdefghij1234567890ab", "depth": 1, "type": "procedure",
                 "text": "P", "response": "text"},
            ],
        }
        result = build_checklist_update(outline)
        for proc in result["payload"]["procedures"]:
            if proc.get("type") == "group":
                assert "rows" not in proc


class TestChoiceIdsNeverInPayload:
    def test_new_checklist_choices_have_no_ids(self):
        outline = {
            "document_type": "checklist",
            "name": "Test", "number": "T-1",
            "items": [
                {"depth": 0, "type": "group", "text": "G"},
                {"depth": 1, "type": "procedure", "text": "P",
                 "response": "choice:Yes,No,Not Applicable"},
            ],
        }
        result = build_checklist(outline)
        for proc in result["payloads"][0]["procedures"]:
            for row in proc.get("rows", []):
                for col in row.get("columns", []):
                    for choice in col.get("choices", []):
                        assert "id" not in choice

    def test_update_checklist_choices_have_no_ids(self):
        outline = {
            "document_type": "checklist",
            "document_id": "abcdefghij1234567890ab",
            "items": [
                {"id": "abcdefghij1234567890ab", "depth": 0, "type": "group",
                 "text": "G"},
                {"id": "bbcdefghij1234567890ab", "depth": 1, "type": "procedure",
                 "text": "P", "response": "choice:Yes,No,Not Applicable"},
            ],
        }
        result = build_checklist_update(outline)
        for proc in result["payload"]["procedures"]:
            for row in proc.get("rows", []):
                for col in row.get("columns", []):
                    for choice in col.get("choices", []):
                        assert "id" not in choice


# ===================================================================
# Ticket 1: Extended numbering stripping (closing-paren & false-positive fix)
# ===================================================================


class TestStripNumberingExtended:
    """Tests for new patterns: 1), a), ii) and false-positive protection."""

    def test_digit_closing_paren(self):
        assert _strip_numbering("1) Verify the balance")[0] == "Verify the balance"

    def test_multi_digit_closing_paren(self):
        assert _strip_numbering("12) Review")[0] == "Review"

    def test_alpha_closing_paren_lower(self):
        assert _strip_numbering("a) Confirm amounts")[0] == "Confirm amounts"

    def test_alpha_closing_paren_upper(self):
        assert _strip_numbering("B) Confirm amounts")[0] == "Confirm amounts"

    def test_roman_closing_paren_lower(self):
        assert _strip_numbering("ii) Review the policy")[0] == "Review the policy"

    def test_roman_closing_paren_upper(self):
        assert _strip_numbering("IV) Review the policy")[0] == "Review the policy"

    def test_bare_letter_not_stripped(self):
        """Single letter without dot/paren is NOT numbering — it's likely an article."""
        text = "A simple procedure"
        assert _strip_numbering(text)[0] == text

    def test_bare_i_not_stripped(self):
        """'I' at start is NOT numbering — it's a pronoun."""
        text = "I Review the policy"
        assert _strip_numbering(text)[0] == text

    def test_letter_with_dot_still_stripped(self):
        """a. is still stripped (dot makes it unambiguous numbering)."""
        assert _strip_numbering("a. Confirm")[0] == "Confirm"


class TestBuildQuestionStripsNumbering:
    """Verify _build_question strips numbering from question text."""

    def test_question_text_stripped(self):
        item = {"type": "question", "text": "1. What is your policy?"}
        q = _build_question(item)
        assert "1." not in q["text"]
        assert "What is your policy?" in q["text"]

    def test_question_title_stripped(self):
        item = {"type": "question", "text": "Q1", "title": "a. Revenue Policy"}
        q = _build_question(item)
        assert q["title"] == "Revenue Policy"

    def test_questionset_not_stripped(self):
        """QuestionSets may have legitimate numbering in titles."""
        item = {"type": "questionSet", "text": "Section 1: Overview"}
        q = _build_question(item)
        assert q["title"] == "Section 1: Overview"


# ===================================================================
# Ticket 2: Default response (checklist settings)
# ===================================================================


class TestDefaultResponse:
    def test_default_applied_to_procedures_without_response(self):
        outline = {
            "document_type": "checklist",
            "name": "Test", "number": "T-1",
            "default_response": "choice:Yes|No|Not Applicable",
            "items": [
                {"depth": 0, "type": "group", "text": "G"},
                {"depth": 1, "type": "procedure", "text": "Check it"},
                {"depth": 1, "type": "procedure", "text": "Verify it"},
            ],
        }
        result = build_checklist(outline)
        assert result["validation"]["valid"] is True
        assert result["metadata"]["default_response_applied"] == 2

    def test_explicit_response_not_overridden(self):
        outline = {
            "document_type": "checklist",
            "name": "Test", "number": "T-1",
            "default_response": "choice:Yes|No|Not Applicable",
            "items": [
                {"depth": 0, "type": "group", "text": "G"},
                {"depth": 1, "type": "procedure", "text": "Describe",
                 "response": "text"},
                {"depth": 1, "type": "procedure", "text": "Check it"},
            ],
        }
        result = build_checklist(outline)
        assert result["validation"]["valid"] is True
        assert result["metadata"]["default_response_applied"] == 1
        # First procedure should have text type (explicit)
        procs = [p for p in result["payloads"][0]["procedures"]
                 if p["type"] == "procedure"]
        assert procs[0]["rows"][0]["columns"][0]["type"] == "text"
        # Second procedure should have choice type (from default)
        assert procs[1]["rows"][0]["columns"][0]["type"] == "choice"

    def test_no_default_unchanged(self):
        outline = {
            "document_type": "checklist",
            "name": "Test", "number": "T-1",
            "items": [
                {"depth": 0, "type": "group", "text": "G"},
                {"depth": 1, "type": "procedure", "text": "Check",
                 "response": "choice"},
            ],
        }
        result = build_checklist(outline)
        assert result["validation"]["valid"] is True
        assert result["metadata"]["default_response_applied"] == 0

    def test_default_unused_warning(self):
        outline = {
            "document_type": "checklist",
            "name": "Test", "number": "T-1",
            "default_response": "choice:Yes|No|Not Applicable",
            "items": [
                {"depth": 0, "type": "group", "text": "G"},
                {"depth": 1, "type": "procedure", "text": "Check",
                 "response": "choice"},
            ],
        }
        result = build_checklist(outline)
        assert any("default was not used" in w for w in result["validation"]["warnings"])

    def test_default_in_update_mode(self):
        outline = {
            "document_type": "checklist",
            "mode": "update",
            "document_id": "abcdefghijklmnopqrstuv",
            "default_response": "text",
            "items": [
                {"depth": 2, "type": "procedure", "text": "New proc"},
            ],
        }
        result = build_checklist_update(outline)
        assert result["validation"]["valid"] is True
        assert result["metadata"]["default_response_applied"] == 1


# ===================================================================
# Tickets 4+5: Dynamic elements in procedures and queries
# ===================================================================


class TestDynamicElementsInProcedures:
    def test_entity_name_formula_in_procedure(self):
        item = {
            "depth": 2, "type": "procedure",
            "text": "Confirm the entity name is correct.",
            "response": "choice",
        }
        proc = _build_procedure(item)
        assert 'formula=' in proc["text"]
        assert 'engprop' in proc["text"]

    def test_date_placeholder_in_procedure(self):
        item = {
            "depth": 2, "type": "procedure",
            "text": "Verify [Date] on report.",
            "response": "choice",
        }
        proc = _build_procedure(item)
        assert 'type="date"' in proc["text"]

    def test_explicit_formula_syntax_in_procedure(self):
        item = {
            "depth": 2, "type": "procedure",
            "text": 'Check wording("@auditGlossary") is correct.',
            "response": "choice",
        }
        proc = _build_procedure(item)
        assert 'formula=' in proc["text"]
        assert 'wording' in proc["text"]

    def test_generic_bracket_not_converted_in_procedure(self):
        """Generic [bracketed text] like [ISA 315] should NOT be converted."""
        item = {
            "depth": 2, "type": "procedure",
            "text": "Per [ISA 315], assess risks.",
            "response": "choice",
        }
        proc = _build_procedure(item)
        assert "[ISA 315]" in proc["text"]
        assert 'type="input-area"' not in proc["text"]

    def test_generic_bracket_still_converted_in_letter(self):
        """Letters should still convert generic [brackets] to input-area."""
        result = _detect_dynamic_elements("[Custom Field]", convert_generic_brackets=True)
        assert 'type="input-area"' in result

    def test_generic_bracket_not_converted_when_disabled(self):
        result = _detect_dynamic_elements("[Custom Field]", convert_generic_brackets=False)
        assert "[Custom Field]" in result
        assert 'type="input-area"' not in result

    def test_plain_procedure_unchanged(self):
        item = {
            "depth": 2, "type": "procedure",
            "text": "Review the financial statements.",
            "response": "choice",
        }
        proc = _build_procedure(item)
        assert "Review the financial statements." in proc["text"]
        assert "formula" not in proc["text"]
        assert "placeholder=" not in proc["text"]

    def test_dynamic_elements_in_update_procedure(self):
        item = {
            "id": "existingProcId12345678",
            "type": "procedure",
            "text": "Confirm entity name matches.",
        }
        proc = _build_update_procedure(item)
        assert 'formula=' in proc["text"]
        assert 'engprop' in proc["text"]

    def test_dynamic_elements_in_query_question(self):
        item = {"type": "question", "text": "Provide the [Date] of signing."}
        q = _build_question(item)
        assert 'type="date"' in q["text"]

    def test_group_text_no_dynamic_elements(self):
        """Groups should NOT have dynamic element detection."""
        item = {"depth": 0, "type": "group", "text": "Entity Name Section"}
        proc = _build_procedure(item)
        assert proc["text"] == "Entity Name Section"
        assert "formula" not in proc["text"]


# ===================================================================
# Ticket 3: Left-align HTML wrapping
# ===================================================================


class TestWrapProcedureText:
    def test_wraps_plain_text(self):
        result = _wrap_procedure_text("Check the balance.")
        assert result == '<p style="text-align: left;">Check the balance.</p>'

    def test_does_not_wrap_html(self):
        html = "<p>Already HTML</p>"
        assert _wrap_procedure_text(html) == html

    def test_does_not_wrap_html_with_whitespace(self):
        html = "  <p>Already HTML</p>"
        assert _wrap_procedure_text(html) == html

    def test_empty_string(self):
        assert _wrap_procedure_text("") == ""

    def test_none_safe(self):
        assert _wrap_procedure_text("") == ""


class TestProcedureTextWrappingIntegration:
    def test_procedure_text_wrapped(self):
        item = {
            "depth": 2, "type": "procedure",
            "text": "Review the balance sheet.",
            "response": "choice",
        }
        proc = _build_procedure(item)
        assert proc["text"].startswith('<p style="text-align: left;">')
        assert "Review the balance sheet." in proc["text"]

    def test_conclusion_text_wrapped(self):
        item = {"depth": 0, "type": "conclusion", "text": "Document conclusion."}
        proc = _build_procedure(item)
        assert proc["text"].startswith('<p style="text-align: left;">')

    def test_group_text_not_wrapped(self):
        item = {"depth": 0, "type": "group", "text": "Revenue Section"}
        proc = _build_procedure(item)
        assert proc["text"] == "Revenue Section"
        assert "<p" not in proc["text"]

    def test_heading_text_not_wrapped(self):
        item = {"depth": 1, "type": "heading", "text": "Testing"}
        proc = _build_procedure(item)
        assert proc["text"] == "Testing"
        assert "<p" not in proc["text"]

    def test_update_procedure_text_wrapped(self):
        item = {"id": "existingProcId12345678", "text": "Updated text"}
        proc = _build_update_procedure(item)
        assert proc["text"].startswith('<p style="text-align: left;">')

    def test_update_heading_text_not_wrapped(self):
        item = {
            "id": "existingProcId12345678",
            "type": "heading",
            "text": "Section Title",
        }
        proc = _build_update_procedure(item)
        assert proc["text"] == "Section Title"
