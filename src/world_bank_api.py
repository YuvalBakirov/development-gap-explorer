"""Small dependency-free client for the World Bank Indicators API."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

from src.settings import (
    MAX_RETRIES,
    PAGE_SIZE,
    REQUEST_TIMEOUT_SECONDS,
    WORLD_BANK_BASE_URL,
)


class WorldBankApiError(RuntimeError):
    """Raised when the API cannot return a valid response."""


class WorldBankClient:
    def __init__(
        self,
        base_url: str = WORLD_BANK_BASE_URL,
        page_size: int = PAGE_SIZE,
        timeout_seconds: int = REQUEST_TIMEOUT_SECONDS,
        max_retries: int = MAX_RETRIES,
        opener: Callable[..., Any] = urllib.request.urlopen,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.page_size = page_size
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self._opener = opener
        self._sleep = sleep

    def get_page(self, resource: str, params: dict[str, Any], page: int) -> list[Any]:
        query = urllib.parse.urlencode({**params, "page": page, "per_page": self.page_size})
        url = f"{self.base_url}/{resource.lstrip('/')}?{query}"
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "development-gap-explorer/0.1"},
        )
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                with self._opener(request, timeout=self.timeout_seconds) as response:
                    status = getattr(response, "status", None)
                    if status is None:
                        status = response.getcode()
                    if status != 200:
                        raise WorldBankApiError(f"HTTP {status} returned by {url}")
                    payload = json.load(response)
                self._validate_envelope(payload, url)
                return payload
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, WorldBankApiError) as exc:
                last_error = exc
                if attempt + 1 < self.max_retries:
                    self._sleep(2**attempt)

        raise WorldBankApiError(
            f"Could not fetch {resource} after {self.max_retries} attempts. "
            f"Last error: {last_error}"
        ) from last_error

    @staticmethod
    def _validate_envelope(payload: Any, url: str) -> None:
        if not isinstance(payload, list) or len(payload) != 2:
            raise WorldBankApiError(f"Unexpected API envelope from {url}")
        metadata, rows = payload
        if not isinstance(metadata, dict) or not isinstance(rows, list):
            raise WorldBankApiError(f"Unexpected API data types from {url}")
        if "pages" not in metadata or "total" not in metadata:
            raise WorldBankApiError(f"Missing pagination metadata from {url}")
