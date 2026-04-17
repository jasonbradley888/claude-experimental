"""Template analysis and export tools — cross-platform, no COM dependency.

This module provides tools for analyzing and extracting .cwp template packages:

- analyze_template_package: Overview of package structure and templates
- get_package_manifest: Every field in manifest.xml + full <File> inventory with MD5
- get_file_inventory: Every inner-zip file, grouped by category (style, doc, db, image, ...)
- list_template_cells: Cell/field names for a specific template
- search_template_cells: Regex search across all template cells
- get_template_structure: OLE2 structural metadata for a template
- get_document_outline: Structured bookmarks + sections + paragraph index
- export_template_cells: Export cell inventory to JSON/CSV
- export_template_structure: Full per-template structural dump
- export_full_package: One-shot comprehensive extraction

Standalone .cvw tools: analyze_cvw_file, list_cvw_cells, get_cvw_structure,
get_cvw_document_outline, export_cvw_file.

These tools work on Mac, Linux, and Windows — no Working Papers installation required.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp.types import Tool

from .cwp_reader import CvwReader, CwpReader
from .errors import with_error_handling
from .export import (
    export_full_package,
    export_template_cells,
    export_template_structure,
)

# === Tool Definitions ===

TOOLS: list[Tool] = [
    Tool(
        name="analyze_template_package",
        description="""Analyze a .cwp template package and return structure overview.

Opens a CaseWare Working Papers template package (.cwp) and lists all
CaseView templates with their codes and cell counts. Works offline —
no Working Papers installation required.

Args:
    cwp_path: Full path to the .cwp template file

Returns:
    Package metadata and list of all templates

Example:
    analyze_template_package(cwp_path="~/Templates/Frazier-Deeter.cwp")
""",
        inputSchema={
            "type": "object",
            "properties": {
                "cwp_path": {
                    "type": "string",
                    "description": "Full path to the .cwp template file",
                },
            },
            "required": ["cwp_path"],
        },
    ),
    Tool(
        name="list_template_cells",
        description="""Get all cell/field names for a specific template in a .cwp package.

Extracts cell names from the template's OLE2 Index/Cell stream. These are
the dynamic field names used in the CaseView document (e.g., CONTACT1,
COMPANYNA, ISSUEDATE1). Works offline — no Working Papers required.

Requires olefile: pip install cwp-template-reader[olefile]

Args:
    cwp_path: Full path to the .cwp template file
    template_code: Template code (e.g., "ENGL", "FRAUD", "MRL")

Returns:
    Cell names, count, and prefix analysis

Example:
    list_template_cells(cwp_path="~/Templates/Frazier-Deeter.cwp", template_code="ENGL")
""",
        inputSchema={
            "type": "object",
            "properties": {
                "cwp_path": {
                    "type": "string",
                    "description": "Full path to the .cwp template file",
                },
                "template_code": {
                    "type": "string",
                    "description": "Template code (e.g., 'ENGL', 'FRAUD', 'MRL')",
                },
            },
            "required": ["cwp_path", "template_code"],
        },
    ),
    Tool(
        name="search_template_cells",
        description="""Search for cells matching a pattern across all templates in a .cwp package.

Searches cell names using a regex pattern. Useful for finding which templates
reference a particular field (e.g., "COMPANY" to find all templates that use
the company name). Works offline — no Working Papers required.

Requires olefile: pip install cwp-template-reader[olefile]

Args:
    cwp_path: Full path to the .cwp template file
    pattern: Regex pattern to match against cell names

Returns:
    List of matching cells with their template codes

Example:
    search_template_cells(cwp_path="...", pattern="COMPANY")
    search_template_cells(cwp_path="...", pattern="^pp")
""",
        inputSchema={
            "type": "object",
            "properties": {
                "cwp_path": {
                    "type": "string",
                    "description": "Full path to the .cwp template file",
                },
                "pattern": {
                    "type": "string",
                    "description": "Regex pattern to match against cell names",
                },
            },
            "required": ["cwp_path", "pattern"],
        },
    ),
    Tool(
        name="get_template_structure",
        description="""Get structural metadata for a specific template in a .cwp package.

Returns OLE2 stream sizes, bookmarks, and cell count for the template.
Useful for understanding the internal structure of a CaseView document.
Works offline — no Working Papers required.

Requires olefile: pip install cwp-template-reader[olefile]

Args:
    cwp_path: Full path to the .cwp template file
    template_code: Template code (e.g., "ENGL", "FRAUD")

Returns:
    Stream sizes, bookmarks, cell count

Example:
    get_template_structure(cwp_path="...", template_code="ENGL")
""",
        inputSchema={
            "type": "object",
            "properties": {
                "cwp_path": {
                    "type": "string",
                    "description": "Full path to the .cwp template file",
                },
                "template_code": {
                    "type": "string",
                    "description": "Template code (e.g., 'ENGL', 'FRAUD')",
                },
            },
            "required": ["cwp_path", "template_code"],
        },
    ),
    Tool(
        name="get_package_manifest",
        description="""Return the complete manifest.xml content for a .cwp package.

Unlike analyze_template_package (which only surfaces 6 common fields), this
tool returns every element in the manifest — packager flags, branding
(watermark, EULA, icon), version ranges, and the complete <File> inventory
(each with MD5 hash and a flag indicating whether it is present in the
inner zip). Works offline — no Working Papers required.

Args:
    cwp_path: Full path to the .cwp template file

Returns:
    Dict with:
      - raw: every manifest element (nested)
      - files: list of {filename, md5, folder, present_in_inner_zip, inner_zip_size}
      - files_folder: the <Files>/<FolderName> value

Example:
    get_package_manifest(cwp_path="~/Templates/Frazier-Deeter.cwp")
""",
        inputSchema={
            "type": "object",
            "properties": {
                "cwp_path": {
                    "type": "string",
                    "description": "Full path to the .cwp template file",
                },
            },
            "required": ["cwp_path"],
        },
    ),
    Tool(
        name="get_file_inventory",
        description="""Enumerate every file inside a .cwp package's inner zip, grouped by category.

Surfaces the non-.cvw content that analyze_template_package ignores:
styles (.sty/.cgf), embedded documents (.docx/.xlsx/.pdf), dBASE tables
(.dbf/.cdx/.fpt), images (.bmp), etc. Also cross-references the manifest
to report drift (files declared but missing, or present but undeclared).
Works offline — no Working Papers required.

Args:
    cwp_path: Full path to the .cwp template file

Returns:
    Dict with:
      - total_files: count
      - by_category: {category: [{filename, size, extension}]}
      - by_extension: {ext: count}
      - manifest_only: filenames declared in manifest but missing from zip
      - zip_only: filenames present in zip but not declared in manifest

Example:
    get_file_inventory(cwp_path="~/Templates/Frazier-Deeter.cwp")
""",
        inputSchema={
            "type": "object",
            "properties": {
                "cwp_path": {
                    "type": "string",
                    "description": "Full path to the .cwp template file",
                },
            },
            "required": ["cwp_path"],
        },
    ),
    Tool(
        name="get_document_outline",
        description="""Return structured bookmarks + sections + paragraph offsets for a template.

Parses Index/Bookmarks (length-prefixed name/label records), Index/Sect
(12-byte header + 16-byte records), and Index/Para (u32 paragraph byte
offsets) from the template's OLE2 structure. Gives the caller a document
outline — number of sections, paragraph boundaries, named bookmarks —
without needing CaseView. Works offline — no Working Papers required.

Requires olefile: pip install olefile

Args:
    cwp_path: Full path to the .cwp template file
    template_code: Template code (e.g., "ENGL", "FRAUD")

Returns:
    Dict with:
      - bookmarks: [{name, label, meta}]
      - sections: [{index, u32_0, u32_1, u32_2, u32_3}]
      - paragraphs: [offset_u32, …] (monotonic ascending)
      - bookmark_count / section_count / paragraph_count
      - parse_warnings: present only if the binary format deviates from
        the expected layout

Example:
    get_document_outline(cwp_path="...", template_code="ENGL")
""",
        inputSchema={
            "type": "object",
            "properties": {
                "cwp_path": {
                    "type": "string",
                    "description": "Full path to the .cwp template file",
                },
                "template_code": {
                    "type": "string",
                    "description": "Template code (e.g., 'ENGL', 'FRAUD')",
                },
            },
            "required": ["cwp_path", "template_code"],
        },
    ),
    Tool(
        name="export_template_cells",
        description="""Export all cell/field names from a .cwp package to a JSON or CSV file.

Extracts the complete cell inventory across all templates and writes it to
a file for reference during Cloud authoring. JSON output includes package
metadata; CSV output has columns: template_code, cell_name, prefix.

Requires olefile: pip install cwp-template-reader[olefile]

Args:
    cwp_path: Full path to the .cwp template file
    output_path: Where to write the output file
    output_format: "json" (default) or "csv"

Returns:
    Summary with output path, template count, total cell count
""",
        inputSchema={
            "type": "object",
            "properties": {
                "cwp_path": {
                    "type": "string",
                    "description": "Full path to the .cwp template file",
                },
                "output_path": {
                    "type": "string",
                    "description": "Path for the output file",
                },
                "output_format": {
                    "type": "string",
                    "enum": ["json", "csv"],
                    "description": "Output format: 'json' (default) or 'csv'",
                    "default": "json",
                },
            },
            "required": ["cwp_path", "output_path"],
        },
    ),
    Tool(
        name="export_template_structure",
        description="""Export full structural dump for a specific template.

Extracts everything available: cell names, bookmarks, OLE2 stream metadata,
and all readable strings from every stream. Writes to a JSON file.

Requires olefile: pip install cwp-template-reader[olefile]

Args:
    cwp_path: Full path to the .cwp template file
    template_code: Template code (e.g., "ENGL")
    output_path: Path for the output JSON file

Returns:
    Summary with output path, cell count, stream count
""",
        inputSchema={
            "type": "object",
            "properties": {
                "cwp_path": {
                    "type": "string",
                    "description": "Full path to the .cwp template file",
                },
                "template_code": {
                    "type": "string",
                    "description": "Template code (e.g., 'ENGL', 'FRAUD')",
                },
                "output_path": {
                    "type": "string",
                    "description": "Path for the output JSON file",
                },
            },
            "required": ["cwp_path", "template_code", "output_path"],
        },
    ),
    Tool(
        name="export_full_package",
        description="""Comprehensive one-shot extraction of an entire .cwp package.

Extracts everything from every template: package metadata, template list,
all cell names, all bookmarks, OLE2 stream sizes, and all readable content
from every stream. Writes a single comprehensive JSON reference document.

This is the primary tool for Cloud authoring — it produces the complete
reference needed to rebuild templates in Caseware Cloud.

Requires olefile: pip install cwp-template-reader[olefile]

Args:
    cwp_path: Full path to the .cwp template file
    output_path: Path for the output JSON file

Returns:
    Summary with output path, template count, total cells extracted
""",
        inputSchema={
            "type": "object",
            "properties": {
                "cwp_path": {
                    "type": "string",
                    "description": "Full path to the .cwp template file",
                },
                "output_path": {
                    "type": "string",
                    "description": "Path for the output JSON file",
                },
            },
            "required": ["cwp_path", "output_path"],
        },
    ),

    # === Standalone .cvw File Tools ===
    Tool(
        name="analyze_cvw_file",
        description="""Analyze a standalone .cvw CaseView template file.

Opens a .cvw file directly as OLE2 (no .cwp container needed) and returns
structural overview: stream count, cell count, bookmark count, total size.
Works offline — no Working Papers installation required.

Requires olefile: pip install olefile

Note: Standalone .cvw files may have encoded Index/Cell streams. Use
list_cvw_cells to check if cell names are extractable, or
export_cvw_file to get the full readable content from every stream.

Args:
    cvw_path: Full path to the .cvw file

Returns:
    File size, stream count, cell count, bookmark count, total OLE size
""",
        inputSchema={
            "type": "object",
            "properties": {
                "cvw_path": {
                    "type": "string",
                    "description": "Full path to the standalone .cvw file",
                },
            },
            "required": ["cvw_path"],
        },
    ),
    Tool(
        name="list_cvw_cells",
        description="""List cell/field names from a standalone .cvw file.

Attempts to parse the Index/Cell OLE2 stream. Standalone .cvw files often
have encoded cell indices; if so, the returned cell list will be empty
with a note explaining the limitation.

For full content extraction when cells are unavailable, use
export_cvw_file which extracts readable strings from all streams.

Requires olefile: pip install olefile

Args:
    cvw_path: Full path to the .cvw file

Returns:
    Cell names, count, and prefix analysis (or empty with note if encoded)
""",
        inputSchema={
            "type": "object",
            "properties": {
                "cvw_path": {
                    "type": "string",
                    "description": "Full path to the standalone .cvw file",
                },
            },
            "required": ["cvw_path"],
        },
    ),
    Tool(
        name="get_cvw_structure",
        description="""Get OLE2 structural metadata for a standalone .cvw file.

Returns stream names and sizes, bookmarks, and cell count. Useful for
understanding the internal structure of a CaseView document before
extracting content.

Requires olefile: pip install olefile

Args:
    cvw_path: Full path to the .cvw file

Returns:
    Stream sizes, bookmarks, total OLE size, file size
""",
        inputSchema={
            "type": "object",
            "properties": {
                "cvw_path": {
                    "type": "string",
                    "description": "Full path to the standalone .cvw file",
                },
            },
            "required": ["cvw_path"],
        },
    ),
    Tool(
        name="get_cvw_document_outline",
        description="""Return structured bookmarks + section/paragraph index for a .cvw file.

Same as get_document_outline but for a .cvw file outside any .cwp package.
Parses Index/Bookmarks, Index/Sect, and Index/Para streams. Useful when
you have a raw CaseView template file extracted from somewhere else.
Works offline.

Requires olefile: pip install olefile

Args:
    cvw_path: Full path to the .cvw file

Returns:
    Dict with bookmarks, sections, paragraphs (see get_document_outline).
""",
        inputSchema={
            "type": "object",
            "properties": {
                "cvw_path": {
                    "type": "string",
                    "description": "Full path to the standalone .cvw file",
                },
            },
            "required": ["cvw_path"],
        },
    ),
    Tool(
        name="export_cvw_file",
        description="""Comprehensive extraction of a standalone .cvw file to JSON.

Extracts everything available: cells (if parseable), bookmarks, OLE2
stream metadata, and all readable strings from every stream (form labels,
scripts, styles). Writes to a JSON file.

This is the primary tool for standalone .cvw analysis — it produces the
complete extraction even when Index/Cell is encoded, pulling form content
from Form/Strings, Scripts/*, and other readable streams.

Requires olefile: pip install olefile

Args:
    cvw_path: Full path to the .cvw file
    output_path: Path for the output JSON file

Returns:
    Summary with output path, stream count, bookmark count, cell count
""",
        inputSchema={
            "type": "object",
            "properties": {
                "cvw_path": {
                    "type": "string",
                    "description": "Full path to the standalone .cvw file",
                },
                "output_path": {
                    "type": "string",
                    "description": "Path for the output JSON file",
                },
            },
            "required": ["cvw_path", "output_path"],
        },
    ),
]


# === Handler Functions (analysis tools) ===


@with_error_handling
def analyze_template_package(cwp_path: str) -> dict[str, Any]:
    """Analyze a .cwp template package."""
    with CwpReader(cwp_path) as reader:
        info = reader.get_package_info()
        templates = reader.list_templates()

        # Try to get cell counts (requires olefile)
        try:
            all_cells = reader.get_all_cells()
            for tmpl in templates:
                cells = all_cells.get(tmpl["code"], [])
                tmpl["cell_count"] = len(cells)
        except ImportError:
            for tmpl in templates:
                tmpl["cell_count"] = None
                tmpl["note"] = "Install olefile for cell counts"

        return {
            **info,
            "templates": templates,
        }


@with_error_handling
def list_template_cells(cwp_path: str, template_code: str) -> dict[str, Any]:
    """Get all cell names for a specific template."""
    with CwpReader(cwp_path) as reader:
        cells = reader.get_template_cells(template_code)

        # Analyze cell name prefixes
        prefixes: Counter[str] = Counter()
        for cell in cells:
            # Extract prefix: first 2 chars if they match known patterns
            match = re.match(r"^(pp|Pa|@@|@Q|`q|``|0A|00|!)", cell)
            if match:
                prefixes[match.group(1)] += 1
            else:
                prefixes["(other)"] += 1

        return {
            "template_code": template_code,
            "cell_count": len(cells),
            "cells": cells,
            "prefix_analysis": dict(prefixes.most_common()),
        }


@with_error_handling
def search_template_cells(cwp_path: str, pattern: str) -> dict[str, Any]:
    """Search for cells matching a pattern across all templates."""
    with CwpReader(cwp_path) as reader:
        matches = reader.search_cells(pattern)

        # Group by template
        by_template: dict[str, list[str]] = {}
        for m in matches:
            code = m["code"]
            if code not in by_template:
                by_template[code] = []
            by_template[code].append(m["cell_name"])

        return {
            "pattern": pattern,
            "total_matches": len(matches),
            "templates_matched": len(by_template),
            "matches_by_template": by_template,
        }


@with_error_handling
def get_template_structure(cwp_path: str, template_code: str) -> dict[str, Any]:
    """Get structural metadata for a specific template."""
    with CwpReader(cwp_path) as reader:
        return reader.get_template_structure(template_code)


@with_error_handling
def get_package_manifest(cwp_path: str) -> dict[str, Any]:
    """Return the complete manifest.xml content for a .cwp package."""
    with CwpReader(cwp_path) as reader:
        return reader.get_package_manifest()


@with_error_handling
def get_file_inventory(cwp_path: str) -> dict[str, Any]:
    """Enumerate every file inside a .cwp package's inner zip, grouped by category."""
    with CwpReader(cwp_path) as reader:
        return reader.get_file_inventory()


@with_error_handling
def get_document_outline(cwp_path: str, template_code: str) -> dict[str, Any]:
    """Return structured bookmarks + section index + paragraph offsets for a template."""
    with CwpReader(cwp_path) as reader:
        return reader.get_document_outline(template_code)


# === Handler Functions (standalone .cvw tools) ===


_CVW_EMPTY_CELLS_NOTE = (
    "Index/Cell stream is missing or produced no valid cell names. "
    "Use export_cvw_file to extract readable content (form labels, "
    "scripts, bookmarks) from all streams even when cells are unavailable."
)


@with_error_handling
def analyze_cvw_file(cvw_path: str) -> dict[str, Any]:
    """Analyze a standalone .cvw template file."""
    with CvwReader(cvw_path) as reader:
        stream_sizes = reader.get_stream_sizes()
        bookmarks = reader.get_bookmarks()
        cells = reader.get_cells()
        path = Path(cvw_path)
        result = {
            "file_path": str(path),
            "file_name": path.name,
            "file_size": path.stat().st_size,
            "stream_count": len(stream_sizes),
            "total_ole_size": sum(stream_sizes.values()),
            "bookmark_count": len(bookmarks),
            "cell_count": len(cells),
        }
        if not cells:
            result["note"] = _CVW_EMPTY_CELLS_NOTE
        return result


@with_error_handling
def list_cvw_cells(cvw_path: str) -> dict[str, Any]:
    """Attempt to extract cell names from a standalone .cvw file."""
    with CvwReader(cvw_path) as reader:
        cells = reader.get_cells()

        prefixes: Counter[str] = Counter()
        for cell in cells:
            match = re.match(r"^(pp|Pa|@@|@Q|`q|``|0A|00|!)", cell)
            if match:
                prefixes[match.group(1)] += 1
            else:
                prefixes["(other)"] += 1

        result: dict[str, Any] = {
            "file_path": cvw_path,
            "cell_count": len(cells),
            "cells": cells,
            "prefix_analysis": dict(prefixes.most_common()),
        }
        if not cells:
            result["note"] = _CVW_EMPTY_CELLS_NOTE
        return result


@with_error_handling
def get_cvw_structure(cvw_path: str) -> dict[str, Any]:
    """Get OLE2 structural metadata for a standalone .cvw file."""
    with CvwReader(cvw_path) as reader:
        structure = reader.get_structure()
        if structure["cell_count"] == 0:
            structure["note"] = _CVW_EMPTY_CELLS_NOTE
        return structure


@with_error_handling
def get_cvw_document_outline(cvw_path: str) -> dict[str, Any]:
    """Return document outline for a standalone .cvw file."""
    with CvwReader(cvw_path) as reader:
        return reader.get_document_outline()


@with_error_handling
def export_cvw_file(cvw_path: str, output_path: str) -> dict[str, Any]:
    """Comprehensive extraction of a standalone .cvw file to JSON."""
    out = Path(output_path)
    src = Path(cvw_path)

    with CvwReader(cvw_path) as reader:
        stream_sizes = reader.get_stream_sizes()
        bookmarks = reader.get_bookmarks()
        cells = reader.get_cells()
        readable_content = reader.get_readable_content()
        outline = reader.get_document_outline()

        result: dict[str, Any] = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "file_path": str(src),
            "file_name": src.name,
            "file_size": src.stat().st_size,
            "cells": {
                "count": len(cells),
                "names": cells,
            },
            "bookmarks": bookmarks,
            "outline": outline,
            "streams": {
                "sizes": stream_sizes,
                "total_size": sum(stream_sizes.values()),
            },
            "readable_content": readable_content,
        }
        if not cells:
            result["cells"]["note"] = _CVW_EMPTY_CELLS_NOTE

        out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    readable_stream_count = len(readable_content)
    total_strings = sum(len(v) for v in readable_content.values())
    return {
        "output_path": str(out),
        "file_name": src.name,
        "stream_count": len(stream_sizes),
        "bookmark_count": len(bookmarks),
        "cell_count": len(cells),
        "readable_stream_count": readable_stream_count,
        "total_readable_strings": total_strings,
    }


# === Handler Registry ===

HANDLERS: dict[str, Any] = {
    "analyze_template_package": analyze_template_package,
    "list_template_cells": list_template_cells,
    "search_template_cells": search_template_cells,
    "get_template_structure": get_template_structure,
    "get_package_manifest": get_package_manifest,
    "get_file_inventory": get_file_inventory,
    "get_document_outline": get_document_outline,
    "export_template_cells": export_template_cells,
    "export_template_structure": export_template_structure,
    "export_full_package": export_full_package,

    # Standalone .cvw tools
    "analyze_cvw_file": analyze_cvw_file,
    "list_cvw_cells": list_cvw_cells,
    "get_cvw_structure": get_cvw_structure,
    "get_cvw_document_outline": get_cvw_document_outline,
    "export_cvw_file": export_cvw_file,
}
