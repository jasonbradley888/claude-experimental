"""Caseware Cloud token manager — acquires and auto-refreshes Bearer tokens
via the API client credentials flow.

Usage:
    manager = TokenManager(host, firm_name, client_id, client_secret)
    token = await manager.get_token()   # auto-refreshes when near expiry
"""

import logging
import time

import httpx

logger = logging.getLogger(__name__)

TOKEN_TTL_SECONDS = 29 * 60  # 29 minutes (Caseware's issued token lifetime)


class TokenManager:
    """Acquires and caches a Bearer token using API client credentials.

    Token endpoint: POST {host}/{firm}/ms/caseware-cloud/api/v2/auth/token
    Payload:        { ClientId, ClientSecret, Language }
    Response:       { Token: "<bearer>" }
    """

    def __init__(self, host: str, firm_name: str, client_id: str, client_secret: str) -> None:
        self._host = host.rstrip("/")
        self._firm_name = firm_name
        self._client_id = client_id
        self._client_secret = client_secret
        self._token: str | None = None
        self._token_ts: float = 0.0
        self._token_url = (
            f"{self._host}/{self._firm_name}/ms/caseware-cloud/api/v2/auth/token"
        )

    def _is_valid(self) -> bool:
        return (
            self._token is not None
            and (time.monotonic() - self._token_ts) < TOKEN_TTL_SECONDS
        )

    async def get_token(self) -> str:
        """Return a valid Bearer token, refreshing if necessary."""
        if not self._is_valid():
            await self._refresh()
        return self._token  # type: ignore[return-value]

    async def _refresh(self) -> None:
        logger.info("Acquiring Caseware Cloud Bearer token from %s", self._token_url)
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self._token_url,
                json={
                    "ClientId": self._client_id,
                    "ClientSecret": self._client_secret,
                    "Language": "en",
                },
            )

        if response.status_code != 200:
            raise RuntimeError(
                f"Token endpoint returned {response.status_code}: {response.text}"
            )

        data = response.json()
        token = data.get("Token")
        if not token:
            raise RuntimeError("Token endpoint did not return a Token field")

        self._token = token
        self._token_ts = time.monotonic()
        logger.info("Bearer token acquired successfully (TTL: 29 min)")
