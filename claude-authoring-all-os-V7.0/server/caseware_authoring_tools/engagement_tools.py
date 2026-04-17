"""Caseware Engagement API tools — async HTTP tools for engagement lifecycle,
users, roles, templates, and visibility operations.

These tools call the Caseware SE REST API directly using CasewareAPIClient.

API URL pattern:
    {host}/{firm}/e/eng/{engagement_id}/api/v1.17.0/{resource}/{action}
"""

from typing import Any

from mcp.types import Tool

from .api_client import CasewareAPIClient

# ---------------------------------------------------------------------------
# Tool names
# ---------------------------------------------------------------------------

ENGAGEMENT_TOOL_NAMES: set[str] = {
    "engagement-get",
    "engagement-create",
    "engagement-lock",
    "engagement-unlock",
    "engagement-rollforward",
    "engagement-copyobjects",
    "users-get",
    "roles-get",
    "staff-assign",
    "firm-templates-get",
    "visibility-get",
}


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

def list_engagement_tools() -> list[Tool]:
    """Return MCP Tool objects for all 11 engagement API tools."""
    return [
        Tool(
            name="engagement-get",
            description="Get properties and details of the current engagement.",
            inputSchema={
                "type": "object",
                "properties": {
                    "engagement_id": {
                        "type": "string",
                        "description": "Optional engagement ID. Defaults to the configured engagement.",
                    },
                },
            },
        ),
        Tool(
            name="engagement-create",
            description=(
                "Create a new engagement from a firm template. "
                "Returns the new engagement details."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "template": {
                        "type": "string",
                        "description": "Template name or ID to create the engagement from.",
                    },
                    "file_name": {
                        "type": "string",
                        "description": "Optional file name for the new engagement.",
                    },
                    "entity": {
                        "type": "string",
                        "description": "Optional entity/client name.",
                    },
                    "year_begin": {
                        "type": "string",
                        "description": "Optional fiscal year begin date (ISO 8601).",
                    },
                    "year_end": {
                        "type": "string",
                        "description": "Optional fiscal year end date (ISO 8601).",
                    },
                    "period_type": {
                        "type": "string",
                        "description": "Optional period type (e.g., 'annual', 'quarterly').",
                    },
                    "current_period": {
                        "type": "string",
                        "description": "Optional current period identifier.",
                    },
                    "prior_years": {
                        "type": "integer",
                        "description": "Optional number of prior years to include.",
                    },
                },
                "required": ["template"],
            },
        ),
        Tool(
            name="engagement-lock",
            description="Lock the engagement for review. Prevents further edits.",
            inputSchema={
                "type": "object",
                "properties": {
                    "engagement_id": {
                        "type": "string",
                        "description": "Optional engagement ID. Defaults to the configured engagement.",
                    },
                },
            },
        ),
        Tool(
            name="engagement-unlock",
            description="Unlock the engagement for editing.",
            inputSchema={
                "type": "object",
                "properties": {
                    "engagement_id": {
                        "type": "string",
                        "description": "Optional engagement ID. Defaults to the configured engagement.",
                    },
                },
            },
        ),
        Tool(
            name="engagement-rollforward",
            description="Roll forward the engagement to a new period.",
            inputSchema={
                "type": "object",
                "properties": {
                    "engagement_id": {
                        "type": "string",
                        "description": "Optional engagement ID. Defaults to the configured engagement.",
                    },
                },
            },
        ),
        Tool(
            name="engagement-copyobjects",
            description=(
                "Copy procedures or documents from another engagement into this one."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "source_engagement_id": {
                        "type": "string",
                        "description": "Engagement ID to copy objects from.",
                    },
                    "object_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Array of object IDs to copy.",
                    },
                    "object_kind": {
                        "type": "string",
                        "description": "Optional kind of objects being copied.",
                    },
                },
                "required": ["source_engagement_id", "object_ids"],
            },
        ),
        Tool(
            name="users-get",
            description="List staff members in the engagement. Optionally include contacts.",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_contacts": {
                        "type": "boolean",
                        "description": "Also fetch contacts in addition to staff (default: false).",
                        "default": False,
                    },
                },
            },
        ),
        Tool(
            name="roles-get",
            description="List available roles and optionally role sets in the engagement.",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_role_sets": {
                        "type": "boolean",
                        "description": "Also fetch role sets (default: true).",
                        "default": True,
                    },
                },
            },
        ),
        Tool(
            name="staff-assign",
            description="Assign a staff member to a role in the engagement.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID of the staff member to assign.",
                    },
                    "role_id": {
                        "type": "string",
                        "description": "Optional role ID to assign the user to.",
                    },
                    "delta": {
                        "type": "object",
                        "description": "Optional delta object for complex user updates.",
                    },
                },
                "required": ["user_id"],
            },
        ),
        Tool(
            name="firm-templates-get",
            description="List available engagement templates from the firm.",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_source_templates": {
                        "type": "boolean",
                        "description": "Include source template details (default: false).",
                        "default": False,
                    },
                },
            },
        ),
        Tool(
            name="visibility-get",
            description="Get visibility rules for the engagement or a specific document.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "Optional document ID to filter visibility rules.",
                    },
                },
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

async def _engagement_get(args: dict, client: CasewareAPIClient) -> dict:
    body: dict = {}
    if args.get("engagement_id"):
        body["id"] = args["engagement_id"]
    return await client.post("engagement/getEngagementProperties", body)


async def _engagement_create(args: dict, client: CasewareAPIClient) -> dict:
    body: dict = {"template": args["template"]}
    for key in ("file_name", "entity", "year_begin", "year_end",
                "period_type", "current_period", "prior_years"):
        if args.get(key) is not None:
            body[key] = args[key]
    return await client.post("firm/createEngagement", body)


async def _engagement_lock(args: dict, client: CasewareAPIClient) -> dict:
    body: dict = {}
    if args.get("engagement_id"):
        body["id"] = args["engagement_id"]
    return await client.post("engagement/lockEngagement", body)


async def _engagement_unlock(args: dict, client: CasewareAPIClient) -> dict:
    body: dict = {}
    if args.get("engagement_id"):
        body["id"] = args["engagement_id"]
    return await client.post("engagement/unlockEngagement", body)


async def _engagement_rollforward(args: dict, client: CasewareAPIClient) -> dict:
    body: dict = {}
    if args.get("engagement_id"):
        body["id"] = args["engagement_id"]
    return await client.post("engagement/rollForward", body)


async def _engagement_copyobjects(args: dict, client: CasewareAPIClient) -> dict:
    return await client.post("engagement/copyObjects", {
        "sourceEngagementId": args["source_engagement_id"],
        "objectIds": args["object_ids"],
        **({"objectKind": args["object_kind"]} if args.get("object_kind") else {}),
    })


async def _users_get(args: dict, client: CasewareAPIClient) -> dict:
    if args.get("include_contacts"):
        return await client.post("user/getAllStaffAndContacts", {})
    return await client.post("user/getAllStaff", {})


async def _roles_get(args: dict, client: CasewareAPIClient) -> dict:
    roles = await client.post("role/get", {})
    result: dict = {"roles": roles}
    if args.get("include_role_sets", True):
        role_sets = await client.post("roleset/get", {})
        result["roleSets"] = role_sets
    return result


async def _staff_assign(args: dict, client: CasewareAPIClient) -> dict:
    body: dict = {"id": args["user_id"]}
    if args.get("role_id"):
        body["roleId"] = args["role_id"]
    if args.get("delta"):
        body["delta"] = args["delta"]
    return await client.post("user/saveUser", body)


async def _firm_templates_get(args: dict, client: CasewareAPIClient) -> dict:
    body: dict = {}
    if args.get("include_source_templates"):
        body["includeSourceTemplates"] = True
    return await client.post("firm/getTemplates", body)


async def _visibility_get(args: dict, client: CasewareAPIClient) -> dict:
    body: dict = {}
    if args.get("document_id"):
        body["documentId"] = args["document_id"]
    return await client.post("visibility/getVisibilities", body)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

_HANDLERS = {
    "engagement-get": _engagement_get,
    "engagement-create": _engagement_create,
    "engagement-lock": _engagement_lock,
    "engagement-unlock": _engagement_unlock,
    "engagement-rollforward": _engagement_rollforward,
    "engagement-copyobjects": _engagement_copyobjects,
    "users-get": _users_get,
    "roles-get": _roles_get,
    "staff-assign": _staff_assign,
    "firm-templates-get": _firm_templates_get,
    "visibility-get": _visibility_get,
}


async def call_engagement_tool(
    name: str, args: dict, client: CasewareAPIClient,
) -> Any:
    """Route a tool call to the appropriate engagement API handler."""
    handler = _HANDLERS[name]
    return await handler(args, client)
