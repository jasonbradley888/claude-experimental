"""CWP Template Reader tools adapter — exposes vendored cwp-template-reader
tools in the same pattern as other tool modules.

These tools work offline (no cloud connection needed) and parse .cwp
template packages to extract cell inventories, metadata, and structure.
"""

from typing import Any

from mcp.types import Tool

from .cwp_reader.tools import TOOLS as CWP_TOOL_DEFS, HANDLERS as CWP_HANDLERS

# ---------------------------------------------------------------------------
# Tool names
# ---------------------------------------------------------------------------

CWP_TOOL_NAMES: set[str] = {t.name for t in CWP_TOOL_DEFS}


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

def list_cwp_tools() -> list[Tool]:
    """Return MCP Tool objects for all 7 CWP template reader tools."""
    return list(CWP_TOOL_DEFS)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

def call_cwp_tool(name: str, args: dict) -> Any:
    """Route a tool call to the appropriate CWP handler.

    CWP tools are synchronous (local file I/O only, no network).
    The handler signature varies per tool — we dispatch with keyword args.
    """
    handler = CWP_HANDLERS[name]

    # Map tool arguments to handler parameters
    if name == "analyze_template_package":
        return handler(cwp_path=args["cwp_path"])

    elif name == "list_template_cells":
        return handler(cwp_path=args["cwp_path"], template_code=args["template_code"])

    elif name == "search_template_cells":
        return handler(cwp_path=args["cwp_path"], pattern=args["pattern"])

    elif name == "get_template_structure":
        return handler(cwp_path=args["cwp_path"], template_code=args["template_code"])

    elif name == "export_template_cells":
        return handler(
            cwp_path=args["cwp_path"],
            output_path=args["output_path"],
            output_format=args.get("output_format", "json"),
        )

    elif name == "export_template_structure":
        return handler(
            cwp_path=args["cwp_path"],
            template_code=args["template_code"],
            output_path=args["output_path"],
        )

    elif name == "export_full_package":
        return handler(
            cwp_path=args["cwp_path"],
            output_path=args["output_path"],
        )

    # Standalone .cvw tools
    elif name == "analyze_cvw_file":
        return handler(cvw_path=args["cvw_path"])

    elif name == "list_cvw_cells":
        return handler(cvw_path=args["cvw_path"])

    elif name == "get_cvw_structure":
        return handler(cvw_path=args["cvw_path"])

    elif name == "export_cvw_file":
        return handler(
            cvw_path=args["cvw_path"],
            output_path=args["output_path"],
        )

    else:
        raise KeyError(f"Unknown CWP tool: {name}")
