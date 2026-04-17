# Caseware Cloud MCP Server - Complete Technical Reference

## Overview

This document provides comprehensive technical specifications for the Caseware Cloud Model Context Protocol (MCP) server implementation. The server provides tools and resources for interacting with a specific Caseware Cloud engagement.

### Server Context
- **Engagement Name**: CaseWare USA Inc.
- **Year**: 2025
- **Product**: Caseware Core

### ID Format
All entity IDs use the JSON schema format `uuid-base64url` - a URL-safe base-64 encoding of a UUID, always 22 characters long.

### Tool Naming Convention
All MCP tools use the prefix `mcp_caseware_clou_` followed by the tool name. For example:
- Short name: `document-manager`
- Full MCP tool name: `mcp_caseware_clou_document-manager`

When making MCP tool calls, use the **full MCP tool name**. This document shows both formats for clarity.

---

## Activation Tools

> **Claude Code**: All MCP tools are available immediately after the server is connected. The activation tools below are part of the MCP server architecture but do not need to be called when using Claude Code.

The MCP server uses an **activation-based architecture**. Core tools (document-manager, engagement-properties) are always available. Specialized tools require calling an activation tool first to enable access.

### Activation Tool Reference

| Activation Tool | Full MCP Name | Enables |
|-----------------|---------------|--------|
| `activate_checklist_and_document_management_tools` | `activate_checklist_and_document_management_tools` | checklist-get, checklist-save, query-get, query-save, statement-get, statement-save |
| `activate_engagement_control_and_risk_management_tools` | `activate_engagement_control_and_risk_management_tools` | controls-get, risks-get |
| `activate_control_and_risk_update_tools` | `activate_control_and_risk_update_tools` | risks-save, controls-save |
| `activate_financial_data_retrieval_tools` | `activate_financial_data_retrieval_tools` | trial-balance-get, materiality-get, accounts-assign |

### Activation Workflow

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│  Connect MCP    │ ──► │  Activate Category   │ ──► │   Use Tools     │
│     Server      │     │  (call activation    │     │  (tools now     │
│                 │     │   tool)              │     │   available)    │
└─────────────────┘     └──────────────────────┘     └─────────────────┘
```

**Best Practice:** Activate all required tool categories at the start of your workflow before making any tool calls.

### Activation Error Handling

If you call a tool without first activating its category, you will receive an error indicating the tool is not available.

| Error Pattern | Cause | Resolution |
|---------------|-------|------------|
| "Tool not available" | Tool category not activated | Call the appropriate activation tool first |
| "Unknown tool" | Tool does not exist or typo | Verify tool name and MCP prefix |
| Tool returns empty/null | May need activation | Ensure activation tool was called successfully |

**Recovery Steps:**
1. Identify which category the tool belongs to (see table above)
2. Call the appropriate activation tool
3. Retry the original tool call

---

## Multi-Year Server Configuration

For comparative analysis workflows (e.g., ratio trending, year-over-year analysis), multiple MCP server instances can be connected simultaneously, each pointing to a different fiscal year's engagement.

### Server Configuration

| Server Name | Fiscal Year | Engagement Period | Use Case |
|-------------|-------------|-------------------|----------|
| `caseware_cloud_priorprior` | FY2023 | Prior Prior Year | Historical baseline |
| `caseware_cloud_prior` | FY2024 | Prior Year | Comparative period |
| `caseware_cloud_current` | FY2025 | Current Year | Active engagement |

### Multi-Year Tool Calls

When multiple servers are connected, prefix tool calls with the server name:

```
# Current year trial balance
mcp_caseware_clou_trial-balance-get (on caseware_cloud_current)

# Prior year trial balance  
mcp_caseware_clou_trial-balance-get (on caseware_cloud_prior)

# Prior prior year trial balance
mcp_caseware_clou_trial-balance-get (on caseware_cloud_priorprior)
```

### Example: Three-Year Ratio Analysis

1. Connect all three MCP servers
2. Activate `financial_data_retrieval_tools` on each server
3. Call `trial-balance-get` on each server to retrieve account balances
4. Calculate ratios (current ratio, quick ratio, etc.) for each year
5. Analyze trends and identify significant changes

---

## Tool Categories

The MCP server organizes tools into functional groups:

| Category | Activation Tool | Purpose |
|----------|-----------------|---------|
| Document Management | `activate_checklist_and_document_management_tools` | Manage checklists, queries, and statements |
| Control & Risk Retrieval | `activate_engagement_control_and_risk_management_tools` | Retrieve controls and risks |
| Control & Risk Updates | `activate_control_and_risk_update_tools` | Create/update controls and risks |
| Financial Data | `activate_financial_data_retrieval_tools` | Retrieve materiality and trial balance data |

---

## Core Tools

### 1. Document Manager

**Short Name**: `document-manager`  
**Full MCP Tool Name**: `mcp_caseware_clou_document-manager`

**Description**: Lists the available documents in the engagement's document manager, grouped by engagement preparation phases and folders within each phase. Returns an ordered list of line items with depth information indicating hierarchy.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `includeHidden` | boolean | No | Whether to include hidden documents (default: false) |

**Request Schema**:
```json
{
  "type": "object",
  "properties": {
    "includeHidden": {
      "type": "boolean",
      "description": "Whether to include hidden documents. Hidden documents may include deleted or archived items that are not normally visible."
    }
  },
  "required": []
}
```

**Response Structure**:
Returns documents organized by:
- Phases (top-level groupings)
- Folders (within phases)
- Documents (within folders)

Each item includes:
- `id` (uuid-base64url): Unique document identifier
- `name`: Document name
- `number`: Document reference number
- `documentType`: Type of document (e.g., "checklist", "query", "statement", "letter")
- `depth`: Hierarchy level indicator
- `hidden`: Whether document is hidden

**Use Cases**:
- Discover existing documents before creating new ones
- Find document IDs for subsequent tool calls
- Understand engagement folder structure
- Identify available document numbers to avoid conflicts

---

### 2. Engagement Properties

**Short Name**: `engagement-properties`  
**Full MCP Tool Name**: `mcp_caseware_clou_engagement-properties`

**Description**: Retrieves the properties of the engagement "CaseWare USA Inc. 2025".

**Parameters**: None required

**Request Schema**:
```json
{
  "type": "object",
  "properties": {},
  "required": []
}
```

**Response Structure**:
Returns engagement metadata including:
- Entity name
- Year end date
- Reporting period
- Engagement type
- Client information
- Firm information

---

### 3. Checklist Get

**Short Name**: `checklist-get`  
**Full MCP Tool Name**: `mcp_caseware_clou_checklist-get`

**Requires Activation**: `activate_checklist_and_document_management_tools`

**Description**: Retrieves the procedures in a given checklist document. Procedures are returned in order with hierarchical depth information. Procedures can include answer rows and columns defining potential answers and chosen responses.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | uuid-base64url | Yes | The checklist document ID (from document-manager) |
| `includeHidden` | boolean | No | Whether to include hidden items (default: false) |

**Request Schema**:
```json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid-base64url",
      "description": "The id of the checklist document to retrieve - this should be provided by the document-manager tool"
    },
    "includeHidden": {
      "type": "boolean",
      "description": "Whether to include hidden items in the checklist. Hidden items are typically those that are not visible to the user in the UI based on other checklist answers."
    }
  },
  "required": []
}
```

**Response Structure**:
Returns array of procedure objects containing:
- `id`: Procedure identifier
- `type`: Procedure type (group, heading, procedure, conclusion)
- `depth`: Hierarchy level (0 = top level)
- `title`: Procedure title
- `text`: Detailed procedure text (HTML)
- `summary`: Procedure summary
- `hidden`: Visibility status
- `hideCondition`: Conditional visibility rule
- `guidance`: Help text for completing the procedure
- `note`: Associated notes
- `notePlaceholder`: Placeholder text for notes
- `includeNote`: Whether notes are enabled
- `includeSignOffs`: Whether sign-offs are enabled
- `signOff`: Sign-off information
- `rows`: Answer rows with columns containing choices
- `authoritativeReferences`: Standards references
- `traceId`: Trace identifier for reasoning

---

### 4. Checklist Save

**Short Name**: `checklist-save`  
**Full MCP Tool Name**: `mcp_caseware_clou_checklist-save`

**Requires Activation**: `activate_checklist_and_document_management_tools`

**Description**: Generates suggested changes for a checklist document - either creating a new one or updating an existing one. Supports creating complete checklists with groups, headings, procedures, and conclusions.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | uuid-base64url | No | Existing checklist ID (null for new) |
| `documentInfo` | object | Conditional | Required when creating new checklist |
| `procedures` | array | No | Procedures to save/update |
| `guidance` | string | No | Preparer guidance |
| `includeConclusion` | boolean | No | Include conclusion section |
| `conclusionTitle` | string | No | Title for conclusion section |
| `includeSignoffs` | boolean | No | Include sign-offs on procedures |
| `purpose` | string | No | Description of why changes are being made |
| `purposeSummary` | string | No | Short title for suggestion set |

**Full Request Schema**:
```json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid-base64url",
      "description": "The id of the checklist document to save - this should be provided by the document-manager tool, or null if creating a new checklist. If creating a new checklist, the 'documentInfo' member must be populated"
    },
    "documentInfo": {
      "type": "object",
      "description": "The document info for the new checklist, if creating a new checklist. If not creating a new checklist, this should be null",
      "properties": {
        "folder": {
          "type": "string",
          "format": "uuid-base64url",
          "description": "The folder id to save the document in - as found in the document-manager tool. Either phase or folder should be provided, but not both."
        },
        "phase": {
          "type": "string",
          "format": "uuid-base64url",
          "description": "The phase id of the engagement to save the document in - as found in the document-manager tool. Either phase or folder should be provided, but not both."
        },
        "name": {
          "type": "string",
          "description": "The name of the new document"
        },
        "number": {
          "type": "string",
          "description": "The number of the new document - note that to avoid conflicts, be sure to check for hidden documents in the document manager"
        }
      }
    },
    "guidance": {
      "type": "string",
      "description": "The guidance for the preparer"
    },
    "includeConclusion": {
      "type": "boolean",
      "description": "Whether the checklist should include a conclusion section"
    },
    "conclusionTitle": {
      "type": "string",
      "description": "The title for the conclusion section, if any"
    },
    "includeSignoffs": {
      "type": "boolean",
      "description": "Whether the checklist includes signoff on each procedure"
    },
    "purpose": {
      "type": "string",
      "description": "The declared purpose (or description) for the suggestion set - if creating a new suggestion set, this should be provided. The purpose will be displayed to the user when they are accepting the changes. The purpose should explain the reason why the changes are being made, which might include the prompt or the agent workflow step."
    },
    "purposeSummary": {
      "type": "string",
      "description": "The purpose summary (or title) for the suggestion set - if creating a new suggestion set, this should be provided. The purpose summary will be displayed to the user when they are accepting the changes. The purpose should explain the reason why the changes are being made, which might include the prompt or the agent workflow step."
    },
    "procedures": {
      "type": "array",
      "description": "The procedures to save in the checklist. If creating a new checklist, this should contain the procedures to be saved in the new checklist, including at least one question set at the root of the hierarchy. New procedures should include at least one row and one column specifying what type of answer is expected. If updating an existing checklist, this should contain the procedures to be updated. The procedures to update can be sparsely populated with only the changes required and the ids",
      "items": {
        "$ref": "#/$defs/Procedure"
      }
    }
  },
  "required": []
}
```

**Procedure Object Schema**:
```json
{
  "$defs": {
    "Procedure": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "format": "uuid-base64url",
          "description": "The id of the procedure"
        },
        "depth": {
          "type": "integer",
          "format": "int32",
          "description": "The depth of the procedure in the hierarchy, where 0 is the top level"
        },
        "type": {
          "$ref": "#/$defs/Type",
          "description": "The type of the procedure. The group type shows up in the document navigation panel and should be used as the parent for a related set of headings and procedures"
        },
        "title": {
          "type": "string",
          "description": "The title of the procedure"
        },
        "text": {
          "type": "string",
          "description": "The text of the procedure - this can be an HTML fragment"
        },
        "summary": {
          "type": "string",
          "description": "The summary of the procedure"
        },
        "hidden": {
          "type": "boolean",
          "description": "Whether the item is hidden. Hidden items are typically those that are not visible to the user in the UI based on checklist answers or other conditions."
        },
        "hideCondition": {
          "type": "string",
          "description": "The condition used to determine if this procedure should be hidden."
        },
        "guidance": {
          "type": "string",
          "description": "The specific guidance for the procedure - this should contain help for the user on how to complete the procedure"
        },
        "note": {
          "type": "string",
          "description": "The note associated with the procedure if any - Conclusion procedures use notes for the conclusion text"
        },
        "notePlaceholder": {
          "type": "string",
          "description": "The placeholder text for the note input, if any"
        },
        "includeNote": {
          "type": "boolean",
          "description": "Whether to include a note input for the procedure"
        },
        "includeSignOffs": {
          "type": "boolean",
          "description": "Whether to include sign-off controls for the procedure"
        },
        "signOff": {
          "$ref": "#/$defs/SignOff",
          "description": "The sign-off information for the procedure, if any"
        },
        "rows": {
          "type": "array",
          "description": "The answer rows for the procedure, which have answer columns which contain choices and may contain a chosen item id and 'other' text - most procedures have one row and column with a single choice set",
          "items": {
            "$ref": "#/$defs/Row"
          }
        },
        "authoritativeReferences": {
          "type": "array",
          "description": "Authoritative reference objects for the procedure - these are typically references to section numbers in a standards document and may or may not have associated URLs that point to detailed documentation",
          "items": {
            "$ref": "#/$defs/AuthoritativeReference"
          }
        },
        "traceId": {
          "type": "string",
          "description": "The trace identifier for this procedure - this is used for providing reasoning traces to explain why changes were suggested"
        },
        "reasoning": {
          "$ref": "#/$defs/Reasoning",
          "description": "The reasoning for the specific change - The reasoning will be displayed to the user when they are accepting the change."
        }
      }
    },
    "Type": {
      "type": "string",
      "enum": ["group", "heading", "procedure", "conclusion"],
      "description": "The type of the procedure"
    },
    "Row": {
      "type": "object",
      "properties": {
        "columns": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/Column"
          }
        }
      }
    },
    "Column": {
      "type": "object",
      "properties": {
        "type": {
          "type": "string",
          "enum": ["choice", "text", "number", "date", "files", "manual"],
          "description": "The type of answer expected"
        },
        "choices": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/Choice"
          }
        },
        "chosenId": {
          "type": "string",
          "format": "uuid-base64url",
          "description": "The ID of the chosen answer"
        },
        "otherText": {
          "type": "string",
          "description": "Additional text for 'other' responses"
        },
        "placeholder": {
          "type": "string",
          "description": "Placeholder text for input fields"
        },
        "fileDestination": {
          "type": "object",
          "description": "File destination information for file uploads"
        }
      }
    },
    "Choice": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "format": "uuid-base64url",
          "description": "The choice identifier"
        },
        "text": {
          "type": "string",
          "description": "The display text for the choice"
        }
      }
    },
    "AuthoritativeReference": {
      "type": "object",
      "properties": {
        "reference": {
          "type": "string",
          "description": "The reference text (e.g., section number)"
        },
        "url": {
          "type": "string",
          "description": "Optional URL to detailed documentation"
        }
      }
    },
    "SignOff": {
      "type": "object",
      "properties": {
        "preparer": {
          "type": "object",
          "description": "Preparer sign-off information"
        },
        "reviewer": {
          "type": "object",
          "description": "Reviewer sign-off information"
        }
      }
    },
    "Reasoning": {
      "type": "object",
      "properties": {
        "description": {
          "type": "string",
          "description": "The detailed description of the reasoning, which should explain the reason why a change is being made, which might include the prompt, the agent workflow step or the specific evaluation that led to the suggestion. This is human readable, so don't include trace or url information here. Include them in the traces and urls fields."
        },
        "confidence": {
          "type": "number",
          "format": "double",
          "description": "The confidence level of the reasoning, from 0.0 (no confidence) to 1.0 (high confidence). This indicates how certain the system is about the reasoning provided."
        },
        "traces": {
          "type": "array",
          "description": "The traces for sources of the reasoning which include the object trace id and field that were used as a source for the reasoning. Populate this instead of including trace information in the description.",
          "items": {
            "type": "object",
            "properties": {
              "traceId": {
                "type": "string",
                "description": "The trace identifier of the object that was used to generate the reason the suggestion was made"
              },
              "field": {
                "type": "string",
                "description": "The field within the object where the source of the reasoning originated"
              },
              "position": {
                "$ref": "#/$defs/ReasoningPosition",
                "description": "The position within the content that supports the reasoning"
              }
            }
          }
        },
        "urls": {
          "type": "array",
          "description": "The URLs for sources of the reasoning, such as documentation or web pages that support the reasoning. These should be relevant to understanding why the suggestion was made. Populate this instead of including URL information in the description.",
          "items": {
            "type": "object",
            "properties": {
              "url": {
                "type": "string",
                "description": "The URL pointing to a source for the reasoning"
              },
              "label": {
                "type": "string",
                "description": "The optional label for the URL"
              },
              "position": {
                "$ref": "#/$defs/ReasoningPosition",
                "description": "The position within the URL content that supports the reasoning"
              }
            }
          }
        }
      }
    },
    "ReasoningPosition": {
      "type": "object",
      "description": "Position information within content"
    }
  }
}
```

> **Do NOT copy these examples to construct payloads manually.** Use `build_payload(outline)` which generates correct payloads and handles conclusion items, chunking, and ID management automatically.

**Example - Create New Checklist**:
```json
{
  "id": null,
  "documentInfo": {
    "folder": "abc123def456ghi789jk",
    "name": "Revenue Testing Checklist",
    "number": "B-100"
  },
  "guidance": "Complete this checklist to document revenue testing procedures.",
  "includeConclusion": true,
  "conclusionTitle": "Conclusion",
  "includeSignoffs": true,
  "purpose": "Create revenue testing checklist for audit procedures",
  "purposeSummary": "Revenue Testing Checklist",
  "procedures": [
    {
      "id": null,
      "depth": 0,
      "type": "group",
      "title": "Revenue Recognition",
      "hidden": false
    },
    {
      "id": null,
      "depth": 1,
      "type": "heading",
      "title": "Verify revenue recognition policies",
      "hidden": false
    },
    {
      "id": null,
      "depth": 2,
      "type": "procedure",
      "title": "Review revenue recognition policy",
      "text": "<p>Has the entity's revenue recognition policy been reviewed for compliance with applicable standards?</p>",
      "includeNote": true,
      "notePlaceholder": "Response and comments",
      "includeSignOffs": true,
      "rows": [
        {
          "columns": [
            {
              "type": "choice",
              "placeholder": "",
              "includeOtherChoice": false,
              "inlineChoices": true,
              "choices": [
                { "text": "Yes" },
                { "text": "No" },
                { "text": "N/A" }
              ]
            }
          ]
        }
      ]
    },
    {
      "id": null,
      "depth": 0,
      "type": "conclusion",
      "title": "Conclusion",
      "text": "<p>Based on the procedures performed above, document your conclusion.</p>",
      "includeNote": true,
      "notePlaceholder": "Enter conclusion here",
      "includeSignOffs": true,
      "rows": [
        {
          "columns": [
            {
              "type": "text",
              "placeholder": "Enter conclusion"
            }
          ]
        }
      ]
    }
  ]
}
```

---

### 5. Query Get

**Short Name**: `query-get`  
**Full MCP Tool Name**: `mcp_caseware_clou_query-get`

**Requires Activation**: `activate_checklist_and_document_management_tools`

**Description**: Retrieves the questions in a given query document. Questions are returned in order with hierarchical depth information. Questions can include answer rows and columns defining potential answers. Queries are used to gather information from clients in a structured way, most often used to request file uploads.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | uuid-base64url | Yes | The query document ID (from document-manager) |
| `includeHidden` | boolean | No | Whether to include hidden items (default: false) |

**Request Schema**:
```json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid-base64url",
      "description": "The id of the query document to retrieve - this should be provided by the document-manager tool."
    },
    "includeHidden": {
      "type": "boolean",
      "description": "Whether to include hidden items in the query. Hidden items are typically those that are not visible to the user in the UI based on other query answers."
    }
  },
  "required": []
}
```

**Response Structure**:
Returns array of question objects containing:
- `id`: Question identifier
- `type`: Question type (questionSet, question)
- `depth`: Hierarchy level
- `title`: Question title
- `text`: Detailed question text (HTML)
- `hidden`: Visibility status
- `hideCondition`: Conditional visibility rule
- `note`: Associated notes
- `rows`: Answer rows with columns
- `traceId`: Trace identifier

---

### 6. Query Save

**Short Name**: `query-save`  
**Full MCP Tool Name**: `mcp_caseware_clou_query-save`

**Requires Activation**: `activate_checklist_and_document_management_tools`

**Description**: Generates suggested changes for a query document - either creating a new one or updating an existing one. Creates client-facing information requests with structured question sets.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | uuid-base64url | No | Existing query ID (null for new) |
| `documentInfo` | object | Conditional | Required when creating new query |
| `questions` | array | No | Questions to save/update |
| `instructions` | string | No | Instructions for the contact |
| `purpose` | string | No | Description of why changes are being made |
| `purposeSummary` | string | No | Short title for suggestion set |

**Full Request Schema**:
```json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid-base64url",
      "description": "The id of the query document to save - this should be provided by the document-manager tool, or null if creating a new query. If creating a new query, the 'documentInfo' member must be populated"
    },
    "documentInfo": {
      "type": "object",
      "description": "The document info for the new query, if creating a new query. If not creating a new query, this should be null",
      "properties": {
        "folder": {
          "type": "string",
          "format": "uuid-base64url",
          "description": "The folder id to save the document in - as found in the document-manager tool. Either phase or folder should be provided, but not both."
        },
        "phase": {
          "type": "string",
          "format": "uuid-base64url",
          "description": "The phase id of the engagement to save the document in - as found in the document-manager tool. Either phase or folder should be provided, but not both."
        },
        "name": {
          "type": "string",
          "description": "The name of the new document"
        },
        "number": {
          "type": "string",
          "description": "The number of the new document - note that to avoid conflicts, be sure to check for hidden documents in the document manager"
        }
      }
    },
    "instructions": {
      "type": "string",
      "description": "The instructions for the contact"
    },
    "purpose": {
      "type": "string",
      "description": "The declared purpose (or description) for the suggestion set - if creating a new suggestion set, this should be provided. The purpose will be displayed to the user when they are accepting the changes. The purpose should explain the reason why the changes are being made, which might include the prompt or the agent workflow step."
    },
    "purposeSummary": {
      "type": "string",
      "description": "The purpose summary (or title) for the suggestion set - if creating a new suggestion set, this should be provided. The purpose summary will be displayed to the user when they are accepting the changes. The purpose should explain the reason why the changes are being made, which might include the prompt or the agent workflow step."
    },
    "questions": {
      "type": "array",
      "description": "The questions to save in the query. If creating a new query, this should contain the questions to be saved in the new query, including at least one question set at the root of the hierarchy. New questions should include at least one row and one column specifying what type of answer is expected. If updating an existing query, this should contain the questions to be updated. The questions to update can be sparsely populated with only the changes required and the ids",
      "items": {
        "$ref": "#/$defs/Question"
      }
    }
  },
  "required": []
}
```

**Question Object Schema**:
```json
{
  "$defs": {
    "Question": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "format": "uuid-base64url",
          "description": "The id of the question"
        },
        "depth": {
          "type": "integer",
          "format": "int32",
          "description": "The depth of the line item in the hierarchy, where 0 is the top level"
        },
        "type": {
          "$ref": "#/$defs/Type",
          "description": "The type of the question"
        },
        "title": {
          "type": "string",
          "description": "The title of the question"
        },
        "text": {
          "type": "string",
          "description": "The detailed text of the question - this can be an HTML fragment"
        },
        "hidden": {
          "type": "boolean",
          "description": "Whether the item is hidden. Hidden items are typically those that are not visible to the user in the UI based on checklist answers or other conditions."
        },
        "hideCondition": {
          "type": "string",
          "description": "The condition used to determine if this question should be hidden."
        },
        "note": {
          "type": "string",
          "description": "The note associated with the question if any - Conclusion questions use notes for the conclusion text"
        },
        "rows": {
          "type": "array",
          "description": "The answer rows for the question, which have answer columns which contain choices and may contain a chosen item id and 'other' text - most questions have one row and column with a single choice set",
          "items": {
            "$ref": "#/$defs/Row"
          }
        },
        "traceId": {
          "type": "string",
          "description": "The trace identifier for this question - this is used for providing reasoning traces to explain why changes were suggested"
        },
        "reasoning": {
          "$ref": "#/$defs/Reasoning",
          "description": "The reasoning for the specific change"
        }
      }
    },
    "Type": {
      "type": "string",
      "enum": ["questionSet", "question"],
      "description": "The type of the question"
    },
    "Row": {
      "type": "object",
      "properties": {
        "columns": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/Column"
          }
        }
      }
    },
    "Column": {
      "type": "object",
      "properties": {
        "type": {
          "type": "string",
          "enum": ["choice", "text", "number", "date", "files"],
          "description": "The type of answer expected"
        },
        "choices": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/Choice"
          }
        },
        "chosenId": {
          "type": "string",
          "format": "uuid-base64url",
          "description": "The ID of the chosen answer"
        },
        "placeholder": {
          "type": "string",
          "description": "Placeholder text for input fields"
        },
        "fileDestination": {
          "type": "object",
          "description": "File destination information for file uploads"
        }
      }
    },
    "Choice": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "format": "uuid-base64url"
        },
        "text": {
          "type": "string"
        }
      }
    }
  }
}
```

**Example - Create New Query**:
```json
{
  "id": null,
  "documentInfo": {
    "folder": "abc123def456ghi789jk",
    "name": "Revenue Process Information Request",
    "number": "B-100Q"
  },
  "instructions": "Please provide the following information to assist with our audit procedures. For each item, enter your response in the text field and upload any supporting documents.",
  "purpose": "Gather client information for revenue cycle audit procedures",
  "purposeSummary": "Revenue Process Query",
  "questions": [
    {
      "id": null,
      "depth": 0,
      "type": "questionSet",
      "title": "Process Overview",
      "hidden": false,
      "hideCondition": null
    },
    {
      "id": null,
      "depth": 1,
      "type": "question",
      "title": "Revenue Recognition Policy",
      "text": "<p>Please describe your revenue recognition policy and provide supporting documentation.</p>",
      "rows": [
        {
          "columns": [
            { "type": "text", "placeholder": "Describe revenue recognition policy" },
            { "type": "files", "placeholder": "", "fileDestination": {} }
          ]
        }
      ],
      "hidden": false,
      "hideCondition": null
    }
  ]
}
```

---

### 7. Statement Get

**Short Name**: `statement-get`  
**Full MCP Tool Name**: `mcp_caseware_clou_statement-get`

**Requires Activation**: `activate_checklist_and_document_management_tools`

**Description**: Retrieves the sections in a given statement document. Sections are returned in order with hierarchical depth information.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | uuid-base64url | Yes | The statement document ID (from document-manager) |
| `includeHidden` | boolean | No | Whether to include hidden items (default: false) |

**Request Schema**:
```json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid-base64url",
      "description": "The id of the statement document to retrieve - this should be provided by the document-manager tool."
    },
    "includeHidden": {
      "type": "boolean",
      "description": "Whether to include hidden items in the statement. Hidden items are typically those that are not visible to the user in the UI based on other statement answers."
    }
  },
  "required": []
}
```

**Response Structure**:
Returns statement sections with:
- `id`: Section identifier
- `type`: Section type (area, content)
- `title`: Section title
- `content`: HTML content
- `depth`: Hierarchy level
- `hidden`: Visibility status
- `hideCondition`: Conditional visibility rule
- `excludeFromTableOfContents`: TOC exclusion flag
- `dontNumberInTableOfContents`: TOC numbering flag

---

### 8. Controls Get

**Short Name**: `controls-get`  
**Full MCP Tool Name**: `mcp_caseware_clou_controls-get`

**Requires Activation**: `activate_engagement_control_and_risk_management_tools`

**Description**: Retrieves all controls for the engagement. Each control includes its properties and references.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `includeHidden` | boolean | No | Whether to include hidden controls (default: false) |

**Request Schema**:
```json
{
  "type": "object",
  "properties": {
    "includeHidden": {
      "type": "boolean",
      "description": "Whether to include hidden controls. Hidden controls are typically those that are not visible to the user in the UI based on other conditions."
    }
  },
  "required": []
}
```

**Response Structure**:
Returns array of control objects containing:
- `id`: Control identifier
- `name`: Control name
- `description`: Control description
- `type`: Control type
- `frequency`: How often control operates
- `nature`: Manual/Automated
- `assertions`: Related assertions
- `risks`: Associated risks
- `references`: Document references
- `hidden`: Visibility status

---

### 9. Risks Get

**Short Name**: `risks-get`  
**Full MCP Tool Name**: `mcp_caseware_clou_risks-get`

**Requires Activation**: `activate_engagement_control_and_risk_management_tools`

**Description**: Retrieves all risks for the engagement. Each risk includes its properties and references.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `includeHidden` | boolean | No | Whether to include hidden risks (default: false) |

**Request Schema**:
```json
{
  "type": "object",
  "properties": {
    "includeHidden": {
      "type": "boolean",
      "description": "Whether to include hidden risks. Hidden risks are typically those that are not visible to the user in the UI based on other conditions."
    }
  },
  "required": []
}
```

**Response Structure**:
Returns array of risk objects containing:
- `id`: Risk identifier
- `name`: Risk name
- `description`: Risk description
- `level`: Risk level (inherent, residual)
- `likelihood`: Probability assessment
- `impact`: Impact assessment
- `assertions`: Related assertions
- `accountGroups`: Associated account groups
- `controls`: Mitigating controls
- `references`: Document references
- `hidden`: Visibility status

---

## Additional Tools (Activation Required)

### 10. Statement Save ✅

**Short Name**: `statement-save`  
**Full MCP Tool Name**: `mcp_caseware_clou_statement-save`

**Requires Activation**: `activate_checklist_and_document_management_tools`

**Validation Status**: Letter authoring validated 2026-01-29 with dynamic element detection (formulas, date/input placeholders, staff selectors) and two-step creation process.

**Description**: Generates suggested changes for a statement document (including letters, worksheets, and memos) - either creating a new one or updating an existing one. Supports creating complete documents with areas, sections, and dynamic content.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | uuid-base64url | No | Existing document ID (null for new) |
| `type` | string | Conditional | Document type: "statement", "worksheet", "memo", "letter" (required for new) |
| `documentInfo` | object | Conditional | Required when creating new document |
| `documentMap` | array | No | Areas and sections to save/update |
| `settings` | object | No | Document settings |
| `purpose` | string | No | Description of why changes are being made |
| `purposeSummary` | string | No | Short title for suggestion set |

**Document Map Structure**:
```json
{
  "documentMap": [
    {
      "type": "area",
      "title": "<p>Area Title</p>",
      "excludeFromTableOfContents": false,
      "dontNumberInTableOfContents": false,
      "hidden": false,
      "sections": [
        {
          "type": "content",
          "title": "Section Name",
          "content": "<p>HTML content here</p>",
          "depth": 0,
          "hidden": false
        }
      ]
    }
  ]
}
```

**Dynamic Content - Formulas**:

Use formulas to pull engagement data dynamically:

| Formula | Purpose | Example |
|---------|---------|--------|
| `engprop("name")` | Entity name | `<span formula="engprop(&quot;name&quot;)" class="formula">Entity Name</span>` |
| `engprop("yearend", 0, "longDate")` | Year end date | Formatted date |
| `collaborate("legalName")` | Legal name from collaborate | Client legal name |
| `collaborate("clientAddressId", "address1")` | Client address | Address line 1 |
| `wording("@glossaryId")` | Glossary/wording reference | Dynamic terminology |
| `procedureAnswer(checklistId.procedureId)` | Checklist answer reference | Conditional text |

**Dynamic Content - Placeholders**:

```html
<!-- Text input placeholder -->
<span placeholder="uniqueId" contenteditable="false" type="input-area" 
      title="[Placeholder Text]" custom-label="[Placeholder Text]" 
      class="placeholder unselected">[Placeholder Text]</span>

<!-- Date picker placeholder -->
<span placeholder="uniqueId" type="date" user="null" contenteditable="false" 
      custom-label="Select Date" class="placeholder unselected">
  <span>Select Date</span><span class="caret hidden-print">&nbsp;</span>
</span>
```

**Example - Create New Letter (TWO-STEP PROCESS)**:

⚠️ **CRITICAL:** Letter creation requires TWO calls. The API ignores sections on initial creation.

**Step 1 - Create Letter (sections ignored):**
```json
{
  "id": null,
  "type": "letter",
  "documentInfo": {
    "folder": "abc123def456ghi789jk",
    "name": "Management Representation Letter - Draft",
    "number": "E-600"
  },
  "purpose": "Create management representation letter for year-end audit",
  "purposeSummary": "Management Rep Letter",
  "documentMap": [
    {
      "type": "area",
      "title": "<p>Management Representation Letter</p>",
      "sections": []
    }
  ]
}
```

**Capture from Step 1 response:**
- `response.id` → document ID (e.g., `"q3tR5SlkTK2je4FUoC5Qlg"`)
- `response.documentMap[0].id` → area ID (e.g., `"WQdUxxYYQPazNUK-2PCiIw"`)

**Step 2 - Add Sections (REQUIRED):**
```json
{
  "id": "q3tR5SlkTK2je4FUoC5Qlg",
  "type": "letter",
  "documentMap": [
    {
      "id": "WQdUxxYYQPazNUK-2PCiIw",
      "type": "area",
      "title": "<p>Management Representation Letter</p>",
      "sections": [
        {
          "type": "content",
          "title": "Header",
          "content": "<p>&nbsp;</p>",
          "depth": 0
        },
        {
          "type": "content",
          "title": "Addressee",
          "content": "<p>To <span placeholder='auditorName' type='input-area' class='placeholder'>[Auditor Name]</span></p>",
          "depth": 0
        },
        {
          "type": "content",
          "title": "Introduction",
          "content": "<p>This representation letter is provided in connection with your audit of the financial statements of <span formula='engprop(&quot;name&quot;)' class='formula'>Entity Name</span>...</p>",
          "depth": 0
        }
      ]
    }
  ]
}
```

**Note:** For EXISTING letters (updates), include the area ID and sections will save in one call.

---

### 11. Trial Balance Get

**Short Name**: `trial-balance-get`  
**Full MCP Tool Name**: `mcp_caseware_clou_trial-balance-get`

**Requires Activation**: `activate_financial_data_retrieval_tools`

**Description**: Retrieves the trial balance data for the engagement, including accounts, balances, financial groups, and consolidation structure.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `fiscalYear` | string | No | The fiscal year to retrieve (defaults to current engagement year) |

**Request Schema**:
```json
{
  "type": "object",
  "properties": {
    "fiscalYear": {
      "type": "string",
      "description": "The fiscal year to retrieve trial balance data for"
    }
  },
  "required": []
}
```

**Response Structure**:
Returns trial balance data containing:
- `accounts`: Array of account objects with:
  - `id`: Account identifier
  - `accountNumber`: Account code/number
  - `accountName`: Account description
  - `financialGroupId`: Associated financial group
  - `depth`: Hierarchy level (0 = unassigned)
  - `balances`: Period balances (current, prior)
- `financialGroups`: Array of financial group definitions
- `periodEnd`: Period end date
- `consolidation`: Consolidation structure (if applicable)

**Use Cases**:
- Calculate financial ratios
- Perform year-over-year analysis
- Identify unassigned accounts (depth 0)
- Support risk assessment with quantitative data

---

### 12. Materiality Get

**Short Name**: `materiality-get`  
**Full MCP Tool Name**: `mcp_caseware_clou_materiality-get`

**Requires Activation**: `activate_financial_data_retrieval_tools`

**Description**: Retrieves the defined materiality levels and associated financial groups for the engagement.

**Parameters**: None required

**Response Structure**:
Returns materiality entries containing:
- `overallMateriality`: Overall materiality amount
- `performanceMateriality`: Performance materiality amount
- `trivialThreshold`: Clearly trivial threshold
- `financialGroups`: Materiality by financial statement area

---

### 13. Accounts Assign

**Short Name**: `accounts-assign`  
**Full MCP Tool Name**: `mcp_caseware_clou_accounts-assign`

**Requires Activation**: `activate_financial_data_retrieval_tools`

**Description**: Assigns accounts to financial groups in the trial balance. Allows bulk assignment of multiple accounts to their respective financial groups.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `assignments` | array | Yes | Array of account-to-group assignments |
| `purpose` | string | No | Description of why changes are being made |
| `purposeSummary` | string | No | Short title for suggestion set |

**Assignment Object**:
```json
{
  "accountId": "uuid-base64url",
  "financialGroupId": "uuid-base64url",
  "reasoning": {
    "description": "Reason for assignment",
    "confidence": 0.95
  }
}
```

---

### 14. Risks Save

**Short Name**: `risks-save`  
**Full MCP Tool Name**: `mcp_caseware_clou_risks-save`

**Requires Activation**: `activate_control_and_risk_update_tools`

**Description**: Creates or updates risks in the engagement risk register. Supports both direct risk creation and linking to risk library entries.

> **Note**: Schema partially inferred from usage patterns. Additional parameters may be available.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | uuid-base64url | No | Existing risk ID (null for new) |
| `name` | string | Yes | Risk name/title |
| `description` | string | No | Detailed risk description |
| `category` | string | No | Risk category (Revenue, Inventory, etc.) |
| `level` | string | No | Risk level (High, Medium, Low) |
| `likelihood` | string | No | Likelihood assessment |
| `impact` | string | No | Impact assessment |
| `assertions` | array | No | Affected assertions |
| `accountGroups` | array | No | Related account groups |
| `libraryId` | uuid-base64url | No | Link to risk library entry |
| `purpose` | string | No | Description of why changes are being made |
| `purposeSummary` | string | No | Short title for suggestion set |
| `reasoning` | object | No | Reasoning object for the suggestion |

**Example - Create New Risk**:
```json
{
  "id": null,
  "name": "Revenue Recognition - Improper Cut-off",
  "description": "Risk that revenue transactions are recorded in the incorrect period due to improper cut-off procedures.",
  "category": "Revenue",
  "level": "High",
  "likelihood": "Medium",
  "impact": "High",
  "assertions": ["Cut-off", "Occurrence"],
  "accountGroups": ["Revenue", "Accounts Receivable"],
  "purpose": "Add risk identified during ratio analysis showing revenue spike in final month",
  "purposeSummary": "Revenue Cut-off Risk",
  "reasoning": {
    "description": "Current ratio analysis identified 40% of annual revenue recorded in December, significantly higher than prior years. Combined with new sales incentive program, this increases cut-off risk.",
    "confidence": 0.85
  }
}
```

**Example - Link to Risk Library**:
```json
{
  "id": null,
  "libraryId": "abc123def456ghi789jk",
  "level": "High",
  "purpose": "Link going concern risk from library based on declining current ratio trend",
  "purposeSummary": "Going Concern Risk"
}
```

---

### 15. Controls Save

**Short Name**: `controls-save`  
**Full MCP Tool Name**: `mcp_caseware_clou_controls-save`

**Requires Activation**: `activate_control_and_risk_update_tools`

**Description**: Creates or updates controls in the engagement. Links controls to risks and assertions.

> **Note**: Schema partially inferred from usage patterns. Additional parameters may be available.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | uuid-base64url | No | Existing control ID (null for new) |
| `name` | string | Yes | Control name |
| `description` | string | No | Control description |
| `type` | string | No | Control type |
| `frequency` | string | No | Operating frequency |
| `nature` | string | No | Manual or Automated |
| `assertions` | array | No | Related assertions |
| `risks` | array | No | Risks this control mitigates |
| `purpose` | string | No | Description of why changes are being made |
| `purposeSummary` | string | No | Short title for suggestion set |

---

## Excel Source Parsing

### Sheet Selection Heuristics

When an Excel workbook contains multiple sheets, select the sheet that contains the primary procedure content by scoring for:
1. Presence of a `Procedure Text` or `PCAOB Procedure Text` column header
2. Response type columns (e.g., `Response Type`, `Answer Type`)
3. Document number references matching the target (e.g., "QR-100" in sheet name or headers)

**Filtering rules:**
- Filter out sheets whose content matches an unrelated document type (e.g., annual audit vs quarterly review)
- If multiple sheets score equally, prefer the sheet with the most recent year in its name

### hideCondition Field

The `hideCondition` field on procedures accepts a condition expression string that controls when a procedure is shown or hidden.

**When authoring from Excel sources:**
- Map condition columns (e.g., "Condition 1" through "Condition 5") to the `hideCondition` field
- Handle `Inherited from above` by copying the last non-inherited condition forward to child procedures
- Expression format: `"[DocNumber] [ProcedureText] = [Value]"` (as observed in PCAOB sources)
- Default value: `null` (always visible)

### authoritativeReferences Field

The `authoritativeReferences` array on procedures accepts objects with a `reference` string field.

**Parsing from Excel:**
- Split multi-line reference strings on `\n`, not whitespace
- Each line that starts with a standard prefix (AS, AT, ISA, ISQM) is one reference
- Cap at 5 references per procedure

**Example:**
```json
"authoritativeReferences": [
  { "reference": "AS 2201.39" },
  { "reference": "AS 1015.02" }
]
```

---

## Data Type Reference

### Common Types

| Type | Format | Description | Example |
|------|--------|-------------|---------|
| uuid-base64url | string (22 chars) | URL-safe base-64 encoded UUID | `abc123def456ghi789jk` |
| depth | integer | Hierarchy level (0 = top) | `0`, `1`, `2` |
| HTML content | string | HTML-formatted text | `<p>Text here</p>` |

### Procedure Types

| Type | Description | Depth Usage |
|------|-------------|-------------|
| `group` | Top-level container, appears in navigation | 0 |
| `heading` | Section header under group | 1 |
| `procedure` | Actionable item with response | 2 |
| `conclusion` | Auto-generated via `includeConclusion: true` — do not include manually | 0 |

### Question Types

| Type | Description | Depth Usage |
|------|-------------|-------------|
| `questionSet` | Section header for questions | 0 |
| `question` | Individual question | 1 |

### Column/Answer Types

| Type | Description | Use Case |
|------|-------------|----------|
| `choice` | Multiple choice/picklist | Yes/No questions, option selection |
| `text` | Free text input | Descriptions, explanations, open-ended responses |
| `number` | Numeric input | Quantities, amounts |
| `date` | Date picker | Date selection |
| `files` | File upload | Document attachments |
| `manual` | ⚠️ **DEPRECATED** - Use `text` instead | Documented but does not create columns correctly |

**⚠️ IMPORTANT:** The `manual` type is listed in the API schema enum but does **NOT** work correctly for checklist authoring. When `"type": "manual"` is submitted, the API returns empty `columns: []` arrays and no response field is created. **Always use `"type": "text"` for manual/free-form text entry responses.**

---

## Best Practices

### Document Creation

1. **Check existing documents first**: Use `document-manager` to find existing documents and available numbers
2. **Use appropriate folder/phase**: Get folder IDs from document-manager response
3. **Avoid number conflicts**: Check for hidden documents when selecting document numbers
4. **Include purpose fields**: Always populate `purpose` and `purposeSummary` for suggestion tracking

### Checklist Authoring

1. **Every procedure needs a response type**: Never create a procedure without configuring response rows/columns
2. **Follow hierarchy**: Group → Heading → Procedure (conclusions are auto-generated via `includeConclusion: true`)
3. **Include sign-offs**: Set `includeSignOffs: true` on procedures
4. **Add notes**: Set `includeNote: true` with appropriate placeholder text
5. **Default to picklist**: Use Yes/No/N/A choices when response type is unclear
6. **Chunk large checklists**: `build_payload` handles chunking automatically — follow its `submission_instructions`

### Query Authoring

1. **Start with question sets**: First item must be a `questionSet` (depth 0)
2. **Two-column responses**: Include both text input and file upload columns
3. **Clear instructions**: Provide comprehensive instructions for clients
4. **Logical grouping**: Use question sets to organize related questions

### Response Options

1. **Order positive to negative**: Yes → No → N/A
2. **Include N/A option**: Always include unless specifically instructed otherwise
3. **Use choice for Yes/No**: Don't use text response for simple yes/no questions
4. **Text for descriptions**: Use `"type": "text"` for "Describe" or "Explain" questions (NOT `"type": "manual"`)
5. **Avoid notes for text responses**: When using `"type": "text"`, set `"includeNote": false` to avoid duplicate input fields

---

## Error Handling

Common errors and resolutions:

| Error | Cause | Resolution |
|-------|-------|------------|
| Invalid document ID | ID not found in engagement | Use document-manager to get valid IDs |
| Missing documentInfo | Creating new doc without info | Provide documentInfo for new documents |
| Invalid folder/phase | Both folder and phase specified | Use only one of folder or phase |
| Number conflict | Document number already exists | Check hidden documents, use different number |
| Missing response type | Procedure without rows/columns | Add rows with column type specification |

---

## Version Information

- **Document Version**: 2.0
- **Last Updated**: 29 January 2026
- **MCP Server**: Caseware Cloud Engagement
- **Engagement Context**: CaseWare USA Inc. 2025, Caseware Core

### Version History

| Version | Date | Changes |
|---------|------|--------|
| 2.0 | 29 Jan 2026 | Added activation tools section, multi-year configuration, statement-save, trial-balance-get, materiality-get, accounts-assign, risks-save, controls-save; added dual naming convention; added activation error handling |
| 1.0 | 25 Jan 2026 | Initial release |

---

## Appendix: Complete Example Payloads

### A. Full Checklist Creation Payload

```json
{
  "id": null,
  "documentInfo": {
    "folder": "abc123def456ghi789jk",
    "name": "Internal Control Evaluation",
    "number": "C-200"
  },
  "guidance": "Use this checklist to evaluate the design and implementation of internal controls over financial reporting. Document your testing procedures and conclusions for each control objective.",
  "includeConclusion": true,
  "conclusionTitle": "Overall Conclusion",
  "includeSignoffs": true,
  "purpose": "Create internal control evaluation checklist for SOX compliance testing",
  "purposeSummary": "Internal Control Evaluation Checklist",
  "procedures": [
    {
      "id": null,
      "depth": 0,
      "type": "group",
      "title": "Control Environment",
      "hidden": false,
      "hideCondition": null
    },
    {
      "id": null,
      "depth": 1,
      "type": "heading",
      "title": "Integrity and Ethical Values",
      "hidden": false,
      "hideCondition": null
    },
    {
      "id": null,
      "depth": 2,
      "type": "procedure",
      "title": "Code of Conduct",
      "text": "<p>Has management established and communicated a code of conduct or ethics policy to all employees?</p>",
      "guidance": "Review the entity's code of conduct. Verify distribution to employees and acknowledgment process.",
      "includeNote": true,
      "notePlaceholder": "Document your observations and testing procedures",
      "includeSignOffs": true,
      "hidden": false,
      "hideCondition": null,
      "rows": [
        {
          "columns": [
            {
              "type": "choice",
              "placeholder": "",
              "includeOtherChoice": false,
              "inlineChoices": true,
              "choices": [
                { "text": "Yes" },
                { "text": "No" },
                { "text": "N/A" }
              ]
            }
          ]
        }
      ],
      "authoritativeReferences": [
        {
          "reference": "COSO 2013 - Principle 1"
        }
      ]
    },
    {
      "id": null,
      "depth": 2,
      "type": "procedure",
      "title": "Tone at the Top",
      "text": "<p>Does management demonstrate commitment to integrity and ethical values through their actions and communications?</p>",
      "guidance": "Consider management's communications, actions in response to ethical violations, and overall culture.",
      "includeNote": true,
      "notePlaceholder": "Document evidence of management's commitment",
      "includeSignOffs": true,
      "hidden": false,
      "hideCondition": null,
      "rows": [
        {
          "columns": [
            {
              "type": "choice",
              "placeholder": "",
              "includeOtherChoice": false,
              "inlineChoices": true,
              "choices": [
                { "text": "Yes" },
                { "text": "No" },
                { "text": "N/A" }
              ]
            }
          ]
        }
      ]
    },
    {
      "id": null,
      "depth": 1,
      "type": "heading",
      "title": "Board of Directors Oversight",
      "hidden": false,
      "hideCondition": null
    },
    {
      "id": null,
      "depth": 2,
      "type": "procedure",
      "title": "Audit Committee Independence",
      "text": "<p>Is the audit committee independent and does it exercise oversight over management?</p>",
      "guidance": "Review audit committee charter, meeting minutes, and member qualifications.",
      "includeNote": true,
      "notePlaceholder": "Document audit committee composition and activities",
      "includeSignOffs": true,
      "hidden": false,
      "hideCondition": null,
      "rows": [
        {
          "columns": [
            {
              "type": "choice",
              "placeholder": "",
              "includeOtherChoice": false,
              "inlineChoices": true,
              "choices": [
                { "text": "Yes" },
                { "text": "No" },
                { "text": "N/A" }
              ]
            }
          ]
        }
      ]
    },
    {
      "id": null,
      "depth": 0,
      "type": "group",
      "title": "Risk Assessment",
      "hidden": false,
      "hideCondition": null
    },
    {
      "id": null,
      "depth": 1,
      "type": "heading",
      "title": "Risk Identification Process",
      "hidden": false,
      "hideCondition": null
    },
    {
      "id": null,
      "depth": 2,
      "type": "procedure",
      "title": "Risk Assessment Process",
      "text": "<p>Describe the entity's process for identifying and assessing risks related to financial reporting.</p>",
      "guidance": "Document how management identifies risks, assesses their significance, and determines responses.",
      "includeNote": false,
      "includeSignOffs": true,
      "hidden": false,
      "hideCondition": null,
      "rows": [
        {
          "columns": [
            {
              "type": "text",
              "placeholder": "Describe the risk assessment process in detail"
            }
          ]
        }
      ]
    },
    {
      "id": null,
      "depth": 0,
      "type": "conclusion",
      "title": "Overall Conclusion",
      "text": "<p>Based on the procedures performed above, document your overall conclusion regarding the design and implementation of internal controls.</p>",
      "includeNote": false,
      "includeSignOffs": true,
      "hidden": false,
      "hideCondition": null,
      "rows": [
        {
          "columns": [
            {
              "type": "text",
              "placeholder": "Enter your overall conclusion regarding internal controls"
            }
          ]
        }
      ]
    }
  ]
}
```

### B. Full Query Creation Payload

```json
{
  "id": null,
  "documentInfo": {
    "folder": "abc123def456ghi789jk",
    "name": "Accounts Payable Information Request",
    "number": "D-300Q"
  },
  "instructions": "Please provide the following information to assist with our audit of accounts payable. For each item, enter your response in the text field and upload any supporting documents using the file upload option. Please ensure all responses are complete and accurate. Contact us if you have any questions about the information requested.",
  "purpose": "Gather client information and documentation for accounts payable audit procedures",
  "purposeSummary": "Accounts Payable Query",
  "questions": [
    {
      "id": null,
      "depth": 0,
      "type": "questionSet",
      "title": "Vendor Information",
      "hidden": false,
      "hideCondition": null
    },
    {
      "id": null,
      "depth": 1,
      "type": "question",
      "title": "Vendor Master List",
      "text": "<p>Please provide a complete listing of all active vendors as of year-end, including vendor name, address, and payment terms.</p>",
      "rows": [
        {
          "columns": [
            { "type": "text", "placeholder": "Describe how the vendor master list is maintained" },
            { "type": "files", "placeholder": "", "fileDestination": {} }
          ]
        }
      ],
      "hidden": false,
      "hideCondition": null
    },
    {
      "id": null,
      "depth": 1,
      "type": "question",
      "title": "New Vendor Additions",
      "text": "<p>List all new vendors added during the year and describe the approval process for adding new vendors.</p>",
      "rows": [
        {
          "columns": [
            { "type": "text", "placeholder": "Describe new vendor approval process" },
            { "type": "files", "placeholder": "", "fileDestination": {} }
          ]
        }
      ],
      "hidden": false,
      "hideCondition": null
    },
    {
      "id": null,
      "depth": 0,
      "type": "questionSet",
      "title": "Invoice Processing",
      "hidden": false,
      "hideCondition": null
    },
    {
      "id": null,
      "depth": 1,
      "type": "question",
      "title": "Invoice Approval Process",
      "text": "<p>Describe the invoice approval process, including authorization limits and segregation of duties.</p>",
      "rows": [
        {
          "columns": [
            { "type": "text", "placeholder": "Describe invoice approval workflow" },
            { "type": "files", "placeholder": "", "fileDestination": {} }
          ]
        }
      ],
      "hidden": false,
      "hideCondition": null
    },
    {
      "id": null,
      "depth": 1,
      "type": "question",
      "title": "Three-Way Match",
      "text": "<p>Does the entity perform three-way matching (purchase order, receiving report, invoice)? If so, please describe the process and provide sample documentation.</p>",
      "rows": [
        {
          "columns": [
            { "type": "text", "placeholder": "Describe three-way matching process" },
            { "type": "files", "placeholder": "", "fileDestination": {} }
          ]
        }
      ],
      "hidden": false,
      "hideCondition": null
    },
    {
      "id": null,
      "depth": 0,
      "type": "questionSet",
      "title": "Year-End Procedures",
      "hidden": false,
      "hideCondition": null
    },
    {
      "id": null,
      "depth": 1,
      "type": "question",
      "title": "Accrued Liabilities",
      "text": "<p>Please provide a detailed schedule of accrued liabilities at year-end with supporting calculations.</p>",
      "rows": [
        {
          "columns": [
            { "type": "text", "placeholder": "Describe accrual methodology" },
            { "type": "files", "placeholder": "", "fileDestination": {} }
          ]
        }
      ],
      "hidden": false,
      "hideCondition": null
    },
    {
      "id": null,
      "depth": 1,
      "type": "question",
      "title": "Cut-off Procedures",
      "text": "<p>Describe the procedures performed to ensure proper cut-off of accounts payable at year-end.</p>",
      "rows": [
        {
          "columns": [
            { "type": "text", "placeholder": "Describe cut-off procedures" },
            { "type": "files", "placeholder": "", "fileDestination": {} }
          ]
        }
      ],
      "hidden": false,
      "hideCondition": null
    }
  ]
}
```

---

*End of Caseware Cloud MCP Server Technical Reference*
