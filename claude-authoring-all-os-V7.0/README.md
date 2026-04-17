# Caseware Authoring Tools — Claude Desktop Extension

Unified authoring tools: Knowledge Graph, reference guides, and Caseware Cloud integration. Author checklists, queries, and letters — all from a single extension.

## Installation

Double-click the `.mcpb` file or drag it into Claude Desktop to install.

## Configuration

| Setting | Description |
|---------|-------------|
| **Knowledge Graph Database Location** | Directory for the SQLite database. Defaults to `~/.local/share/caseware-authoring-tools/knowledge_graph.db` |
| **Caseware Cloud Engagement URL** | MCP endpoint URL for your Caseware Cloud engagement. Leave blank to use KG tools only. |
| **Bearer Token** | Authentication token for the Caseware Cloud engagement. |

To configure: Open Claude Desktop Settings > Extensions > Caseware Authoring Tools.

## Tools

### Local Tools (always available)

| Tool | Description |
|------|-------------|
| **initialize_authoring_tools** | Overview of available tools and getting started guide |
| **kg_create_entities** | Create entities in the Knowledge Graph |
| **kg_create_relations** | Create relations between Knowledge Graph entities |
| **kg_add_observations** | Add observations to a Knowledge Graph entity |
| **kg_query** | Query entities by pattern, type, or relationship |
| **kg_search** | Full-text search across the Knowledge Graph |
| **kg_export_mermaid** | Export a Mermaid diagram from the Knowledge Graph |

### Caseware Cloud Tools (requires engagement connection)

| Tool | Description |
|------|-------------|
| **document-manager** | Manage engagement documents |
| **engagement-properties** | Read engagement properties |
| **checklist-save / checklist-get** | Author and retrieve checklists |
| **query-save / query-get** | Author and retrieve queries |
| **statement-save / statement-get** | Author and retrieve letters |
| **controls-get / controls-save** | Manage controls |
| **risks-get / risks-save** | Manage risks |
| **trial-balance-get** | Retrieve trial balance data |
| **materiality-get** | Retrieve materiality data |
| **accounts-assign** | Assign accounts |

## Reference Prompts

| Prompt | Description |
|--------|-------------|
| **reference-hierarchy-rules** | Depth marker system and validation rules |
| **reference-checklist-authoring** | Checklist payload structure and chunking |
| **reference-query-authoring** | Query payload structure and templating |
| **reference-letter-authoring** | Letter structure and dynamic elements |
| **reference-knowledge-graph** | Knowledge Graph naming and CLI usage |
| **reference-caseware-cloud-mcp** | Complete Caseware Cloud MCP API reference |
| **reference-document-type-detection** | Weighted scoring algorithm for document type classification |

## Requirements

- Claude Desktop with extension support
- UV runtime (bundled with Claude Desktop)

## Full Workflow

1. **Upload documents** — Claude reads and analyses the content directly
2. **Author** — Claude builds JSON payloads and authors content into your Caseware Cloud engagement
3. **Track** — Log workflows in the Knowledge Graph for audit trail
