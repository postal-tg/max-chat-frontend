from typing import Any

import httpx

from max_chat_frontend.core.config import Settings


class BackendUnavailableError(Exception):
    pass


class BackendApiClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url = f"{settings.backend_base_url}{settings.backend_api_prefix}"
        self.headers = {"X-Internal-API-Key": settings.internal_api_key}

    def fetch(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            response = httpx.get(f"{self.base_url}{path}", params=params, headers=self.headers, timeout=20.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise BackendUnavailableError(f"Backend request failed for {path}") from exc

    def fetch_bytes(self, path: str, params: dict[str, Any] | None = None) -> tuple[bytes, str]:
        try:
            response = httpx.get(f"{self.base_url}{path}", params=params, headers=self.headers, timeout=60.0)
            response.raise_for_status()
            return response.content, response.headers.get("content-type", "application/octet-stream")
        except httpx.HTTPError as exc:
            raise BackendUnavailableError(f"Backend request failed for {path}") from exc

