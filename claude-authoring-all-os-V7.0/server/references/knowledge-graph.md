# Knowledge Graph Reference

Single source of truth for KG entity naming, types, relations, observations, CLI usage, and trace schema.

---

## Entity Naming Convention

```
{AgentCode}_{TypeCode}_{Identifier}
```

### Agent Codes

| Agent | Code |
|-------|------|
| Authoring Agent | AA |
| Risk Suggestion Agent | RSA |
| Audit Evidence Agent | AEA |
| Financial Statement Agent | FSA |

### Type Codes

| Type | Code | Example |
|------|------|---------|
| Workflow | W | `AA_W_20260205` |
| Task | T | `AA_T_ValidateStructure` |
| Document | D | `AA_D_D100` |
| Tool | Tool | `AA_Tool_CasewareCloud` |
| Outcome | O | `AA_O_AuthoredChecklists` |
| Finding | F | `RSA_F_DecliningRatio` |
| Risk | R | `RSA_R_GoingConcern` |
| Control | Control | `RSA_Control_CashApproval` |
| Checklist | Checklist | `AA_Checklist_D100` |
| Evidence | Evidence | `AEA_Evidence_BankConfirmation` |
| Trace | Trace | `AA_Trace_Step1_CasewareCloud_ChecklistSave_103015` |

---

## Entity Types

| Type | Purpose | Key Observations |
|------|---------|------------------|
| workflow | Orchestrates multiple tasks | Goal, scope, status, timestamps, completion % |
| task | Individual action or step | Duration, tool calls, errors, decisions |
| document | Files processed or produced | File path, line count, document type |
| tool | MCP servers/scripts/functions | Endpoint, response time, success/failure |
| checklist | Audit checklists authored | Procedure count, groups, response types |
| outcome | Results and deliverables | Deliverables list, quality assessment |
| finding | Analysis discoveries | Metric, trend, significance |
| risk | Identified risks | Likelihood, impact, assertions |
| control | Internal controls | Type, frequency, effectiveness |
| evidence | Audit evidence items | Source, reliability, sufficiency |
| trace | MCP call observability data | See Trace Entity Schema below |

---

## Relation Types

| Relation | From → To | Description |
|----------|-----------|-------------|
| contains | Workflow → Task/Trace | Workflow includes this item |
| precedes | Task → Task | Sequential task order |
| uses | Task → Tool | Task utilizes this tool |
| processes | Task → Document | Task reads/analyzes document |
| produces | Task → Document/Checklist/Finding | Task creates artifact |
| leads_to | Task/Finding → Outcome/Risk | Contributes to result |
| mitigates | Control → Risk | Control addresses risk |
| supports | Evidence → Risk/Finding | Evidence substantiates |
| references | Any → Any | General reference link |

---

## Observation Guidelines

### Required on Every Entity

1. **Timestamp** — `"Created at 2026-02-05 10:30"`
2. **Source** — `"Source: local_markitdown.py"`
3. **Status** — `"Status: Complete"` / `"Status: In Progress"`

### Format

```
"{Type}: {Value} | {Context}"
```

Examples:
- `"Procedures: 85 | All with response types assigned"`
- `"Chunks: 3 | Chunked at group boundaries"`

### When to Update

| Event | Action |
|-------|--------|
| Workflow start | Create workflow entity with goal and scope |
| Major step complete | Create task entity with actions, decisions, results |
| Tool usage | Create tool entity, relate to task |
| Document processed | Create document entity, relate to task |
| Decision point | Add observation explaining rationale |
| Workflow end | Create outcome entity with summary |

---

## Trace Entity Schema

Naming: `{AgentCode}_Trace_{Step}_{Server}_{Tool}_{Timestamp}`

### Required Observations

| Observation | Format | Example |
|-------------|--------|---------|
| Start | `Start: {ISO 8601}` | `Start: 2026-01-16T10:30:15.000Z` |
| End | `End: {ISO 8601}` | `End: 2026-01-16T10:30:16.247Z` |
| Duration | `Duration: {ms}ms` | `Duration: 1247ms` |
| Status | `Status: {success/error/timeout}` | `Status: success` |
| Server | `Server: {name}` | `Server: caseware_cloud_current` |
| Tool | `Tool: {name}` | `Tool: trial-balance-get` |
| Request | `Request: {json}` | `Request: {"fiscalYear":"2025"}` |
| Response | `Response: {json}` | `Response: {"accounts":[...]}` |
| Items | `Items: {count} {type}` | `Items: 245 accounts` |
| Error | `Error: {message}` | `Error: Connection timeout after 30s` |

### Trace Relations

- Task → contains → Trace
- Workflow → contains → Trace

---

## CLI Usage

```bash
# Script location
python3 authoring-agent/scripts/local_knowledge_graph.py

# Create entities
python3 local_knowledge_graph.py create-entities '[{"name": "AA_W_20260205", "type": "workflow"}]'

# Create relations
python3 local_knowledge_graph.py create-relations '[["AA_W_20260205", "contains", "AA_T_Convert"]]'

# Add observations
python3 local_knowledge_graph.py add-observations "AA_W_20260205" '["Started: 2026-02-05"]'

# Query entities
python3 local_knowledge_graph.py query --pattern "AA_T_*"

# Full-text search
python3 local_knowledge_graph.py search "revenue"

# Export Mermaid diagram
python3 local_knowledge_graph.py export-mermaid "AA_W_20260205"

# Prepare visualization with stats
python3 local_knowledge_graph.py visualize "AA_W_20260205" --depth 3
```

---

## Visualization

Export diagrams via CLI, then generate with Figma MCP:
- Use LR (left-to-right) direction for sequential workflows
- Differentiate entity types with shapes/colors (tasks vs tools vs documents)
- For tool nodes, include the tool type in brackets on a new line
- After generating, instruct user to open the Figma link and click "Save to Figma"
- Figma diagrams are **ephemeral** — they must be manually saved by the user

---

## Query Patterns

| Goal | Approach |
|------|----------|
| Tasks in a workflow | Search relations from `AA_W_{id}` with type `contains` |
| Documents processed | Search relations with type `processes` |
| Task execution order | Search relations with type `precedes` |
| Tool usage | Search relations with type `uses` |
