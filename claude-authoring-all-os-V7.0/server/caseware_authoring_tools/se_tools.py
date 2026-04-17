"""Caseware SE API tools — async HTTP tools for file, suggestion, risk, and tag operations.

These tools call the Caseware SE REST API directly (not via MCP proxy) using
client credentials managed by TokenManager.

API URL pattern:
    {host}/{firm}/eng/{engagement_id}/api/v1.17.0/{resource}/{action}
"""

import asyncio
import hashlib
import logging
import mimetypes
import os
from typing import Any

import httpx

from mcp.types import Tool

from .token_manager import TokenManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SE_TOOL_NAMES
# ---------------------------------------------------------------------------

SE_TOOL_NAMES: set[str] = {
    "file-upload",
    "file-download",
    "suggestion-get",
    "suggestion-commit",
    "risk-assessment-get",
    "risk-assessment-save",
    "tags-get",
    "tags-save",
}


# ---------------------------------------------------------------------------
# SEClient
# ---------------------------------------------------------------------------

class SEClient:
    """HTTP client for the Caseware SE REST API.

    Builds the base URL from host, firm, and engagement_id, and uses a
    TokenManager to inject a fresh Bearer token on every request.
    """

    def __init__(
        self,
        host: str,
        firm: str,
        engagement_id: str,
        token_manager: TokenManager,
    ) -> None:
        self._base_url = (
            f"{host.rstrip('/')}/{firm}/eng/{engagement_id}/api/v1.17.0"
        )
        self._token_manager = token_manager

    async def _headers(self) -> dict[str, str]:
        """Return auth + content-type headers with a fresh Bearer token."""
        token = await self._token_manager.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def post(self, path: str, body: dict | None = None) -> Any:
        """POST to {base_url}/{path} and return parsed JSON.

        Raises httpx.HTTPStatusError if the response is not 2xx.
        """
        url = f"{self._base_url}/{path}"
        headers = await self._headers()
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=body or {}, headers=headers)
            response.raise_for_status()
            return response.json()

    async def put_raw(
        self,
        url: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> None:
        """PUT raw bytes to an arbitrary URL (e.g. a pre-signed upload URL).

        Uses a generous timeout (120 s) for large file uploads.
        """
        headers = {"Content-Type": content_type}
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.put(url, content=data, headers=headers)
            response.raise_for_status()


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

def list_se_tools() -> list[Tool]:
    """Return MCP Tool objects for all 8 SE API tools."""
    return [
        Tool(
            name="file-upload",
            description=(
                "Upload a file (Word/Excel/PDF) into the engagement. "
                "Returns the fileId. Uses a two-step initiateUpload → PUT → finalizeUpload flow."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to the file to upload",
                    },
                    "mime_type": {
                        "type": "string",
                        "description": (
                            "MIME type e.g. application/pdf. "
                            "Defaults to application/octet-stream."
                        ),
                        "default": "application/octet-stream",
                    },
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="file-download",
            description=(
                "Get metadata and download URL for a file in the engagement."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_id": {
                        "type": "string",
                        "description": "22-char uuid-base64url file ID",
                    },
                },
                "required": ["file_id"],
            },
        ),
        Tool(
            name="suggestion-get",
            description=(
                "Retrieve pending suggestion sets for a document or the whole engagement. "
                "Pass document_id to scope to a specific document."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": (
                            "Optional: 22-char uuid-base64url document ID to filter suggestions"
                        ),
                    },
                    "suggestion_set_id": {
                        "type": "string",
                        "description": "Optional: specific suggestion set ID to retrieve",
                    },
                },
            },
        ),
        Tool(
            name="suggestion-commit",
            description=(
                "Commit a suggestion set, applying all pending changes to the document."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "suggestion_set_id": {
                        "type": "string",
                        "description": "22-char uuid-base64url suggestion set ID to commit",
                    },
                },
                "required": ["suggestion_set_id"],
            },
        ),
        Tool(
            name="risk-assessment-get",
            description=(
                "Retrieve risk assessments. Pass document_id to scope to a specific document."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "Optional: document ID to filter risk assessments",
                    },
                },
            },
        ),
        Tool(
            name="risk-assessment-save",
            description=(
                "Save a risk assessment. Pass the delta (changes) and optionally "
                "a suggestion set ID to create as a suggestion."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "delta": {
                        "type": "object",
                        "description": (
                            "The risk assessment object to save "
                            "(id, kind='riskassessment', properties)"
                        ),
                    },
                    "suggestion_set_id": {
                        "type": "string",
                        "description": "Optional: commit to this suggestion set",
                    },
                },
                "required": ["delta"],
            },
        ),
        Tool(
            name="tags-get",
            description="List tags and tag categories in the engagement.",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_categories": {
                        "type": "boolean",
                        "description": "Also fetch tag categories (default: true)",
                        "default": True,
                    },
                },
            },
        ),
        Tool(
            name="tags-save",
            description="Create or update a tag.",
            inputSchema={
                "type": "object",
                "properties": {
                    "delta": {
                        "type": "object",
                        "description": (
                            "The tag object to save "
                            "(id, kind='tag', properties including name, categoryId)"
                        ),
                    },
                    "suggestion_set_id": {
                        "type": "string",
                        "description": "Optional: commit to this suggestion set",
                    },
                },
                "required": ["delta"],
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

async def _file_upload(args: dict, client: SEClient) -> dict:
    file_path = args["file_path"]
    mime_type = (
        args.get("mime_type")
        or mimetypes.guess_type(file_path)[0]
        or "application/octet-stream"
    )
    with open(file_path, "rb") as f:
        data = f.read()
    md5 = hashlib.md5(data).hexdigest()
    file_name = os.path.basename(file_path)

    init_resp = await client.post(
        "file/initiateUpload",
        {
            "fileName": file_name,
            "length": len(data),
            "mimeType": mime_type,
            "md5hex": md5,
        },
    )
    upload_url = init_resp.get("uploadUrl") or init_resp.get("url")
    file_id = init_resp.get("fileId") or init_resp.get("id")

    if upload_url:
        await client.put_raw(upload_url, data, mime_type)

    final_resp = await client.post("file/finalizeUpload", {"fileId": file_id})
    return {
        "success": True,
        "fileId": file_id,
        "fileName": file_name,
        "finalizeResponse": final_resp,
    }


async def _file_download(args: dict, client: SEClient) -> dict:
    return await client.post("file/get", {"id": args["file_id"]})


async def _suggestion_get(args: dict, client: SEClient) -> dict:
    body: dict = {}
    if args.get("suggestion_set_id"):
        body["suggest"] = args["suggestion_set_id"]
    if args.get("document_id"):
        body["filterId"] = args["document_id"]
        body["filterKind"] = "document"
    return await client.post("suggest/getSuggestions", body)


async def _suggestion_commit(args: dict, client: SEClient) -> dict:
    return await client.post(
        "suggest/commitSuggestionSet",
        {"suggest": args["suggestion_set_id"]},
    )


async def _risk_assessment_get(args: dict, client: SEClient) -> dict:
    body: dict = {}
    if args.get("document_id"):
        body["filter"] = {"id": args["document_id"]}
    return await client.post("riskassessment/getRiskAssessments", body)


async def _risk_assessment_save(args: dict, client: SEClient) -> dict:
    body: dict = {"delta": args["delta"]}
    if args.get("suggestion_set_id"):
        body["suggest"] = args["suggestion_set_id"]
    return await client.post("riskassessment/saveRiskAssessment", body)


async def _tags_get(args: dict, client: SEClient) -> dict:
    tags = await client.post("tag/getTags", {})
    result: dict = {"tags": tags}
    if args.get("include_categories", True):
        categories = await client.post("tag/getTagCategories", {})
        result["categories"] = categories
    return result


async def _tags_save(args: dict, client: SEClient) -> dict:
    body: dict = {"delta": args["delta"]}
    if args.get("suggestion_set_id"):
        body["suggest"] = args["suggestion_set_id"]
    return await client.post("tag/saveTag", body)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

_HANDLERS = {
    "file-upload": _file_upload,
    "file-download": _file_download,
    "suggestion-get": _suggestion_get,
    "suggestion-commit": _suggestion_commit,
    "risk-assessment-get": _risk_assessment_get,
    "risk-assessment-save": _risk_assessment_save,
    "tags-get": _tags_get,
    "tags-save": _tags_save,
}


async def call_se_tool(name: str, args: dict, client: SEClient) -> Any:
    """Route a tool call to the appropriate SE API handler.

    Raises KeyError if name is not a recognised SE tool.
    """
    handler = _HANDLERS[name]
    return await handler(args, client)
