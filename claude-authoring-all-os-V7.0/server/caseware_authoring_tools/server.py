"""Caseware Authoring Tools — stdio MCP Server (Claude Desktop Extension).

Provides Knowledge Graph tools, reference prompts, and Caseware Cloud tool
proxying via MCP. For binary files (Word, Excel, PowerPoint), the
convert_document tool extracts text content.

Configuration:
    KG_PATH environment variable sets the Knowledge Graph database path.
    Falls back to ~/.local/share/caseware-authoring-tools/knowledge_graph.db

    ENGAGEMENT_URL, CASEWARE_HOST, CASEWARE_FIRM_NAME, CASEWARE_CLIENT_ID,
    and CASEWARE_CLIENT_SECRET environment variables enable the Caseware
    Cloud MCP proxy. Tokens are acquired and refreshed automatically — no
    manual BEARER_TOKEN management needed.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, Tool, TextContent, Prompt, PromptMessage, PromptArgument

from .cloud_proxy import CloudProxy
from .se_tools import SEClient, SE_TOOL_NAMES, list_se_tools, call_se_tool
from .knowledge_graph import KnowledgeGraph
from .api_client import CasewareAPIClient, AnalyticsAPIClient
from .engagement_tools import ENGAGEMENT_TOOL_NAMES, list_engagement_tools, call_engagement_tool
from .workflow_tools import WORKFLOW_TOOL_NAMES, list_workflow_tools, call_workflow_tool
from .analytics_tools import ANALYTICS_TOOL_NAMES, list_analytics_tools, call_analytics_tool
from .cwp_tools import CWP_TOOL_NAMES, list_cwp_tools, call_cwp_tool

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Knowledge Graph singleton
# ---------------------------------------------------------------------------

_kg_instance: Optional[KnowledgeGraph] = None
_kg_path: Optional[Path] = None


def _get_kg() -> KnowledgeGraph:
    """Get or create the KG singleton."""
    global _kg_instance
    if _kg_instance is None:
        _kg_instance = KnowledgeGraph(path=_kg_path, backend="sqlite")
    return _kg_instance


# ---------------------------------------------------------------------------
# Cloud Proxy singleton
# ---------------------------------------------------------------------------

_cloud_proxy: Optional[CloudProxy] = None
_se_client: Optional[SEClient] = None
_engagement_client: Optional[CasewareAPIClient] = None
_workflow_client: Optional[CasewareAPIClient] = None  # shares instance with _engagement_client
_analytics_client: Optional[AnalyticsAPIClient] = None


# ---------------------------------------------------------------------------
# Reference file loading
# ---------------------------------------------------------------------------

_REFERENCES_DIR = Path(__file__).resolve().parent.parent / "references"

_REFERENCE_PROMPTS = {
    "reference-hierarchy-rules": {
        "file": "hierarchy-rules.md",
        "description": "Depth marker system ([D0]-[D4], [R], [C], [G]) and validation rules for authoring checklists",
    },
    "reference-checklist-authoring": {
        "file": "checklist-authoring.md",
        "description": "Checklist payload structure, response type detection, and chunking strategy",
    },
    "reference-query-authoring": {
        "file": "query-authoring.md",
        "description": "Query payload structure with question sets, response columns, and templating",
    },
    "reference-letter-authoring": {
        "file": "letter-authoring.md",
        "description": "Letter structure, two-step creation, dynamic element detection (formulas, dates, staff)",
    },
    "reference-knowledge-graph": {
        "file": "knowledge-graph.md",
        "description": "Knowledge Graph entity naming convention, relation types, CLI usage, and trace schema",
    },
    "reference-caseware-cloud-mcp": {
        "file": "caseware-cloud-mcp-authoring.md",
        "description": "Caseware Cloud MCP API reference — core authoring tools, schemas, Excel parsing, best practices",
    },
    "reference-caseware-cloud-mcp-full": {
        "file": "caseware-cloud-mcp-full.md",
        "description": "Complete Caseware Cloud MCP API reference — all tools including activation, multi-year, financial data",
    },
    "reference-document-type-detection": {
        "file": "document-type-detection.md",
        "description": "Weighted scoring algorithm for classifying documents as checklist, query, or letter",
    },
    "reference-payload-schemas": {
        "file": "payload-schemas.md",
        "description": "Consolidated JSON payload schemas for checklist, query, and letter MCP submissions",
    },
    "workflow-convert": {
        "file": "workflow-convert.md",
        "description": "Read and analyse source documents — text extraction, structure analysis, and procedure outline",
    },
    "workflow-author": {
        "file": "workflow-author.md",
        "description": "Author documents to Caseware Cloud — evaluator-optimizer loop, chunking, and reporting",
    },
    "workflow-full": {
        "file": "workflow-full.md",
        "description": "Full end-to-end authoring workflow — read, analyse, author, and report",
    },
    "workflow-identify-type": {
        "file": "workflow-identify-type.md",
        "description": "Document type identification — decision tree and weighted scoring for checklist/query/letter routing",
    },
    "reference-outline-format": {
        "file": "outline-format.md",
        "description": "Procedure outline schema for build_payload tool — checklist, query, letter formats and response notation",
    },
    "workflow-visualize": {
        "file": "workflow-visualize.md",
        "description": "Visualize Knowledge Graph workflows as Mermaid flowcharts with optional Figma rendering",
    },
    "workflow-edit": {
        "file": "workflow-edit.md",
        "description": "Edit existing documents — retrieve, modify, and update checklists, queries, and letters",
    },
}


def _load_reference(filename: str) -> str:
    """Load a reference file from the references directory."""
    ref_path = _REFERENCES_DIR / filename
    if ref_path.exists():
        return ref_path.read_text(encoding="utf-8")
    return f"Reference file not found: {filename}"


def _resolve_reference_name(name: str) -> str | None:
    """Resolve a short or full reference name to the canonical key.

    Accepts:
      - Full name: "reference-checklist-authoring"
      - Short name: "checklist-authoring"
      - Prefix-stripped: "hierarchy-rules"
      - Workflow names: "workflow-convert"
    Returns the canonical key or None if not found.
    """
    # Direct match
    if name in _REFERENCE_PROMPTS:
        return name
    # Try adding "reference-" prefix
    prefixed = f"reference-{name}"
    if prefixed in _REFERENCE_PROMPTS:
        return prefixed
    # Fuzzy: check if name is a suffix of any key
    for key in _REFERENCE_PROMPTS:
        if key.endswith(name):
            return key
    return None


def _extract_section(content: str, section_heading: str) -> str | None:
    """Extract a specific ## section from markdown content.

    Returns the section content (heading + body) or None if not found.
    """
    lines = content.split("\n")
    start = None
    section_level = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        # Match ## headings (any level)
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            heading_text = stripped.lstrip("#").strip().lower()

            if section_heading.lower() in heading_text:
                start = i
                section_level = level
                continue

            # End of matched section (same or higher level heading)
            if start is not None and level <= section_level:
                return "\n".join(lines[start:i]).strip()

    # Section extends to end of file
    if start is not None:
        return "\n".join(lines[start:]).strip()

    return None


# ---------------------------------------------------------------------------
# Dynamic welcome text
# ---------------------------------------------------------------------------


def _build_welcome_text() -> str:
    """Build welcome text with dynamic cloud connection status."""
    cloud_section = ""
    if _cloud_proxy and _cloud_proxy.connected:
        cloud_tool_count = len(_cloud_proxy.tools)
        cloud_section = f"""\
### Caseware Cloud: Connected

Caseware Cloud MCP is connected with **{cloud_tool_count} tools** available. You can author checklists, queries, and letters directly into your engagement.

Available Caseware Cloud tools include:
- **checklist-save/get** — Author and retrieve checklists
- **query-save/get** — Author and retrieve queries
- **statement-save/get** — Author and retrieve letters
- **document-manager** — Manage engagement documents
- **engagement-properties** — Read engagement properties
- **controls-get/save**, **risks-get/save** — Manage controls and risks
- **trial-balance-get**, **materiality-get**, **accounts-assign** — Financial data
"""
    else:
        cloud_section = """\
### Caseware Cloud: Not Connected

Configure your **Engagement URL** and credentials in the extension settings to enable Caseware Cloud tools. Without this, only Knowledge Graph tools, CWP Template Reader, and reference prompts are available.

To configure: Open Claude Desktop Settings > Extensions > Caseware Gateway > enter your engagement URL and credentials.
"""

    # Build engagement/workflow/analytics sections if clients available
    api_section = ""
    if _engagement_client is not None:
        api_section += """\
### Engagement Tools: Available

| Tool | What It Does |
|------|-------------|
| **engagement-get** | Get engagement properties |
| **engagement-create** | Create engagement from template |
| **engagement-lock/unlock** | Lock or unlock for review |
| **engagement-rollforward** | Roll forward to new period |
| **users-get** | List staff members |
| **roles-get** | List roles and role sets |
| **staff-assign** | Assign staff to roles |
| **firm-templates-get** | List available templates |
| **visibility-get** | Get visibility rules |

"""

    if _workflow_client is not None:
        api_section += """\
### Workflow Tools: Available

| Tool | What It Does |
|------|-------------|
| **attachments-get/save/sign** | Manage and sign off attachments |
| **document-grant-access** | Grant staff access to documents |
| **document-publish** | Publish completed documents |
| **document-sign** | Sign off documents |
| **events-get/save** | Manage events and milestones |
| **history-get** | View audit trail |
| **history-files** | View file change history |

"""

    if _analytics_client is not None:
        api_section += """\
### Analytics Tools: Available

| Tool | What It Does |
|------|-------------|
| **analytics-get-catalog** | Browse available analytics |
| **analytics-get-predefined-configs** | List ready-to-use configurations |
| **analytics-trigger** | Run analytics on demand |
| **analytics-get-status** | Check execution status |
| **analytics-get-execution-details** | Get detailed results |
| **analytics-get-dataset** | Download output datasets |
| **analytics-get-notebook-content/data** | Access notebook results |
| **analytics-get-permissions** | Check user permissions |

"""

    return f"""\
# Caseware Gateway

Welcome! This gateway provides unified access to Caseware Cloud — authoring, engagement management, workflow, analytics, and offline template analysis.

## The Full Workflow

Upload your source documents and Claude reads the content, analyses the structure, and authors directly to Caseware Cloud — all in a single pass.

**Supported formats:** .docx, .doc, .xlsx, .xls, .pdf, .pptx, .md

{cloud_section}\
{api_section}\
### CWP Template Reader (Always Available)

Analyze CaseWare Working Papers `.cwp` template packages offline:

| Tool | What It Does |
|------|-------------|
| **analyze_template_package** | Package overview with template list |
| **list_template_cells** | Cell/field names for a template |
| **search_template_cells** | Regex search across all templates |
| **get_template_structure** | OLE2 metadata and bookmarks |
| **export_template_cells** | Export cells to JSON/CSV |
| **export_template_structure** | Full template structural dump |
| **export_full_package** | Comprehensive package extraction |

### How a typical authoring session works

1. **Upload your document** — Claude reads the content (using `convert_document` for binary formats, or natively for PDF/markdown)
2. **Analyse structure** — Claude classifies the document type (checklist, query, or letter) and determines the hierarchy, response types, and validation rules
3. **Build outline** — Claude produces a procedure outline and calls `build_payload` to generate validated payloads
4. **Author** — Claude submits the payloads to Caseware Cloud via the appropriate save tool
5. **Edit** — Need to update an existing document? Claude retrieves it, identifies changes, and submits sparse updates
6. **Track** — Optionally, Claude logs the workflow in the Knowledge Graph for audit trail

### What gets created in Caseware Cloud

| Document Type | What's Created | Key Features |
|--------------|----------------|--------------|
| **Checklist** | Groups, headings, procedures with response types | Yes/No/N/A picklists, text fields, date fields, engagement signoff |
| **Query** | Question sets with text input and file upload columns | Client-facing information requests |
| **Letter** | Formatted letter sections with dynamic formulas | Engagement properties, collaboration fields, date placeholders |

## Knowledge Graph Tools

Track your authoring workflows with a local knowledge graph for audit trail and observability:

| Tool | What It Does |
|------|-------------|
| **kg_create_entities** | Create workflow, task, or document entities |
| **kg_create_relations** | Link entities together (e.g. workflow contains task) |
| **kg_add_observations** | Add notes, timestamps, and results to entities |
| **kg_query** | Find entities by name pattern, type, or relationship |
| **kg_search** | Full-text search across all entities |
| **kg_export_mermaid** | Export a visual diagram of your workflow |

## Reference Guides

Claude loads reference guides autonomously via the `load_reference` tool — no manual attachment needed. Use `list_references` to see all available guides.

| Reference | What It Contains | Load With |
|-----------|-----------------|-----------|
| **hierarchy-rules** | Depth marker system and validation rules | `load_reference('hierarchy-rules')` |
| **checklist-authoring** | Checklist payload structure and chunking | `load_reference('checklist-authoring')` |
| **query-authoring** | Query payload structure and templating | `load_reference('query-authoring')` |
| **letter-authoring** | Letter structure and dynamic elements | `load_reference('letter-authoring')` |
| **knowledge-graph** | Knowledge Graph naming and CLI usage | `load_reference('knowledge-graph')` |
| **caseware-cloud-mcp** | Caseware Cloud MCP API reference | `load_reference('caseware-cloud-mcp')` |
| **document-type-detection** | Weighted scoring for document classification | `load_reference('document-type-detection')` |
| **payload-schemas** | JSON payload schemas for MCP submissions | `load_reference('payload-schemas')` |
| **outline-format** | Procedure outline schema for `build_payload` | `load_reference('outline-format')` |
| **workflow-convert** | Read and analyse source documents | `load_reference('workflow-convert')` |
| **workflow-author** | Authoring with evaluator loop and reporting | `load_reference('workflow-author')` |
| **workflow-full** | Complete end-to-end workflow | `load_reference('workflow-full')` |
| **workflow-identify-type** | Document type detection and routing | `load_reference('workflow-identify-type')` |
| **workflow-edit** | Edit existing documents in Caseware Cloud | `load_reference('workflow-edit')` |

Prompts are also available for manual browsing via the Claude Desktop UI.

## Getting Started

- **If Caseware Cloud is connected:** "Upload my document and author it as a checklist in Caseware Cloud"
- **If only KG tools are available:** "Upload my document and analyse its structure" (configure Cloud connection in extension settings to author later)
- **To check your connections:** Call `initialize_authoring_tools` to see current status
"""


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

def _build_instructions() -> str:
    """Build server instructions with dynamic cloud status.

    These instructions are always-on context for Claude Desktop — equivalent to
    SKILL.md in the VS Code authoring-agent. They ensure critical rules are
    enforced without requiring Claude to load reference prompts first.
    """
    base = (
        "You have access to the Caseware Gateway — a unified interface for authoring, "
        "engagement management, workflow, analytics, and offline template analysis. "
        "For binary files (Word, Excel, PowerPoint), use the convert_document tool to extract text. "
        "For .cwp template packages, use the CWP Template Reader tools (always available, no auth needed).\n\n"

        # ---- API Tool Categories ----
        "API TOOL CATEGORIES (require credentials):\n"
        "- Engagement tools (engagement-get, engagement-create, users-get, roles-get, etc.)\n"
        "- Workflow tools (attachments-get/save, document-sign, events-get/save, history-get, etc.)\n"
        "- Analytics tools (analytics-get-catalog, analytics-trigger, analytics-get-status, etc.)\n"
        "- SE tools (file-upload/download, suggestion-get/commit, risk-assessment-get/save, tags-get/save)\n"
        "- Cloud Proxy tools (checklist-save/get, query-save/get, statement-save/get, etc.)\n\n"

        # ---- Reference Loading ----
        "REFERENCE LOADING:\n"
        "Load detailed reference guides using the load_reference tool. "
        "Use list_references to see all available guides. Key references:\n"
        "- call load_reference('checklist-authoring') — MANDATORY before authoring any checklist\n"
        "- call load_reference('letter-authoring') — MANDATORY before authoring any letter\n"
        "- call load_reference('query-authoring') — before authoring any query\n"
        "- call load_reference('payload-schemas') — for raw payload structure reference\n"
        "- call load_reference('hierarchy-rules') — for full depth marker reference\n"
        "- call load_reference('outline-format') — for the outline schema used by build_payload\n"
        "For large references, use the section parameter: "
        "load_reference('caseware-cloud-mcp', section='checklist-save')\n\n"

        # ---- Critical Rules (unique to this description — not duplicated elsewhere) ----
        "CRITICAL RULES:\n"
        "- Call build_payload EXACTLY ONCE per document. Do NOT call it during read/analyse — "
        "only during the authoring step. If validation fails, fix the outline and re-call.\n"
        "- Follow the submission_instructions returned by build_payload PRECISELY. "
        "Do NOT make additional API calls beyond what it specifies.\n"
        "- Do NOT manually construct payloads — build_payload generates correct payloads "
        "with all boilerplate, chunking, and validation.\n"
        "- Do NOT manually chunk procedures — build_payload handles all chunking automatically.\n"
        "- Do NOT include conclusion items in the outline — the API generates conclusions "
        "automatically via includeConclusion: true (set by build_payload). Explicit conclusion "
        "items render as groups, not conclusions.\n"
        "- Always include guidance and authoritativeReferences on batched updates — "
        "never strip to reduce payload size.\n"
        "- After each -save call, compare response procedure count against expected_per_payload "
        "from metadata — HARD FAIL with PAYLOAD_TRUNCATED if they differ.\n"
        "- All -save MCP operations MUST be sequential (never parallel).\n\n"

        # ---- Workflow References ----
        "WORKFLOW REFERENCES (load for guided workflows):\n"
        "- call load_reference('workflow-convert'): Read and analyse source documents\n"
        "- call load_reference('workflow-author'): Authoring to Caseware Cloud\n"
        "- call load_reference('workflow-full'): Complete end-to-end workflow (convert + author)\n"
        "- call load_reference('workflow-identify-type'): Document type detection and routing\n"
        "- call load_reference('workflow-edit'): Edit existing documents (retrieve, modify, update)\n"
    )
    if _cloud_proxy and _cloud_proxy.connected:
        base += (
            "\nCaseware Cloud tools are available — you can author checklists, queries, "
            "and letters directly into the engagement."
        )
    else:
        base += (
            "\nTo use Cloud tools, the user needs to configure the "
            "engagement URL and credentials in the extension settings."
        )
    base += (
        "\nWhen a user says 'Initialise Caseware Authoring Tools' or asks what tools are "
        "available, call the 'initialize_authoring_tools' tool to show the full workflow overview."
    )
    return base


app = Server("caseware-gateway")


@app.list_prompts()
async def list_prompts() -> list[Prompt]:
    """List available prompts."""
    prompts = [
        Prompt(
            name="initialize-authoring-tools",
            description=(
                "Get a full overview of Caseware Authoring Tools — what's available, "
                "how to use each tool, and suggested first steps. "
                "Trigger by saying: Initialise Caseware Authoring Tools"
            ),
            arguments=[],
        ),
    ]

    # Add reference prompts
    for name, info in _REFERENCE_PROMPTS.items():
        prompts.append(
            Prompt(
                name=name,
                description=info["description"],
                arguments=[],
            )
        )

    return prompts


@app.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None = None) -> list[PromptMessage]:
    """Handle prompt requests."""
    if name == "initialize-authoring-tools":
        return [
            PromptMessage(
                role="user",
                content=TextContent(type="text", text=_build_welcome_text()),
            )
        ]

    # Handle reference prompts
    if name in _REFERENCE_PROMPTS:
        ref_info = _REFERENCE_PROMPTS[name]
        content = _load_reference(ref_info["file"])
        return [
            PromptMessage(
                role="user",
                content=TextContent(type="text", text=content),
            )
        ]

    raise ValueError(f"Unknown prompt: {name}")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools — local KG tools plus any proxied cloud tools."""
    local_tools = [
        Tool(
            name="initialize_authoring_tools",
            description=(
                "Show a full overview of Caseware Authoring Tools — available tools, "
                "supported formats, and how to get started. Call this when the user says "
                "'Initialise Caseware Authoring Tools' or asks what this server can do."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="kg_create_entities",
            description=(
                "Create one or more entities in the Knowledge Graph. "
                "Each entity has a name (following {AgentCode}_{TypeCode}_{Identifier} convention) "
                "and a type (workflow, task, document, tool, outcome, finding, risk, etc.)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "entities": {
                        "type": "array",
                        "description": 'Array of entity objects with "name" and "type" fields',
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "type": {"type": "string"},
                            },
                            "required": ["name", "type"],
                        },
                    }
                },
                "required": ["entities"],
            },
        ),
        Tool(
            name="kg_create_relations",
            description=(
                "Create one or more relations between entities in the Knowledge Graph. "
                "Each relation is a [from_entity, relation_type, to_entity] tuple."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "relations": {
                        "type": "array",
                        "description": "Array of [from, type, to] tuples",
                        "items": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 3,
                            "maxItems": 3,
                        },
                    }
                },
                "required": ["relations"],
            },
        ),
        Tool(
            name="kg_add_observations",
            description=(
                "Add observation strings to an existing entity in the Knowledge Graph. "
                "Observations record timestamps, results, decisions, and findings."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_name": {
                        "type": "string",
                        "description": "Name of the entity to add observations to",
                    },
                    "observations": {
                        "type": "array",
                        "description": "Array of observation strings to add",
                        "items": {"type": "string"},
                    },
                },
                "required": ["entity_name", "observations"],
            },
        ),
        Tool(
            name="kg_query",
            description=(
                "Query entities in the Knowledge Graph with optional filters. "
                "Supports filtering by glob pattern, entity type, and related entity."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern to match entity names (e.g., 'AA_T_*')",
                    },
                    "entity_type": {
                        "type": "string",
                        "description": "Filter by entity type (workflow, task, document, etc.)",
                    },
                    "related_to": {
                        "type": "string",
                        "description": "Filter entities related to this entity name",
                    },
                },
            },
        ),
        Tool(
            name="kg_search",
            description="Full-text search across all entities in the Knowledge Graph.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query text",
                    }
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="kg_export_mermaid",
            description="Export a Mermaid diagram from the Knowledge Graph, optionally rooted at a specific entity.",
            inputSchema={
                "type": "object",
                "properties": {
                    "root": {
                        "type": "string",
                        "description": "Optional root entity name for the diagram",
                    },
                    "direction": {
                        "type": "string",
                        "description": "Diagram direction: LR, TB, RL, or BT",
                        "default": "LR",
                        "enum": ["LR", "TB", "RL", "BT"],
                    },
                },
            },
        ),
        Tool(
            name="list_references",
            description=(
                "List all available authoring reference guides with descriptions. "
                "Returns reference names that can be loaded with load_reference."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="load_reference",
            description=(
                "Load an authoring reference guide by name. Returns the full content of the "
                "reference file. Use list_references to see available names. Accepts short names "
                "(e.g., 'checklist-authoring') or full names (e.g., 'reference-checklist-authoring'). "
                "Use the optional section parameter to load only a specific ## heading from large files."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "reference_name": {
                        "type": "string",
                        "description": (
                            "Name of the reference to load. Accepts short names like "
                            "'checklist-authoring', 'hierarchy-rules', 'caseware-cloud-mcp', "
                            "'payload-schemas', 'letter-authoring', 'query-authoring', "
                            "'workflow-convert', 'workflow-author', 'workflow-full', etc."
                        ),
                    },
                    "section": {
                        "type": "string",
                        "description": (
                            "Optional: load only a specific ## section by heading text. "
                            "Useful for large references like caseware-cloud-mcp. "
                            "Example: 'checklist-save', 'statement-save', 'Excel Source Parsing'."
                        ),
                    },
                },
                "required": ["reference_name"],
            },
        ),
        Tool(
            name="build_payload",
            description=(
                "Build validated Caseware Cloud payload from a procedure outline. "
                "Supports create mode (default) and update mode (mode: 'update' with document_id). "
                "Handles all boilerplate (rows/columns/choices JSON), validation, chunking, "
                "and letter two-step creation. Call load_reference('outline-format') for "
                "the outline schema. "
                "IMPORTANT: The result includes submission_instructions — follow them exactly "
                "for the correct number of API calls. Do NOT use other submission guidance. "
                "build_payload handles all boilerplate (conclusions, IDs, chunking, validation) — "
                "do not duplicate this work manually."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "outline": {
                        "type": "object",
                        "description": (
                            "Procedure outline with document_type (checklist/query/letter), "
                            "name, number, folder_id, purpose, purpose_summary, and "
                            "items (checklist/query) or sections (letter). "
                            "For updates: add mode: 'update', document_id, and item IDs. "
                            "See load_reference('outline-format') for full schema."
                        ),
                    }
                },
                "required": ["outline"],
            },
        ),
        Tool(
            name="convert_document",
            description=(
                "Extract text content from a document file (Word, Excel, PowerPoint, PDF) "
                "and detect its type (checklist, query, or letter). Use this for binary "
                "formats that cannot be read directly. Returns extracted text, detected "
                "document type, and confidence score."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to the document file",
                    }
                },
                "required": ["file_path"],
            },
        ),
    ]

    # Append proxied Caseware Cloud tools if connected
    if _cloud_proxy and _cloud_proxy.connected:
        local_tools.extend(_cloud_proxy.tools)

    # Append SE API tools if client is available
    if _se_client is not None:
        local_tools.extend(list_se_tools())

    # Append Engagement API tools
    if _engagement_client is not None:
        local_tools.extend(list_engagement_tools())

    # Append Workflow API tools
    if _workflow_client is not None:
        local_tools.extend(list_workflow_tools())

    # Append Analytics API tools
    if _analytics_client is not None:
        local_tools.extend(list_analytics_tools())

    # CWP Template Reader tools (always available — local file ops, no auth)
    local_tools.extend(list_cwp_tools())

    return local_tools


def _cloud_error(message: str) -> CallToolResult:
    """Return a properly-typed error result for cloud tool failures."""
    return CallToolResult(
        content=[TextContent(type="text", text=f"❌ {message}")],
        isError=True,
    )


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult | list[TextContent]:
    """Handle tool calls — route to cloud proxy or local handler."""
    # Check if this is a proxied cloud tool
    if _cloud_proxy and _cloud_proxy.has_tool(name):
        # Health check: is the proxy still connected?
        if not _cloud_proxy.connected:
            # Attempt automatic reconnection before failing
            reconnected = await _cloud_proxy.reconnect()
            if not reconnected:
                return _cloud_error(
                    "Caseware Cloud connection lost. Reconnection failed after 3 attempts. "
                    "Restart the extension or check your engagement URL and Bearer token."
                )
        try:
            result = await asyncio.wait_for(
                _cloud_proxy.call_tool(name, arguments),
                timeout=90.0,
            )
            # Return CallToolResult directly — the MCP server framework
            # handles this natively (preserves isError, ResourceLink, etc.)
            return result
        except asyncio.TimeoutError:
            return _cloud_error("Caseware Cloud tool call timed out after 90 seconds.")
        except Exception as e:
            return _cloud_error(f"Caseware Cloud error: {e}")

    # Async SE API tools
    if _se_client is not None and name in SE_TOOL_NAMES:
        try:
            result = await call_se_tool(name, arguments, _se_client)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"success": False, "error": str(e)}, indent=2))]

    # Engagement API tools
    if _engagement_client is not None and name in ENGAGEMENT_TOOL_NAMES:
        try:
            result = await call_engagement_tool(name, arguments, _engagement_client)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"success": False, "error": str(e)}, indent=2))]

    # Workflow API tools
    if _workflow_client is not None and name in WORKFLOW_TOOL_NAMES:
        try:
            result = await call_workflow_tool(name, arguments, _workflow_client)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"success": False, "error": str(e)}, indent=2))]

    # Analytics API tools
    if _analytics_client is not None and name in ANALYTICS_TOOL_NAMES:
        try:
            result = await call_analytics_tool(name, arguments, _analytics_client)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"success": False, "error": str(e)}, indent=2))]

    # CWP Template Reader tools (always available)
    if name in CWP_TOOL_NAMES:
        try:
            result = call_cwp_tool(name, arguments)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"success": False, "error": str(e)}, indent=2))]

    # Local tool dispatch
    try:
        result = _dispatch_tool(name, arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    except Exception as e:
        error_result = {"success": False, "error": str(e)}
        return [TextContent(type="text", text=json.dumps(error_result, indent=2))]


def _dispatch_tool(name: str, args: dict[str, Any]) -> dict:
    """Route tool call to the appropriate handler."""

    # --- Initialization tool ---
    if name == "initialize_authoring_tools":
        status: dict = {
            "success": True,
            "overview": _build_welcome_text(),
            "kg_tools": 6,
            "cwp_tools": len(CWP_TOOL_NAMES),
        }
        if _cloud_proxy and _cloud_proxy.connected:
            status["cloud_connected"] = True
            status["cloud_tools"] = len(_cloud_proxy.tools)
        else:
            status["cloud_connected"] = False
            status["cloud_tools"] = 0
        status["engagement_tools"] = len(ENGAGEMENT_TOOL_NAMES) if _engagement_client else 0
        status["workflow_tools"] = len(WORKFLOW_TOOL_NAMES) if _workflow_client else 0
        status["analytics_tools"] = len(ANALYTICS_TOOL_NAMES) if _analytics_client else 0
        status["se_tools"] = len(SE_TOOL_NAMES) if _se_client else 0
        if not (_cloud_proxy and _cloud_proxy.connected):
            status["cloud_hint"] = (
                "Configure Engagement URL and credentials in extension settings "
                "to enable Caseware Cloud tools."
            )
        return status

    # --- Knowledge Graph tools ---
    elif name == "kg_create_entities":
        kg = _get_kg()
        created = kg.create_entities(args["entities"])
        return {"success": True, "created": created, "count": len(created)}

    elif name == "kg_create_relations":
        kg = _get_kg()
        created = kg.create_relations(args["relations"])
        return {"success": True, "created": created, "count": len(created)}

    elif name == "kg_add_observations":
        kg = _get_kg()
        added = kg.add_observations(args["entity_name"], args["observations"])
        return {
            "success": True,
            "entity": args["entity_name"],
            "added": added,
            "count": len(added),
        }

    elif name == "kg_query":
        kg = _get_kg()
        results = kg.query(
            pattern=args.get("pattern"),
            entity_type=args.get("entity_type"),
            related_to=args.get("related_to"),
        )
        return {
            "success": True,
            "entities": [e.to_dict() for e in results],
            "count": len(results),
        }

    elif name == "kg_search":
        kg = _get_kg()
        results = kg.search(args["query"])
        return {
            "success": True,
            "entities": [e.to_dict() for e in results],
            "count": len(results),
            "query": args["query"],
        }

    elif name == "kg_export_mermaid":
        kg = _get_kg()
        mermaid = kg.export_mermaid(
            root=args.get("root"),
            direction=args.get("direction", "LR"),
        )
        return {"success": True, "mermaid": mermaid}

    # --- Reference tools ---
    elif name == "list_references":
        refs = {}
        for key, info in _REFERENCE_PROMPTS.items():
            # Provide both full name and short name
            short = key.replace("reference-", "") if key.startswith("reference-") else key
            refs[key] = {
                "short_name": short,
                "description": info["description"],
                "file": info["file"],
            }
        return {"success": True, "references": refs, "count": len(refs)}

    elif name == "load_reference":
        ref_name = args.get("reference_name", "")
        section = args.get("section")

        canonical = _resolve_reference_name(ref_name)
        if canonical is None:
            available = ", ".join(
                k.replace("reference-", "") if k.startswith("reference-") else k
                for k in _REFERENCE_PROMPTS
            )
            return {
                "success": False,
                "error": f"Unknown reference: '{ref_name}'. Available: {available}",
            }

        ref_info = _REFERENCE_PROMPTS[canonical]
        content = _load_reference(ref_info["file"])

        if content.startswith("Reference file not found"):
            return {"success": False, "error": content}

        if section:
            extracted = _extract_section(content, section)
            if extracted is None:
                return {
                    "success": False,
                    "error": f"Section '{section}' not found in {canonical}.",
                    "hint": "Try loading the full reference without a section parameter.",
                }
            return {
                "success": True,
                "reference": canonical,
                "section": section,
                "content": extracted,
            }

        return {
            "success": True,
            "reference": canonical,
            "content": content,
        }

    # --- Payload builder tool ---
    elif name == "build_payload":
        from .payload_builder import build_payload
        return build_payload(args["outline"])

    # --- Document conversion tool ---
    elif name == "convert_document":
        from .converter import convert_single_file
        return convert_single_file(args["file_path"])

    else:
        return {"success": False, "error": f"Unknown tool: {name}"}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def _run():
    """Run the MCP server via stdio, optionally connecting to Caseware Cloud."""
    import os
    from .token_manager import TokenManager

    global _cloud_proxy

    # Read cloud config from environment
    engagement_url = os.environ.get("ENGAGEMENT_URL", "").strip()
    caseware_host = os.environ.get("CASEWARE_HOST", "").strip()
    caseware_firm = os.environ.get("CASEWARE_FIRM_NAME", "").strip()
    client_id = os.environ.get("CASEWARE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("CASEWARE_CLIENT_SECRET", "").strip()

    # Support legacy BEARER_TOKEN for backward compatibility
    bearer_token = os.environ.get("BEARER_TOKEN", "").strip()
    if bearer_token.lower().startswith("bearer "):
        bearer_token = bearer_token[7:].strip()

    # Connect to Caseware Cloud if configured
    if engagement_url:
        # Prefer client credentials over legacy static token
        if caseware_host and caseware_firm and client_id and client_secret:
            try:
                token_manager = TokenManager(caseware_host, caseware_firm, client_id, client_secret)
                bearer_token = await token_manager.get_token()
                logger.info("Bearer token acquired via client credentials")
            except Exception as e:
                logger.warning("Could not acquire token via client credentials: %s", e)
                if not bearer_token:
                    logger.info("No fallback BEARER_TOKEN — starting with KG tools only")
                    bearer_token = ""

        if bearer_token:
            _cloud_proxy = CloudProxy(engagement_url, bearer_token)
            try:
                await _cloud_proxy.connect()
                logger.info("Caseware Cloud proxy connected successfully")
            except Exception as e:
                logger.warning("Could not connect to Caseware Cloud: %s", e)
                logger.info("Starting with KG tools only")
                _cloud_proxy = None
        else:
            logger.info("No bearer token available — KG tools only")
    else:
        logger.info("No ENGAGEMENT_URL configured — KG tools only")

    # Set dynamic instructions
    app.instructions = _build_instructions()

    # Initialize API clients if we have host + firm + credentials
    global _se_client, _engagement_client, _workflow_client, _analytics_client
    if caseware_host and caseware_firm and client_id and client_secret and engagement_url:
        import re
        _ENGAGEMENT_ID_RE = re.compile(r'/eng/([A-Za-z0-9_-]{20,25})(?:/|$)')
        match = _ENGAGEMENT_ID_RE.search(engagement_url)
        if match:
            engagement_id = match.group(1)

            # SE API client (existing)
            _se_tm = TokenManager(caseware_host, caseware_firm, client_id, client_secret)
            _se_client = SEClient(caseware_host, caseware_firm, engagement_id, _se_tm)
            logger.info("SE API client initialized for engagement %s", engagement_id)

            # Engagement + Workflow API client (shared instance)
            _api_tm = TokenManager(caseware_host, caseware_firm, client_id, client_secret)
            _api_client = CasewareAPIClient(caseware_host, caseware_firm, engagement_id, _api_tm)
            _engagement_client = _api_client
            _workflow_client = _api_client
            logger.info("Engagement + Workflow API clients initialized")

            # Analytics API client (different base URL + cookie auth)
            _analytics_tm = TokenManager(caseware_host, caseware_firm, client_id, client_secret)
            _analytics_client = AnalyticsAPIClient(
                caseware_host, caseware_firm, engagement_id, _analytics_tm,
            )
            logger.info("Analytics API client initialized")
        else:
            logger.warning("Could not extract engagement ID from ENGAGEMENT_URL — API tools disabled")

    try:
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())
    finally:
        # Clean up proxies on shutdown
        if _cloud_proxy:
            await _cloud_proxy.disconnect()


def main():
    """Main entry point — reads config from environment variables."""
    import os

    global _kg_path
    kg_path_env = os.environ.get("KG_PATH", "").strip()
    if kg_path_env:
        _kg_path = Path(kg_path_env)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(name)s - %(levelname)s - %(message)s",
    )

    asyncio.run(_run())


if __name__ == "__main__":
    main()
