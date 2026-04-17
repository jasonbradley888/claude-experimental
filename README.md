<div align="center">

# Caseware Authoring Tools

**A Claude Desktop extension for authoring checklists, queries, and letters into Caseware Cloud**

[![MCPB v0.4](https://img.shields.io/badge/MCPB-v0.4-blue)](https://github.com/anthropics/mcpb)
[![Version](https://img.shields.io/badge/Extension-v5.0.0-brightgreen)]()
[![Claude Desktop](https://img.shields.io/badge/Claude%20Desktop-Extension-blueviolet)](https://claude.ai)
[![MCP](https://img.shields.io/badge/Model%20Context%20Protocol-orange)](https://modelcontextprotocol.io/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Platforms](https://img.shields.io/badge/Platforms-macOS%20%7C%20Windows-lightgrey)]()
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

*Upload source documents. Claude converts and authors them directly into your Caseware Cloud engagement.*

</div>

---

## Overview

Upload a Word, Excel, PDF, or PowerPoint file to Claude Desktop and the extension handles the rest — reading the content, detecting the document type, and authoring it as a validated JSON payload directly into Caseware Cloud as a checklist, query, or letter.

The extension runs as an MCP (Model Context Protocol) server, giving Claude Desktop access to document conversion, payload construction, a local knowledge graph, and a full Caseware Cloud API proxy — all from a single `.mcpb` package with zero manual setup.

```
  Upload .docx/.xlsx/.pdf/.pptx
           |
           v
  Read & Analyse -----> Detect Type (checklist / query / letter)
           |                  |
           v                  v
       Build Validated JSON Payload (build_payload)
                |
                v     (chunked, sequential -save calls)
        Submit to Caseware Cloud
                |
                v
       Caseware Cloud Engagement
  (checklists, queries, letters)
```

### What Gets Created

| Document Type | Caseware Cloud Output |
|--------------|----------------------|
| **Checklist** | Groups, headings, procedures with response types (picklist, text, date, number), auto-generated conclusions, engagement signoff |
| **Query** | Question sets with text input and file upload columns |
| **Letter** | Formatted sections with dynamic formulas (`engprop()`, `collaborate()`, `wording()`), date/staff placeholders |

### Key Capabilities

- **Autonomous execution** — the agent runs end-to-end without user prompts; it applies sensible defaults when information is ambiguous
- **Response type detection** — a 4-priority rule engine (explicit options > keyword patterns > semantic analysis > fallback) assigns the correct response type to every procedure
- **Automatic bullet/number stripping** — leading indicators (`1.`, `a.`, `ii.`, `(1)`, `*`, `-`, etc.) are stripped during `build_payload`
- **Auto-generated conclusions** — the API adds platform conclusions via `includeConclusion: true`; no manual conclusion items needed
- **Chunked submission** — large checklists (>20 procedures per chunk) are automatically split and submitted sequentially
- **Evaluator-optimizer loop** — payloads are validated against depth, type, and response rules before submission with up to 3 fix iterations
- **Orchestrator-workers pattern** — files with 400+ procedures are split across parallel workers coordinated by an orchestrator
- **Knowledge graph tracking** — local SQLite graph database tracks workflows, entities, and relationships across engagements

---

## Installation

**Supported platforms:** macOS and Windows (zero-install — Claude Desktop manages Python and dependencies via [uv](https://docs.astral.sh/uv/))

1. Download or build the `caseware-authoring-tools-5.0.0.mcpb` file
2. **Double-click** the file or **drag it** into Claude Desktop
3. Configure in **Settings > Extensions > Caseware Authoring Tools**:

| Setting | Description | Required |
|---------|-------------|----------|
| **Knowledge Graph Database Location** | Directory for the SQLite database. Defaults to `~/.local/share/caseware-authoring-tools/` | No |
| **Caseware Cloud Engagement URL** | MCP endpoint URL (e.g., `https://us.cwcloudpartner.com/.../api/v1.16.0/mcp`) | For Cloud tools |
| **Bearer Token** | Authentication token for the engagement (stored securely by Claude Desktop) | For Cloud tools |

Knowledge Graph tools work without any configuration. Cloud tools require the engagement URL and bearer token.

---

## Tools

The extension exposes 28 tools across four categories.

### Document Conversion

| Tool | Description |
|------|-------------|
| `convert_document` | Extract text content from a document (Word, Excel, PowerPoint) and detect its type |
| `batch_convert` | Extract text content from multiple documents in one operation |
| `list_supported_formats` | List all supported file formats |

### Payload Builder

| Tool | Description |
|------|-------------|
| `build_payload` | Build a validated Caseware Cloud payload from a procedure outline. Handles bullet stripping, response type validation, chunking, and `includeConclusion` flag |

### Knowledge Graph

Track authoring workflows with a local SQLite graph database. Supports entity creation, relations, observations, querying, full-text search, and Mermaid diagram export.

| Tool | Description |
|------|-------------|
| `kg_create_entities` | Create entities (workflows, tasks, documents, risks, findings) |
| `kg_create_relations` | Create directed relations between entities |
| `kg_add_observations` | Add timestamped observations to an entity |
| `kg_query` | Query by glob pattern, entity type, or relationship |
| `kg_search` | Full-text search across all entities and observations |
| `kg_export_mermaid` | Export a Mermaid flowchart diagram for a workflow |

### Reference Guides

| Tool | Description |
|------|-------------|
| `list_references` | List all available authoring reference guides with descriptions |
| `load_reference` | Load a reference guide by name, with optional section filtering |

### Caseware Cloud (requires connection)

These tools proxy requests to the Caseware Cloud MCP API. They require a valid engagement URL and bearer token configured in extension settings.

| Tool | Description |
|------|-------------|
| `initialize_authoring_tools` | Show overview of available tools and how to get started |
| `document-manager` | List and manage engagement documents (with `includeHidden` support) |
| `engagement-properties` | Read engagement properties |
| `checklist-save` / `checklist-get` | Author and retrieve checklists |
| `query-save` / `query-get` | Author and retrieve queries |
| `statement-save` / `statement-get` | Author and retrieve letters |
| `controls-get` / `controls-save` | Manage controls |
| `risks-get` / `risks-save` | Manage risks |
| `trial-balance-get` | Retrieve trial balance data |
| `materiality-get` | Retrieve materiality data |
| `accounts-assign` | Assign accounts |
| `adjustments-get` | Retrieve adjustments |
| `document-get` | Get document content |
| `issues-get` | Retrieve issues |

---

## Prompts

Pre-built prompts accessible from the Claude Desktop prompt menu (15 prompts total):

### Workflows

| Prompt | Description |
|--------|-------------|
| `workflow-full` | Full end-to-end authoring (convert, validate, author, report) |
| `workflow-convert` | Read and analyse source documents — text extraction, structure analysis, procedure outline |
| `workflow-author` | Author converted content to Caseware Cloud — evaluator-optimizer loop, chunking, reporting |
| `workflow-identify-type` | Classify documents as checklist, query, or letter using weighted scoring |
| `workflow-edit` | Edit existing documents in Caseware Cloud |
| `workflow-visualize` | Visualize Knowledge Graph workflows as Mermaid flowcharts |

### Reference Guides

| Prompt | Description |
|--------|-------------|
| `reference-hierarchy-rules` | Depth marker system (`[D0]`-`[D4]`, `[R]`, `[C]`, `[G]`) and validation rules |
| `reference-checklist-authoring` | Checklist payload structure, response type detection, and chunking strategy |
| `reference-query-authoring` | Query payload structure with question sets and response columns |
| `reference-letter-authoring` | Letter structure, two-step creation, and dynamic elements |
| `reference-payload-schemas` | Consolidated JSON payload schemas for all document types |
| `reference-outline-format` | Procedure outline schema for the `build_payload` tool |
| `reference-knowledge-graph` | Knowledge Graph entity naming, relation types, and CLI usage |
| `reference-caseware-cloud-mcp` | Complete Caseware Cloud MCP API reference |
| `reference-document-type-detection` | Weighted scoring algorithm for document type classification |

---

## Depth Marker System

The extension uses a depth marker system to map document structure to Caseware Cloud's hierarchy:

| Marker | Purpose | Valid Types |
|--------|---------|-------------|
| `[D0]` | Top-level container | `group` |
| `[D1]` | First nesting level | `group` (sub-group), `heading`, `procedure` |
| `[D2]` | Second nesting level | `heading`, `procedure` |
| `[D3]` | Third nesting level | `heading`, `procedure` |
| `[D4]` | Fourth nesting level (max) | `procedure` only |
| `[R]` | Response configuration | Procedure requires a response type |
| `[G]` | Guidance text | Populates guidance field |

**Validation rules:** Max depth is 4, depth can only increase by 1 per level, `group` type only at depth 0-1, all branches must terminate in a procedure with `[R]`.

### Structural Examples

```
# Pattern 1: Simple Flat (2 levels)
[D0] Group Title
  [D1] Procedure text [R]

# Pattern 2: Standard (3 levels)
[D0] Group Title
  [D1] Heading Title
    [D2] Procedure text [R]

# Pattern 3: Deep Nesting (5 levels)
[D0] Group Title
  [D1] Sub-Group Title
    [D2] Heading Title
      [D3] Sub-Heading
        [D4] Procedure text [R]
```

---

## Response Type Detection

The agent determines each procedure's response type using a strict 4-priority cascade — it stops at the first match:

| Priority | Method | Example |
|----------|--------|---------|
| **1** | Explicit inline choices in the text | "public or private?" -> `["Public", "Private", "Not Applicable"]` |
| **2** | First-word keyword matching | "Describe..." -> `text`, "Calculate..." -> `number`, "Verify..." -> `choice` |
| **3** | Semantic analysis of the full text | Questions asking for narrative -> `text`, quantities -> `number` |
| **4** | Fallback (last resort) | `Yes / No / Not Applicable` picklist |

If >20% of procedures fall to Priority 4 fallback, the agent re-evaluates its detection.

---

## Project Structure

```
claude-authoring/
|-- claude-authoring-all-os-V5.0/          # Current extension (packed into .mcpb)
|   |-- manifest.json                      # MCPB v0.4 manifest (uv server type)
|   |-- icon.png                           # Extension icon
|   |-- README.md                          # Bundled extension readme
|   +-- server/
|       |-- main.py                        # Entry point
|       |-- pyproject.toml                 # Python dependencies (mcp, httpx, networkx)
|       |-- uv.lock                        # Locked dependency versions
|       |-- caseware_authoring_tools/
|       |   |-- server.py                  # MCP server — tool handlers, prompts, instructions
|       |   |-- converter.py               # Document conversion (markitdown)
|       |   |-- cloud_proxy.py             # Caseware Cloud MCP HTTP proxy
|       |   |-- payload_builder.py         # Payload construction, validation, chunking
|       |   +-- knowledge_graph/           # Graph database package
|       |       |-- core/                  # Models and graph engine
|       |       |-- storage/               # SQLite + JSON backends, migration
|       |       |-- algorithms/            # Graph traversal algorithms
|       |       |-- export/                # Mermaid, DOT, GraphML exporters
|       |       |-- visualize/             # Figma visualization helpers
|       |       +-- cli/                   # CLI entry point
|       |-- references/                    # 18 authoring reference guides (loaded by tools)
|       +-- tests/                         # Test suite (excluded from .mcpb package)
|-- Preview Verions/                       # Previous extension versions and WP MCP
|   |-- claude-authoring-all-os/           # V1 extension (archived)
|   |-- Previous Versions/                 # Earlier builds
|   +-- working-papers-mcp/               # Working Papers MCP proxy (reserved for V2)
|-- build-extension.sh                     # Validate and pack .mcpb
|-- claude-authoring-all-os-V5.0.mcpb     # Built extension package (~8.3 MB)
|-- CLAUDE.md                              # Agent behavior rules and authoring instructions
+-- README.md                              # This file
```

---

## Building

### Quick Build

```bash
./build-extension.sh
```

> **Note:** The build script currently points at `claude-authoring-all-os/`. To build V5.0, either update the script or run the manual build below.

### Manual Build

Requires the [`mcpb`](https://www.npmjs.com/package/@anthropic-ai/mcpb) CLI:

```bash
npm install -g @anthropic-ai/mcpb
cd claude-authoring-all-os-V5.0
mcpb validate manifest.json
mcpb pack
```

Both approaches validate the manifest against MCPB v0.4 spec and produce a `.mcpb` file.

---

## Development

The server is a Python project managed by [uv](https://docs.astral.sh/uv/):

```bash
cd claude-authoring-all-os-V5.0/server
uv sync
uv run python main.py
```

### Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `mcp` | >=1.26.0 | Model Context Protocol SDK |
| `httpx` | >=0.27.0 | Async HTTP client for Cloud proxy |
| `networkx` | >=3.0 | Knowledge Graph algorithms |

### Running Tests

```bash
cd claude-authoring-all-os-V5.0/server
uv run --with pytest python -m pytest tests/
```

### Knowledge Graph CLI

The knowledge graph can also be used standalone from the command line:

```bash
cd claude-authoring-all-os-V5.0/server
uv run python -m caseware_authoring_tools.knowledge_graph

# Examples
uv run python -m caseware_authoring_tools.knowledge_graph create-entities '[{"name": "AA_W_20260123", "type": "workflow"}]'
uv run python -m caseware_authoring_tools.knowledge_graph query --type workflow
uv run python -m caseware_authoring_tools.knowledge_graph search "revenue"
uv run python -m caseware_authoring_tools.knowledge_graph export-mermaid "AA_W_20260123"
```

### Entity Naming Convention

Entities follow the pattern `{AgentCode}_{TypeCode}_{Identifier}`:
- **Agent codes:** RSA (Risk), AA (Authoring), AEA (Evidence), FSA (Financial)
- **Type codes:** W (Workflow), T (Task), D (Document), Tool, O (Outcome), F (Finding), R (Risk)

Example: `AA_W_20260119`, `RSA_R_GoingConcern`

---

## Error Handling

The agent enforces hard-fail conditions that halt execution immediately:

| Error Code | Trigger |
|------------|---------|
| `CONTENT_LOSS_EXCEEDED` | Parsing lost >10% of procedures |
| `MISSING_RESPONSE_TYPE` | Procedure has no `rows` array |
| `INVALID_DEPTH` | Depth exceeds 4 or depth jump >1 |
| `INVALID_TYPE_AT_DEPTH` | Type not allowed at specified depth (e.g., group at depth 2+) |
| `NUMBER_CONFLICT` | Document number already exists in engagement |
| `PAYLOAD_TRUNCATED` | Response contains fewer procedures than submitted |
| `MCP_RETRY_EXHAUSTED` | 3 consecutive MCP failures after retry |

Transient errors (network timeouts, rate limits, 5xx) are retried with exponential backoff. Authentication (401) and bad request (400) errors fail immediately.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Cloud tools show "not connected" | Enter Engagement URL and Bearer Token in extension settings |
| Bearer token expired | Generate a new token from Caseware Cloud |
| Procedures truncated after save | `build_payload` handles chunking automatically; if still truncated, check for `PAYLOAD_TRUNCATED` error |
| Extension not loading after reinstall | User config is reset on reinstall — re-enter settings |
| `mcpb` not found | `npm install -g @anthropic-ai/mcpb` |
| Knowledge graph database locked | Check for other processes using the SQLite file |
| Binary files not converting | Ensure you're using `convert_document` tool — Claude cannot read `.docx`/`.xlsx`/`.pptx` natively |

---

## Version History

| Version | Highlights |
|---------|-----------|
| **5.0.0** | Current release — unified extension with reference guides as tools, `workflow-edit` and `workflow-visualize` prompts, pipe-delimited choice parsing, auto-generated conclusions |
| **3.0.0** | Code review fixes, pipe delimiter for response choices, bullet/number stripping in `build_payload` |
| **1.2.0** | MCPB v0.4 migration, cross-platform support, knowledge graph with SQLite backend |
| **1.0.0** | Initial release — document conversion, checklist/query/letter authoring |

---

## License

MIT — Caseware International Inc.

## Acknowledgments

Built with [Model Context Protocol](https://modelcontextprotocol.io/) and [Claude Desktop](https://claude.ai).

**Maintainer:** Jason Bradley (Caseware International)
