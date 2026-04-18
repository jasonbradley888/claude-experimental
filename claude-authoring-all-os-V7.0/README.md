# Claude CWI Experimental — Caseware Gateway V7.0

Unified MCP gateway packaged as a Claude Desktop extension (`.mcpb`). Author checklists, queries, and letters to Caseware Cloud; analyse `.cwp`/`.cvw` CaseView templates fully offline; manage engagements, workflow, analytics, and SE API — all from a single connection.

**Full configuration → 89 tools across 7 categories, plus 15 reference/workflow prompts.**

## Installation

Double-click the `.mcpb` file or drag it into Claude Desktop. Configure under **Settings → Extensions → Claude CWI Experimental**.

## Configuration

All fields are optional. The gateway exposes only the tool categories that are fully configured.

| Setting | Required for | Notes |
|---|---|---|
| **Knowledge Graph Database Location** | KG tools | Defaults to `~/.local/share/caseware-authoring-tools/knowledge_graph.db` |
| **Caseware Cloud Engagement URL** | Cloud authoring proxy | e.g. `https://us.cwcloudpartner.com/.../api/v1.16.0/mcp` |
| **Bearer Token (Legacy)** | Cloud authoring proxy | Static token; prefer client credentials below |
| **Caseware Host** | Engagement / Workflow / Analytics / SE | e.g. `https://us.cwcloudpartner.com` |
| **Firm Name** | Engagement / Workflow / Analytics / SE | Caseware firm identifier |
| **Client ID** | Engagement / Workflow / Analytics / SE | OAuth2 client ID |
| **Client Secret** | Engagement / Workflow / Analytics / SE | OAuth2 client secret |

Local authoring and the CWP Template Reader work with **zero configuration**.

## Tools

### Local authoring (11, always-on)

| Tool | Description |
|---|---|
| `initialize_authoring_tools` | Show overview of available tools and how to get started |
| `kg_create_entities` | Create entities in the Knowledge Graph |
| `kg_create_relations` | Create relations between Knowledge Graph entities |
| `kg_add_observations` | Add observations to a Knowledge Graph entity |
| `kg_query` | Query entities by pattern, type, or relationship |
| `kg_search` | Full-text search across the Knowledge Graph |
| `kg_export_mermaid` | Export a Mermaid diagram from the Knowledge Graph |
| `list_references` | List available authoring reference guides |
| `load_reference` | Load an authoring reference guide by name |
| `build_payload` | Build validated Caseware Cloud payload from a procedure outline |
| `convert_document` | Extract text content from a document and detect its type |

### CWP Template Reader (15, always-on, 100% offline)

Parse `.cwp` template packages and standalone `.cvw` files without a Working Papers installation. Cross-platform (ZIP + XML + OLE2 only).

#### `.cwp` package tools (10)

| Tool | Description |
|---|---|
| `analyze_template_package` | Overview: metadata + template list with cell counts |
| `get_package_manifest` | Full `manifest.xml` + `<File>` inventory with MD5 hashes, cross-referenced to inner zip |
| `get_file_inventory` | Every inner-zip file grouped by category (templates, styles, embedded docs, dBASE, images…) with manifest drift detection |
| `list_template_cells` | All cell/field names for one template, with prefix analysis |
| `search_template_cells` | Regex search across all templates' cell names |
| `get_template_structure` | OLE2 stream sizes + bookmarks + cell count for one template |
| `get_document_outline` | Structured bookmarks + sections + paragraph offsets from `Index/Bookmarks`, `Index/Sect`, `Index/Para` |
| `export_template_cells` | Export cell inventory to JSON or CSV |
| `export_template_structure` | Full per-template structural dump to JSON |
| `export_full_package` | One-shot comprehensive extraction of an entire package |

#### Standalone `.cvw` tools (5)

For `.cvw` files extracted or received outside a `.cwp` container:

| Tool | Description |
|---|---|
| `analyze_cvw_file` | Structural overview of a standalone `.cvw` |
| `list_cvw_cells` | Attempt cell extraction (may be empty if `Index/Cell` is encoded) |
| `get_cvw_structure` | OLE2 stream metadata |
| `get_cvw_document_outline` | Structured bookmarks + sections + paragraph offsets |
| `export_cvw_file` | Comprehensive extraction — cells, bookmarks, outline, readable strings from every stream |

**Defensive parsing:** malformed OLE2 bytes surface as `parse_warnings` rather than raising; `manifest.xml` falls back to latin-1 when UTF-8 fails. Verified on Frazier-Deeter (43 templates, 288 files) and BT Examinations (41 templates, 171 files).

### Cloud authoring proxy (17)

Requires **Engagement URL** + **Bearer Token**.

| Tool | Description |
|---|---|
| `document-manager` | Manage engagement documents |
| `engagement-properties` | Read engagement properties |
| `checklist-save` / `checklist-get` | Author and retrieve checklists |
| `query-save` / `query-get` | Author and retrieve queries |
| `statement-save` / `statement-get` | Author and retrieve letters |
| `controls-save` / `controls-get` | Manage controls |
| `risks-save` / `risks-get` | Manage risks |
| `trial-balance-get` | Retrieve trial balance data |
| `materiality-get` | Retrieve materiality data |
| `accounts-assign` | Assign accounts |
| `adjustments-get` | Retrieve adjustments |
| `document-get` | Get document content |
| `issues-get` | Retrieve issues |

### SE API (8)

Requires **Host** + **Firm Name** + **Client ID / Secret**.

| Tool | Description |
|---|---|
| `file-upload` / `file-download` | File transfers on the engagement |
| `suggestion-get` / `suggestion-commit` | Pending suggestion sets |
| `risk-assessment-get` / `risk-assessment-save` | Risk assessments |
| `tags-get` / `tags-save` | Tags and categories |

### Engagement API (11)

| Tool | Description |
|---|---|
| `engagement-get` | Engagement properties and details |
| `engagement-create` | Create a new engagement from a firm template |
| `engagement-lock` / `engagement-unlock` | Lock / unlock the engagement |
| `engagement-rollforward` | Roll forward to a new period |
| `engagement-copyobjects` | Copy procedures / documents from another engagement |
| `users-get` | List staff members |
| `roles-get` | List available roles and role sets |
| `staff-assign` | Assign staff to a role |
| `firm-templates-get` | List available engagement templates |
| `visibility-get` | Visibility rules for the engagement |

### Workflow API (10)

| Tool | Description |
|---|---|
| `attachments-get` / `attachments-save` / `attachments-sign` | Procedure / document attachments |
| `document-grant-access` | Grant staff access to a document |
| `document-publish` | Publish a completed document |
| `document-sign` | Sign off a document as reviewed |
| `events-get` / `events-save` | Events and milestones |
| `history-get` | Audit trail of changes |
| `history-files` | Deleted / modified files history |

### Analytics API (17)

Catalog: `analytics-get-catalog`, `analytics-get-catalog-by-analytic-id`, `analytics-get-predefined-configs`, `analytics-get-predefined-config-by-id`, `analytics-get-predefined-config-by-analytic-id`, `analytics-get-predefined-configs-by-tags`, `analytics-get-permissions`.

Execution: `analytics-trigger`, `analytics-get-status`, `analytics-get-status-grouped-by-dataset-type`, `analytics-get-execution-details`, `analytics-get-execution-details-by-config-ids`, `analytics-get-execution-details-by-result-id`.

Results: `analytics-get-dataset`, `analytics-get-notebook-content`, `analytics-get-notebook-data`, `analytics-delete-datasets`.

## Reference prompts (15)

| Prompt | Description |
|---|---|
| `initialize-authoring-tools` | Full overview and suggested first steps |
| `workflow-convert` | Read source documents, extract structure, produce a procedure outline |
| `workflow-author` | Author to Caseware Cloud via evaluator-optimizer loop and chunking |
| `workflow-full` | End-to-end: read → analyse → author → report |
| `workflow-identify-type` | Document type decision tree (checklist / query / letter) |
| `workflow-visualize` | Generate Mermaid flowcharts from Knowledge Graph data |
| `reference-hierarchy-rules` | Depth markers `[D0]`–`[D4]`, `[R]`, `[C]`, `[G]` and validation rules |
| `reference-checklist-authoring` | Checklist payload structure, response-type detection, chunking |
| `reference-query-authoring` | Query payload structure and templating |
| `reference-letter-authoring` | Letter two-step creation and dynamic elements |
| `reference-knowledge-graph` | KG entity naming, relation types, CLI |
| `reference-caseware-cloud-mcp` | Complete Caseware Cloud MCP API reference |
| `reference-document-type-detection` | Weighted scoring for type classification |
| `reference-payload-schemas` | Consolidated JSON payload schemas |
| `reference-outline-format` | Procedure outline schema for `build_payload` |

## Requirements

- Claude Desktop with extension support (MCPB v0.4)
- Python ≥ 3.10 (UV runtime bundled with Claude Desktop)
- macOS or Windows

## Full Workflow

1. **Read** — `convert_document` or native PDF read to extract source content
2. **Outline** — produce a depth-marked procedure outline
3. **Build** — `build_payload` validates, strips numbering, left-aligns HTML, and chunks
4. **Author** — `checklist-save` / `query-save` / `statement-save` to Caseware Cloud
5. **Track** — log the workflow in the Knowledge Graph for audit trail
6. **(Optional) Reference templates** — use the CWP Template Reader to export cell inventories and outlines from the corresponding firm template for cross-referencing
