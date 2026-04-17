"""Document text extraction — extracts text content from PDF, Word, Excel, PowerPoint.

Markers ([D0]-[D4], [R], [C], [G]) are NOT applied here; the LLM applies
them during structure analysis.
"""

import re
from pathlib import Path

# Confidence thresholds
CONFIDENCE_DOCTYPE_THRESHOLD = 0.7

# Document types
DOCTYPE_CHECKLIST = "checklist"
DOCTYPE_LETTER = "letter"
DOCTYPE_QUERY = "query"
DOCTYPE_AMBIGUOUS = "ambiguous"
DOCTYPE_UNKNOWN = "unknown"

# Supported file extensions
SUPPORTED_EXTENSIONS = {
    ".pdf": "PDF documents",
    ".docx": "Word documents (modern)",
    ".doc": "Word documents (legacy)",
    ".xlsx": "Excel spreadsheets (modern)",
    ".xls": "Excel spreadsheets (legacy)",
    ".pptx": "PowerPoint presentations",
}


def check_markitdown_installed() -> bool:
    """Check if markitdown library is available."""
    try:
        from markitdown import MarkItDown  # noqa: F401
        return True
    except ImportError:
        return False


def convert_file(file_path: Path) -> str:
    """Extract text content from a file using markitdown.

    Returns:
        Extracted text content.

    Raises:
        ImportError: If markitdown is not installed.
    """
    from markitdown import MarkItDown

    md = MarkItDown()
    result = md.convert(str(file_path))
    return result.text_content


def detect_document_type(text: str) -> dict:
    """Detect whether document is a checklist, letter, query, or unknown.

    Returns:
        Dictionary with type, confidence, and indicators.
    """
    indicators: list[str] = []
    letter_score = 0.0
    checklist_score = 0.0
    query_score = 0.0

    text_lower = text.lower()
    lines = text.split("\n")

    # Letter indicators
    letter_patterns = [
        (r"\bdear\s+", "salutation_found", 0.2),
        (r"\bsincerely\b", "closing_sincerely", 0.15),
        (r"\byours\s+(truly|faithfully)\b", "closing_yours", 0.15),
        (r"\bkind\s+regards\b", "closing_regards", 0.1),
        (r"\bengagement\s+letter\b", "engagement_letter_title", 0.25),
        (r"\bwe\s+(are\s+pleased|confirm)\b", "letter_opening", 0.1),
        (r"\bplease\s+sign\s+and\s+return\b", "signature_request", 0.15),
        (r"\btext\s+area\s*[-–]\s*", "text_area_section", 0.1),
        (r"\bin\s+connection\s+with\s+your\b", "representation_opening", 0.2),
        (r"\bwe\s+make\s+the\s+following\s+representations?\b", "representation_statement", 0.25),
        (r"\bto\s+the\s+best\s+of\s+our\s+knowledge\s+and\s+belief\b", "knowledge_belief", 0.2),
        (r"\bwe\s+acknowledge\s+that\b", "acknowledgment_statement", 0.15),
        (r"\bwe\s+have\s+(disclosed|provided|made\s+available)\b", "disclosure_statement", 0.15),
        (r"\bwe\s+are\s+responsible\s+for\b", "responsibility_statement", 0.15),
        (r"\battached\s+hereto\b", "attachment_reference", 0.1),
        (r"\bexhibit\s+[a-z]\b", "exhibit_reference", 0.1),
        (r"^[A-Z][A-Za-z\s,\.]+\n\[?address\]?", "addressee_block", 0.15),
        (r"\battestation\s+engagement\b", "attestation_engagement", 0.2),
        (r"\bcompliance\s+(with|attestation)\b", "compliance_reference", 0.15),
        (r"\bmanagement\s*('s)?\s+representation\b", "management_rep_title", 0.25),
        (r"\bwritten\s+representations?\b", "written_representation", 0.15),
    ]

    for pattern, indicator, score in letter_patterns:
        if re.search(pattern, text_lower):
            indicators.append(indicator)
            letter_score += score

    # Footnote back-references (common in Caseware letters)
    footnote_refs = len(re.findall(r"\[\[\d+\]\]\(#footnote-\d+\)", text))
    if footnote_refs > 10:
        indicators.append("many_footnote_refs")
        letter_score += 0.15

    # Query indicators
    query_patterns = [
        (r"\b(please\s+provide|kindly\s+provide)\b", "client_request_language", 0.20),
        (r"\binformation\s+request\b", "information_request", 0.25),
        (r"\bupload\s+(the\s+)?following\b", "file_upload_request", 0.20),
        (r"\bprovide\s+(a\s+)?copy\b", "document_request", 0.15),
        (r"\bquestion(s)?\s*:", "question_format", 0.15),
        (r"\bclient\s+response\b", "client_response", 0.20),
        (r"\bsupporting\s+documentation\b", "supporting_docs", 0.15),
        (r"\bplease\s+(describe|explain|list)\b", "query_verbs", 0.15),
    ]

    for pattern, indicator, score in query_patterns:
        if re.search(pattern, text_lower):
            indicators.append(indicator)
            query_score += score

    # Checklist indicators
    checklist_patterns = [
        (r"\bprocedure\s*(number|#)?\b", "procedure_column", 0.2),
        (r"\byes\s*/\s*no\s*/\s*(n/?a|not\s+applicable)\b", "yes_no_response", 0.25),
        (r"^\s*isa\s+\d{3}\s*$", "isa_column_header", 0.15),
        (r"\bresponse\s*(type|option)?\b", "response_column", 0.1),
        (r"\bstep\s*\d+", "step_numbering", 0.15),
        (r"\btask\s*\d+", "task_numbering", 0.1),
        (r"\bwork\s*paper\s*ref", "workpaper_reference", 0.15),
        (r"\bprepared\s*by.*reviewed\s*by", "audit_signoff", 0.2),
        (r"\bassertions?\s*:?\s*(existence|completeness|accuracy|valuation|rights|obligations|presentation)", "audit_assertions", 0.2),
        (r"\b(complete|completed|done)\s*[☐☑✓✗□■]", "checkbox_response", 0.2),
        (r"\bconclusion\s*(and|&)?\s*sign-?off", "conclusion_signoff", 0.2),
        (r"\boverall\s+conclusion", "overall_conclusion", 0.15),
        (r"\bcontrol\s+(testing|evaluation|deficienc)", "control_testing", 0.15),
    ]

    for pattern, indicator, score in checklist_patterns:
        if re.search(pattern, text_lower):
            indicators.append(indicator)
            checklist_score += score

    # Structural analysis
    numbered_items = len(re.findall(r"^\s*\d{1,3}\.\s+", text, re.MULTILINE))
    lettered_items = len(re.findall(r"^\s*[a-z]\.\s+", text, re.MULTILINE))
    prose_paragraphs = len([
        l for l in lines
        if len(l.strip()) > 100 and not l.strip().startswith(("|", "#", "*", "-"))
    ])

    if numbered_items > 20 and lettered_items > 10:
        indicators.append("many_numbered_lettered_items")
        checklist_score += 0.2

    if prose_paragraphs > 10 and numbered_items < prose_paragraphs:
        indicators.append("prose_heavy")
        letter_score += 0.15

    # Determine type
    total_score = letter_score + checklist_score + query_score
    if total_score == 0:
        return {"type": DOCTYPE_UNKNOWN, "confidence": 0.0, "indicators": indicators}

    letter_confidence = letter_score / max(total_score, 0.01)
    checklist_confidence = checklist_score / max(total_score, 0.01)
    query_confidence = query_score / max(total_score, 0.01)

    scores = {
        DOCTYPE_LETTER: (letter_score, letter_confidence),
        DOCTYPE_CHECKLIST: (checklist_score, checklist_confidence),
        DOCTYPE_QUERY: (query_score, query_confidence),
    }
    best_type = max(scores, key=lambda x: scores[x][0])
    max_confidence = max(letter_confidence, checklist_confidence, query_confidence)

    # Check for ambiguity
    score_values = [letter_score, checklist_score, query_score]
    sorted_scores = sorted(score_values, reverse=True)
    if sorted_scores[0] > 0 and sorted_scores[1] > 0:
        ratio = sorted_scores[1] / sorted_scores[0]
        if ratio > 0.7:
            return {
                "type": DOCTYPE_AMBIGUOUS,
                "confidence": max_confidence,
                "indicators": indicators,
                "requires_manual_review": True,
                "review_reason": (
                    f"Document has mixed signals: letter={letter_score:.2f}, "
                    f"checklist={checklist_score:.2f}, query={query_score:.2f}"
                ),
            }

    _, best_confidence = scores[best_type]
    if best_confidence >= CONFIDENCE_DOCTYPE_THRESHOLD:
        return {
            "type": best_type,
            "confidence": min(best_confidence, 0.95),
            "indicators": indicators,
        }
    return {"type": DOCTYPE_UNKNOWN, "confidence": max_confidence, "indicators": indicators}


def convert_single_file(file_path: str) -> dict:
    """Extract text content from a single file with type detection.

    Args:
        file_path: Absolute path to the file.

    Returns:
        Result dict with text content, document_type, etc.
    """
    path = Path(file_path).resolve()
    if not path.exists():
        return {"success": False, "error": f"File not found: {path}"}
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return {
            "success": False,
            "error": f"Unsupported file type: {path.suffix}",
            "supported": list(SUPPORTED_EXTENSIONS.keys()),
        }

    markdown_text = convert_file(path)
    doc_type_info = detect_document_type(markdown_text)

    output_path = path.with_suffix(".md")
    output_path.write_text(markdown_text, encoding="utf-8")

    return {
        "success": True,
        "file": str(path),
        "output_file": str(output_path),
        "markdown_text": markdown_text,
        "document_type": doc_type_info.get("type", DOCTYPE_UNKNOWN),
        "detection_confidence": doc_type_info.get("confidence", 0.0),
        "detection_indicators": doc_type_info.get("indicators", []),
    }


def batch_convert(folder_path: str, recursive: bool = False) -> dict:
    """Batch convert all supported files in a folder.

    Args:
        folder_path: Absolute path to the folder.
        recursive: Whether to recurse into subfolders.

    Returns:
        Result dict with per-file results.
    """
    path = Path(folder_path).resolve()
    if not path.exists():
        return {"success": False, "error": f"Folder not found: {path}"}
    if not path.is_dir():
        return {"success": False, "error": f"Not a directory: {path}"}

    files = []
    for ext in SUPPORTED_EXTENSIONS:
        if recursive:
            files.extend(path.rglob(f"*{ext}"))
        else:
            files.extend(path.glob(f"*{ext}"))
    files = sorted(set(files))

    if not files:
        return {
            "success": True,
            "message": "No supported files found",
            "folder": str(path),
            "files_processed": 0,
        }

    results = []
    success_count = 0
    for f in files:
        r = convert_single_file(str(f))
        r.pop("markdown_text", None)
        results.append(r)
        if r.get("success"):
            success_count += 1

    return {
        "success": success_count == len(files),
        "folder": str(path),
        "files_processed": len(files),
        "success_count": success_count,
        "error_count": len(files) - success_count,
        "results": results,
    }
