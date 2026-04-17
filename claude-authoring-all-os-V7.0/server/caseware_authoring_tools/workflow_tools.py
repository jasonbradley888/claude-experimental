"""Caseware Workflow API tools — async HTTP tools for attachments, document
signing/publishing, events, milestones, and audit history.

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

WORKFLOW_TOOL_NAMES: set[str] = {
    "attachments-get",
    "attachments-save",
    "attachments-sign",
    "document-grant-access",
    "document-publish",
    "document-sign",
    "events-get",
    "events-save",
    "history-get",
    "history-files",
}


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

def list_workflow_tools() -> list[Tool]:
    """Return MCP Tool objects for all 10 workflow API tools."""
    return [
        Tool(
            name="attachments-get",
            description="Get attachments linked to a procedure or document.",
            inputSchema={
                "type": "object",
                "properties": {
                    "owner_id": {
                        "type": "string",
                        "description": "Optional owner ID (procedure or document) to filter attachments.",
                    },
                    "attachment_id": {
                        "type": "string",
                        "description": "Optional specific attachment ID to retrieve.",
                    },
                },
            },
        ),
        Tool(
            name="attachments-save",
            description=(
                "Attach a file to a procedure or document. "
                "The file must already be uploaded via file-upload."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "owner_id": {
                        "type": "string",
                        "description": "ID of the procedure or document to attach to.",
                    },
                    "file_id": {
                        "type": "string",
                        "description": "File ID of the previously uploaded file.",
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional description for the attachment.",
                    },
                    "suggestion_set_id": {
                        "type": "string",
                        "description": "Optional suggestion set ID to create as a suggestion.",
                    },
                },
                "required": ["owner_id", "file_id"],
            },
        ),
        Tool(
            name="attachments-sign",
            description="Sign off an attachment as reviewed.",
            inputSchema={
                "type": "object",
                "properties": {
                    "attachment_id": {
                        "type": "string",
                        "description": "ID of the attachment to sign off.",
                    },
                    "suggestion_set_id": {
                        "type": "string",
                        "description": "Optional suggestion set ID.",
                    },
                },
                "required": ["attachment_id"],
            },
        ),
        Tool(
            name="document-grant-access",
            description="Grant a staff member access to a document.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "ID of the document to grant access to.",
                    },
                    "user_id": {
                        "type": "string",
                        "description": "ID of the user to grant access.",
                    },
                    "access_level": {
                        "type": "string",
                        "description": "Access level: 'read', 'write', or 'admin' (default: 'read').",
                        "enum": ["read", "write", "admin"],
                        "default": "read",
                    },
                },
                "required": ["document_id", "user_id"],
            },
        ),
        Tool(
            name="document-publish",
            description="Publish a completed document in the engagement.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "ID of the document to publish.",
                    },
                    "suggestion_set_id": {
                        "type": "string",
                        "description": "Optional suggestion set ID.",
                    },
                },
                "required": ["document_id"],
            },
        ),
        Tool(
            name="document-sign",
            description="Sign off a document as reviewed/approved.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "ID of the document to sign off.",
                    },
                    "suggestion_set_id": {
                        "type": "string",
                        "description": "Optional suggestion set ID.",
                    },
                },
                "required": ["document_id"],
            },
        ),
        Tool(
            name="events-get",
            description="Get events and milestones in the engagement.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "string",
                        "description": "Optional event ID to retrieve a specific event.",
                    },
                },
            },
        ),
        Tool(
            name="events-save",
            description="Create or update an event or milestone.",
            inputSchema={
                "type": "object",
                "properties": {
                    "delta": {
                        "type": "object",
                        "description": "The event delta object with properties to create/update.",
                    },
                    "suggestion_set_id": {
                        "type": "string",
                        "description": "Optional suggestion set ID.",
                    },
                },
                "required": ["delta"],
            },
        ),
        Tool(
            name="history-get",
            description="Get the audit trail of changes in the engagement.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "Optional document ID to filter history.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of history entries to return (default: 50).",
                        "default": 50,
                    },
                },
            },
        ),
        Tool(
            name="history-files",
            description="Get deleted or modified files history.",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_deleted": {
                        "type": "boolean",
                        "description": "Include deleted files in results (default: true).",
                        "default": True,
                    },
                },
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

async def _attachments_get(args: dict, client: CasewareAPIClient) -> dict:
    body: dict = {}
    if args.get("owner_id"):
        body["ownerId"] = args["owner_id"]
    if args.get("attachment_id"):
        body["id"] = args["attachment_id"]
    return await client.post("attachable/getAttachables", body)


async def _attachments_save(args: dict, client: CasewareAPIClient) -> dict:
    body: dict = {
        "ownerId": args["owner_id"],
        "fileId": args["file_id"],
    }
    if args.get("description"):
        body["description"] = args["description"]
    if args.get("suggestion_set_id"):
        body["suggest"] = args["suggestion_set_id"]
    return await client.post("attachable/saveAttachable", body)


async def _attachments_sign(args: dict, client: CasewareAPIClient) -> dict:
    body: dict = {"id": args["attachment_id"]}
    if args.get("suggestion_set_id"):
        body["suggest"] = args["suggestion_set_id"]
    return await client.post("attachable/sign", body)


async def _document_grant_access(args: dict, client: CasewareAPIClient) -> dict:
    return await client.post("document/grantDocumentAccess", {
        "documentId": args["document_id"],
        "userId": args["user_id"],
        "accessLevel": args.get("access_level", "read"),
    })


async def _document_publish(args: dict, client: CasewareAPIClient) -> dict:
    body: dict = {"documentId": args["document_id"]}
    if args.get("suggestion_set_id"):
        body["suggest"] = args["suggestion_set_id"]
    return await client.post("document/publishDocument", body)


async def _document_sign(args: dict, client: CasewareAPIClient) -> dict:
    body: dict = {"documentId": args["document_id"]}
    if args.get("suggestion_set_id"):
        body["suggest"] = args["suggestion_set_id"]
    return await client.post("document/sign", body)


async def _events_get(args: dict, client: CasewareAPIClient) -> dict:
    body: dict = {}
    if args.get("event_id"):
        body["id"] = args["event_id"]
    return await client.post("event/get", body)


async def _events_save(args: dict, client: CasewareAPIClient) -> dict:
    body: dict = {"delta": args["delta"]}
    if args.get("suggestion_set_id"):
        body["suggest"] = args["suggestion_set_id"]
    return await client.post("event/save", body)


async def _history_get(args: dict, client: CasewareAPIClient) -> dict:
    body: dict = {}
    if args.get("document_id"):
        body["documentId"] = args["document_id"]
    if args.get("limit"):
        body["limit"] = args["limit"]
    return await client.post("history/get", body)


async def _history_files(args: dict, client: CasewareAPIClient) -> dict:
    body: dict = {}
    if args.get("include_deleted") is not None:
        body["includeDeleted"] = args["include_deleted"]
    return await client.post("history/getDeletedFiles", body)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

_HANDLERS = {
    "attachments-get": _attachments_get,
    "attachments-save": _attachments_save,
    "attachments-sign": _attachments_sign,
    "document-grant-access": _document_grant_access,
    "document-publish": _document_publish,
    "document-sign": _document_sign,
    "events-get": _events_get,
    "events-save": _events_save,
    "history-get": _history_get,
    "history-files": _history_files,
}


async def call_workflow_tool(
    name: str, args: dict, client: CasewareAPIClient,
) -> Any:
    """Route a tool call to the appropriate workflow API handler."""
    handler = _HANDLERS[name]
    return await handler(args, client)
