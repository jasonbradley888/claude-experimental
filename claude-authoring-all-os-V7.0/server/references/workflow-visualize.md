# Visualize Workflow

Generate a Mermaid flowchart visualization from the Knowledge Graph.

**Workflow name:** (provide a workflow entity name, e.g. `AA_W_20260314`)

---

## Prerequisites

- Knowledge Graph tools available (`kg_query`, `kg_export_mermaid`)
- Optional: Figma MCP server for diagram rendering

---

## Steps

**Step 1:** Query the Knowledge Graph for workflow data.

Use `kg_query` with `entity_type: "workflow"` to list all workflows, or with a specific pattern:

```json
{"pattern": "AA_W_*"}
```

To get a specific workflow and its related entities:

```json
{"related_to": "AA_W_20260314"}
```

**Step 2:** Export a Mermaid diagram using `kg_export_mermaid`:

```json
{"root": "AA_W_20260314", "direction": "LR"}
```

**Step 3:** Review and refine the Mermaid output. Apply entity shapes and colors:

| Entity Type | Shape | Color |
|-------------|-------|-------|
| Workflow | Stadium/pill | Blue |
| Task | Rectangle | Green |
| Tool | Rectangle | Purple |
| Document | Document shape | Orange |
| Outcome | Stadium/pill | Gold |

**Step 4:** If Figma MCP is available, generate a Figma diagram with LR direction.

**Step 5:** Present the result with a workflow summary table:

| Metric | Value |
|--------|-------|
| Workflow | Entity name |
| Tasks | Count |
| Tools used | List |
| Documents | Count |
| Outcomes | Count |

---

## Example Output

```mermaid
graph LR
    subgraph WF["Full Authoring Workflow"]
        D[Discovery] --> C1[Convert Doc 1]
        C1 --> C2[Convert Doc 2]
        C2 --> V[Validate All]
        V --> A1[Author Checklist 1]
        A1 --> A2[Author Checklist 2]
    end

    MD[/"markitdown MCP<br/>(MCP Server)"/]
    C1 -.-> MD
    C2 -.-> MD

    CW[/"caseware_cloud MCP<br/>(MCP Server)"/]
    A1 -.-> CW
    A2 -.-> CW

    A2 --> OUT((Workflow Complete))

    style MD fill:#9370DB
    style CW fill:#9370DB
    style OUT fill:#FFD700
```

---

## Notes

- If no workflow name is provided, list all available workflows and let the user choose
- Diagrams exported via Figma are **ephemeral** — they must be manually saved in the Figma interface
- For complex workflows with many entities, consider filtering by relation type (e.g., only `contains` or `uses` relations)
