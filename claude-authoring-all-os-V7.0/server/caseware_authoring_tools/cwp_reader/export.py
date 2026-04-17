"""Export tools for comprehensive template extraction.

Provides tools to export template content to JSON/CSV files for use as
reference when authoring equivalent forms in Caseware Cloud.
"""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .cwp_reader import CwpReader
from .errors import with_error_handling


@with_error_handling
def export_template_cells(
    cwp_path: str,
    output_path: str,
    output_format: str = "json",
) -> dict[str, Any]:
    """Export all cell/field names from a .cwp package to a file.

    Args:
        cwp_path: Path to the .cwp template file
        output_path: Where to write the output file
        output_format: "json" (default) or "csv"

    Returns:
        Summary with output path, template count, total cell count.
    """
    out = Path(output_path)

    with CwpReader(cwp_path) as reader:
        info = reader.get_package_info()
        all_cells = reader.get_all_cells()

        total_cells = sum(len(cells) for cells in all_cells.values())

        if output_format == "csv":
            _write_cells_csv(out, all_cells)
        else:
            _write_cells_json(out, info, all_cells)

    return {
        "output_path": str(out),
        "output_format": output_format,
        "template_count": len(all_cells),
        "total_cells": total_cells,
    }


@with_error_handling
def export_template_structure(
    cwp_path: str,
    template_code: str,
    output_path: str,
) -> dict[str, Any]:
    """Export full structural dump for a specific template.

    Extracts cells, bookmarks, OLE2 stream metadata, and all readable
    strings from every stream in the template.

    Args:
        cwp_path: Path to the .cwp template file
        template_code: Template code (e.g., "ENGL")
        output_path: Path for the output JSON file

    Returns:
        Summary with output path, cell count, stream count.
    """
    out = Path(output_path)

    with CwpReader(cwp_path) as reader:
        cells = reader.get_template_cells(template_code)
        structure = reader.get_template_structure(template_code)
        readable = reader.get_template_readable_content(template_code)
        outline = reader.get_document_outline(template_code)

        # Analyze cell prefixes
        prefix_analysis = _analyze_prefixes(cells)

        result = {
            "template_code": template_code,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "cells": {
                "count": len(cells),
                "names": cells,
                "prefix_analysis": prefix_analysis,
            },
            "bookmarks": structure.get("bookmarks", []),
            "outline": outline,
            "streams": {
                "sizes": structure.get("stream_sizes", {}),
                "total_size": structure.get("total_ole_size", 0),
            },
            "readable_content": readable,
        }

        out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    return {
        "output_path": str(out),
        "template_code": template_code,
        "cell_count": len(cells),
        "stream_count": len(structure.get("stream_sizes", {})),
        "bookmark_count": len(structure.get("bookmarks", [])),
    }


@with_error_handling
def export_full_package(
    cwp_path: str,
    output_path: str,
) -> dict[str, Any]:
    """Comprehensive one-shot extraction of an entire .cwp package.

    Extracts everything from every template: package metadata, all cell
    names, all bookmarks, OLE2 stream sizes, and all readable content.
    Writes a single comprehensive JSON reference document.

    Args:
        cwp_path: Path to the .cwp template file
        output_path: Path for the output JSON file

    Returns:
        Summary with output path, template count, total cells extracted.
    """
    out = Path(output_path)

    with CwpReader(cwp_path) as reader:
        info = reader.get_package_info()
        manifest = reader.get_package_manifest()
        inventory = reader.get_file_inventory()
        templates_list = reader.list_templates()

        templates_data: dict[str, Any] = {}
        total_cells = 0

        for tmpl in templates_list:
            code = tmpl["code"]
            template_entry: dict[str, Any] = {
                "filename": tmpl["filename"],
                "file_size": tmpl["file_size"],
            }

            try:
                cells = reader.get_template_cells(code)
                template_entry["cells"] = {
                    "count": len(cells),
                    "names": cells,
                    "prefix_analysis": _analyze_prefixes(cells),
                }
                total_cells += len(cells)
            except ImportError:
                template_entry["cells"] = {"error": "olefile not installed"}

            try:
                structure = reader.get_template_structure(code)
                template_entry["bookmarks"] = structure.get("bookmarks", [])
                template_entry["streams"] = {
                    "sizes": structure.get("stream_sizes", {}),
                    "total_size": structure.get("total_ole_size", 0),
                }
            except ImportError:
                template_entry["bookmarks"] = []
                template_entry["streams"] = {"error": "olefile not installed"}

            try:
                readable = reader.get_template_readable_content(code)
                template_entry["readable_content"] = readable
            except ImportError:
                template_entry["readable_content"] = {"error": "olefile not installed"}

            try:
                template_entry["outline"] = reader.get_document_outline(code)
            except ImportError:
                template_entry["outline"] = {"error": "olefile not installed"}

            templates_data[code] = template_entry

        result = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "package": info,
            "manifest": manifest,
            "inventory": inventory,
            "template_count": len(templates_data),
            "total_cells": total_cells,
            "templates": templates_data,
        }

        out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    return {
        "output_path": str(out),
        "template_count": len(templates_data),
        "total_cells": total_cells,
    }


def _analyze_prefixes(cells: list[str]) -> dict[str, int]:
    """Analyze cell name prefixes and return counts."""
    from collections import Counter

    prefixes: Counter[str] = Counter()
    for cell in cells:
        match = re.match(r"^(pp|Pa|@@|@Q|`q|``|0A|00|!)", cell)
        if match:
            prefixes[match.group(1)] += 1
        else:
            prefixes["(other)"] += 1
    return dict(prefixes.most_common())


def _write_cells_csv(out: Path, all_cells: dict[str, list[str]]) -> None:
    """Write cell inventory as CSV."""
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["template_code", "cell_name", "prefix"])
        for code, cells in sorted(all_cells.items()):
            for cell in cells:
                match = re.match(r"^(pp|Pa|@@|@Q|`q|``|0A|00|!)", cell)
                prefix = match.group(1) if match else ""
                writer.writerow([code, cell, prefix])


def _write_cells_json(
    out: Path, info: dict[str, Any], all_cells: dict[str, list[str]]
) -> None:
    """Write cell inventory as JSON."""
    result = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "package": info,
        "templates": {
            code: {
                "cell_count": len(cells),
                "cells": cells,
            }
            for code, cells in sorted(all_cells.items())
        },
    }
    out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
