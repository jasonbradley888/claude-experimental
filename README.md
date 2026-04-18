# Caseware Gateway — V7.0

![Extension Version](https://img.shields.io/badge/version-7.0.0-blue.svg)
![Platforms](https://img.shields.io/badge/platforms-macOS%20%7C%20Windows-lightgrey.svg)
![Python](https://img.shields.io/badge/python-%3E%3D3.10-yellow.svg)

A unified MCP gateway for Caseware Cloud **and** CaseWare Working Papers, packaged as a single Claude Desktop extension (`.mcpb`). Author checklists, queries, and letters to the Cloud; analyse `.cwp` template packages and standalone `.cvw` files fully offline; manage engagements, workflow, analytics, and SE API operations from one connection.

At full configuration the gateway exposes **89 tools** across 7 categories plus 15 reference/workflow prompts.

---

## Tool Categories

| Category | Count | Always-on? | Scope |
|---|---|---|---|
| **Local authoring** | 11 | ✅ | Knowledge Graph (6), payload builder, document converter, references, initialiser |
| **CWP Template Reader** | 15 | ✅ | Offline analysis of `.cwp` packages and standalone `.cvw` files |
| **Cloud proxy (authoring)** | 17 | Requires engagement URL + bearer token | Checklist / query / letter / controls / risks / trial balance / materiality / adjustments / issues |
| **SE API** | 8 | Requires host + client credentials | File upload/download, suggestions, risk assessments, tags |
| **Engagement API** | 11 | Requires host + client credentials | Create / lock / rollforward / copy, users, roles, staff, firm templates, visibility |
| **Workflow API** | 10 | Requires host + client credentials | Attachments, document sign/publish/grant, events, milestones, audit history |
| **Analytics API** | 17 | Requires host + client credentials | Catalog, predefined configs, trigger, status, execution details, notebooks, permissions |

**26 tools** work without any Cloud credentials (local authoring + template reader). The remaining 63 activate when the corresponding configuration is provided.

---

## CWP Template Reader — Offline Template Analysis

The template reader is **100% offline** — no Working Papers installation, no Windows, no COM. Parses ZIP, XML, and OLE2 structures directly on macOS, Linux, or Windows.

### What it extracts

For a `.cwp` package:

- **Package manifest** — every element of `manifest.xml`, plus the complete `<File>` inventory with MD5 hashes and cross-references against the inner zip (flagging manifest/zip drift).
- **File inventory** — every file inside `OptionsData.cwp`, grouped by category: caseview templates, styles (`.sty`/`.cgf`), embedded documents (`.docx`/`.xlsx`/`.pdf`), dBASE tables (`.dbf`/`.cdx`/`.fpt`), images, and more.
- **Template cell/field inventory** — the dynamic field names used in each CaseView template (e.g. `CONTACT1`, `COMPANYNA`, `ISSUEDATE1`), with prefix analysis.
- **Document outline** — structured bookmarks, section index, and paragraph byte offsets, parsed from the OLE2 `Index/Bookmarks`, `Index/Sect`, and `Index/Para` streams.
- **Structural dumps** — per-template OLE2 stream sizes, readable strings from every stream, and full-package JSON exports suitable as a Cloud-authoring reference.

### `.cwp` tools (10)

| Tool | Purpose |
|---|---|
| `analyze_template_package` | Overview: metadata, template list, cell counts per template |
| `get_package_manifest` | Full manifest.xml + file inventory with MD5 hashes and zip cross-reference |
| `get_file_inventory` | Every inner-zip file, grouped by category, with manifest drift detection |
| `list_template_cells` | All cell/field names for one template, with prefix analysis |
| `search_template_cells` | Regex search across all templates' cell names |
| `get_template_structure` | OLE2 stream sizes, bookmarks, cell count for one template |
| `get_document_outline` | Structured bookmarks + sections + paragraph offsets for one template |
| `export_template_cells` | Export cell inventory to JSON or CSV |
| `export_template_structure` | Full per-template structural dump to JSON |
| `export_full_package` | One-shot comprehensive extraction of the entire package |

### Standalone `.cvw` tools (5)

For `.cvw` files extracted or received outside a package:

| Tool | Purpose |
|---|---|
| `analyze_cvw_file` | Structural overview: stream count, cell count, bookmarks, size |
| `list_cvw_cells` | Attempt cell extraction (may be empty if Index/Cell is encoded) |
| `get_cvw_structure` | OLE2 stream metadata |
| `get_cvw_document_outline` | Structured bookmarks + sections + paragraph offsets |
| `export_cvw_file` | Comprehensive extraction — cells, bookmarks, outline, readable strings from every stream |

### Defensive parsing

All OLE2 parsers surface malformed bytes as `parse_warnings` rather than raising. `manifest.xml` falls back to latin-1 when UTF-8 fails. Verified against real-world packages:

- **Frazier-Deeter** — 43 templates, 288 inner files
- **BT Examinations** — 41 templates, 171 inner files

Every template outline parses without raising; all paragraph offsets are monotonic ascending.

---

## Authoring Capabilities (Cloud)

Author three document types directly into a Caseware Cloud engagement via MCP proxy:

- **Checklists** — groups → headings → procedures → auto-generated conclusions, with response type detection (text / number / date / picklist / multi-picklist), depth markers `[D0]`–`[D4]`, automatic leading-number stripping, left-aligned HTML wrapping, default response settings, and dynamic element detection (`engprop()`, `collaborate()`, `wording()`, placeholders).
- **Queries** — question sets (D0) + questions (D1) with text input + file upload columns. Document number with `Q` suffix.
- **Letters** — flat `content` sections, two-step creation (document map then sections), dynamic bracketed-text conversion to formulas and placeholders.

All payloads go through `build_payload`, which validates structure, strips numbering, wraps procedure/conclusion HTML, injects `includeConclusion: true`, and chunks large payloads at group boundaries.

---

## Engagement Management

- `engagement-create` from a firm template, `engagement-lock`/`unlock`, `engagement-rollforward`, `engagement-copyobjects` from a prior engagement.
- `users-get`, `roles-get`, `staff-assign` to map staff to roles.
- `firm-templates-get` to discover available templates, `visibility-get` for rules.
- `attachments-get`/`save`/`sign`, `document-sign`/`publish`/`grant-access`, `events-get`/`save`, `history-get`/`files` for audit trail.

---

## Analytics

17 tools across catalog discovery, predefined configurations, triggering, execution monitoring, and result retrieval (dataset URLs, full notebook content, structured notebook data).

---

## SE API

8 tools for file upload/download, suggestion retrieval and commit, risk-assessment get/save, and tag/category management.

---

## Knowledge Graph

Local SQLite-backed workflow tracking, shared with the Python CLI (`~/Documents/Agentic Workflows/authoring-agent/scripts/local_knowledge_graph.py`).

- `kg_create_entities`, `kg_create_relations`, `kg_add_observations`
- `kg_query` (pattern / type / relation), `kg_search` (full-text)
- `kg_export_mermaid` for Mermaid flowchart visualisation

Entity naming: `{AgentCode}_{TypeCode}_{Identifier}` — e.g. `AA_W_20260418`, `RSA_R_GoingConcern`.

---

## Reference Prompts (15)

Workflow guides and authoring references loaded on demand:

- `initialize-authoring-tools`
- `workflow-convert` · `workflow-author` · `workflow-full` · `workflow-identify-type` · `workflow-visualize`
- `reference-hierarchy-rules` · `reference-checklist-authoring` · `reference-query-authoring` · `reference-letter-authoring`
- `reference-knowledge-graph` · `reference-caseware-cloud-mcp` · `reference-document-type-detection` · `reference-payload-schemas` · `reference-outline-format`

---

## Installation

1. Build (or download) the `.mcpb` bundle — see **Build** below.
2. Double-click the `.mcpb` file, or drag it into Claude Desktop.
3. Open **Claude Desktop → Settings → Extensions → Claude CWI Experimental** and fill in configuration.

## Configuration

All fields are optional — the gateway will start with whatever is provided and expose only the tool categories that are fully configured.

| Setting | Required for | Notes |
|---|---|---|
| **Knowledge Graph Database Location** | KG tools | Defaults to `~/.local/share/caseware-authoring-tools/knowledge_graph.db` |
| **Caseware Cloud Engagement URL** | Cloud authoring proxy | MCP endpoint — e.g. `https://us.cwcloudpartner.com/.../api/v1.16.0/mcp` |
| **Bearer Token** | Cloud authoring proxy (legacy) | Static bearer token; prefer client credentials |
| **Caseware Host** | Engagement / Workflow / Analytics / SE | e.g. `https://us.cwcloudpartner.com` |
| **Firm Name** | Engagement / Workflow / Analytics / SE | Caseware firm identifier |
| **Client ID** | Engagement / Workflow / Analytics / SE | OAuth2 client ID |
| **Client Secret** | Engagement / Workflow / Analytics / SE | OAuth2 client secret |

**CWP Template Reader** and **local authoring** tools work with zero configuration.

---

## Build

Requires [`@anthropic-ai/mcpb`](https://www.npmjs.com/package/@anthropic-ai/mcpb):

```bash
npm install -g @anthropic-ai/mcpb
./build-extension.sh
```

Produces `claude-CWI-experimental-7.0.0.mcpb` in the repo root.

## Repository Layout

```
claude-CWI-experimental/
├── build-extension.sh                   # mcpb validate + pack
├── claude-CWI-experimental-7.0.1.mcpb   # prebuilt bundle
├── claude-authoring-all-os-V7.0/        # extension source
│   ├── manifest.json                    # MCPB manifest
│   ├── icon.png
│   └── server/
│       ├── main.py                      # stdio entry point
│       ├── pyproject.toml
│       └── caseware_authoring_tools/
│           ├── server.py                # MCP server + tool registry
│           ├── cloud_proxy.py           # HTTP MCP proxy to Caseware Cloud
│           ├── token_manager.py         # OAuth2 client-credentials
│           ├── payload_builder.py       # Checklist/query/letter payload builder
│           ├── converter.py             # Document → text (markitdown)
│           ├── knowledge_graph/         # Local SQLite KG (shared with Python CLI)
│           ├── cwp_reader/              # Offline .cwp / .cvw parser
│           ├── cwp_tools.py             # CWP tool adapter
│           ├── engagement_tools.py      # Engagement API (11)
│           ├── workflow_tools.py        # Workflow API (10)
│           ├── analytics_tools.py       # Analytics API (17)
│           ├── se_tools.py              # SE API (8)
│           ├── api_client.py            # Shared HTTP client
│           ├── references/              # Authoring reference prompts
│           └── tests/                   # Payload builder + CWP reader tests
└── CLAUDE.md                            # Authoring agent system prompt
```

## Requirements

- Claude Desktop with extension support (MCPB v0.4)
- Python ≥ 3.10 (UV runtime bundled with Claude Desktop)
- `olefile` (bundled) — required by CWP template cell/structure/outline tools

## Version History

- **V7.0** — CWP Template Reader with offline `.cwp`/`.cvw` analysis; richer `.cwp` extraction (`get_package_manifest`, `get_file_inventory`, `get_document_outline`, `get_cvw_document_outline`) with defensive OLE2 parsing. Unified gateway packaging across authoring, engagement, workflow, analytics, and SE API.
- **V6.0** — Numbering regex extended (`1)`, `a)`, `ii)`), left-aligned procedure HTML, default response setting, dynamic element detection for procedures and query questions, 8 new SE API tools, token manager.
- **V5.0** — Full unified extension with 28 authoring tools and 15 prompts.

## Licence

MIT.
