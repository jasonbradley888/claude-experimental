"""Shared HTTP clients for Caseware SE REST API endpoints.

CasewareAPIClient — Bearer-token authenticated client for the SE API
(engagement, workflow, and general SE endpoints).

AnalyticsAPIClient — Machine-ID cookie authenticated client for the
Analytics Library API (different base URL and auth mechanism).

Both use TokenManager for automatic token refresh.
"""

import base64
import logging
from typing import Any, Optional

import httpx

from .token_manager import TokenManager

logger = logging.getLogger(__name__)


class CasewareAPIClient:
    """HTTP client for the Caseware SE REST API (v1.17.0).

    Used by engagement, workflow, and SE tool modules.  Builds the base URL
    from host/firm/engagement_id and injects a fresh Bearer token on every
    request via TokenManager.
    """

    def __init__(
        self,
        host: str,
        firm: str,
        engagement_id: str,
        token_manager: TokenManager,
    ) -> None:
        self._base_url = (
            f"{host.rstrip('/')}/{firm}/e/eng/{engagement_id}/api/v1.17.0"
        )
        self._token_manager = token_manager

    async def _headers(self) -> dict[str, str]:
        token = await self._token_manager.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def post(self, path: str, body: dict | None = None) -> Any:
        """POST to {base_url}/{path} and return parsed JSON."""
        url = f"{self._base_url}/{path}"
        headers = await self._headers()
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=body or {}, headers=headers)
            response.raise_for_status()
            return response.json()

    async def get(self, path: str, params: dict | None = None) -> Any:
        """GET from {base_url}/{path} and return parsed JSON."""
        url = f"{self._base_url}/{path}"
        headers = await self._headers()
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()


class AnalyticsAPIClient:
    """HTTP client for the Caseware Analytics Library API.

    Uses a different base URL pattern and authenticates via a machine-ID
    cookie (derived from the bearer token) rather than a Bearer header.

    Analytics API URL pattern:
        {host}/{firm}/e/eng/{engagement_id}/s/analytics-library/api/v1/{resource}
    """

    def __init__(
        self,
        host: str,
        firm: str,
        engagement_id: str,
        token_manager: TokenManager,
    ) -> None:
        self._base_url = (
            f"{host.rstrip('/')}/{firm}/e/eng/{engagement_id}"
            f"/s/analytics-library/api/v1"
        )
        self._token_manager = token_manager
        self._machine_id: Optional[str] = None

    async def _get_machine_id(self) -> str:
        """Derive the machine ID from the bearer token.

        Bearer token format (base64-encoded): uuid1:uuid2:uuid3
        Machine ID is the second UUID (uuid2).
        """
        if self._machine_id is None:
            token = await self._token_manager.get_token()
            try:
                decoded = base64.b64decode(token).decode("utf-8")
                parts = decoded.split(":")
                if len(parts) >= 2 and parts[1]:
                    self._machine_id = parts[1]
                else:
                    raise ValueError("Token does not contain machine ID")
            except Exception as e:
                logger.warning("Could not derive machine ID from token: %s", e)
                raise RuntimeError(
                    "Cannot derive machine ID from bearer token — "
                    "analytics tools require a valid token"
                ) from e
        return self._machine_id

    async def _cookies(self) -> dict[str, str]:
        machine_id = await self._get_machine_id()
        return {"MachineId": machine_id}

    async def _headers(self) -> dict[str, str]:
        token = await self._token_manager.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def post(self, path: str, body: dict | None = None) -> Any:
        """POST to {base_url}/{path} and return parsed JSON."""
        url = f"{self._base_url}/{path}"
        headers = await self._headers()
        cookies = await self._cookies()
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url, json=body or {}, headers=headers, cookies=cookies,
            )
            response.raise_for_status()
            return response.json()

    async def get(self, path: str, params: dict | None = None) -> Any:
        """GET from {base_url}/{path} and return parsed JSON."""
        url = f"{self._base_url}/{path}"
        headers = await self._headers()
        cookies = await self._cookies()
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                url, params=params, headers=headers, cookies=cookies,
            )
            response.raise_for_status()
            return response.json()
