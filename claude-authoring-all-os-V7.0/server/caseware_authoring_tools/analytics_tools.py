"""Caseware Analytics Library API tools — async HTTP tools for analytics
catalog, predefined configs, triggering, status, execution details,
results, notebooks, permissions, and dataset management.

These tools call the Analytics Library REST API using AnalyticsAPIClient
(different base URL and machine-ID cookie auth from the SE API).

API URL pattern:
    {host}/{firm}/e/eng/{engagement_id}/s/analytics-library/api/v1/{resource}
"""

from typing import Any

from mcp.types import Tool

from .api_client import AnalyticsAPIClient

# ---------------------------------------------------------------------------
# Tool names
# ---------------------------------------------------------------------------

ANALYTICS_TOOL_NAMES: set[str] = {
    "analytics-get-catalog",
    "analytics-get-catalog-by-analytic-id",
    "analytics-get-predefined-configs",
    "analytics-get-predefined-config-by-id",
    "analytics-get-predefined-config-by-analytic-id",
    "analytics-get-predefined-configs-by-tags",
    "analytics-trigger",
    "analytics-get-status",
    "analytics-get-status-grouped-by-dataset-type",
    "analytics-get-execution-details",
    "analytics-get-execution-details-by-config-ids",
    "analytics-get-execution-details-by-result-id",
    "analytics-get-dataset",
    "analytics-get-notebook-content",
    "analytics-get-notebook-data",
    "analytics-get-permissions",
    "analytics-delete-datasets",
}


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

def list_analytics_tools() -> list[Tool]:
    """Return MCP Tool objects for all 17 analytics API tools."""
    return [
        # --- Catalog Discovery ---
        Tool(
            name="analytics-get-catalog",
            description=(
                "List all available analytics in the catalog. "
                "Returns IDs, names, descriptions, tags, inputs, outputs, and parameters."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="analytics-get-catalog-by-analytic-id",
            description="Get the full definition for a specific analytic by its ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "analytic_id": {
                        "type": "string",
                        "description": "Analytic ID (e.g., 'cwi.high_amount').",
                    },
                },
                "required": ["analytic_id"],
            },
        ),

        # --- Predefined Configurations ---
        Tool(
            name="analytics-get-predefined-configs",
            description=(
                "List all predefined analytics configurations. "
                "Returns ready-to-use configs with inputs, parameters, and column mappings."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="analytics-get-predefined-config-by-id",
            description="Get a specific predefined configuration by its ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "predefined_config_id": {
                        "type": "string",
                        "description": "Predefined config ID (e.g., 'generic.cwi.cwi.notebook_id.config_id').",
                    },
                },
                "required": ["predefined_config_id"],
            },
        ),
        Tool(
            name="analytics-get-predefined-config-by-analytic-id",
            description="Get all predefined configurations for a specific analytic.",
            inputSchema={
                "type": "object",
                "properties": {
                    "analytic_id": {
                        "type": "string",
                        "description": "Analytic ID to get configurations for.",
                    },
                },
                "required": ["analytic_id"],
            },
        ),
        Tool(
            name="analytics-get-predefined-configs-by-tags",
            description="Filter predefined configurations by tags.",
            inputSchema={
                "type": "object",
                "properties": {
                    "exclude_tags": {
                        "type": "string",
                        "description": "Comma-separated tags to exclude.",
                    },
                    "include_only_tags": {
                        "type": "string",
                        "description": "Comma-separated tags to include (filter to only these).",
                    },
                },
            },
        ),

        # --- Trigger ---
        Tool(
            name="analytics-trigger",
            description=(
                "Trigger one or more analytics to run on demand. "
                "Returns accepted/rejected analytics with status."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "analytics": {
                        "type": "array",
                        "description": (
                            "Array of analytics to trigger. Each item should have "
                            "analyticId, and optionally inputs, parameters, dataSourceType."
                        ),
                        "items": {
                            "type": "object",
                            "properties": {
                                "analytic_id": {
                                    "type": "string",
                                    "description": "ID of the analytic to run.",
                                },
                                "inputs": {
                                    "type": "object",
                                    "description": "Optional input mappings.",
                                },
                                "parameters": {
                                    "type": "object",
                                    "description": "Optional parameter overrides.",
                                },
                                "data_source_type": {
                                    "type": "string",
                                    "description": "Optional data source type.",
                                },
                            },
                            "required": ["analytic_id"],
                        },
                    },
                },
                "required": ["analytics"],
            },
        ),

        # --- Status Monitoring ---
        Tool(
            name="analytics-get-status",
            description=(
                "Check execution status for analytics by configuration IDs. "
                "Statuses: PENDING, IN_PROGRESS, RUN_FAILED, RUN_SUCCESSFUL, "
                "CANCELLED, PROCESSING_OUTPUT, NOT_FOUND."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "configuration_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Array of configuration IDs to check status for.",
                    },
                    "consolidation_entity_id": {
                        "type": "string",
                        "description": "Optional consolidation entity ID.",
                    },
                },
                "required": ["configuration_ids"],
            },
        ),
        Tool(
            name="analytics-get-status-grouped-by-dataset-type",
            description="Get analytics execution status grouped by dataset type.",
            inputSchema={
                "type": "object",
                "properties": {
                    "configuration_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Array of configuration IDs to check.",
                    },
                    "consolidation_entity_id": {
                        "type": "string",
                        "description": "Optional consolidation entity ID.",
                    },
                },
                "required": ["configuration_ids"],
            },
        ),

        # --- Execution Details ---
        Tool(
            name="analytics-get-execution-details",
            description=(
                "Get execution details for a single analytics configuration. "
                "Returns analytic version, status, timestamps, datasets, parameters."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "configuration_id": {
                        "type": "string",
                        "description": "Configuration ID to get execution details for.",
                    },
                    "consolidation_entity_id": {
                        "type": "string",
                        "description": "Optional consolidation entity ID.",
                    },
                },
                "required": ["configuration_id"],
            },
        ),
        Tool(
            name="analytics-get-execution-details-by-config-ids",
            description="Get execution details for multiple analytics configurations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "configuration_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Array of configuration IDs.",
                    },
                    "consolidation_entity_id": {
                        "type": "string",
                        "description": "Optional consolidation entity ID.",
                    },
                },
                "required": ["configuration_ids"],
            },
        ),
        Tool(
            name="analytics-get-execution-details-by-result-id",
            description="Look up execution details by result ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "result_id": {
                        "type": "string",
                        "description": "Result ID (e.g., 'SjaZZ5lMSXWWfwkRlLTlYw').",
                    },
                },
                "required": ["result_id"],
            },
        ),

        # --- Results ---
        Tool(
            name="analytics-get-dataset",
            description=(
                "Get output dataset download URLs for an analytics result. "
                "Returns pre-signed URLs for dataset downloads."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "result_id": {
                        "type": "string",
                        "description": "Result ID to get datasets for.",
                    },
                },
                "required": ["result_id"],
            },
        ),
        Tool(
            name="analytics-get-notebook-content",
            description="Get the full notebook content for an analytics result.",
            inputSchema={
                "type": "object",
                "properties": {
                    "result_id": {
                        "type": "string",
                        "description": "Result ID to get notebook content for.",
                    },
                    "cell_tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional cell tags to filter (max 5).",
                        "maxItems": 5,
                    },
                },
                "required": ["result_id"],
            },
        ),
        Tool(
            name="analytics-get-notebook-data",
            description="Get structured output data from an analytics notebook.",
            inputSchema={
                "type": "object",
                "properties": {
                    "result_id": {
                        "type": "string",
                        "description": "Result ID to get notebook data for.",
                    },
                    "output_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional output names to filter.",
                    },
                },
                "required": ["result_id"],
            },
        ),

        # --- Authorization ---
        Tool(
            name="analytics-get-permissions",
            description=(
                "Get current user's analytics permissions. "
                "Returns edit rights and engagement lock status."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),

        # --- Deletion ---
        Tool(
            name="analytics-delete-datasets",
            description=(
                "Delete analytics datasets by configuration IDs. "
                "WARNING: This is a destructive operation."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "configuration_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Array of configuration IDs (with optional suffixes) to delete.",
                    },
                    "consolidation_entity_id": {
                        "type": "string",
                        "description": "Optional consolidation entity ID.",
                    },
                },
                "required": ["configuration_ids"],
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

# --- Catalog ---

async def _get_catalog(args: dict, client: AnalyticsAPIClient) -> Any:
    return await client.get("catalog")


async def _get_catalog_by_analytic_id(args: dict, client: AnalyticsAPIClient) -> Any:
    return await client.get(f"catalog/{args['analytic_id']}")


# --- Predefined Configs ---

async def _get_predefined_configs(args: dict, client: AnalyticsAPIClient) -> Any:
    return await client.get("predefinedConfigs")


async def _get_predefined_config_by_id(args: dict, client: AnalyticsAPIClient) -> Any:
    return await client.get(f"predefinedConfigs/{args['predefined_config_id']}")


async def _get_predefined_config_by_analytic_id(args: dict, client: AnalyticsAPIClient) -> Any:
    return await client.get(f"predefinedConfigs/analytic/{args['analytic_id']}")


async def _get_predefined_configs_by_tags(args: dict, client: AnalyticsAPIClient) -> Any:
    params: dict = {}
    if args.get("exclude_tags"):
        params["excludeTags"] = args["exclude_tags"]
    if args.get("include_only_tags"):
        params["includeOnlyTags"] = args["include_only_tags"]
    return await client.get("predefinedConfigsByTags", params=params)


# --- Trigger ---

async def _trigger(args: dict, client: AnalyticsAPIClient) -> Any:
    analytics_list = []
    for item in args["analytics"]:
        entry: dict = {"analyticId": item["analytic_id"]}
        if item.get("inputs"):
            entry["inputs"] = item["inputs"]
        if item.get("parameters"):
            entry["parameters"] = item["parameters"]
        if item.get("data_source_type"):
            entry["dataSourceType"] = item["data_source_type"]
        analytics_list.append(entry)
    return await client.post("trigger", {"analytics": analytics_list})


# --- Status ---

async def _get_status(args: dict, client: AnalyticsAPIClient) -> Any:
    body: dict = {"configurationIds": args["configuration_ids"]}
    if args.get("consolidation_entity_id"):
        body["consolidationEntityId"] = args["consolidation_entity_id"]
    return await client.post("getStatus", body)


async def _get_status_grouped(args: dict, client: AnalyticsAPIClient) -> Any:
    body: dict = {"configurationIds": args["configuration_ids"]}
    if args.get("consolidation_entity_id"):
        body["consolidationEntityId"] = args["consolidation_entity_id"]
    return await client.post("status/getStatusGroupedByDatasetType", body)


# --- Execution Details ---

async def _get_execution_details(args: dict, client: AnalyticsAPIClient) -> Any:
    params: dict = {}
    if args.get("consolidation_entity_id"):
        params["consolidationEntityId"] = args["consolidation_entity_id"]
    return await client.get(
        f"executionDetails/{args['configuration_id']}", params=params or None,
    )


async def _get_execution_details_by_config_ids(args: dict, client: AnalyticsAPIClient) -> Any:
    body: dict = {"configurationIds": args["configuration_ids"]}
    if args.get("consolidation_entity_id"):
        body["consolidationEntityId"] = args["consolidation_entity_id"]
    return await client.post("executionDetails", body)


async def _get_execution_details_by_result_id(args: dict, client: AnalyticsAPIClient) -> Any:
    return await client.get(f"executionDetailsByResultId/{args['result_id']}")


# --- Results ---

async def _get_dataset(args: dict, client: AnalyticsAPIClient) -> Any:
    return await client.get(f"result/dataset/{args['result_id']}")


async def _get_notebook_content(args: dict, client: AnalyticsAPIClient) -> Any:
    params: dict = {}
    if args.get("cell_tags"):
        params["cellTags"] = ",".join(args["cell_tags"])
    return await client.get(
        f"result-notebook/content/{args['result_id']}", params=params or None,
    )


async def _get_notebook_data(args: dict, client: AnalyticsAPIClient) -> Any:
    params: dict = {}
    if args.get("output_names"):
        params["outputNames"] = ",".join(args["output_names"])
    return await client.get(
        f"result-notebook/data/{args['result_id']}", params=params or None,
    )


# --- Authorization ---

async def _get_permissions(args: dict, client: AnalyticsAPIClient) -> Any:
    return await client.get("authorization/permissions")


# --- Deletion ---

async def _delete_datasets(args: dict, client: AnalyticsAPIClient) -> Any:
    body: dict = {"configurationIds": args["configuration_ids"]}
    if args.get("consolidation_entity_id"):
        body["consolidationEntityId"] = args["consolidation_entity_id"]
    return await client.post("deletion/deleteDatasets", body)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

_HANDLERS = {
    "analytics-get-catalog": _get_catalog,
    "analytics-get-catalog-by-analytic-id": _get_catalog_by_analytic_id,
    "analytics-get-predefined-configs": _get_predefined_configs,
    "analytics-get-predefined-config-by-id": _get_predefined_config_by_id,
    "analytics-get-predefined-config-by-analytic-id": _get_predefined_config_by_analytic_id,
    "analytics-get-predefined-configs-by-tags": _get_predefined_configs_by_tags,
    "analytics-trigger": _trigger,
    "analytics-get-status": _get_status,
    "analytics-get-status-grouped-by-dataset-type": _get_status_grouped,
    "analytics-get-execution-details": _get_execution_details,
    "analytics-get-execution-details-by-config-ids": _get_execution_details_by_config_ids,
    "analytics-get-execution-details-by-result-id": _get_execution_details_by_result_id,
    "analytics-get-dataset": _get_dataset,
    "analytics-get-notebook-content": _get_notebook_content,
    "analytics-get-notebook-data": _get_notebook_data,
    "analytics-get-permissions": _get_permissions,
    "analytics-delete-datasets": _delete_datasets,
}


async def call_analytics_tool(
    name: str, args: dict, client: AnalyticsAPIClient,
) -> Any:
    """Route a tool call to the appropriate analytics API handler."""
    handler = _HANDLERS[name]
    return await handler(args, client)
